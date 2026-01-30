import logging
import os


def setup_logging(level: int = logging.INFO):
    """
    Globally configures logging to use standard Python logging.
    OTel bridge is now handled via LoggingHandler in TelemetryProvider.
    """
    # Configure root logger
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, force=True)

    # Silence noisy loggers
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)
    logging.getLogger("ray").setLevel(logging.WARNING)


def get_telemetry_logger(name: str) -> logging.Logger:
    """Returns a standard logger. OTel injection is handled globally."""
    logger = logging.getLogger(name)
    return logger
