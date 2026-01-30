# Product Guidelines - TradingView Scraper

## Design Philosophy
* **Developer-Centric:** The API should be intuitive and well-documented, making it easy for quantitative traders to integrate data into their existing pipelines.
* **Consistency:** Method names, parameter structures, and return types should follow a predictable pattern across all scraper modules.
* **Performance:** Efficiency is paramount, especially for real-time streaming and large-scale data extraction.

## API Standards
* **Data Format:** All scrapers must return data as standard Python dictionaries or lists of dictionaries to ensure easy conversion to JSON or Pandas DataFrames.
* **Error Handling:** Use clear, descriptive exceptions. Avoid silent failures; if a scrape fails due to a network error or structural change on TradingView, the user should be informed immediately.
* **Configuration:** Support environment variables (via `python-dotenv`) for sensitive information like `TRADINGVIEW_COOKIE` and `websocket_jwt_token`.

## Quality & Reliability
* **Maintenance:** Regularly update scrapers to handle structural changes on TradingView.com.
* **Testing:** Maintain high test coverage for core scraping logic and WebSocket communication to ensure data accuracy.
* **Modularity:** Keep scraper logic modular and separated from export/utility logic to facilitate easier debugging and enhancement.
