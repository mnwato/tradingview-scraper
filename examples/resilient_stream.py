import logging
import os

from dotenv import load_dotenv

from tradingview_scraper.symbols.stream import Streamer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_resilient_stream():
    """
    Demonstrates a long-running stream that survives connection drops.
    """
    jwt_token = os.getenv("TRADINGVIEW_JWT_TOKEN", "unauthorized_user_token")

    # Initialize Streamer with custom retry settings
    streamer = Streamer(export_result=False, websocket_jwt_token=jwt_token, max_retries=10, initial_delay=2.0, max_delay=30.0, backoff_factor=1.5)

    logging.info("Starting resilient stream for BINANCE:BTCUSDT...")

    try:
        # Start streaming (returns a generator)
        data_gen = streamer.stream(exchange="BINANCE", symbol="BTCUSDT", timeframe="1m", indicators=[("STD;RSI", "31.0")])

        # Consume the stream
        for i, packet in enumerate(data_gen):
            if packet.get("m") == "timescale_update":
                logging.info("Received OHLC update #%d", i)
            elif packet.get("m") == "du":
                logging.info("Received indicator update #%d", i)

            # Limit the example to 100 packets
            if i >= 100:
                logging.info("Reached packet limit for example.")
                break

    except Exception as e:
        logging.error("Stream failed: %s", e)


if __name__ == "__main__":
    run_resilient_stream()
