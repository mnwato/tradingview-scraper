# Specification: Selection Jaccard (Selection Stability) v1

This spec defines **Selection Jaccard**, the canonical selection-stability metric used by the strict tournament scoreboard.

## 1. Purpose

Selection Jaccard quantifies how stable a strategy’s **chosen universe** is from one walk-forward window to the next.

Institutional intent:
- Prefer configurations that do not “churn” their selected assets every window.
- Make churn auditable using the **audit ledger** rather than ad-hoc artifacts.

## 2. Definition

For two consecutive windows:

- Let `A` be the set of symbols with **non-zero weights** in window `t-1`.
- Let `B` be the set of symbols with **non-zero weights** in window `t`.

The per-transition Jaccard similarity is:

`J(A,B) = |A ∩ B| / |A ∪ B|`

The scoreboard’s `selection_jaccard` is the mean Jaccard similarity across all consecutive window transitions for a given `(selection_mode, rebalance_mode, engine, profile)` pair.

Edge case:
- If there are fewer than 2 windows with usable weight sets, `selection_jaccard` defaults to `1.0` (no evidence of churn).

## 3. Source of Truth (Audit Ledger)

Selection Jaccard is computed from **window-level optimize outcomes** recorded in the audit ledger:

- `audit.jsonl` records `step="backtest_optimize"`, `status="success"`
- The window payload must include `data.weights` as a dict: `{symbol: weight, ...}`
- The window index must be present in `context.window_index`

This makes the metric:
- Deterministic
- Replayable
- Resistant to “missing returns pickle” issues

### Baseline requirement

Baseline profiles (`market`, `benchmark`, `raw_pool_ew`) must emit `backtest_optimize` outcomes with `data.weights` so they can:
- populate `selection_jaccard`
- be used as calibration anchors (and not fail strict gating due to missing selection logs)

## 4. Failure Modes / Diagnostics

Common reasons for `missing:selection_jaccard` (or unstable values):

1. **Optimize outcomes missing**:
   - `backtest_optimize:intent` exists without a matching outcome.
   - or outcomes exist but no `data.weights` payload is persisted.
2. **Empty optimizations**:
   - `status="empty"` windows reduce usable transitions; treat as an upstream stability failure, not a scoreboard failure.
3. **Universe mismatch**:
   - candidate symbols are unqualified (e.g., `BTCUSDT`) while returns columns are qualified (e.g., `BINANCE:BTCUSDT`), leading to inconsistent weight keys.

## 5. Relationship to Strict Gating

- `selection_jaccard` is a **strict gate** (thresholded) when `--allow-missing` is not set.
- Research-only diagnostics (e.g., HHI, max weight, number of assets) may be computed from the same weight payloads but must be treated as **non-gating** unless explicitly promoted by spec.

## 6. Implementation Reference

- Scoreboard computation: `scripts/research/tournament_scoreboard.py` (`_load_optimize_metrics`)
- Jaccard helper: `tradingview_scraper/utils/metrics.py` (`calculate_selection_jaccard`)

