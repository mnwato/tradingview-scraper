# Design Doc: Dynamic Selection Intelligence (v1)

## 1. Problem Statement & Root Cause
The previous "Static Veto" architecture suffered from **Degrees of Freedom (DOF) Mismatch**. While spectral filters (Entropy, Efficiency) were technically correct, their static nature caused "Sparsity Collapse" (n < 4) in early backtest windows or quiet regimes, rendering convex optimization engines (`max_sharpe`, `hrp`) numerically unstable.

### Root Causes
1. **Lookback Truncation**: High-entropy noise caused by calculating 500d metrics on 60d of actual data.
2. **Selection-Solver Decoupling**: Selection logic was unaware of the minimum $N$ required for a stable covariance matrix.
3. **Regime Blindness**: Global thresholds didn't adapt to market-wide volatility compression.

## 2. Proposed Solution: Hierarchical Threshold Relaxation (HTR)
We move from a binary "Veto/Pass" system to a **Multi-Stage Recruitment Funnel**.

### Stage 1: The Golden Filter (Strict)
Apply institutional defaults (e.g., Entropy < 0.995, Efficiency > 0.03). If $N \ge 15$, stop.

### Stage 2: Spectral Relaxation
If $N < 15$, incrementally relax predictability thresholds by 20% (e.g., Entropy < 0.999, Efficiency > 0.01). If $N \ge 15$, stop.

### Stage 3: Clustered Representation (Factor Floor)
If $N$ is still too low, the engine must ensure every significant cluster (determined via Ward linkage) has at least **one** representative asset, regardless of marginal spectral failure. This ensures the optimizer has a "complete map" of the market factor space.

### Stage 4: Alpha-Leader Recruitment (Final Fallback)
If $N < 15$ after Stage 3, recruit the top-ranked assets by `alpha_score` from the rejected pool until $N = 15$.

## 3. Implementation Plan
- **`SelectionEngineV3_3`**: New engine class implementing the HTR loop.
- **`SelectionResponse`**: Updated to include `relaxation_stage` and `active_thresholds` for forensic audit.
- **`Metadata Fallback`**: If `tick_size` or `lot_size` is missing, use exchange-class defaults (e.g., BINANCE_SPOT_DEFAULT) instead of an absolute veto.

## 4. Success Metrics
1. **Solver Success Rate**: 100% (No `nan` or `infeasible` results).
2. **Cluster Coverage**: 100% of non-empty clusters represented in the final selection.
3. **Audit Traceability**: Every recruited asset must be tagged with its recruitment stage in `audit.jsonl`.

## 6. Numerical Hardening (v1.1)
To handle highly correlated crypto regimes, the platform now implements **Adaptive Ridge Scaling**.

### 6.1 Dynamic Shrinkage Loop
If the condition number $\kappa$ of the correlation/covariance matrix exceeds `kappa_shrinkage_threshold` (default: 5000), the engine applies iterative diagonal loading:
$R' = (1-\lambda)R + \lambda I$
The intensity $\lambda$ starts at 1% and increases in 1% steps until $\kappa$ is bounded or $\lambda = 10\%$ is reached.

### 6.2 Adaptive Fallback (ERC)
The meta-engine transition logic now incorporates an **Equal Risk Contribution (ERC)** safety state. This ensures that during regime transitions or solver instability, the portfolio defaults to a risk-parity state rather than returning NaN or unhedged weights.

## 8. Modular Portfolio Engine Architecture (v1.3)
To improve maintainability and testability, the portfolio engine layer has been refactored from a monolithic `engines.py` into a directory-based structure.

### 8.1 Directory Structure
- `tradingview_scraper/portfolio_engines/`:
    - `__init__.py`: Factory (`build_engine`) and central registry.
    - `base.py`: Shared abstract base class (`BaseRiskEngine`) and common mathematical utilities (`_project_capped_simplex`, `_safe_series`).
    - `impl/`: Concrete implementations.
        - `custom.py`: Clustered/Barbell logic.
        - `skfolio.py`, `riskfolio.py`, `pypfopt.py`, `cvx.py`: 3rd-party library adapters.
        - `adaptive.py`: Regime-aware meta-engine logic.

## 9. Performance Recovery & Factor Hardening (v1.4)
Analysis of previous results showed that aggressive stability hardening and small winner pools ($N < 5$) led to "Metric Collisions" where diverse solvers converged to Equal Weight.

### 9.1 Toxicity Hard-Stop
To prevent alpha dilution, we enforce a quality-gate on HTR relaxation. If the best asset in a cluster has an Entropy $> 0.999$, Stage 3 recruitment is skipped. This ensures the portfolio remains a collection of شناسایی identifiable trends.

### 9.2 Backend Purity & Hybrid Barbell
By refactoring the portfolio layer into modular adapters and removing silent fallbacks, each engine now provides a unique mathematical signature. The `barbell` strategy has been upgraded to a "Hybrid" model, where the engine-native optimizer is applied to the core layer, restoring strategy-specific alpha views.

### 9.3 Pool Expansion
Relaxing the momentum hurdle to $-0.05$ and the entropy ceiling to $0.999$ ensures that the portfolio engines always have sufficient degrees of freedom ($N \ge 15$) to differentiate their optimization solutions.

## 10. Top-N Cluster Selection Logic (v2.1)
To ensure factor diversity while maintaining alpha conviction, the selection engine implements a **Dual-Layer Filter**.

### 10.1 Hierarchical Factor Mapping
The engine performs hierarchical clustering (Ward Linkage) on the raw return correlations of the candidate pool. This identifies latent factor groupings (e.g., Meme coins, AI tokens, DeFi anchors) based on price action rather than metadata tags.

### 10.2 Intra-Cluster Conviction Ranking
Within each identified cluster, candidates are ranked by their **Log-MPS Conviction Score**.
- **The Top-N Rule**: Only the top $N$ (default: 3) highest-conviction assets per cluster are recruited for the final portfolio.
- **Directional Diversity**: Ranking is performed separately for `LONG` and `SHORT` directions within the cluster to ensure balanced factor exposure in multi-directional profiles.

## 11. Baseline Selection Standards (v2.2)
To quantify the impact of statistical selection, the platform utilizes two distinct baseline standards.

### 11.1 Pass-through Baseline (`baseline`)
Passes ALL raw candidates sanctioned by discovery. This quantifies the "Gross Selection Alpha" of the entire funnel, including liquidity and hygiene filters.

### 11.2 Structural Baseline (`liquid_htr`)
Performs hierarchical clustering and HTR relaxation exactly like the production engines, but picks the Top-N per cluster based on **Liquidity** (`Value.Traded`) instead of Log-MPS conviction.
- **Purpose**: Isolate "Clustering Alpha" (diversification benefit) from "Statistical Alpha" (predictive conviction).
- **Justification**: Differentiates whether performance gains are due to purely reducing the pool size ($N=200 \rightarrow 20$) or due to picking superior assets within each cluster.

## 15. Recursive Weight Flattening (v2.0)
To bridge the gap between abstract Strategy Optimization and physical asset execution, the platform implements a recursive aggregation chain.

### 15.1 The Weight Chain
1.  **Solver Layer (Pillar 3)**: Output is $w_{strat\_i}$, the weight of the $i$-th strategy stream.
2.  **Synthesis Layer (Pillar 2)**: Each stream $i$ maps to a set of underlying assets with logic-specific factors.
3.  **Physical Layer (Execution)**: The Orchestrator flattens these weights:
    $$Weight_{Asset,j} = \sum_i (w_{strat\_i} \times Factor_{asset\_j, i})$$

### 15.2 Directional Handling
Directionality is handled via **Synthetic Factors**:
- If Atom $i$ is `LONG` Asset $j$: $Factor = 1.0$
- If Atom $i$ is `SHORT` Asset $j$: $Factor = -1.0$
- **Net Exposure**: The resulting `Net_Weight` represents the actual dollar position to be executed, while `Weight` represents the absolute capital allocation.

