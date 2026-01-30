# Design: OpenTelemetry API Standardization (v2)

## 1. Objective
To fully standardize the platform's observability architecture on core OpenTelemetry (OTel) APIs, ensuring backend neutrality and signal unification.

## 2. Signal Unification

### 2.1 Tracing
- **API**: `opentelemetry.trace.get_tracer(__name__)`.
- **Instrumentation**: Standardize all `@trace_span` usage to avoid manual timing. Use `span.set_attribute` for status and error reporting.

### 2.2 Metrics
- **API**: `opentelemetry.metrics.get_meter(__name__)`.
- **Standard Instruments**:
  - `quant.stage.duration` (Histogram)
  - `quant.stage.total` (Counter)
  - `quant.asset.return` (Histogram)
- **Decoupling**: Remove all hardcoded Prometheus Pushgateway logic. Rely on standard OTel exporters.

### 2.3 Logging
- **API**: Standard Python `logging` module.
- **Bridge**: Use OTel `LoggingHandler` to automatically export logs as OTel LogRecords.
- **Correlation**: Trace and Span IDs must be automatically injected into OTel Logs.

## 3. Distributed Context Propagation
- Use W3C TraceContext headers.
- **Ray Workers**: Injected via `carrier` dictionary during task/actor dispatch and extracted during worker initialization.

## 4. Backend Neutrality (OTLP)
- The platform will prioritize **OTLP over gRPC or HTTP** for signal delivery.
- Configuration will be entirely driven by `OTEL_*` environment variables.
- **Local Development**: Default to `ConsoleExporter` or `ForensicSpanExporter` (JSON).

## 5. Migration Map

| Feature | Legacy Implementation | OTel Standard Implementation |
| :--- | :--- | :--- |
| **Duration** | `time.time()` math in decorator | Span start/end times |
| **Status** | Manual `success_counter.add(1)` | Span Status (OK/Error) |
| **Log Linkage** | Custom `LogRecordFactory` | Official `LoggingHandler` |
| **Prometheus** | Hardcoded Pushgateway logic | `PrometheusMetricReader` or OTLP to Collector |

## 6. Security
- Sensitive metadata (e.g., wallet addresses, API keys) MUST NOT be included in Span attributes or Log bodies.
