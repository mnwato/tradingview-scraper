# Market Benchmark & Simulator Fidelity Report (Jan 2026)

## 1. Summary of Simulator Performance (Run 20260101-002201)

The "Market" benchmark (Min Variance profile for the `market` engine) was used as a control group to identify simulation artifacts.

| Simulator    | Sharpe | Return | Vol    | Turnover | Methodology |
| :----------- | :----- | :----- | :----- | :------- | :---------- |
| **Custom**   | 2.2157 | 17.64% | 20.05% | 5.68%    | Frictionless, Window-Aware |
| **CvxPortfolio** | 2.1887 | 17.02% | 20.36% | 5.34%    | Friction-Aware, Window-Aware |
| **VectorBT** | 2.0504 | 15.76% | 19.57% | 99.31%   | Vectorized, Fresh Buy-In |

## 2. Key Findings

### Return Discrepancy Resolved
Initially, `vectorbt` reported significantly lower returns (~5%). This was traced to a **Starting Price Mismatch**. The pipeline constructs prices from returns starting at the first test date (Day 1). `vectorbt` assumes the first price entry is the "end of Day 1", missing the return from Day 0 to Day 1.
*   **Fix**: Prepending a dummy row of 1.0 at Day 0 in the simulator synchronized the indices and restored return parity.

### Turnover Outlier: VectorBT
`vectorbt` consistently reports ~100% turnover per window.
*   **Root Cause**: It simulates a "Fresh Buy-In" from cash at the start of every 20-day window.
*   **Comparison**: `Custom` and `CvxPortfolio` simulators are "Window-Aware"—they track ending holdings from the previous window and only record the *delta* as turnover.
*   **Recommendation**: Use `vectorbt` for fast strategy exploration, but rely on `CvxPortfolio` for realistic transaction cost and churn analysis.

## 3. Audit Fidelity & Reconstruction

The audit ledger (`audit.jsonl`) has been updated to provide 100% transparency into the portfolio's evolution.

### Ledger Enhancements
- **Full Weights Recording**: Every `backtest_optimize` success now logs the full dictionary of asset weights.
- **Reproducibility**: With the hashes of input returns and the recorded output weights, any window can be reconstructed and verified against the simulator's results.

### Sample Audit Entry
```json
{
  "step": "backtest_optimize",
  "status": "success",
  "data": {
    "weights": {
      "OANDA:WHEATUSD": 0.0715,
      "BYBIT:ETHUSD.P": 0.0515,
      ...
    }
  }
}
```

## 4. Conclusion
The simulators are now directionally aligned and produce reliable metrics. The system is stable, and the decision-making process is fully auditable.
