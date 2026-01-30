"""Module providing a function to scrape published news about a symbol."""

import argparse
import json
import logging
import sys
from importlib.resources import files
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from tradingview_scraper.symbols.utils import (
    generate_user_agent,
    save_csv_file,
    save_json_file,
)


class NewsScraper:
    def __init__(self, export_result=False, export_type="json"):
        self.export_result = export_result
        self.export_type = export_type
        self.headers = {"user-agent": generate_user_agent()}
        self.session = requests

        self.exchanges = self._load_exchanges()
        self.languages = self._load_languages()
        self.news_providers = self._load_news_providers()
        self.areas = self._load_areas()

    def validate_inputs(self, **kwargs):
        symbol = kwargs.get("symbol")
        exchange = kwargs.get("exchange")
        provider = kwargs.get("provider")
        area = kwargs.get("area")
        sort = kwargs.get("sort")
        section = kwargs.get("section")
        language = kwargs.get("language")

        if not any([symbol, exchange]):
            raise ValueError("At least 'symbol' and 'exchange' must be specified.")

        if symbol and not exchange:
            raise ValueError("'symbol' must be used together with 'exchange'.")

        if exchange and exchange not in self.exchanges:
            raise ValueError(
                "Unsupported exchange! Please check 'the available options' at the link below:\n\thttps://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/exchanges.txt"
            )

        if provider and provider not in self.news_providers:
            raise ValueError(
                "Unsupported provider! Please check 'the available options' at the link below:\n\thttps://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/news_providers.txt"
            )

        if area and area not in self.areas:
            raise ValueError("Invalid area! Please check 'the available options' at the link below:\n\thttps://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/areas.json")

        if section not in ["all", "esg", "financial_statement", "press_release"]:
            raise ValueError("Invalid section! It must be 'all' or 'esg'.")

        if sort not in ["latest", "oldest", "most_urgent", "least_urgent"]:
            raise ValueError("Invalid sort option! It must be one of 'latest', 'oldest', 'most_urgent', or 'least_urgent'.")

        if language not in self.languages:
            raise ValueError(
                "Unsupported language! Please check 'the available options' at the link below:\n\thttps://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/languages.json"
            )

        return kwargs

    def scrape_news_content(self, story_path: str):
        """
        Scrapes news content from a TradingView article based on the provided story path.

        Args:
            story_path (str): The path of the story on TradingView, which is appended to the base URL.

        Returns:
            dict: A dictionary containing the scraped article data, including:
                - breadcrumbs (str or None): A string representing the breadcrumb navigation, or None if not found.
                - title (str or None): The title of the article, or None if not found.
                - published_datetime (str or None): The publication date and time of the article, or None if not found.
                - related_symbols (list): A list of dictionaries, each containing 'symbol' and 'logo' for related symbols.
                - body (list): A list of dictionaries representing the article body content, with type and content/attributes.
                - tags (list): A list of tags associated with the article.

        Raises:
            requests.HTTPError: If the HTTP request to fetch the article fails.
        """
        # construct the URL
        url = f"https://tradingview.com{story_path}"

        response = self.session.get(url, headers=self.headers)
        response.raise_for_status()

        # Use BeautifulSoup to parse the HTML
        soup = BeautifulSoup(response.text, "html.parser")

        article_tag = soup.find("article")
        row_tags = soup.find("div", class_=lambda x: x and x.startswith("rowTags-"))

        article_json = {
            "breadcrumbs": None,
            "title": None,
            "published_datetime": None,
            "related_symbols": [],
            "body": [],
            "tags": [],
        }

        # Extracting the fields
        # Breadcrumbs
        breadcrumbs = article_tag.find("nav", {"aria-label": "Breadcrumbs"})
        if breadcrumbs:
            article_json["breadcrumbs"] = " > ".join([item.get_text(strip=True) for item in breadcrumbs.find_all("span", class_="breadcrumb-content-cZAS4vtj")])

        # Title
        title = article_tag.find("h1", class_="title-KX2tCBZq")
        if title:
            article_json["title"] = title.get_text(strip=True)

        # Published Date
        published_time = article_tag.find("time")
        if published_time:
            article_json["published_datetime"] = published_time["datetime"]

        # Symbol Exchange and Logo
        symbol_container = article_tag.find("div", class_="symbolsContainer-cBh_FN2P")
        if symbol_container:
            for a in symbol_container.find_all("a"):
                if a:
                    symbol_name_tag = a.find("span", class_="description-cBh_FN2P")
                    if symbol_name_tag:
                        symbol_name = symbol_name_tag.get_text(strip=True)
                        if symbol_name:
                            symbol_img = a.find("img")
                            article_json["related_symbols"].append({"symbol": symbol_name, "logo": symbol_img})

        # Body extraction
        body_content = article_tag.find("div", class_="body-KX2tCBZq")
        if body_content:
            for element in body_content.find_all(["p", "img"], recursive=True):
                if element.name == "p":
                    article_json["body"].append({"type": "text", "content": element.get_text(strip=True)})
                elif element.name == "img":
                    article_json["body"].append(
                        {
                            "type": "image",
                            "src": element["src"],
                            "alt": element.get("alt", ""),
                        }
                    )

        # Tags
        # Assuming tags are part of the article; adjust as necessary if they're located elsewhere
        if row_tags:
            for a in row_tags.find_all("span"):
                if a:
                    article_json["tags"].append(a.text)

        return article_json

    def scrape_headlines(
        self,
        symbol: str,
        exchange: str,
        provider: Optional[str] = None,
        area: Optional[str] = None,
        sort: str = "latest",
        section: str = "all",
        language: str = "en",
    ):
        """
        Scrapes news headlines for a specified symbol from a given exchange, provider, or global area.

        Parameters
        ----------
        symbol : str
            The trading symbol for which to fetch news.
        exchange : str
            The exchange from which to fetch news.
        provider : str, optional
            The provider from which to fetch news. Defaults to None.
        area : str, optional
            The news area (e.g., "world", "americas", "europe", "asia", "oceania", "africa"). Defaults to None.
        sort : str, optional
            The sorting order of the news. Options are "latest", "oldest", "most_urgent", or "least_urgent". Defaults to "latest".
        section : str, optional
            The section of news to fetch. Options are "all" or "esg". Defaults to "all".
        language : str, optional
            The language code for the news. Defaults to "en".

        Returns
        -------
        list
            A list of news articles, where each article is represented as a dictionary containing relevant details.
            Returns an empty list if no news items are found.

        Raises
        ------
        ValueError
            If the provided section, sort option, language, or exchange is not supported.
        RuntimeError
            If an error occurs during the scraping process.
        HTTPError
            If the HTTP request returns an error response.

        Example
        -------
        news = scraper.scrape_headlines(symbol="AAPL", exchange="NASDAQ", sort="most_urgent")
        """
        # Validate inputs
        kwargs = self.validate_inputs(
            symbol=symbol,
            exchange=exchange,
            provider=provider,
            area=area,
            sort=sort,
            section=section,
            language=language,
        )
        symbol = kwargs["symbol"]
        exchange = kwargs["exchange"]
        provider = kwargs["provider"]
        area = kwargs["area"]
        sort = kwargs["sort"]
        section = kwargs["section"]
        language = kwargs["language"]

        section = "" if section == "all" else section

        area_code = "" if not area else self.areas[area]

        provider = "" if not provider else provider.replace(".", "_")

        url = f"https://news-headlines.tradingview.com/v2/view/headlines/symbol?client=web&lang={language}&area={area_code}&provider={provider}&section={section}&streaming=&symbol={exchange}:{symbol}"

        try:
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx and 5xx)

            response_json = response.json()
            items = response_json.get("items", [])

            if not items:
                return []  # Return empty list if no items

            news_list = self._sort_news(items, sort)

            # Save results
            if self.export_result:
                self._export(data=news_list, symbol=symbol, provider=provider, area=area)

            return news_list

        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 400:
                raise ValueError("Bad request: The server could not understand the request.") from http_err
            raise  # Propagate other HTTP errors
        except Exception as err:
            raise RuntimeError("An error occurred while scraping news.") from err

    def _sort_news(self, news_list, sort):
        # Sort by latest published date
        if sort == "latest":
            news_list = sorted(news_list, key=lambda x: x["published"], reverse=True)

        # Sort by oldest published date
        elif sort == "oldest":
            news_list = sorted(news_list, key=lambda x: x["published"], reverse=False)

        # Sort by most urgent
        elif sort == "most_urgent":
            news_list = sorted(news_list, key=lambda x: x["urgency"], reverse=True)

        # Sort by least urgent
        elif sort == "least_urgent":
            news_list = sorted(news_list, key=lambda x: x["urgency"], reverse=False)

        return news_list

    def _export(self, data, symbol=None, provider=None, area=None):
        data_category = "news_symbol" if symbol else "news_provider" if provider else "news_area"

        if self.export_type == "json":
            save_json_file(data=data, symbol=symbol, data_category=data_category)

        elif self.export_type == "csv":
            save_csv_file(data=data, symbol=symbol, data_category=data_category)

    def _load_languages(self):
        """Load languages from a specified file.

        Returns:
            list: A list of languages loaded from the file.

        Raises:
            IOError: If there is an error reading the file.
        """
        try:
            raw = files("tradingview_scraper").joinpath("data/languages.json").read_text(encoding="utf-8")
            exchanges = json.loads(raw)
            return list(exchanges.values()) if isinstance(exchanges, dict) else []
        except FileNotFoundError:
            print("[ERROR] Languages file not found in package data.")
            return []
        except (OSError, json.JSONDecodeError) as e:
            print(f"[ERROR] Error reading languages file: {e}")
            return []

    def _load_exchanges(self):
        """Load exchanges from a specified file.

        Returns:
            list: A list of exchanges loaded from the file. Returns an empty list if the file is not found.

        Raises:
            IOError: If there is an error reading the file.
        """
        try:
            text = files("tradingview_scraper").joinpath("data/exchanges.txt").read_text(encoding="utf-8")
            return [line.strip() for line in text.splitlines() if line.strip()]
        except FileNotFoundError:
            print("[ERROR] Exchanges file not found in package data.")
            return []
        except OSError as e:
            print(f"[ERROR] Error reading exchanges file: {e}")
            return []

    def _load_news_providers(self):
        """Load news providers from a specified file.

        Returns:
            list: A list of news providers loaded from the file.

        Raises:
            IOError: If there is an error reading the file.
        """
        try:
            text = files("tradingview_scraper").joinpath("data/news_providers.txt").read_text(encoding="utf-8")
            return [line.strip() for line in text.splitlines() if line.strip()]
        except FileNotFoundError:
            print("[ERROR] News provider file not found in package data.")
            return []
        except OSError as e:
            print(f"[ERROR] Error reading providers file: {e}")
            return []

    def _load_areas(self) -> dict:
        """Load areas from a specified file.

        Returns:
            list: A list of areas loaded from the file.

        Raises:
            IOError: If there is an error reading the file.
        """
        try:
            raw = files("tradingview_scraper").joinpath("data/areas.json").read_text(encoding="utf-8")
            areas = json.loads(raw)
            return areas if isinstance(areas, dict) else {}
        except FileNotFoundError:
            print("[ERROR] Areas file not found in package data.")
            return {}
        except (OSError, json.JSONDecodeError) as e:
            print(f"[ERROR] Error reading areas file: {e}")
            return []


def _parse_symbol_list(raw: str) -> List[str]:
    symbols = []
    for part in raw.split(","):
        cleaned = part.strip()
        if cleaned:
            symbols.append(cleaned)
    return symbols


def _load_symbols_from_file(path: str) -> List[str]:
    symbols: List[str] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            candidate = line.strip()
            if candidate:
                symbols.append(candidate)
    return symbols


def _parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TradingView news scraper (headlines + optional bodies)")
    parser.add_argument("--exchange", required=True, help="Exchange code (e.g., BINANCE, NASDAQ)")
    parser.add_argument("--symbols", help="Comma-separated symbols (e.g., BTCUSD,ETHUSD)")
    parser.add_argument(
        "--symbols-file",
        dest="symbols_file",
        help="Path to file with one symbol per line",
    )
    parser.add_argument("--provider", help="News provider filter (see data/news_providers.txt)")
    parser.add_argument("--area", help="Geographic area filter (see data/areas.json, e.g., americas)")
    parser.add_argument(
        "--section",
        default="all",
        choices=["all", "esg", "financial_statement", "press_release"],
        help="News section",
    )
    parser.add_argument("--language", default="en", help="Language code (see data/languages.json)")
    parser.add_argument(
        "--sort",
        default="latest",
        choices=["latest", "oldest", "most_urgent", "least_urgent"],
        help="Sort order",
    )
    parser.add_argument("--max-headlines", type=int, default=20, help="Cap headlines per symbol")
    parser.add_argument(
        "--fetch-content",
        action="store_true",
        help="Fetch article bodies for the first N headlines",
    )
    parser.add_argument(
        "--content-limit",
        type=int,
        default=5,
        help="Number of headlines to fetch body for when enabled",
    )
    parser.add_argument("--export", choices=["json", "csv"], help="Enable export and set format")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def _gather_symbols(args: argparse.Namespace) -> List[str]:
    symbols: List[str] = []
    if args.symbols:
        symbols.extend(_parse_symbol_list(args.symbols))
    if args.symbols_file:
        symbols.extend(_load_symbols_from_file(args.symbols_file))
    # dedupe, preserve order
    seen = set()
    ordered: List[str] = []
    for sym in symbols:
        if sym not in seen:
            ordered.append(sym)
            seen.add(sym)
    if not ordered:
        raise ValueError("At least one symbol is required via --symbols or --symbols-file")
    return ordered


def main(argv: List[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    try:
        symbols = _gather_symbols(args)
    except Exception as exc:  # pragma: no cover - CLI arg validation
        logging.error("Failed to parse symbols: %s", exc)
        return 1

    scraper = NewsScraper(export_result=bool(args.export), export_type=args.export or "json")
    results = {}
    errors: List[str] = []

    for sym in symbols:
        try:
            headlines = scraper.scrape_headlines(
                symbol=sym,
                exchange=args.exchange,
                provider=args.provider,
                area=args.area,
                sort=args.sort,
                section=args.section,
                language=args.language,
            )
            if args.max_headlines:
                headlines = headlines[: args.max_headlines]

            entry = {"headlines": headlines}

            if args.fetch_content and headlines:
                contents = []
                for item in headlines[: args.content_limit]:
                    story_path = item.get("storyPath") or item.get("link", "").replace("https://tradingview.com", "")
                    if not story_path:
                        continue
                    try:
                        content = scraper.scrape_news_content(story_path=story_path)
                        contents.append({"storyPath": story_path, "content": content})
                    except Exception as exc:
                        errors.append(f"{sym}:{story_path}:{exc}")
                entry["content"] = contents

            results[sym] = entry
        except Exception as exc:
            errors.append(f"{sym}:{exc}")

    status = "success" if not errors else "partial_success"
    output = {"status": status, "results": results, "errors": errors}
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0 if status == "success" else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
