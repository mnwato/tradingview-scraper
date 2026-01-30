import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential_jitter,
)

from tradingview_scraper.symbols.utils import (
    generate_user_agent,
    save_csv_file,
    save_json_file,
)

logger = logging.getLogger(__name__)


class AsyncScreener:
    """
    Asynchronous version of the Screener for high-performance scanning.
    """

    SUPPORTED_MARKETS = {
        "america": "https://scanner.tradingview.com/america/scan",
        "australia": "https://scanner.tradingview.com/australia/scan",
        "canada": "https://scanner.tradingview.com/canada/scan",
        "germany": "https://scanner.tradingview.com/germany/scan",
        "india": "https://scanner.tradingview.com/india/scan",
        "israel": "https://scanner.tradingview.com/israel/scan",
        "italy": "https://scanner.tradingview.com/italy/scan",
        "luxembourg": "https://scanner.tradingview.com/luxembourg/scan",
        "mexico": "https://scanner.tradingview.com/mexico/scan",
        "spain": "https://scanner.tradingview.com/spain/scan",
        "turkey": "https://scanner.tradingview.com/turkey/scan",
        "uk": "https://scanner.tradingview.com/uk/scan",
        "crypto": "https://scanner.tradingview.com/crypto/scan",
        "forex": "https://scanner.tradingview.com/forex/scan",
        "cfd": "https://scanner.tradingview.com/cfd/scan",
        "futures": "https://scanner.tradingview.com/futures/scan",
        "bonds": "https://scanner.tradingview.com/bonds/scan",
        "global": "https://scanner.tradingview.com/global/scan",
    }

    # Default columns for stock screener
    DEFAULT_STOCK_COLUMNS = [
        "name",
        "close",
        "change",
        "change_abs",
        "volume",
        "Recommend.All",
        "market_cap_basic",
        "price_earnings_ttm",
        "earnings_per_share_basic_ttm",
    ]

    # Default columns for crypto screener
    DEFAULT_CRYPTO_COLUMNS = [
        "name",
        "close",
        "change",
        "change_abs",
        "volume",
        "market_cap_calc",
        "Recommend.All",
    ]

    # Default columns for forex screener
    DEFAULT_FOREX_COLUMNS = [
        "name",
        "close",
        "change",
        "change_abs",
        "Recommend.All",
    ]

    def __init__(self, export_result: bool = False, export_type: str = "json"):
        """
        Initialize the AsyncScreener.
        """
        self.export_result = export_result
        self.export_type = export_type
        self.headers = {"User-Agent": generate_user_agent()}

    def _get_default_columns(self, market: str) -> List[str]:
        """
        Get default columns based on market type.
        """
        if market == "crypto":
            return self.DEFAULT_CRYPTO_COLUMNS
        elif market == "forex":
            return self.DEFAULT_FOREX_COLUMNS
        else:
            return self.DEFAULT_STOCK_COLUMNS

    def _export(
        self,
        data: List[Dict],
        symbol: Optional[str] = None,
        data_category: Optional[str] = None,
    ) -> None:
        """
        Export screened data to file.
        """
        if self.export_type == "json":
            save_json_file(data=data, symbol=symbol, data_category=data_category)
        elif self.export_type == "csv":
            save_csv_file(data=data, symbol=symbol, data_category=data_category)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=1, max=30),
        retry=(
            retry_if_exception_type(aiohttp.ClientError)
            | retry_if_result(lambda res: res.get("status") == "failed" and "HTTP 429" in res.get("error", ""))
            | retry_if_result(lambda res: res.get("status") == "failed" and any(code in res.get("error", "") for code in ["500", "502", "503", "504"]))
        ),
        reraise=True,
    )
    async def _single_screen(
        self,
        session: aiohttp.ClientSession,
        market: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        columns: Optional[List[str]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 50,
        range_start: int = 0,
    ) -> Dict:
        """Perform a single asynchronous screen request."""
        url = self.SUPPORTED_MARKETS.get(market)
        if not url:
            return {"status": "failed", "error": f"Unsupported market: {market}"}

        if columns is None:
            columns = self._get_default_columns(market)

        if filters is None:
            filters = []

        payload = {
            "columns": columns,
            "filter": filters,
            "options": {"lang": "en"},
            "range": [range_start, range_start + limit],
        }
        if sort_by:
            payload["sort"] = {"sortBy": sort_by, "sortOrder": sort_order}

        try:
            async with session.post(url, json=payload, headers=self.headers, timeout=10) as response:
                if response.status == 200:
                    json_response = await response.json()
                    data = json_response.get("data", [])
                    if data is None:
                        data = []

                    formatted_data = []
                    for item in data:
                        if not item or not isinstance(item, dict):
                            continue
                        symbol_data = item.get("d", [])
                        if symbol_data and len(symbol_data) > 0:
                            formatted_item = {"symbol": item.get("s", "")}
                            for idx, field in enumerate(columns):
                                if idx < len(symbol_data):
                                    formatted_item[field] = symbol_data[idx]
                            formatted_data.append(formatted_item)

                    return {"status": "success", "data": formatted_data}
                else:
                    text = await response.text()
                    return {"status": "failed", "error": f"HTTP {response.status}: {text}"}
        except aiohttp.ClientError:
            # Reraise so tenacity @retry can catch it
            raise
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def screen(
        self,
        session: aiohttp.ClientSession,
        market: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        columns: Optional[List[str]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 50,
        range_start: int = 0,
    ) -> Dict:
        """
        Screen instruments with automatic pagination for limits > 50.
        """
        if columns is None:
            columns = self._get_default_columns(market)

        if filters is None:
            filters = []

        all_data = []
        remaining = limit
        current_offset = range_start
        page_size = 50

        while remaining > 0:
            batch_limit = min(page_size, remaining)
            res = await self._single_screen(
                session=session,
                market=market,
                filters=filters,
                columns=columns,
                sort_by=sort_by,
                sort_order=sort_order,
                limit=batch_limit,
                range_start=current_offset,
            )

            if res["status"] != "success":
                # If we have some data, return partial success
                if all_data:
                    break
                return res

            page_data = res.get("data", [])
            all_data.extend(page_data)

            if len(page_data) < batch_limit:
                # End of results
                break

            remaining -= len(page_data)
            current_offset += len(page_data)

        # Export if requested
        if self.export_result:
            self._export(
                data=all_data,
                symbol=f"{market}_screener",
                data_category="screener",
            )

        return {"status": "success", "data": all_data}

    async def screen_many(self, payloads: List[Dict], max_concurrent: int = 5) -> List[Dict]:
        """
        Perform multiple screen requests in parallel.

        Each payload should contain: market, filters, columns, and optionally sort_by, sort_order, limit, range_start.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _bounded_screen(session, p):
            async with semaphore:
                return await self.screen(
                    session=session,
                    market=p["market"],
                    filters=p["filters"],
                    columns=p["columns"],
                    sort_by=p.get("sort_by"),
                    sort_order=p.get("sort_order", "desc"),
                    limit=p.get("limit", 50),
                    range_start=p.get("range_start", 0),
                )

        async with aiohttp.ClientSession() as session:
            tasks = [_bounded_screen(session, p) for p in payloads]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Post-process to handle captured exceptions
            final_results = []
            for i, res in enumerate(results):
                if isinstance(res, Exception):
                    logger.error(f"Async scan {i} failed with exception: {res}")
                    final_results.append({"status": "failed", "error": str(res)})
                else:
                    final_results.append(res)
            return final_results
