# Specification: Universe Selection 2.0 (CARS)

This document defines the selection standard implemented by **SelectionEngineV2**.

## 1. Scoring Model: Composite Alpha-Risk Scoring (CARS 2.0)

Unlike the multiplicative model in 3.0, Selection 2.0 uses an **additive** scoring model based on cross-sectional ranks:

$$ \text{Score} = 0.4 \times \text{MomentumRank} + 0.2 \times \text{StabilityRank} + 0.2 \times \text{AntifragilityRank} + 0.2 \times \text{LiquidityRank} - 0.1 \times \text{FragilityRank} $$

### Key Properties:
- **Rank-Based**: Scores are normalized to [0, 1] percentiles before weighting.
- **Compensation**: High performance in one category (e.g., Alpha) can offset weaknesses in another (e.g., higher risk), provided it doesn't fail hard health gates.
- **Gate Integration**: Respects forensic health gates but lacks the advanced numerical stability and execution vetoes of version 3.0.

## 2. Triple-Gate Architecture (Legacy Implementation)

## 3. Dynamic Cluster Sizing

The number of winners selected per cluster ($N_c$) scales inversely with cluster density:
$$ N_c = \max(1, \text{round}(\text{base\_n} \times (1 - \rho_{\text{cluster}}))) $$
where $\rho_{\text{cluster}}$ is the mean pairwise correlation. This forces deeper selection in diversified clusters and prevents redundancy in tight ones.

## 4. Implementation Path (14-Step Production Lifecycle)

1.  **Cleanup**: Reset transient state (`make clean-daily`).
2.  **Discovery**: Run multi-engine scanners (`make scan-all`).
3.  **Aggregation**: Build the raw pool with `select_top_universe.py --mode raw`.
4.  **Lightweight Prep**: Fetch 60d history for forensic audit.
5.  **Forensic Risk Audit**: Execute `audit_antifragility.py` (Gate 1 & Gate 2 metrics).
6.  **Natural Selection**: Apply CARS 2.0 filtering with `natural_selection.py`.
7.  **Enrichment**: Add fundamental/metadata context.
8.  **High-Integrity Alignment**: Fetch 500d history for final candidate set.
9.  **Health Audit**: Verify survival through the high-fidelity stretch.
10. **Factor Analysis**: Map clusters and correlations.
11. **Regime Detection**: Switch profiles based on market environment.
12. **Optimization**: Compute final weights via `optimize_clustered_v2.py`.
13. **Validation**: Run backtest tournament.
14. **Reporting & Audit**: Finalize documentation and verify cryptographic ledger.

