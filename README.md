# Tradingview scraper
[![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![MIT License](https://img.shields.io/github/license/mnwato/tradingview-scraper.svg?color=brightgreen)](https://opensource.org/licenses/MIT)

---

This is a Python library for scraping ideas and indicators of [TradingView.com](https://www.tradingview.com).
The goal is to develop this package for scraping anything on [TradingView.com](https://www.tradingview.com) with realtime response.  
**Thanks to contributors**

## To Do List:
- [x] Scrape ideas section of a symbol
- [x] Export as `csv` file
- [x] Export as `JSON`
- [x] Scrape indicators status data
- [ ] Review and fix bugs   
  etc ... (You suggest)

### To be aware of last changes go to the [end of this page](https://github.com/mnwato/tradingview-scraper#changes)

## Features:

- Scrape idea's informations like:
  > #### Idea's Title
  > #### Idea's description
  > #### Idea's symbol
  > #### Idea's timeframe
  > #### Idea's timestamp
  > #### Idea's label
  > #### Idea's social informations

- Three ways to scrape webpage:
  > #### Scrape the front page
  > #### Scrape all pages
  > #### Scrape specific range of pages
- Extract indicators status like of symbols:
  > `RSI` `Stoch.K` , etc [full list of indicators](https://github.com/mnwato/tradingview-scraper/blob/dev/tradingview_scraper/indicators.txt)
- Save data into a CSV file
- Return json format


## Installation:
Open your favorite Terminal and run the command:
```sh
pip install tradingview-scraper
```


## Examples:
#### 1. Getting ideas:
```sh
from tradingview_scraper import Ideas
obj = Ideas().scraper(symbol: str = None,
                      startPage: int = 1,
                      endPage: int = 2,
                      to_csv: bool = False,
                      return_json: bool = False)
print(obj)
```
Setting symbol to None will scrape the [ideas front page on TradingView](https://www.tradingview.com/ideas).

#### Output:
```
- By default a tuple object containing the following columns is returned:
  1. A pandas dataframe (contains: Timestamp, Title, Description, Symbol, Timeframe, Label, Url, ImageURL, Likes, Comments) 
  2. A string (Symbol description in the first webpage)
- If 'return_json' is set to True, a dictionary will be returned containing the keys below:   
  `dict_keys(['symbol_description', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])`   
  Where each of '0' to '9' keys contain an idea's details like 'Timestamp','Title','Description', etc.
 ```
#### 2. Getting indicators status:
```sh
from tradingview_scraper import Indicators
obj = Indicators().scraper(exchange: str = "BITSTAMP",
                           symbols: list = ["BTCUSD", "LTCUSDT"],
                           indicators: list = ["RSI", "Stoch.K"],
                           allIndicators: bool = False)
print(obj)
```
#### Output:
```
{'BTCUSD': {'RSI': '46.34926112', 'Stoch.K': '40.40173723'}, 'LTCUSD': {'RSI': '43.38421064', 'Stoch.K': '42.32662465'}}
```
  
## Note:
### Default arguments are set to:
```sh
Ideas.scraper(symbol: str = None,
              startPage: int = 1,
              endPage: int = 2,
              to_csv: bool = False,
              return_json: bool = False)
```
Argument  | Description
--------  | -----------
symbol | Symbol name
startPage | specify first page number to scrape
endPage	| specify last page number to scrape
to_csv | Set it True to save data as a 'CSV' file
return_json | Set it True to have json format in return

```
Indicators().scraper(exchange: str = "BITSTAMP",
                     symbols: list = ["BTCUSD", "LTCUSDT"],
                     indicators: list = ["RSI", "Stoch.K"],
                     allIndicators: bool = False)
```
Argument  | Description
--------  | -----------
exchange | Exchange name<br /> also you can use [another exchanges](https://github.com/mnwato/tradingview-scraper/blob/dev/tradingview_scraper/data/exchanges.txt)
symbols | A list of symbols
indicators | A list of indicators
allIndicators | Set it True if you need [all of indicators](https://github.com/mnwato/tradingview-scraper/blob/dev/tradingview_scraper/data/indicators.txt)


## Changes:
 - Release `0.1.0` :  
   The name of `ClassA` changed to `Ideas`
    
## License
- MIT
