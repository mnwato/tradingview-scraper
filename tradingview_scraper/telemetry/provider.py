import logging
import os
import threading
from pathlib import Path

from typing import Any, Dict, List, Optional

from opentelemetry import metrics, trace, _logs
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter

logger = logging.getLogger(__name__)


class TelemetryProvider:
    """
    Singleton manager for OpenTelemetry standardization (Tracing, Metrics, Logs).
    Follows OTel standard APIs and supports backend-neutral OTLP delivery.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TelemetryProvider, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def initialize(self, service_name: str = "quant-platform", console_export: bool = False, prometheus_endpoint: Optional[str] = None):
        if self._initialized:
            return

        resource = Resource.create({"service.name": service_name})
        self.prometheus_endpoint = prometheus_endpoint

        # 1. Tracing Setup
        tracer_provider = TracerProvider(resource=resource)
        if console_export:
            tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        # OTLP Trace Exporter
        if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

                tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
                logger.info("OTel: OTLP Trace exporter registered")
            except ImportError:
                logger.warning("OTLP Trace exporter requested but not installed.")

        trace.set_tracer_provider(tracer_provider)
        self.tracer = trace.get_tracer(__name__)

        # 2. Metrics Setup
        metric_readers = []
        if console_export:
            metric_readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))

        # OTLP Metric Exporter
        if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
            try:
                from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

                metric_readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
                logger.info("OTel: OTLP Metric exporter registered")
            except ImportError:
                logger.warning("OTLP Metric exporter requested but not installed.")

        # Prometheus (Legacy support via reader)
        if self.prometheus_endpoint:
            try:
                from opentelemetry.exporter.prometheus import PrometheusMetricReader

                metric_readers.append(PrometheusMetricReader())
            except ImportError:
                logger.warning("Prometheus exporter requested but not installed.")

        meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
        metrics.set_meter_provider(meter_provider)
        self.meter = metrics.get_meter(__name__)

        # Pre-register common instruments
        self.duration_histogram = self.meter.create_histogram("quant_stage_duration_seconds", description="Duration of pipeline stages", unit="s")
        self.success_counter = self.meter.create_counter("quant_stage_success_total", description="Count of successful stage completions")
        self.failure_counter = self.meter.create_counter("quant_stage_failure_total", description="Count of stage failures")

        # 3. Logs Setup (OTel Standard)
        logger_provider = LoggerProvider(resource=resource)
        if console_export:
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(ConsoleLogExporter()))

        # OTLP Log Exporter
        if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
            try:
                from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

                logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
                logger.info("OTel: OTLP Log exporter registered")
            except ImportError:
                logger.warning("OTLP Log exporter requested but not installed.")

        _logs.set_logger_provider(logger_provider)

        # Bridge to standard Python logging
        handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)

        self._initialized = True

    def flush_metrics(self, job_name: str = "quant_pipeline", grouping_key: Optional[dict] = None):
        """Standard OTel metrics flushing."""
        # Standard OTel MetricReaders flush automatically or on shutdown
        pass

    def register_forensic_exporter(self, output_path: Path):
        """Registers a run-specific forensic exporter."""
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from tradingview_scraper.telemetry.exporter import ForensicSpanExporter

        exporter = ForensicSpanExporter(output_path)
        # Use standard API to add processor
        tp = trace.get_tracer_provider()
        if isinstance(tp, TracerProvider):
            tp.add_span_processor(SimpleSpanProcessor(exporter))
        return exporter

    @property
    def is_initialized(self) -> bool:
        return self._initialized
