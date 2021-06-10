# Tradingview scraper

The goal is to develop this package for scapping anything on https://tradingview.com with realtime response.
**I would thankful of any contributers**

## Features

- Scrape idea's informations like:
-- Idea's Title
-- Idea's symbol
-- Idea's timeframe
-- Idea's timestamp
-- Idea's label
-- Idea's social informations
-- Idea's description
- Three ways to scrape webpage:
-- Scrape just first page
-- Scrape all pages
-- Scrape specific range of pages
- Save data into a CSV file

## Installation
Open your favorite Terminal and run the command:
```sh
pip install tradingview_scrape_mnajmi
```


## Examples

```sh
from tradingview_scraper_mnajmi import main
main.scraper()
```

### Note:
Default arguments are set to:
```sh
main.scraper(symbol = 'btc',
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