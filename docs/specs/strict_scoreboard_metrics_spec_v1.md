# Strict Scoreboard Metrics Specification (v1)
**Status**: Formalizing
**Date**: 2026-01-05

This document standardizes the definitions, provenance, and interpretation of metrics emitted by:
- `scripts/research/tournament_scoreboard.py`

Primary artifacts:
- `artifacts/summaries/runs/<RUN_ID>/data/tournament_scoreboard.csv`
- `artifacts/summaries/runs/<RUN_ID>/data/tournament_candidates.csv`
- `artifacts/summaries/runs/<RUN_ID>/reports/research/tournament_scoreboard.md`

Scope:
- Metric definitions and how they are computed.
- Required upstream artifacts for each metric.
- Known failure modes and audit expectations.

Non-goals:
- Choosing gate thresholds (policy lives in `CandidateThresholds` defaults + dated policy docs).
- Defining new gates beyond the current strict scoreboard.

Related specs:
- `docs/specs/benchmark_standards_v1.md` (institutional gates + runbooks)
- `docs/specs/iss002_policy_decision_20260105.md` (min_af_dist policy)
- `docs/specs/selection_jaccard_v1.md` (selection stability provenance)

---

## 1) Row Identity

A scoreboard row represents a single evaluated configuration for a specific simulator:
- `(selection, rebalance, simulator, engine, profile)`

Where:
- `selection`: selection mode identifier (e.g., `v3.2`)
- `rebalance`: rebalance mode identifier (e.g., `window`)
- `simulator`: simulation implementation (e.g., `custom`, `cvxportfolio`, `nautilus`)
- `engine`: portfolio construction engine (e.g., `skfolio`, `custom`, `market`)
- `profile`: portfolio/risk profile (e.g., `hrp`, `barbell`, `benchmark`)

The strict scoreboard determines a boolean eligibility flag:
- `is_candidate` (strict eligibility decision)
- `candidate_failures` (semicolon-separated veto reasons, including `missing:<metric>` markers)

---

## 2) Baseline Semantics in Scoreboard Outputs

Baseline rows are identified as:
- `engine == "market"` and `profile in {"market","benchmark","raw_pool_ew"}`

The scoreboard emits:
- `is_baseline` (bool)
- `baseline_role` (string; `anchor|baseline|calibration`)
  - `benchmark` → `anchor` (reference row; eligible if it passes strict gates)
  - `market` → `baseline` (market reference; may pass/fail)
  - `raw_pool_ew` → `calibration` (calibration-first; valid if it passes)

Ranking policy:
- Baselines are not structurally excluded from `tournament_candidates.csv`, but they must be treated as reference rows in downstream ranking (see `docs/specs/benchmark_standards_v1.md`).

---

## 3) Performance Metrics (Direct from Tournament Summaries)

These are read from the tournament results payload (per-window aggregation already computed by the backtest framework):
- `avg_window_sharpe`
- `annualized_return`
- `annualized_vol`
- `max_drawdown`
- `cvar_95`
- `avg_turnover`

Provenance:
- `grand_4d_tournament_results.json` or `tournament_results.json` embedded per `(simulator, engine, profile)`

Notes:
- These metrics are not strict gates by themselves, but many strict gates are derived from them (e.g., tail multipliers, parity).

---

## 4) Robustness & Stability Metrics

### 4.1 Temporal Fragility (`temporal_fragility`)
Definition:
- Coefficient of variation (CV) of window Sharpe:
  - `temporal_fragility = std(sharpe_windows) / abs(mean(sharpe_windows))`
  - If `abs(mean) < 1e-9`, the metric returns `0.0` (guard against blow-ups).

Provenance:
- `windows[].sharpe` values from tournament results payload.

Interpretation:
- High values indicate instability / sign-flips / high variance across windows.
- 20-day windows are naturally more fragile than 40-day windows; gate calibration must be window-aware.

Known failure mode:
- Near-zero mean Sharpe can cause CV blow-ups. The current implementation returns 0.0 in that degenerate case, so “extreme fragility” in the scoreboard implies the mean is not ~0 but the variability is very large.

### 4.2 Selection Stability (`selection_jaccard`)
Definition:
- Average Jaccard similarity of selected asset sets between consecutive windows.

Provenance:
- `audit.jsonl` `backtest_optimize` success outcomes must include `data.weights`.
- The scoreboard extracts per-window winner sets from weights and computes:
  - `selection_jaccard = mean_{t}( Jaccard(winners_t, winners_{t-1}) )`

Interpretation:
- Higher values mean more stable membership across windows.
- Very low values indicate high churn in selection membership (potentially unstable behavior).

Audit expectation:
- Missing selection stability metrics (`missing:selection_jaccard`) should be treated as an instrumentation failure unless the run is explicitly legacy/backfill.

Reference:
- `docs/specs/selection_jaccard_v1.md`

### 4.3 Concentration (`hhi`, `max_weight`, `n_assets`)
Definitions:
- `HHI = sum_i w_i^2` (per-window), then averaged across windows.
- `max_weight`: average of maximum single-asset weight across windows.
- `n_assets`: average number of non-zero weights across windows.

Provenance:
- Same as selection stability: `audit.jsonl` `backtest_optimize` outcomes with weights.

Interpretation:
- Higher HHI and max_weight imply more concentrated portfolios.
- These are currently diagnostics (not all are hard strict gates), but they are critical for risk review.

---

## 5) Antifragility Metrics

### 5.1 Distribution Antifragility (`af_dist`)
Definition (from distribution shape):
- `af_dist = skew(daily_returns) + log(tail_asym + eps)`
- where:
  - `tail_asym = mean(right_tail) / (abs(mean(left_tail)) + eps)`
  - tails are defined by quantile `q` (default `q=0.95`)
  - tail sufficiency uses an effective minimum tail size coherent with sample size.

Provenance:
- `summary.antifragility_dist.af_dist` from tournament summary.

Interpretation:
- Often skew-dominated; `min_af_dist = 0` is effectively a “positive skew required” gate.

Policy note:
- Institutional default for strict gating is `min_af_dist = -0.20` (see `docs/specs/iss002_policy_decision_20260105.md`).

### 5.2 Stress Antifragility (`stress_alpha`, `stress_delta`, `stress_ref`)
Definition:
- Stress-response metrics computed by the backtest framework and stored in tournament summaries.
  - `stress_alpha`: excess performance in stress windows vs reference
  - `stress_delta`: raw difference vs reference
  - `stress_ref`: which reference baseline was used (e.g., `market`)

Provenance:
- `summary.antifragility_stress.*` from tournament summary.

Interpretation:
- Ensures candidates survive crisis-like regimes and do not rely on benign windows only.

---

## 6) Cross-Simulator Fidelity Metrics

### 6.1 Friction Alignment (`friction_decay`)
Definition:
- “Sharpe decay” from idealized simulator → high-fidelity simulator:
  - `friction_decay = 1 - (sharpe_real / sharpe_ideal)`

Implementation convention:
- In current scoreboard implementation, `sharpe_ideal` and `sharpe_real` are sourced by pivoting the per-row `avg_window_sharpe` across simulators and comparing specific simulator pairs when present.

Interpretation:
- Higher values indicate a larger drop when moving to the more realistic simulator (potentially overfit or friction-sensitive behavior).

### 6.2 Simulator Parity (`parity_ann_return_gap`)
Definition:
- Absolute difference in annualized return between `cvxportfolio` and `nautilus`:
  - `abs(annualized_return_cvx - annualized_return_nautilus)`

Provenance:
- Requires both simulators to have produced rows for the same `(selection, rebalance, engine, profile)`.

Interpretation:
- Measures cross-simulator consistency.
- If only one simulator is present, parity is not computed and must not be treated as pass/fail.

---

## 7) Tail-Risk Multipliers (Relative to Baseline `market`)

These metrics compare a strategy row’s tail risk to the baseline market row for the same simulator:
- `cvar_mult = abs(cvar_95_row) / (abs(cvar_95_market) + eps)`
- `mdd_mult = abs(max_drawdown_row) / (abs(max_drawdown_market) + eps)`

Provenance:
- `cvar_95` and `max_drawdown` in tournament summaries.
- baseline is taken from `engine=market, profile=market` within the same simulator bucket.

Interpretation:
- Values > 1 imply worse tail risk than baseline market.

---

## 8) Market Sensitivity (`beta`, `corr`)

Definition:
- `beta` and `corr` against the baseline market return stream.

Provenance preference:
1. **Daily returns pickles**: `data/returns/<sim>_<engine>_<profile>.pkl`
2. Fall back to **per-window returns series** (windows’ `returns` field) if daily series are missing.

Implementation note:
- Overlapping windows can create duplicate timestamps in stitched daily series; the scoreboard deduplicates by keeping the last value.

Interpretation:
- Beta and correlation help classify exposures (e.g., min-variance should not have high beta).

---

## 9) Candidate Thresholds and Auditability

Strict gates are implemented in `scripts/research/tournament_scoreboard.py`:
- `CandidateThresholds` defaults are the “institutional baseline”.
- Some thresholds may be auto-calibrated (currently `max_temporal_fragility` may be derived from baseline percentiles across recent runs).

Audit expectation:
- Any auto-calibrated threshold must be printed into the markdown report (runs used, percentile, margin, cutoff policy).

