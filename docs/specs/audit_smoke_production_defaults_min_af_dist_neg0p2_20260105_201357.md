# Audit Note: Production-Parity Mini Matrix (Defaults = `180/40/20`, `min_af_dist=-0.20`) — Run `20260105-201357`

This smoke validates that:

1. The stability-default windowing (`train/test/step = 180/40/20`) is exercised by the tournament orchestrator (Grand 4D).
2. The newly adopted institutional strict-scoreboard default `min_af_dist = -0.20` is applied by the scoreboard, yielding **non-empty strict candidates** and allowing baseline `benchmark` to appear as an **anchor candidate** when it meets gates.

Policy references:
- ISS-002 decision record: `docs/specs/iss002_policy_decision_20260105.md`
- ISS-002 research deep dive: `docs/specs/audit_iss002_af_dist_dominance_20260105.md`

---

## Run

- Run: `20260105-201357`
- Matrix: `v3.2 / window / engines custom,skfolio / profiles market,hrp,barbell / simulators custom,cvxportfolio,nautilus`
- Windowing (from `audit.jsonl` context): **`180/40/20`**

Artifacts:
- Tournament payload: `artifacts/summaries/runs/20260105-201357/grand_4d_tournament_results.json`
- Scoreboard: `artifacts/summaries/runs/20260105-201357/data/tournament_scoreboard.csv`
- Candidates: `artifacts/summaries/runs/20260105-201357/data/tournament_candidates.csv`
- Markdown report: `artifacts/summaries/runs/20260105-201357/reports/research/tournament_scoreboard.md`
- Log: `artifacts/summaries/runs/20260105-201357/logs/grand_4d_tournament.log` (written by Grand 4D)
- Ledger: `artifacts/summaries/runs/20260105-201357/audit.jsonl` (hash chain verified)

Scoreboard thresholds (from `tournament_scoreboard.md`):
- `min_af_dist`: **`-0.2`** (institutional default)
- `max_temporal_fragility`: **`2.7530`** (auto-calibrated, `runs=8 pctl=95 margin=0.25`)

---

## Strict Scoreboard Outcome

- Scoreboard rows: **27**
- Strict candidates: **12**

Candidate composition:
- `custom/barbell`: 3 (all simulators)
- `custom/hrp`: 3 (all simulators)
- `skfolio/hrp`: 3 (all simulators)
- baseline `market/benchmark`: 3 (all simulators) — **anchor candidate behavior**

Dominant vetoes (`candidate_failures`):
- `af_dist`: **15/27**
- `cvar_mult`: **3/27**

Interpretation:
- The new `min_af_dist=-0.20` default materially expands strict candidates vs the prior `min_af_dist=0.0` runs by admitting “slightly-negative-skew but otherwise robust” configurations (notably barbell).
- Baseline `market` remains excluded by `af_dist` (consistent with its stability-window signature around `-0.55..-0.60`).

---

## Baseline Rows (Policy Check)

Baseline rows present: **9** (`engine=market`, profiles `market/benchmark/raw_pool_ew` × 3 simulators)

Baseline candidates:
- `benchmark`: **3** (eligible anchor candidate; passes full strict gate stack under `min_af_dist=-0.20`)
- `market`: **0** (fails `af_dist`)
- `raw_pool_ew`: **0** (fails `af_dist` and tail risk via `cvar_mult > 1.25`; calibration-first baseline)

This matches the baseline semantics in `docs/specs/iss002_policy_decision_20260105.md`:
- baseline `benchmark` is allowed to pass strict gates and may be treated as an expected anchor candidate.
- `raw_pool_ew` remains calibration-first but valid if it passes.

---

## Audit Notes / Known Deviations

These did not block tournament completion or scoreboard generation, but are recorded for audit completeness:

- `make data-audit STRICT_HEALTH=1` failed due to **`BINANCE:LUNCUSDT` STALE** in the selected universe (last date `2026-01-02`), so strict-health “freshness” enforcement did not pass for this run.
- `audit.jsonl` includes an early `metadata_coverage` failure event from an initial `port-select` attempt before running `make data-fetch LOOKBACK=60`; the subsequent `data-fetch` + `port-select` produced a valid selected universe and the tournament completed successfully.

---

## Next Action

If this policy is considered validated, the next strict-scoreboard bottleneck to address is:
- **ISS-005 — Friction alignment (`friction_decay`)** and/or **ISS-001 — Parity gate realism**, depending on which veto dominates in broader stability-default matrices after this `min_af_dist` change.

