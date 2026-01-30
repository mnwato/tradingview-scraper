# Audit: Meta-Portfolio Pipeline Deep Audit (v1)

## 1. Objective
To evaluate the numerical stability, recursive safety, and conservation of weights within the fractal meta-portfolio architecture.

## 2. Identified Issues

### 2.1 Recursive Depth Fragility
- **Issue**: `build_meta_returns.py` and `flatten_meta_weights.py` call themselves recursively to resolve nested meta-profiles.
- **Risk**: Circular dependencies in `manifest.json` will cause a `RecursionError` or infinite loop.
- **Remediation**: Implement a `max_depth` (default=3) and track visited profiles to detect cycles.

### 2.2 Weight Conservation Gap
- **Issue**: `flatten_meta_weights.py` projects meta-weights down to atoms but does not verify that the final sum of physical weights matches the original meta-allocation.
- **Risk**: Floating point drift or missing sleeve artifacts can lead to "leaking" or "phantom" weights.
- **Remediation**: Implement a **Stable Sum Gate** that asserts `abs(sum(physical) - sum(meta)) < 1e-6`.

### 2.3 Registry Inconsistency
- **Issue**: The `StageRegistry` ID for aggregation is `meta.aggregation` but the orchestrator (`run_meta_pipeline.py`) uses the legacy ID in some internal logs/comments.
- **Remediation**: Standardize on `meta.aggregation`.

### 2.4 Numerical Scaling in Reports
- **Issue**: `generate_meta_report.py` caps display at `>1000%`.
- **Observation**: This suggests that some combined return streams have extreme volatility during certain windows.
- **Remediation**: Add a "Numerical Stability" audit to the report that flags high-kurtosis or extreme-variance windows in the aggregated returns.

## 3. Conclusion
The fractal logic is elegant but needs "guards" to prevent mathematical divergence and recursion crashes.
