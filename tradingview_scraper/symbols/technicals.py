import requests
import pkg_resources
import os
import re
import json
from typing import List, Optional

from tradingview_scraper.symbols.utils import generate_user_agent, save_json_file, save_csv_file

class Indicators:
    def __init__(self, export_result=False, export_type='json'):
        self.export_result = export_result
        self.export_type = export_type
        
        self.indicators = self._load_indicators()
        self.exchanges = self._load_exchanges()
        self.timeframes = self._load_timeframes()


    def _validate_timeframe(self, timeframe: str):
        """
        Validates the specified timeframe against the list of supported timeframes.

        Args:
            timeframe (str): The timeframe to validate.

        Raises:
            AssertionError: If the specified timeframe is not in the list of supported timeframes.

        Notes:
            Supported timeframes are derived from the keys of the `timeframes` attribute.
        """
        valid_timeframes = self.timeframes.keys()
        assert timeframe in valid_timeframes, "This timeframe is not supported! Please check the list of supported timeframes."


    def _edit_indicators_by_specified_timeframe(self, indicators: list, timeframe: str):
        """
        Edits the list of indicators by appending the specified timeframe.

        If the timeframe is '1d', it will be treated as None and not appended to the indicators.

        Args:
            indicators (list): A list of indicator names to be modified.
            timeframe (str): The timeframe to append to each indicator. If '1d', no timeframe is appended.

        Returns:
            str: A comma-separated string of revised indicators with timeframes appended.

        Notes:
            If the timeframe is not provided or is None, the original indicators are returned as is.
        """
        if timeframe == '1d':
            timeframe = None
            
        if timeframe:
            timeframe = self.timeframes.get(timeframe)
            revised_indicators = [f'{ind}|{timeframe}' for ind in indicators]
        else:
            revised_indicators = indicators

        return ','.join(revised_indicators)
        
        
    def scrape(
        self,
        exchange: str = "BITSTAMP",
        symbol: str = "BTCUSD",
        timeframe: Optional[str] = None,
        indicators: Optional[List[str]] = None,
        allIndicators: bool = False,
    ) -> dict:
        """Scrape data from the TradingView scanner.

        Args:
            exchange (str): The exchange to scrape data from (default is "BITSTAMP").
            symbol (str): The symbol to scrape data for (default is "BTCUSD").
            timeframe (str): A timeframe (default is "1d").
            indicators (list): A list of indicators to scrape (default is ["RSI", "Stoch.K"]).
            allIndicators (bool): If True, scrape all indicators; otherwise, check if specified indicators are valid (default is False).

        Returns:
            dict: The scraped data in JSON format. Returns an empty dictionary if the request fails.

        Raises:
            AssertionError: If the specified exchange or indicators are not supported.
            requests.RequestException: If there is an error during the HTTP request.
        """
        
        self._validate_timeframe(timeframe)
        

        # Check if the exchange is supported
        if exchange not in self.exchanges:
            raise ValueError("This exchange is not supported! Please check the list of supported exchanges.")

        # Validate indicators based on allIndicators flag
        if not allIndicators:
            if indicators is None or len(indicators) == 0:
                raise ValueError("If allIndicators is False, indicators cannot be empty.")
            
            unsupported_indicators = [indicator for indicator in indicators if indicator not in self.indicators]
            if unsupported_indicators:
                raise ValueError(f"Unsupported indicators: {', '.join(unsupported_indicators)}. "
                                "Please check the list of supported indicators at the following link:\n"
                                "https://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/indicators.txt")
        else:
            indicators = self.indicators

            
        # Construct the URL for scraping
        base_url = "https://scanner.tradingview.com/symbol"
        # fields = ','.join(indicators)
        fields = self._edit_indicators_by_specified_timeframe(indicators, timeframe)
        url = f"{base_url}?symbol={exchange}:{symbol}&fields={fields}&no_404=true"
        headers = {'user-agent': generate_user_agent()}

        # Make the HTTP request
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses
            json_response = response.json()
            
            # Save results
            if self.export_result == True:
                self._export(data=[json_response], symbol=symbol)

            revised_response = self.revise_response(json_response)                
            return revised_response
        
        except requests.RequestException as e:
            print(f"[ERROR] Failed to scrape data: {e}")
            return {}


    def revise_response(self, json_response):
        revised_response = {}
        for k,v in json_response.items():
            k = re.sub('\|.*', '', k)
            revised_response.update({k:v})
        return revised_response
        

    def _export(self, data, symbol):
        if self.export_type == "json":
            save_json_file(data=data, symbol=symbol, data_category='indicators')
            
        elif self.export_type == "csv":
            save_csv_file(data=data, symbol=symbol, data_category='indicators')
            
            
    def _load_indicators(self):
        """Load indicators from a specified file.

        Returns:
            list: A list of indicators loaded from the file. Returns an empty list if the file is not found.

        Raises:
            IOError: If there is an error reading the file.
        """
        # Get the path to the indicators.txt file in the package
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/indicators.txt')
        if not os.path.exists(path):
            print(f"[ERROR] Indicators file not found at {path}.")
            return []
        try:
            with open(path, 'r') as f:
                indicators = f.readlines()
            return [indicator.strip() for indicator in indicators]
        except IOError as e:
            print(f"[ERROR] Error reading indicators file: {e}")
            return []
        

    def _load_exchanges(self):
        """Load exchanges from a specified file.

        Returns:
            list: A list of exchanges loaded from the file. Returns an empty list if the file is not found.

        Raises:
            IOError: If there is an error reading the file.
        """
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/exchanges.txt')
        if not os.path.exists(path):
            print(f"[ERROR] Exchanges file not found at {path}.")
            return []
        try:
            with open(path, 'r') as f:
                exchanges = f.readlines()
            return [exchange.strip() for exchange in exchanges]
        except IOError as e:
            print(f"[ERROR] Error reading exchanges file: {e}")
            return []
    
    
    def _load_timeframes(self):
        """Load timeframes from a specified file.

        Returns:
            dict: A dictionary of timeframes mapping loaded from the file. Returns a dict with '1d' timeframe as default timeframe.

        Raises:
            IOError: If there is an error reading the file.
        """
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/timeframes.json')
        if not os.path.exists(path):
            print(f"[ERROR] Timeframe file not found at {path}.")
            return {"1d": None}
        try:
            with open(path, 'r') as f:
                timeframes = json.load(f)
            if 'indicators' in timeframes:
                return timeframes['indicators']
            else:
                return {"1d": None}
        except IOError as e:
            print(f"[ERROR] Error reading timeframe file: {e}")
            return {"1d": None}
