import json
import logging

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clustered_optimizer")


def calculate_cluster_risk(weights: np.ndarray, cov_matrix: pd.DataFrame) -> float:
    port_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
    return np.sqrt(port_variance)


def risk_parity_objective(weights: np.ndarray, cov_matrix: pd.DataFrame) -> float:
    port_vol = calculate_cluster_risk(weights, cov_matrix)
    if port_vol == 0:
        return 0
    mrc = np.dot(cov_matrix, weights) / port_vol
    rc = weights * mrc
    target_rc = port_vol / len(weights)
    return float(np.sum(np.square(rc - target_rc)))


def optimize_clustered_portfolio():
    # 1. Load Data
    returns = pd.read_pickle("data/lakehouse/portfolio_returns.pkl")
    with open("data/lakehouse/portfolio_clusters.json", "r") as f:
        clusters = json.load(f)

    # 2. Filter returns to only include clustered symbols
    all_clustered_symbols = [sym for cluster in clusters.values() for sym in cluster]
    returns = pd.DataFrame(returns[all_clustered_symbols])
    returns = returns.fillna(0.0)

    cov_matrix = returns.cov() * 252  # type: ignore

    # 3. Calculate Cluster Returns (Equal weighted within cluster)
    cluster_returns = pd.DataFrame()
    for c_id, symbols in clusters.items():
        cluster_returns[f"Cluster_{c_id}"] = returns[symbols].mean(axis=1)

    cluster_cov = cluster_returns.cov() * 252
    n_clusters = len(clusters)

    # 4. Step 1: Allocate across Clusters (Risk Parity)
    logger.info(f"Allocating across {n_clusters} clusters using Risk Parity...")
    init_weights = np.array([1.0 / n_clusters] * n_clusters)
    bounds = tuple((0.0, 1.0) for _ in range(n_clusters))
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

    res_clusters = minimize(risk_parity_objective, init_weights, args=(cluster_cov,), method="SLSQP", bounds=bounds, constraints=constraints)
    cluster_weights = res_clusters.x

    # 5. Step 2: Allocate within Clusters (Risk Parity or Equal Weight)
    final_weights = pd.Series(0.0, index=returns.columns)

    for i, (c_id, symbols) in enumerate(clusters.items()):
        c_weight = cluster_weights[i]
        n_in_cluster = len(symbols)

        if n_in_cluster == 1:
            final_weights[symbols[0]] = c_weight
        else:
            # Simple equal weight within cluster for now
            # Could do risk parity here too if desired
            for sym in symbols:
                final_weights[sym] = c_weight / n_in_cluster

    # 6. Results & Reporting
    results = []
    for c_id, symbols in clusters.items():
        c_total_weight = cluster_weights[list(clusters.keys()).index(c_id)]
        for sym in symbols:
            results.append({"Symbol": sym, "Cluster": f"Cluster {c_id}", "Weight": final_weights[sym], "Cluster_Total": c_total_weight})

    df = pd.DataFrame(results).sort_values(by=["Cluster_Total", "Weight"], ascending=False)

    print("\n" + "=" * 80)
    print("CLUSTERED PORTFOLIO ALLOCATION (Hierarchy-Aware)")
    print("=" * 80)

    current_cluster = ""
    for _, row in df.iterrows():
        if row["Cluster"] != current_cluster:
            print(f"\n[{row['Cluster']}] (Total Allocation: {row['Cluster_Total']:.2%})")
            current_cluster = row["Cluster"]
        print(f"  - {row['Symbol']:<25}: {row['Weight']:.4%}")

    # Save results
    df.to_json("data/lakehouse/portfolio_clustered.json")
    print("\n" + "=" * 80)
    print("Saved clustered portfolio to data/lakehouse/portfolio_clustered.json")


if __name__ == "__main__":
    optimize_clustered_portfolio()
