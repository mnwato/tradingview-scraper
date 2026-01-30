import argparse
import json
import logging
import os
from pathlib import Path

import numpy as np
import optuna
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("selection_hpo")


def objective(trial, df_cache: pd.DataFrame):
    # 1. Suggest weights for components
    weights = {
        "momentum": trial.suggest_float("w_momentum", 0.0, 2.0),
        "stability": trial.suggest_float("w_stability", 0.0, 2.0),
        "liquidity": trial.suggest_float("w_liquidity", 0.0, 2.0),
        "antifragility": trial.suggest_float("w_antifragility", 0.0, 2.0),
        "survival": trial.suggest_float("w_survival", 0.0, 2.0),
        "efficiency": trial.suggest_float("w_efficiency", 0.0, 2.0),
        "entropy": trial.suggest_float("w_entropy", 0.0, 2.0),
        "hurst_clean": trial.suggest_float("w_hurst", 0.0, 2.0),
    }

    # 2. Suggest top_n (Breadth Tuning)
    top_n = trial.suggest_int("top_n", 2, 5)

    # 3. Calculate Log-MPS Score
    floor = 1e-9
    df = df_cache.copy()

    log_score = pd.Series(0.0, index=df.index)
    for name, w in weights.items():
        p_col = f"p_{name}"
        if p_col in df.columns:
            log_score += w * np.log(df[p_col].clip(lower=floor))

    df["log_score"] = log_score

    # 4. Select top N symbols per window
    def get_window_alpha(group):
        selected = group.nlargest(top_n, "log_score")
        sel_ret = selected["forward_return"].mean()
        raw_ret = group["forward_return"].mean()
        return sel_ret - raw_ret

    window_alphas = df.groupby("window_start", group_keys=False).apply(get_window_alpha, include_groups=False)

    # 5. Objective: Risk-Adjusted Selection Alpha
    # We want high mean and low variance across windows (consistency)
    mean_alpha = window_alphas.mean()
    std_alpha = window_alphas.std()

    if std_alpha == 0 or np.isnan(std_alpha):
        return -1.0  # Penalize lack of variance (usually means no data)

    risk_adjusted = mean_alpha / std_alpha

    return float(risk_adjusted)


def run_study(regime_name: str, cache_path: str, trials: int = 200):
    if not os.path.exists(cache_path):
        logger.error(f"Feature cache not found: {cache_path}")

        return

    df_all = pd.read_parquet(cache_path)

    # Filter by regime

    if regime_name == "expansion":
        study_df = df_all[df_all["regime"].isin(["NORMAL", "QUIET"])]

    elif regime_name == "stressed":
        study_df = df_all[df_all["regime"].isin(["TURBULENT", "CRISIS"])]

    else:
        # 'all' or 'global' mode

        study_df = df_all

    if study_df.empty:
        logger.warning(f"No data for regime {regime_name}")

        return

    logger.info(f"Starting HPO for {regime_name} | Rows: {len(study_df)} | Windows: {len(study_df['window_start'].unique())}")

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))

    study.optimize(lambda t: objective(t, study_df), n_trials=trials)

    logger.info(f"✅ HPO Complete for {regime_name}")

    logger.info(f"Best Risk-Adj Alpha: {study.best_value:.4f}")

    logger.info("Best Parameters:")

    for k, v in study.best_params.items():
        logger.info(f"  {k}: {v:.4f}")

    # 6. Final Report Artifacts

    output_dir = Path("artifacts/hpo")

    output_dir.mkdir(parents=True, exist_ok=True)

    results = {"regime": regime_name, "best_risk_adj_alpha": float(study.best_value), "best_params": study.best_params, "n_trials": trials, "timestamp": pd.Timestamp.now().isoformat()}

    output_file = output_dir / f"selection_best_{regime_name}.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved to {output_file}")

    with open(output_dir / f"selection_best_{regime_name}.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--regime", choices=["expansion", "stressed", "all"], default="all")
    parser.add_argument("--trials", type=int, default=200)
    args = parser.parse_args()

    cache_path = "data/lakehouse/hpo_feature_cache.parquet"

    if args.regime == "all":
        run_study("expansion", cache_path, args.trials)
        run_study("stressed", cache_path, args.trials)
    else:
        run_study(args.regime, cache_path, args.trials)
