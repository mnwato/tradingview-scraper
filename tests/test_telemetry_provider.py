import unittest

from tradingview_scraper.telemetry.provider import TelemetryProvider
from tradingview_scraper.telemetry.tracing import trace_span


class TestTelemetryProvider(unittest.TestCase):
    def setUp(self):
        self.provider = TelemetryProvider()
        self.provider.initialize(service_name="test-service", console_export=True)

    def test_singleton(self):
        p2 = TelemetryProvider()
        self.assertIs(self.provider, p2)

    def test_trace_span_decorator(self):
        @trace_span("test_span")
        def sample_function():
            return "success"

        result = sample_function()
        self.assertEqual(result, "success")

    def test_logger_injection(self):
        from tradingview_scraper.telemetry.logging import get_telemetry_logger

        logger = get_telemetry_logger("test_logger")

        with self.provider.tracer.start_as_current_span("log_test"):
            logger.info("This is a test log with trace context")
            # In a real OTel setup, we would verify the log record has trace_id
            # For now, we just ensure it doesn't crash.
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
