# Spec: Regime Labeling Semantics (Decision vs Realized) — v1

## Problem Statement

Tournament window payloads currently contain a single `regime` label per test window.
In the current implementation, this label is computed from the **training slice** and then attached to the **test window** record.

This creates a recurrent audit confusion:
- A test window can be labeled `QUIET` while the realized test-window Sharpe/return is strongly negative.
- Observers interpret this as “regime detector mismatch”, but the real issue is **semantic ambiguity** (decision-time vs realized-time labeling).

## Current Behavior (Observed + Confirmed)

- In `scripts/backtest_engine.py`, per-window regime is computed as:
  - `regime = self.detector.detect_regime(train_data_raw)[0]`
  - `market_env, _ = self.detector.detect_quadrant_regime(train_data_raw)`
- That `regime` value is then attached to each `windows[]` record for the corresponding **test window**.

Therefore the current `windows[].regime` should be interpreted as:
- **Decision-time market regime** at the end of training / start of test (used for optimization parameterization),
not a label describing the realized test window.

## Goals

1. **Remove semantic ambiguity** in window payloads and downstream audits.
2. Ensure regime-based robustness summaries (e.g., worst-regime analytics) are based on **realized** regime labeling.
3. Preserve backward compatibility for downstream consumers (scoreboards, reports).

## Non-Goals

- Redesigning the regime detector itself (thresholds/weights) is out of scope for v1.
- Guaranteeing that `QUIET` implies positive returns is explicitly not a goal (QUIET is primarily volatility/turbulence-driven).

## Proposed Schema (Backward Compatible)

### Window Record Fields

Keep `regime` for compatibility, but introduce explicit fields:

- `decision_regime` (str): computed from `train_data_raw` (same source as current `regime`).
- `decision_regime_score` (float): score returned by the detector for `decision_regime`.
- `decision_quadrant` (str): quadrant returned by `detect_quadrant_regime(train_data_raw)` (e.g., `EXPANSION`, `CRISIS`).

Optionally in v1 (recommended, but can ship separately if risk/complexity is high):
- `realized_regime` (str): computed from realized **test** returns slice (either:
  - from `test_data` matrix used in the window, or
  - from a canonical benchmark proxy series for comparability across strategies).
- `realized_regime_score` (float)
- `realized_quadrant` (str)

### Feature Toggles (Implementation Notes)

- `TV_ENABLE_REALIZED_REGIME=1`: emit `realized_*` fields in tournament window payloads (off by default).
- `TV_DISABLE_REGIME_AUDIT=1`: disable regime audit logging entirely.
- `TV_REGIME_AUDIT_PATH=/path/to/file.jsonl`: override the regime audit log destination.

### Compatibility Rule

- Set `windows[].regime = decision_regime` until consumers migrate.
- Update docs/specs so any existing “regime” references are interpreted as **decision_regime** unless explicitly called out.

## Behavioral Rules

1. **Decision regime** must be computed strictly using information available at decision time:
   - `train_data_raw` ending at `test_start - 1 session`.
2. **Realized regime** (if enabled) must use only within-window data:
   - `test_data` or benchmark series restricted to `[test_start, test_end]`.
3. Any per-window regime audit logging must be:
   - run-scoped (preferred), OR
   - disabled during tournaments (avoid global `data/lakehouse/regime_audit.jsonl` contamination).

## Downstream Consumer Updates

### Reports / Forensics
- Regime robustness summaries should use `realized_regime` when available; otherwise they should state clearly that they are decision-regime buckets.

### Scoreboard
- Scoreboard should prefer `realized_regime` for “worst regime” reporting once available.
- If only `decision_regime` exists, label output column as `decision_regime` (or include a note in markdown footer).

## Validation (Acceptance Criteria)

### A. Payload Auditability
- For any run, a single window row contains:
  - `decision_regime` + `decision_regime_score` + `decision_quadrant`.
- The audit note “QUIET but negative” is reclassified as expected when decision regime != realized outcome direction.

### B. No Lookahead
- `decision_regime` does not change if test returns are removed/perturbed (since computed only from train slice).

### C. Stability Smoke
- Run a small tournament smoke and confirm:
  - `decision_regime` is populated for all windows,
  - `realized_regime` (if enabled) is populated for all windows,
  - regime fields are stable across simulators.

## Plan Self-Audit Checklist

Use this checklist before implementing code changes:

1. **Terminology clarity**
   - [ ] All docs/specs use `decision_regime` when referring to train-derived labels.
   - [ ] All realized regime outputs explicitly state their data source (test slice vs benchmark proxy).
2. **Backward compatibility**
   - [ ] Existing consumers reading `windows[].regime` continue to function without changes.
   - [ ] Any new fields are additive and optional for legacy payloads.
3. **No lookahead**
   - [ ] `decision_*` computed strictly from train slice (up to `test_start - 1`).
   - [ ] `realized_*` computed strictly within `[test_start, test_end]`.
4. **Run-scoped auditability**
   - [ ] Regime diagnostics required for audits are persisted in run artifacts (not only logs).
   - [ ] Global `data/lakehouse/regime_audit.jsonl` is not polluted by tournament runs (or explicitly disabled).
5. **Validation readiness**
   - [ ] Smoke run commands are written and acceptance criteria are measurable (files + fields + counts).

## Risks / Tradeoffs

- Computing realized regimes per strategy may create many “different” realized regime labels (strategy-dependent),
  so a benchmark-proxy realized regime is often preferable for cross-strategy comparability.
- Extra per-window computation may increase tournament runtime slightly.

## Rollout Plan (Minimal, Safe)

1. **Docs-first** (this spec + plan tracking).
2. Add `decision_*` fields to payloads while keeping `regime` unchanged.
3. Update forensics/reporting to prefer explicit `decision_*` naming.
4. (Optional) Add `realized_*` regime fields behind a feature flag.

## Validation (Completed Smokes)

- Decision regime fields validation: Run `20260105-174600` (tournament payload includes `decision_regime`, `decision_regime_score`, `decision_quadrant`).
- Realized regime + scoreboard preference validation (pre-fix window override wiring): Run `20260105-175200` with `TV_ENABLE_REALIZED_REGIME=1` (payload includes `realized_*` fields; scoreboard worst-regime uses them when present; windowing remained `120/20/20`).
- Realized regime + larger-window validation (corrected `180/40/20`): Run `20260105-180000` with `TV_ENABLE_REALIZED_REGIME=1` (payload includes `realized_*` fields under true overlapping windows; scoreboard worst-regime uses them when present).
