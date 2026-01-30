import unittest
from unittest.mock import AsyncMock, patch

from tradingview_scraper.symbols.stream.streamer_async import AsyncStreamer


class TestAsyncStreamer(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jwt_token = "test_token"

    @patch("tradingview_scraper.symbols.stream.streamer_async.AsyncStreamHandler")
    async def test_stream_initialization(self, MockHandler):
        mock_handler = MockHandler.return_value
        mock_handler.connect = AsyncMock()
        mock_handler.quote_session = "qs_test"
        mock_handler.chart_session = "cs_test"

        streamer = AsyncStreamer(websocket_jwt_token=self.jwt_token)

        # Test basic initialization
        self.assertEqual(streamer.websocket_jwt_token, self.jwt_token)

    @patch("tradingview_scraper.symbols.stream.streamer_async.AsyncStreamHandler")
    async def test_get_data_generator_raw(self, MockHandler):
        mock_handler = MockHandler.return_value
        mock_handler.get_next_message = AsyncMock(side_effect=[{"m": "timescale_update", "p": []}, {"m": "du", "p": []}])

        streamer = AsyncStreamer()
        streamer.stream_obj = mock_handler

        # Use formatted=False to get raw packets
        gen = streamer.get_data(formatted=False)

        msg1 = await gen.__anext__()
        self.assertEqual(msg1["m"], "timescale_update")

        msg2 = await gen.__anext__()
        self.assertEqual(msg2["m"], "du")

    @patch("tradingview_scraper.symbols.stream.streamer_async.AsyncStreamHandler")
    async def test_stream_integration(self, MockHandler):
        mock_handler = MockHandler.return_value
        mock_handler.connect = AsyncMock()
        mock_handler.start_listening = AsyncMock()
        mock_handler.send_message = AsyncMock()
        mock_handler.quote_session = "qs_test"
        mock_handler.chart_session = "cs_test"

        streamer = AsyncStreamer()
        streamer.stream_obj = mock_handler

        # Test stream (non-export mode returns generator)
        await streamer.stream(exchange="BINANCE", symbol="BTCUSDT")

        # Verify connect and start_listening called
        mock_handler.connect.assert_called_once()
        mock_handler.start_listening.assert_called_once()

        # Verify messages sent (at least 4: add_symbol, resolve, create_series, fast_symbols)
        self.assertGreaterEqual(mock_handler.send_message.call_count, 4)

    @patch("tradingview_scraper.symbols.stream.streamer_async.fetch_indicator_metadata")
    @patch("tradingview_scraper.symbols.stream.streamer_async.AsyncStreamHandler")
    async def test_add_indicators(self, MockHandler, mock_fetch):
        mock_handler = MockHandler.return_value
        mock_handler.send_message = AsyncMock()
        mock_fetch.return_value = {"p": [None, "st9"]}

        streamer = AsyncStreamer()
        streamer.stream_obj = mock_handler

        await streamer._add_indicators([("STD;RSI", "37.0")])

        self.assertIn("st9", streamer.study_id_to_name_map)
        self.assertEqual(mock_handler.send_message.call_count, 2)  # create_study + hibernate

    @patch("tradingview_scraper.symbols.stream.streamer_async.AsyncStreamHandler")
    async def test_close(self, MockHandler):
        mock_handler = MockHandler.return_value
        mock_handler.close = AsyncMock()

        streamer = AsyncStreamer()
        streamer.stream_obj = mock_handler

        await streamer.close()
        mock_handler.close.assert_called_once()

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
