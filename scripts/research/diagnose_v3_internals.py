import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.natural_selection import run_selection
from tradingview_scraper.selection_engines import get_robust_correlation
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("diagnose_v3")


def diagnose_v3():
    settings = get_settings()

    returns_path = "data/lakehouse/portfolio_returns.pkl"
    if not Path(returns_path).exists():
        logger.error("Returns missing")
        return

    df_returns = pd.read_pickle(returns_path)
    try:
        new_idx = [pd.to_datetime(t).replace(tzinfo=None) for t in df_returns.index]
        df_returns.index = pd.DatetimeIndex(new_idx)
    except Exception:
        pass

    raw_candidates = json.load(open("data/lakehouse/portfolio_candidates_raw.json"))

    train_window = 120
    test_window = 20
    step_size = 20

    total_len = len(df_returns)
    logs = []

    logger.info(f"Diagnosing V3 Internals over {total_len} days...")

    for start_idx in range(0, total_len - train_window - test_window + 1, step_size):
        train_end = start_idx + train_window
        train_data = df_returns.iloc[start_idx:train_end]

        # Calculate Kappa
        corr = get_robust_correlation(train_data)
        kappa = 0.0
        if not corr.empty:
            eigenvalues = np.linalg.eigvalsh(corr.values)
            min_ev = np.abs(eigenvalues).min()
            kappa = float(eigenvalues.max() / (min_ev + 1e-15))

        panic_mode = kappa > 1e18

        # Run Selection V3
        stats_df = pd.DataFrame(
            [
                {"Symbol": s, "Vol": train_data[s].std() * np.sqrt(252), "Return": train_data[s].mean() * 252, "Antifragility_Score": 0.5, "Fragility_Score": 0.0, "Regime_Survival_Score": 1.0}
                for s in train_data.columns
            ]
        )

        response = run_selection(train_data, raw_candidates, stats_df=stats_df, top_n=2, threshold=0.45, m_gate=-0.05, mode="v3.1")

        n_selected = len(response.winners)
        n_clusters = len(response.audit_clusters) if response.audit_clusters else 0
        avg_cluster_size = np.mean([d["size"] for d in response.audit_clusters.values()]) if response.audit_clusters else 0

        logs.append(
            {
                "date": str(train_data.index[-1]),
                "kappa": kappa,
                "panic_mode": panic_mode,
                "n_selected": n_selected,
                "n_clusters": n_clusters,
                "n_vetoed": len(response.vetoes),
                "avg_cluster_size": avg_cluster_size,
            }
        )

    df_logs = pd.DataFrame(logs)
    print("\n--- V3 Internal Diagnosis ---")
    print(f"Total Windows: {len(df_logs)}")
    print(f"Panic Mode (Kappa > 1e6): {df_logs['panic_mode'].sum()} windows ({df_logs['panic_mode'].mean():.1%})")
    print(f"Avg Kappa: {df_logs['kappa'].mean():.2e}")
    print(f"Avg Selected: {df_logs['n_selected'].mean():.1f}")
    print(f"Avg Vetoed: {df_logs['n_vetoed'].mean():.1f}")

    if df_logs["panic_mode"].sum() > 0:
        print("\n--- Panic Mode Analysis ---")
        panic_df = df_logs[df_logs["panic_mode"]]
        print(f"Avg Selected in Panic: {panic_df['n_selected'].mean():.1f}")
        print(f"Avg Vetoed in Panic: {panic_df['n_vetoed'].mean():.1f}")


if __name__ == "__main__":
    diagnose_v3()
