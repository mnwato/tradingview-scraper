import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import aiohttp

from tradingview_scraper.symbols.stream.stream_handler_async import AsyncStreamHandler


class TestAsyncStreamHandler(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ws_url = "wss://data.tradingview.com/socket.io/websocket"
        self.jwt_token = "test_token"

    @patch("aiohttp.ClientSession.ws_connect", new_callable=AsyncMock)
    async def test_initialize_sessions(self, mock_ws_connect):
        # Setup mock websocket
        mock_ws = AsyncMock()
        mock_ws_connect.return_value = mock_ws

        # Initialize handler
        handler = AsyncStreamHandler(websocket_url=self.ws_url, jwt_token=self.jwt_token)

        try:
            # We need to manually call initialize because __init__ might not be async or might not call it
            # Actually, in async handler, we probably want an async factory or a separate init method
            await handler.connect()

            # Verify messages sent during initialization
            # Expected: set_auth_token, set_locale, chart_create_session, quote_create_session, quote_set_fields, quote_hibernate_all
            self.assertGreater(mock_ws.send_str.call_count, 5)

            # Check if sessions were generated
            self.assertTrue(handler.quote_session.startswith("qs_"))
            self.assertTrue(handler.chart_session.startswith("cs_"))
        finally:
            await handler.close()

    async def test_generate_session(self):
        handler = AsyncStreamHandler(websocket_url=self.ws_url)
        session = handler.generate_session("test_")
        self.assertTrue(session.startswith("test_"))
        self.assertEqual(len(session), 5 + 12)

    @patch("aiohttp.ClientSession.ws_connect", new_callable=AsyncMock)
    async def test_heartbeat_handling(self, mock_ws_connect):
        # Setup mock websocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws_connect.return_value = mock_ws

        # Simulate receiving a heartbeat
        heartbeat_msg = "~m~10~m~~h~1"

        # We need to use real types for type checks in the loop
        mock_ws.receive.side_effect = [aiohttp.WSMessage(type=aiohttp.WSMsgType.TEXT, data=heartbeat_msg, extra=None), aiohttp.WSMessage(type=aiohttp.WSMsgType.CLOSED, data=None, extra=None)]

        handler = AsyncStreamHandler(websocket_url=self.ws_url)
        await handler.connect()

        # Start listening
        await handler.start_listening()

        # Give it some time to process
        await asyncio.sleep(0.1)

        # Verify heartbeat echoed
        mock_ws.send_str.assert_any_call(heartbeat_msg)
        await handler.close()


if __name__ == "__main__":
    unittest.main()
