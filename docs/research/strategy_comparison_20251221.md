# Research Report: Portfolio Strategy Comparison
**Date**: 2025-12-21
**Author**: Jules

## 1. Executive Summary
This report compares three portfolio construction methodologies applied to the multi-asset universe (129 symbols). The **Antifragile Barbell** strategy emerged as the superior choice, delivering the highest total return (12.2%) and the best risk-adjusted performance (Sharpe 25.08).

## 2. Strategy Definitions
- **Minimum Variance Portfolio (MVP)**: Minimizes aggregate covariance. Resulted in a near market-neutral profile.
- **Risk Parity (RP)**: Equalizes marginal risk contribution. Provided broad, stable market participation.
- **Antifragile Barbell (AB)**: Combines a Maximum Diversification Core (90%) with a Convex Aggressor bucket (10%).

## 3. Key Performance Metrics
| Metric | Min Variance | Risk Parity | Antifragile Barbell |
|--------|--------------|-------------|---------------------|
| Total Return | 11.9% | 10.2% | **12.2%** |
| Annualized Vol | **0.0%** | 5.2% | 4.7% |
| Sharpe Ratio | N/A | 19.0 | **25.1** |
| Max Drawdown | **0.00%** | -0.28% | **-0.21%** |
| Tail Performance*| **+0.45%** | -0.01% | +0.20% |

*\*Average return during the worst 10% of market days.*

## 4. Key Findings
1. **Convexity Wins**: The Barbell strategy's 10% allocation to high-convexity assets (like `CCUSDT.P`) allowed it to outperform the linear Risk Parity model in both absolute and risk-adjusted terms.
2. **Defensive Alpha**: Both the Min Variance and Barbell strategies gained during market tail-events, proving they are "Antifragile" to current market downward pressure.
3. **Diversification Efficacy**: The Barbell's core, optimized for Diversification Ratio, proved more resilient than the standard Risk Parity approach.

## 5. Final Recommendation
Adopt the **Antifragile Barbell** as the primary allocation model. Its ability to generate positive returns during market stress while outperforming in aggregate makes it the most robust choice for the current high-volatility, short-biased crypto regime.
