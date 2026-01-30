import argparse
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from tradingview_scraper.settings import get_settings
from tradingview_scraper.symbols.overview import Overview

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ingest_features")


class FeatureIngestionService:
    def __init__(self, lakehouse_dir: Path | None = None, workers: int = 10):
        settings = get_settings()
        self.lakehouse_dir = lakehouse_dir or settings.lakehouse_dir
        self.features_dir = self.lakehouse_dir / "features" / "tv_technicals_1d"
        self.features_dir.mkdir(parents=True, exist_ok=True)
        self.workers = workers
        self.overview = Overview()

    def fetch_technicals_single(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch technicals for a single symbol."""
        try:
            # Multi-Timeframe Configuration
            timeframes = {
                "1m": "1",
                "3m": "3",
                "5m": "5",
                "15m": "15",
                "30m": "30",
                "1h": "60",
                "2h": "120",
                "4h": "240",
                "1d": "",
                "1W": "1W",
                "1M": "1M",
            }
            # Key technicals to expand across timeframes
            mtf_fields = [
                "Recommend.All",
                "Recommend.MA",
                "Recommend.Other",
                "RSI",
                "ADX",
                "AO",
                "CCI20",
                "Stoch.K",
                "Stoch.D",
                "MACD.macd",
                "MACD.signal",
                # Price Performance & Volume
                "change",  # Percent change
                "change_abs",  # Absolute change
                "close",  # Close price
                "volume",  # Volume
                "gap",  # Gap percent
                "high",  # High price
                "low",  # Low price
                "open",  # Open price
            ]

            request_fields = []

            # 1. Add Base Fields (Volatility, Performance - keep default 1d)
            request_fields.extend(Overview.VOLATILITY_FIELDS)
            request_fields.extend(Overview.PERFORMANCE_FIELDS)

            # 2. Add MTF Fields
            for field in mtf_fields:
                for _, suffix in timeframes.items():
                    if suffix:
                        request_fields.append(f"{field}|{suffix}")
                    else:
                        request_fields.append(field)

            # Deduplicate
            request_fields = sorted(list(set(request_fields)))

            res = self.overview.get_symbol_overview(symbol, fields=request_fields)

            if res["status"] == "success" and res.get("data"):
                data = res["data"]

                # Base Record
                record = {
                    "symbol": symbol,
                    "volatility_d": data.get("Volatility.D"),
                    "perf_w": data.get("Perf.W"),
                    "perf_1m": data.get("Perf.1M"),
                    "perf_3m": data.get("Perf.3M"),
                    "perf_6m": data.get("Perf.6M"),
                    "perf_y": data.get("Perf.Y"),
                    "perf_3y": data.get("Perf.3Y"),
                    "perf_5y": data.get("Perf.5Y"),
                    "perf_all": data.get("Perf.All"),
                    "perf_ytd": data.get("Perf.YTD"),
                }

                # Map MTF Fields to flattened schema
                # Schema: {feature}_{interval} (e.g. rsi_1h, recommend_all_1m)
                for field in mtf_fields:
                    clean_name = field.lower().replace(".", "_")
                    for tf_name, suffix in timeframes.items():
                        lookup_key = f"{field}|{suffix}" if suffix else field
                        val = data.get(lookup_key)

                        # Store with interval suffix
                        # e.g. recommend_all_1d, recommend_all_1h
                        col_name = f"{clean_name}_{tf_name}"
                        record[col_name] = val

                return record
        except Exception as e:
            logger.warning(f"Failed to fetch technicals for {symbol}: {e}")
        return None

    def ingest_batch(self, symbols: List[str]):
        """Fetch and store technicals for a batch of symbols."""
        if not symbols:
            return

        logger.info(f"Fetching technicals for {len(symbols)} symbols...")
        results = []

        # Current UTC timestamp for the snapshot
        now_ts = int(time.time())
        # Partition Date
        partition_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            for i, result in enumerate(executor.map(self.fetch_technicals_single, symbols)):
                if result:
                    result["timestamp"] = now_ts
                    results.append(result)
                if (i + 1) % 50 == 0:
                    logger.info(f"Processed {i + 1}/{len(symbols)}")

        if not results:
            logger.warning("No technicals fetched.")
            return

        # Create DataFrame
        df = pd.DataFrame(results)

        # Define Partition Path
        part_dir = self.features_dir / f"date={partition_date}"
        part_dir.mkdir(parents=True, exist_ok=True)

        # Save Parquet
        # We append a timestamp/uuid to filename to avoid overwrites in case of multiple runs per day?
        # Or just overwrite "part-0.parquet" if we assume one batch per day?
        # Let's use a timestamped filename to allow multiple batches.
        filename = f"part-{now_ts}.parquet"
        out_path = part_dir / filename

        df.to_parquet(out_path, index=False)
        logger.info(f"Saved {len(df)} records to {out_path}")

    def process_candidate_file(self, file_path: Path):
        """Load symbols from a candidates JSON file."""
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        symbols = []
        # Handle list or dict envelope
        candidates = data.get("data", []) if isinstance(data, dict) else data

        if isinstance(candidates, list):
            for c in candidates:
                if isinstance(c, dict) and "symbol" in c:
                    symbols.append(c["symbol"])
                elif isinstance(c, str):
                    symbols.append(c)

        # Dedupe
        symbols = sorted(list(set(symbols)))
        self.ingest_batch(symbols)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, help="Path to candidates.json")
    parser.add_argument("--lakehouse", default=None, help="Lakehouse root directory")
    parser.add_argument("--workers", type=int, default=10, help="Concurrency level")
    args = parser.parse_args()

    lakehouse_path = Path(args.lakehouse) if args.lakehouse else None
    service = FeatureIngestionService(lakehouse_dir=lakehouse_path, workers=args.workers)
    service.process_candidate_file(Path(args.candidates))
