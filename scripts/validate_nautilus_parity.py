import argparse
import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

from tradingview_scraper.portfolio_engines.backtest_simulators import NautilusSimulator, ReturnsSimulator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("parity_validator")


def extract_physical_symbol(atom_id: str) -> str:
    """
    Extracts physical symbol from strategy atom ID.
    Heuristic: Split by '_rating_' or '_logic_' or similar, or just take the first part if no underscore logic.
    Example: 'BINANCE:BTCUSDT_rating_ma_long_LONG' -> 'BINANCE:BTCUSDT'
    """
    # Common separators in synthesis
    separators = ["_rating_", "_logic_", "_momentum_", "_trend_", "_reversion_"]

    for sep in separators:
        if sep in atom_id:
            return atom_id.split(sep)[0]

    # Fallback: if it ends with _LONG or _SHORT, try to strip it
    if atom_id.endswith("_LONG"):
        return atom_id.rsplit("_LONG", 1)[0]
    if atom_id.endswith("_SHORT"):
        return atom_id.rsplit("_SHORT", 1)[0]

    return atom_id


def load_run_data(run_id: str, base_dir: Path):
    """
    Loads weights and returns from a specific run directory.
    Reconstructs the full weight history from audit.jsonl.
    """
    run_dir = base_dir / run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    # 1. Load Returns Matrix
    returns_path = run_dir / "data" / "returns_matrix.parquet"
    if not returns_path.exists():
        # Fallback to shared lakehouse if not in run (older runs)
        # But usually runs have it.
        raise FileNotFoundError(f"Returns matrix not found in run: {returns_path}")

    logger.info(f"Loading returns from {returns_path}...")
    returns_df = pd.read_parquet(returns_path)

    # 2. Parse Audit Ledger for Weights
    audit_path = run_dir / "audit.jsonl"
    if not audit_path.exists():
        raise FileNotFoundError(f"Audit ledger not found: {audit_path}")

    logger.info(f"Parsing audit ledger {audit_path}...")

    weight_records = []

    with open(audit_path, "r") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("step") == "backtest_optimize" and rec.get("status") == "success":
                    # Extract Context (Window Index) and Metrics (Weights)
                    ctx = rec.get("context", {})
                    metrics = rec.get("outcome", {}).get("metrics", {})

                    window_idx = ctx.get("window_index")
                    raw_weights = metrics.get("weights", {})

                    if window_idx is None or not raw_weights:
                        continue

                    # Determine Timestamp from Window Index
                    # The window index 'i' in backtest_engine corresponds to test_rets starting at 'i'
                    # So the weights calculated at 'i' are effective for [i, i+test_window)
                    # The rebalance happens at i (or just before).
                    # We map window_index to the timestamp in returns_df.index
                    if window_idx < len(returns_df):
                        ts = returns_df.index[window_idx]

                        # Flatten Weights
                        flat_weights = {}
                        for atom, w in raw_weights.items():
                            phys = extract_physical_symbol(atom)
                            flat_weights[phys] = flat_weights.get(phys, 0.0) + float(w)

                        for phys, w in flat_weights.items():
                            weight_records.append(
                                {
                                    "Timestamp": ts,
                                    "Symbol": phys,
                                    "Net_Weight": w,
                                    "Weight": abs(w),  # Gross weight
                                }
                            )
            except Exception as e:
                logger.warning(f"Failed to parse line: {e}")

    if not weight_records:
        raise ValueError("No optimization weights found in audit ledger.")

    weights_df = pd.DataFrame(weight_records)
    logger.info(f"Reconstructed {len(weights_df)} weight records.")

    # Pivot to wide format for visualization/checking (optional)
    # But simulators expect long format or can handle it.
    # ReturnsSimulator expects DataFrame with [Symbol, Weight/Net_Weight] columns, usually per step?
    # Actually, ReturnsSimulator simulate() takes 'weights_df' which is usually the Target Weights for the *entire* period?
    # No, usually in backtest loop, we simulate window by window.
    # But here we want to run a full backtest over the aggregated weights?

    # Wait, the simulators in `backtest_simulators.py` simulate a *single window* given `weights_df` (target) and `returns` (future).
    # To validate parity, we should validate *one window* at a time, or chain them.
    # The `BacktestEngine` runs simulation per window.

    # Let's validate the *latest* or a *specific* window to ensure parity logic holds.
    # Simulating the whole chain requires stitching, which `BacktestEngine` does.
    # We want to verify the *Engine Parity* (Step 5 in BacktestEngine).

    return returns_df, weights_df


def validate_window_parity(returns: pd.DataFrame, weights: pd.DataFrame, initial_holdings=None):
    """
    Runs both simulators on the same data and compares results.
    """
    # 1. Run Baseline (ReturnsSimulator)
    logger.info("Running Baseline (ReturnsSimulator)...")

    # Enforce strict daily rebalancing for Parity Check
    with patch("tradingview_scraper.portfolio_engines.backtest_simulators.get_settings") as mock_settings:
        # We must replicate the actual settings structure or values
        # Better: Get actual settings and just override specific fields
        from tradingview_scraper.settings import get_settings as real_get_settings

        real_settings = real_get_settings()

        # Configure the mock to behave like real settings
        mock_settings.return_value = real_settings

        # Override
        # We need to be careful not to mutate the global singleton permanently if get_settings is cached.
        # But for this script, it's fine.
        real_settings.features.feat_rebalance_mode = "daily"
        real_settings.features.feat_rebalance_tolerance = False

        # Ensure friction matches Nautilus (which uses current settings by default, but we should be explicit)
        # Note: Nautilus adapter reads settings from 'settings' argument.

        base_sim = ReturnsSimulator()
        base_res = base_sim.simulate(returns, weights, initial_holdings)

    # 2. Run Challenger (NautilusSimulator)
    # CRITICAL PARITY FIX: ReturnsSimulator assumes instant fill at T0 Open (captures T0 return).
    # Nautilus trades at T0 Close (captures T1 return).
    # To match, we prepend a dummy T-1 bar to Nautilus so it trades at T-1 Close and captures T0 return.

    logger.info("Running Challenger (NautilusSimulator) with Pre-Start Priming...")

    t0 = returns.index[0]
    t_minus_1 = t0 - pd.Timedelta(days=1)

    # Create dummy row (0.0 return)
    dummy_row = pd.DataFrame(0.0, index=pd.Index([t_minus_1]), columns=returns.columns)
    returns_naut = pd.concat([dummy_row, returns])

    naut_sim = NautilusSimulator()
    naut_res = naut_sim.simulate(returns_naut, weights, initial_holdings)

    # 3. Compare Metrics
    base_metrics = base_res.get("metrics", {}) or base_res
    naut_metrics = naut_res.get("metrics", {}) or naut_res

    # Extract Daily Returns series to align and compare properly
    base_series = base_res.get("daily_returns")
    naut_series = naut_res.get("daily_returns")

    if isinstance(naut_series, pd.Series) and isinstance(base_series, pd.Series):
        # Nautilus handles Entry Cost at T-1 (Pre-Start). ReturnsSimulator handles it at T (First Step).
        # We must compound Nautilus T-1 return into T return to match ReturnsSimulator's T0.

        start_t = base_series.index[0]
        if start_t in naut_series.index:
            # Check for preceding index in Nautilus
            # We know we prepended 1 day.
            naut_idx_loc = naut_series.index.get_loc(start_t)
            if naut_idx_loc > 0:
                prev_t = naut_series.index[naut_idx_loc - 1]
                prev_ret = naut_series.loc[prev_t]
                curr_ret = naut_series.loc[start_t]

                # Compound: (1+r1)*(1+r2) - 1
                compounded = (1 + prev_ret) * (1 + curr_ret) - 1
                logger.info(f"Compounding Nautilus Entry Cost: T-1 ({prev_ret:.6f}) + T ({curr_ret:.6f}) -> {compounded:.6f}")

                # Update Nautilus T return
                naut_series.loc[start_t] = compounded

        # Trim Nautilus series to match Baseline index
        # Nautilus will have T-1 (0.0) and T...
        # Baseline has T...
        # We align by index
        common_idx = base_series.index.intersection(naut_series.index)
        naut_series = naut_series.loc[common_idx]
        base_series = base_series.loc[common_idx]

        # Recalculate scalar metrics on aligned series for fair comparison
        from tradingview_scraper.utils.metrics import calculate_performance_metrics

        base_metrics = calculate_performance_metrics(base_series)
        naut_metrics = calculate_performance_metrics(naut_series)

    base_sharpe = base_metrics.get("sharpe", 0.0)
    naut_sharpe = naut_metrics.get("sharpe", 0.0)

    base_ret = base_metrics.get("cagr", 0.0)
    naut_ret = naut_metrics.get("cagr", 0.0)

    logger.info("=== PARITY REPORT ===")

    logger.info(f"Sharpe: Base={base_sharpe:.4f} vs Nautilus={naut_sharpe:.4f} (Diff: {naut_sharpe - base_sharpe:.4f})")
    logger.info(f"CAGR:   Base={base_ret:.4%} vs Nautilus={naut_ret:.4%} (Diff: {naut_ret - base_ret:.4%})")

    return {"base": base_metrics, "nautilus": naut_metrics, "diff_sharpe": naut_sharpe - base_sharpe, "diff_cagr": naut_ret - base_ret}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", help="Run ID to validate", required=True)
    parser.add_argument("--window-idx", type=int, help="Specific window index to validate (default: last)", default=-1)
    parser.add_argument("--base-dir", help="Artifacts directory", default="artifacts/summaries/runs")
    args = parser.parse_args()

    logger.info(f"Starting Nautilus Parity Validation for Run {args.run_id}...")

    try:
        full_returns, full_weights = load_run_data(args.run_id, Path(args.base_dir))

        # Select Window
        unique_timestamps = sorted(full_weights["Timestamp"].unique())
        if not unique_timestamps:
            raise ValueError("No timestamps found in weights.")

        target_ts = unique_timestamps[args.window_idx]
        logger.info(f"Validating Window starting at {target_ts}")

        # Filter for specific profile if duplicates exist
        weights_at_ts = full_weights[full_weights["Timestamp"] == target_ts]
        if "Profile" in weights_at_ts.columns:
            profiles = weights_at_ts["Profile"].unique()
            if len(profiles) > 1:
                logger.warning(f"Multiple profiles found: {profiles}. Selecting first one: {profiles[0]}")
                window_weights = weights_at_ts[weights_at_ts["Profile"] == profiles[0]]
            else:
                window_weights = weights_at_ts
        else:
            window_weights = weights_at_ts

        # Check for duplicates
        if window_weights.duplicated(subset=["Symbol"]).any():
            logger.warning("Duplicate symbols found in weights! Inspecting...")
            logger.warning(window_weights[window_weights.duplicated(subset=["Symbol"], keep=False)].to_string())
            # Dedup by taking the last one? or raising error?
            # For validation, let's dedup keeping last
            logger.warning("Deduplicating weights (keeping last)...")
            window_weights = window_weights.drop_duplicates(subset=["Symbol"], keep="last")

        # Slice Returns for this window (e.g., next 20 days)
        # We need to know the test_window size. Assume 20 for production.
        # Or look at the run config.
        # For parity check, exact length matches what `BacktestEngine` does.
        # `BacktestEngine`: test_rets = returns.iloc[i : i + test_window]
        # We map `target_ts` to index location in full_returns

        loc = full_returns.index.get_loc(target_ts)
        test_window = 20  # Standard

        window_returns = full_returns.iloc[loc : loc + test_window]

        # Sanitize Return Columns (Run contains synthesized returns)
        # We map them back to physical for the simulation check
        new_cols = []
        for c in window_returns.columns:
            new_cols.append(extract_physical_symbol(str(c)))
        window_returns.columns = new_cols

        # Filter returns to match weights (and vice versa)
        common_syms = list(set(window_returns.columns) & set(window_weights["Symbol"]))
        if not common_syms:
            raise ValueError("No common symbols between returns and weights after sanitization.")

        window_weights = window_weights[window_weights["Symbol"].isin(common_syms)]
        window_returns = window_returns[common_syms]

        # Robustness: Fill NaNs in returns to avoid Nautilus crash
        window_returns = window_returns.fillna(0.0)

        logger.info(f"Window Returns Shape: {window_returns.shape}")
        logger.info(f"Window Weights Count: {len(window_weights)}")

        # Execute Validation
        results = validate_window_parity(window_returns, window_weights)

        # Output Results
        if abs(results["diff_sharpe"]) > 0.1 or abs(results["diff_cagr"]) > 0.015:
            logger.error("❌ PARITY CHECK FAILED: Divergence exceeds tolerance.")
            sys.exit(1)
        else:
            logger.info("✅ PARITY CHECK PASSED")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)
