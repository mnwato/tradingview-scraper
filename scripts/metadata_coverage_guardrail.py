from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from scripts.enrich_candidates_metadata import enrich_metadata
from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.audit import AuditLedger

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("metadata_guardrail")


@dataclass
class MetadataTarget:
    label: str
    candidates: Path
    returns: Optional[Path]


def parse_target(spec: str) -> MetadataTarget:
    parts = spec.split(":")
    if len(parts) < 2 or len(parts) > 3:
        raise ValueError("target must be label:candidates_path[:returns_path]")
    label = parts[0]
    cand_path = Path(parts[1])
    returns_path = Path(parts[2]) if len(parts) == 3 else None
    return MetadataTarget(label=label, candidates=cand_path, returns=returns_path)


def coverage_for(path: Path) -> Tuple[int, int, float]:
    if not path.exists():
        return 0, 0, 0.0
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0, 0, 0.0

    def has_metadata(entry: dict) -> bool:
        return all(entry.get(field) is not None for field in ["tick_size", "lot_size", "price_precision"])

    total = len(entries)
    covered = sum(1 for entry in entries if has_metadata(entry))
    pct = (covered / total) if total else 0.0
    return total, covered, pct


def append_log(run_dir: Path, lines: Iterable[str]) -> None:
    log_dir = run_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "metadata_coverage.log"
    with open(log_path, "a", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line + "\n")


def record_audit(run_dir: Path, metrics: Dict[str, Dict[str, float]], threshold: float, status: str) -> None:
    settings = get_settings()
    if not settings.features.feat_audit_ledger:
        return

    ledger = AuditLedger(run_dir)
    summary = {label: values for label, values in metrics.items()}
    output_hashes = {"metadata_coverage": hashlib.sha256(json.dumps(summary, sort_keys=True).encode("utf-8")).hexdigest()}
    ledger.record_outcome(
        step="metadata_coverage",
        status=status,
        output_hashes=output_hashes,
        metrics={
            "threshold": threshold,
            "coverage": {label: values["pct"] for label, values in metrics.items()},
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Guard metadata coverage and run enrichment when needed.")
    parser.add_argument(
        "--target",
        action="append",
        required=True,
        help="label:candidates_path[:returns_path]; repeatable for canonical/selected catalogs",
    )
    parser.add_argument("--threshold", type=float, default=0.95, help="Coverage threshold (0-1 range)")
    args = parser.parse_args()

    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()
    coverage_metrics: Dict[str, Dict[str, float]] = {}
    log_lines: list[str] = []
    failures: list[str] = []

    targets = [parse_target(value) for value in args.target]

    for target in targets:
        total, covered, pct = coverage_for(target.candidates)
        enriched = False

        if pct < args.threshold:
            logger.info(f"{target.label}: coverage {pct:.2%} below threshold {args.threshold:.2%}, running enrichment")
            enrich_metadata(
                candidates_path=str(target.candidates),
                returns_path=str(target.returns) if target.returns else "data/lakehouse/portfolio_returns.pkl",
            )
            total, covered, pct = coverage_for(target.candidates)
            enriched = True

        status = "pass" if pct >= args.threshold else "fail"
        if status == "fail":
            failures.append(target.label)

        coverage_metrics[target.label] = {"total": float(total), "covered": float(covered), "pct": pct}

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"{ts} | {settings.run_id} | {target.label} | {pct:.2%} ({covered}/{total}) | status={status}" + (" | enriched" if enriched else "")
        log_lines.append(line)

    append_log(run_dir, log_lines)
    record_audit(run_dir, coverage_metrics, args.threshold, "failure" if failures else "success")

    if failures:
        logger.error(f"Metadata coverage below threshold for: {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
