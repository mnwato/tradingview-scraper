# Design: Feature Store Resilience (v1)

## 1. Objective
To implement numerical consistency checks and PIT-fidelity gates for the global feature store.

## 2. Feature-Inference Gate

### 2.1 symbol Coverage
The `backfill_features.py` script will be updated to perform a "Full-Foundation Audit".

- **Logic**: 
  - Retrieve list of all `.parquet` files in `data/lakehouse/`.
  - Ensure every symbol has a corresponding column in the feature matrix.
  - Fail-fast if coverage $< 100\%$ in `STRICT_HEALTH` mode.

### 2.2 NaN Sanitization
Implement a `sanitize_features` utility.
- **Rule**: Drop leading NaNs (warm-up period).
- **Rule**: If internal NaNs exist after warm-up, use `ffill(limit=3)`.
- **Rule**: If an instrument has $> 5$ consecutive NaNs, mark as "Feature Toxic" and veto.

## 3. Pandera Feature Schema
Add `FeatureStoreSchema` to `tradingview_scraper/pipelines/contracts.py`.

```python
FeatureStoreSchema = pa.DataFrameSchema({
    "timestamp": pa.Column(pa.DateTime),
    "symbol": pa.Column(str),
    "recommend_all": pa.Column(float, checks=[pa.Check.in_range(-1.0, 1.0)]),
    "adx": pa.Column(float, checks=[pa.Check.in_range(0, 100)]),
    # ... additional technical features
})
```

## 4. Implementation Roadmap
1. Define `FeatureStoreSchema` in `contracts.py`.
2. Update `scripts/services/backfill_features.py` to include coverage check.
3. Update `Foundation Gate` to verify `features_matrix.parquet` freshness against `returns_matrix.parquet`.

## 5. TDD Strategy
- **`tests/test_feature_consistency.py`**:
    - Mock a features matrix with a missing symbol.
    - Verify that the coverage check fails.
    - Verify that `ffill` limit is respected.
