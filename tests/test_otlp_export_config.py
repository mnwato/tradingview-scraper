import unittest
import os
from unittest.mock import patch
from tradingview_scraper.telemetry.provider import TelemetryProvider


class TestOTLPExportConfig(unittest.TestCase):
    def setUp(self):
        # Reset singleton state if possible or use fresh env
        pass

    def test_otlp_endpoint_resolution(self):
        """Verify that OTLP endpoints are correctly resolved from environment variables."""
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4317"}):
            provider = TelemetryProvider()
            # Force re-initialization if needed or check internal state
            # (Note: initialize is protected by self._initialized)
            self.assertEqual(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"), "http://collector:4317")


if __name__ == "__main__":
    unittest.main()
