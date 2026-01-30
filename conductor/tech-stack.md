# Tech Stack - TradingView Scraper

## Core Language
* **Python (>= 3.8):** The primary programming language for the library.

## Scraping & HTTP
* **requests:** For making synchronous HTTP requests to TradingView.
* **aiohttp:** For high-performance asynchronous HTTP requests in the quantitative pipeline.
* **beautifulsoup4:** For parsing and extracting data from HTML responses.

## Data Processing & Validation
* **pandas:** Used for data manipulation and as an export format for structured data.
* **scipy (stats/optimize):** Utilized for higher-order moment calculations (skewness, kurtosis) and constrained convex optimization.
* **pywt (PyWavelets):** Employed for Discrete Wavelet Transform (DWT) spectral analysis in regime detection and predictability filtering.
* **pydantic:** Employed for data validation and settings management.
* **optuna:** Framework used for automated hyperparameter optimization of the selection engine and risk parameters.
* **scikit-learn:** Provides robust estimators like Ledoit-Wolf shrinkage for covariance and risk management.
* **Market Cap Metadata:** External `market_caps_crypto.json` provides global asset ranking for hybrid guards.

## Real-time & WebSockets
* **aiohttp:** Primary library for asynchronous WebSocket streaming (`AsyncStreamHandler`).
* **websockets & websocket-client:** Legacy foundations for real-time data streaming.
* **cvxportfolio:** Core library for high-fidelity backtest simulation and friction modeling.

## Configuration & Tooling
* **python-dotenv:** For managing environment variables and secrets.
* **setuptools:** Used for packaging and distribution.
* **tenacity:** For robust retry logic across synchronous and asynchronous API requests.
* **uv:** Employed for fast, reproducible dependency management and locking.

## Quality Assurance
* **pytest:** The testing framework for the project.
* **ruff:** A fast Python linter and formatter, configured via `pyproject.toml`.
