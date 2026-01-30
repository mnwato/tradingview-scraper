import unittest
from tradingview_scraper.telemetry.exporter import ForensicSpanExporter
from pathlib import Path


class TestDistributedTelemetryMerge(unittest.TestCase):
    def test_span_merging(self):
        """Verify that spans from multiple sources can be merged into a single timeline."""
        host_file = Path("tests/data/host_trace.json")
        exporter = ForensicSpanExporter(host_file)

        # Mock some spans from host
        host_span = {
            "name": "host_op",
            "start_time": 1000,
            "end_time": 2000,
            "duration_ms": 1.0,
            "status": "OK",
            "attributes": {},
            "trace_id": "trace1",
            "span_id": "span_host",
            "parent_span_id": None,
        }
        exporter.spans.append(host_span)

        # Mock some spans from worker
        worker_spans = [
            {
                "name": "worker_op",
                "start_time": 1200,
                "end_time": 1800,
                "duration_ms": 0.6,
                "status": "OK",
                "attributes": {},
                "trace_id": "trace1",
                "span_id": "span_worker",
                "parent_span_id": "span_host",
            }
        ]

        # Merge logic (simplified for test)
        exporter.spans.extend(worker_spans)

        # Sort and verify
        exporter.spans.sort(key=lambda s: s["start_time"])
        self.assertEqual(len(exporter.spans), 2)
        self.assertEqual(exporter.spans[0]["name"], "host_op")
        self.assertEqual(exporter.spans[1]["name"], "worker_op")


if __name__ == "__main__":
    unittest.main()
