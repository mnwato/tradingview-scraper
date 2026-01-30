# Audit: Feature Parity & Ground Truth Verification (v1)

## 1. Objective
To audit the accuracy of the replicated technical ratings (`TechnicalRatings`) by comparing them against the "Ground Truth" values fetched directly from the TradingView Screener API.

## 2. Identified Risks

### 2.1 Component Weight Mismatch
- **Risk**: TradingView's internal formula for `Recommend.All` is proprietary. While we use $0.574 \times MA + 0.3914 \times Other$, any deviation in component weighting will lead to cumulative error.

### 2.2 Alignment Offset (Ichimoku/Projected)
- **Risk**: TradingView projects certain indicators (like Ichimoku Cloud) into the future. Our replication must correctly shift these components to match the "Today" view of the Screener.

### 2.3 Floating Point Precision
- **Risk**: Slight differences in the implementation of TA-Lib or standard formulas (e.g., EMA smoothing) can cause divergence in the final rating (-1 to 1 range).

## 3. Ground Truth Protocol

### 3.1 Sample Selection
Sample 10 high-liquidity assets from Binance (USDT pairs) representing various volatility quadrants:
- `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, `XRPUSDT`, etc.

### 3.2 Sourcing
1. Fetch latest ratings via `Screener` API snapshot.
2. Fetch corresponding 500-day OHLCV history via `DataLoader`.
3. Calculate replicated ratings using `TechnicalRatings.calculate_recommend_all`.

## 4. Conclusion
This audit is a critical forensic step to ensure that the "Natural Selection" pillar is not biased by implementation artifacts.
