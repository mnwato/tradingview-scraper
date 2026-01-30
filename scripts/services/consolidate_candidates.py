import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from tradingview_scraper.pipelines.selection.base import FoundationHealthRegistry
from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.candidates import normalize_candidate_record

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("consolidate_candidates")


def consolidate(run_id: str, output_path: str | None = None):
    settings = get_settings()
    export_dir = settings.export_dir / run_id
    if not output_path:
        output_path = str(settings.lakehouse_dir / "portfolio_candidates.json")

    registry = FoundationHealthRegistry(path=settings.lakehouse_dir / "foundation_health.json")

    if not export_dir.exists():
        logger.error(f"Export directory not found: {export_dir}")
        return

    strict_schema = bool(settings.strict_health) or os.getenv("TV_STRICT_CANDIDATE_SCHEMA") == "1"

    by_symbol: Dict[str, Dict[str, Any]] = {}
    dropped_invalid = 0
    dropped_toxic = 0

    # Find all .json files, excluding 'ohlc_' prefix just in case (though we fixed that)
    files = sorted(export_dir.glob("*.json"))
    logger.info(f"Found {len(files)} candidate files in {export_dir}")

    for file_path in files:
        if file_path.name.startswith("ohlc_"):
            continue

        try:
            with open(file_path, "r") as f:
                content = json.load(f)

            # Handle {meta, data} envelope
            candidates = []
            if isinstance(content, dict):
                if "data" in content and isinstance(content["data"], list):
                    candidates = content["data"]
                elif "symbol" in content:  # Single object? Unlikely based on schema
                    candidates = [content]
            elif isinstance(content, list):
                candidates = content

            # Extract and dedup
            count = 0
            for cand in candidates:
                try:
                    normalized = normalize_candidate_record(cand, strict=strict_schema)
                except Exception:
                    if strict_schema:
                        raise
                    dropped_invalid += 1
                    continue

                if not normalized:
                    dropped_invalid += 1
                    continue

                sym = normalized.get("symbol")
                if not sym:
                    dropped_invalid += 1
                    continue

                # Registry Veto (Fail-fast in consolidation)
                if not registry.is_healthy(sym) and sym in registry.data:
                    reg_entry = registry.data[sym]
                    if reg_entry.get("status") == "toxic":
                        logger.debug(f"Consolidation Gate: Dropping known TOXIC asset: {sym}")
                        dropped_toxic += 1
                        continue

                existing = by_symbol.get(sym)
                if existing is None:
                    by_symbol[sym] = normalized
                    count += 1
                    continue

                # Merge metadata deterministically for duplicates (keep first canonical fields).
                existing_meta = existing.get("metadata") if isinstance(existing.get("metadata"), dict) else {}
                new_meta = normalized.get("metadata") if isinstance(normalized.get("metadata"), dict) else {}
                for k, v in new_meta.items():
                    existing_meta.setdefault(k, v)
                existing["metadata"] = existing_meta

                # Opportunistically fill missing optional fields (first non-null wins).
                for opt_key in ["sector", "industry", "market_cap_rank", "volume_24h"]:
                    if existing.get(opt_key) is None and normalized.get(opt_key) is not None:
                        existing[opt_key] = normalized.get(opt_key)

            logger.debug(f"Processed {file_path}: added {count} candidates")

        except Exception as e:
            if strict_schema:
                raise
            logger.error(f"Failed to process {file_path}: {e}")

    all_candidates: List[Dict[str, Any]] = [by_symbol[k] for k in sorted(by_symbol.keys())]
    logger.info(f"Consolidated {len(all_candidates)} unique candidates from run {run_id}.")
    if dropped_invalid:
        logger.warning("Dropped %s invalid candidate records while consolidating (strict=%s).", dropped_invalid, strict_schema)
    if dropped_toxic:
        logger.warning("Dropped %s TOXIC assets found in health registry.", dropped_toxic)

    # Write output
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w") as f:
        json.dump(all_candidates, f, indent=2)

    logger.info(f"Wrote to {out_p}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, help="Run ID to consolidate export files from")
    parser.add_argument("--output", default=None, help="Output path")
    args = parser.parse_args()

    consolidate(args.run_id, args.output)
