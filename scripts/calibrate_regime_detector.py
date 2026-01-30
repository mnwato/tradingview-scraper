import json
import logging
from pathlib import Path

import numpy as np
import optuna

from scripts.backtest_engine import BacktestEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("regime_calibration")


class RegimeCalibrationObjective:
    def __init__(self, train_window: int = 60, test_window: int = 40, step_size: int = 40):
        self.engine = BacktestEngine()
        self.train_window = train_window
        self.test_window = test_window
        self.step_size = step_size

    def __call__(self, trial: optuna.Trial):
        # 1. Suggest Weights
        weights = {
            "vol_ratio": trial.suggest_float("vol_ratio", 0.0, 1.0),
            "turbulence": trial.suggest_float("turbulence", 0.0, 1.0),
            "clustering": trial.suggest_float("clustering", 0.0, 1.0),
            "entropy": trial.suggest_float("entropy", 0.0, 1.0),
            "hurst": trial.suggest_float("hurst", 0.0, 1.0),
            "stationarity": trial.suggest_float("stationarity", 0.0, 1.0),
        }

        # 2. Normalize weights
        total = sum(weights.values())
        for k in weights:
            weights[k] /= total

        # 3. Run Tournament
        try:
            # We pass the weights to the BacktestEngine which we modified to accept them
            results = self.engine.run_tournament(
                train_window=self.train_window, test_window=self.test_window, step_size=self.step_size, engines=["adaptive"], profiles=["adaptive"], regime_weights=weights
            )

            # 4. Extract Average Sharpe
            sharpes = []
            for res in results["tournament_results"]:
                s = res["metrics"].get("sharpe", 0.0)
                if not np.isnan(s):
                    sharpes.append(s)

            return np.mean(sharpes) if sharpes else -10.0

        except Exception as e:
            logger.error(f"Trial failed: {e}")
            return -10.0


def run_calibration(n_trials=20):
    study = optuna.create_study(direction="maximize")
    objective = RegimeCalibrationObjective()
    study.optimize(objective, n_trials=n_trials)

    print("\n### 🏆 Optimal Regime Weights Found:")
    print(json.dumps(study.best_params, indent=2))

    # Save best params
    best_path = Path("artifacts/summaries/best_regime_weights.json")
    best_path.parent.mkdir(parents=True, exist_ok=True)
    with open(best_path, "w") as f:
        json.dump(study.best_params, f, indent=2)

    return study.best_params


if __name__ == "__main__":
    # For execution in the build mode
    run_calibration(n_trials=5)
