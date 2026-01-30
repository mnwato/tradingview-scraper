# Audit Note: Regime Semantics + Windowing Effectiveness (Jan 2026)

This audit evaluates whether:

1. **Larger test windows** (`test_window=40`, overlapping) reduce short-window Sharpe sign-flips / temporal fragility.
2. **Realized regime labeling** improves regime robustness reporting (worst-regime summaries are realized-time, not decision-time).
3. **Audit ledger + artifacts** remain institutional (no intent→outcome gaps; run-scoped regime audit logs; global lakehouse logs not polluted).

## Runs

### Smoke A (Control)
- Run: `20260105-174600`
- Windowing: `train/test/step = 120/20/20`
- Realized regime: disabled (fields present but null)
- Payload: `artifacts/summaries/runs/20260105-174600/data/tournament_results.json`
- Scoreboard: `artifacts/summaries/runs/20260105-174600/data/tournament_scoreboard.csv`

### Smoke B (Corrected Larger Window + Realized Regime)
- Run: `20260105-180000`
- Windowing: `train/test/step = 180/40/20`
- Realized regime: enabled (`TV_ENABLE_REALIZED_REGIME=1`)
- Payload: `artifacts/summaries/runs/20260105-180000/data/tournament_results.json`
- Scoreboard: `artifacts/summaries/runs/20260105-180000/data/tournament_scoreboard.csv`

## Audit Ledger Integrity (Both Runs)

Both runs have complete optimize logging (no missing outcomes):
- `backtest_optimize:intent == backtest_optimize:success` (gap = 0)

This ensures:
- Selection stability metrics (Jaccard/HHI) are computed from full window coverage.
- Strict scoreboard gates are not invalidated by missing optimize outcomes.

## Effectiveness: Larger Window Reduces Fragility and Sign-Flips

Computed from each run’s window Sharpe series in `data/tournament_results.json`, averaged across simulators (`custom`, `cvxportfolio`, `nautilus`) for key profiles:

### `market/market`
- Temporal fragility (avg): **~1.79 → ~0.55**
- Sign-flip rate (avg): **~0.20 → 0.00**
- Negative Sharpe windows (avg): **~3.0 → 0.0**

### `custom/hrp`
- Temporal fragility (avg): **~1.62 → ~0.48**
- Sign-flip rate (avg): **~0.17 → 0.00**
- Negative Sharpe windows (avg): **~2.67 → 0.0**

### `market/raw_pool_ew` (diagnostic baseline, historically the outlier)
- Temporal fragility (avg): **~7.25 → ~0.96**
- Sign-flip rate (avg): **~0.40 → ~0.33**
- Negative Sharpe windows (avg): **~4.0 → 1.0**

Interpretation:
- Larger windowing materially reduces polarity-driven instability (especially for `market/market` and `custom/hrp`).
- `raw_pool_ew` becomes a usable calibration reference rather than an extreme fragility outlier, but still retains some flip behavior (expected: it is intentionally “raw”).

## Effectiveness: Realized Regime Improves Regime Robustness Reporting

### Payload semantics
- Smoke A (`20260105-174600`):
  - `decision_*` fields present.
  - `realized_*` fields are null.
- Smoke B (`20260105-180000`):
  - `realized_*` fields populated and differ from decision labels in some windows.
  - Example (`custom market/market`):
    - Window 0: decision_regime=`TURBULENT` while realized_regime=`QUIET`.
    - Agreement rate across windows: ~**0.71** (not identical, which is the point).

### Scoreboard behavior
For Smoke B (`20260105-180000`), scoreboard worst-regime summaries use realized regime grouping when present:
- Example (`custom market/market`):
  - Scoreboard `worst_regime = TURBULENT` and `worst_regime_mean_return ≈ 0.0419`
  - Recomputed directly from payload `windows[].realized_regime` and `windows[].returns` matches the scoreboard.

## Strict Gating Outcomes (Candidates)

- Smoke A (`20260105-174600`): candidates **12**
- Smoke B (`20260105-180000`): candidates **46**

Primary driver of the improvement:
- Many profiles stop failing the `temporal_fragility` gate once `test_window=40` smooths short-window Sharpe sign-flips.

## Regime Audit Log Hygiene

- Each run writes a run-scoped regime audit log:
  - `artifacts/summaries/runs/20260105-174600/regime_audit.jsonl`
  - `artifacts/summaries/runs/20260105-180000/regime_audit.jsonl`
- The global lakehouse regime audit log `data/lakehouse/regime_audit.jsonl` is not modified during these runs (size and mtime unchanged during validation).

## Notes / Follow-ups

- Makefile bridge: `BACKTEST_*` overrides are promoted to `TV_*` equivalents, so windowing smokes can be reproduced via `make port-test BACKTEST_TRAIN=... BACKTEST_TEST=... BACKTEST_STEP=...`.
- If running scripts directly (outside `make`), prefer setting `TV_TRAIN_WINDOW`, `TV_TEST_WINDOW`, `TV_STEP_SIZE` explicitly (the settings model uses `env_prefix="TV_"`).
