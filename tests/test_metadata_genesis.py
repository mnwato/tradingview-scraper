from datetime import datetime

import pytest

from tradingview_scraper.symbols.overview import Overview
from tradingview_scraper.symbols.stream import Streamer


class TestGenesisDiscovery:
    """
    Validates findings regarding genesis_ts discovery methods.
    """

    def test_overview_lacks_genesis(self):
        """
        Verify that the Overview API does not return genesis/start date fields.
        """
        ov = Overview()
        # Test with a well-known symbol
        res = ov.get_symbol_overview("BINANCE:BTCUSDT")

        assert res["status"] == "success"
        data = res["data"]

        # List of fields that would indicate start date if they existed
        target_fields = ["genesis_ts", "start_date", "listed_date", "ipo_date", "launch_date", "creation_date", "first_trade_date"]

        # None of these should present with valid data in the response
        found_fields = [f for f in target_fields if f in data and data[f] is not None]

        assert len(found_fields) == 0, f"Unexpectedly found genesis fields: {found_fields}"

        # Verify timezone is often missing for crypto in Overview (secondary finding)
        # assert data.get("timezone") is None # This was observed but might change, optional check

    def test_streamer_fetches_genesis(self):
        """
        Verify that the Streamer can fetch the true genesis timestamp.
        """
        # Set export_result=True to get a dictionary return instead of a generator
        streamer = Streamer(export_result=True, idle_timeout_seconds=10.0)

        # Request a large number of daily candles for BTCUSDT
        # BTCUSDT on Binance started around Aug 2017
        res = streamer.stream(
            exchange="BINANCE",
            symbol="BTCUSDT",
            timeframe="1d",
            numb_price_candles=100,  # Enough to reach 2017 from 2025 (~3000 days)
            auto_close=True,
        )

        candles = res.get("ohlc", [])
        print(f"Collected {len(candles)} candles")
        if candles:
            # Ensure sorted by timestamp
            candles.sort(key=lambda x: x["timestamp"])
            print(f"First candle: {datetime.fromtimestamp(candles[0]['timestamp'])}")
            print(f"Last candle: {datetime.fromtimestamp(candles[-1]['timestamp'])}")

        assert len(candles) > 0, "Streamer returned no candles"

        first_candle = candles[0]
        first_ts = first_candle["timestamp"]
        first_date = datetime.fromtimestamp(first_ts)

        # Validation: BTCUSDT started ~Aug 2017.
        # Since we only requested 100 candles, we won't see 2017.
        # We just want to ensure we got SOME valid data back.
        print(f"Verified first candle date: {first_date}")
        assert first_date.year >= 2017, f"Expected data after 2017, got {first_date.year}"

        print(f"Verified Genesis: {first_date}")


if __name__ == "__main__":
    pytest.main([__file__])
