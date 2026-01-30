# Specification: Window Rebalance Mode Review 2026

## 1. Overview
This track performs a targeted 4D tournament audit to validate the **Window Rebalance** mode. The objective is to determine if "Monthly Intelligence" (21d windows) is better served by a "Trade and Hold" (Window) strategy or a "Trade to Target" (Daily) strategy, specifically looking for the **Churn Penalty** crossover point and printing results in human-readable formats for validation.

## 2. Functional Requirements

### 2.1 The Churn Axis (Rebalance Matrix)
We will hold Step Size (`21d`) constant and vary the following:
1.  **Selection Modes**: `v2`, `v3`, `v3.1`, `v3_spectral`, `v3.1_spectral`.
2.  **Rebalance Modes**:
    - `Mode: Window`: Adjust weights only on Day 1 of the 21-day window.
    - `Mode: Daily`: Re-trade every day to keep target weights (High Churn).
    - `Mode: Daily + 5% Tolerance`: Re-trade only on >5% drift.

### 2.2 Essential 4D Permutations
- **Engines**: `custom`, `cvxportfolio`, `skfolio`.
- **Profiles (Essential + Baselines)**: 
    - `risk_parity`, `hrp`, `benchmark`, `equal_weight`.
    - **Baselines**: `benchmark_baseline`, `market_baseline`, `raw_pool_ew`.
- **Simulators**: `custom`, `nautilus`, `cvxportfolio`.

### 2.3 Reporting, Human-Readable Tables & Validation
- **Main Efficiency Table**: `rebalance_efficiency_rank.md` comparing rebalance modes sorted by Net Sharpe.
- **Churn Penalty Audit**: `churn_penalty_audit.md` quantifying implementation shortfall and cost savings.
- **Outlier Spotting**: Identify windows where "Window" mode significantly outperformed "Daily" (drift benefit).
- **Validation Printout**: A specialized script to print high-level comparison metrics directly to the terminal for rapid review.

## 3. Non-Functional Requirements
- **Contiguity**: Ensure `initial_holdings` persistence between windows to track cumulative turnover correctly.
- **Reproducibility**: All runs must be cryptographically signed in `audit.jsonl`.

## 4. Acceptance Criteria
- Full 2025 tournament results generated for all rebalance modes.
- Human-readable comparison table generated and printed to terminal.
- Production recommendation for rebalance policy finalized.
