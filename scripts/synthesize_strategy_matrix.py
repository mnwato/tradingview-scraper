import json
import logging
import os

import pandas as pd

from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.audit import AuditLedger, get_df_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("strategy_synthesis")


def synthesize_strategy_matrix():
    """
    Step 8.5: Strategy Synthesis
    Expands the Physical Returns Matrix (returns_matrix.parquet) into a
    Synthetic Strategy Matrix (synthetic_returns.parquet) based on logic definitions
    in portfolio_candidates.json.

    This effectively re-couples Logic to Data just-in-time for Optimization.
    """
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()
    ledger = AuditLedger(run_dir) if settings.features.feat_audit_ledger else None

    # 1. Load Physical Returns
    # CR-831: Workspace Isolation
    returns_path = os.getenv("PORTFOLIO_RETURNS_PATH") or str(run_dir / "data" / "returns_matrix.parquet")
    if not os.path.exists(returns_path):
        # Fallback
        returns_path = "data/lakehouse/portfolio_returns.pkl"

    if not os.path.exists(returns_path):
        logger.error(f"Physical returns matrix not found at {returns_path}")
        return

    logger.info(f"Loading physical returns from {returns_path}")
    if str(returns_path).endswith(".parquet"):
        phys_df = pd.read_parquet(returns_path)
    else:
        phys_df = pd.read_pickle(returns_path)

    # 2. Load Candidates (Logic Definitions)
    candidates_path = os.getenv("CANDIDATES_SELECTED") or str(run_dir / "data" / "portfolio_candidates.json")
    if not os.path.exists(candidates_path):
        # Fallback to raw if selection hasn't run or overwritten
        candidates_path = os.getenv("CANDIDATES_RAW") or str(run_dir / "data" / "portfolio_candidates_raw.json")

    if not os.path.exists(candidates_path):
        logger.error(f"Candidates file not found at {candidates_path}")
        return

    logger.info(f"Loading candidates from {candidates_path}")
    with open(candidates_path, "r") as f:
        candidates = json.load(f)

    # 3. Synthesize
    syn_data = {}
    syn_meta = {}

    for cand in candidates:
        # Resolve keys
        phys_sym = cand.get("physical_symbol") or cand.get("symbol")

        # If symbol was physical in select_top_universe, we need to reconstruct atom_id or use provided one
        atom_id = cand.get("atom_id")
        if not atom_id:
            # Reconstruct if missing (Legacy support)
            logic = cand.get("logic", "trend")
            direction = cand.get("direction", "LONG")
            atom_id = f"{phys_sym}_{logic}_{direction}"

        logic = cand.get("logic", "trend")
        direction = cand.get("direction", "LONG")

        if phys_sym not in phys_df.columns:
            logger.warning(f"Physical symbol {phys_sym} for atom {atom_id} not found in returns matrix. Skipping.")
            continue

        raw_series = phys_df[phys_sym]

        # Apply Logic (Inversion)
        if direction == "SHORT":
            # Synthetic Long: Invert returns
            syn_series = -1.0 * raw_series
            # CR-187: Bankruptcy Guard for Synthetic Shorts
            # Cap negative returns at -1.0 (Liquidation) to prevent mathematical explosions
            syn_series = syn_series.clip(lower=-1.0)
        else:
            syn_series = raw_series

        syn_data[atom_id] = syn_series
        syn_meta[atom_id] = cand

    if not syn_data:
        logger.error("No synthetic streams generated.")
        return

    # 4. Create DataFrame
    syn_df = pd.DataFrame(syn_data, index=phys_df.index)

    # 5. Persist
    output_path = os.getenv("SYNTHETIC_RETURNS_PATH") or str(run_dir / "data" / "synthetic_returns.parquet")
    syn_df.to_parquet(output_path)
    logger.info(f"Wrote synthetic matrix ({syn_df.shape}) to {output_path}")

    # Persist Meta map? (Optional, existing meta might be enough)

    if ledger:
        ledger.record_outcome(step="synthesis", status="success", output_hashes={"synthetic_matrix": get_df_hash(syn_df)}, metrics={"shape": syn_df.shape, "n_atoms": len(syn_df.columns)})


if __name__ == "__main__":
    synthesize_strategy_matrix()
