# Implementation Plan: Universe Selection 3.0

## Phase 1: The Darwinian Audit (Week 1)
1.  **Config**: Create `configs/legacy/stress_calendar.yaml` with the defined extinction events.
2.  **Logic**: Update `audit_antifragility.py` to calculate the `Regime_Survival_Score`.
3.  **Verification**: Ensure that assets launched AFTER 2024-08 are flagged as "Untested/High Risk".

## Phase 2: MPS Integration (Week 1)
1.  **Utility**: Implement `tradingview_scraper/utils/scoring.py:calculate_mps_score`.
2.  **Pruning**: Refactor `natural_selection.py` to use MPS.
3.  **Backtest Tournament**: Compare the "V3 Selected" universe vs. "V2 Selected" universe using the existing tournament loop.

## Phase 3: Entropy Diversification (Week 2)
1.  **Research**: Implement a prototype in `scripts/research_entropy_map.py` using `scikit-learn` (Mutual Information).
2.  **Clustering**: Replace Ward Linkage with Mutual Information distance if results show better "Regime Stability" (lower cluster drift).

## Phase 4: Capacity Shield (Week 2)
1.  **Logic**: Inject $AUM / ADV$ penalty into the `Liquidity_Efficiency` component of MPS.
2.  **Final Polish**: Update `scripts/run_production_pipeline.py` to reflect the V3 logic.
