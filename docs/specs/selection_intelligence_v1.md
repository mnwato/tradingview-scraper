# Specification: Selection Intelligence (V2)
**Status**: Formalized
**Date**: 2026-01-01

## 1. Overview
Selection Intelligence defines the logic for "Pruning" the raw discovered candidate pool into a high-quality implementation universe. It supports multiple logic versions to adapt to different market regimes and risk appetites, now benchmarked via the 4D Tournament Matrix.

## 2. Selection Strategy Versions

### 2.1 Additive Local (V2.0)
- **Logic**: Local normalization within clusters.
- **Renamed**: Formerly "legacy" (V1.0).
- **Goal**: Breadth and cluster-local leadership.

### 2.2 Additive Global (V2)
- **Model**: Composite Alpha-Risk Scoring (CARS 2.0).
- **Formula**: $0.4 \times Mom + 0.2 \times Stab + 0.2 \times AF + 0.2 \times Liq - 0.1 \times Frag$.
- **Behavior**: Compensatory logic where high momentum can offset moderate risk.

### 2.3 Additive Global (V2.1)
- **Model**: Tuned CARS (v2.1).
- **Refinement**: Optimized weights via Global Robust HPO and Multi-Method Normalization (Logistic/Z-score/Rank).
- **Status**: Champion (2026-01-02).

### 2.4 Multiplicative Probability Scoring (MPS 3.0 / V3)
- **Model**: Multiplicative Probabilities ($P_1 \times P_2 \times ...$).
- **Vetoes**: Hard gates for Survival (< 0.1), ECI (Cost), and Numerical Stability ($\kappa$).
- **ECI Estimation**: Uses a standardized 0.5% (0.005) daily volatility default when `Volatility.D` metadata is missing or `NaN`. This prevents punitive over-vetoing of assets with high alpha proxies but missing volatility metrics.
- **Behavior**: Non-compensatory "Darwinian" survival. Structural failure in any category results in immediate disqualification.

### 2.4 Alpha Standard (V3.1)
- **Status**: Validated (2026-01-01 Grand Tournament Top Performer).
- **Refinement**: Relaxed condition number thresholds ($10^{18}$) and lowered ECI hurdles (0.5%) to allow defensive breadth.
- **Predictability Filters**: Integrated asset-level "Operation Darwin" vetoes:
    - **Entropy Max**: $PE \le 0.9$ (Discard chaotic noise).
    - **Efficiency Min**: $ER \ge 0.1$ (Discard excessive chop).
    - **Hurst Zone**: Avoid $0.45 < H < 0.55$ (Discard pure random walks).

### 2.5 Log-MPS (V3.2)
- **Model**: Additive Log-Probabilities ($Score = \sum \omega_i \ln(P_i)$).
- **Weights**: Optimized via Global Robust HPO (Optuna).
- **Status**: **New Champion (2026-01-02)**.
- **Goal**: Numerical stability for automated tuning without losing "Darwinian" pruning intensity.
- **Breadth**: Optimized for `top_n=5` to leverage cluster-wide signals.

## 3. Integration with Risk Profiles (Tournament Dimensions)

| Spec Profile | Selection Engine | Target Profile | Rationale |
| :--- | :--- | :--- | :--- |
| **Darwinian** | `v3` | `hrp`, `min_variance` | Focuses on high-quality, numerically stable clusters for risk-parity engines. |
| **Aggressive** | `v3` | `max_sharpe` | Selects single leaders with the highest combined MPS for alpha-seeking profiles. |
| **Robust** | `v3` | `barbell`, `equal_weight` | Balanced V3 logic; allows more breadth while maintaining non-compensatory health gates. |

## 4. Selection Alpha Isolation

To quantify the value of the selection logic, the platform measures **Selection Alpha ($A_s$):**

$$ A_s = \text{Return}(\text{Filtered EW}) - \text{Return}(\text{Raw Discovery EW}) $$

This metric is archived in the **Immutable Audit Ledger** at each walk-forward step of the backtest.

### 4.1 Baseline Coupling Rules
- **`raw_pool_ew` scope**: Used only for selection alpha isolation; it must remain **selection-mode invariant** when the universe source is unchanged.
- **Universe separation**: Do **not** compare canonical vs selected `raw_pool_ew` as an invariance test; those are different universes by definition.
- **Risk profile comparisons**: Use `benchmark` as the default baseline when comparing risk profiles; use `market` for simulator calibration.
- **Selection alpha calculation**: Requires `raw_pool_ew` built from the **canonical** universe and `benchmark` built from the **selected** universe; if both baselines use the same universe, $A_s$ collapses toward zero by construction.

### 4.2 Selection Audit Requirements (Canonical → Selected)
To make selection alpha reproducible and reviewable, every selection run must emit a structured audit record and be archived with the run:
- **Canonical source**: `portfolio_candidates_raw.json` (raw pool) with `raw_pool_count` and `raw_pool_hash`.
- **Selected output**: `portfolio_candidates.json` with `selected_count` and `selection_hash`.
- **Selection mode + lookbacks**: `selection_mode` and `lookbacks_used` (e.g., `[60,120,200]`).
- **Cluster map**: cluster sizes and selected winners per cluster.
- **Vetoes**: rejected symbols and veto reasons (ECI/entropy/efficiency/Hurst, etc.).
- **Archival**: Persist `selection_audit.json` (or `.md`) in the run directory and link its hash in `audit.jsonl`.

**Update (Jan 2026)**: Tournament runs now log explicit per-window selection intents/outcomes in `audit.jsonl` via the `backtest_select` step. Continue to persist `selection_audit.json` for full selection provenance, but use `backtest_select` to confirm that Grand 4D selection-mode sweeps actually exercised dynamic selection (and did not silently skip due to symbol-format mismatches or all-veto winner collapse).

## 5. Natural Selection Contract (Spec)
For the concrete artifact contracts, audit expectations, and multi-venue expansion policy used by `scripts/natural_selection.py`, see:
- `docs/specs/natural_selection_spec_v1.md`
