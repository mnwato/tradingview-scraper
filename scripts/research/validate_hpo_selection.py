import json
import logging
import os
from typing import Any, Dict, List

from scripts.backtest_engine import BacktestEngine
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("hpo_validation")


def validate_hpo():
    settings = get_settings()

    # Tournament Axis - Selection
    # v3.1: Multiplicative, baseline
    # v3.2: Log-MPS, optimized weights
    selection_configs: List[Dict[str, Any]] = [
        {"name": "v3.1", "mode": "v3.1", "logmps": False},
        {"name": "v3.2", "mode": "v3.2", "logmps": True},
    ]

    # Use window rebalancing as standard
    settings.features.feat_rebalance_mode = "window"

    engines = ["custom"]  # Use custom engine for speed and stability
    profiles = ["equal_weight", "raw_pool_ew"]  # Focused on selection alpha
    simulators = ["custom"]

    # Full 2025 Matrix
    train_window = 126
    test_window = 21
    step_size = 21
    start_date = "2025-01-01"
    end_date = "2025-12-31"

    all_results = {}

    orig_mode = settings.features.selection_mode
    orig_logmps = settings.features.feat_selection_logmps

    try:
        run_dir = settings.prepare_summaries_run_dir()

        for s_cfg in selection_configs:
            sel_name = s_cfg["name"]
            logger.info(f"\n🚀 HPO VALIDATION: Selection={sel_name}")

            # Apply Selection Config
            settings.features.selection_mode = s_cfg["mode"]
            settings.features.feat_selection_logmps = s_cfg["logmps"]

            if s_cfg["logmps"]:
                settings.top_n = settings.features.top_n_global
                logger.info(f"Setting breadth top_n to {settings.top_n} (Global Robust)")
            else:
                settings.top_n = 3  # Reset to baseline

            # Export to ENV
            os.environ["TV_FEATURES_SELECTION_MODE"] = s_cfg["mode"]
            os.environ["TV_FEATURES_FEAT_SELECTION_LOGMPS"] = "1" if s_cfg["logmps"] else "0"

            bt = BacktestEngine()
            res = bt.run_tournament(
                train_window=train_window, test_window=test_window, step_size=step_size, engines=engines, profiles=profiles, simulators=simulators, start_date=start_date, end_date=end_date
            )

            all_results[sel_name] = res["results"]

        final_output = {
            "hpo_validation_results": all_results,
            "meta": {
                "period": f"{start_date} to {end_date}",
                "protocol": "HPO Validation (v3.1 vs v3.2)",
            },
        }

        output_path = run_dir / "hpo_validation_results.json"
        with open(output_path, "w") as f:
            json.dump(final_output, f, indent=2)

        settings.promote_summaries_latest()
        logger.info(f"✅ HPO Validation finalized: {output_path}")

    finally:
        settings.features.selection_mode = orig_mode
        settings.features.feat_selection_logmps = orig_logmps


if __name__ == "__main__":
    validate_hpo()
