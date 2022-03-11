# Tradingview scraper

The goal is to develop this package for scapping anything on https://tradingview.com with realtime response.  
**Thanks to contributors**


## To Do List:
- [x] Scrape ideas section of a symbol
- [x] Export as `csv` file
- [x] Export as `JSON`
- [x] Scrape indicators status data
- [ ] Review and fix bugs   
  etc ... (You suggest)

### To be aware of last changes go to the [end of this page](https://github.com/mnwato/tradingview-scraper/edit/dev/README.md#changes)

## Features:

- Scrape idea's informations like:
  > #### Idea's Title
  > #### Idea's symbol
  > #### Idea's timeframe
  > #### Idea's timestamp
  > #### Idea's label
  > #### Idea's social informations
  > #### Idea's description
- Three ways to scrape webpage:
  > #### Scrape just first page
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
obj = Ideas().scraper(symbol = 'btc',
                      wholePage = False,
                      startPage = 1,
                      endPage = 2, 
                      to_csv = False,
                      return_json=False)
print(obj)
```
#### Output:
```
- A tuple which contain:
  1. A pandas dataframe (contains: timeStamp, symbol, timeFrame, label, title, socialInfo) 
  2. A string (Symbol description in the first webpage)
- A Json which contain keys like bellow:   
  `dict_keys(['symbol_description', '0', '1', '2', '3', '4', '5'])`   
  which each of '0' to '5' keys containing ideas details like 'timestamp','symbol','timefram', etc.
 ```
#### 2. Getting indicators status:
```sh
from tradingview_scraper import Indicators
obj = Indicators().scraper(exchange="BITSTAMP",
                          symbols=["BTCUSD","LTCUSD"],
                          indicators=["RSI","Stoch.K"],
                          allIndicators=False)
print(obj)
```
#### Output:
```
{'BTCUSD': {'RSI': '46.34926112', 'Stoch.K': '40.40173723'}, 'LTCUSD': {'RSI': '43.38421064', 'Stoch.K': '42.32662465'}}
```
  
## Note:
### Default arguments are set to:
```sh
Ideas.scraper(symbol = 'btc',
              wholePage = False,
              startPage = 1,
              endPage = 2, 
              to_csv = False,
              return_json = False)
```
Argument  | Description
--------  | -----------
symbol | Symbol name
wholePage | Set it True if you want to scrape all pages<br> (Then specify startPage and endPage)
startPage | specify first page number to scrape
endPage	| specify last page number to scrape
to_csv | Set it True to save data as a 'CSV' file
return_json | Set it True to have json format in return

```
Indicators().scraper(exchange="BITSTAMP",
                    symbols=["BTCUSD"],
                    indicators=["RSI"],
                    allIndicators=False)
```
Argument  | Description
--------  | -----------
exchange | Exchange name<br /> also you can use [another exchanges](https://github.com/mnwato/tradingview-scraper/blob/dev/tradingview_scraper/exchanges.txt)
symbols | A list of symbols
indicators | A list of indicators
allIndicators | Set it True if you need [all of indicators](https://github.com/mnwato/tradingview-scraper/blob/dev/tradingview_scraper/indicators.txt)


## Changes:
 - Release `0.1.0` :  
   The name of `ClassA` changed to `Ideas`
    
## License
- MIT
