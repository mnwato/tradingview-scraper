"""Module providing a function to scrape published user ideas about a symbol."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# loading environment variables
from dotenv import load_dotenv
from requests.exceptions import JSONDecodeError, RequestException

from tradingview_scraper.symbols.utils import (
    generate_user_agent,
    save_csv_file,
    save_json_file,
)

load_dotenv()


class Ideas:
    def __init__(self, export_result=False, export_type="json"):
        self.export_result = export_result
        self.export_type = export_type
        self.headers = {"user-agent": generate_user_agent()}
        self.session = requests

    def scrape(self, symbol: str = "BTCUSD", startPage: int = 1, endPage: int = 1, sort: str = "popular"):
        """
        Extract trading ideas from TradingView for a specified symbol over a range of pages.

        This method scrapes trading ideas related to a particular symbol from TradingView.
        Users can specify the range of pages to scrape, enabling the collection of multiple ideas at once.
        The results can be sorted by popularity or recency.

        Parameters
        ----------
        symbol : str, optional
            The trading symbol for which to scrape ideas. Defaults to "BTCUSD".
        startPage : int, optional
            The page number where the scraper should start. Defaults to 1.
        endPage : int, optional
            The page number where the scraper should end. Defaults to 1.
            If this is the same as startPage, the scraper will only scrape one page.
        sort : str, optional
            The sorting criteria for the ideas. Can be either 'popular' or 'recent'. Defaults to 'popular'.

        Returns
        -------
        list
            A list of dictionaries containing the scraped trading ideas. Each dictionary
            includes details such as title, description, author, and publication date.

        Raises
        ------
        Exception
            If no ideas are found for the specified symbol or page number, or if the sort argument is invalid.

        Notes
        -----
        The method includes a delay of 5 seconds between requests to avoid overwhelming
        the server with rapid requests.
        """
        cookie = os.getenv("TRADINGVIEW_COOKIE", "")
        if cookie:
            self.headers["cookie"] = cookie
        pageList = range(startPage, endPage + 1)
        articles = []

        if sort not in ["popular", "recent"]:
            logging.error("sort argument must be one 'popular' or 'recent'")
            return []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(self.scrape_ideas, symbol, page, sort): page for page in pageList}
            for future in as_completed(futures):
                page = futures[future]
                try:
                    result = future.result()
                    articles.extend(result)
                    # print(f"[INFO] Page {page} scraped successfully")
                except Exception as e:
                    logging.error(f"Failed to scrape page {page}: {e}")
                    # errors.append(f"[ERROR] Failed to scrape page {page}: {e}")

        # Save results
        if self.export_result == True:
            self._export(data=articles, symbol=symbol)

        return articles

    def _export(self, data, symbol):
        if self.export_type == "json":
            save_json_file(data=data, symbol=symbol, data_category="ideas")

        elif self.export_type == "csv":
            save_csv_file(data=data, symbol=symbol, data_category="ideas")

    def scrape_ideas(self, symbol: str, page: int, sort: str):
        """
        Scrapes trading ideas (popular or recent) for a specified symbol and page from TradingView using JSON API.
        """
        base_url = "https://www.tradingview.com/symbols/"
        symbol_payload = f"{symbol}/"

        if page == 1:
            url = f"{base_url}{symbol_payload}ideas/"
        else:
            url = f"{base_url}{symbol_payload}ideas/page-{page}/"

        params = {"component-data-only": "1"}  # to receive json data
        if sort == "recent":
            params["sort"] = "recent"  # default is popular so only include for recent

        try:
            response = self.session.get(url, headers=self.headers, params=params, timeout=10)
            if response.status_code != 200:
                logging.error(f"HTTP {response.status_code}: Failed to fetch page {page} for {symbol}")
                return []
            if r"<title>Captcha Challenge</title>" in response.text:
                logging.error(f"Captcha Challenge encountered for page {page} of {symbol}. Try updating the TRADINGVIEW_COOKIE in your .env file.")
                return []
            data = response.json()

            ideas_data = data.get("data", {}).get("ideas", {}).get("data", {})
            items = ideas_data.get("items", [])

            # Transform each item to desired output format
            ideas = []
            for item in items:
                ideas.append(
                    {
                        "title": item.get("name", ""),
                        "description": item.get("description", ""),
                        "preview_image": item.get("symbol", {}).get("logo_urls", []),
                        "chart_url": item.get("chart_url", ""),
                        "comments_count": item.get("comments_count", 0),
                        "views_count": item.get("views_count", 0),
                        "author": item.get("user", {}).get("username", ""),
                        "likes_count": item.get("likes_count", 0),
                        "timestamp": item.get("date_timestamp", 0),
                    }
                )
            return ideas

        except JSONDecodeError as e:
            logging.error(f"Invalid JSON for page {page} of {symbol}: {e}")
            return []

        except RequestException as e:
            logging.error(f"Network request failed for page {page} of {symbol}: {e}")
            return []

        except Exception as e:
            logging.error(f"Unexpected error scraping page {page} of {symbol}: {e}")
            return []
