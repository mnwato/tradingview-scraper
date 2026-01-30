# Design: Distributed Forensic Merging (v1)

## 1. Objective
To unify OpenTelemetry traces from distributed Ray worker nodes into a single, cohesive `forensic_trace.json` file on the host machine.

## 2. Distributed Tracing Protocol

### 2.1 Worker-Side Collection
Each `SleeveActor` (running in a separate Ray process) will maintain its own `ForensicSpanExporter`.

- **Initialization**: The actor initializes its telemetry provider with the propagated `trace_id` from the host.
- **Buffer**: Spans generated within the actor are stored in its local memory-based exporter.
- **Collection API**: The `SleeveActorImpl` will expose a `get_telemetry_spans() -> List[Dict]` method.

### 2.2 Host-Side Aggregation
The `RayComputeEngine` will act as the aggregator.

1. **Post-Execution Loop**: After all sleeve futures are collected (`ray.get`), the engine will call `get_telemetry_spans.remote()` on each actor.
2. **Span Harvesting**: The engine retrieves the list of spans from each worker node.
3. **Merging**: The engine appends these remote spans to the host's local `ForensicSpanExporter` buffer.

## 3. Merging Logic

### 3.1 Trace Linking
Because the `trace_id` is propagated, all spans (host and worker) will naturally belong to the same trace. The `parent_span_id` will correctly link worker "Root Spans" (e.g., `run_production_pipeline`) to the host's dispatch span (`execute_sleeves`).

### 3.2 Duplicate Prevention
The merger must ensure that if an exporter is flushed multiple times, spans are not duplicated. This will be handled by using the unique `span_id` as a primary key during the merge.

## 4. Integration with `QuantSDK`
The `QuantSDK.run_pipeline` lifecycle will be updated:
1. Start main span.
2. If parallel branches run, they return their spans.
3. `DAGRunner` merges branch spans into the context.
4. SDK flushes the combined buffer to `forensic_trace.json`.

## 5. Scalability
For very large runs (>100 sleeves), the JSON file might become large. We will implement basic filtering to exclude high-frequency, low-value spans (e.g., internal utility functions) unless `TV_TRACE_LEVEL=DEBUG` is set.
