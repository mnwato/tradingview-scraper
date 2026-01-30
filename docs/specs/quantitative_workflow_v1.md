# Specification: Quantitative Workflow V1
**Status**: Finalized (Production Ready)
**Date**: 2025-12-21

## 1. Executive Summary
The V1 Quantitative Workflow is a Python-native, asynchronous pipeline designed for high-performance multi-asset discovery and robust risk management. It replaces sequential shell-script execution with a unified orchestrator that adapts to market volatility regimes.

## 2. Pipeline Architecture

### Stage 1: Async Discovery & Liquid Selection
- **Engine**: `AsyncScreener` + `FuturesUniverseSelector`
- **Mechanism**: "Liquid Winners" Filter Architecture.
    1.  **API Fetch**: Sort by `Value.Traded` to fetch top 300 liquid assets (avoids API starvation).
    2.  **Client Filter**: Apply strict Alpha/Trend gates (ADX > 15) and Hygiene gates locally.
    3.  **Ranking**: Re-sort survivors by Alpha Signal (Perf/Yield).
- **Latency**: Reduced by >60% compared to sequential processing.

### Stage 2: Alpha Generation & Post-Processing
- **Engine**: `FuturesUniverseSelector.process_data`
- **Logic**: Filters raw candidates by Liquidity Floors, Market Cap Rank, and Trend Strength (ADX).
- **Output**: Tagged LONG/SHORT signals with normalized metadata.

### Stage 3: Robust Risk Management
- **Regime Detection**: `MarketRegimeDetector` monitors cross-sectional volatility to classify market states into `QUIET`, `NORMAL`, or `CRISIS`.
- **Covariance Estimation**: `ShrinkageCovariance` uses **Ledoit-Wolf Shrinkage** to stabilize risk matrices for short-lookback windows (preventing numerical singularity).
- **Secular Alignment Standard**: All production-grade historical data must maintain a minimum **500-day lookback** to capture full volatility cycles across varied asset classes.
- **Outlier Detection Protocol**: `port-analyze` calculates a **"Cluster Concentration Entropy"** score ($H$). If $H < 0.5$ (indicating single-asset dominance), the risk engine must trigger a weight-smearing pass to maintain diversity.
- **Optimization**: `BarbellOptimizer` implements a Taleb-inspired split:
    - **Safe Core**: Optimized for Maximum Diversification Ratio.
    - **Convex Aggressor**: Exposure to high-antifragility (high-optionality) assets.
    - **Adaptive Shift**: Automatically increases Core allocation (up to 95%) during `CRISIS` regimes.

### Stage 4: Metadata Lakehouse & PIT Integrity
- **Persistence**: Symbols and execution parameters are upserted into the Parquet-based `MetadataCatalog`.
- **Compliance**: Ensures all portfolio constituents have verified tick sizes and Point-in-Time versioning for backtest reliability.
- **Resolver Integrity Standard**: All feature flags and the `selection_mode` must be explicitly defined in the profile-level `features` block to ensure deterministic override of global defaults.
- **Stale-Tolerance Policy**: Strict zero-tolerance for stale production assets. Any asset with a data lag $>3$ market sessions relative to the universe benchmark (e.g., SPY) must be force-refreshed via targeted sync or auto-pruned before Factor Analysis to prevent volatility understatement.

### Stage 5: Multi-Sleeve Meta-Portfolio (Recursive HRP)
- **Engine**: `InterSleeveOptimizer`
- **Mechanism**: Aggregates return streams from independent sleeves (e.g., Crypto/Futures vs. TradFi ETFs).
- **Allocation**: Applies **Hierarchical Risk Parity (HRP)** across sleeves to determine top-level weights.
- **Flattening**: Reconciles sleeve weights with asset weights to produce a final, diversified execution manifest.
- **Benefit**: Handles disparate trading calendars and liquidity regimes while maintaining orthogonal exposure.

## 3. Operations
The full pipeline is executed via a single entry point:
```python
from tradingview_scraper.pipeline import QuantitativePipeline

pipeline = QuantitativePipeline()
result = pipeline.run_full_pipeline(configs=["config1.yaml", "config2.yaml"])
```

## 4. Key Performance Indicators (V1)
- **Parallelism**: 100% async I/O for API interactions.
- **Robustness**: No matrix inversion failures on identical crypto assets.
- **Adaptability**: Dynamic risk-budgeting based on realized volatility.
