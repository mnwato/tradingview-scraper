"""Module providing a function to scrape published user ideas about a symbol."""

from time import sleep

import requests
from bs4 import BeautifulSoup

from tradingview_scraper.symbols.utils import save_csv_file, save_json_file, generate_user_agent

class Ideas:
    def __init__(self, export_result=False, export_type='json'):
        self.export_result = export_result
        self.export_type = export_type
        self.headers = {"user-agent": generate_user_agent()}
        
    def scrape(
        self,
        symbol: str = "BTCUSD",
        startPage: int = 1,
        endPage: int  = 1,
        sort: str = "popular"
    ):
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
            includes details such as title, paragraph, author, and publication date.

        Raises
        ------
        Exception
            If no ideas are found for the specified symbol or page number, or if the sort argument is invalid.

        Notes
        -----
        The method includes a delay of 5 seconds between requests to avoid overwhelming
        the server with rapid requests.
        """
        
        pageList = range(startPage, endPage + 1)

        articles = []
        
        for page in pageList:

            if sort == "popular":
                articles.extend(self.scrape_popular_ideas(symbol, page))
            elif sort == "recent":
                articles.extend(self.scrape_recent_ideas(symbol, page))
            else:
                print("[ERROR] sort argument must be one 'popular' or 'recent'")
            
            print(f"[INFO] Page {page} scraped successfully")

            # Wait 5 seconds before going to the next page
            if len(pageList) > 1 and page<len(pageList):
                sleep(5)

        # Save results
        if self.export_result == True:
            self._export(data=articles, symbol=symbol)
            
        return articles


    def _export(self, data, symbol):
        if self.export_type == "json":
            save_json_file(data=data, symbol=symbol, data_category='ideas')
            
        elif self.export_type == "csv":
            save_csv_file(data=data, symbol=symbol, data_category='ideas')


    def parse_article(self, article_tag):
        
        article_json = {
            "title": None,
            "paragraph": None,
            "preview_image": None,
            "author": None,
            "comments_count": None,
            "boosts_count": None,
            "publication_datetime": None,
            "is_updated": False,
            "idea_strategy": None,
        }

        # Extract title
        article_json["title"] = article_tag.find('a', class_=lambda x: x and x.startswith('title-')).text

        # Extract paragraph
        article_json["paragraph"] = article_tag.find('a', class_=lambda x: x and x.startswith('paragraph-')).text

        # Extract picture and preview image
        picture_tag = article_tag.find('picture')
        article_json["preview_image"] = picture_tag.find('img')['src'] if picture_tag else None

        # Extract author
        article_json["author"] = article_tag.find('span', class_=lambda x: x and x.startswith('card-author-')).text.replace("by", "").strip()

        # Extract comments count
        comments_count_tag = article_tag.find('span', class_=lambda x: x and x.startswith('ellipsisContainer'))
        if comments_count_tag:
            article_json["comments_count"] = comments_count_tag.text.strip()

        # Extract boosts count
        boosts_count_tag = article_tag.find('button', class_=lambda x: x and x.startswith('boostButton-'))
        if boosts_count_tag:
            aria_label = boosts_count_tag.get('aria-label')
            if aria_label:
                article_json["boosts_count"] = aria_label.split()[0]
            else:
                article_json["boosts_count"] = 0
        else:
            article_json["boosts_count"] = 0

        # Extract publication info
        publication_text = article_tag.find('time', class_=lambda x: x and x.startswith('publication-date-')).text.strip()
        if publication_text:
            article_json["is_updated"] = True
        publication_datetime_tag = article_tag.find('time', class_=lambda x: x and x.startswith('publication-date-'))
        if publication_datetime_tag:
            publication_datetime = publication_datetime_tag.get('datetime','')
            article_json["publication_datetime"] = publication_datetime

        # Extract idea strategy (short or long)
        ideas_strategy_tag = article_tag.find('span', class_=lambda x: x and x.startswith('idea-strategy-icon-'))
        if ideas_strategy_tag:
            article_json["idea_strategy"] = ideas_strategy_tag.get('title', '').strip()

        return article_json
        
    def scrape_popular_ideas(self, symbol, page):
        """
        Scrapes popular trading ideas for a specified symbol from TradingView.

        Parameters
        ----------
        symbol : str
            The trading symbol for which to scrape ideas.
        page : int
            The page number to scrape.

        Returns
        -------
        list
            A list of dictionaries containing the scraped popular ideas.

        Raises
        ------
        Exception
            If no ideas are found for the specified symbol or page number.
        """
        # If no symbol is provided check the front page
        if symbol:
            symbol_payload = f"/{symbol}/"
        else:
            symbol_payload = "/"

        # Fetch the page as plain HTML text
        response = requests.get(
            f"https://www.tradingview.com/symbols{symbol_payload}ideas/page-{page}/?component-data-only=1&sort=recent",
            headers=self.headers,
            timeout=5
        ).text

        # Use BeautifulSoup to parse the HTML
        soup = BeautifulSoup(response, "html.parser")

        # Each div contains a single idea
        content = soup.find(
            "div",
            class_="listContainer-rqOoE_3Q",
        )

        if content is None:
            raise ValueError("No ideas found. Check the symbol or page number.")

        articles_tag = content.find_all("article")
        if not articles_tag:
            raise ValueError("No ideas found. Check the symbol or page number.")

        return [self.parse_article(tag) for tag in articles_tag]


    def scrape_recent_ideas(self, symbol, page):
        """
        Scrapes recent trading ideas for a specified symbol from TradingView.

        Parameters
        ----------
        symbol : str
            The trading symbol for which to scrape ideas.
        page : int
            The page number to scrape.

        Returns
        -------
        list
            A list of dictionaries containing the scraped recent ideas.

        Raises
        ------
        Exception
            If the symbol is None when trying to scrape recent ideas.
        """
        if symbol:
            symbol_payload = f"/{symbol}/"
        else:
            raise ValueError("symbol could not be null when getting recent ideas")
            
        if page == 1:
            url = f"https://www.tradingview.com/symbols{symbol_payload}ideas/?component-data-only=1&sort=recent"
        else:
            url = f"https://www.tradingview.com/symbols{symbol_payload}ideas/page-{page}/?sort=recent&component-data-only=1&sort=recent"

        response = requests.get(url, headers=self.headers, timeout=5)
        if response.status_code != 200:
            return []

        response_json = response.json()
        items = response_json.get("data", {}).get("ideas", {}).get("data", {}).get("items", [])
        
        return [item for item in items if item.pop("symbol", None) is not None]
