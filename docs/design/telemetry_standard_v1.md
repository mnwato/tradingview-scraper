# Design: Telensic Telemetry Standard (v1)

## 1. Objective
To provide institutional-grade observability across the quantitative platform, enabling forensic audit of distributed pipeline executions.

## 2. Architecture
The telemetry system is built on OpenTelemetry (OTel), providing a vendor-agnostic layer for tracing, metrics, and structured logging.

### 2.1 Package: `tradingview_scraper.telemetry`
A shared internal package that provides:
- **`TelemetryProvider`**: Singleton manager for OTel SDK lifecycle.
- **`tracing`**: Decorators and context managers for spans.
- **`logging`**: Factory for trace-aware loggers.

## 3. Tracing Specification

### 3.1 Trace Context Propagation
- **Mechanism**: Use standard W3C TraceContext headers for cross-process propagation.
- **Injection**: The `RayComputeEngine` must inject the current trace context into a dictionary (using `TraceContextTextMapPropagator`) and pass it to the `SleeveActor`.
- **Extraction**: Ray actors must extract the context during initialization and start their spans as children of the propagated parent.
- **Host → Worker**: Propagation is performed via environment variables or explicit task arguments.

### 3.2 Standard Spans
| Component | Span Name | Attributes |
| :--- | :--- | :--- |
| `PipelineRoot` | `pipeline:<profile>` | `profile`, `run_id`, `type` |
| `QuantSDK` | `run_stage:<id>` | `stage_id`, `profile`, `run_id` |
| `ProductionPipeline` | `run_step:<step>` | `step`, `profile`, `is_strict` |
| `RayComputeEngine` | `execute_sleeves` | `n_sleeves`, `parallelism` |
| `SleeveActor` | `run_pipeline` | `profile`, `node_ip` |

## 4. Logging Specification

### 4.1 Structured Format
Logs should be emitted in a format that includes:
- `timestamp`
- `level`
- `message`
- `trace_id` (HEX)
- `span_id` (HEX)
- `run_id` (if available)

### 4.2 Correlation
The `logging` module will be configured to automatically inject current span context into every log record.
- **Automatic Setup**: `telemetry.setup_logging()` should be called once globally to configure the root logger and `LogRecordFactory`.

## 5. Metrics Specification

### 5.1 Key Performance Indicators (KPIs)
- **`stage_duration_seconds`** (Histogram): Bucketed duration of pipeline stages. Labels: `stage_id`, `status`.
- **`stage_success_total`** (Counter): Count of successful stage completions. Labels: `stage_id`.
- **`stage_failure_total`** (Counter): Count of stage failures. Labels: `stage_id`, `error_type`.

### 5.2 Automatic Emission
The `@trace_span` decorator must automatically calculate duration and emit these metrics upon function completion.

## 6. Security & Privacy
- Telemetry MUST NOT capture secrets, API keys, or raw market data (except metadata needed for audit).
- Logs are persisted in `data/logs/` and exported to `data/artifacts/summaries/runs/<RUN_ID>/logs/`.
