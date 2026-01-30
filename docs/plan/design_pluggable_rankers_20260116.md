# Design Plan: Pluggable Selection Rankers (2026-01-16)

## 1. Objective
Refactor the Selection Engine to support a **Pluggable Ranker Architecture**. This allows strategies to define *how* candidates are prioritized (e.g., Log-MPS, Raw Signal, Volatility Adjusted) directly in the manifest, decoupling sorting logic from the Policy Stage.

## 2. Architecture

### 2.1 Interface (`BaseRanker`)
A standardized protocol for ranking a list of candidate IDs based on a Selection Context.

```python
class BaseRanker(ABC):
    def rank(self, candidates: List[str], context: SelectionContext, ascending: bool = False) -> List[str]:
        """
        Sorts the candidate list.
        Args:
            candidates: List of symbol IDs (atoms).
            context: Full selection context (features, scores, metadata).
            ascending: Sort direction (True=Low->High, False=High->Low).
        Returns:
            Sorted list of symbol IDs.
        """
```

### 2.2 Implementations
1.  **`MPSRanker`** (Default): Uses `context.inference_outputs["alpha_score"]`. Matches current v3.6 behavior.
2.  **`SignalRanker`**: Uses a specific raw feature column (e.g., `recommend_ma`, `rsi`, `volatility`). Useful for single-factor strategies.
3.  **`HybridRanker`**: (Future) Complex logic combining multiple scores dynamically.

### 2.3 Configuration Schema (`manifest.json`)
The `selection.ranking` block is expanded:

```json
"ranking": {
  "method": "mps",          // "mps" or "signal"
  "direction": "descending", // "ascending" or "descending"
  "signal": "recommend_ma"   // Only used if method="signal"
}
```

## 3. Implementation Steps

### 3.1 Create Ranker Module
- `tradingview_scraper/pipelines/selection/rankers/base.py`
- `tradingview_scraper/pipelines/selection/rankers/mps.py`
- `tradingview_scraper/pipelines/selection/rankers/signal.py`
- `tradingview_scraper/pipelines/selection/rankers/factory.py`

### 3.2 Update Settings
- Update `SelectionRanking` model in `settings.py` to include `signal` (Optional).

### 3.3 Refactor Policy Stage
- Modify `SelectionPolicyStage` to instantiate the ranker via `RankerFactory`.
- Replace hardcoded `sorted(..., key=_get_score)` with `ranker.rank(...)`.

## 4. Migration Strategy
- **Backward Compatibility**: The default `method` will be "mps" (mapped from old "alpha_score" if needed), preserving existing behavior for all production profiles.
- **New Capability**: `binance_spot_rating_ma_short` can eventually switch to `method="signal", signal="recommend_ma"` if we want to bypass the MPS ensemble entirely (though the current "Dominant Signal" feature achieves a similar result within MPS).

## 5. Deliverables
- Python Code (Rankers + Factory).
- Updated `Policy` Stage.
- Updated Docs (`universe_selection_v3.md`).
