from unittest.mock import MagicMock, patch

from websocket import WebSocketConnectionClosedException

from tradingview_scraper.symbols.stream import Streamer


def test_streamer_reconnects_on_connection_closed():
    """
    Test that Streamer attempts to reconnect when WebSocketConnectionClosedException occurs.
    """
    with patch("tradingview_scraper.symbols.stream.streamer.StreamHandler") as MockStreamHandler:
        mock_handler = MockStreamHandler.return_value
        mock_ws = mock_handler.ws

        # Simulate data, then connection loss, then more data
        mock_ws.recv.side_effect = [
            '~m~20~m~{"m":"timescale_update","p":[{},{"sds_1":{"s":[{"i":0,"v":[1600000000,1,2,3,4,10]}]}}]}',
            WebSocketConnectionClosedException("Connection lost"),
            '~m~20~m~{"m":"timescale_update","p":[{},{"sds_1":{"s":[{"i":1,"v":[1600000060,2,3,4,5,20]}]}}]}',
        ]

        streamer = Streamer(export_result=False)
        # Mock sleep to avoid actual delay in tests
        with patch("tradingview_scraper.symbols.stream.streamer.sleep"):
            # We use get_data() directly to test the loop
            data_gen = streamer.get_data()

            # First packet
            pkt1 = next(data_gen)
            assert pkt1["m"] == "timescale_update"

            # The next() call should encounter the exception,
            # trigger reconnect (re-init StreamHandler), and then yield the next packet
            pkt2 = next(data_gen)
            assert pkt2["m"] == "timescale_update"
            assert pkt2["p"][1]["sds_1"]["s"][0]["i"] == 1

            # Verify MockStreamHandler was called twice (initial + reconnect)
            assert MockStreamHandler.call_count == 2


def test_streamer_restores_state_on_reconnect():
    """
    Test that Streamer re-subscribes to symbols and indicators after reconnection.
    """
    with patch("tradingview_scraper.symbols.stream.streamer.StreamHandler") as MockStreamHandler:
        mock_handler = MockStreamHandler.return_value
        mock_ws = mock_handler.ws

        # Simulate connection loss on first recv, then success
        mock_ws.recv.side_effect = [WebSocketConnectionClosedException("Connection lost"), '~m~20~m~{"m":"timescale_update","p":[{},{"sds_1":{"s":[{"i":0,"v":[1600000000,1,2,3,4,10]}]}}]}']

        streamer = Streamer(export_result=False)

        # Set up initial subscription
        indicators = [("STD;RSI", "37.0")]

        # Mock methods to track calls but keep original functionality to set state
        original_add_sym = streamer._add_symbol_to_sessions
        streamer._add_symbol_to_sessions = MagicMock(side_effect=original_add_sym)

        original_add_ind = streamer._add_indicators
        streamer._add_indicators = MagicMock(side_effect=original_add_ind)

        with patch("tradingview_scraper.symbols.stream.streamer.sleep"):
            # Initial call to stream would set the state
            data_gen = streamer.stream(exchange="BINANCE", symbol="BTCUSDT", timeframe="1h", indicators=indicators)

            # Trigger iteration to run get_data() and encounter exception
            next(data_gen)

            # Check if _add_symbol_to_sessions was called again during reconnection
            # It should be called twice: once in stream(), once in get_data() retry loop
            assert streamer._add_symbol_to_sessions.call_count == 2
            streamer._add_symbol_to_sessions.assert_called_with(mock_handler.quote_session, mock_handler.chart_session, "BINANCE:BTCUSDT", "1h", 10)

            # Check if _add_indicators was called again
            assert streamer._add_indicators.call_count == 2
            streamer._add_indicators.assert_called_with(indicators)
