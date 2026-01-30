import unittest
from unittest.mock import AsyncMock, patch

from tradingview_scraper.symbols.stream.retry_async import AsyncRetryHandler


class TestAsyncRetryHandler(unittest.IsolatedAsyncioTestCase):
    async def test_async_sleep(self):
        handler = AsyncRetryHandler(max_retries=3, initial_delay=1.0)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await handler.sleep(0)  # attempt 0
            # should sleep for roughly 1.0 (with jitter)
            mock_sleep.assert_called_once()

            args, _ = mock_sleep.call_args
            delay = args[0]
            self.assertGreater(delay, 0.8)  # 1.0 - 0.1 jitter - some margin
            self.assertLess(delay, 1.2)  # 1.0 + 0.1 jitter + some margin


if __name__ == "__main__":
    unittest.main()
