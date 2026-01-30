import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tradingview_scraper.symbols.stream.streamer_async import AsyncStreamer


class TestAsyncStreamerReconnect(unittest.IsolatedAsyncioTestCase):
    @patch("tradingview_scraper.symbols.stream.streamer_async.AsyncStreamHandler")
    async def test_streamer_reconnects_async(self, MockHandler):
        # Configure the MockHandler to always return a mock with async methods
        def create_mock_handler(*args, **kwargs):
            m = MagicMock()
            m.connect = AsyncMock()
            m.start_listening = AsyncMock()
            m.send_message = AsyncMock()
            m.close = AsyncMock()
            # Shared side effect for all instances
            m.get_next_message = mock_get_next
            return m

        mock_get_next = AsyncMock(
            side_effect=[
                {"m": "timescale_update", "p": []},
                None,  # Sentinel for connection lost
                {"m": "timescale_update", "p": []},
            ]
        )

        MockHandler.side_effect = create_mock_handler

        streamer = AsyncStreamer()
        # Mock sleep to avoid delay
        with patch("asyncio.sleep", new_callable=AsyncMock):
            gen = await streamer.stream(exchange="BINANCE", symbol="BTCUSDT", formatted=False)

            # First packet
            pkt1 = await gen.__anext__()
            self.assertEqual(pkt1["m"], "timescale_update")

            # Second packet - should trigger reconnect internally and then return the next packet
            pkt2 = await gen.__anext__()
            self.assertEqual(pkt2["m"], "timescale_update")

            # Verify MockHandler was initialized at least twice (init + reconnect)
            self.assertGreaterEqual(MockHandler.call_count, 2)


if __name__ == "__main__":
    unittest.main()
