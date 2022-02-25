# Tradingview scraper

The goal is to develop this package for scapping anything on https://tradingview.com with realtime response.  
**Thanks to contributors**


## To Do List:
- [x] Scrape ideas section of a symbol
- [x] Export as `csv` file
- [x] Export as `JSON`
- [ ] Scrape indicators status data
- [ ] Review and fix bugs
  etc ... (You suggest)


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
- Save data into a CSV file
- Return json format


## Installation:
Open your favorite Terminal and run the command:
```sh
pip install tradingview-scraper
```


## Example:

```sh
from tradingview_scraper import scraper
ClassA.scraper()
```
### Output format:
- A tuple which contain:
  1. A pandas dataframe (contains: timeStamp, symbol, timeFrame, label, title, socialInfo) 
  2. A string (Symbol description in the first webpage)
- A Json which contain keys like bellow:   
  `dict_keys(['symbol_description', '0', '1', '2', '3', '4', '5'])`   
  which each of '0' to '5' keys containing ideas details like 'timestamp','symbol','timefram', etc.
  
### Note:
Default arguments are set to:
```sh
ClassA.scraper(symbol = 'btc',
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

## License
- MIT
