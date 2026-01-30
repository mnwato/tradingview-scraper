# Design: OTLP Forensic Export & Collector Integration (v1)

## 1. Objective
To establish OTLP as the universal delivery mechanism for all forensic signals (Traces, Metrics, Logs), decoupling the quantitative platform from specific backends and enabling centralized observability through an OTel Collector.

## 2. Universal Frontend Strategy
The platform will strictly use the standard OpenTelemetry APIs (`trace`, `metrics`, `_logs`) as the "Universal Frontend". Business logic will remain agnostic of the backend.

### 2.1 Signal Delivery Map
| Signal | Implementation | Target |
| :--- | :--- | :--- |
| **Traces** | `OTLPSpanExporter` | Collector (gRPC/HTTP) |
| **Metrics** | `OTLPMetricExporter` | Collector (gRPC/HTTP) |
| **Logs** | `OTLPLogExporter` | Collector (gRPC/HTTP) |

## 3. Configuration Management
Delivery is configured via standard `OTEL_*` environment variables, resolved during `TelemetryProvider.initialize()`.

- `OTEL_EXPORTER_OTLP_ENDPOINT`: Root endpoint (e.g., `http://localhost:4317`).
- `OTEL_EXPORTER_OTLP_PROTOCOL`: `grpc` (default) or `http/protobuf`.
- `OTEL_RESOURCE_ATTRIBUTES`: Standard tags (e.g., `service.name=quant-orchestrator,env=production`).

## 4. Distributed Collector Integration
For Ray-based distributed executions, each worker node sends its signals directly to the OTel Collector. The `trace_id` propagated from the host ensures the Collector can stitch the spans together into a single forensic trace.

## 5. Implementation Roadmap

### 5.1 `TelemetryProvider` Refactor
Update `initialize()` to automatically detect OTLP configurations and register the corresponding exporters.

### 5.2 Forensic Trace Merging (Sync Mode)
While OTLP handles live delivery, the `forensic_trace.json` local file remains as an "Offline-First" backup. The `ForensicSpanExporter` will continue to run in parallel with OTLP.

## 6. Verification (TDD)
- **`tests/test_otlp_export_config.py`**:
    - Set `OTEL_EXPORTER_OTLP_ENDPOINT`.
    - Initialize provider.
    - Verify that OTLP processors are added to the Providers.
