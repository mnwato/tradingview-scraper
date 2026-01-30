import argparse
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, cast

import pandas as pd

from tradingview_scraper.portfolio_engines import build_engine
from tradingview_scraper.portfolio_engines.base import EngineRequest
from tradingview_scraper.regime import MarketRegimeDetector
from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.audit import get_df_hash

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("generate_orders_v3")


def generate_production_orders(source_run_id: str = "20260106-prod-q1", top_n: int = 1):
    settings = get_settings()

    # 1. Load Tournament Results to find the Winners
    candidates_path = settings.summaries_runs_dir / source_run_id / "data" / "tournament_candidates.csv"
    if not os.path.exists(candidates_path):
        logger.error(f"Source run candidates not found: {candidates_path}")
        return

    candidates_df = pd.read_csv(candidates_path)
    if candidates_df.empty:
        logger.error(f"Source run has no candidates: {source_run_id}")
        return

    # Deduplicate by (engine, profile) to ensure unique strategies
    unique_winners = candidates_df.drop_duplicates(subset=["engine", "profile"]).head(top_n)
    n_winners = len(unique_winners)
    logger.info(f"🏆 Identified {n_winners} unique winners from {source_run_id}")

    # 2. Load Live Data
    returns_path = settings.lakehouse_dir / "portfolio_returns.pkl"
    clusters_path = settings.lakehouse_dir / "portfolio_clusters.json"
    meta_path = settings.lakehouse_dir / "portfolio_meta.json"
    stats_path = settings.lakehouse_dir / "antifragility_stats.json"

    with open(returns_path, "rb") as f:
        returns = cast(pd.DataFrame, pd.read_pickle(f))
    with open(clusters_path, "r") as f:
        clusters = cast(Dict[str, List[str]], json.load(f))
    with open(meta_path, "r") as f:
        meta = cast(Dict[str, Any], json.load(f))

    stats = None
    if os.path.exists(stats_path):
        stats = pd.read_json(stats_path)

    # 3. Detect Regime
    detector = MarketRegimeDetector()
    regime, score, quadrant = detector.detect_regime(returns)
    logger.info(f"Current Market Regime: {regime} (Score: {score:.2f}) | Quadrant: {quadrant}")

    all_orders = []
    ts_str = datetime.now().strftime("%Y%m%d")
    # CR-831: Output to Artifacts Orders, not Lakehouse directly
    # Ideally orders should be in data/artifacts/orders/ for pickup
    output_dir = settings.artifacts_dir / "orders"
    os.makedirs(output_dir, exist_ok=True)

    # 4. Iterate through unique winners and generate orders
    for i, (_, winner) in enumerate(unique_winners.iterrows()):
        rank = i + 1
        selection_mode = str(winner.get("selection", "v3.2"))
        engine_name = str(winner.get("engine", "riskfolio"))
        profile_name = str(winner.get("profile", "barbell"))

        logger.info(f"[{rank}/{n_winners}] Generating orders for: {engine_name}/{profile_name}")

        # Instantiate Engine
        try:
            engine = build_engine(engine_name)
        except Exception as e:
            logger.error(f"Failed to build engine {engine_name}: {e}")
            continue

        # Generate Orders
        request = EngineRequest(
            profile=cast(Any, profile_name),
            cluster_cap=0.25,
            regime=regime,
            market_environment=quadrant,
        )

        response = engine.optimize(returns=returns, clusters=clusters, meta=meta, stats=stats, request=request)

        weights_df = response.weights
        if weights_df.empty:
            logger.warning(f"Optimization failed for {engine_name}/{profile_name}")
            continue

        # Add Provenance Metadata
        weights_df["Rank"] = rank
        weights_df["Regime"] = regime
        weights_df["Regime_Score"] = score
        weights_df["Generated_At"] = datetime.now().isoformat()
        weights_df["Engine"] = engine_name
        weights_df["Profile"] = profile_name
        weights_df["Source_Run"] = source_run_id

        # Persist Rank-Specific CSV
        output_path = os.path.join(output_dir, f"target_weights_rank{rank}_{engine_name}_{profile_name}_{ts_str}.csv")
        weights_df.to_csv(output_path, index=False)
        logger.info(f"✅ Rank {rank} Orders Generated: {output_path}")

        all_orders.append(
            {
                "rank": rank,
                "profile": profile_name,
                "engine": engine_name,
                "regime": {"name": regime, "score": float(score)},
                "assets": weights_df.to_dict(orient="records"),
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "source_run_id": source_run_id,
                    "selection_mode": selection_mode,
                    "source_returns_hash": get_df_hash(returns),
                    "cluster_cap": 0.25,
                },
            }
        )

    # 5. Persist Unified JSON State
    # This is the "Current Production State", so lakehouse IS appropriate here?
    # Or should it be in artifacts/latest?
    # Let's keep it in lakehouse as it represents the "Live" state for execution engines to read.
    # But let's verify if execution reads from lakehouse or artifacts.
    # Nautilus reads from... config.
    # Let's move it to artifacts/orders/latest_portfolio.json to be safe and symlink if needed.

    latest_path = settings.artifacts_dir / "orders" / "portfolio_optimized_v3.json"
    with open(latest_path, "w") as f:
        json.dump({"winners": all_orders}, f, indent=2)
    logger.info(f"✅ Optimized State (V3) Persisted: {latest_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auditable production order generator (Multi-Winner)")
    parser.add_argument("--source-run-id", type=str, default="20260106-prod-q1", help="Run ID to pull the winner from")
    parser.add_argument("--top-n", type=int, default=3, help="Number of unique strategies to generate orders for")
    args = parser.parse_args()

    generate_production_orders(source_run_id=args.source_run_id, top_n=args.top_n)
