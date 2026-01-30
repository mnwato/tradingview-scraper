import argparse
import json
import logging
import os
from typing import Any, Dict

import numpy as np
import pandas as pd

from tradingview_scraper.execution.metadata import ExecutionMetadataCatalog
from tradingview_scraper.settings import get_settings
from tradingview_scraper.symbols.stream.metadata import ExchangeCatalog, MetadataCatalog

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("metadata_enrichment")


def get_asset_class(symbol: str) -> str:
    """Heuristic to determine asset class from symbol."""
    if ":" not in symbol:
        # Fallback for cryptos that might not have a prefix in some contexts
        if any(pair in symbol for pair in ["USDT", "USDC", "BTC", "ETH"]):
            return "CRYPTO"
        return "UNKNOWN"
    exchange = symbol.split(":")[0].upper()
    if exchange in ["BINANCE", "OKX", "BYBIT", "BITGET", "PHEMEX", "MEXC", "DERIBIT", "BITMEX"]:
        return "CRYPTO"
    if exchange in ["NYSE", "NASDAQ", "AMEX", "BATS", "ARCA"]:
        return "EQUITY"
    if exchange in ["OANDA", "THINKMARKETS", "FOREXCOM", "SAXO", "IG"]:
        return "FOREX"
    if exchange in ["CME", "CBOT", "NYMEX", "COMEX", "ICE", "EUREX"]:
        return "FUTURES"
    return "CFD"


def get_defaults(asset_class: str, symbol: str) -> Dict[str, Any]:
    """Returns institutional defaults based on asset class."""
    if asset_class == "CRYPTO":
        is_perp = symbol.endswith(".P")
        return {
            "tick_size": 0.00000001 if not is_perp else 0.01,
            "lot_size": 0.001,
            "price_precision": 8 if not is_perp else 2,
            "min_qty": 0.001,
            "value_traded": 1e8,
        }
    if asset_class == "FOREX":
        is_jpy = "JPY" in symbol
        return {
            "tick_size": 0.001 if is_jpy else 0.00001,
            "lot_size": 1000.0,
            "price_precision": 3 if is_jpy else 5,
            "min_qty": 1000.0,
            "value_traded": 1e9,
        }
    if asset_class == "EQUITY":
        return {
            "tick_size": 0.01,
            "lot_size": 1.0,
            "price_precision": 2,
            "min_qty": 1.0,
            "value_traded": 5e8,
        }
    # Default for FUTURES/CFD
    return {
        "tick_size": 0.01,
        "lot_size": 1.0,
        "price_precision": 2,
        "min_qty": 1.0,
        "value_traded": 1e8,
    }


def enrich_metadata(candidates_path: str = "data/lakehouse/portfolio_candidates_raw.json", returns_path: str = "data/lakehouse/portfolio_returns.pkl"):
    if not os.path.exists(candidates_path):
        logger.error(f"Candidates file not found: {candidates_path}")
        return

    settings = get_settings()
    with open(candidates_path, "r") as f:
        data = json.load(f)

    # Initialize Catalogs
    exec_catalog = ExecutionMetadataCatalog()
    sym_catalog = MetadataCatalog()
    ex_catalog = ExchangeCatalog()

    # Handle both list (raw candidates) and dict (refined meta)
    if isinstance(data, list):
        candidates = data
        candidate_map = {c["symbol"]: c for c in candidates}
    else:
        # Dictionary format from prepare_portfolio_data
        candidate_map = data
        candidates = list(data.values())
        # Ensure 'symbol' key exists in dictionaries if missing
        for s, c in candidate_map.items():
            if "symbol" not in c:
                c["symbol"] = s

    # 1. Synchronize with Returns Universe
    if os.path.exists(returns_path):
        try:
            if returns_path.endswith(".parquet"):
                returns = pd.read_parquet(returns_path)
            else:
                returns = pd.read_pickle(returns_path)
            active_symbols = returns.columns.tolist()
        except Exception as e:
            logger.error(f"Error loading returns matrix for enrichment: {e}")
            active_symbols = []

        added_count = 0
        bench_set = set(settings.benchmark_symbols)
        for symbol in active_symbols:
            if symbol not in candidate_map:
                asset_class = get_asset_class(symbol)
                is_bench = symbol in bench_set
                new_cand = {
                    "symbol": symbol,
                    "identity": symbol.split(":")[-1] if ":" in symbol else symbol,
                    "direction": "LONG",
                    "value_traded": 1e9,
                    "sector": "Crypto" if asset_class == "CRYPTO" else "Financial",
                    "asset_class": asset_class,
                    "is_benchmark": is_bench,
                }
                candidates.append(new_cand)
                candidate_map[symbol] = new_cand
                added_count += 1
        if added_count > 0:
            logger.info(f"➕ Added {added_count} missing symbols from returns matrix.")

    # 2. Multi-Stage Enrichment (Catalog -> Defaults)
    enriched_count = 0
    catalog_hits = 0

    for c in candidates:
        symbol = c.get("symbol", "UNKNOWN")
        exchange = symbol.split(":")[0].upper() if ":" in symbol else "UNKNOWN"
        asset_class = c.get("asset_class") or get_asset_class(symbol)
        c["asset_class"] = asset_class

        is_enriched = False

        # A. Try Symbol Catalog (Structural Meta)
        sym_meta = sym_catalog.get_instrument(symbol)
        if sym_meta:
            for key in ["description", "sector", "industry", "country", "type"]:
                if key in sym_meta and (c.get(key) is None or c.get(key) == "N/A" or c.get(key) == "UNKNOWN"):
                    c[key] = sym_meta[key]
                    is_enriched = True

            # Use pricescale if tick_size is missing
            if c.get("tick_size") is None and sym_meta.get("tick_size"):
                c["tick_size"] = sym_meta["tick_size"]
                is_enriched = True

        # B. Try Execution Catalog (Venue Limits)
        exec_limits = exec_catalog.get_limits(symbol, exchange)
        if exec_limits:
            catalog_hits += 1
            for key in ["lot_size", "tick_size", "min_notional", "step_size", "maker_fee", "taker_fee"]:
                val = getattr(exec_limits, key, None)
                if val is not None and val > 0:
                    c[key] = val
                    is_enriched = True

            # Map step_size to lot_size if lot_size is missing but step_size exists
            if c.get("lot_size") is None and getattr(exec_limits, "step_size", 0) > 0:
                c["lot_size"] = exec_limits.step_size
                is_enriched = True

        # C. Try Exchange Catalog
        ex_meta = ex_catalog.get_exchange(exchange)
        if ex_meta:
            if c.get("timezone") is None:
                c["timezone"] = ex_meta.get("timezone")
                is_enriched = True

        # D. Apply Institutional Defaults (Final Fallback)
        defaults = get_defaults(asset_class, symbol)
        for key, val in defaults.items():
            current_val = c.get(key)

            # Special handling for liquidity fields
            if key == "value_traded":
                if current_val is None or (isinstance(current_val, float) and (np.isnan(current_val) or current_val <= 0.0)):
                    c[key] = val
                    is_enriched = True
            # General missing check
            elif current_val is None or (isinstance(current_val, float) and np.isnan(current_val)):
                c[key] = val
                is_enriched = True
            elif isinstance(current_val, str) and (current_val == "N/A" or current_val == ""):
                c[key] = val
                is_enriched = True

        if is_enriched:
            enriched_count += 1

    # 3. Save back in original format
    with open(candidates_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"✅ Total candidates: {len(candidates)}. Enriched {enriched_count} ({catalog_hits} catalog hits).")


def main() -> None:
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    default_candidates = str(run_dir / "data" / "portfolio_candidates_raw.json")
    default_returns = str(run_dir / "data" / "returns_matrix.parquet")

    parser = argparse.ArgumentParser(description="Enrich candidate manifests with catalog and default metadata.")
    parser.add_argument("--candidates", default=os.getenv("CANDIDATES_RAW", default_candidates), help="Path to the candidates JSON file to enrich")
    parser.add_argument("--returns", default=os.getenv("RETURNS_MATRIX", default_returns), help="Optional returns matrix to align against")
    args = parser.parse_args()

    enrich_metadata(candidates_path=args.candidates, returns_path=args.returns)


if __name__ == "__main__":
    main()
