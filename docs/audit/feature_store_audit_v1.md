# Audit: Feature Store Consistency & PIT Integrity (v1)

## 1. Objective
To audit the integrity of the Point-in-Time (PIT) feature store, ensuring that the `features_matrix.parquet` is consistent with the latest 49-symbol Lakehouse foundation.

## 2. Identified Issues

### 2.1 Incomplete Backfill Coverage
- **Observation**: `backfill_features.py` processes symbols extracted from a candidates JSON file.
- **Problem**: If a symbol exists in the Lakehouse but is missing from the provided candidates list, it will be missing from the global feature matrix. This causes failures in dynamic selection during backtests.
- **Suggestion**: Implement a `coverage_check` that compares the feature matrix columns against all available `.parquet` files in the Lakehouse.

### 2.2 Feature NaN Propagation
- **Observation**: Technical features (ADX, RSI) naturally produce NaNs during their warm-up periods.
- **Problem**: Excessive NaNs in the feature matrix can lead to "Silent Vetoes" in the selection engine.
- **Suggestion**: Implement strict NaN tracking. If an asset has > 10% NaNs after the initial warm-up, it should be flagged as "Degraded".

### 2.3 Timestamp Alignment
- **Observation**: Features are calculated on individual symbol history and then merged.
- **Problem**: If symbols have different start/end dates or missing bars, the outer-joined matrix will have sparse rows.
- **Remediation**: Use `ffill(limit=3)` for minor gaps, but never ffill across large gaps (> 3 days) to avoid lookahead bias from stale data.

## 3. Tool Research: Pandera
- **Status**: `Pandera` has been successfully added to the project. It will be used to enforce these PIT integrity rules at the `backfill_features.py` boundary.

## 4. Conclusion
The feature store is the most sensitive data artifact in the "Natural Selection" pillar. Implementing these consistency gates will ensure that alpha scoring is always performed on high-integrity, PIT-correct data.
