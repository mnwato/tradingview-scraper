import unittest
import json
import os
from pathlib import Path
from opentelemetry import trace
from tradingview_scraper.telemetry.provider import TelemetryProvider
from tradingview_scraper.telemetry.exporter import ForensicSpanExporter


class TestTelensicReporting(unittest.TestCase):
    def setUp(self):
        self.test_file = Path("tests/data/test_forensic_trace.json")
        self.test_file.parent.mkdir(parents=True, exist_ok=True)
        if self.test_file.exists():
            self.test_file.unlink()

    def test_span_export_to_json(self):
        """Verify that OTel spans are correctly captured and written to JSON."""
        exporter = ForensicSpanExporter(self.test_file)

        # We need a tracer to emit spans
        provider = TelemetryProvider()
        provider.initialize(service_name="test-forensic", console_export=False)

        # Add the exporter manually for this test if not using the singleton initialization
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test_stage", attributes={"profile": "test"}):
            pass

        # Flush/Save
        exporter.save()

        self.assertTrue(self.test_file.exists())
        with open(self.test_file, "r") as f:
            data = json.load(f)

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "test_stage")
        self.assertEqual(data[0]["attributes"]["profile"], "test")

    def tearDown(self):
        if self.test_file.exists():
            self.test_file.unlink()


if __name__ == "__main__":
    unittest.main()
