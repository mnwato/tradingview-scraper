# Policy Decision: ISS-002 — `min_af_dist` Default + Baseline Semantics (Jan 5, 2026)

This document records the institutional policy decision for strict-scoreboard issue **ISS-002** (`af_dist` dominance under stability-default windowing).

Scope:
- Strict-scoreboard eligibility policy for `af_dist` (distribution antifragility gate).
- Baseline semantics for `market`, `benchmark`, and `raw_pool_ew` under strict gating.
- Feature-flag roadmap for a future runtime auto-calibrated `min_af_dist`.

Primary research note:
- `docs/specs/audit_iss002_af_dist_dominance_20260105.md`

Tracking:
- `docs/specs/plan.md` (ISS-002 section)

---

## Decision 1 — Fixed Institutional Default: `min_af_dist = -0.20`

**Decision**:
- Set strict-scoreboard default `min_af_dist` to **`-0.20`**.

Rationale:
- `af_dist` is empirically **skew-dominated** in stability-default runs; `min_af_dist=0` is therefore effectively a hard “positive skew required” gate.
- In a production-parity default-window mini-matrix (`20260105-191332`), barbell-like profiles can fail only `af_dist` when `min_af_dist=0`, despite passing the rest of the strict gate stack; relaxing to `≈ -0.2` admits these barbell candidates.
- Baseline `market` exhibits a stable antifragility signature around `af_dist ≈ -0.55..-0.60` in stability-default runs; using `-0.20` remains strict enough to keep baseline `market` excluded under normal conditions.

Implementation:
- Default threshold is set in `scripts/research/tournament_scoreboard.py` (`CandidateThresholds.min_af_dist = -0.20`).

---

## Decision 2 — Baseline Semantics Under Strict Gating

Baseline policy:
- Baselines are always required to be present and audit-complete (no `missing:*` due to instrumentation).
- Baselines are not guaranteed to pass strict gates.
- If a baseline **does** pass strict gates, it is a valid strict candidate (not structurally excluded).

Specific interpretations:

### `market` baseline
- Allowed to pass strict gates if it meets them, but typically expected to fail antifragility (`af_dist`) in most regimes.
- If `market` passes under the strict gate stack, treat it as a strong “strategy indistinguishable from baseline” signal and review (not necessarily a bug).

### `benchmark` baseline (expected anchor candidate)
- `benchmark` is explicitly allowed to be a strict candidate when it meets gates.
- Under `min_af_dist≈-0.2`, `benchmark` becoming eligible is an **acceptable and expected** outcome (“anchor candidate”).
- **Ranking semantics**: even when eligible, treat `benchmark` as a **reference anchor row** in downstream ranking (do not let it displace “top strategy” slots by default).
  - Implementation: scoreboard outputs include `is_baseline` + `baseline_role`, and the markdown report separates non-baseline candidates from baseline reference rows.

### `raw_pool_ew` baseline (calibration-first)
- `raw_pool_ew` is primarily treated as a calibration signal for fragility/tail risk.
- If it passes strict gates, it is valid (no structural exclusion).

---

## Decision 3 — Future Auto-Calibration (Feature-Flagged, Not Default)

Decision:
- Keep the institutional default **fixed** (`min_af_dist = -0.20`) for determinism and auditability.
- Add a **feature-flagged** path for a future runtime auto-calibrated `min_af_dist` derived from “latest N runs”.

Feature flag (reserved):
- `TV_FEATURES__FEAT_SCOREBOARD_AF_DIST_AUTOCALIB=1`

Status:
- This feature flag is **not enabled by default**.
- If implemented, it must be fully auditable:
  - anchor set definition (e.g., strategies-only vs benchmark-only),
  - run IDs used,
  - percentile and margin,
  - final `min_af_dist` applied (written into `tournament_scoreboard.md`).

---

## Validation Expectations

When applying `min_af_dist = -0.20`:
- Strict candidates should remain non-empty under stability-default (`180/40/20`) in production-parity mini-matrices.
- `benchmark` may appear as an eligible strict candidate; this is acceptable.
- `market` should remain excluded under normal conditions (unless other changes cause its `af_dist` signature to shift materially).
- `raw_pool_ew` will often remain excluded due to tail multipliers / stress gates; treat it as calibration-first but valid if it passes.

Validation evidence:
- Run `20260105-201357` (production-parity mini-matrix, stability-default `180/40/20`) produced 12/27 strict candidates under `min_af_dist=-0.20`, including baseline `benchmark` as an anchor candidate; see `docs/specs/audit_smoke_production_defaults_min_af_dist_neg0p2_20260105_201357.md`.
