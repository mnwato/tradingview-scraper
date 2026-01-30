import logging
from typing import Any, Dict, cast

import numpy as np
import pandas as pd

from scripts.backtest_engine import BacktestEngine
from scripts.natural_selection import run_selection
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("tournament_normalization")


def run_tournament():
    settings = get_settings()
    bt = BacktestEngine()

    # 1. Configuration Archetypes
    architectures: Dict[str, Dict[str, Any]] = {
        "v3.1_multiplicative": {"mode": "v3.1"},
        "v2.1_baseline_rank": {
            "mode": "v2.1",
            "weights": {
                "momentum": 0.9070,
                "stability": 0.0723,
                "liquidity": 0.0534,
                "antifragility": 0.2429,
                "survival": 0.8690,
                "efficiency": 0.2946,
                "entropy": 0.3911,
                "hurst_clean": 0.0208,
            },
            "methods": {f: "rank" for f in ["momentum", "stability", "liquidity", "antifragility", "survival", "efficiency", "entropy", "hurst_clean"]},
        },
        "v2.1_optimized_multi_norm": {
            "mode": "v2.1",
            "weights": settings.features.weights_v2_1_global,
            "methods": settings.features.normalization_methods_v2_1,
            "sigma": settings.features.clipping_sigma_v2_1,
        },
    }
    results = []

    # Tournament Loop
    for name, config in architectures.items():
        logger.info(f"\n🏆 Evaluating Architecture: {name}")

        # Override settings

        settings.features.selection_mode = cast(str, config["mode"])
        if "weights" in config:
            settings.features.weights_v2_1_global = cast(Dict[str, float], config["weights"])
        if "methods" in config:
            settings.features.normalization_methods_v2_1 = cast(Dict[str, str], config["methods"])
        if "sigma" in config:
            settings.features.clipping_sigma_v2_1 = cast(float, config["sigma"])

        # Run Backtest (Simplified for Selection Alpha)
        train_window = 126
        test_window = 21
        step_size = 21

        returns = bt.returns
        window_alphas = []

        for start_idx in range(0, len(returns) - train_window - test_window + 1, step_size):
            train_data = returns.iloc[start_idx : start_idx + train_window]
            test_data = returns.iloc[start_idx + train_window : start_idx + train_window + test_window]

            response = run_selection(train_data, bt.raw_candidates, stats_df=bt._audit_training_stats(train_data), top_n=5)

            if not response.winners:
                continue

            selected_symbols = [w["symbol"] for w in response.winners]
            sel_returns = test_data[selected_symbols].mean(axis=1)
            pool_returns = test_data.mean(axis=1)

            # Selection Alpha: Selected - Pool
            alpha = (1 + sel_returns).prod() - (1 + pool_returns).prod()
            window_alphas.append(alpha)

        mean_alpha = np.mean(window_alphas)
        std_alpha = np.std(window_alphas)
        sharpe_alpha = mean_alpha / std_alpha if std_alpha != 0 else 0

        results.append({"architecture": name, "mean_alpha": mean_alpha, "std_alpha": std_alpha, "risk_adj_alpha": sharpe_alpha, "total_alpha": np.sum(window_alphas)})

    df_results = pd.DataFrame(results)
    print("\n🏁 Final Tournament Results (Selection Alpha):")
    print(df_results.to_string())

    champion = df_results.loc[df_results["risk_adj_alpha"].idxmax(), "architecture"]
    print(f"\n🥇 Champion: {champion}")


if __name__ == "__main__":
    run_tournament()
