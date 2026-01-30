# Audit Note: Recent Smokes (Strict Scoreboard) — Jan 5, 2026

This note consolidates strict-scoreboard-oriented learnings across the most recent tournament smoke runs, with emphasis on:

- **Institutional correctness**: audit ledger completeness, reproducibility, and “no missing:* due to instrumentation.”
- **Strict gating behavior**: which gates dominate and why strict candidates are empty vs non-empty.
- **Calibration targets**: which metrics now dominate once temporal fragility is stabilized via longer windows.

## Runs Included

| Run ID | Windowing (train/test/step) | Scoreboard Rows | Strict Candidates | Notes |
| --- | --- | ---:| ---:| --- |
| `20260105-011037` | `120/20/20` | 54 | 0 | Constrained production-parity sweep; baseline rows missing `selection_jaccard` **at the time** (no baseline optimize weight payloads). |
| `20260105-154839` | `120/20/20` | 15 | 0 | Baseline optimize weights instrumented; candidates still empty due to fragility/friction/af gates. |
| `20260105-174600` | `120/20/20` | 92 | 12 | Regime semantics fields validated; strict candidates non-empty; parity gate dominates vetoes. |
| `20260105-180000` | `180/40/20` | 92 | 46 | Larger windows materially reduce fragility; baseline rows still present but fail `af_dist` (negative) → not candidates. |
| `20260105-191332` | `180/40/20` | 27 | 3 | Default-windowing production-parity mini-matrix; strict candidates non-empty under defaults; `af_dist` is the dominant veto. |
| `20260105-170324` | `180/40/20` | 15 | 0 | Early stability probe; `missing:af_dist` dominated (pre tail-sufficiency fix). |
| `20260105-201357` | `180/40/20` | 27 | 12 | Stability-default production-parity mini-matrix under institutional `min_af_dist=-0.20`; baseline `benchmark` appears as an anchor candidate. |

Supporting audit note for the windowing/regime effect:
- `docs/specs/audit_smoke_regime_windowing_20260105_174600_vs_180000.md`
- `docs/specs/audit_smoke_production_defaults_20260105_191332.md` (defaults-driven `180/40/20`, strict candidates non-empty)

## Audit Ledger Integrity (Run-Scoped, No Gaps)

All runs above are ledger-complete for optimize/simulate steps (no silent intent→no-outcome gaps):

- `20260105-011037`: `backtest_optimize intent=132 / success=132` (11 windows)
- `20260105-154839`: `backtest_optimize intent=55 / success=55` (11 windows)
- `20260105-174600`: `backtest_optimize intent=253 / success=253` (11 windows)
- `20260105-180000`: `backtest_optimize intent=161 / success=161` (7 windows; overlapping tests)

Implication:
- Selection stability metrics (`selection_jaccard`, HHI) are meaningful for strategies **when** `data.weights` exists.
- Missing selection stability is now treated as an **instrumentation bug** (unless a specific run predates the fix).

## Strict Gate Veto Distribution (What Dominates)

Counts below come from `candidate_failures` in each run’s `data/tournament_scoreboard.csv`.

### Run `20260105-011037` (0/54 candidates)
Dominant vetoes:
- `temporal_fragility` (54/54)
- `af_dist` (48/54)
- `friction_decay` (30/54)
- `stress_alpha` (30/54)
- `sim_parity` (21/54)
- `missing:selection_jaccard` (18/54; baseline rows only, pre-fix)

### Run `20260105-154839` (0/15 candidates)
Dominant vetoes:
- `temporal_fragility` (15/15)
- `af_dist` (12/15)
- `friction_decay` (9/15)
- `stress_alpha` (9/15)
- `sim_parity` (6/15)

### Run `20260105-174600` (12/92 candidates)
Dominant vetoes:
- `sim_parity` (76/92)
- `temporal_fragility` (23/92)
- `beta` (20/92; profile-specific to `min_variance`)
- `friction_decay` (20/92)

Interpretation:
- Under `120/20/20`, parity gating is the dominant exclusion once other missing-data issues are resolved.

### Run `20260105-180000` (46/92 candidates)
Dominant vetoes:
- `af_dist` (26/92)
- `beta` (12/92)
- `sim_parity` (12/92)
- tail multipliers: `cvar_mult` (8/92), `mdd_mult` (7/92)

Interpretation:
- Once the `temporal_fragility` driver is reduced by larger test windows, **antifragility distribution** (`af_dist`) becomes the dominant gate.

### Run `20260105-191332` (3/27 candidates)
Dominant vetoes:
- `af_dist` (24/27)
- tail multipliers and stress: `stress_alpha` (3/27), `cvar_mult` (3/27), `mdd_mult` (3/27)

Interpretation:
- Under stability-default windowing exercised via manifest/code defaults (no explicit window overrides), the strict gate stack is functional (non-empty candidates), but `af_dist` becomes the near-universal exclusion criterion for non-`hrp` rows in this mini-matrix.

### Run `20260105-170324` (0/15 candidates)
Dominant vetoes:
- `missing:af_dist` (15/15)

Interpretation:
- This run predates the antifragility distribution tail-sufficiency fix; all rows report `antifragility_dist.is_sufficient=false` (tail size 8) and are treated as missing `af_dist` by the strict scoreboard.

### Run `20260105-201357` (12/27 candidates)
Dominant vetoes:
- `af_dist` (15/27)
- `cvar_mult` (3/27)

Interpretation:
- With institutional default `min_af_dist = -0.20`, strict candidates expand materially in the stability-default mini-matrix.
- Baseline `benchmark` becomes eligible (anchor candidate behavior) while baseline `market` remains excluded by `af_dist`.

## Baseline Rows: Presence vs Eligibility

Institutional rule (current):
- Baseline rows must be present in the scoreboard and must not fail due to missing instrumentation (`missing:*`).
- Baselines may legitimately fail strict gates (they are reference rows, not automatically “robust candidates”).

Observed:
- `20260105-174600`: baseline candidates exist (8/12 baseline rows pass strict gates).
- `20260105-180000`: baseline rows fail `af_dist` (negative `af_dist` for `market/market` and `market/benchmark`), and `raw_pool_ew` also fails tail multipliers → **0 baseline candidates**.
- `20260105-191332`: baseline rows remain present and audit-complete but fail `af_dist` (negative for `market`/`benchmark`, very negative for `raw_pool_ew`) → **0 baseline candidates**.

This is consistent with “baselines are diagnostic anchors”; it also surfaces a calibration question:
- Should baselines have separate threshold expectations, or remain non-candidate references?

## Actionable Issues (Rescheduled)

1. **Downstream regime consumer migration**
   - Ensure downstream forensics/reporting reads `decision_*` fields and treats `windows[].regime` as legacy.
2. **Calibration: `af_dist` dominance under `180/40/20`**
   - Decide whether negative `af_dist` for baselines is expected (valid “fragile” signal) or indicates a metric definition mismatch for baseline series.
   - Deep dive: `docs/specs/audit_iss002_af_dist_dominance_20260105.md` (component breakdown + threshold sensitivity on `20260105-191332`).
   - Policy decision: institutional strict default is now `min_af_dist = -0.20` (see `docs/specs/iss002_policy_decision_20260105.md`).
3. **Parity gate realism**
   - When parity becomes the top veto (`sim_parity`), prioritize investigating whether:
     - Nautilus modeling differs materially from CVXPortfolio (expected), or
     - friction / cash / execution assumptions are mismatched (bug).

Tracking:
- `docs/specs/plan.md` (Rescheduled Queue + per-run deep audit entries)
