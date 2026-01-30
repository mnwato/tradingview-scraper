# Design: Real-time Monitoring with Prometheus (v1)

## 1. Objective
To provide real-time visibility into pipeline execution and health using Prometheus and Grafana, building upon the existing OpenTelemetry foundation.

## 2. Architecture

### 2.1 Metric Collection
We will use the OpenTelemetry Metrics SDK to generate metrics and a Prometheus exporter to expose them.

- **Instrument Types**:
  - `Histogram`: For stage durations (e.g., `quant_stage_duration_seconds`).
  - `Counter`: For stage outcomes (e.g., `quant_stage_total`).
  - `Gauge`: For resource usage and active tasks.

### 2.2 Exposure Mechanism
Since the quantitative platform consists of short-lived batch jobs (pipelines), we have two options:
1. **Pushgateway**: For standard CLI/batch runs where a scraper cannot reach the ephemeral process.
2. **Prometheus Exporter (HTTP)**: For long-running services (e.g., Prefect workers, Ray cluster head).

**Initial Implementation**: Focus on **Pushgateway** integration for pipeline runs.

## 3. Telemetry Package Update

### 3.1 `PrometheusExporter`
Update `tradingview_scraper/telemetry/provider.py` to support Prometheus Pushgateway.

```python
def initialize(..., prometheus_endpoint: str = None):
    # Setup Prometheus exporter
    pass
```

### 3.2 Automatic Emission
The `@trace_span` decorator already calculates duration. We will extend it to also increment the corresponding Prometheus instruments.

## 4. Metric Schema

| Metric Name | Type | Labels |
| :--- | :--- | :--- |
| `quant_stage_duration_seconds` | Histogram | `stage_id`, `profile`, `run_id` |
| `quant_stage_total` | Counter | `stage_id`, `status` (success/failure) |
| `quant_engine_resource_usage` | Gauge | `resource_type` (cpu/mem), `node` |

## 5. TDD Strategy
- **`tests/test_prometheus_metrics.py`**:
    - Mock the Prometheus Pushgateway.
    - Execute a decorated function.
    - Verify that the metrics are formatted correctly in the push payload.

## 6. Implementation Roadmap
1. Update `TelemetryProvider` to include Prometheus SDK setup.
2. Update `@trace_span` to emit metrics to the Prometheus provider.
3. Add `TV_PROMETHEUS_PUSHGATEWAY` environment variable support.
