import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import yaml

from tradingview_scraper.risk import AntifragilityAuditor, TailRiskAuditor
from tradingview_scraper.settings import get_settings
from tradingview_scraper.symbols.stream.metadata import DataProfile, get_exchange_calendar, get_symbol_profile
from tradingview_scraper.utils.audit import AuditLedger, get_df_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("antifragility_audit")


def calculate_effective_gaps(symbol: str, returns_series: pd.Series, profile: DataProfile) -> Dict[str, Any]:
    """
    Calculates gaps aware of the exchange calendar using exchange_calendars library.
    """
    total_slots = len(returns_series)
    if total_slots == 0:
        return {"n_bars": 0, "gap_pct": 0.0, "is_healthy": False}

    # Identify literal zeros
    zero_mask = returns_series == 0

    if profile == DataProfile.CRYPTO:
        # Crypto is 24/7
        n_gaps = zero_mask.sum()
        gap_pct = n_gaps / total_slots
    else:
        # TradFi: Use institutional calendar
        cal = get_exchange_calendar(symbol, profile)
        dates = pd.to_datetime(returns_series.index)

        # Determine valid trading sessions in this date range
        try:
            d_idx = pd.DatetimeIndex(dates)
            valid_sessions = cal.sessions_in_range(d_idx[0].normalize(), d_idx[-1].normalize())
            # Convert to date set for fast lookup
            valid_dates = set(valid_sessions.to_series().dt.date)

            # Map returns_series dates to a mask of valid trading days
            is_trading_day = pd.Series(returns_series.index).apply(lambda d: d in valid_dates).values

            # Effective slots are those where the market was actually open
            effective_zeros = zero_mask & is_trading_day
            effective_total_slots = is_trading_day.sum()

            n_gaps = effective_zeros.sum()
            gap_pct = n_gaps / effective_total_slots if effective_total_slots > 0 else 0.0
        except Exception as e:
            logger.warning(f"Calendar error for {symbol}: {e}. Falling back to 5/7 heuristic.")
            # Fallback to simple weekend filter if calendar fails
            is_weekend = (dates.to_series().dt.dayofweek >= 5).values
            effective_zeros = zero_mask & ~is_weekend
            effective_total_slots = (~is_weekend).sum()
            n_gaps = effective_zeros.sum()
            gap_pct = n_gaps / effective_total_slots if effective_total_slots > 0 else 0.0

    n_bars = total_slots - zero_mask.sum()
    is_healthy = gap_pct <= 0.10

    return {"n_bars": n_bars, "gap_pct": gap_pct, "is_healthy": is_healthy, "profile": profile.value}


def calculate_regime_survival(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Checks if assets survived defined historical stress events.
    """
    cal_path = Path("configs/stress_calendar.yaml")
    if not cal_path.exists():
        logger.warning("Stress calendar missing. Defaulting to 100% survival.")
        return pd.DataFrame({"Symbol": returns.columns, "Regime_Survival_Score": 1.0})

    with open(cal_path, "r") as f:
        config = yaml.safe_load(f)

    events = config.get("stress_events", [])
    if not events:
        return pd.DataFrame({"Symbol": returns.columns, "Regime_Survival_Score": 1.0})

    results = []
    for symbol in returns.columns:
        passed = 0
        total_eligible = 0

        for event in events:
            start = pd.to_datetime(event["start"])
            end = pd.to_datetime(event["end"])

            # Check if the asset was even alive (first valid bar before or during event)
            if returns.index[0] > end:
                continue  # Event is before the data start

            total_eligible += 1

            # Extract event window
            mask = (returns.index >= start) & (returns.index <= end)
            window_data = returns.loc[mask, symbol]

            if window_data.empty:
                continue

            # Pass criteria: < 5% missing bars (0.0 returns)
            gap_pct = (window_data == 0).mean()
            if gap_pct < 0.05:
                passed += 1

        score = passed / total_eligible if total_eligible > 0 else 0.5  # Neutral for brand new assets
        results.append(
            {
                "Symbol": symbol,
                "Regime_Survival_Score": score,
                "Events_Tested": total_eligible,
                "Events_Passed": passed,
            }
        )

    return pd.DataFrame(results)


def audit_portfolio_fragility():
    # 1. Load Returns
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    default_returns = str(run_dir / "data" / "returns_matrix.parquet")
    if not os.path.exists(default_returns):
        default_returns = "data/lakehouse/portfolio_returns.pkl"

    default_meta = str(run_dir / "data" / "portfolio_meta.json")
    if not os.path.exists(default_meta):
        default_meta = "data/lakehouse/portfolio_meta.json"

    returns_path = os.getenv("RETURNS_MATRIX", default_returns)
    meta_path = os.getenv("PORTFOLIO_META", default_meta)
    output_path = os.getenv("ANTIFRAGILITY_STATS", str(run_dir / "data" / "antifragility_stats.json"))

    ledger = AuditLedger(run_dir) if settings.features.feat_audit_ledger else None

    if not os.path.exists(returns_path):
        logger.error(f"Returns matrix missing: {returns_path}")
        return

    # Load returns (Parquet or Pickle)
    if returns_path.endswith(".parquet"):
        returns = pd.read_parquet(returns_path)
    else:
        returns = pd.read_pickle(returns_path)

    if not os.path.exists(meta_path):
        logger.error(f"Metadata missing: {meta_path}")
        return

    with open(meta_path, "r") as f:
        meta = json.load(f)

    if ledger:
        ledger.record_intent(
            step="forensic_audit",
            params={"audit_type": "antifragility_tail_risk"},
            input_hashes={"returns_matrix": get_df_hash(returns)},
        )

    # Filter valid columns

    returns = returns.loc[:, (returns != 0).any(axis=0)]

    # --- GATE 1: CALENDAR-AWARE HEALTH CHECK ---
    health_results = {}
    valid_symbols = []

    for symbol in returns.columns:
        # Resolve Profile
        s_meta = meta.get(symbol, {})
        profile = get_symbol_profile(symbol, s_meta)

        health = calculate_effective_gaps(symbol, returns[symbol], profile)
        health_results[symbol] = health

        if health["is_healthy"]:
            valid_symbols.append(symbol)
        else:
            logger.warning(f"Symbol {symbol} ({profile.value}) FAILED Gate 1 (Health): {health['n_bars']} bars, {health['gap_pct']:.1%} effective gaps")

    # --- REGIME SURVIVAL (V3) ---
    settings = get_settings()
    if settings.features.feat_regime_survival:
        survival_df = calculate_regime_survival(returns)
        logger.info("Darwinian Audit: Regime Survival enabled.")
    else:
        survival_df = pd.DataFrame({"Symbol": returns.columns, "Regime_Survival_Score": 1.0, "Events_Tested": 0, "Events_Passed": 0})

    # 2. Audit Antifragility
    auditor = AntifragilityAuditor()
    af_df = auditor.audit(returns)

    # 3. Audit Tail Risk
    tail_auditor = TailRiskAuditor()
    tail_df = tail_auditor.calculate_metrics(returns, confidence_level=0.95)

    # 4. Merge Metrics
    df = pd.merge(af_df, tail_df, on="Symbol")
    df = pd.merge(df, survival_df, on="Symbol")

    # Inject metadata
    df["Direction"] = df["Symbol"].apply(lambda x: meta.get(x, {}).get("direction", "N/A"))
    df["ADX"] = df["Symbol"].apply(lambda x: meta.get(x, {}).get("adx", 0))

    # Inject Health Metrics
    df["Bars"] = df["Symbol"].apply(lambda x: health_results.get(x, {}).get("n_bars", 0))
    df["Gap_Pct"] = df["Symbol"].apply(lambda x: health_results.get(x, {}).get("gap_pct", 0))

    # Fragility Score (V3): Composite of Risk + Survival Failure
    af_max = df["Antifragility_Score"].max()
    af_denom = af_max if af_max != 0 else 1.0
    cvar_max = abs(df["CVaR_95"]).max()
    cvar_denom = cvar_max if cvar_max != 0 else 1.0

    if settings.features.feat_regime_survival:
        df["Fragility_Score"] = (1.0 - (df["Antifragility_Score"] / af_denom)) + (abs(df["CVaR_95"]) / cvar_denom) + ((1.0 - df["Regime_Survival_Score"]) * 2.0) + (df["Gap_Pct"] * 5)
    else:
        df["Fragility_Score"] = (1.0 - (df["Antifragility_Score"] / af_denom)) + (abs(df["CVaR_95"]) / cvar_denom)

    print("\n" + "=" * 100)
    print("PORTFOLIO FRAGILITY & DARWINIAN SURVIVAL AUDIT (V3)")
    print("=" * 100)

    print("\n[Top 10 Institutional-Grade Survivors (Regime Survival >= 0.8)]")
    cols = ["Symbol", "Direction", "Regime_Survival_Score", "Events_Passed", "Antifragility_Score"]
    print(df.sort_values(["Regime_Survival_Score", "Antifragility_Score"], ascending=False).head(10)[cols].to_string(index=False))

    print("\n[Bottom 10 Most Fragile Assets (Composite Fragility Score)]")
    print(df.sort_values("Fragility_Score", ascending=False).head(10)[["Symbol", "Direction", "Fragility_Score", "Regime_Survival_Score", "Skew"]].to_string(index=False))

    # Save for Barbell Optimizer and Reporting
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_json(output_path, orient="records", indent=2)
    print(f"\nSaved comprehensive risk stats to {output_path}")

    if ledger:
        ledger.record_outcome(
            step="forensic_audit",
            status="success",
            output_hashes={"antifragility_stats": get_df_hash(df)},
            metrics={"n_assets": len(df), "avg_fragility": float(df["Fragility_Score"].mean())},
        )


if __name__ == "__main__":
    audit_portfolio_fragility()
