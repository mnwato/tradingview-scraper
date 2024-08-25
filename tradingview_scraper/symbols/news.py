
import requests
import pkg_resources
import json
import os


from tradingview_scraper.symbols.utils import save_csv_file, save_json_file, generate_user_agent

class NewsScraper:
    def __init__(self, export_result=False, export_type='json'):
        self.export_result = export_result
        self.export_type = export_type
        self.headers = {"user-agent": generate_user_agent()}
        
        self.exchanges = self._load_exchanges()
        self.languages = self._load_languages()

    def scrape_headlines(
        self,
        symbol: str = "BTCUSD",
        exchange: str = "BINANCE",
        sort: str = "latest",
        section: str = "all",
        language: str = "en"
      ):
        """
        Scrapes news headlines for a specified symbol from a given exchange.

        Parameters:
            symbol (str): The trading symbol for which to fetch news. Default is "BTCUSD".
            exchange (str): The exchange from which to fetch news. Default is "BINANCE".
            sort (str): The sorting order of the news. Options are "latest", "oldest", 
                        "most_urgent", or "least_urgent". Default is "latest".
            section (str): The section of news to fetch. Options are "all" or "esg". 
                          Default is "all".
            language (str): The language code for the news. Default is "en".

        Returns:
            list: A list of news articles, where each article is represented as a 
                  dictionary containing relevant details. Returns an empty list if 
                  no news items are found.

        Raises:
            ValueError: If the provided section, sort option, language, or exchange 
                        is not supported.
            RuntimeError: If an error occurs during the scraping process.
            HTTPError: If the HTTP request returns an error response.

        Example:
            news = scraper.scrape_news(symbol="AAPL", exchange="NASDAQ", sort="most_urgent")
        """

        # Validate inputs
        if section not in ["all", "esg"]:
            raise ValueError("This section is not supported! It must be 'all' or 'esg'")
        section = "" if section == "all" else section

        if sort not in ["latest", "oldest", "most_urgent", "least_urgent"]:
            raise ValueError("This section is not supported! It must be 'latest' or 'esoldestg', or 'most_urgent', 'least_urgent'")
        
        if language not in self.languages:
            raise ValueError("This language is not supported! Please check 'the available options'.")
        
        if exchange not in self.exchanges:
            raise ValueError("This exchange is not supported! Please check 'the available options'.")
        
        # Construct the URL
        url = f"https://news-headlines.tradingview.com/v2/view/headlines/symbol?client=web&lang={language}&section={section}&streaming=&symbol={exchange}:{symbol}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx and 5xx)
            
            response_json = response.json()
            items = response_json.get('items', [])
            
            if not items:
                return []  # Return empty list if no items
            
            # Filter out items without relatedSymbols
            news_list = [item for item in items if item.pop("relatedSymbols", None) is not None]

            news_list = NewsScraper._sort_news(news_list, sort)
                        
            # Save results
            if self.export_result == True:
                self._export(data=news_list, symbol=symbol)

            return news_list
            
        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 400:
                raise ValueError("Bad request: The server could not understand the request.") from http_err
            raise  # Propagate other HTTP errors
        except Exception as err:
            raise RuntimeError("An error occurred while scraping news.") from err

    def _sort_news(news_list, sort):
      # Sort by latest published date
      if sort=="latest":
        news_list = sorted(news_list, key=lambda x: x['published'], reverse=True)
      
      # Sort by oldest published date
      elif sort=="oldest":
        news_list = sorted(news_list, key=lambda x: x['published'], reverse=False)
        
      # Sort by most urgent
      elif sort=="most_urgent":
        news_list = sorted(news_list, key=lambda x: x['urgency'], reverse=True)
      
      # Sort by least urgent
      elif sort=="least_urgent":
        news_list = sorted(news_list, key=lambda x: x['urgency'], reverse=False)
      
      return news_list


    def _export(self, data, symbol):
        if self.export_type == "json":
            save_json_file(data=data, symbol=symbol, data_category='news')
            
        elif self.export_type == "csv":
            save_csv_file(data=data, symbol=symbol, data_category='news')


    def _load_languages(self):
        """Load languages from a specified file.

        Returns:
            list: A list of languages loaded from the file.

        Raises:
            IOError: If there is an error reading the file.
        """
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/languages.json')
        if not os.path.exists(path):
            print(f"[ERROR] Languages file not found at {path}.")
            return []
        try:
            with open(path, 'r') as f:
                exchanges = json.load(f)
            return list(exchanges.values())
        except IOError as e:
            print(f"[ERROR] Error reading languages file: {e}")
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