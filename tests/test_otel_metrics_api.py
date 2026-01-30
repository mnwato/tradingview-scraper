import unittest
from opentelemetry import metrics
from tradingview_scraper.telemetry.provider import TelemetryProvider


class TestOTelMetricsAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = TelemetryProvider()
        cls.provider.initialize(service_name="test-metrics-api")

    def test_meter_availability(self):
        """Verify standard OTel meter instruments."""
        meter = metrics.get_meter("test_meter")
        self.assertIsNotNone(meter)

        counter = meter.create_counter("test_counter")
        counter.add(1, {"attr": "val"})

        # Verify provider has instruments
        self.assertTrue(hasattr(self.provider, "duration_histogram"))


if __name__ == "__main__":
    unittest.main()
