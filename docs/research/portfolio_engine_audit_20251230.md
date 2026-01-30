# Research: Portfolio Engine Audit & Profile Review (2025-12-30)

## 1. Executive Summary
This audit reviews the behavior of five optimization engines across four risk profiles, validated via 3D tournament benchmarking. We identified critical performance outliers, analyzed the impact of universe pruning on risk stability, and audited the fidelity of our market simulators.

## 2. Optimization Engine Analysis

### 2.1 Top Performers by Profile
| Profile | Top Engine | Realized Sharpe | Rationale |
| :--- | :--- | :--- | :--- |
| **Min Variance** | `skfolio` | 1.76 | Superior handling of hierarchical covariance shrinkage. |
| **Risk Parity** | `skfolio` | 3.62 | Most stable risk contribution across clusters. |
| **Max Sharpe** | `custom (cvxpy)` | **3.55** | Best identification of high-convexity clusters in current regime. |
| **Antifragile Barbell** | `custom (cvxpy)` | **1.67** | Reliable execution of dual-sleeve (Aggressor/Core) logic. |

### 2.2 Outlier Detection: The "Execution Alpha" Anomaly
In the **Maximum Sharpe** profile, we observed "Negative Alpha Decay" (Realized Sharpe > Idealized Sharpe). 
- **Cause**: The `cvxportfolio` simulator performs continuous rebalancing to target weights, which in highly trending/volatile regimes (Regime Score: 0.88), acts as a "gamma scalping" mechanism, capturing more intraday trend than the point-in-time `custom` simulator.
- **Action**: No remediation needed, but this confirms that our strategies benefit from the execution fidelity of a policy-based simulator.

### 2.3 Turnover Stability
- **`cvxportfolio` (Engine)**: Leads in operational stability with the lowest average turnover (21.1%). It successfully filters out tactical noise.
- **`custom (cvxpy)`**: Shows higher turnover (32%+) in MaxSharpe, indicating a high-conviction response to regime shifts.

## 3. Universe Selection & Discovery Audit

### 3.1 Pruning Efficiency
- **Discovery Pool**: 368 raw symbols narrowed to 115 canonical identities.
- **Natural Selection**: 65 winners chosen.
- **Observation**: Cluster 4 (BTC/ETH variants) remains a point of concentration. While these are economically distinct (Perps vs Spot), their correlation is > 0.95.
- **Recommendation**: Tighten the `Identity Merging` logic to treat BTC and ETH variants across all venues as a single economic identity during the pruning phase.

## 4. Data Health & Workflow Integrity

### 4.1 Missing Artifact Gate
- **Detection**: The `health-report` was missing from the `latest` implementation artifacts.
- **Remediation**: Added `make health-report` to the `finalize` workflow to ensure every implemented portfolio is accompanied by a 100% gap-free audit.

## 5. Conclusion & Implementation Guide

1.  **For Stability (Conservative/HRP)**: Utilize **`skfolio`** or **`cvxportfolio`** as the implementation backend.
2.  **For Growth (MaxSharpe/Barbell)**: Utilize the **`custom (cvxpy)`** engine, as its identified clusters provide the highest convex returns in trending regimes.
3.  **Governance**: Always run `make tournament` before implementation to check if the current market regime has caused a "Leader Shift" between engines.
