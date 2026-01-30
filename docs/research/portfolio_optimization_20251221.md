# Research Report: Portfolio Optimization Results
**Date**: 2025-12-21
**Author**: Jules

## 1. Objective
Construct a risk-optimized portfolio using candidates from the 2025-12-21 global market scans, utilizing Modern Portfolio Theory (MPT).

## 2. Universe Composition
- **Total Candidates**: 129 symbols.
- **Diversity**: Crypto (Binance, OKX, Bybit, Bitget), US Stocks (NASDAQ, NYSE), Commodities (COMEX, NYMEX), Forex (ThinkMarkets).
- **Sentiment**: Heavily Short-biased in Crypto; Long-biased in Precious Metals and Defensive Equities.

## 3. Optimization Results

### A. Minimum Variance Portfolio (MVP)
- **Primary Goal**: Minimize aggregate volatility.
- **Expected Volatility**: ~0.0% (Statistical estimate on the selected window).
- **Top Holdings**:
    1. `NYSE:SHW` (Short) - 11.4%
    2. `CBOT:KEH2026` (Short) - 9.1%
    3. `NYSE:PNNT` (Short) - 9.0%
    4. `NYSE:MRK` (Long) - 5.4%
- **Observation**: The optimizer paired low-volatility commodities and defensive stocks to cancel out directional risk.

### B. Risk Parity Portfolio (RP)
- **Primary Goal**: Equalize risk contribution across all assets.
- **Asset Distribution**: Diversified weights (~2% per asset).
- **Top Contributors**: `THINKMARKETS:CADJPY` (Long), `OANDA:DE30EUR` (Long), `COMEX:SI1!` (Long).
- **Observation**: Provides much broader market participation than Min Var, capturing "Alpha" from a wider range of sectors.

## 4. Signal Inversion Strategy
The portfolio treated **Short** signals as "Synthetic Longs" by inverting their historical returns. This allowed the optimizer to maximize the benefit of downward trends in the crypto market while maintaining a long-only constraint in the weight solver.
