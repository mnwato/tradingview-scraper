"""Module providing a function to scrape published news about a symbol."""

import os
import json

from bs4 import BeautifulSoup
import requests
import pkg_resources


from tradingview_scraper.symbols.utils import save_csv_file, save_json_file, generate_user_agent

class NewsScraper:
    def __init__(self, export_result=False, export_type='json'):
        self.export_result = export_result
        self.export_type = export_type
        self.headers = {"user-agent": generate_user_agent()}

        self.exchanges = self._load_exchanges()
        self.languages = self._load_languages()
        self.news_providers = self._load_news_providers()
        self.areas = self._load_areas()

    def validate_inputs(self, **kwargs):
        symbol = kwargs.get('symbol')
        exchange = kwargs.get('exchange')
        provider = kwargs.get('provider')
        area = kwargs.get('area')
        sort = kwargs.get('sort')
        section = kwargs.get('section')
        language = kwargs.get('language')

        if not any([symbol, exchange]):
            raise ValueError("At least 'symbol' and 'exchange' must be specified.")

        if symbol and not exchange:
            raise ValueError("'symbol' must be used together with 'exchange'.")

        if exchange and exchange not in self.exchanges:
            raise ValueError("Unsupported exchange! Please check 'the available options' at the link below:\n\t"
                             "https://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/exchanges.txt")

        if provider and provider not in self.news_providers:
            raise ValueError("Unsupported provider! Please check 'the available options' at the link below:\n\t"
                             "https://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/news_providers.txt")

        if area and area not in self.areas:
            raise ValueError("Invalid area! Please check 'the available options' at the link below:\n\t"
                             "https://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/areas.json")

        if section not in ["all", "esg", "financial_statement", "press_release"]:
            raise ValueError("Invalid section! It must be 'all' or 'esg'.")

        if sort not in ["latest", "oldest", "most_urgent", "least_urgent"]:
            raise ValueError("Invalid sort option! It must be one of 'latest', 'oldest', 'most_urgent', or 'least_urgent'.")

        if language not in self.languages:
            raise ValueError("Unsupported language! Please check 'the available options' at the link below:\n\t"
                             "https://github.com/mnwato/tradingview-scraper/blob/main/tradingview_scraper/data/languages.json")

        return kwargs
        
    def scrape_news_content(
      self,
      story_path: str
      ):
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
        
        response = requests.get(url, headers=self.headers, timeout=5)
        response.raise_for_status()

        # Use BeautifulSoup to parse the HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        article_tag = soup.find('article')
        row_tags = soup.find('div', class_=lambda x: x and x.startswith('rowTags-'))

        article_json = {
            "breadcrumbs": None,
            "title": None,
            "published_datetime": None,
            "related_symbols": [],
            "body": [],
            "tags": []
        }
        
        # Extracting the fields
        # Breadcrumbs
        breadcrumbs = article_tag.find('nav', {'aria-label': 'Breadcrumbs'})
        if breadcrumbs:
            article_json['breadcrumbs'] = ' > '.join(
                [item.get_text(strip=True) for item in breadcrumbs.find_all('span', class_='breadcrumb-content-cZAS4vtj')]
            )

        # Title
        title = article_tag.find('h1', class_='title-KX2tCBZq')
        if title:
            article_json['title'] = title.get_text(strip=True)

        # Published Date
        published_time = article_tag.find('time')
        if published_time:
            article_json['published_datetime'] = published_time['datetime']

        # Symbol Exchange and Logo
        symbol_container = article_tag.find('div', class_='symbolsContainer-cBh_FN2P')
        if symbol_container:
            for a in symbol_container.find_all('a'):
                if a:
                    symbol_name_tag = a.find('span', class_='description-cBh_FN2P')
                    if symbol_name_tag:
                        symbol_name = symbol_name_tag.get_text(strip=True)
                        if symbol_name:
                            symbol_img = a.find('img')
                            article_json['related_symbols'].append({'symbol': symbol_name, 'logo': symbol_img})

        # Body extraction
        body_content = article_tag.find('div', class_='body-KX2tCBZq')
        if body_content:
            for element in body_content.find_all(['p', 'img'], recursive=True):
                if element.name == 'p':
                    article_json['body'].append({
                        "type": "text",
                        "content": element.get_text(strip=True)
                    })
                elif element.name == 'img':
                    article_json['body'].append({
                        "type": "image",
                        "src": element['src'],
                        "alt": element.get('alt', '')
                    })

        # Tags
        # Assuming tags are part of the article; adjust as necessary if they're located elsewhere
        if row_tags:
            for a in row_tags.find_all('span'):
                if a:
                    article_json['tags'].append(a.text)
        
        return article_json


    def scrape_headlines(
        self,
        symbol: str,
        exchange: str,
        provider: str = None,
        area: str = None,
        sort: str = "latest",
        section: str = "all",
        language: str = "en"
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
            symbol = symbol,
            exchange = exchange,
            provider = provider,
            area = area,
            sort = sort,
            section = section,
            language = language
        )
        symbol = kwargs['symbol']
        exchange = kwargs['exchange']
        provider = kwargs['provider']
        area = kwargs['area']
        sort = kwargs['sort']
        section = kwargs['section']
        language = kwargs['language']

        section = "" if section == "all" else section

        area_code = "" if not area else self.areas[area]
        
        provider = "" if not provider else provider.replace('.', '_')
            
        url = f"https://news-headlines.tradingview.com/v2/view/headlines/symbol?client=web&lang={language}&area={area_code}&provider={provider}&section={section}&streaming=&symbol={exchange}:{symbol}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx and 5xx)
            
            response_json = response.json()
            items = response_json.get('items', [])
            
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


    def _export(self, data, symbol=None, provider=None, area=None):
        data_category = 'news_symbol' if symbol else 'news_provider' if provider else 'news_area'
        
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
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/languages.json')
        if not os.path.exists(path):
            print(f"[ERROR] Languages file not found at {path}.")
            return []
        try:
            with open(path, 'r', encoding="utf-8") as f:
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
            with open(path, 'r', encoding="utf-8") as f:
                exchanges = f.readlines()
            return [exchange.strip() for exchange in exchanges]
        except IOError as e:
            print(f"[ERROR] Error reading exchanges file: {e}")
            return []


    def _load_news_providers(self):
        """Load news providers from a specified file.

        Returns:
            list: A list of news providers loaded from the file.

        Raises:
            IOError: If there is an error reading the file.
        """
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/news_providers.txt')
        if not os.path.exists(path):
            print(f"[ERROR] News provider file not found at {path}.")
            return []
        try:
            with open(path, 'r', encoding="utf-8") as f:
                providers = f.readlines()
            return [provider.strip() for provider in providers]
        except IOError as e:
            print(f"[ERROR] Error reading providers file: {e}")
            return []

    
    def _load_areas(self) -> list:
        """Load areas from a specified file.

        Returns:
            list: A list of areas loaded from the file.

        Raises:
            IOError: If there is an error reading the file.
        """
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/areas.json')
        if not os.path.exists(path):
            print(f"[ERROR] Areas file not found at {path}.")
            return []
        try:
            with open(path, 'r', encoding="utf-8") as f:
                areas = json.load(f)
            return areas
        except IOError as e:
            print(f"[ERROR] Error reading areas file: {e}")
            return []
