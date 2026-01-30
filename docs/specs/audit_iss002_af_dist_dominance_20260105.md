# Audit Note: ISS-002 — `af_dist` Dominance Under Stability Windowing (`180/40/20`) — Jan 5, 2026

This note is a strict-scoreboard oriented deep dive into **ISS-002**:

- Under stability-default windowing (`train/test/step = 180/40/20`), once temporal fragility is stabilized, the **antifragility distribution gate** (`af_dist`) becomes the dominant veto.
- In small production-parity mini-matrices, `af_dist` can become a near-universal exclusion criterion (e.g., Run `20260105-191332`: `af_dist` vetoed **24/27** rows).

Primary artifacts (defaults-driven stability smoke):
- Run: `20260105-191332`
- Tournament payload: `artifacts/summaries/runs/20260105-191332/grand_4d_tournament_results.json`
- Scoreboard: `artifacts/summaries/runs/20260105-191332/data/tournament_scoreboard.csv`
- Report: `artifacts/summaries/runs/20260105-191332/reports/research/tournament_scoreboard.md`

Related context:
- Consolidated smokes: `docs/specs/audit_recent_smokes_strict_scoreboard_20260105.md`
- Production-parity default-windowing smoke audit: `docs/specs/audit_smoke_production_defaults_20260105_191332.md`
- Issue backlog + policy: `docs/specs/plan.md`, `docs/specs/iss003_iss004_policy_decisions_20260105.md`
- ISS-002 decision record: `docs/specs/iss002_policy_decision_20260105.md`

---

## Policy Alignment (Baselines)

This note assumes the following baseline rules (institutional strict-scoreboard oriented):

- **`market` baseline**: allowed to pass strict gates if it meets them, but it is expected to fail antifragility (`af_dist`) in most regimes; treating it as a candidate would be unusual and should be considered a strong signal.
- **`benchmark` baseline**: **allowed to pass strict gates** if it meets them; it is a legitimate strict candidate when it clears the threshold stack.
- **`raw_pool_ew` baseline**: primarily treated as a **calibration signal** (fragility / tail-risk stress reference), but **if it passes strict gates, it is valid** (no structural exclusion).

Implication for ISS-002:
- If `min_af_dist` is calibrated to `≈ -0.2`, baseline `benchmark` becoming eligible is an **acceptable** outcome and should be interpreted as “benchmark is not antifragile, but also not failing the antifragility floor.”

---

## 1) Definition: What `af_dist` Actually Measures

Source of truth:
- `tradingview_scraper/utils/metrics.py` (`calculate_antifragility_distribution`)

Definition:
- `tail_asym = mean(right_tail) / (abs(mean(left_tail)) + eps)` (when `mean(right_tail) > 0`, else `tail_asym = 0`)
- `af_dist = skew(daily_returns) + log(tail_asym + eps)`

Interpretation:
- `skew` captures whole-distribution asymmetry (very crash-sensitive).
- `log(tail_asym)` captures “right-tail gains vs left-tail losses” asymmetry (tail-slice sensitive).

Important empirical observation (Run `20260105-191332`):
- For baselines, **the sign and magnitude of `af_dist` is dominated by `skew`**, not by `log(tail_asym)`.

---

## 2) Evidence: Why Baselines Fail `af_dist` in Run `20260105-191332`

Baseline antifragility distribution components (custom simulator shown; other simulators are consistent in sign/magnitude):

### `market/market` (baseline)
- `af_dist ≈ -0.582`
- `skew ≈ -0.526` (dominant negative contributor)
- `tail_asym ≈ 0.945` → `log(tail_asym) ≈ -0.057`

### `market/benchmark` (baseline)
- `af_dist ≈ -0.001` (near-zero but still negative)
- `skew ≈ -0.147`
- `tail_asym ≈ 1.157` → `log(tail_asym) ≈ +0.146` (partially offsets skew)

### `market/raw_pool_ew` (baseline)
- `af_dist ≈ -3.437` (very negative)
- `skew ≈ -3.158` (dominant driver)
- `tail_asym ≈ 0.756` → `log(tail_asym) ≈ -0.280`

Implication:
- Under the current strict gate (`min_af_dist = 0`), **baselines are expected to be excluded** unless they exhibit positive skew and tail asymmetry strong enough to offset it.
- This is consistent with locked ISS-003 policy: baselines are **reference rows** (presence + audit-complete required), not guaranteed candidates.

---

## 3) Evidence: When Barbell Fails `af_dist` (Despite Having “Good Tails”)

Run `20260105-191332` (mini-matrix profiles `market, hrp, barbell`):
- `skfolio/hrp` is the only strict candidate family (3 rows / 3 simulators).
- `skfolio/barbell` fails **only** `af_dist` in this run (all other strict gates pass).

Component breakdown (typical values across simulators):
- `skfolio/barbell`: `tail_asym ≈ 1.062` → `log(tail_asym) ≈ +0.060`, but `skew ≈ -0.234` → `af_dist ≈ -0.174`

Interpretation:
- Barbell exhibits a “better right tail than left tail” signal (`tail_asym > 1`) but still has **negative skew** at the distribution level.
- With `af_dist = skew + log(tail_asym)`, the skew term dominates and keeps `af_dist < 0`, causing a strict veto.

This creates a policy tension:
- The barbell profile is conceptually the most “antifragility-seeking” profile, yet `min_af_dist = 0` can exclude it even when other antifragility gates (`stress_alpha`, tail multipliers) pass.

Counter-evidence (larger sweep, same stability windowing):
- In Run `20260105-180000` (also `180/40/20`, broader engine/profile grid), barbell rows have **positive** `af_dist` across engines (mean roughly `0.19..0.27` depending on engine), indicating barbell is **not inherently incompatible** with `min_af_dist = 0`.

Interpretation:
- Barbell failures under `min_af_dist = 0` are **run/universe dependent** and appear when barbell’s return distribution becomes skew-negative enough that the `skew` term dominates the (positive) `log(tail_asym)` term.

---

## 4) Threshold Sensitivity (Strict Gate Simulation on Run `20260105-191332`)

Using the computed scoreboard fields (without re-running the tournament), strict candidates under varying `min_af_dist`:

| `min_af_dist` | Candidates | Baseline candidates (`market|benchmark|raw_pool_ew`) |
| ---:| ---:| ---:|
| `0.0` | 3 | 0 |
| `-0.1` | 6 | 3 (benchmark only) |
| `-0.2` | 9 | 3 (benchmark only) |
| `-0.25` | 15 | 3 (benchmark only) |
| `-0.4` | 15 | 3 (benchmark only) |
| `-0.6` | 24 | 6 (benchmark + market) |

What changes first as the gate relaxes:
- Around `min_af_dist ≈ -0.2`, **`skfolio/barbell` becomes eligible** (it fails only `af_dist` at `0.0`).
- Baseline `benchmark` has `af_dist ≈ 0`, so it becomes eligible once `min_af_dist < 0` (if a policy prefers baselines never appear in candidates, that should be implemented explicitly rather than via the antifragility gate).
- Baseline `market` does not become eligible until `min_af_dist <= -0.58` (undesirable if the antifragility gate is intended to exclude “market-like” fragile skew).

---

## 5) Suggestions (Strict-Scoreboard Oriented)

The core question for ISS-002 is not whether `af_dist` is “correct” mathematically, but whether the **strict threshold** and **definition weighting** match institutional intent.

### Option A — Keep `min_af_dist = 0` (status quo), document implications
Use when:
- The goal is to select only truly positively-skewed strategies.

Implications:
- Baselines will often be excluded (expected under ISS-003).
- “Antifragile” strategies that still have negative skew (like barbell in `20260105-191332`) may be excluded even when tails/stress behavior is positive.

Required docs update:
- Explicitly state that `min_af_dist = 0` is a **positive-skew requirement**, not merely “tail asymmetry.”

### Option B — Calibrate gate to admit barbell-like profiles (recommended candidate)
Proposal:
- Adopt strict gate default `min_af_dist = -0.20` for stability-default evaluation (**policy decision**).

Rationale (from `20260105-191332`):
- Admits `skfolio/barbell` (which otherwise fails only `af_dist`).
- Keeps baseline `market` excluded (still at `-0.58`).
- Baseline `benchmark` becomes eligible (its `af_dist` clusters near `0` but slightly negative in stability runs); this is **acceptable** per the baseline policy above.
- `raw_pool_ew` remains excluded in the examined runs because it fails tail multipliers (and often also `stress_alpha`), not only because of `af_dist`.

Policy note:
- This is a **strict-gate calibration change** and is recorded as a policy decision:
  - `docs/specs/iss002_policy_decision_20260105.md`

### Option D — Runtime auto-calibration (parallels temporal fragility calibration)
If `af_dist` remains the dominant exclusion under stability-default windowing, consider a runtime auto-calibration pattern similar to `max_temporal_fragility`:

- Calibrate `min_af_dist` from the **latest N runs** using a percentile reference and a margin.
- Use a stable anchor set (example candidates):
  - “all non-baseline strategy rows” (prevents baselines from defining antifragility expectations),
  - or “barbell rows only” if barbell is treated as the antifragility reference profile.
- Add explicit exclusions (e.g., ignore `raw_pool_ew` blowups, ignore missing/insufficient tails).

This should be treated as a policy change:
- auto-calibration changes the strict gate behavior run-to-run and must be auditable (include the anchor set, run ids, percentile, and final threshold in `tournament_scoreboard.md`).

### Option C — Split “distribution skew” vs “tail asymmetry” as separate signals (research → potential spec)
If the institutional intent is “barbell should be admissible when tails are good,” a more faithful gate might be:
- gate on `tail_asym` (or `log_tail_asym`) rather than on `skew + log(tail_asym)`, and keep skew as a diagnostic

This is a metric/payload/scoreboard change and should be treated as a separate issue if promoted.

---

## 6) Next Actions (Issue-Ready)

1. **Policy decision recorded (Jan 2026)**:
   - Institutional default is now `min_af_dist = -0.20` (see `docs/specs/iss002_policy_decision_20260105.md`).
2. **Validation smoke (recommended)**:
   - Re-run a stability-default (`180/40/20`) production-parity mini-matrix and confirm:
     - strict candidates remain non-empty under the new default,
     - barbell candidates are admissible when they otherwise pass the gate stack,
     - baseline `benchmark` may appear as an eligible anchor candidate (acceptable),
     - baseline `market` remains excluded under normal conditions,
     - `raw_pool_ew` remains calibration-first but valid if it passes.
3. **Feature-flag roadmap (deferred)**:
   - If Option D (auto-calibration) is pursued, implement it behind `TV_FEATURES__FEAT_SCOREBOARD_AF_DIST_AUTOCALIB=1` with full audit output (anchor set, run ids, pctl, margin, final threshold).
4. **Research-only extension**:
   - If Option C is pursued, add non-gating diagnostic fields (`skew`, `tail_asym`, `log_tail_asym`, `tail_gain/loss`) to scoreboard outputs, then create a separate spec issue for any promotion into strict gates.

---

## Appendix A) Multi-Run Evidence (Jan 5, 2026)

This appendix consolidates the key observations across the stability-default (`180/40/20`) runs most relevant to ISS-002.

### A.1 Runs

| Run ID | Windowing | Rows | Strict candidates | Dominant `candidate_failures` | Notes |
| --- | --- | ---:| ---:| --- | --- |
| `20260105-170324` | `180/40/20` | 15 | 0 | `missing:af_dist` (15/15) | Predates tail-sufficiency fix; all `antifragility_dist` payloads report `is_sufficient=false` (tail size 8, but min tail requirement was effectively >8). |
| `20260105-180000` | `180/40/20` | 92 | 46 | `af_dist` (26/92) | Fully sufficient distribution tails; `af_dist` correlates strongly with skew; baseline rows have negative `af_dist`. |
| `20260105-191332` | `180/40/20` | 27 | 3 | `af_dist` (24/27) | Defaults-driven stability smoke; barbell fails only `af_dist` in this mini-matrix; baseline `benchmark` is eligible in principle but fails `af_dist` under `min_af_dist=0` (becomes eligible under `≈ -0.2`). |

### A.2 Skew dominance is consistent (not a single-run artifact)

Correlation between `af_dist` and its components (computed from payloads):
- Run `20260105-180000`: `corr(af_dist, skew) ≈ 0.98`, `corr(af_dist, log(tail_asym)) ≈ 0.76`
- Run `20260105-191332`: `corr(af_dist, skew) ≈ 1.00`, `corr(af_dist, log(tail_asym)) ≈ 0.89`

Interpretation:
- `af_dist` is systematically skew-dominated across runs; this makes `min_af_dist = 0` a strong “positive skew required” gate.

### A.3 Baseline `market` remains well-separated from “barbell-like” candidates

Empirical anchor points:
- Baseline `market/market`:
  - Run `20260105-180000`: `af_dist ≈ -0.55..-0.57`
  - Run `20260105-191332`: `af_dist ≈ -0.58..-0.59`
- Barbell:
  - Run `20260105-180000`: positive `af_dist` (mean ≈ `0.19..0.27` by engine)
  - Run `20260105-191332`: slightly negative `af_dist` (≈ `-0.17..-0.21`)

This separation is the basis for the “`min_af_dist ≈ -0.2` admits barbell without admitting baseline market” proposal.

### A.4 Cross-run threshold sensitivity (`min_af_dist`: `0.0` → `-0.2`)

What changes when relaxing `min_af_dist` from `0.0` to `-0.2` (using existing scoreboard fields; no tournament reruns):

- Run `20260105-191332`:
  - new eligible rows: 6
  - composition: `skfolio/barbell` (3) + baseline `market/benchmark` (3)
  - all new rows were failing **only** `af_dist` under the strict gate stack for this mini-matrix
- Run `20260105-180000`:
  - new eligible rows: 18
  - composition: mostly `cvxportfolio/max_sharpe` (4), `cvxportfolio/min_variance` (4), baseline `market/benchmark` (4), and `hrp` rows (6 total across engines)
  - 14/18 were failing **only** `af_dist`; 4/18 were `af_dist;beta` (so they remain excluded by profile-specific `min_variance` beta gating even if `af_dist` is relaxed)

Interpretation:
- A single global relaxation of `min_af_dist` primarily admits “slightly-negative-skew” configurations that otherwise satisfy the strict gate stack.
- Baseline `benchmark` will tend to become eligible first because its `af_dist` clusters near `0` (slightly negative) across stability-default runs; per baseline policy, this is acceptable and should be audited like any other candidate.
