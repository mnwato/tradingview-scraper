import time
from datetime import datetime

import pytest

from tradingview_scraper.symbols.stream import Streamer


class TestStreamerParity:
    """
    Validates Streamer behavior for loading candles without blocking.
    """

    def test_load_capped_candles_no_block(self):
        """
        Verify that requesting a capped number of candles (e.g. 3050 for BTCUSDT)
        returns successfully without blocking/timeout.
        """
        # Initialize streamer with export_result=True to get dict return
        streamer = Streamer(export_result=True, idle_timeout_seconds=15.0)

        start_time = time.time()

        # Request 3050 daily candles (known available history for BTCUSDT)
        res = streamer.stream(exchange="BINANCE", symbol="BTCUSDT", timeframe="1d", numb_price_candles=3050, auto_close=True)

        end_time = time.time()
        duration = end_time - start_time

        candles = res.get("ohlc", [])
        print(f"Collected {len(candles)} candles in {duration:.2f} seconds")

        assert len(candles) > 0, "No candles returned"
        assert duration < 60.0, f"Request took too long: {duration:.2f}s"

        # Verify data range
        if candles:
            candles.sort(key=lambda x: x["timestamp"])
            first_date = datetime.fromtimestamp(candles[0]["timestamp"])
            last_date = datetime.fromtimestamp(candles[-1]["timestamp"])
            print(f"Range: {first_date} to {last_date}")

            # Genesis for BTCUSDT is ~Aug 2017
            assert first_date.year <= 2017, f"Expected data from 2017 or earlier, got {first_date}"

    def test_graceful_timeout_handling(self):
        """
        Verify that Streamer exits gracefully if data stops arriving or timeout occurs,
        returning whatever data was collected.
        """
        # Use short timeout
        streamer = Streamer(export_result=True, idle_timeout_seconds=5.0, idle_packet_limit=3)

        start_time = time.time()

        # Request an excessive number of candles to force a "end of history" or timeout scenario
        # But for this test, we want to see it return PARTIAL data if it times out waiting for more
        # Note: If it downloads all available history quickly, it might just finish naturally.
        # So we test with a symbol and count that definitely exceeds history.

        res = streamer.stream(
            exchange="BINANCE",
            symbol="BTCUSDT",
            timeframe="1d",
            numb_price_candles=10000,  # Way more than available (~3000)
            auto_close=True,
        )

        end_time = time.time()
        duration = end_time - start_time

        candles = res.get("ohlc", [])
        print(f"Timeout Test: Collected {len(candles)} candles in {duration:.2f} seconds")

        # Should have collected SOME data (the max available) and exited
        assert len(candles) > 0, "Should have collected available history"
        assert len(candles) < 10000, "Should not have invented data"
        # It should exit reasonably fast (idle timeout is 5s)
        # Actual transfer of 3000 candles takes a few seconds.
        assert duration < 30.0, "Should handle 'end of data' timeout gracefully"


if __name__ == "__main__":
    pytest.main([__file__])
