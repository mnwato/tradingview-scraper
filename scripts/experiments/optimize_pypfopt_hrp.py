import logging

import numpy as np
import pandas as pd
from pypfopt import HRPOpt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_sharpe(weights, returns):
    port_returns = returns.dot(weights)
    mean_ret = port_returns.mean()
    std_ret = port_returns.std()
    return (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0


def run_experiment():
    # Load data
    df = pd.read_pickle("data/lakehouse/portfolio_returns.pkl")
    df.index = pd.to_datetime(df.index)

    # Slice for Window 6 (Turbulent)

    # Based on audit log: test_start="2025-09-29", test_end="2025-11-07"
    start_date = "2025-09-29"
    end_date = "2025-11-07"

    mask = (df.index >= start_date) & (df.index <= end_date)
    window_returns = df.loc[mask]

    if window_returns.empty:
        logger.error("No data for window 6")
        return

    logger.info(f"Window 6 Data: {window_returns.shape}")

    # Train data (usually the window BEFORE the test, or we simulate the optimization AT start_date)
    # The optimization happens on TRAIN data, then tested on TEST data.
    # Audit log says: train_window=180.
    # So train data is [start_date - 180d : start_date]

    train_end = pd.Timestamp(start_date)
    train_start = train_end - pd.Timedelta(days=180)

    train_mask = (df.index >= train_start) & (df.index < train_end)
    train_returns = df.loc[train_mask].dropna(axis=1, how="all").fillna(0.0)

    # Align columns
    test_returns = window_returns[train_returns.columns].fillna(0.0)

    logger.info(f"Train Data: {train_returns.shape}")
    logger.info(f"Test Data: {test_returns.shape}")

    linkage_methods = ["single", "complete", "average", "ward"]
    results = []

    for method in linkage_methods:
        try:
            hrp = HRPOpt(train_returns)
            weights = hrp.optimize(linkage_method=method)
            w_series = pd.Series(weights)

            # Evaluate on Test Data
            sharpe = calculate_sharpe(w_series, test_returns)
            logger.info(f"Method: {method} -> Sharpe: {sharpe:.4f}")
            results.append({"method": method, "sharpe": sharpe})
        except Exception as e:
            logger.error(f"Method {method} failed: {e}")

    # Output results
    print("\n--- HRP Linkage Experiment Results ---")
    print(pd.DataFrame(results).to_markdown())


if __name__ == "__main__":
    run_experiment()
