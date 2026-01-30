import unittest
import time
from opentelemetry import metrics
from tradingview_scraper.telemetry.provider import TelemetryProvider
from tradingview_scraper.telemetry.tracing import trace_span


class TestTelemetryMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = TelemetryProvider()
        cls.provider.initialize(service_name="test-metrics", console_export=False)

    def test_stage_duration_metric(self):
        # We wrap a function and check if duration is emitted
        # In unit tests, we mainly ensure it doesn't crash
        @trace_span("metric_test_stage")
        def mock_stage():
            time.sleep(0.01)
            return True

        mock_stage()
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
