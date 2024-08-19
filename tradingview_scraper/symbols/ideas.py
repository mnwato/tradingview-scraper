
import requests
from time import sleep

from bs4 import BeautifulSoup


from tradingview_scraper import Symbols
from symbols.utils import save_csv_file, save_json_file

class Ideas(Symbols):
    def scrape(
        self,
        symbol: str,
        startPage: int = 1,
        endPage: int  = 1,
    ):
        """
        Extract trading ideas from TradingView for a specified symbol over a range of pages.

        This method scrapes trading ideas related to a particular symbol from TradingView. 
        It allows users to specify the range of pages to scrape, enabling the collection 
        of multiple ideas at once.

        Parameters
        ----------
        symbol : str
            The symbol (e.g., 'BTC') or type of trading idea (e.g., 'stocks' or 'crypto').
            If this is None, the front page will be used (tradingview.com/ideas).
        startPage : int, optional
            The page where the scraper should start, by default 1.
        endPage : int, optional
            The page where the scraper should end, by default 1.
            If this is left the same as startPage, the scraper will only scrape one page.

        Returns
        -------
        list
            A list of dictionaries containing the scraped trading ideas. Each dictionary 
            includes details such as title, paragraph, author, and publication date.

        Raises
        ------
        Exception
            If no ideas are found for the specified symbol or page number.

        Notes
        -----
        The method includes a delay of 5 seconds between requests to avoid overwhelming 
        the server with rapid requests.
        """

        pageList = range(startPage, endPage + 1)

        articles = []
        
        for page in pageList:

            # If no symbol is provided check the front page
            if symbol:
                symbol_payload = f"/{symbol}/"
            else:
                symbol_payload = "/"

            # Fetch the page as plain HTML text
            response = requests.get(
                f"https://www.tradingview.com/symbols{symbol_payload}ideas/page-{page}/"
            ).text

            # Use BeautifulSoup to parse the HTML
            soup = BeautifulSoup(response, "html.parser")

            # Each div contains a single idea
            content = soup.find(
                "div",
                class_="listContainer-rqOoE_3Q",
            )

            if content is None:
                raise Exception("No ideas found. Check the symbol or page number.")

            articles_tag = content.find_all("article")
            
            if articles_tag is None:
                raise Exception("No ideas found. Check the symbol or page number.")

            for tag in articles_tag:
                
                article_json = self.parse_article(tag)
                
                if article_json is not None:
                    articles.append(article_json)

            print(f"[INFO] Page {page} scraped successfully")

            # Wait 5 seconds before going to the next page
            if len(pageList) > 1:
                sleep(5)

        if self.export_type:
            self.export(articles)

        return articles


    def export(self, data):
        if self.export_type == 'json':
            save_json_file(data=data, symbol=self.symbol)
        
        elif self.export_type == 'csv':
            save_csv_file(data=data, symbol=self.symbol)
            

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
            article_json["boosts_count"] = boosts_count_tag.get('aria-label').split()[0]

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