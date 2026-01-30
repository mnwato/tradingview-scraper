# Design: Forensic Telemetry & Dashboarding (v1)

## 1. Objective
To provide an offline-first, high-fidelity audit of pipeline performance by persisting OpenTelemetry traces directly to the run directory and integrating them into forensic reports.

## 2. Forensic Trace Persistence

### 2.1 `ForensicSpanExporter`
A custom OpenTelemetry `SpanExporter` will be implemented to capture spans in memory during a run and write them to a JSON file upon completion.

- **File Path**: `data/artifacts/summaries/runs/<RUN_ID>/data/forensic_trace.json`
- **Format**: A list of structured span objects including:
  - `name` (Stage/Step ID)
  - `start_time`, `end_time`, `duration_ms`
  - `status` (Success/Error)
  - `attributes` (Profile, Run ID, etc.)
  - `trace_id`, `span_id`, `parent_span_id`

### 2.2 Lifecycle Hooks
The `QuantSDK.run_pipeline` method will serve as the lifecycle manager:
1. Initialize the `ForensicSpanExporter`.
2. Execute the DAG.
3. Flush/Save the exporter's buffer to disk.

## 3. Telemetry Integration in Reports

### 3.1 Report Schema
The "Pipeline Health" section of the Forensic Report (Markdown) will include:
- **Total Duration**: Wall-clock time for the entire DAG.
- **Stage Breakdown**: A table showing each stage, its status, and its duration.
- **Parallelism Efficiency**: If branches were executed in parallel, show the speedup factor.

### 3.2 Automated Generation
The `risk.report_meta` and atomic reporting stages will be updated to automatically look for `forensic_trace.json` and embed the summary table.

## 4. Technical Implementation

### 4.1 Dependency Check
Ensure `opentelemetry-sdk` is used to register the custom exporter.

### 4.2 Cross-Node Tracing (Ray)
Since Ray actors have isolated environments, they must also use a local `ForensicSpanExporter`. Their traces will be collected and merged by the `DAGRunner` or exported as individual worker trace files.
- **Initial Scope**: Local execution and primary orchestrator traces.
- **Future Scope**: Merging distributed worker traces into a single JSON.

## 5. Security
- Ensure no sensitive attributes (e.g., API keys) are captured in span attributes.
- Limit JSON size by excluding verbose trace events unless `TV_DEBUG_TELEMETRY=1`.
