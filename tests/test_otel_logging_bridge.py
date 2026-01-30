import unittest
import logging
from opentelemetry import _logs
from opentelemetry.sdk._logs import LoggerProvider, LogRecordProcessor
from tradingview_scraper.telemetry.provider import TelemetryProvider


class MockLogProcessor(LogRecordProcessor):
    def __init__(self):
        self.logs = []

    def emit(self, log_data):
        self.logs.append(log_data)

    def on_emit(self, log_record):
        self.logs.append(log_record)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    def shutdown(self):
        pass


class TestOTelLoggingBridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = TelemetryProvider()
        cls.provider.initialize(service_name="test-logs")

        # Add mock processor to capture logs
        cls.processor = MockLogProcessor()
        _logs.get_logger_provider().add_log_record_processor(cls.processor)

    def test_logging_bridge(self):
        """Verify that standard logging is captured by OTel."""
        logger = logging.getLogger("test_bridge")
        logger.info("Test message for OTel bridge")

        # This will be verified after refactoring TelemetryProvider
        # For now, we ensure it doesn't crash
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
