import json
import logging
from pathlib import Path
from typing import List, Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)


class ForensicSpanExporter(SpanExporter):
    """
    Custom OpenTelemetry Span Exporter that persists spans to a JSON file for forensic auditing.
    """

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.spans = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Captures spans in memory."""
        for span in spans:
            # Standardize attributes
            attrs = {k: v for k, v in span.attributes.items()}

            span_data = {
                "name": span.name,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "duration_ms": (span.end_time - span.start_time) / 1e6,  # nanoseconds to milliseconds
                "status": span.status.status_code.name,
                "attributes": attrs,
                "trace_id": format(span.context.trace_id, "032x"),
                "span_id": format(span.context.span_id, "016x"),
                "parent_span_id": format(span.parent.span_id, "016x") if span.parent else None,
            }
            self.spans.append(span_data)
        return SpanExportResult.SUCCESS

    def save(self):
        """Persists captured spans to disk."""
        if not self.spans:
            logger.debug("ForensicSpanExporter: No spans to save.")
            return

        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(self.spans, f, indent=2)
            logger.info(f"Forensic trace saved to {self.output_path} ({len(self.spans)} spans)")
        except Exception as e:
            logger.error(f"Failed to save forensic trace: {e}")


def get_forensic_summary_md(trace_file: Path) -> str:
    """Generates a markdown summary of the pipeline health from a forensic trace file."""
    if not trace_file.exists():
        return "*Forensic trace missing.*"

    try:
        with open(trace_file, "r") as f:
            spans = json.load(f)

        if not spans:
            return "*No spans recorded in trace.*"

        # Sort spans by start time
        spans.sort(key=lambda s: s["start_time"])

        lines = []
        lines.append("### 🕒 Pipeline Health (Forensic Audit)")
        lines.append("| Stage / Step | Status | Duration (s) | Start Time |")
        lines.append("| :--- | :--- | :--- | :--- |")

        from datetime import datetime

        for s in spans:
            name = s["name"]
            status = s["status"]
            # Convert ns to s for display
            dur = s["duration_ms"] / 1000.0

            # Formatting timestamp
            # start_time is in ns, convert to seconds
            start_dt = datetime.fromtimestamp(s["start_time"] / 1e9).strftime("%H:%M:%S")

            status_mark = "✅" if status == "UNSET" or status == "OK" else "❌"
            if status == "ERROR":
                status_mark = "❌"

            lines.append(f"| {name} | {status_mark} {status} | {dur:.2f}s | {start_dt} |")

        return "\n".join(lines)
    except Exception as e:
        return f"*Error parsing forensic trace: {e}*"
