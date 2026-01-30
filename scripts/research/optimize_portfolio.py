import json
import logging
from typing import Any, Dict, Iterable, Mapping, cast

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mpt_optimizer")


def calculate_portfolio_stats(weights: np.ndarray, returns: pd.DataFrame) -> float:
    cov_matrix = returns.cov() * 252
    port_variance = float(np.dot(weights.T, np.dot(cov_matrix, weights)))
    port_volatility = float(np.sqrt(port_variance))
    return port_volatility


def min_variance_objective(weights: np.ndarray, returns: pd.DataFrame) -> float:
    return calculate_portfolio_stats(weights, returns)


def risk_parity_objective(weights: np.ndarray, returns: pd.DataFrame) -> float:
    cov_matrix = returns.cov() * 252
    port_vol = float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))))

    mrc = np.dot(cov_matrix, weights) / port_vol
    rc = weights * mrc
    target_rc = port_vol / len(weights)
    return float(np.sum(np.square(rc - target_rc)))


def max_sharpe_objective(weights: np.ndarray, returns: pd.DataFrame) -> float:
    # Minimize negative Sharpe Ratio
    port_vol = calculate_portfolio_stats(weights, returns)
    port_ret = np.sum(returns.mean() * weights) * 252
    if port_vol == 0:
        return 0.0
    return -(port_ret / port_vol)


def _build_meta_map(meta: Iterable[Any] | Mapping[str, Any]) -> Dict[str, str]:
    if isinstance(meta, dict):
        out: Dict[str, str] = {}
        for k, v in meta.items():
            if isinstance(v, dict):
                v_dict = cast(Mapping[str, Any], v)
                out[str(k)] = str(v_dict.get("direction", "UNKNOWN"))
        return out

    out: Dict[str, str] = {}
    for item in meta:
        if isinstance(item, dict) and item.get("symbol"):
            out[str(item["symbol"])] = str(item.get("direction", "UNKNOWN"))
    return out


def optimize_portfolio():
    returns = pd.read_pickle("data/lakehouse/portfolio_returns.pkl")
    with open("data/lakehouse/portfolio_meta.json", "r") as f:
        meta = json.load(f)

    returns = returns.loc[:, (returns != 0).any(axis=0)]
    n_assets = returns.shape[1]
    logger.info(f"Optimizing for {n_assets} assets...")

    init_weights = np.array([1.0 / n_assets] * n_assets)
    bounds = tuple((0.0, 1.0) for _ in range(n_assets))
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

    logger.info("Solving Minimum Variance Portfolio...")
    res_mv = minimize(min_variance_objective, init_weights, args=(returns,), method="SLSQP", bounds=bounds, constraints=constraints)

    logger.info("Solving Risk Parity Portfolio...")
    res_rp = minimize(risk_parity_objective, init_weights, args=(returns,), method="SLSQP", bounds=bounds, constraints=constraints)

    logger.info("Solving Maximum Sharpe Ratio Portfolio...")
    res_ms = minimize(max_sharpe_objective, init_weights, args=(returns,), method="SLSQP", bounds=bounds, constraints=constraints)

    results_df = pd.DataFrame(index=returns.columns)
    results_df["Min_Var_Weight"] = res_mv.x
    results_df["Risk_Parity_Weight"] = res_rp.x
    results_df["Max_Sharpe_Weight"] = res_ms.x

    meta_map = _build_meta_map(meta)
    results_df["Signal"] = [meta_map.get(s, "UNKNOWN") for s in results_df.index]

    mv_top = results_df[results_df["Min_Var_Weight"] > 0.001].sort_values(by="Min_Var_Weight", ascending=[False])  # type: ignore[arg-type]
    rp_top = results_df[results_df["Risk_Parity_Weight"] > 0.001].sort_values(by="Risk_Parity_Weight", ascending=[False])  # type: ignore[arg-type]
    ms_top = results_df[results_df["Max_Sharpe_Weight"] > 0.001].sort_values(by="Max_Sharpe_Weight", ascending=[False])  # type: ignore[arg-type]

    print("\n" + "=" * 80)
    print("PORTFOLIO OPTIMIZATION RESULTS (MPT)")
    print("=" * 80)

    print(f"\n[1] MINIMUM VARIANCE PORTFOLIO (Expected Vol: {res_mv.fun:.2%})")
    print(mv_top[["Signal", "Min_Var_Weight"]].head(15).to_string())

    print("\n[2] RISK PARITY PORTFOLIO")
    print(rp_top[["Signal", "Risk_Parity_Weight"]].head(15).to_string())

    print(f"\n[3] MAXIMUM SHARPE RATIO PORTFOLIO (Sharpe: {-res_ms.fun:.2f})")
    print(ms_top[["Signal", "Max_Sharpe_Weight"]].head(15).to_string())

    with open("data/lakehouse/portfolio_optimized.json", "w") as f:
        results_df.to_json(f)


if __name__ == "__main__":
    optimize_portfolio()
