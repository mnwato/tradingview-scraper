import argparse
import asyncio
import contextlib
import logging
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional, cast

from dotenv import load_dotenv

from tradingview_scraper.symbols.stream.streamer_async import AsyncStreamer

DEFAULT_PACKETS = 5
DEFAULT_TIMEOUT = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demonstrate AsyncStreamer streaming and one-shot collection.")
    parser.add_argument("--exchange", default="BINANCE", help="Exchange name, e.g. BINANCE.")
    parser.add_argument("--stream-symbol", default="BTCUSDT", help="Symbol to stream continuously.")
    parser.add_argument("--collect-symbol", default="ETHUSDT", help="Symbol to collect in batch mode.")
    parser.add_argument("--timeframe", default="1m", help="Timeframe to request (default: 1m).")
    parser.add_argument("--packets", type=int, default=DEFAULT_PACKETS, help="How many packets to print in streaming mode.")
    parser.add_argument("--candles", type=int, default=5, help="How many candles to retrieve in collection mode.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Seconds to wait per receive attempt.")
    parser.add_argument("--jwt-token", dest="jwt_token", default=None, help="JWT token; falls back to TRADINGVIEW_JWT_TOKEN env var.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def resolve_token(cli_token: Optional[str]) -> str:
    token = cli_token or os.getenv("TRADINGVIEW_JWT_TOKEN", "unauthorized_user_token")
    if token == "unauthorized_user_token":
        logging.warning("Using default unauthorized token; set TRADINGVIEW_JWT_TOKEN for full data access.")
    return token


async def run_stream_mode(streamer: AsyncStreamer, *, exchange: str, symbol: str, timeframe: str, packet_limit: int, timeout: int) -> None:
    logging.info("=== Mode 1: Continuous streaming ===")
    streamer.export_result = False

    result = await streamer.stream(exchange=exchange, symbol=symbol, timeframe=timeframe, numb_price_candles=max(packet_limit, 1))

    if not hasattr(result, "__anext__"):
        logging.error("Stream returned %s instead of an async generator.", type(result).__name__)
        return

    data_gen = cast(AsyncGenerator[Dict[str, Any], None], result)
    packets_seen = 0

    try:
        while packets_seen < packet_limit:
            pkt = await asyncio.wait_for(data_gen.__anext__(), timeout=timeout)
            packets_seen += 1
            ohlc = pkt.get("ohlc")
            if ohlc:
                candle = ohlc[-1]
                ts = datetime.fromtimestamp(candle["timestamp"])
                logging.info("[Mode1 %d/%d] %s close=%s", packets_seen, packet_limit, ts, candle.get("close"))
    except asyncio.TimeoutError:
        logging.warning("Mode 1 timed out after %s seconds without data.", timeout)
    except StopAsyncIteration:
        logging.info("Stream closed by server.")
    finally:
        with contextlib.suppress(Exception):
            await data_gen.aclose()


async def run_collect_mode(streamer: AsyncStreamer, *, exchange: str, symbol: str, timeframe: str, candles: int, timeout: int) -> None:
    logging.info("=== Mode 2: One-shot collection ===")
    streamer.export_result = True

    try:
        result = await asyncio.wait_for(
            streamer.stream(exchange=exchange, symbol=symbol, timeframe=timeframe, numb_price_candles=candles),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logging.warning("Mode 2 timed out after %s seconds without data.", timeout)
        return
    finally:
        streamer.export_result = False

    if not isinstance(result, dict):
        logging.warning("Unexpected payload from stream(): %s", type(result).__name__)
        return

    result_map = cast(Dict[str, Any], result)
    ohlc_raw = cast(list[dict[str, Any]], result_map.get("ohlc", []))
    ohlc_data: list[dict[str, Any]] = [x for x in ohlc_raw if isinstance(x, dict)]
    logging.info("Collected %d candle(s) for %s:%s", len(ohlc_data), exchange, symbol)

    if ohlc_data:
        latest = ohlc_data[-1]
        ts = datetime.fromtimestamp(latest["timestamp"])
        logging.info("Latest close %s at %s", latest.get("close"), ts)


async def main() -> None:
    load_dotenv()
    setup_logging()
    args = parse_args()

    jwt_token = resolve_token(args.jwt_token)

    streamer = AsyncStreamer(websocket_jwt_token=jwt_token)

    try:
        await run_stream_mode(streamer, exchange=args.exchange, symbol=args.stream_symbol, timeframe=args.timeframe, packet_limit=args.packets, timeout=args.timeout)
        await run_collect_mode(streamer, exchange=args.exchange, symbol=args.collect_symbol, timeframe=args.timeframe, candles=args.candles, timeout=args.timeout)
    except KeyboardInterrupt:
        logging.info("Interrupted by user, closing connections...")
    except Exception as exc:
        logging.exception("Error during demo: %s", exc)
    finally:
        logging.info("Closing streamer...")
        await streamer.close()
        logging.info("Streamer closed.")


if __name__ == "__main__":
    asyncio.run(main())
