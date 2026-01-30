import unittest
from opentelemetry import trace
from tradingview_scraper.telemetry.provider import TelemetryProvider
from tradingview_scraper.telemetry.context import inject_trace_context, extract_trace_context


class TestDistributedTracing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = TelemetryProvider()
        cls.provider.initialize(service_name="test-distributed", console_export=False)

    def test_context_injection_extraction(self):
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("parent_span") as parent:
            parent_ctx = parent.get_span_context()
            carrier = {}
            inject_trace_context(carrier)

            # Carrier should have traceparent
            self.assertIn("traceparent", carrier)

            # Now extract in a "different" process
            extracted_ctx = extract_trace_context(carrier)

            with tracer.start_as_current_span("child_span", context=extracted_ctx) as child:
                child_ctx = child.get_span_context()

                # Trace IDs should match
                self.assertEqual(parent_ctx.trace_id, child_ctx.trace_id)
                # Child should be different from parent
                self.assertNotEqual(parent_ctx.span_id, child_ctx.span_id)


if __name__ == "__main__":
    unittest.main()
