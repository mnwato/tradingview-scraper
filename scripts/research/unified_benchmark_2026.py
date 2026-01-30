import json
import logging
import os
from typing import Any, Dict, List

from scripts.backtest_engine import BacktestEngine
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("unified_benchmark")


def run_unified_benchmark():
    settings = get_settings()

    # Unified Axis - All major 2026 Selection Architectures
    selection_configs: List[Dict[str, Any]] = [
        {"name": "v2.0", "mode": "v2.0", "logmps": False},
        {"name": "v2.1", "mode": "v2.1", "logmps": False},
        {"name": "v3.1", "mode": "v3.1", "logmps": False},
        {"name": "v3.2", "mode": "v3.2", "logmps": True},
    ]

    # Standard rebalancing
    settings.features.feat_rebalance_mode = "window"

    engines = ["custom"]
    profiles = ["equal_weight", "hrp", "benchmark"]
    simulators = ["custom"]

    # Full 2025 Matrix (Starting training in 2024 to cover 12 months of testing)
    train_window = 126
    test_window = 21
    step_size = 21
    start_date = "2024-08-19"  # Data start
    end_date = "2025-12-31"

    all_results = {}

    orig_mode = settings.features.selection_mode
    orig_logmps = settings.features.feat_selection_logmps
    orig_top_n = settings.top_n

    try:
        run_dir = settings.prepare_summaries_run_dir()

        for s_cfg in selection_configs:
            sel_name = s_cfg["name"]
            logger.info(f"\n🚀 UNIFIED BENCHMARK: Selection={sel_name}")

            # Apply Selection Config
            settings.features.selection_mode = s_cfg["mode"]
            settings.features.feat_selection_logmps = s_cfg["logmps"]

            # Respect architectural breadth standards
            if sel_name == "v3.2":
                settings.top_n = settings.features.top_n_global
            elif sel_name == "v2.1":
                settings.top_n = settings.features.top_n_v2_1
            elif sel_name == "v2.0":
                settings.top_n = 2  # Original V2 standard
            else:
                settings.top_n = 3  # V3.1 Baseline standard

            # Export to ENV for subprocess consistency if needed
            os.environ["TV_FEATURES_SELECTION_MODE"] = s_cfg["mode"]
            os.environ["TV_FEATURES_FEAT_SELECTION_LOGMPS"] = "1" if s_cfg["logmps"] else "0"

            bt = BacktestEngine()
            res = bt.run_tournament(
                train_window=train_window, test_window=test_window, step_size=step_size, engines=engines, profiles=profiles, simulators=simulators, start_date=start_date, end_date=end_date
            )

            all_results[sel_name] = res["results"]

        final_output = {
            "unified_benchmark_results": all_results,
            "meta": {
                "period": f"{start_date} to {end_date}",
                "protocol": "Unified Benchmark (v2.0 vs v2.1 vs v3.1 vs v3.2)",
            },
        }

        output_path = run_dir / "unified_benchmark_results.json"
        with open(output_path, "w") as f:
            json.dump(final_output, f, indent=2)

        settings.promote_summaries_latest()
        logger.info(f"✅ Unified Benchmark finalized: {output_path}")

        # Print summary table
        for profile in profiles:
            print(f"\n🏁 Unified Benchmark Results (Profile: {profile}):")
            print(f"{'Mode':<10} | {'Return':<10} | {'Sharpe':<10} | {'DD':<10} | {'Turnover':<10}")
            print("-" * 60)
            for name in all_results:
                try:
                    summ = all_results[name]["custom"]["custom"][profile]["summary"]
                    print(f"{name:<10} | {summ['annualized_return']:>10.2%} | {summ['sharpe']:>10.2f} | {summ['max_drawdown']:>10.2%} | {summ['avg_turnover']:>10.2f}")
                except KeyError:
                    print(f"{name:<10} | N/A")

    finally:
        # Restore settings
        settings.features.selection_mode = orig_mode
        settings.features.feat_selection_logmps = orig_logmps
        settings.top_n = orig_top_n


if __name__ == "__main__":
    run_unified_benchmark()
