import argparse
import json
import logging
import sys
from typing import Any, Dict, List, Optional

import ccxt
import pandas as pd

from tradingview_scraper.execution.metadata import ExecutionMetadataCatalog

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fetch_execution_metadata")


def resolve_ccxt_exchange(venue: str) -> Optional[ccxt.Exchange]:
    """
    Maps venue name to CCXT exchange instance.
    """
    venue_lower = venue.lower()

    # Common mappings
    if "binance" in venue_lower:
        return ccxt.binance()
    elif "bybit" in venue_lower:
        return ccxt.bybit()
    elif "okx" in venue_lower:
        return ccxt.okx()
    elif "kraken" in venue_lower:
        return ccxt.kraken()
    elif "coinbase" in venue_lower:
        return ccxt.coinbase()
    elif "bitget" in venue_lower:
        return ccxt.bitget()

    return None


def normalize_symbol_for_ccxt(tv_symbol: str, venue: str) -> str:
    """
    Converts TradingView symbol (e.g. BTCUSDT) to CCXT format (e.g. BTC/USDT).
    """
    # Simple heuristic: Split base/quote.
    # Most crypto pairs are like BTCUSDT -> BTC/USDT
    # Or PERP like BTCUSDT.P -> BTC/USDT:USDT (depending on exchange)

    # For now, let's try to rely on the market loading to find the symbol
    # But we need a guess.

    # Remove .P for perps common in TV
    clean_sym = tv_symbol.replace(".P", "")

    if clean_sym.endswith("USDT"):
        base = clean_sym[:-4]
        return f"{base}/USDT"
    elif clean_sym.endswith("USD"):
        base = clean_sym[:-3]
        return f"{base}/USD"

    return clean_sym


def fetch_metadata(candidates_path: str):
    logger.info(f"Loading candidates from {candidates_path}")
    try:
        with open(candidates_path, "r") as f:
            candidates = json.load(f)
    except FileNotFoundError:
        logger.error(f"Candidates file not found: {candidates_path}")
        sys.exit(1)

    catalog = ExecutionMetadataCatalog()

    # Group candidates by venue to minimize CCXT init overhead
    venue_map: Dict[str, List[str]] = {}
    for cand in candidates:
        full_sym = cand.get("symbol", "")
        if ":" in full_sym:
            venue, sym = full_sym.split(":")
        else:
            venue, sym = "UNKNOWN", full_sym

        if venue not in venue_map:
            venue_map[venue] = []
        venue_map[venue].append(sym)

    updates = []

    for venue, symbols in venue_map.items():
        logger.info(f"Processing venue: {venue} ({len(symbols)} symbols)")

        exchange = resolve_ccxt_exchange(venue)
        if not exchange:
            logger.warning(f"No CCXT adapter for venue '{venue}'. Using default/fallback metadata for {len(symbols)} symbols.")
            # Generate fallback metadata for TradFi/Unsupported venues
            for sym in symbols:
                updates.append(
                    {
                        "symbol": f"{venue}:{sym}",
                        "venue": venue,
                        "lot_size": 1.0,  # Default: 1 unit
                        "min_notional": 0.0,  # Default: No limit
                        "step_size": 1.0,  # Default: Integer units
                        "tick_size": 0.01,  # Default: 2 decimals
                        "maker_fee": 0.0,
                        "taker_fee": 0.0,
                        "contract_size": 1.0,
                    }
                )
            continue

        try:
            logger.info(f"Fetching markets for {exchange.id}...")
            markets = exchange.load_markets()

            for sym in symbols:
                # Try to find match in markets
                # TV: BTCUSDT -> CCXT: BTC/USDT
                # TV: BTCUSDT.P -> CCXT: BTC/USDT:USDT (Swap)

                found_market = None

                # Heuristic 1: Exact match (rare due to separators)
                if sym in markets:
                    found_market = markets[sym]

                # Heuristic 2: BTC/USDT form
                if not found_market:
                    guess = normalize_symbol_for_ccxt(sym, venue)
                    if guess in markets:
                        found_market = markets[guess]

                # Heuristic 3: Linear scan (slow but robust)
                if not found_market:
                    clean_target = sym.replace(".P", "").replace("/", "").replace("-", "")
                    for m_id, market in markets.items():
                        m_clean = m_id.replace("/", "").replace(":", "").replace("-", "")
                        # Try to match the ID or the symbol
                        if market["id"] == sym or m_clean == clean_target:
                            found_market = market
                            break

                if found_market:
                    logger.info(f"✅ Found market for {venue}:{sym} -> {found_market['symbol']}")

                    # Extract limits
                    limits = found_market.get("limits", {})
                    amount_limits = limits.get("amount", {})
                    price_limits = limits.get("price", {})
                    cost_limits = limits.get("cost", {})

                    # Precision
                    precision = found_market.get("precision", {})
                    amount_precision = precision.get("amount", 0.0)
                    price_precision = precision.get("price", 0.0)

                    # If precision is int (decimal places), convert to float step
                    if isinstance(amount_precision, int):
                        step_size = 1.0 / (10**amount_precision)
                    else:
                        step_size = float(amount_precision) if amount_precision else 0.00000001

                    if isinstance(price_precision, int):
                        tick_size = 1.0 / (10**price_precision)
                    else:
                        tick_size = float(price_precision) if price_precision else 0.01

                    updates.append(
                        {
                            "symbol": f"{venue}:{sym}",
                            "venue": venue,
                            "lot_size": float(amount_limits.get("min") or step_size),
                            "min_notional": float(cost_limits.get("min") or 0.0),
                            "step_size": step_size,
                            "tick_size": tick_size,
                            "maker_fee": float(found_market.get("maker", 0.001)),
                            "taker_fee": float(found_market.get("taker", 0.001)),
                            "contract_size": float(found_market.get("contractSize") or 1.0),
                        }
                    )
                else:
                    logger.warning(f"❌ Market not found for {venue}:{sym}. Using defaults.")
                    updates.append(
                        {
                            "symbol": f"{venue}:{sym}",
                            "venue": venue,
                            "lot_size": 0.0001,
                            "min_notional": 5.0,
                            "step_size": 0.0001,
                            "tick_size": 0.01,
                            "maker_fee": 0.001,
                            "taker_fee": 0.001,
                            "contract_size": 1.0,
                        }
                    )

        except Exception as e:
            logger.error(f"Failed to fetch metadata for {venue}: {e}")
            # Add fallbacks for this venue's symbols?
            # Ideally yes, but let's just log for now.

    if updates:
        catalog.upsert_limits(updates)
        logger.info(f"Updated metadata for {len(updates)} symbols.")
    else:
        logger.info("No updates found.")


if __name__ == "__main__":
    from tradingview_scraper.settings import get_settings

    settings = get_settings()
    default_cand = str(settings.lakehouse_dir / "portfolio_candidates.json")

    parser = argparse.ArgumentParser(description="Fetch execution metadata from exchanges")
    parser.add_argument("--candidates", default=default_cand, help="Path to candidates file")
    args = parser.parse_args()

    fetch_metadata(args.candidates)
