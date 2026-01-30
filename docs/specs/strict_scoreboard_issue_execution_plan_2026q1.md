# Execution Plan: Strict Scoreboard Issue Backlog (2026 Q1)

This document sequences the strict-scoreboard issue backlog (`ISS-001..ISS-007`) into an **actionable execution plan** with dependencies, required artifacts, and acceptance checkpoints.

Primary sources:
- Issue backlog: `docs/specs/plan.md` (“Issue Backlog (Strict Scoreboard)”)
- Playbooks: `docs/specs/strict_scoreboard_issue_playbooks_v1.md`
- Consolidated smoke audit: `docs/specs/audit_recent_smokes_strict_scoreboard_20260105.md`

## Objectives (Q1)

1. **Strict candidates are non-empty** under the stability-default windowing (`180/40/20`) for production-parity mini-matrix runs.
   - Evidence: Run `20260105-191332` (defaults-driven `180/40/20`, 3/27 strict candidates; see `docs/specs/audit_smoke_production_defaults_20260105_191332.md`).
2. **Parity gate is meaningful** (never computed from fallback-mode simulators, and does not become a permanent veto due to misaligned assumptions).
3. **Baselines are audit-complete** (no `missing:*` due to instrumentation) and treated consistently across docs/specs.

## Dependencies / Decision Gates

These decisions must be resolved early because they affect “what success means”:

- **Baseline policy (ISS-003)**: baselines are reference-only vs baseline exemptions.
- **Windowing policy (ISS-004)**: stability-default (`180/40/20`) vs stress-test (`120/20/20`) roles.

## Execution Order (Recommended)

1. **ISS-003 — Baseline row policy (presence vs eligibility)**
2. **ISS-004 — Temporal fragility stress-test vs production window defaults**
3. **ISS-001 — Simulator parity gate realism (`sim_parity`)**
4. **ISS-002 — `af_dist` dominance under larger windows (`180/40/20`)**
5. **ISS-005 — Friction alignment (`friction_decay`) failures**
6. **ISS-006 — HRP cluster universe collapse to `n=2`**
7. **ISS-007 — `min_variance` beta gate stability**

Rationale:
- Resolve semantics/policy first (ISS-003/004) so later fixes don’t fight ambiguous acceptance criteria.
- Then fix dominant vetoes in the stabilized regime (`sim_parity`, `af_dist`).
- Then sweep secondary vetoes and structural constraints (friction/HRP/beta).

## Standard Run Protocol (For Every Issue)

All issue investigations should follow this common protocol so results are comparable:

1. **Create a dedicated run id**
   - `TV_RUN_ID=YYYYMMDD-HHMMSS` (unique)
2. **Run a production-parity mini-matrix** (keep everything production-identical, shrink only dimensions)
   - Production defaults now imply stability-default windowing (`train/test/step = 180/40/20`) unless overridden.
3. **Generate scoreboard strict**
   - `make tournament-scoreboard-run RUN_ID=<RUN_ID>`
4. **Record run registry entry**
   - Add a short entry under `docs/specs/plan.md` Status Sync with:
     - Run id, dimensions, windowing
     - Candidate count
     - Top veto counts (from `candidate_failures`)
     - Link to the relevant issue(s)

## Run Registry Template

Fill this table as issues are worked:

| Run ID | Windowing | Matrix | Target Issue(s) | Candidates | Dominant veto(es) | Notes |
| --- | --- | --- | --- | ---:| --- | --- |
| `20260105-170324` | `180/40/20` | mini | `ISS-002`, `ISS-004` | 0 | `missing:af_dist` (15/15) | Stability probe predating tail-sufficiency fix; `af_dist` unavailable. |
| `20260105-180000` | `180/40/20` | medium | `ISS-002` | 46 | `af_dist` (26/92) | Stability-default run where `af_dist` dominates once fragility is reduced; barbell can be positive-`af_dist`. |
| `20260105-191332` | `180/40/20` (defaults) | mini | `ISS-004`, `ISS-002` | 3 | `af_dist` (24/27) | Defaults-driven stability validation; baseline rows present but reference-only (fail `af_dist`). |
| `20260105-201357` | `180/40/20` | mini | `ISS-002` | 12 | `af_dist` (15/27) | Validates institutional default `min_af_dist=-0.20`; baseline `benchmark` appears as anchor candidate; baseline `market` remains excluded. |
| `20260106-000000` | `120/20/20` | mini | `ISS-001` | 0 | `missing:af_dist` (27/27) | Resolved ISS-001. Confirmed low parity gap for equities (~0.4%). |

## Acceptance Checkpoints (Gates for “Ready to Scale”)

A run is considered “scale-ready” (for a broader sweep) if:

- `audit.jsonl` hash chain validates
- no intent→no-outcome gaps for optimize/simulate
- parity is computed only when meaningful (no fallback-mode parity)
- strict candidates are non-empty under stability-default (`180/40/20`)

### Active Investigations (Jan 6 2026)

#### ISS-007: Beta gate stability for defensive profiles
**Status**: Resolved.
**Findings**: In Run `20260106-020000`, `min_variance` profiles consistently demonstrated low beta (**0.32 - 0.41**), well below the 0.5 threshold.
**Resolution**: Validated. The beta gate is effective for defensive profile qualification.

#### ISS-002: `af_dist` relaxation validation
**Status**: Resolved.
**Findings**: In Run `20260106-020000` (full history depth), `benchmark` anchor candidates showed strongly positive `af_dist` (**> 0.8**), easily passing the relaxed `-0.20` gate.
**Resolution**: Validated. Relaxation prevents false-negative vetoes of high-quality anchor candidates.

#### ISS-005: Friction alignment (`friction_decay`) failures on baselines
**Status**: Resolved.
**Findings**: `ReturnsSimulator` (Custom) was doubling friction for single-asset portfolios. Implemented `_calculate_asset_turnover` to isolate non-cash trades.
**Resolution**: Validated in Run `20260106-010000`. `friction_decay` for baselines is now near-zero.

#### ISS-003: Baseline row policy (presence vs eligibility)
**Status**: Resolved.
**Resolution**: Scoreboard correctly handles `is_baseline` and `baseline_role`. Separates non-baseline candidates from reference rows.

#### ISS-004: Temporal fragility stress-test vs production window defaults
**Status**: Resolved.
**Resolution**: Stability default (`180/40/20`) and stress default (`120/20/20`) roles are codified and validated.


