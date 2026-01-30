import logging
from datetime import datetime

from tradingview_scraper.symbols.stream import Streamer
from tradingview_scraper.symbols.stream.metadata import MetadataCatalog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("populate_genesis")


def populate():
    catalog = MetadataCatalog()
    df = catalog._df

    if "genesis_ts" not in df.columns:
        logger.info("Adding genesis_ts column")
        df["genesis_ts"] = None

    symbol = "BINANCE:BTCUSDT"
    exchange, ticker = symbol.split(":")

    # Use aggressive idle timeout to return quickly after fetching all available history
    streamer = Streamer(export_result=True, idle_timeout_seconds=5.0, idle_packet_limit=5)

    logger.info(f"Fetching history for {symbol}...")
    # Request 10000 daily candles (enough for ~27 years, covers all crypto history)
    try:
        res = streamer.stream(exchange, ticker, timeframe="1d", numb_price_candles=10000, auto_close=True)
        candles = res.get("ohlc", [])
    except Exception as e:
        logger.error(f"Stream failed: {e}")
        candles = []

    if candles:
        first_ts = candles[0]["timestamp"]
        genesis_dt = datetime.fromtimestamp(first_ts)
        logger.info(f"Genesis for {symbol}: {genesis_dt} (Timestamp: {first_ts})")
        logger.info(f"Retrieved {len(candles)} candles")

        # Update catalog
        mask = (df["symbol"] == symbol) & (df["valid_until"].isna())
        if mask.any():
            df.loc[mask, "genesis_ts"] = first_ts
            catalog._df = df
            catalog.save()
            logger.info("Catalog updated.")
        else:
            logger.error("Symbol not found in active catalog")
    else:
        logger.warning("No candles found")


if __name__ == "__main__":
    populate()
