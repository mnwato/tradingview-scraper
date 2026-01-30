#!/bin/bash
set -e

echo "Starting Crypto Base Top 50 Scans..."

# Binance
echo "1. Binance Base Top 50 Spot..."
uv run -m tradingview_scraper.futures_universe_selector --config configs/crypto_cex_base_top50_binance.yaml --export json

echo "1b. Binance Base Top 50 Perp..."
uv run -m tradingview_scraper.futures_universe_selector --config configs/crypto_cex_base_top50_binance_perp.yaml --export json

# OKX
echo "2. OKX Base Top 50 Spot..."
uv run -m tradingview_scraper.futures_universe_selector --config configs/crypto_cex_base_top50_okx.yaml --export json

echo "2b. OKX Base Top 50 Perp..."
uv run -m tradingview_scraper.futures_universe_selector --config configs/crypto_cex_base_top50_okx_perp.yaml --export json

# Bybit
echo "3. Bybit Base Top 50 Spot..."
uv run -m tradingview_scraper.futures_universe_selector --config configs/crypto_cex_base_top50_bybit.yaml --export json

echo "3b. Bybit Base Top 50 Perp..."
uv run -m tradingview_scraper.futures_universe_selector --config configs/crypto_cex_base_top50_bybit_perp.yaml --export json

# Bitget
echo "4. Bitget Base Top 50 Spot..."
uv run -m tradingview_scraper.futures_universe_selector --config configs/crypto_cex_base_top50_bitget.yaml --export json

echo "4b. Bitget Base Top 50 Perp..."
uv run -m tradingview_scraper.futures_universe_selector --config configs/crypto_cex_base_top50_bitget_perp.yaml --export json

echo "All base scans completed."
