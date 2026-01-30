# Audit: Pipeline Composability & Scalability (v1)

## 1. Objective
To analyze the current `DAGRunner` and `StageRegistry` implementations for scalability bottlenecks and architectural brittle points.

## 2. Identified Issues

### 2.1 Brittle Stage Discovery
- **Current State**: `StageRegistry._ensure_loaded()` uses a hardcoded list of `import` statements.
- **Problem**: Adding a new module requires manually updating the registry's core code. This violates the Open-Closed Principle.
- **Suggestion**: Implement dynamic package scanning or use `pkgutil`/`importlib` to discover all modules in `tradingview_scraper.pipelines`.

### 2.2 Limited Context Merging
- **Current State**: `DAGRunner._merge_contexts()` has hardcoded logic for `SelectionContext` and `dict`.
- **Problem**: As we add new context types (e.g., `BacktestContext`, `DataOpsContext`), the runner becomes a bottleneck. Parallel branches cannot easily merge complex state changes.
- **Suggestion**: Transition to a **Merge Strategy Pattern**. Context objects should implement a `__add__` or `merge(other)` method.

### 2.3 Redundant Logic
- **Current State**: `DAGRunner` contains duplicate code for `_merge_contexts`.
- **Problem**: Maintenance overhead and risk of divergence.
- **Remediation**: Immediate cleanup of the duplicated block.

### 2.4 Snapshot Incompleteness
- **Current State**: `WorkspaceManager.create_golden_snapshot()` symlinks the `features/` directory.
- **Problem**: If the source features are updated during a run, the snapshot is mutated.
- **Suggestion**: Implement recursive hard-linking or filtered copying for feature subdirectories.

## 3. Tool Research

### 3.1 Pandera (Data Contracts)
- **Benefit**: Provides schema validation for Pandas DataFrames with a clear DSL.
- **Integration**: Can be used in the `IngestionValidator` and at stage boundaries to ensure L0-L4 contracts are met.

### 3.2 Ray Datasets
- **Benefit**: Designed for large-scale data transformation. 
- **Integration**: Consider moving from `pd.read_parquet` to `ray.data.read_parquet` for the global returns matrix to leverage cluster-wide memory.

## 4. Conclusion
The foundation is strong, but the "glue" (Registry and Runner) needs to be more polymorphic and automated to support the next level of strategy complexity.
