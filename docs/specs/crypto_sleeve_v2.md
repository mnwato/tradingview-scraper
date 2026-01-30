# Crypto Sleeve Operations v2

## 1. Overview
The crypto sleeve operates as an orthogonal capital allocation within the multi-sleeve meta-portfolio architecture. It is designed to capture high-volatility alpha while mitigating tail risk through strict constraints.

## 2. Exchange Strategy
- **Production**: BINANCE-only (Spot & Perpetual Futures) for institutional execution.
- **Research**: Multi-exchange (BINANCE/OKX/BYBIT/BITGET) configs available.

## 3. Production Pillars (Forensic Standards)
Agents must ensure every production run adheres to the following five pillars:

### I. Regime Alignment
- **Step Size**: 10 days (Bi-Weekly).
- **Rationale**: Captures fast-moving volatility clusters specific to crypto markets.

### II. Tail-Risk Mitigation
- **Alignment**: 20-day alignment provides best balance between momentum capture and drawdown protection.
- **Clipping**: Annualized Return Clipping (-99.99%) enforced to prevent mathematical divergence.

### III. Alpha Capture
- **Factor Isolation**: High-resolution (threshold=0.45).
- **Entropy Resolution**: Order=5.
- **Selection Scarcity Protocol (SSP)**: Robust multi-stage fallbacks (Max-Sharpe -> Min-Var -> EW) when winner pool is sparse ($N < 15$).

### IV. Directional Purity
- **Inversion**: SHORT candidate returns are inverted with a -100% loss cap before optimization ($R_{synthetic,short} = -clip(R_{raw}, upper=1.0)$).
- **Goal**: Risk-parity engines (HRP/MinVar) correctly reward stable downward drift.

### V. Toxic Data Guard
- **Filter**: Assets with daily returns > 500% (5.0) are automatically dropped.
- **Short Cap**: Synthetic shorts are capped at -100% loss.

## 4. Crypto-Specific Parameters
| Parameter | Crypto Value | TradFi Value | Rationale |
| :--- | :--- | :--- | :--- |
| `entropy_max_threshold` | 0.999 | 0.995 | Higher noise tolerance for microstructure |
| `backtest_slippage` | 0.001 | 0.0005 | Higher volatility and wider spreads |
| `backtest_commission` | 0.0004 | 0.0001 | Typical CEX maker/taker fees |
| `feat_dynamic_selection` | false | true | Stable universe benefits crypto |

## 5. Calendar Handling
- **Calendar**: XCRY (24x7, no holidays).
- **Meta-Portfolio Join**: Inner join on dates when combining with TradFi sleeves.
- **Zero-Fill**: NEVER zero-fill weekends for crypto-TradFi correlation calculations.
