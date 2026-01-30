#!/bin/bash
set -e

echo "Starting Global Universe Trend Scans..."

# Check if PROFILE is set, and use it if manifest discovery is preferred.
# Usage: PROFILE=production bash scripts/run_local_scans.sh
PROFILE_ARG=""
if [ -n "$PROFILE" ]; then
  PROFILE_ARG="--profile $PROFILE"
fi

# 1. Futures (Commodities)
echo "----------------------------------------"
echo "1. Futures Trend Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type futures_long \
  --config configs/futures_trend_momentum.yaml \
  --export json

echo "1b. Futures Trend Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type futures_short \
  --config configs/futures_trend_momentum_short.yaml \
  --export json

echo "1e. Futures Mean Reversion Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type futures_mr_long \
  --config configs/futures_mean_reversion.yaml \
  --export json

echo "1f. Futures Mean Reversion Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type futures_mr_short \
  --config configs/futures_mean_reversion_short.yaml \
  --export json

# 2. Futures (Metals specific)
echo "----------------------------------------"
echo "2. Futures Metals Trend Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type futures_metals_long \
  --config configs/futures_metals_trend_momentum.yaml \
  --export json

echo "2b. Futures Metals Trend Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type futures_metals_short \
  --config configs/futures_metals_trend_momentum_short.yaml \
  --export json

# 3. CFD
echo "----------------------------------------"
echo "3. CFD Trend Scan (Long)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  $PROFILE_ARG --scanner-type cfd_long \
  --config configs/cfd_trend_momentum.yaml \
  --export json

echo "3b. CFD Trend Scan (Short)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  $PROFILE_ARG --scanner-type cfd_short \
  --config configs/cfd_trend_momentum_short.yaml \
  --export json

# 4. Forex
echo "----------------------------------------"
echo "4. Forex Trend Scan (Long)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  $PROFILE_ARG --scanner-type forex_long \
  --config configs/forex_trend_momentum.yaml \
  --export json

echo "4b. Forex Trend Scan (Short)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  $PROFILE_ARG --scanner-type forex_short \
  --config configs/forex_trend_momentum_short.yaml \
  --export json

echo "4c. Forex Mean Reversion Scan (Long)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  $PROFILE_ARG --scanner-type forex_mr_long \
  --config configs/forex_mean_reversion.yaml \
  --export json

echo "4d. Forex Mean Reversion Scan (Short)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  $PROFILE_ARG --scanner-type forex_mr_short \
  --config configs/forex_mean_reversion_short.yaml \
  --export json

# 5. US ETFs
echo "----------------------------------------"
echo "5. US ETF Trend Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type etf_long \
  --config configs/us_etf_trend_momentum.yaml \
  --export json

echo "5b. US ETF Trend Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type etf_short \
  --config configs/us_etf_trend_momentum_short.yaml \
  --export json

# 6. US Stocks
echo "----------------------------------------"
echo "6. US Stocks Trend Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type stocks_long \
  --config configs/us_stocks_trend_momentum.yaml \
  --export json

echo "6b. US Stocks Trend Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type stocks_short \
  --config configs/us_stocks_trend_momentum_short.yaml \
  --export json

echo "6c. US Stocks Mean Reversion Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type stocks_mr_long \
  --config configs/us_stocks_mean_reversion.yaml \
  --export json

echo "6d. US Stocks Mean Reversion Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type stocks_mr_short \
  --config configs/us_stocks_mean_reversion_short.yaml \
  --export json


echo "1b. Futures Trend Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  $PROFILE_ARG --scanner-type futures_short \
  --config configs/futures_trend_momentum_short.yaml \
  --export json

echo "1e. Futures Mean Reversion Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  --config configs/futures_mean_reversion.yaml \
  --export json

echo "1f. Futures Mean Reversion Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  --config configs/futures_mean_reversion_short.yaml \
  --export json

# 2. Futures (Metals specific)
echo "----------------------------------------"
echo "2. Futures Metals Trend Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  --config configs/futures_metals_trend_momentum.yaml \
  --export json

echo "2b. Futures Metals Trend Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  --config configs/futures_metals_trend_momentum_short.yaml \
  --export json

# 3. CFD
echo "----------------------------------------"
echo "3. CFD Trend Scan (Long)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  --config configs/cfd_trend_momentum.yaml \
  --export json

echo "3b. CFD Trend Scan (Short)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  --config configs/cfd_trend_momentum_short.yaml \
  --export json

# 4. Forex
echo "----------------------------------------"
echo "4. Forex Trend Scan (Long)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  --config configs/forex_trend_momentum.yaml \
  --export json

echo "4b. Forex Trend Scan (Short)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  --config configs/forex_trend_momentum_short.yaml \
  --export json

echo "4c. Forex Mean Reversion Scan (Long)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  --config configs/forex_mean_reversion.yaml \
  --export json

echo "4d. Forex Mean Reversion Scan (Short)..."
uv run -m tradingview_scraper.cfd_universe_selector \
  --config configs/forex_mean_reversion_short.yaml \
  --export json

# 5. US ETFs
echo "----------------------------------------"
echo "5. US ETF Trend Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  --config configs/us_etf_trend_momentum.yaml \
  --export json

echo "5b. US ETF Trend Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  --config configs/us_etf_trend_momentum_short.yaml \
  --export json

# 6. US Stocks
echo "----------------------------------------"
echo "6. US Stocks Trend Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  --config configs/us_stocks_trend_momentum.yaml \
  --export json

echo "6b. US Stocks Trend Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  --config configs/us_stocks_trend_momentum_short.yaml \
  --export json

echo "6c. US Stocks Mean Reversion Scan (Long)..."
uv run -m tradingview_scraper.futures_universe_selector \
  --config configs/us_stocks_mean_reversion.yaml \
  --export json

echo "6d. US Stocks Mean Reversion Scan (Short)..."
uv run -m tradingview_scraper.futures_universe_selector \
  --config configs/us_stocks_mean_reversion_short.yaml \
  --export json

echo "----------------------------------------"
echo "All global scans completed successfully. Results are in data/export/"