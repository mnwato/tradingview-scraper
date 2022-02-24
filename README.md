# Tradingview scraper

The goal is to develop this package for scapping anything on https://tradingview.com with realtime response.
**I would thankful of any contributers**


## To Do List:
- [x] Scrape ideas section of a symbol
- [x] Export as `csv` file
- [ ] Export as `JSON`
- [ ] Scrape indicators status data             
  etc ... (You suggest)


## Features

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


## Installation
Open your favorite Terminal and run the command:
```sh
pip install tradingview-scraper
```


## Examples

```sh
from tradingview_scraper import scraper
ClassA.scraper()
```
### Output:
A tuple which includes:
1. A pandas dataframe (contains: timeStamp, symbol, timeFrame, label, title, socialInfo) 
2. A string (Symbol description in the first webpage)

### Note:
Default arguments are set to:
```sh
ClassA.scraper(symbol = 'btc',
            wholePage = False,
            startPage = 1,
            endPage = 2, 
            to_csv = False)
```
Argument  | Description
--------  | -----------
symbol | Symbol name
wholePage | Set it True if you want to scrape all pages
startPage | Set start page to scrape
endPage	| Set end page to scrape
to_csv | Set True to save data as a 'CSV' file

## License
- MIT
