import logging
import os
from pathlib import Path

import pandas as pd

from scripts.backtest_engine import BacktestEngine
from scripts.natural_selection import run_selection
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("feature_cache")


def cache_features():
    settings = get_settings()
    bt = BacktestEngine()

    train_window = 126
    test_window = 21
    step_size = 21
    start_date = "2025-01-01"
    end_date = "2025-12-31"

    returns_to_use = bt.returns
    if start_date:
        returns_to_use = returns_to_use[returns_to_use.index >= pd.to_datetime(start_date)]
    if end_date:
        returns_to_use = returns_to_use[returns_to_use.index <= pd.to_datetime(end_date)]

    total_len = len(returns_to_use)

    all_feature_rows = []

    # We use v3 engine to get all component probs
    settings.features.selection_mode = "v3"

    for start_idx in range(0, total_len - train_window - test_window + 1, step_size):
        train_end = start_idx + train_window
        train_data = returns_to_use.iloc[start_idx:train_end]

        # Forward return for HPO objective (Selection Alpha)
        # We look at the next 21 days
        test_data = returns_to_use.iloc[train_end : train_end + test_window]
        forward_returns = (1 + test_data).prod() - 1

        regime_info = bt.detector.detect_regime(train_data)
        regime = regime_info[0]

        logger.info(f"Processing window starting {train_data.index[0]} | Regime: {regime}")

        # Run selection once to get the raw candidate pool and their probabilities
        # We need ALL symbols in the discovery pool, not just winners
        response = run_selection(train_data, bt.raw_candidates, stats_df=bt._audit_training_stats(train_data), top_n=settings.top_n, threshold=settings.threshold, m_gate=-1.0)

        component_probs = response.metrics.get("component_probs", {})
        raw_metrics = response.metrics.get("raw_metrics", {})

        for symbol in train_data.columns:
            if symbol not in forward_returns.index:
                continue

            row = {
                "window_start": train_data.index[0],
                "symbol": symbol,
                "regime": regime,
                "forward_return": forward_returns[symbol],
            }

            # Add all component probabilities
            for comp_name, sym_probs in component_probs.items():
                row[f"p_{comp_name}"] = sym_probs.get(symbol, 0.0)

            # Add all raw metrics
            for comp_name, sym_raw in raw_metrics.items():
                row[f"raw_{comp_name}"] = sym_raw.get(symbol, 0.0)

            all_feature_rows.append(row)

    df_cache = pd.DataFrame(all_feature_rows)
    output_path = Path("data/lakehouse/hpo_feature_cache_raw.parquet")
    os.makedirs(output_path.parent, exist_ok=True)
    df_cache.to_parquet(output_path, index=False)
    logger.info(f"✅ Raw feature cache saved to {output_path} | Total rows: {len(df_cache)}")


if __name__ == "__main__":
    cache_features()
