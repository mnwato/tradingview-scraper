"""Module providing a function to recieve indicators of a symbol."""

import os
import re
import json
from typing import List, Optional

import requests
import pkg_resources

from tradingview_scraper.symbols.utils import generate_user_agent, save_json_file, save_csv_file

class Indicators:
    def __init__(self, export_result: bool = False, export_type: str = 'json'):
        self.export_result: bool = export_result
        self.export_type: str = export_type
        
        self.indicators: List[str] = self._load_indicators()
        self.exchanges: List[str] = self._load_exchanges()
        self.timeframes: dict = self._load_timeframes()


    def _validate_timeframe(self, timeframe: str) -> None:
        """Validates the specified timeframe against the list of supported timeframes.

        Args:
            timeframe (str): The timeframe to validate.

        Raises:
            ValueError: If the specified timeframe is not in the list of supported timeframes.
        """
        valid_timeframes = self.timeframes.keys()
        if timeframe not in valid_timeframes:
            raise ValueError("This timeframe is not supported! Please check the list of supported timeframes.")


    def _edit_indicators_by_specified_timeframe(self, indicators: List[str], timeframe: str) -> str:
        """Edits the list of indicators by appending the specified timeframe.

        Args:
            indicators (List[str]): A list of indicator names.
            timeframe (str): The timeframe to append to each indicator.

        Returns:
            str: A comma-separated string of revised indicators with timeframes appended.
        """
        if timeframe == '1d':
            return ','.join(indicators)

        timeframe_value = self.timeframes.get(timeframe)
        if timeframe_value:
            revised_indicators = [f'{ind}|{timeframe_value}' for ind in indicators]
            return ','.join(revised_indicators)
        
        return ','.join(indicators)
        
            
    def scrape(
        self,
        exchange: str = "BITSTAMP",
        symbol: str = "BTCUSD",
        timeframe: str = "1d",
        indicators: Optional[List[str]] = None,
        allIndicators: bool = False,
    ) -> dict:
        """Scrape data from the TradingView scanner.

        Args:
            exchange (str): The exchange to scrape data from (default is "BITSTAMP").
            symbol (str): The symbol to scrape data for (default is "BTCUSD").
            timeframe (str): A timeframe. (default is "1d").
            indicators (Optional[List[str]]): A list of indicators to scrape (default is None).
            allIndicators (bool): If True, scrape all indicators; otherwise, check if specified indicators are valid (default is False).

        Returns:
            dict: The scraped data in JSON format. Returns an empty dictionary if the request fails.

        Raises:
            ValueError: If the specified exchange or indicators are not supported.
            requests.RequestException: If there is an error during the HTTP request.
        """
        self._validate_timeframe(timeframe)

        if exchange not in self.exchanges:
            raise ValueError("This exchange is not supported! Please check the list of supported exchanges.")

        if not allIndicators:
            if not indicators or len(indicators) == 0:
                raise ValueError("If allIndicators is False, indicators cannot be empty.")
            
            unsupported_indicators = [indicator for indicator in indicators if indicator not in self.indicators]
            if unsupported_indicators:
                raise ValueError(f"Unsupported indicators: {', '.join(unsupported_indicators)}. "
                                "Please check the list of supported indicators at the following link:\n"
                                "https://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/indicators.txt")
        else:
            indicators = self.indicators

        base_url = "https://scanner.tradingview.com/symbol"
        fields = self._edit_indicators_by_specified_timeframe(indicators, timeframe)
        url = f"{base_url}?symbol={exchange}:{symbol}&fields={fields}&no_404=true"
        headers = {'user-agent': generate_user_agent()}

        try:
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                json_response = response.json()
                if not json_response:
                    return {"status": "failed"}
                
                if self.export_result:
                    self._export(data=[json_response], symbol=symbol)
                return {"status": "success", "data": self.revise_response(json_response)}
            
            else:
                return {"status": "failed"}
            
        except requests.RequestException as e:
            print(f"[ERROR] Failed to scrape data: {e}")
            return {"status": "failed"}


    def revise_response(self, json_response: dict) -> dict:
        """Revise the JSON response by removing timeframes from indicator keys.

        Args:
            json_response (dict): The original JSON response.

        Returns:
            dict: The revised response with cleaned keys.
        """
        return {re.sub(r'\|.*', '', k): v for k, v in json_response.items()}
            

    def _export(self, data: List[dict], symbol: str) -> None:
        """Export data to a file in the specified format.

        Args:
            data (List[dict]): The data to export.
            symbol (str): The symbol associated with the data.
        """
        if self.export_type == "json":
            save_json_file(data=data, symbol=symbol, data_category='indicators')
        elif self.export_type == "csv":
            save_csv_file(data=data, symbol=symbol, data_category='indicators')
    
    def _load_file(self, path):
        """Load data from a specified file.

        Args:
            path (str): The path to the file.

        Returns:
            list: A list of data loaded from the file, or an empty list if the file is not found or an error occurs.
        """
        if not os.path.exists(path):
            print(f"[ERROR] file not found at {path}.")
            return []
        try:
            with open(path, 'r', encoding="utf-8") as f:
                return [line.strip() for line in f.readlines()]
        except IOError as e:
            print(f"[ERROR] Error reading file {path}: {e}")
            return []

    def _load_indicators(self) -> List[str]:
        """Load indicators from a specified file.

        Returns:
            List[str]: A list of indicators loaded from the file. Returns an empty list if the file is not found.
        """
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/indicators.txt')
        return self._load_file(path)

    def _load_exchanges(self) -> List[str]:
        """Load exchanges from a specified file.

        Returns:
            List[str]: A list of exchanges loaded from the file. Returns an empty list if the file is not found.
        """
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/exchanges.txt')
        return self._load_file(path)
    
    def _load_timeframes(self) -> dict:
        """Load timeframes from a specified file.

        Returns:
            dict: A dictionary of timeframes loaded from the file. Returns a dict with '1d' as default.
        """
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/timeframes.json')
        if not os.path.exists(path):
            print(f"[ERROR] Timeframe file not found at {path}.")
            return {"1d": None}
        try:
            with open(path, 'r', encoding="utf-8") as f:
                timeframes = json.load(f)
            return timeframes.get('indicators', {"1d": None})
        except IOError as e:
            print(f"[ERROR] Error reading timeframe file: {e}")
            return {"1d": None}
