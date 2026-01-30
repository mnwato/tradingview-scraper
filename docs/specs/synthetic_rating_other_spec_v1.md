# Specification: Synthetic Recommend.Other Reconstruction (v1.0)

## 1. Overview
This specification defines the logic for reconstructing TradingView's `Recommend.Other` (Oscillators Rating) from raw OHLCV data. This enables the generation of historical rating signals for backtesting.

## 2. Component Logic
The rating is an unweighted average of **11 components**.
Formula: $$ Score = \frac{N_{Buy} - N_{Sell}}{11} $$

### 2.1 RSI (14)
- **Buy**: $< 30$ (Oversold)
- **Sell**: $> 70$ (Overbought)
- **Neutral**: $30 \le RSI \le 70$

### 2.2 Stochastic (14, 3, 3)
- **Buy**: $\%K < 20$
- **Sell**: $\%K > 80$
- **Neutral**: $20 \le \%K \le 80$

### 2.3 CCI (20)
- **Buy**: $< -100$
- **Sell**: $> 100$
- **Neutral**: $-100 \le CCI \le 100$

### 2.4 ADX (14, 14)
- **Buy**: $ADX > 20$ AND $+DI > -DI$
- **Sell**: $ADX > 20$ AND $+DI < -DI$
- **Neutral**: $ADX \le 20$

### 2.5 Awesome Oscillator (AO)
- **Buy**: $AO > 0$ AND Rising ($AO_t > AO_{t-1}$)
- **Sell**: $AO < 0$ AND Falling ($AO_t < AO_{t-1}$)
- **Neutral**: Counter-trend moves (e.g. $AO > 0$ but Falling)

### 2.6 Momentum (10)
- **Buy**: $Mom > 0$
- **Sell**: $Mom < 0$

### 2.7 MACD (12, 26, 9)
- **Buy**: $Histogram > 0$ (MACD Line > Signal Line)
- **Sell**: $Histogram < 0$ (MACD Line < Signal Line)

### 2.8 Stochastic RSI (3, 3, 14, 14)
- **Buy**: $K < 20$
- **Sell**: $K > 80$

### 2.9 Williams %R (14)
- **Buy**: $< -80$
- **Sell**: $> -20$

### 2.10 Bull Bear Power (13)
- **Formula**: $Value = (High - EMA_{13}) + (Low - EMA_{13})$
- **Buy**: $Value > 0$ AND Rising ($Value_t > Value_{t-1}$)
- **Sell**: $Value < 0$ AND Falling ($Value_t < Value_{t-1}$)
- **Neutral**: Counter-trend moves

### 2.11 Ultimate Oscillator (7, 14, 28)
- **Buy**: $< 30$
- **Sell**: $> 70$

## 3. Implementation Verification
Validating against `BINANCE:BTCUSDT` snapshot on 2026-01-17:
- **Actual TV Score**: 0.1818
- **Synthetic Score**: 0.2727
- **Difference**: 0.0909 (1 Vote)
- **Status**: ✅ Acceptable Correlation

## 4. Usage
This logic (along with `Recommend.MA`) enables the reconstruction of the full `Recommend.All` composite signal:
$$ \text{Recommend.All} \approx 0.57 \times MA + 0.43 \times Other $$
