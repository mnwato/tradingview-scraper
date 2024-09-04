import requests
import pkg_resources
import os
from tradingview_scraper.symbols.utils import generate_user_agent, save_json_file, save_csv_file

class Indicators:
    def __init__(self, export_result=False, export_type='json'):
        self.export_result = export_result
        self.export_type = export_type
        
        self.indicators = self._load_indicators()
        self.exchanges = self._load_exchanges()


    def scrape(
        self,
        exchange: str = "BITSTAMP",
        symbol: str = "BTCUSD",
        indicators: list = ["RSI", "Stoch.K"],
        allIndicators: bool = False,
    ) -> dict:
        """Scrape data from the TradingView scanner.

        Args:
            exchange (str): The exchange to scrape data from (default is "BITSTAMP").
            symbol (str): The symbol to scrape data for (default is "BTCUSD").
            indicators (list): A list of indicators to scrape (default is ["RSI", "Stoch.K"]).
            allIndicators (bool): If True, scrape all indicators; otherwise, check if specified indicators are valid (default is False).

        Returns:
            dict: The scraped data in JSON format. Returns an empty dictionary if the request fails.

        Raises:
            AssertionError: If the specified exchange or indicators are not supported.
            requests.RequestException: If there is an error during the HTTP request.
        """
        # Check if the exchange and indicators are supported
        assert exchange in self.exchanges, "This exchange is not supported! Please check the list of supported exchanges."

        if not allIndicators:
            for indicator in indicators:
                assert indicator in self.indicators, "This indicator is not supported! Please check the list of supported indicators at link bellow\n\thttps://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/indicators.txt"

        # Construct the URL for scraping
        base_url = "https://scanner.tradingview.com/symbol"
        fields = ','.join(indicators)
        url = f"{base_url}?symbol={exchange}:{symbol}&fields={fields}&no_404=true"
        headers = {'user-agent': generate_user_agent()}

        # Make the HTTP request
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses
            indicators_json = response.json()
            
            # Save results
            if self.export_result == True:
                self._export(data=[indicators_json], symbol=symbol)
                
            return indicators_json
        
        except requests.RequestException as e:
            print(f"[ERROR] Failed to scrape data: {e}")
            return {}


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