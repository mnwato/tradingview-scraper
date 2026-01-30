import json
import logging
import math
import os
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timedelta
from typing import Any, cast

import pandas as pd

from tradingview_scraper.settings import get_settings
from tradingview_scraper.symbols.stream.metadata import DataProfile, get_symbol_profile
from tradingview_scraper.symbols.stream.persistent_loader import PersistentDataLoader
from tradingview_scraper.utils.audit import AuditLedger, get_df_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("portfolio_data_prep")


def get_data_source() -> str:
    """Returns the effective data source mode from environment."""
    return os.getenv("PORTFOLIO_DATA_SOURCE", "lakehouse_only")


def prepare_portfolio_universe():
    """
    Preparation Stage (Pillar 0).
    Orchestrates high-integrity ingestion and transformation using the Workflow Engine.
    """
    active_settings = get_settings()
    run_dir = active_settings.prepare_summaries_run_dir()
    ledger = AuditLedger(run_dir) if active_settings.features.feat_audit_ledger else None

    # 1. Load sanctioned candidates
    default_c_sel = str(run_dir / "data" / "portfolio_candidates.json")
    default_c_raw = str(run_dir / "data" / "portfolio_candidates_raw.json")

    preselected_file = os.getenv("CANDIDATES_FILE") or os.getenv("CANDIDATES_SELECTED")
    if not preselected_file or not os.path.exists(preselected_file):
        # CR-FIX: Strict Isolation (Phase 234)
        strict_iso = os.getenv("TV_STRICT_ISOLATION") == "1"

        preselected_file = str(active_settings.lakehouse_dir / "portfolio_candidates.json")
        if not os.path.exists(preselected_file):
            preselected_file = str(active_settings.lakehouse_dir / "portfolio_candidates_raw.json")

        if strict_iso:
            logger.error("[STRICT ISOLATION] Candidate manifest missing in RUN_DIR. Fallback to Lakehouse (%s) denied.", active_settings.lakehouse_dir)
            preselected_file = ""

    if not preselected_file or not os.path.exists(preselected_file):
        logger.error(f"No candidate manifest found at {preselected_file}")
        return

    logger.info(f"Loading candidates from {preselected_file}")
    with open(preselected_file, "r") as f:
        universe = json.load(f)

    if not universe:
        logger.error("No candidates found in manifest.")
        return

    lookback_env = os.getenv("PORTFOLIO_LOOKBACK_DAYS")
    lookback_days = int(lookback_env) if lookback_env else int(active_settings.resolve_portfolio_lookback_days())

    # CR-831: Workspace Isolation - Outputs
    os.makedirs(run_dir / "data", exist_ok=True)
    returns_path = os.getenv("PORTFOLIO_RETURNS_PATH", str(run_dir / "data" / "returns_matrix.parquet"))
    meta_path = os.getenv("PORTFOLIO_META_PATH", str(run_dir / "data" / "portfolio_meta.json"))

    # 2. Extract Canonical Symbols
    physical_map = {}
    for candidate in universe:
        atom_id = candidate["symbol"]
        phys_sym = candidate.get("physical_symbol", atom_id)
        physical_map.setdefault(phys_sym, []).append(candidate)

    logger.info(f"Portfolio Universe: {len(universe)} atoms across {len(physical_map)} physical assets.")

    # 3. Fetch/Load Data
    # Phase 372: Alpha Read-Only Enforcement
    source_mode = get_data_source()

    if source_mode != "lakehouse_only":
        raise RuntimeError(
            "Alpha/Prep is read-only by default. Network ingestion must run in DataOps. Run `make flow-data` (or `make data-ingest`) first, then re-run with PORTFOLIO_DATA_SOURCE=lakehouse_only."
        )

    # 4. Alignment Phase (Disk -> Memory)
    price_data = {}
    alpha_meta = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    batch_size = int(os.getenv("PORTFOLIO_BATCH_SIZE", active_settings.portfolio_batch_size))

    # Define worker function for loading (and optional fetch if not lakehouse_only)
    def process_symbol(phys_sym):
        try:
            # We use a new loader instance per thread/task
            # Note: websocket_jwt_token logic removed for simplicity in this consolidation unless needed
            local_loader = PersistentDataLoader(lakehouse_path=str(active_settings.lakehouse_dir))

            # If not lakehouse_only, we might want to ensure sync here too?
            # But step 3 already did ingest_universe which handles batching.
            # So here we just LOAD.

            df = local_loader.load(phys_sym, start_date, end_date, interval="1d")

            if df.empty:
                if source_mode == "lakehouse_only":
                    logger.warning(f"Missing data for {phys_sym} in Lakehouse.")
                return None

            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s").dt.date
            df_series = df.set_index("timestamp")["close"]
            returns = df_series.pct_change().dropna()

            # Generate Metadata
            meta_entry = None
            candidates_for_phys = physical_map.get(phys_sym, [])
            if candidates_for_phys:
                candidate = candidates_for_phys[0]
                meta_entry = {
                    "symbol": phys_sym,
                    "description": candidate.get("description", "N/A"),
                    "sector": candidate.get("sector", "N/A"),
                    "market": candidate.get("market", "UNKNOWN"),
                    "identity": candidate.get("identity", phys_sym),
                    "adx": candidate.get("adx", 0),
                    "close": candidate.get("close", 0),
                    "atr": candidate.get("atr", 0),
                    "volatility_d": candidate.get("volatility_d", 0),
                    "volume_change_pct": candidate.get("volume_change_pct", 0),
                    "roc": candidate.get("roc", 0),
                    "value_traded": candidate.get("value_traded", 0),
                    "is_benchmark": candidate.get("is_benchmark", False),
                    "direction": candidate.get("direction", "LONG"),
                    "logic": candidate.get("logic", "trend"),
                    "atom_id": candidate.get("atom_id"),
                }

            return phys_sym, returns, meta_entry

        except Exception as e:
            logger.error(f"Error processing {phys_sym}: {e}")
            return None

    # Parallel Execution
    phys_symbols = sorted(list(physical_map.keys()))
    total_batches = math.ceil(len(phys_symbols) / batch_size) if batch_size > 0 else 1

    for batch_idx in range(total_batches):
        batch_syms = phys_symbols[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        logger.info("Loading batch %s/%s (%s physical symbols)", batch_idx + 1, total_batches, len(batch_syms))

        with ThreadPoolExecutor(max_workers=max(1, batch_size)) as executor:
            futures = [executor.submit(process_symbol, s) for s in batch_syms]
            done, _ = wait(futures, timeout=300, return_when=ALL_COMPLETED)

            for fut in done:
                try:
                    res = fut.result()
                    if res:
                        sym, rets, meta = res
                        price_data[sym] = rets
                        alpha_meta[sym] = meta
                except Exception as e:
                    logger.error(f"Batch worker error: {e}")

    # 5. Matrix Creation
    if not price_data:
        logger.error("No price data loaded. Aborting matrix creation.")
        return

    all_dates_raw = sorted(set().union(*(rets.index for rets in price_data.values())))
    all_dates = pd.to_datetime(all_dates_raw, utc=True)
    returns_df = pd.DataFrame(index=all_dates)

    for atom_id, rets in price_data.items():
        if not isinstance(rets.index, pd.DatetimeIndex):
            rets.index = pd.to_datetime(rets.index)

        # Timezone standardization
        idx_check = cast(Any, rets.index)
        if idx_check.tz is None:
            rets.index = idx_check.tz_localize("UTC")
        else:
            rets.index = idx_check.tz_convert("UTC")

        returns_df[atom_id] = rets

    # 6. Cleaning & Filters (TradFi Weekends, History Floor, Toxic Data, Zero Variance)
    profiles = {symbol: get_symbol_profile(symbol) for symbol in returns_df.columns}
    tradfi_cols = [s for s, p in profiles.items() if p != DataProfile.CRYPTO]
    if tradfi_cols:
        tradfi_all_nan = returns_df[tradfi_cols].isna().all(axis=1)
        returns_df = returns_df.loc[~tradfi_all_nan]

    min_days = int(active_settings.min_days_floor)
    if min_days > 0 and not returns_df.empty:
        counts = returns_df.count()
        short_history = [str(c) for c in returns_df.columns if counts[c] < min_days]
        if short_history:
            returns_df = returns_df.drop(columns=short_history)
            logger.info("Dropped %d symbols due to insufficient secular history (< %d days): %s", len(short_history), min_days, ", ".join(short_history))

    TOXIC_THRESHOLD = 5.0
    if not returns_df.empty:
        max_abs_rets = returns_df.abs().max()
        toxic_assets = [str(c) for c in returns_df.columns if max_abs_rets[c] > TOXIC_THRESHOLD]
        if toxic_assets:
            returns_df = returns_df.drop(columns=toxic_assets)
            logger.warning(f"Dropped {len(toxic_assets)} TOXIC assets: {', '.join(toxic_assets)}")

    if not returns_df.empty:
        # Standardize on Series for diagnostic sanity
        vars_s: pd.Series = cast(pd.Series, returns_df.var(ddof=0))
        zero_vars = [str(c) for c in returns_df.columns if vars_s.get(c, 1.0) == 0.0]
        if zero_vars:
            returns_df = returns_df.drop(columns=zero_vars)
            logger.info("Dropped zero-variance symbols: %s", ", ".join(zero_vars))

    # 7. Deduplication
    dedupe_env = os.getenv("PORTFOLIO_DEDUPE_BASE")
    do_dedupe = dedupe_env == "1" if dedupe_env is not None else bool(active_settings.portfolio_dedupe_base)
    if do_dedupe:
        deduped_cols = []
        seen_idents = set()
        for col in returns_df.columns:
            ident = alpha_meta.get(col, {}).get("identity", col)
            if ident in seen_idents:
                continue
            seen_idents.add(ident)
            deduped_cols.append(col)
        returns_df = returns_df[deduped_cols]

    # 8. Save
    logger.info(f"Returns matrix created: {returns_df.shape}")
    logger.info(f"Writing returns matrix to: {returns_path}")
    if returns_path.endswith(".parquet"):
        returns_df.to_parquet(returns_path)
    else:
        returns_df.to_pickle(returns_path)

    with open(meta_path, "w") as f:
        json.dump(alpha_meta, f, indent=2)

    if ledger:
        ledger.record_outcome(
            step="data_prep",
            status="success",
            output_hashes={"returns_matrix": get_df_hash(returns_df)},
            metrics={"shape": returns_df.shape, "n_symbols": len(returns_df.columns), "returns_path": returns_path, "meta_path": meta_path},
        )

    print("\n" + "=" * 50)
    print("PORTFOLIO UNIVERSE PREPARED")
    print("=" * 50)
    print(f"Matrix Shape : {returns_df.shape}")
    print(f"Symbols      : {', '.join(returns_df.columns)}")


if __name__ == "__main__":
    prepare_portfolio_universe()
