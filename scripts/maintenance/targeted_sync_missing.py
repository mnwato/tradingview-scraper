import logging
import os

from tradingview_scraper.symbols.stream.persistent_loader import PersistentDataLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("targeted_sync")

MISSING_SYMBOLS = [
    "NYMEX:HPJ2026",
    "COMEX:GCG2026",
    "COMEX:GC1!",
    "COMEX:1OZ1!",
    "COMEX:SIH2026",
    "COMEX:SI1!",
    "CBOT:ZC1!",
    "COMEX:HGH2026",
    "COMEX:HG1!",
    "NYMEX:PL1!",
    "PEPPERSTONE:XAUUSD",
    "OANDA:XCUUSD",
    "OANDA:AU200AUD",
    "OANDA:CORNUSD",
    "OANDA:XAUUSD",
    "OKX:IPUSDT",
    "OKX:ICPUSDT",
    "OKX:BCHUSDT",
    "OKX:PAXGUSDT",
    "THINKMARKETS:CADJPY",
    "OKX:TONUSDT.P",
    "BITGET:BCHUSDT",
    "BITGET:ICPUSDT",
]


def run_targeted_sync():
    jwt_token = os.getenv("TRADINGVIEW_JWT_TOKEN", "unauthorized_user_token")
    loader = PersistentDataLoader(websocket_jwt_token=jwt_token)

    for symbol in MISSING_SYMBOLS:
        logger.info(f"Targeted sync for {symbol}...")
        try:
            # Increased depth to 300 and total_timeout to 300s
            added = loader.sync(symbol, interval="1d", depth=300, total_timeout=300)
            logger.info(f"Successfully synced {symbol}, added {added} candles.")

            # Efficient repair: newest to oldest with fail-fast
            repaired = loader.repair(symbol, interval="1d", max_depth=500, max_fills=10, max_time=300, total_timeout=300)
            logger.info(f"Repaired {symbol}, added {repaired} candles via gap-fill.")
        except Exception as e:
            logger.error(f"Failed to sync {symbol}: {e}")


if __name__ == "__main__":
    run_targeted_sync()
