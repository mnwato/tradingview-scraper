"""Module providing a function to scrape dividend and earnings of a specific market."""

import json
import datetime
from typing import TypedDict, Union, Optional, List, Dict

import requests
from tradingview_scraper.symbols.utils import (
    save_csv_file,
    save_json_file,
    generate_user_agent,
)


class DividendEvent(TypedDict):
    """
    Represents a dividend event for a financial asset.

    Attributes:
        full_symbol (str): The full trading symbol of the asset.
        dividend_ex_date_recent (int): The most recent ex-dividend date as a timestamp.
        dividend_ex_date_upcoming (Union[int, None]): The upcoming ex-dividend date as a timestamp, or None if not applicable.
        logoid (str): The logo identifier for the asset.
        name (str): The name of the asset.
        description (str): A description of the asset.
        dividends_yield (float): The dividend yield as a percentage.
        dividend_payment_date_recent (int): The most recent dividend payment date as a timestamp.
        dividend_payment_date_upcoming (Union[int, None]): The upcoming dividend payment date as a timestamp, or None if not applicable.
        dividend_amount_recent (float): The amount of the most recent dividend payment.
        dividend_amount_upcoming (Union[float, None]): The amount of the upcoming dividend payment, or None if not applicable.
        fundamental_currency_code (str): The currency code used for the dividends.
        market (str): The market in which the asset is traded.
    """
    full_symbol: str
    dividend_ex_date_recent: int
    dividend_ex_date_upcoming: Union[int, None]
    logoid: str
    name: str
    description: str
    dividends_yield: float
    dividend_payment_date_recent: int
    dividend_payment_date_upcoming: Union[int, None]
    dividend_amount_recent: float
    dividend_amount_upcoming: Union[float, None]
    fundamental_currency_code: str
    market: str


class EarningsEvent(TypedDict):
    """
    Represents an earnings event for a financial asset.

    Attributes:
        full_symbol (str): The full trading symbol of the asset.
        earnings_release_next_date (int): The next earnings release date as a timestamp.
        logoid (str): The logo identifier for the asset.
        name (str): The name of the asset.
        description (str): A description of the asset.
        earnings_per_share_fq (Union[float, None]): The earnings per share for the most recent quarter, or None if not available.
        earnings_per_share_forecast_next_fq (Union[float, None]): The forecasted earnings per share for the next quarter, or None if not available.
        eps_surprise_fq (Union[float, None]): The earnings per share surprise for the most recent quarter, or None if not available.
        eps_surprise_percent_fq (Union[float, None]): The percentage surprise for earnings per share for the most recent quarter, or None if not available.
        revenue_fq (Union[float, None]): The revenue for the most recent quarter, or None if not available.
        revenue_forecast_next_fq (Union[float, None]): The forecasted revenue for the next quarter, or None if not available.
        market_cap_basic (float): The basic market capitalization of the asset.
        earnings_release_time (int): The time of the earnings release as a timestamp.
        earnings_release_next_time (int): The time of the next earnings release as a timestamp.
        earnings_per_share_forecast_fq (Union[float, None]): The forecasted earnings per share for the most recent quarter, or None if not available.
        revenue_forecast_fq (Union[float, None]): The forecasted revenue for the most recent quarter, or None if not available.
        fundamental_currency_code (str): The currency code used for the earnings.
        market (str): The market in which the asset is traded.
        earnings_publication_type_fq (int): The type of earnings publication for the most recent quarter.
        earnings_publication_type_next_fq (int): The type of earnings publication for the next quarter.
        revenue_surprise_fq (Union[float, None]): The revenue surprise for the most recent quarter, or None if not available.
        revenue_surprise_percent_fq (Union[float, None]): The percentage surprise for revenue for the most recent quarter, or None if not available.
    """
    full_symbol: str
    earnings_release_next_date: int
    logoid: str
    name: str
    description: str
    earnings_per_share_fq: Union[float, None]
    earnings_per_share_forecast_next_fq: Union[float, None]
    eps_surprise_fq: Union[float, None]
    eps_surprise_percent_fq: Union[float, None]
    revenue_fq: Union[float, None]
    revenue_forecast_next_fq: Union[float, None]
    market_cap_basic: float
    earnings_release_time: int
    earnings_release_next_time: int
    earnings_per_share_forecast_fq: Union[float, None]
    revenue_forecast_fq: Union[float, None]
    fundamental_currency_code: str
    market: str
    earnings_publication_type_fq: int
    earnings_publication_type_next_fq: int
    revenue_surprise_fq: Union[float, None]
    revenue_surprise_percent_fq: Union[float, None]


class CalendarScraper:
    """
    A class used to scrape dividend and earnings events from the TradingView event calendar.

    Parameters:
        export_result (bool): Optional. A flag indicating whether to export the scraped data to a file. Defaults to False.
        export_type (str): Optional. The type of file to export the data to. Can be 'json' or 'csv'. Defaults to 'json'.
    """

    def __init__(self, export_result: bool = False, export_type: str = "json"):
        self.export_result: bool = export_result
        self.export_type: str = export_type
        self.headers: Dict[str, str] = {"User-Agent": generate_user_agent()}

    def _export(
        self, data, symbol: Union[str, None] = None, data_category: Union[str, None] = None
    ):
        if self.export_result:
            if self.export_type == "json":
                save_json_file(data, symbol, data_category)
            elif self.export_type == "csv":
                save_csv_file(data, symbol, data_category)

    def scrape_dividends(
        self,
        timestamp_from: Optional[int] = None,
        timestamp_to: Optional[int] = None,
        markets: Optional[List[str]] = None,
    ) -> List[DividendEvent]:
        """
        Scrapes dividends events from the TradingView event calendar.

        Args:
            timestamp_from (int): Optional. The start timestamp for the range of dividends to scrape.
            timestamp_to (int): Optional. The end timestamp for the range of dividends to scrape.
            markets (list): Optional. A list of market names to scrape the events from. Example: ["america","argentina","australia","belgium","brazil","canada","china", ...]

        Returns:
            list[DividendEvent]: A typed dictionary containing the scraped event data.

        Raises:
            requests.HTTPError: If the HTTP request to fetch the article fails.
        """
        url = "https://scanner.tradingview.com/global/scan?label-product=calendar-dividends"

        # By default the timestamps mimick the timestamps used in the web requests
        if timestamp_from is None:
            current_date = datetime.datetime.now().timestamp()
            current_date = current_date - (current_date % 86400) - (3 * 86400)
            timestamp_from = int(current_date)

        if timestamp_to is None:
            current_date = datetime.datetime.now().timestamp()
            current_date = current_date - (current_date % 86400) + (3 * 86400) + 86399
            timestamp_to = int(current_date)

        payload = {
            "columns": [
                "dividend_ex_date_recent",
                "dividend_ex_date_upcoming",
                "logoid",
                "name",
                "description",
                "dividends_yield",
                "dividend_payment_date_recent",
                "dividend_payment_date_upcoming",
                "dividend_amount_recent",
                "dividend_amount_upcoming",
                "fundamental_currency_code",
                "market",
            ],
            "filter": [
                {
                    "left": "dividend_ex_date_recent,dividend_ex_date_upcoming",
                    "operation": "in_range",
                    "right": [timestamp_from, timestamp_to],
                }
            ],
            "ignore_unknown_fields": False,
            "options": {"lang": "en"},
        }

        if markets:
            payload["markets"] = markets

        response = requests.post(url, headers=self.headers, data=json.dumps(payload), timeout=5)
        response.raise_for_status()

        # Parse the result into a list
        dividend_events: List[DividendEvent] = []

        for event in response.json()["data"]:
            event_data = event.get("d")

            dividend_event = DividendEvent(
                full_symbol=event.get("s"),
                dividend_ex_date_recent=event_data[0],
                dividend_ex_date_upcoming=event_data[1],
                logoid=event_data[2],
                name=event_data[3],
                description=event_data[4],
                dividends_yield=event_data[5],
                dividend_payment_date_recent=event_data[6],
                dividend_payment_date_upcoming=event_data[7],
                dividend_amount_recent=event_data[8],
                dividend_amount_upcoming=event_data[9],
                fundamental_currency_code=event_data[10],
                market=event_data[11],
            )
            dividend_events.append(dividend_event)

        if self.export_result:
            self._export(dividend_events, "dividends", "calendar")

        return dividend_events


    def scrape_earnings(
        self,
        timestamp_from: Optional[int] = None,
        timestamp_to: Optional[int] = None,
        markets: Optional[List[str]] = None,
    ) -> List[EarningsEvent]:
        """
        Scrapes earnings events from the TradingView event calendar.

        Args:
            timestamp_from (int): Optional. The start timestamp for the range of earnings to scrape.
            timestamp_to (int): Optional. The end timestamp for the range of earnings to scrape.
            markets (list): Optional. A list of market names to scrape the events from. Example: ["america","argentina","australia","belgium","brazil","canada","china", ...]

        Returns:
            list[EarningsEvent]: A typed dictionary containing the scraped event data.

        Raises:
            requests.HTTPError: If the HTTP request to fetch the article fails.
        """
        url = "https://scanner.tradingview.com/global/scan?label-product=calendar-earnings"

        # By default the timestamps mimick the timestamps used in the web requests
        if timestamp_from is None:
            current_date = datetime.datetime.now().timestamp()
            current_date = current_date - (current_date % 86400) - (3 * 86400)
            timestamp_from = int(current_date)

        if timestamp_to is None:
            current_date = datetime.datetime.now().timestamp()
            current_date = current_date - (current_date % 86400) + (3 * 86400) + 86399
            timestamp_to = int(current_date)

        payload = {
            "filter": [
                {
                    "left": "earnings_release_date,earnings_release_next_date",
                    "operation": "in_range",
                    "right": [timestamp_from, timestamp_to],
                }
            ],
            "columns": [
                "earnings_release_next_date",
                "earnings_release_date",
                "logoid",
                "name",
                "description",
                "earnings_per_share_fq",
                "earnings_per_share_forecast_next_fq",
                "eps_surprise_fq",
                "eps_surprise_percent_fq",
                "revenue_fq",
                "revenue_forecast_next_fq",
                "market_cap_basic",
                "earnings_release_time",
                "earnings_release_next_time",
                "earnings_per_share_forecast_fq",
                "revenue_forecast_fq",
                "fundamental_currency_code",
                "market",
                "earnings_publication_type_fq",
                "earnings_publication_type_next_fq",
                "revenue_surprise_fq",
                "revenue_surprise_percent_fq",
            ],
            "options": {"lang": "en"},
        }

        if markets:
            payload["markets"] = markets

        response = requests.post(url, headers=self.headers, data=json.dumps(payload), timeout=5)
        response.raise_for_status()

        # Parse the result into a list
        earnings_events: List[EarningsEvent] = []

        for event in response.json()["data"]:
            event_data = event.get("d")

            earnings_event = EarningsEvent(
                full_symbol=event.get("s"),
                earnings_release_next_date=event_data[0],
                logoid=event_data[1],
                name=event_data[2],
                description=event_data[3],
                earnings_per_share_fq=event_data[4],
                earnings_per_share_forecast_next_fq=event_data[5],
                eps_surprise_fq=event_data[6],
                eps_surprise_percent_fq=event_data[7],
                revenue_fq=event_data[8],
                revenue_forecast_next_fq=event_data[9],
                market_cap_basic=event_data[10],
                earnings_release_time=event_data[11],
                earnings_release_next_time=event_data[12],
                earnings_per_share_forecast_fq=event_data[13],
                revenue_forecast_fq=event_data[14],
                fundamental_currency_code=event_data[15],
                market=event_data[16],
                earnings_publication_type_fq=event_data[17],
                earnings_publication_type_next_fq=event_data[18],
                revenue_surprise_fq=event_data[19],
                revenue_surprise_percent_fq=event_data[20],
            )
            earnings_events.append(earnings_event)

        if self.export_result:
            self._export(earnings_events, "earnings", "calendar")

        return earnings_events
