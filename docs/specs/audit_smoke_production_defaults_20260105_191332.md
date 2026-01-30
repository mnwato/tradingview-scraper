# Audit Note: Production-Parity Mini Matrix (Defaults = 180/40/20) — Run `20260105-191332`

This smoke validates that the newly adopted **stability-default windowing** (`train/test/step = 180/40/20`) is actually exercised by the tournament orchestrator (Grand 4D), and that strict scoreboard candidates remain **non-empty** under the updated defaults.

## Run

- Run: `20260105-191332`
- Invocation: production-parity mini-matrix (v3.2 / window / engines `custom,skfolio` / profiles `market,hrp,barbell` / simulators `custom,cvxportfolio,nautilus`)
- Windowing (from `audit.jsonl` context): **`180/40/20`**

Artifacts:
- Tournament payload: `artifacts/summaries/runs/20260105-191332/grand_4d_tournament_results.json`
- Scoreboard: `artifacts/summaries/runs/20260105-191332/data/tournament_scoreboard.csv`
- Candidates: `artifacts/summaries/runs/20260105-191332/data/tournament_candidates.csv`
- Log: `artifacts/summaries/runs/20260105-191332/logs/grand_4d_tournament.log`
- Ledger: `artifacts/summaries/runs/20260105-191332/audit.jsonl` (hash chain verified)

## Strict Scoreboard Outcome

- Scoreboard rows: **27**
- Strict candidates: **3**
- Candidate composition: **all `skfolio/hrp`** (3 rows = 3 simulators)

Dominant vetoes (from `candidate_failures`):
- `af_dist`: **24/27** rows
- tail multipliers: `cvar_mult` **3**, `mdd_mult` **3**
- `stress_alpha`: **3**

Interpretation:
- Under stability-default windowing, **temporal fragility no longer dominates** this mini-matrix.
- The next strict-scoreboard bottleneck is clearly **`af_dist`**, which is consistent with earlier observations that `af_dist` becomes dominant once short-window sign flips are reduced.

## Baseline Rows (Policy Check)

- Baseline rows present: **9** (`engine=market`, profiles `market/benchmark/raw_pool_ew` × 3 simulators)
- Baseline candidates: **0**

Reason:
- Baselines fail `af_dist` (and `raw_pool_ew` also fails tail multipliers).

This matches the locked ISS-003 policy:
- Baselines are **reference rows** (presence + audit-complete required), not guaranteed strict candidates.

Policy reference:
- `docs/specs/iss003_iss004_policy_decisions_20260105.md`

## Orchestrator / Log Hygiene

- No Nautilus parity fallback warnings observed in the run log.
- No `skfolio hrp: cluster_benchmarks n=2 < 3; using custom HRP fallback.` warnings observed in the run log.

## Next Issue Focus

This smoke shifts the strict-scoreboard focus to:
- **ISS-002 — `af_dist` dominance under `180/40/20`** (definition + calibration + baseline expectations).

Deep dive note (component-level analysis + threshold sensitivity on this run):
- `docs/specs/audit_iss002_af_dist_dominance_20260105.md`

Baseline policy note:
- Baseline `benchmark` is allowed to be a strict candidate if it meets strict gates (no structural exclusion); see `docs/specs/audit_iss002_af_dist_dominance_20260105.md` “Policy Alignment (Baselines)”.
  - Policy decision record (Jan 2026): `docs/specs/iss002_policy_decision_20260105.md` (institutional default `min_af_dist = -0.20`).
