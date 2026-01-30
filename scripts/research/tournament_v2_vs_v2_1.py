import logging
from typing import Any, Dict, cast

import numpy as np
import pandas as pd

from scripts.backtest_engine import BacktestEngine
from scripts.natural_selection import run_selection
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("tournament_v2_vs_v2_1")


def run_tournament():
    settings = get_settings()
    bt = BacktestEngine()

    # 1. Configuration Archetypes
    architectures: Dict[str, Dict[str, Any]] = {
        "v2_baseline": {
            "mode": "v2",
        },
        "v2.1_optimized": {
            "mode": "v2.1",
        },
    }

    results = []

    # Tournament Loop
    for name, config in architectures.items():
        logger.info(f"\n🏆 Evaluating Architecture: {name}")

        # Override settings
        settings.features.selection_mode = cast(str, config["mode"])

        # Run Backtest (Simplified for Selection Alpha)
        train_window = 126
        test_window = 21
        step_size = 21

        returns = bt.returns
        window_alphas = []
        all_selected = []

        for start_idx in range(0, len(returns) - train_window - test_window + 1, step_size):
            train_data = returns.iloc[start_idx : start_idx + train_window]
            test_data = returns.iloc[start_idx + train_window : start_idx + train_window + test_window]

            response = run_selection(train_data, bt.raw_candidates, stats_df=bt._audit_training_stats(train_data), top_n=1)

            if not response.winners:
                window_alphas.append(0.0)
                all_selected.append(set())
                continue

            selected_symbols = [w["symbol"] for w in response.winners]
            all_selected.append(set(selected_symbols))

            sel_returns = test_data[selected_symbols].mean(axis=1)
            pool_returns = test_data.mean(axis=1)

            # Selection Alpha: Selected - Pool
            alpha = (1 + sel_returns).prod() - (1 + pool_returns).prod()
            window_alphas.append(alpha)

        # Metrics Calculation
        mean_alpha = np.mean(window_alphas)
        std_alpha = np.std(window_alphas)
        sharpe_alpha = mean_alpha / std_alpha if std_alpha != 0 else 0

        # Max Drawdown of Alpha (Cumulative)
        cum_alpha = np.cumsum(window_alphas)
        peak = np.maximum.accumulate(cum_alpha)
        mdd_alpha = np.min(cum_alpha - peak)

        # Turnover (Average symbol change between windows)
        turnovers = []
        for i in range(1, len(all_selected)):
            prev = all_selected[i - 1]
            curr = all_selected[i]
            if not prev or not curr:
                continue
            # Jaccard Distance = 1 - (Intersection / Union)
            intersection = len(prev.intersection(curr))
            union = len(prev.union(curr))
            turnovers.append(1.0 - (intersection / union))
        avg_turnover = np.mean(turnovers) if turnovers else 0

        results.append(
            {
                "architecture": name,
                "mean_alpha": mean_alpha,
                "std_alpha": std_alpha,
                "risk_adj_alpha": sharpe_alpha,
                "total_alpha": np.sum(window_alphas),
                "mdd_alpha": mdd_alpha,
                "avg_turnover": avg_turnover,
                "hit_rate": np.mean([1 if a > 0 else 0 for a in window_alphas]),
            }
        )

    df_results = pd.DataFrame(results)
    print("\n🏁 Final Tournament Results (Selection Alpha):")
    print(df_results.to_string(index=False))

    champion = df_results.loc[df_results["risk_adj_alpha"].idxmax(), "architecture"]
    print(f"\n🥇 Champion: {champion}")


if __name__ == "__main__":
    run_tournament()
