# Design: Unified DAG Orchestrator (v1)

## 1. Objective
To replace imperative pipeline scripts with a declarative, SDK-managed execution engine that supports composition, parallelism, and institutional-grade observability.

## 2. Core Components

### 2.1 `DAGRunner`
A lightweight engine responsible for:
- Resolving stage dependencies.
- Executing stages in sequence or parallel branches.
- Handling state propagation via a polymorphic `Context` object.

### 2.2 Pipeline Manifests
Pipelines will be defined in `configs/manifest.json` using a new `pipelines` schema:

```json
"pipelines": {
  "alpha.full": {
    "steps": [
      "foundation.ingest",
      "foundation.features",
      "alpha.inference",
      "alpha.clustering",
      "alpha.policy",
      "alpha.synthesis",
      "risk.optimize"
    ]
  }
}
```

## 3. State-Passing Protocol

### 3.1 Context Transformation
Each stage in the `StageRegistry` must adhere to the signature:
`execute(context: Any) -> Any`

The `DAGRunner` will:
1. Initialize the root context (e.g., `SelectionContext` or `MetaContext`).
2. Pass the context to the first stage.
3. Use the return value of stage $N$ as the input for stage $N+1$.

### 3.2 Polymorphism
For heterogeneous pipelines (e.g., DataOps followed by Alpha), the runner will support **Context Adapters** that map outputs of one pillar to the inputs of another.

## 4. Parallelism Strategy

### 4.1 Branch Execution
If a pipeline definition contains a list of lists, those sub-lists will be executed in parallel:

```json
"steps": [
  "foundation.ingest",
  ["alpha.inference_model_a", "alpha.inference_model_b"],
  "alpha.ensemble"
]
```

### 4.2 Ray Integration
The `DAGRunner` will detect parallel branches and automatically dispatch them to the `RayComputeEngine` if `TV_ORCH_PARALLEL=1` is set.

## 5. Context Merging Strategy (Parallel Execution)

When multiple branches execute in parallel, they each receive a deep copy of the current `Context`. Upon completion, the `DAGRunner` must merge the resulting contexts back into the main timeline.

### 5.1 Merging Protocol
1. **Additive Merge**: For fields like `audit_trail`, branches are concatenated in order of completion.
2. **Key-Space Partitioning**: For fields like `feature_store` or `inference_outputs`, branches are merged using `pd.concat(axis=1)` if they produce distinct features/columns.
3. **Collision Strategy**: If two branches modify the same key/field, the runner will raise a `ContextCollisionError` unless a specific `MergeStrategy` is defined for that pipeline.

### 5.2 Merge Adapters
Pipelines can define an optional `merge_adapter` stage to resolve complex state merges (e.g., ensembling multiple model outputs).

## 6. Telemetry & Error Handling

### 5.1 Linkage
The `trace_id` will be established at the `DAGRunner` constructor and passed into all child spans.

### 5.2 Failure Propagation
- **Graceful Abortion**: On stage failure, the runner will stop execution and invoke `QuantSDK.cleanup_workspace(run_id)`.
- **Forensic Capture**: The exact state of the context at the point of failure will be serialized to `data/artifacts/summaries/runs/<RUN_ID>/error_context.pkl`.

## 6. Migration Plan
1. Implement `DAGRunner` in `orchestration/runner.py`.
2. Update `QuantSDK.run_pipeline` to load definitions from manifest.
3. Port `ProductionPipeline` logic to a declarative sequence.
4. Port `run_meta_pipeline.py` to a nested DAG sequence.
