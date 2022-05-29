## > Imports
# > Standard Library
import os
import requests
import datetime
from time import sleep

# > Third Party Libaries
import json
import pandas as pd
from bs4 import BeautifulSoup


class Ideas:
    def scraper(
        self,
        symbol: str = None,
        startPage: int = 1,
        endPage: int = 2,
        to_csv: bool = False,
        return_json: bool = False,
    ):
        """
        Extract the any page of trading ideas on TradingView.

        Parameters
        ----------
        symbol : str, optional
            The symbol (e.g. 'BTC') or type of trading idea (e.g. 'stocks' or 'crypto').
            If this is None the front page will be used (tradingview.com/ideas), by default None.
        startPage : int
            The page where the scraper should start, by default 1.
        endPage : int
            The page where the scraper should end, by default 2.
            If this is left to the same as startPage, the scraper will only scrape one page.
        to_csv : bool
            If set to True a .csv file will be generated containing all scraped ideas.
            If set to False (default), a tuple containing the symbol's description and ideas DataFrame is returned.
        return_json : bool
            If set to True the json file containing the scraped ideas will be returned.
            If set to False (default), a tuple containing the symbol's description and ideas DataFrame is returned.

        Returns
        -------
        tuple(str, DataFrame) or dict
            By default a tuple containing the symbol's description and ideas DataFrame is returned.
            If return_json is set to True, a dict containing the scraped ideas will be returned.
        """

        pageList = range(startPage, endPage + 1)

        # The information will be saved in these lists
        titleList = []
        descriptionList = []
        labelList = []
        timeFrameList = []
        symbolList = []
        timestampList = []
        commentsList = []
        imageUrlList = []
        likesList = []
        urlList = []

        for page in pageList:

            # If no symbol is provided check the front page
            if symbol:
                symbol_payload = f"/{symbol}/"
            else:
                symbol_payload = "/"

            # Fetch the page as plain HTML text
            response = requests.get(
                f"https://www.tradingview.com/ideas{symbol_payload}page-{page}/"
            ).text

            # Use BeautifulSoup to parse the HTML
            soup = BeautifulSoup(response, "html.parser")

            # Each div contains a single idea
            content = soup.find(
                "div",
                class_="tv-card-container__ideas tv-card-container__ideas--with-padding js-balance-content",
            )

            # Get the description of this symbol (if there is any)
            if page == pageList[0]:
                description = None
                if symbol:
                    description = content.find(
                        "div", class_="tv-widget-description__text"
                    )
                    if description != None:
                        description = description.get_text().strip()

            # Get the description of this idea
            for description_row in content.find_all(
                "p",
                class_="tv-widget-idea__description-row tv-widget-idea__description-row--clamped js-widget-idea__popup",
            ):
                descriptionList.append(description_row.get_text())

            # Social items info, such as comments likes and the url
            for social_row in content.find_all(
                "div", class_="tv-social-row tv-widget-idea__social-row"
            ):
                social_info = json.loads(social_row["data-model"])

                # Get the information in social_info dict
                commentsList.append(social_info["commentsCount"])
                likesList.append(social_info["agreesCount"])
                urlList.append(
                    f"https://www.tradingview.com{social_info['publishedUrl']}"
                )

            # Get the image url
            for img_row in content.find_all("div", class_="tv-widget-idea__cover-wrap"):
                imageUrlList.append(img_row.find("img")["data-src"])

            # Get the title of the idea
            for title_row in content.find_all(
                "div", class_="tv-widget-idea__title-row"
            ):
                titleList.append(title_row.a.get_text())

            # Get the Labels, timeFrame and Symbol
            for info_row in content.find_all("div", class_="tv-widget-idea__info-row"):

                if "type-long" in str(info_row):
                    label = "Long"
                elif "type-short" in str(info_row):
                    label = "Short"
                else:
                    label = "Neutral"

                labelList.append(label)

                symbol_info = info_row.find("div", class_="tv-widget-idea__symbol-info")

                # Add it to the list if there is any
                if symbol_info:
                    symbolList.append(symbol_info.a.text)
                else:
                    symbolList.append(None)

                timeFrameList.append(
                    info_row.find_all("span", class_="tv-widget-idea__timeframe")[
                        1
                    ].text
                )

            # Save the Timestamps
            for time_upd in content.find_all(
                "span", class_="tv-card-stats__time js-time-upd"
            ):
                timestampList.append(
                    str(datetime.datetime.fromtimestamp(float(time_upd["data-timestamp"])))
                )

            # Wait 5 seconds before going to the next page
            if len(pageList) > 1:
                sleep(5)

        if return_json == True:
            data = {"symbol_description": description}

            # Iterate through the lists and add them to the data dict
            for elem in range(len(timestampList)):
                data.update(
                    {
                        str(elem): {
                            "Timestamp": timestampList[elem],
                            "Title": titleList[elem],
                            "Description": descriptionList[elem],
                            "Symbol": symbolList[elem],
                            "Timeframe": timeFrameList[elem],
                            "Label": labelList[elem],
                            "Url": urlList[elem],
                            "ImageURL": imageUrlList[elem],
                            "Likes": likesList[elem],
                            "Comments": commentsList[elem],
                        }
                    }
                )

            if to_csv == True:
                data_copy = data.copy()
                data_copy.pop("symbol_description")
                df = pd.read_json(json.dumps(data_copy), orient="index")
                df.to_csv(f"tradingview_{symbol}.csv", index=False)
            return data

        else:
            data = {
                "Timestamp": timestampList,
                "Title": titleList,
                "Description": descriptionList,
                "Symbol": symbolList,
                "Timeframe": timeFrameList,
                "Label": labelList,
                "Url": urlList,
                "ImageURL": imageUrlList,
                "Likes": likesList,
                "Comments": commentsList,
            }

            # Convert the data to a dataframe
            df = pd.DataFrame(data)

            if to_csv == True:
                df.to_csv(f"tradingview_{symbol}.csv", index=False)

            return description, df


class Indicators:
    def __init__(self) -> None:
        self.indicators_url = "https://scanner.tradingview.com/crypto/scan"

    def scraper(
        self,
        exchange="BITSTAMP",
        symbols=["BTCUSD"],
        indicators=["RSI"],
        allIndicators=False,
    ):
        """
        ## Extract symbol indicators
        ## Args:\n
                1- exchange(String):\n
                Exchange name like (Default: `BITSTAMP`),`BINANCE`,`BINANCEUS`,`BITCOKE`,`BITFINEX`,\n
                `BITTREX`,`BYBIT`,`CEXIO`,`EXMO`,`FTX`,`GEMINI`,`KRAKEN`,`OKCOIN`,`TIMEX`,\n
                `TRADESTATION`

                2- symbols(List of strings):\n
                        List of symbols (Default: `BTCUSD`)\n
                3- indicators(List of string):\n
                        List of indicators (Default: `RSI`) [Others](https://github.com/mnwato/tradingview-scraper/tree/main/tradingview_scraper/indicatos.txt)\n
                4- allIndicators(Boolean):\n
                        True > Extract all indicators Whether the indicators are specified or not\n
                        False > Extract only indicators which are apecified in indicators arguments
        ## Return(JSON):\n
                List of indicators for specified symbols
        """
        symbols = [f"{exchange}:" + x for x in symbols]
        if allIndicators == True:
            with open(
                os.path.join(os.getcwd(), "tradingview_scraper", "indicators.txt"), "r"
            ) as f:
                indicators = f.read().replace('"', "").split(",")

        payload = {
            "symbols": {"tickers": symbols, "query": {"types": []}},
            "columns": indicators,
        }
        headers = {
            "authority": "scanner.tradingview.com",
            "method": "POST",
            "path": "/crypto/scan",
            "scheme": "https",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "content-length": "1269",
            "content-type": "application/x-www-form-urlencoded",
            "cookie": "_ga=GA1.2.170692871.1636066864; __gads=ID=eafb0f94683db984:T=1636066978:S=ALNI_MZ-0TZNoN6EUwbt302scWBNrnE-rA; sessionid=n27htwjuhx5678st2mpj5oe66y49lioh; tv_ecuid=f9bf1dfb-91fe-4e97-ada2-7cdcbc502c2e; _sp_ses.cf1a=*; _gid=GA1.2.734511956.1646977393; _gat_gtag_UA_24278967_1=1; _sp_id.cf1a=07117aec-f7ee-4bd8-af59-f80ae57f124d.1643982464.4.1646977457.1645721190.42cd0b0d-4b87-4c86-9350-8d5fea7a8f66",
            "origin": "https://www.tradingview.com",
            "referer": "https://www.tradingview.com/",
            "sec-ch-ua": """Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99""",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Windows",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
        }
        res = requests.post(self.indicators_url, headers=headers, json=payload)
        inds = {}
        for elem in res.json()["data"]:
            temp = []
            temp = {key: str(val) for key, val in zip(indicators, elem["d"])}
            inds.update({elem["s"].split(":")[-1]: temp})
        return inds
