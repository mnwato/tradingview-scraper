# Specification: Selection Stability Metric (`selection_jaccard`) (v1)

## 1. Objective
`selection_jaccard` measures **selection stability**: how much the *membership* of the selected universe changes from one walk-forward window to the next.

This is intended to separate:
- **Structural selection** (stable winners; likely durable factors) from
- **Noise-chasing** (high churn in winners; likely overfit to short-window variance).

It is a **membership metric** (set overlap), not a weight-drift metric (turnover).

## 2. Metric Definition

### 2.1 Jaccard Similarity
For consecutive windows, with winner sets `U_t` and `U_{t-1}`:

`J(U_t, U_{t-1}) = |U_t ∩ U_{t-1}| / |U_t ∪ U_{t-1}|`

The tournament pipeline reports:
- `selection_jaccard`: **average** Jaccard over all consecutive window transitions for a given configuration.

### 2.2 Implementation
The canonical helper lives in `tradingview_scraper/utils/metrics.py:264`.

Current behavior:
- Converts inputs into Python `set`s.
- Returns `1.0` when the union is empty (both sets empty).

## 3. Where It Comes From in the Pipeline

### 3.1 Source-of-truth data
In the current implementation, `selection_jaccard` is computed from **per-window optimize weight dumps** in the audit ledger:
- File: `artifacts/summaries/runs/<RUN_ID>/audit.jsonl`
- Records: `step == "backtest_optimize"` and `status == "success"`
- Payload: `data.weights` (a `dict[str, float]` mapping symbol → weight)

This is loaded and aggregated by:
- `_load_optimize_metrics()` in `scripts/research/tournament_scoreboard.py` (computes avg Jaccard + HHI + max weight + average number of assets).

Then it is merged into the scoreboard rows (per simulator) in:
- `build_scoreboard()` in `scripts/research/tournament_scoreboard.py`

### 3.2 Practical implication: what it actually measures today
Because the set is derived from `data.weights.keys()`, `selection_jaccard` is a **proxy** for “winner stability”.

It is *equivalent* to true winner stability if (and only if):
- Every selected winner is emitted in `weights` with a non-zero weight, and
- Non-winners are not emitted (or are filtered out).

If an optimizer emits lots of near-zero “dust” holdings, the metric can be artificially inflated unless a membership threshold is used.

## 4. Standards / Thresholding
The repo standard bands are defined in `docs/specs/benchmark_standards_v1.md` (Selection Stability).

The tournament scoreboard’s strict candidate gate is:
- `CandidateThresholds.min_selection_jaccard` in `scripts/research/tournament_scoreboard.py` (default `0.30`)

Interpretation:
- `> 0.7` stable selection
- `0.3 – 0.7` dynamic (regime-adaptive)
- `< 0.3` unstable / noise-chasing

## 5. Case Study: Run `20260105-011037`
This run is referenced in `docs/specs/plan.md` as a “Constrained Full” production-parity sweep.

### 5.1 What the scoreboard shows
From `artifacts/summaries/runs/20260105-011037/data/tournament_scoreboard.csv`:
- Total rows: **54**
- Rows with non-null `selection_jaccard`: **36**
- Rows with null `selection_jaccard`: **18**

The nulls are all **baseline rows** with:
- `engine == "market"` and `profile in {"market", "benchmark", "raw_pool_ew"}` (3 profiles × 3 simulators × 2 selection modes).

This is expected for this specific historical run because baseline weights are computed in `scripts/backtest_engine.py` “Special Baselines” and (at the time of Run `20260105-011037`) did not emit a `backtest_optimize` audit outcome with `data.weights`.

### 5.2 Observed values (non-baselines)
The metric is constant across simulators (by design) and also constant across engines/profiles in this run because the membership set is identical per window for all non-baseline engines.

- `v2.1`: average `selection_jaccard ≈ 0.5739` (11 windows → 10 transitions)
  - Transition range: `min ≈ 0.2308`, `median ≈ 0.6667`, `max ≈ 0.7692`
- `v3.2`: average `selection_jaccard ≈ 0.5467` (11 windows → 10 transitions)
  - Transition range: `min ≈ 0.2308`, `median ≈ 0.5000`, `max ≈ 0.9412`

Interpretation: both modes are in the **dynamic** band (0.3–0.7), not “noise chasing”.

## 6. Key Nuances / Failure Modes

### 6.1 “Missing selection_jaccard” usually means missing audit weight traces
The scoreboard can only compute selection stability if it can find:
- `backtest_optimize` + `status=success` + non-empty `data.weights`.

If `data.weights` is not recorded (or is empty), the strict scoreboard flags:
- `missing:selection_jaccard`

### 6.2 Baselines are a special case
Baselines should emit optimize weights into the audit ledger so the scoreboard can compute:
- `selection_jaccard` (stability) and
- concentration diagnostics (HHI / max weight / average number of assets),
for the baseline rows exactly like non-baseline strategies.

You have two reasonable interpretations here:
1. Treat baseline `selection_jaccard` as **not applicable** (and ignore missing for baseline rows), or
2. Instrument baseline weight dumps into the ledger so baseline stability metrics exist (useful for universe drift diagnostics).

Policy (Jan 2026): prefer (2) so baseline rows are fully instrumented in strict scoreboards. Older runs may still show baseline `selection_jaccard == null` and should be interpreted as “not recorded”, not “unstable selection”.

### 6.3 Membership definition matters
Today’s definition uses **all keys** in `data.weights`.

If you want “stability of what we actually hold meaningfully”, consider adding a second metric variant:
- **Top-K Jaccard**: compare `top_k` holdings by weight per window (e.g., `k=5`)
- **Thresholded Jaccard**: compare holdings with `weight >= 0.02` (or similar)

Empirically in Run `20260105-011037`, these variants can differ materially for HRP profiles (the “core holdings” churn more than the full membership set).

## 7. Recommended Guardrails

### 7.1 Scoreboard readiness check
For strict scoreboard runs, add/keep a pre-flight that asserts:
- Non-baseline configs have `selection_jaccard` populated.
- Baseline configs are either exempt, or instrumented.

### 7.2 Debug checklist for a run
1. Confirm optimize outcomes exist:
   - `jq -c 'select(.step==\"backtest_optimize\" and .status==\"success\")' audit.jsonl | head`
2. Confirm `data.weights` exists and is non-empty.
3. Confirm `context` keys match the scoreboard join key:
   - `selection_mode`, `rebalance_mode`, `engine`, `profile`, `window_index`
4. Recompute with the same logic as `_load_optimize_metrics()` to isolate whether the issue is:
   - missing audit data vs scoreboard merge/join mismatch.
