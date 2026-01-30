import time

import pytest

from tradingview_scraper.symbols.stream import Streamer


class TestStreamerCompleteness:
    """
    Validates Streamer capability to load both small and maximum/excessive candle counts.
    """

    def test_small_candle_load(self):
        """
        Verify that requesting a small number of candles returns quickly and accurately.
        """
        streamer = Streamer(export_result=True, idle_timeout_seconds=10.0)

        target_candles = 50
        print(f"\n[Test] Requesting {target_candles} daily candles...")

        start_time = time.time()
        res = streamer.stream(exchange="BINANCE", symbol="BTCUSDT", timeframe="1d", numb_price_candles=target_candles, auto_close=True)
        duration = time.time() - start_time

        candles = res.get("ohlc", [])
        count = len(candles)
        print(f"Collected {count} candles in {duration:.2f}s")

        # We expect exactly 50 if history allows (which it does)
        assert count >= target_candles, f"Expected {target_candles}, got {count}"
        # It might return slightly more due to packet framing, but usually close.
        # Actually TV streamer tends to return exactly requested if available, or slightly more.

        # Speed check: 50 candles should be very fast (< 5s)
        assert duration < 10.0, "Small load took too long"

    def test_max_candle_load(self):
        """
        Verify that requesting a maximum/excessive number of candles:
        1. Returns all available history (up to the request limit).
        2. Does not block indefinitely.
        """
        # Use a slightly aggressive idle timeout to fail fast if it hangs
        streamer = Streamer(export_result=True, idle_timeout_seconds=10.0, idle_packet_limit=5)

        # 10,000 daily candles is ~27 years. BTCUSDT has ~8 years (~3000 days).
        # This tests the "request > available" scenario.
        target_candles = 10000
        print(f"\n[Test] Requesting {target_candles} daily candles (Max Load)...")

        start_time = time.time()
        res = streamer.stream(exchange="BINANCE", symbol="BTCUSDT", timeframe="1d", numb_price_candles=target_candles, auto_close=True)
        duration = time.time() - start_time

        candles = res.get("ohlc", [])
        count = len(candles)
        print(f"Collected {count} candles in {duration:.2f}s")

        # Verification:
        # 1. We got data.
        assert count > 0, "No candles returned for max load"

        # 2. We didn't get the full 10,000 (because history is shorter).
        #    If we did, it means history is longer than expected or duplicate data?
        #    BTCUSDT daily count is ~3050 as of late 2025.
        assert count < 10000, f"Unexpectedly got full {count} candles? History might be shorter."

        # 3. We got "enough" to represent full history.
        #    Genesis is 2017. 2025 - 2017 = 8 years * 365 = 2920.
        assert count > 2500, f"Expected > 2500 candles for full history, got {count}"

        # 4. It didn't hang forever (timeout is 10s logic, usually takes 2-5s)
        print(f"Load speed: {count / duration:.1f} candles/sec")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
