# Specification: E2E Quantitative Orchestration & Robust Risk

## 1. Goal
Transition the project from shell-script based execution to a Python-native, asynchronous pipeline. This improves performance via parallelized I/O and provides a foundation for more complex, state-aware risk management.

## 2. Technical Requirements

### A. Async Screener
- **Library**: `aiohttp` for asynchronous HTTP requests.
- **Functionality**: Parallelize requests to the TradingView scanner API across multiple exchanges and markets.
- **Error Handling**: Graceful handling of individual request failures without halting the entire batch.

### B. Unified Pipeline Orchestrator
- **Class**: `tradingview_scraper.Pipeline`
- **Responsibility**: Orchestrate the flow:
    1.  **Discovery**: High-speed parallel scanning.
    2.  **Alpha Filtering**: Sequential or parallel filtering based on strategy rules.
    3.  **Risk Optimization**: Solve for portfolio weights (Min Var, Risk Parity, Barbell).
    4.  **Persistence**: Save results to the Data Lakehouse and metadata catalogs.

### C. Robust Risk Management
- **Regime Detection**: Detect market volatility regimes to dynamically adjust risk parameters.
- **Covariance Shrinkage**: Use Ledoit-Wolf shrinkage to stabilize the covariance matrix, especially when dealing with limited historical windows.

## 3. Success Criteria
- [ ] Scan latency reduced by at least 50% through parallelization.
- [ ] Ability to run the entire pipeline with a single Python command.
- [ ] Verified stable portfolio weights during regime transitions.
