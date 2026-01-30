#!/usr/bin/env python3
"""
Audit symbol age using Perf.Y as a proxy for >1 year history.
Updates MetadataCatalog with 'min_age_1y' field.
"""

import logging

from tradingview_scraper.symbols.screener import Screener
from tradingview_scraper.symbols.stream.metadata import MetadataCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audit_age")


def audit_ages():
    catalog = MetadataCatalog()
    df = catalog._df

    # Get active symbols
    active_mask = df["valid_until"].isna()
    active_symbols = df[active_mask]["symbol"].tolist()

    logger.info(f"Auditing age for {len(active_symbols)} active symbols...")

    # Initialize new column if not exists
    if "min_age_1y" not in df.columns:
        df["min_age_1y"] = None

    # Group by exchange/market because Screener requires 'market' param
    # We need to map our exchanges to Screener markets.
    # Default is 'crypto' for BINANCE, BYBIT, OKX, BITGET.
    # What about NYSE? 'america'.
    # We need a mapping.

    exchange_to_market = {
        "BINANCE": "crypto",
        "BYBIT": "crypto",
        "OKX": "crypto",
        "BITGET": "crypto",
        "THINKMARKETS": "forex",  # Or cfd? Let's try forex first.
        "FX_IDC": "forex",
        "OANDA": "cfd",  # or forex? OANDA is often CFD.
        "NASDAQ": "america",
        "NYSE": "america",
        "AMEX": "america",
        "CME": "futures",  # or america? 'futures' market usually.
        "CBOT": "futures",
        "COMEX": "futures",
        "NYMEX": "futures",
        "CME_MINI": "futures",
        "ICE": "futures",  # or america?
        "LSE": "uk",
        "EUREX": "germany",  # EUREX is derivatives, maybe 'futures'?
        "XETRA": "germany",
        "TSX": "canada",  # or canada?
        "SSE": "china",  # or china? 'china' is not in standard list usually, 'global'?
        "OTC": "america",  # OTC usually covered under america or specific OTC market
    }

    # Helper to get market
    def get_market(exchange):
        return exchange_to_market.get(exchange, "crypto")  # Default to crypto for safety? No, risky.

    # Process by market to batch efficiently
    symbols_by_market = {}
    for sym in active_symbols:
        exchange = sym.split(":")[0]
        market = get_market(exchange)
        if market not in symbols_by_market:
            symbols_by_market[market] = []
        symbols_by_market[market].append(sym)

    screener = Screener()
    results = {}

    for market, syms in symbols_by_market.items():
        logger.info(f"Processing {len(syms)} symbols for market '{market}'...")

        # Batch size 50
        batch_size = 50
        for i in range(0, len(syms), batch_size):
            batch = syms[i : i + batch_size]

            # Construct filters: symbol in [list]
            # Screener 'symbol' filter usually takes one? Or 'name' in list?
            # 'name' operation 'in_range' doesn't make sense.
            # Usually we filter by exchange and get all, then match locally.
            # But getting ALL for 'america' is huge.
            # Filter 'name' 'in' list? 'equal' only takes one.
            # We can use 'name' 'in_range' for alphabetical? No.

            # Strategy: Query by exchange(s) and maybe volume > 0 to limit?
            # Actually, we can pass a large list of tickers to 'symbol' param? No.
            # The 'filters' support 'name' 'in' [list]?
            # Check Screener code. OPERATIONS list doesn't show 'in'.
            # 'equal', 'egreater', ... 'has'.

            # Alternative: One request per symbol? Too slow (400 requests).
            # Alternative: Request ALL for the exchange(s) involved, then map.

            # Let's get unique exchanges in this market batch
            exchanges = set(s.split(":")[0] for s in batch)

            for ex in exchanges:
                # Get all symbols for this exchange
                # We can't easily filter specific symbols in one go if API doesn't support 'in'.
                # But we can just fetch ALL from that exchange?
                # For NYSE it's big.
                # But we only need Perf.Y.
                pass

    # Revised Strategy:
    # 1. Group by Exchange.
    # 2. For each Exchange, fetch all symbols (with limit?).
    #    If exchange is huge (NYSE), fetching all is heavy.
    #    Is there a way to filter specific symbols?
    #    TradingView scanner allows "name" "equal" "AAPL".
    #    Does it allow multiple filters with "OR"? Logic "OR"?
    #    Screener config allows 'logic': 'OR'. But  ?
    #    It puts filters in a list. Usually implied AND.

    # Let's try fetching symbol by symbol for non-crypto (fewer symbols).
    # For Crypto, fetching all BINANCE is fine (2000 symbols).

    updates = {}

    # Process Exchange-by-Exchange
    unique_exchanges = df[active_mask]["exchange"].unique()

    for ex in unique_exchanges:
        market = get_market(ex)
        ex_symbols = df[active_mask & (df["exchange"] == ex)]["symbol"].tolist()

        logger.info(f"Processing {ex} ({len(ex_symbols)} symbols) in market {market}...")

        if len(ex_symbols) > 50:
            # Fetch ALL for this exchange
            # Filter: exchange == ex
            filters = [{"left": "exchange", "operation": "equal", "right": ex}]
            # We need to map 's' (symbol) to our format.
            # Crypto returns 'BINANCE:BTCUSDT'.
            # America returns 'NASDAQ:AAPL'? Or just 'AAPL'?
            # Usually 'AAPL' and exchange is separate.

            try:
                # Use higher limit to catch all
                limit = 5000
                res = screener.screen(market=market, filters=filters, columns=["name", "Perf.Y"], limit=limit)
                if res["status"] == "success":
                    for item in res["data"]:
                        # Symbol from screener might vary.
                        # item['symbol'] is usually 'EXCHANGE:SYMBOL' or just 'SYMBOL'.
                        # Let's match carefully.
                        scr_sym = item["symbol"]
                        # If screener returns 'BTCUSDT', we need 'BINANCE:BTCUSDT'.
                        if ":" not in scr_sym:
                            scr_sym = f"{ex}:{scr_sym}"

                        if scr_sym in ex_symbols:
                            perf_y = item.get("Perf.Y")
                            updates[scr_sym] = perf_y is not None
                else:
                    logger.error(f"Failed to screen {ex}: {res.get('error')}")
            except Exception as e:
                logger.error(f"Error screening {ex}: {e}")

        else:
            # Few symbols, query one by one to be safe and avoid fetching thousands
            for sym in ex_symbols:
                ticker = sym.split(":")[1]
                filters = [{"left": "exchange", "operation": "equal", "right": ex}, {"left": "name", "operation": "equal", "right": ticker}]
                try:
                    res = screener.screen(market=market, filters=filters, columns=["name", "Perf.Y"], limit=1)
                    if res["status"] == "success" and res["data"]:
                        item = res["data"][0]
                        perf_y = item.get("Perf.Y")
                        updates[sym] = perf_y is not None
                    else:
                        logger.warning(f"No data for {sym}")
                        updates[sym] = False  # Assume False if not found? Or None?
                except Exception as e:
                    logger.error(f"Error checking {sym}: {e}")

    # Apply updates
    logger.info(f"Updating {len(updates)} symbols...")
    for sym, is_old in updates.items():
        # Find index for this symbol (active)
        idx_mask = (df["symbol"] == sym) & (df["valid_until"].isna())
        if idx_mask.any():
            df.loc[idx_mask, "min_age_1y"] = is_old

    catalog.save()
    logger.info("Audit complete.")


if __name__ == "__main__":
    audit_ages()
