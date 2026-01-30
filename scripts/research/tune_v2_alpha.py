import argparse
import json
import logging
import os
from pathlib import Path

import numpy as np
import optuna
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("normalization_audit")


def apply_normalization(series: pd.Series, method: str, clipping_sigma: float = 3.0) -> pd.Series:
    """
    Applies window-relative normalization to a series of raw metrics.
    """
    if series.empty:
        return series

    if method == "rank":
        return series.rank(pct=True)

    elif method == "zscore":
        mu = series.mean()
        sigma = series.std()
        if sigma == 0:
            return pd.Series(0.5, index=series.index)
        z = (series - mu) / sigma
        z_clipped = z.clip(-clipping_sigma, clipping_sigma)
        return (z_clipped + clipping_sigma) / (2 * clipping_sigma)

    elif method == "logistic":
        mu = series.mean()
        sigma = series.std()
        if sigma == 0:
            return pd.Series(0.5, index=series.index)
        z = (series - mu) / (sigma if sigma != 0 else 1.0)
        return 1.0 / (1.0 + np.exp(-z))

    elif method == "minmax":
        s_min = series.min()
        s_max = series.max()
        if s_max == s_min:
            return pd.Series(0.5, index=series.index)
        return (series - s_min) / (s_max - s_min)

    return series


def objective(trial, df_cache: pd.DataFrame):
    # 1. Global Parameters
    clipping_sigma = trial.suggest_float("clipping_sigma", 1.0, 5.0)
    top_n = trial.suggest_int("top_n", 2, 5)

    # 2. Factor-Specific parameters (Weights and Methods)
    factors = ["momentum", "stability", "liquidity", "antifragility", "survival", "efficiency", "entropy", "hurst"]

    raw_weights = {}
    methods = {}
    for f in factors:
        raw_weights[f] = trial.suggest_float(f"w_{f}", 0.0, 1.0)
        methods[f] = trial.suggest_categorical(f"m_{f}", ["rank", "zscore", "logistic", "minmax"])

    total_w = sum(raw_weights.values())
    if total_w == 0:
        return -1.0
    weights = {k: v / total_w for k, v in raw_weights.items()}

    # 3. Apply Normalization per window
    df = df_cache.copy()

    def normalize_window(group):
        for f in factors:
            raw_col = f"raw_{f}"
            if raw_col in group.columns:
                vals = group[raw_col]
                if f == "entropy":
                    vals = -vals
                elif f == "hurst":
                    vals = -np.abs(vals - 0.5)

                group[f"n_{f}"] = apply_normalization(vals, methods[f], clipping_sigma)
        return group

    df = df.groupby("window_start", group_keys=False).apply(normalize_window)

    # 4. Calculate Score & Alpha
    additive_score = pd.Series(0.0, index=df.index)
    for f, w in weights.items():
        n_col = f"n_{f}"
        if n_col in df.columns:
            additive_score += w * df[n_col]

    df["v2_score"] = additive_score

    def get_window_alpha(group):
        selected = group.nlargest(top_n, "v2_score")
        sel_ret = selected["forward_return"].mean()
        raw_ret = group["forward_return"].mean()
        return sel_ret - raw_ret

    window_alphas = df.groupby("window_start", group_keys=False).apply(get_window_alpha, include_groups=False)

    mean_alpha = window_alphas.mean()
    std_alpha = window_alphas.std()

    if std_alpha == 0 or np.isnan(std_alpha):
        return -1.0

    return float(mean_alpha / std_alpha)


def run_study(cache_path: str, trials: int = 500):
    if not os.path.exists(cache_path):
        logger.error(f"Raw feature cache not found: {cache_path}")
        return

    df_all = pd.read_parquet(cache_path)

    logger.info(f"Starting Multi-Method Normalization HPO | Rows: {len(df_all)} | Windows: {len(df_all['window_start'].unique())}")

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))

    study.optimize(lambda t: objective(t, df_all), n_trials=trials)

    logger.info("✅ Normalization Study Complete")
    logger.info(f"Best Risk-Adj Alpha: {study.best_value:.4f}")

    # Save results
    output_dir = Path("artifacts/hpo")
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_final = {k.replace("w_", ""): v for k, v in study.best_params.items() if k.startswith("w_")}
    total_final = sum(raw_final.values())
    norm_final = {k: v / total_final for k, v in raw_final.items()}

    methods_final = {k.replace("m_", ""): v for k, v in study.best_params.items() if k.startswith("m_")}

    results = {
        "engine": "v2.1_multi_norm_audit",
        "best_risk_adj_alpha": float(study.best_value),
        "best_params": study.best_params,
        "normalized_weights": norm_final,
        "methods": methods_final,
        "n_trials": trials,
        "timestamp": pd.Timestamp.now().isoformat(),
    }

    output_file = output_dir / "normalization_audit_multi_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=500)
    args = parser.parse_args()

    cache_path = "data/lakehouse/hpo_feature_cache_raw.parquet"
    run_study(cache_path, args.trials)
