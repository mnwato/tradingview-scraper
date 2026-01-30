import json
import logging
import os
from typing import Any, Dict, List

from scripts.backtest_engine import BacktestEngine
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("4d_tournament")


def run_4d_tournament():
    settings = get_settings()

    # Grand Matrix Axis - Selection
    selection_configs: List[Dict[str, Any]] = [
        {"name": "v3.1", "mode": "v3.1", "vetoes": False, "efficiency": False},
        {"name": "v3.1_spectral", "mode": "v3.1", "vetoes": True, "efficiency": True},
        {"name": "v3.2", "mode": "v3.2", "vetoes": True, "efficiency": True},
        {"name": "v3.2_streamlined", "mode": "v3.2", "vetoes": False, "efficiency": True},
    ]

    # Rebalance Axis (New for Window Rebalance Audit)
    rebalance_configs: List[Dict[str, Any]] = [
        {"name": "window", "mode": "window", "tolerance": False, "drift": 0.0},
        {"name": "daily", "mode": "daily", "tolerance": False, "drift": 0.0},
        {"name": "daily_5pct", "mode": "daily", "tolerance": True, "drift": 0.05},
    ]

    engines = ["skfolio", "cvxportfolio", "custom"]
    profiles = ["risk_parity", "hrp", "max_sharpe", "benchmark", "equal_weight", "raw_pool_ew", "benchmark_baseline", "market_baseline"]
    simulators = ["cvxportfolio", "nautilus", "custom"]

    # Audited Execution Parameters
    train_window = 126
    test_window = 21
    step_size = 21
    start_date = "2025-01-01"
    end_date = "2025-12-31"

    all_results = {}

    # Save original state to restore later
    orig_mode = settings.features.selection_mode
    orig_vetoes = settings.features.feat_predictability_vetoes
    orig_eff = settings.features.feat_efficiency_scoring
    orig_reb_mode = settings.features.feat_rebalance_mode
    orig_reb_tol = settings.features.feat_rebalance_tolerance
    orig_drift = settings.features.rebalance_drift_limit

    try:
        run_dir = settings.prepare_summaries_run_dir()
        log_dir = run_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "rebalance_audit.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(file_handler)
        logger.info("Logging rebalance audit to %s", log_path)

        for r_cfg in rebalance_configs:
            reb_name = r_cfg["name"]
            all_results[reb_name] = {}

            # Apply Rebalance Config to Settings
            settings.features.feat_rebalance_mode = r_cfg["mode"]
            settings.features.feat_rebalance_tolerance = r_cfg["tolerance"]
            settings.features.rebalance_drift_limit = r_cfg["drift"]

            # Export to ENV
            os.environ["TV_FEATURES_FEAT_REBALANCE_MODE"] = r_cfg["mode"]
            os.environ["TV_FEATURES_FEAT_REBALANCE_TOLERANCE"] = "1" if r_cfg["tolerance"] else "0"
            os.environ["TV_FEATURES_REBALANCE_DRIFT_LIMIT"] = str(r_cfg["drift"])

            for s_cfg in selection_configs:
                sel_name = s_cfg["name"]
                logger.info(f"\n🚀 REBALANCE AUDIT: Mode={reb_name} | Selection={sel_name}")

                # Apply Selection Config to Settings
                settings.features.selection_mode = s_cfg["mode"]
                settings.features.feat_predictability_vetoes = s_cfg["vetoes"]
                settings.features.feat_efficiency_scoring = s_cfg["efficiency"]

                # Export to ENV
                os.environ["TV_FEATURES_SELECTION_MODE"] = s_cfg["mode"]
                os.environ["TV_FEATURES_FEAT_PREDICTABILITY_VETOES"] = "1" if s_cfg["vetoes"] else "0"
                os.environ["TV_FEATURES_FEAT_EFFICIENCY_SCORING"] = "1" if s_cfg["efficiency"] else "0"

                bt = BacktestEngine()
                res = bt.run_tournament(
                    train_window=train_window, test_window=test_window, step_size=step_size, engines=engines, profiles=profiles, simulators=simulators, start_date=start_date, end_date=end_date
                )

                all_results[reb_name][sel_name] = res["results"]

        final_output = {
            "rebalance_audit_results": all_results,
            "meta": {
                "period": f"{start_date} to {end_date}",
                "dimensions": ["rebalance_mode", "selection_mode", "simulator", "engine", "profile"],
                "protocol": "Continuous Walk-Forward (100% Coverage)",
                "train_test_step": [train_window, test_window, step_size],
            },
        }

        output_path = run_dir / "rebalance_audit_results.json"
        with open(output_path, "w") as f:
            json.dump(final_output, f, indent=2)

        # Promote to latest
        settings.promote_summaries_latest()
        logger.info(f"✅ Rebalance Audit Tournament finalized: {output_path}")

    finally:
        # Restore settings
        settings.features.selection_mode = orig_mode
        settings.features.feat_predictability_vetoes = orig_vetoes
        settings.features.feat_efficiency_scoring = orig_eff
        settings.features.feat_rebalance_mode = orig_reb_mode
        settings.features.feat_rebalance_tolerance = orig_reb_tol
        settings.features.rebalance_drift_limit = orig_drift


if __name__ == "__main__":
    run_4d_tournament()
