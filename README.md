# TradingView Scraper
[![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![MIT License](https://img.shields.io/github/license/mnwato/tradingview-scraper.svg?color=brightgreen)](https://opensource.org/licenses/MIT)


This is a Python library for scraping ideas and indicators from [TradingView.com](https://www.tradingview.com). The goal is to develop this package to scrape anything on [TradingView.com](https://www.tradingview.com) with real-time responses.  
**Thanks to contributors!**

## To-Do List

### Completed Tasks
- [x] Export as a `CSV` file
- [x] Export as `JSON`

### Pending Tasks
- [ ] Scrape Symbol Subpages:
  - [x] [Ideas](https://www.tradingview.com/symbols/BTCUSD/ideas/)
  - [x] [Indicators](https://www.tradingview.com/symbols/BTCUSD/technicals/)
  - [ ] [Overview](https://www.tradingview.com/symbols/BTCUSD/)
  - [ ] [News](https://www.tradingview.com/symbols/BTCUSD/news/)
  - [ ] [Minds](https://www.tradingview.com/symbols/BTCUSD/minds/)
  - [ ] [Technical](https://www.tradingview.com/symbols/BTCUSD/technicals/)
  - [ ] [Market](https://www.tradingview.com/symbols/BTCUSD/markets/)
  - [ ] Get data using TradingView WebSocket
  - [ ] Additional suggestions welcome!

### To be aware of the latest changes, go to the [end of this page](https://github.com/mnwato/tradingview-scraper#changes).

## Features

- **Idea Information Scraping**
  - Title
  - Paragraph
  - Preview Image
  - Author
  - Comments Count
  - Boosts Count
  - Publication Datetime
  - Is Updated
  - Idea Strategy

- **Webpage Scraping Options**
  - Scrape All Pages
  - Scrape a Specific Range of Pages

- **Indicator Extraction**
  - Extract values for indicators like `RSI`, `Stoch.K`, etc. 
  - [Full list of indicators](https://github.com/mnwato/tradingview-scraper/blob/dev/tradingview_scraper/indicators.txt)

- **Export Formats**
  - CSV
  - JSON

- **Output Format**
  - Returns data in JSON format

Here’s a revised version of the Installation section that enhances clarity and encourages user engagement:


## Installation

To get started with the TradingView Scraper library, follow these simple steps:

1. **Open your terminal**: Launch your preferred command line interface.

2. **Install the package**: Run the following command to install the TradingView Scraper:
   ```sh
   pip install tradingview-scraper
   ```

3. **Upgrade if necessary**: If you already have the library installed and want to upgrade to the latest version, use:
   ```sh
   pip install --upgrade tradingview-scraper
   ```

Here’s a revised version of the Examples section, focusing on clarity, ease of understanding, and providing essential information about default values:


## Examples

### 1. Fast Running (Default Parameters)
To quickly scrape ideas using default settings, use the following code:
```python
from symbols.ideas import Ideas

# Initialize the Ideas scraper with default parameters
ideas_scraper = Ideas()  # Default: export_result=False, export_type='json'
ideas = ideas_scraper.scrape()  # Default symbol: 'BTCUSD'
print("Ideas:", ideas)
```
**Default Parameters:**
- `export_result`: `False` (no file will be saved)
- `export_type`: `'json'` (output format)

### 2. Getting Ideas for a Specific Symbol, Export Type, and Pages
To scrape ideas for a specific symbol and export them as a CSV file, you can specify the parameters:
```python
from symbols.ideas import Ideas

# Initialize the Ideas scraper with custom parameters
ideas_scraper = Ideas(
  export_result=True,  # Set to True to save the results
  export_type='csv'    # Specify the export type (json or csv)
)

# Scrape ideas for the ETHUSD symbol, from page 1 to page 2
ideas = ideas_scraper.scrape(
  symbol="ETHUSD",
  startPage=1,
  endPage=2
)
print("Ideas:", ideas)
```

**Output Format:**
The output will always be a list of Python dictionaries, structured as follows:
```json
[
  {
      "title": "Bitcoin -65% crash, ETH -83%, DOGE -89%, SHIBA -90%",
      "paragraph": "Name your altcoin in the comment section, and I will do a technical analysis for you!\n\nThe crypto market looks ...",
      "preview_image": "https://s3.tradingview.com/6/6VQphWH6_mid.png",
      "author": "Xanrox",
      "comments_count": "295",
      "boosts_count": "678",
      "publication_datetime": "2024-08-18T05:55:19.000Z",
      "is_updated": "True",
      "idea_strategy": "Short"
  }
]
```
- When `export_result=True`, the default `export_type` is `'json'`, and a JSON file will be saved in the `/export` directory. To save as CSV, set `export_type='csv'`.

### 3. Getting Indicators Status
To scrape the status of specific indicators, use the following code:
```python
from symbols.indicators import Indicators

# Initialize the Indicators scraper with export options
indicators_scraper = Indicators(export_result=True, export_type='json')

# Scrape indicators for the BTCUSD symbol from the BINANCE exchange
indicators = indicators_scraper.scrape(
    exchange="BINANCE",
    symbol="BTCUSD",
    indicators=["RSI", "Stoch.K"]
)
print("Indicators:", indicators)
```

**Output:**
```json
{'RSI': '46.34926112', 'Stoch.K': '40.40173723'}
```

### 4. Getting All Indicators
If you want to retrieve all available indicators for a symbol, set `allIndicators=True`:
```python
# Scrape all indicators for the BTCUSD symbol
indicators_scraper = Indicators(export_result=True, export_type='json')
indicators = indicators_scraper.scrape(
    symbol="BTCUSD",
    allIndicators=True
)
print("All Indicators:", indicators)
```

Feel free to further customize any part to better fit your documentation style!
## Changes:
- Release `0.2.9`:   
  Refactor for new TradingView structure
- Release `0.1.0`:  
  The name of `ClassA` changed to `Ideas`

## License:
```
[MIT]
```