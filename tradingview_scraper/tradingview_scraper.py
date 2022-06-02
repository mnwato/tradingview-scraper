## > Imports
# > Standard Library
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

            if content is None:
                raise Exception("No ideas found. Check the symbol or page number.")

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
                    str(
                        datetime.datetime.fromtimestamp(
                            float(time_upd["data-timestamp"])
                        )
                    )
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
    def __init__(self):

        # Read and save all indicators
        indicators = """"Recommend.Other","Recommend.All","Recommend.MA","RSI","RSI[1]","Stoch.K","Stoch.D","Stoch.K[1]","Stoch.D[1]","CCI20","CCI20[1]","ADX","ADX+DI","ADX-DI","ADX+DI[1]","ADX-DI[1]","AO","AO[1]","AO[2]","Mom","Mom[1]","MACD.macd","MACD.signal","Rec.Stoch.RSI","Stoch.RSI.K","Rec.WR","W.R","Rec.BBPower","BBPower","Rec.UO","UO","EMA10","close","SMA10","EMA20","SMA20","EMA30","SMA30","EMA50","SMA50","EMA100","SMA100","EMA200","SMA200","Rec.Ichimoku","Ichimoku.BLine","Rec.VWMA","VWMA","Rec.HullMA9","HullMA9","Pivot.M.Classic.S3","Pivot.M.Classic.S2","Pivot.M.Classic.S1","Pivot.M.Classic.Middle","Pivot.M.Classic.R1","Pivot.M.Classic.R2","Pivot.M.Classic.R3","Pivot.M.Fibonacci.S3","Pivot.M.Fibonacci.S2","Pivot.M.Fibonacci.S1","Pivot.M.Fibonacci.Middle","Pivot.M.Fibonacci.R1","Pivot.M.Fibonacci.R2","Pivot.M.Fibonacci.R3","Pivot.M.Camarilla.S3","Pivot.M.Camarilla.S2","Pivot.M.Camarilla.S1","Pivot.M.Camarilla.Middle","Pivot.M.Camarilla.R1","Pivot.M.Camarilla.R2","Pivot.M.Camarilla.R3","Pivot.M.Woodie.S3","Pivot.M.Woodie.S2","Pivot.M.Woodie.S1","Pivot.M.Woodie.Middle","Pivot.M.Woodie.R1","Pivot.M.Woodie.R2","Pivot.M.Woodie.R3","Pivot.M.Demark.S1","Pivot.M.Demark.Middle","Pivot.M.Demark.R1"""
        self.indicators = indicators.replace('"', "").split(",")

        exchanges = "BINANCE,BINANCEUS,BITCOKE,BITFINEX,BITSTAMP,BITTREX,BYBIT,CAPITALCOM,CEXIO,CURRENCYCOM,EASYMARKETS,EIGHTCAP,EXMO,FOREXCOM,FTX,FXCM,GEMINI,GLOBALPRIME,INDEX,KRAKEN,OANDA,OKCOIN,PEPPERSTONE,SAXO,SKILLING,TIMEX,TRADESTATION,VANTAGE"
        self.exchanges = exchanges.split(",")

    def scraper(
        self,
        exchange: str = "BITSTAMP",
        symbols: list = ["BTCUSD", "LTCUSDT"],
        indicators: list = ["RSI", "Stoch.K"],
        allIndicators: bool = False,
    ) -> dict:
        """
        Extract indicators from TradingView for the given symbol and exchange.

        Parameters
        ----------
        exchange : str
            The name of the exchange, by default "BITSTAMP".
            The supported exchanges can be found in the data/exchanges.txt file.
        symbols : list
            The list of symbols to scrape indicators for, by default ["BTCUSD"].
        indicators : list
            The list of indicators to scrape, by default ["RSI"].
            The supported indicators can be found in the data/indicators.txt file.
        allIndicators : bool, optional
            If this is set to True return all the indicators, by default False.

        Returns
        -------
        dict
            A dictionary containing the indicators for the given symbol and exchange.
            The format is {symbol: {indicator: value}}.
        """

        # Check if the exchange and indicators are supported
        assert (
            exchange in self.exchanges
        ), "This exchange is not supported! Please check the list of supported exchanges."

        if not allIndicators:
            for indicator in indicators:
                assert (
                    indicator in self.indicators
                ), "This indicator is not supported! Please check the list of supported indicators."

        # Format the symbols based on given exchange
        symbols = [f"{exchange}:{x}" for x in symbols]

        # If it is set to True use all the indicators
        if allIndicators == True:
            indicators = self.indicators

        payload = {
            "symbols": {"tickers": symbols},
            "columns": indicators,
        }

        res = requests.post("https://scanner.tradingview.com/crypto/scan", json=payload)

        # Save the response from tradingview in this dictionary
        inds = {}
        for elem in res.json()["data"]:
            # Save all indicator : value pairs in this dictionary
            indicator = {key: str(val) for key, val in zip(indicators, elem["d"])}

            # Add them to the list with the symbol as key
            inds[elem["s"].split(":")[-1]] = indicator

        return inds
