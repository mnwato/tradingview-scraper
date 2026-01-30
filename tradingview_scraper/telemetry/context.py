from typing import Dict, Optional
from opentelemetry import propagate
from opentelemetry.context.context import Context


def inject_trace_context(carrier: Dict[str, str]) -> None:
    """Injects current trace context into the provided carrier dictionary."""
    propagate.inject(carrier)


def extract_trace_context(carrier: Dict[str, str]) -> Optional[Context]:
    """Extracts trace context from the carrier and returns an OTel Context."""
    return propagate.extract(carrier)
