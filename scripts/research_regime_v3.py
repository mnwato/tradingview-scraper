import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, cast

import numpy as np
import pandas as pd

from tradingview_scraper.regime import MarketRegimeDetector
from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.metrics import calculate_max_drawdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("research_regime_v3")


def calculate_tail_risk_metrics(returns: pd.DataFrame) -> Dict[str, float]:
    """Calculates tail risk metrics for the portfolio."""
    metrics = {}
    if returns.empty:
        return metrics

    # Portfolio-level returns (equal weight for estimation)
    # Explicitly cast to Series to satisfy type checker
    port_ret = cast(pd.Series, returns.mean(axis=1))

    # Max Drawdown
    mdd = calculate_max_drawdown(port_ret)
    metrics["max_drawdown"] = float(mdd)

    # VaR (95%)
    var_95 = np.percentile(port_ret, 5)
    metrics["var_95"] = float(var_95)

    # CVaR (95%) - Expected Shortfall
    cvar_95 = port_ret[port_ret <= var_95].mean()
    metrics["cvar_95"] = float(cvar_95)

    # Tail-Risk Mitigation Metric (TRM): Inverse of MDD adjusted for volatility
    vol = port_ret.std() * np.sqrt(252)
    metrics["trm_score"] = float(1.0 / (mdd * vol)) if mdd > 0 and vol > 0 else 0.0

    # Skewness and Kurtosis
    metrics["skew"] = float(port_ret.skew())
    metrics["kurtosis"] = float(port_ret.kurtosis())

    return metrics


def calculate_alpha_capture_metrics(returns: pd.DataFrame) -> Dict[str, float]:
    """Calculates metrics related to alpha capture potential."""
    metrics = {}
    if returns.empty:
        return metrics

    # Momentum strength (avg absolute return)
    # High momentum environments are better for alpha capture
    metrics["momentum_strength"] = float(returns.abs().mean().mean())

    # Dispersion (cross-sectional std dev)
    # Higher dispersion = more opportunities for alpha
    metrics["dispersion"] = float(returns.std(axis=1).mean())

    # Alpha Capture Efficiency (ACE): Returns adjusted for turnover proxy (dispersion)
    metrics["ace_score"] = float(returns.mean().mean() / (metrics["dispersion"] + 1e-6))

    return metrics


def research_regime_v3():
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    # Use settings.lakehouse_dir instead of hardcoded strings
    default_returns = str(run_dir / "data" / "returns_matrix.parquet")
    if not os.path.exists(default_returns):
        default_returns = str(settings.lakehouse_dir / "portfolio_returns.pkl")

    returns_path = os.getenv("RETURNS_MATRIX", default_returns)

    if not os.path.exists(returns_path):
        logger.error(f"Returns matrix missing at {returns_path}")
        return

    if str(returns_path).endswith(".parquet"):
        returns = pd.read_parquet(returns_path)
    else:
        returns = cast(pd.DataFrame, pd.read_pickle(returns_path))

    logger.info(f"Loaded returns matrix from {returns_path} with shape: {returns.shape}")

    detector = MarketRegimeDetector()

    # 1. Regime Detection
    regime, regime_score, quadrant = detector.detect_regime(returns)
    logger.info(f"Market Regime: {regime} (Score: {regime_score:.2f}) | Quadrant: {quadrant}")

    # 2. Tail Risk Analysis
    tail_risk = calculate_tail_risk_metrics(returns)
    logger.info("Tail Risk Metrics:")
    for k, v in tail_risk.items():
        logger.info(f"  - {k}: {v:.4f}")

    # 3. Alpha Capture Analysis
    alpha_metrics = calculate_alpha_capture_metrics(returns)
    logger.info("Alpha Capture Potential:")
    for k, v in alpha_metrics.items():
        logger.info(f"  - {k}: {v:.4f}")

    # 4. Persistence Integration
    # Try to find persistence metrics in run dir first, then lakehouse
    persistence_path = run_dir / "data" / "persistence_metrics.json"
    if not persistence_path.exists():
        persistence_path = settings.lakehouse_dir / "persistence_metrics.json"

    median_duration: Optional[float] = None

    if persistence_path.exists():
        with open(persistence_path, "r") as f:
            persistence_data = json.load(f)

        # Calculate population median duration if available
        durations = [x["trend_duration"] for x in persistence_data if x.get("regime") in ["STRONG_TREND", "TRENDING"]]
        if durations:
            median_duration = float(np.median(durations))
            logger.info(f"Median Trend Duration (Persistence): {median_duration:.1f} days")

            # Recommendation Logic - Nyquist sampling (duration / 2)
            recommended_window = max(5, int(median_duration / 2))
            logger.info(f"Recommended Rebalance Window (Nyquist): {recommended_window} days")
        else:
            logger.warning("No trend durations found in persistence data.")
            # Default fallback if no trends found
            recommended_window = 20
    else:
        logger.warning(f"Persistence metrics not found at {persistence_path}. Run 'make research-persistence' first.")
        recommended_window = 20  # Default

    # Save Enhanced Analysis
    analysis_output = {
        "regime": {"label": regime, "score": regime_score},
        "tail_risk": tail_risk,
        "alpha_capture": alpha_metrics,
        "persistence": {"median_trend_duration": median_duration, "recommended_window": recommended_window},
        "timestamp": pd.Timestamp.now().isoformat(),
    }

    # CR-831: Output Isolation
    default_output = str(run_dir / "data" / "regime_analysis_v3.json")
    output_path = os.getenv("REGIME_ANALYSIS_OUTPUT", default_output)

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(analysis_output, f, indent=2)
    logger.info(f"Enhanced regime analysis saved to {output_path}")


if __name__ == "__main__":
    research_regime_v3()
