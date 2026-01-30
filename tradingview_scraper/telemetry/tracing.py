import functools
import time
from typing import Optional

from opentelemetry import metrics, trace

from tradingview_scraper.telemetry.provider import TelemetryProvider


def get_tracer():
    provider = TelemetryProvider()
    if not provider.is_initialized:
        provider.initialize()
    return provider.tracer


def get_meter():
    provider = TelemetryProvider()
    if not provider.is_initialized:
        provider.initialize()
    return provider.meter


def trace_span(name: str, attributes: Optional[dict] = None):
    """Decorator to wrap a function in an OpenTelemetry span and emit metrics."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            provider = TelemetryProvider()

            with tracer.start_as_current_span(name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, v)

                try:
                    result = func(*args, **kwargs)
                    if hasattr(provider, "success_counter"):
                        provider.success_counter.add(1, {"stage_id": name})
                    return result
                except Exception as e:
                    if hasattr(provider, "failure_counter"):
                        provider.failure_counter.add(1, {"stage_id": name, "error_type": type(e).__name__})
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    raise

        return wrapper

    return decorator
