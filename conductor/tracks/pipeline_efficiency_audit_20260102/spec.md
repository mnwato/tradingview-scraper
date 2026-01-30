# Spec: Pipeline Efficiency & Scoring Consolidation

## 1. Goal
Remove redundant alpha scoring and pruning logic in the early Discovery stages. Centralize all performance-based decisions in the **Natural Selection (Log-MPS 3.2)** engine to prevent "Double Filtering" and "Factor Drift."

## 2. Structural Changes
### 2.1 Discovery Consolidation (`select_top_universe.py`)
- **Old**: Calculated a weighted `_alpha_score` and truncated the universe to 80.
- **New**: Focuses on **Venue Selection**. If the same asset (e.g. BTC) appears across multiple exchanges or products (Spot vs Perp), it selects the one with the highest **Value.Traded** (Liquidity).
- **Expansion**: Passes up to **200 unique assets** to the next stage to allow for deeper statistical clustering.

### 2.2 Strict Data Provenance (`prepare_portfolio_data.py`)
- **Old**: Had fallback logic to scan the `export/` directory if the candidate manifest was missing.
- **New**: Strict dependency on the consolidated candidate file. This ensures that only "Sanctioned Identities" enter the expensive historical loading phase.

### 2.3 Unit of Selection (The Identity)
- Downstream Selection (Stage 6) should always group by **Identity** (e.g. `BTC`) to ensure that even if multiple venues survive the Consolidator, only the single best statistical instance survives the Final Gate.

## 3. Success Criteria
- Removal of `_alpha_score` calculation from `select_top_universe.py`.
- 100% elimination of legacy folder-scanning in `prepare_portfolio_data.py`.
- Pass-through rate of ~200 assets from Discovery to Natural Selection.
