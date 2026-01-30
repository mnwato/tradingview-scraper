# Design Specification: Meta-Portfolio Streamlining (v1.0)

## 1. Problem Statement
The current meta-portfolio pipeline (`run_meta_pipeline.py`) is functionally correct but exhibits several bottlenecks:
1. **Redundant Aggregation**: Recursive fractal trees reload the same atomic `.pkl` files multiple times.
2. **Solver Fragility**: Dependency mismatches (e.g. missing `skfolio`) are only detected at runtime, leading to degraded meta-portfolios.
3. **Namespace Pollution**: Meta-artifacts are stored in `data/lakehouse` with conflicting names if not carefully prefixed.

## 2. Proposed Improvements

### 2.1 Recursive Result Caching
- **Mechanism**: `build_meta_returns.py` should check for a `{meta_profile}_{prof}_returns.pkl` in a dedicated `data/lakehouse/.cache` directory.
- **TTL**: Cache is invalidated if any of the underlying atomic Run IDs change in `manifest.json`.

### 2.2 Solver Health Guardrail
- **Requirement**: Meta-aggregation MUST verify that at least 75% of requested windows for a sleeve were successfully optimized.
- **Action**: A new `scripts/validate_sleeve_health.py` tool will parse `audit.jsonl` and return a non-zero exit code if health thresholds are not met.

### 2.3 Automated Outlier Audit
- **Feature**: Integrate the logic from `scripts/audit_windows.py` directly into `generate_meta_report.py`.
- **Output**: Add an "Anomalies" section to the Markdown report listing windows with Sharpe > 10 or Volatility > 200%.

### 2.4 Parallel Sleeve Execution
- **Mechanism**: Use `ProcessPoolExecutor` in `run_meta_pipeline.py` to trigger underlying atomic production runs in parallel (if `run_id` is not provided).

### 2.5 Manifest Resolution (Correctness Hardening)
- **Requirement**: Meta orchestration MUST NOT hard-code `configs/manifest.json`.
- **Mechanism**:
  - Accept `--manifest` CLI arg in `scripts/run_meta_pipeline.py` (default `configs/manifest.json`).
  - Export `TV_MANIFEST_PATH=<manifest>` before calling `get_settings()`.
  - Use `settings.manifest_path` everywhere a manifest is loaded (including sleeve execution).
- **Rationale**: Without this, meta runs are not replayable when alternative manifests are used (e.g., canary/prod forks).

## 3. Implementation Plan
1. **Stage 1**: Implement `validate_sleeve_health.py`.
2. **Stage 2**: Add caching to `build_meta_returns.py`.
3. **Stage 3**: Enhance meta-report with anomaly tables.
