import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from tradingview_scraper.symbols.screener import Screener
from tradingview_scraper.symbols.screener_async import AsyncScreener


class TestAsyncScreener(unittest.TestCase):
    def setUp(self):
        self.screener = AsyncScreener()

    def test_market_parity(self):
        # Verify AsyncScreener supports all markets that Screener supports
        sync_markets = set(Screener.SUPPORTED_MARKETS.keys())
        async_markets = set(self.screener.SUPPORTED_MARKETS.keys())
        self.assertEqual(sync_markets, async_markets)

    def test_default_columns_parity(self):
        # Verify default columns are consistent
        for market in ["crypto", "forex", "america"]:
            sync_cols = Screener()._get_default_columns(market)
            async_cols = self.screener._get_default_columns(market)
            self.assertEqual(sync_cols, async_cols)

    @patch("aiohttp.ClientSession.post")
    def test_screen_retry_on_429(self, mock_post):
        # Setup mock responses: first two fail with 429, third succeeds
        mock_fail = MagicMock()
        mock_fail.status = 429
        mock_fail.text = AsyncMock(return_value="Rate limit exceeded")

        mock_success = MagicMock()
        mock_success.status = 200
        mock_success.json = AsyncMock(return_value={"data": [{"s": "BINANCE:BTCUSDT", "d": [100]}]})

        mock_post.return_value.__aenter__.side_effect = [mock_fail, mock_fail, mock_success]

        async def run_test():
            async with aiohttp.ClientSession() as session:
                return await self.screener.screen(session, "crypto", [], ["close"])

        result = asyncio.run(run_test())

        self.assertEqual(result["status"], "success")
        self.assertEqual(mock_post.call_count, 3)

    @patch("aiohttp.ClientSession.post")
    def test_screen_retry_on_connection_error(self, mock_post):
        # Setup mock responses: first two fail with ClientError, third succeeds
        mock_success = MagicMock()
        mock_success.status = 200
        mock_success.json = AsyncMock(return_value={"data": [{"s": "BINANCE:BTCUSDT", "d": [100]}]})

        # mock_post is a context manager
        cm_fail = MagicMock()
        cm_fail.__aenter__.side_effect = aiohttp.ClientError("Connection reset")

        cm_success = MagicMock()
        cm_success.__aenter__.return_value = mock_success

        mock_post.side_effect = [cm_fail, cm_fail, cm_success]

        async def run_test():
            async with aiohttp.ClientSession() as session:
                return await self.screener.screen(session, "crypto", [], ["close"])

        result = asyncio.run(run_test())

        self.assertEqual(result["status"], "success")
        self.assertEqual(mock_post.call_count, 3)

    @patch("aiohttp.ClientSession.post")
    @patch("tradingview_scraper.symbols.screener_async.save_json_file")
    def test_screen_export_json(self, mock_save_json, mock_post):
        # Setup mock response
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"data": [{"s": "BINANCE:BTCUSDT", "d": [100]}]})
        mock_post.return_value.__aenter__.return_value = mock_resp

        # Initialize screener with export enabled
        self.screener.export_result = True
        self.screener.export_type = "json"

        async def run_test():
            async with aiohttp.ClientSession() as session:
                return await self.screener.screen(session, "crypto", [], ["close"])

        asyncio.run(run_test())

        mock_save_json.assert_called_once()

    @patch("aiohttp.ClientSession.post")
    def test_screen_many(self, mock_post):
        # Setup mock response
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"data": [{"s": "BINANCE:BTCUSDT", "d": [100]}]})

        # mock_post is a context manager
        mock_post.return_value.__aenter__.return_value = mock_resp

        payloads = [{"market": "crypto", "filters": [], "columns": ["close"]}, {"market": "crypto", "filters": [], "columns": ["close"]}]

        results = asyncio.run(self.screener.screen_many(payloads))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["status"], "success")
        self.assertEqual(results[0]["data"][0]["symbol"], "BINANCE:BTCUSDT")

    @patch("aiohttp.ClientSession.post")
    def test_screen_pagination(self, mock_post):
        # Setup mock response that respects the requested limit in the payload
        def mock_post_side_effect(url, json, headers, timeout):
            requested_limit = json["range"][1] - json["range"][0]
            mock_resp = MagicMock()
            mock_resp.status = 200
            data_page = [{"s": f"SYM_{i}", "d": [100]} for i in range(requested_limit)]
            mock_resp.json = AsyncMock(return_value={"data": data_page})

            # Setup __aenter__ for the context manager
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=mock_resp)
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        mock_post.side_effect = mock_post_side_effect

        async def run_test():
            async with aiohttp.ClientSession() as session:
                # Request 120 items (should trigger 3 requests: 50, 50, 20)
                return await self.screener.screen(session, "crypto", [], ["close"], limit=120)

        result = asyncio.run(run_test())

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 120)
        self.assertEqual(mock_post.call_count, 3)

    @patch("aiohttp.ClientSession.post")
    def test_screen_many_concurrency(self, mock_post):
        # Setup mock response
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"data": []})

        # We need a custom side effect to track simultaneous active requests
        active_requests = 0
        max_seen = 0

        def mock_post_side_effect(*args, **kwargs):
            nonlocal active_requests, max_seen

            async def mock_context():
                nonlocal active_requests, max_seen
                active_requests += 1
                max_seen = max(max_seen, active_requests)
                await asyncio.sleep(0.1)  # Simulate network delay
                active_requests -= 1
                return mock_resp

            cm = MagicMock()
            cm.__aenter__ = mock_context
            cm.__aexit__ = AsyncMock(return_value=None)
            return cm

        mock_post.side_effect = mock_post_side_effect

        payloads = [{"market": "crypto", "filters": [], "columns": ["close"]} for _ in range(10)]

        # Run with max_concurrent=2
        asyncio.run(self.screener.screen_many(payloads, max_concurrent=2))

        self.assertLessEqual(max_seen, 2)

    @patch("aiohttp.ClientSession.post")
    @patch("requests.post")
    def test_sync_async_parity(self, mock_sync_post, mock_async_post):
        # Setup identical mock response for both
        raw_data = {"data": [{"s": "BINANCE:BTCUSDT", "d": [100, 50]}]}

        # Sync mock
        mock_sync_resp = MagicMock()
        mock_sync_resp.status_code = 200
        mock_sync_resp.json.return_value = raw_data
        mock_sync_post.return_value = mock_sync_resp

        # Async mock
        mock_async_resp = MagicMock()
        mock_async_resp.status = 200
        mock_async_resp.json = AsyncMock(return_value=raw_data)

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_async_resp)
        cm.__aexit__ = AsyncMock(return_value=None)
        mock_async_post.return_value = cm

        # Run sync
        sync_screener = Screener()
        sync_result = sync_screener.screen(market="crypto", columns=["close", "volume"])

        # Run async
        async def run_async():
            async with aiohttp.ClientSession() as session:
                return await self.screener.screen(session, market="crypto", columns=["close", "volume"])

        async_result = asyncio.run(run_async())

        # Verify parity
        self.assertEqual(sync_result["status"], async_result["status"])
        self.assertEqual(sync_result["data"], async_result["data"])
        self.assertEqual(sync_result["data"][0]["symbol"], "BINANCE:BTCUSDT")
        self.assertEqual(sync_result["data"][0]["close"], 100)


if __name__ == "__main__":
    unittest.main()
