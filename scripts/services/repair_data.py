import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Assume PersistentDataLoader is available via PYTHONPATH or install
try:
    from tradingview_scraper.symbols.stream.metadata import DataProfile, get_symbol_profile
    from tradingview_scraper.symbols.stream.persistent_loader import PersistentDataLoader
except ImportError:
    PersistentDataLoader = None  # type: ignore
    DataProfile = None  # type: ignore
    get_symbol_profile = None  # type: ignore

from tradingview_scraper.pipelines.selection.base import FoundationHealthRegistry
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("repair_data")


class RepairService:
    def __init__(self, lakehouse_dir: Path | None = None):
        settings = get_settings()
        self.lakehouse_dir = lakehouse_dir or settings.lakehouse_dir
        self.registry = FoundationHealthRegistry(path=self.lakehouse_dir / "foundation_health.json")

        if PersistentDataLoader:
            self.loader = PersistentDataLoader(lakehouse_path=str(self.lakehouse_dir))
        else:
            self.loader = None
            logger.error("PersistentDataLoader not available.")

    def load_candidates(self, candidates_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load candidates from file or return empty."""
        if not candidates_path:
            # Default to lakehouse candidates
            candidates_path = str(self.lakehouse_dir / "portfolio_candidates.json")

        path = Path(candidates_path)
        if not path.exists():
            # Fallback to raw
            path = self.lakehouse_dir / "portfolio_candidates_raw.json"

        if not path.exists():
            logger.error(f"Candidates file not found: {candidates_path}")
            return []

        try:
            with open(path, "r") as f:
                data = json.load(f)
                if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                    return data["data"]
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            logger.error(f"Failed to load candidates: {e}")
            return []

    def repair(self, candidates: List[Dict[str, Any]], asset_type: str = "all", max_fills: int = 10, timeout: int = 60):
        """
        Repair gaps for the provided candidates.
        """
        if not self.loader:
            return

        targets = []
        for c in candidates:
            symbol = c.get("symbol")
            if not symbol or not self.loader:
                continue

            # Determine profile for efficient filtering
            # We can use the catalog attached to loader, or the helper
            meta = self.loader.catalog.get_instrument(symbol)

            profile = None
            if get_symbol_profile:
                profile = get_symbol_profile(symbol, meta)

            is_crypto = profile == DataProfile.CRYPTO if DataProfile else False

            if asset_type == "crypto" and not is_crypto:
                continue
            if asset_type == "trad" and is_crypto:
                continue

            targets.append((symbol, profile))

        logger.info(f"Starting repair for {len(targets)} symbols (Filter: {asset_type})")

        total_filled = 0
        symbols_repaired = 0

        for i, (symbol, profile) in enumerate(targets):
            logger.info(f"[{i + 1}/{len(targets)}] Checking {symbol}...")

            retries = 2
            for attempt in range(retries + 1):
                try:
                    filled = self.loader.repair(symbol, interval="1d", max_depth=500, max_fills=max_fills, total_timeout=timeout, profile=profile)
                    if filled > 0:
                        total_filled += filled
                        symbols_repaired += 1
                        logger.info(f"  -> Filled {filled} gaps.")
                        self.registry.update_status(symbol, status="healthy", gaps_filled=filled)
                    else:
                        # If no gaps found and already healthy, keep it.
                        # If it was toxic, maybe repair fixed it?
                        # (Usually repair only fills gaps, doesn't fix price stalls)
                        pass

                    self.registry.save()
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < retries:
                        sleep_time = 30 * (attempt + 1)
                        logger.warning(f"  Rate limit. Sleeping {sleep_time}s...")
                        time.sleep(sleep_time)
                        continue
                    logger.error(f"  Failed to repair {symbol}: {e}")
                    break

        logger.info("=" * 40)
        logger.info(f"REPAIR COMPLETE. Symbols: {symbols_repaired}, Total Fills: {total_filled}")
        logger.info("=" * 40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair Data Gaps Service")
    parser.add_argument("--candidates", help="Path to candidates file")
    parser.add_argument("--type", choices=["crypto", "trad", "all"], default="all", help="Asset type filter")
    parser.add_argument("--max-fills", type=int, default=15, help="Max gaps to fill per symbol")
    parser.add_argument("--lakehouse", help="Lakehouse root")

    args = parser.parse_args()

    lakehouse_arg = Path(args.lakehouse) if args.lakehouse else None
    service = RepairService(lakehouse_dir=lakehouse_arg)
    candidates = service.load_candidates(args.candidates)

    if candidates:
        service.repair(candidates, asset_type=args.type, max_fills=args.max_fills)
    else:
        logger.warning("No candidates found to repair.")
