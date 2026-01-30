# Grand Evaluation Report: Crypto Portfolio Q1-2026

## 1. Executive Summary
The transition of the crypto discovery pipeline from a TradFi-centric model to a **Short-Cycle Momentum** and **Regime-Aware** architecture is complete. Empirical benchmarking (Run `20260108-150623`) confirms that broadening the candidate universe (Top 25) significantly outperforms strict filtering (Top 5) in both risk-adjusted returns and drawdown protection.

**Production Status (2026-01-09)**: The `crypto_production` sleeve is fully production-ready with BINANCE-only exchange focus and comprehensive hygiene templates.

## 2. Key Forensic Discoveries
### 2.1 The Gold Tracking Anomaly
- **Finding**: `BINANCE:PAXGUSDT.P` exhibited a critical tracking failure (Correlation 0.44 with direct gold), while `OKX:XAUTUSDT.P` maintained high fidelity (Correlation 0.98).
- **Action**: Blacklisted `PAXGUSDT.P`. Standardized `OKX:XAUT` as the primary Safe Haven anchor.

### 2.2 Selection Alpha vs. Engine Trust
- **Evidence**:
    - **Tier 1 (Strict Top 5)**: Sharpe 1.47, Max DD -35.7%.
    - **Tier 2 (Broad Top 25)**: Sharpe 1.76, Max DD -23.0%.
- **Conclusion**: Strict selection was destroying value by over-concentrating the portfolio.
- **Policy**: Shifted Natural Selection to a **"Noise Floor"** role. It now filters only mathematically erratic white noise (Entropy > 0.999), delegating weighting and factor pruning to the **Barbell/HRP** risk engines.

## 3. Performance & Risk Audit (Barbell Champion)
| Profile | Sharpe | Ann. Return | Ann. Vol | Max DD | Calmar | Beta (SPY) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Barbell** | **4.46** | **150.5%** | **33.8%** | **-5.1%** | **29.3** | **0.87** |
| **Benchmark (SPY)**| 0.75 | 8.3% | 11.0% | -4.5% | 1.8 | 1.00 |

- **The Barbell Effect**: Achieved sub-40% volatility by anchoring 90% in Safe Havens while capturing explosive short-cycle alpha through 10% Aggressor exposure.

## 4. Operational Standards
- **Temporal Scale**: removed 3M/6M anchors; focused on Daily/Weekly/Monthly cycles.
- **Diversity Floor**: Enforced min 5 assets for crypto sleeves.
- **Entropy Acceptance**: Set baseline to 0.995 - 0.999 to accommodate crypto microstructure noise.

## 5. Production Hardening (2026-01-09)

### 5.1 Exchange Strategy
- **BINANCE-only**: Production crypto sleeve uses BINANCE exclusively for highest liquidity and cleanest execution.
- **Rationale**: Eliminates multi-exchange deduplication complexity and reduces cross-exchange arbitrage noise.

### 5.2 Scanner Consolidation
| Scanner | Type | Status |
| :--- | :--- | :--- |
| `binance_spot_trend` | Spot Long | Active |
| `binance_perp_trend` | Perp Long | Active |
| `binance_perp_short` | Perp Short | Active |
| `binance_mtf_trend` | MTF Confirmation | Active |
| `vol_breakout` | Volatility Breakout | Active |

### 5.3 Backtesting Parameters
| Parameter | Value | Rationale |
| :--- | :--- | :--- |
| Slippage | 0.001 (0.1%) | Higher for crypto volatility |
| Commission | 0.0004 (0.04%) | Typical CEX maker/taker fees |
| Benchmarks | BINANCE:BTCUSDT, AMEX:SPY | Dual benchmark for cross-asset comparison |

### 5.4 Key Make Targets
```bash
make flow-crypto           # Full crypto production run
make crypto-scan-audit     # Validate crypto scanner configs
make flow-meta-production  # Multi-sleeve including crypto
```

## 6. Conclusion
The `crypto_production` sleeve is fully deliverable and verified. It provides a de-risked path to high-velocity alpha that is statistically sound and institutionally traceable.
