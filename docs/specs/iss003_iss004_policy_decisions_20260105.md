# Policy Decisions: Baseline Semantics (ISS-003) + Windowing Defaults (ISS-004) — Jan 5, 2026

This note closes two strict-scoreboard policy ambiguities:

- **ISS-003**: baseline row expectations (presence vs eligibility)
- **ISS-004**: windowing defaults (stability-default vs fragility stress test)

It is grounded in observed behavior from recent smokes and is intended to be the canonical policy reference for 2026 Q1 work.

## Evidence Runs (Strict Scoreboard)

Key runs used for policy grounding:

- `20260105-174600` (`train/test/step = 120/20/20`)
  - Total candidates: **12 / 92**
  - Baseline candidates: **8 / 12** baseline rows
- `20260105-180000` (`train/test/step = 180/40/20`, overlapping tests)
  - Total candidates: **46 / 92**
  - Baseline candidates: **0 / 12** baseline rows (baseline rows fail `af_dist` / tail multipliers in this run)

Supporting audit notes:
- `docs/specs/audit_recent_smokes_strict_scoreboard_20260105.md`
- `docs/specs/audit_smoke_regime_windowing_20260105_174600_vs_180000.md`

## Decision: ISS-003 — Baselines Are Reference Rows (Presence Required; Eligibility Not Guaranteed)

### Policy

1. **Baselines must always appear in the scoreboard**
   - Baseline profiles: `market`, `benchmark`, `raw_pool_ew` (engine `market`).
2. **Baselines must be audit-complete**
   - No strict gating failures due to missing instrumentation (e.g., no `missing:selection_jaccard` because `backtest_optimize` weight dumps are absent).
3. **Baselines are not guaranteed to pass strict gates**
   - Baselines may legitimately fail strict gates (e.g., `af_dist` negative) and therefore may be absent from `tournament_candidates.csv`.
   - Baselines are diagnostic anchors and calibration references, not automatically “robust candidates.”

### Rationale

- In `20260105-180000`, strict candidates are non-empty (**46**), but baselines are not candidates (**0**) due to `af_dist` and tail multiplier vetoes.
- Treating baselines as “must-pass” would conflate baseline diagnostic intent with candidate eligibility and would force broad gate exemptions.

### Implications

- “Strict candidates must be non-empty” does **not** mean “baseline candidates must exist.”
- If a baseline-exemption policy is desired, it must be:
  - explicitly scoped (which gates are exempted, for which baseline rows),
  - documented in specs, and
  - validated via dedicated smokes (because it changes institutional meaning of gates).

## Decision: ISS-004 — Two Windowing Modes (Stability Default vs Fragility Stress Test)

### Policy

Define two institutional windowing modes:

1. **Stability Default (Production-Parity Robustness Probe)**
   - `train/test/step = 180/40/20`
   - Purpose: reduce 20-day sign-flip dominated fragility; prioritize robust ranking and regime-aware stability.
   - Expected outcome: strict candidates are non-empty and gate dominance shifts away from `temporal_fragility`.

2. **Fragility Stress Test (Sign-Flip Amplifier)**
   - `train/test/step = 120/20/20`
   - Purpose: deliberately amplify short-window Sharpe polarity flips so temporal fragility is visible.
   - Expected outcome: higher `temporal_fragility` veto rates; used as a stress diagnostic, not the default production robustness view.

### Rationale

- `180/40/20` materially reduces sign-flip driven instability (see windowing comparison notes).
- `120/20/20` remains valuable as a diagnostic probe for strategies that only look good under short-window noise.

### Operational notes

- Overlapping windows (`test_window > step_size`) require duplicate-timestamp deduplication for daily-series metrics (already handled in scoreboard computations).
- Windowing should be overridden using Makefile knobs (`BACKTEST_TRAIN/BACKTEST_TEST/BACKTEST_STEP`) so settings propagate to `get_settings()` consumers.

### Default alignment

- The institutional stability-default windowing (`180/40/20`) is now the `configs/manifest.json` `defaults.backtest` baseline, so “production-parity” runs inherit it unless explicitly overridden.

## What This Unblocks (Next Work)

With ISS-003 and ISS-004 policy fixed:

- Parity gate (`sim_parity`) can be investigated without baseline-policy ambiguity.
- `af_dist` dominance under stability-default windows can be treated as a real calibration question rather than “why did baselines disappear?”
