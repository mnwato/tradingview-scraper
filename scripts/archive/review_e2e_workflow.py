import logging
from typing import Dict, List

import pandas as pd

from tradingview_scraper.futures_universe_selector import FuturesUniverseSelector, load_config
from tradingview_scraper.symbols.stream.metadata import MetadataCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("e2e_orchestrator")


class QuantitativePipeline:
    """
    Unified orchestrator for the full end-to-end quantitative workflow.
    Discovery -> Alpha -> Risk -> Catalog
    """

    def __init__(self, lakehouse_path: str = "data/lakehouse"):
        self.lakehouse_path = lakehouse_path
        self.catalog = MetadataCatalog(base_path=lakehouse_path)

    def run_discovery(self, config_paths: List[str], limit: int = 100) -> List[Dict]:
        """Stage 1 & 2: Discover high-liquidity symbols and apply strategy filters."""
        all_signals = []

        for path in config_paths:
            logger.info(f"Running discovery for config: {path}")
            try:
                cfg = load_config(path)
                cfg.limit = limit
                selector = FuturesUniverseSelector(cfg)
                resp = selector.run()

                if resp.get("status") in ["success", "partial_success"]:
                    signals = resp.get("data", [])
                    # Tag with direction from config
                    direction = "LONG" if "short" not in path.lower() else "SHORT"
                    for s in signals:
                        s["direction"] = direction
                    all_signals.extend(signals)
                    logger.info(f"  Generated {len(signals)} signals.")
            except Exception as e:
                logger.error(f"  Discovery failed for {path}: {e}")

        return all_signals

    def run_pipeline(self, config_paths: List[str]):
        """Executes the full E2E flow."""
        print("\n" + "=" * 80)
        print("E2E QUANTITATIVE PIPELINE EXECUTION")
        print("=" * 80)

        # 1. Discovery & Alpha
        signals = self.run_discovery(config_paths)
        if not signals:
            logger.error("No signals generated. Aborting.")
            return

        # 2. Portfolio Prep (Mocking the data prep logic for this review)
        logger.info(f"Preparing portfolio for {len(signals)} candidates...")
        # In a real run, this would trigger scripts/prepare_portfolio_data.py

        # 3. Suggestions for Improvements
        print("\n" + "=" * 80)
        print("E2E WORKFLOW REVIEW & SUGGESTIONS")
        print("=" * 80)

        suggestions = [
            {"Stage": "Discovery", "Review": "Currently relies on sequential REST calls to TradingView.", "Suggestion": "Implement an async scanner client to parallelize multi-exchange scans."},
            {
                "Stage": "Orchestration",
                "Review": "Shell scripts are used for batching.",
                "Suggestion": "Transition to a Python-based DAG (e.g., using 'prefect') for better error recovery and logging.",
            },
            {
                "Stage": "Risk (MPT)",
                "Review": "Standard SLSQP optimizer used for all regimes.",
                "Suggestion": "Add a 'Regime Switch' logic that swaps between Min-Var (Defensive) and Max-Diversification (Offensive) based on VIX or Crypto-Vol.",
            },
            {"Stage": "Data", "Review": "180-day window is fixed.", "Suggestion": "Implement dynamic look-back periods based on asset class (e.g., shorter for high-vol perps)."},
        ]

        print(pd.DataFrame(suggestions).to_string(index=False))


if __name__ == "__main__":
    orchestrator = QuantitativePipeline()
    # Sample configs for review
    configs = ["configs/crypto_cex_trend_binance_spot_daily_long.yaml", "configs/crypto_cex_trend_binance_perp_daily_short.yaml"]
    orchestrator.run_pipeline(configs)
