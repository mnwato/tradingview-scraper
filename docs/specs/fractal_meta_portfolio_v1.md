# Specification: Fractal Hierarchical Meta-Portfolio (v1.0)

## 1. Overview
The Fractal Meta-Portfolio architecture enables hierarchical risk allocation by nesting strategy sleeves into recursive structures. This allows the platform to manage complexity by grouping strategies into logical branches (e.g., "Crypto Trend", "TradFi Value") before final top-level aggregation.

## 2. Core Requirements

### 2.1 Recursive Nesting
- The system MUST support `sleeves` that point to other `meta_profile` definitions.
- The aggregation logic MUST recursively descend the tree until it reaches atomic sleeves (individual production runs).

### 2.2 Weighted Return Aggregation
- When resolving a nested meta-profile, the parent node MUST use the sub-meta's **Optimized Return Stream**.
- If optimized weights for the sub-meta are available, the return stream is the weighted sum of its children.
- If optimization failed, the system defaults to an **Equal-Weight Proxy** to ensure pipeline continuity.

### 2.3 Physical Asset Collapse (Flattening)
- The final implementation target MUST consist strictly of **Physical Assets** (e.g., `BINANCE:BTCUSDT`).
- "Logic Atoms" (e.g., `BTC_trend_LONG`) must be resolved into their underlying symbols.
- Weights for the same physical asset across different branches MUST be summed.

### 2.4 Forensic Auditability
- The system MUST persist the **Hierarchical Cluster Tree** (`meta_cluster_tree_*.json`) at each level.
- This artifact preserves the uncollapsed strategy-level weights for review before they are merged into symbols.

### 2.5 Directional Correction (Sign Test)
- The system MUST implement **Synthetic Long Normalization** for SHORT atoms before optimization/ensembling:
  - `R_syn_short = -clip(R_raw, upper=1.0)` (short loss cap at -100%)
  - `R_syn_long = R_raw`
- A deterministic audit MUST be available to prove SHORT inversion occurs **before** meta-layer ensembling.
- Reference: `docs/specs/directional_correction_sign_test_v1.md`

## 3. Data Pipeline Orchestration

### 3.1 Streamlined Execution (`run_meta_pipeline.py`)
The meta-portfolio pipeline is unified into a single command that executes the following stages sequentially:
0.  **Directional Gate**: Executes the Directional Correction Sign Test (when enabled) and persists `directional_sign_test.json`.
1.  **Aggregation**: Recursively joins return series from all sleeves.
2.  **Optimization**: Applies HRP/MVO solvers at the current hierarchy level.
3.  **Flattening**: Recursively multiplies weights down to physical symbols.
4.  **Reporting**: Generates a forensic Markdown report with cluster trees and performance metrics.

### 3.2 Workspace Isolation
All intermediate artifacts are prefixed with the root `meta_profile` name to prevent cross-profile namespace pollution in the Lakehouse.

## 4. Implementation Reference
- **Orchestrator**: `scripts/run_meta_pipeline.py`
- **Builder**: `scripts/build_meta_returns.py`
- **Optimizer**: `scripts/optimize_meta_portfolio.py`
- **Flattener**: `scripts/flatten_meta_weights.py`
- **Reporter**: `scripts/generate_meta_report.py`
