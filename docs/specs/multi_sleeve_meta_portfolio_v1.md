# Specification: Multi-Sleeve Meta-Portfolio (v1)
> **Status:** [SPEC] Fractal Risk Architecture (v1.4) - 2026-01-14
> **Conceptual Note:** Meta-portfolio sleeves are treated as profile-matrices. The meta-layer recursively reuses risk profiles (e.g., Meta-MinVar over sub-MinVar portfolios) to ensure philosophy consistency across the capital stack.

## 1. Objective
To build robust, diversified meta-portfolios by combining independent strategy sleeves using a recursive risk multiverse. This prevents risk-philosophy "drift" between the asset layer and the allocation layer.

## 2. Sleeve Inventory (Production)

| Sleeve ID | Profile | Exchange Scope | Calendar | Status |
|-----------|---------|----------------|----------|--------|
| `instruments` | `production` | TradFi (NYSE, NASDAQ, CME) | Market Hours | Active |
| `etfs` | `institutional_etf` | TradFi (AMEX, NYSE) | Market Hours | Active |
| `crypto` | `crypto_production` | BINANCE-only | 24x7 (XCRY) | Active |

### 2.1 Crypto Sleeve Requirements
The crypto sleeve has unique requirements due to its 24x7 trading calendar and market microstructure:

**Calendar Handling**:
- Uses XCRY calendar (24x7, no holidays)
- When joining with TradFi sleeves, use **inner join** on dates (no weekend padding)
- Warning: Zero-filling weekends would inflate crypto-TradFi correlation artificially

**Exchange Strategy**:
- BINANCE-only for production (highest liquidity, cleanest execution)
- Multi-exchange (BINANCE/OKX/BYBIT/BITGET) available for research only

**Predictability Thresholds**:
- Entropy acceptance: 0.900-0.950 (Hard veto at 0.999 per CR-631)
- Hurst random-walk zone: 0.48-0.52

**Backtesting Parameters**:
- Slippage: 0.001 (vs 0.0005 for TradFi)
- Commission: 0.0004 (vs 0.0001 for TradFi)
- Cash asset: USDT
- Benchmarks: `BINANCE:BTCUSDT`, `AMEX:SPY`

## 2. Architecture: Fractal Optimization

### Layer 1: Intra-Sleeve Matrix
- **Definition**: Each sleeve executes a tournament of risk profiles (MinVar, HRP, Barbell).
- **Output**: A return matrix $R_{sleeve}[t, profile]$ representing each optimization philosophy.

### Layer 2: Inter-Sleeve Allocation (Fractal Meta)
- **Mechanism**: Philosophy-Matched Optimization.
- **Protocol**: 
    - `Meta-MinVar` targets `[Sleeve1-MinVar, Sleeve2-MinVar]`.
    - `Meta-HRP` targets `[Sleeve1-HRP, Sleeve2-HRP]`.
    - `Meta-Barbell` targets `[Sleeve1-Barbell, Sleeve2-Barbell]`.
- **Consistency Rule**: A Meta-Portfolio profile MUST only consume the corresponding return stream from its constituent sleeves to preserve the risk objective across scales.
- **Constraint**: All sleeves must share a common `temporal_id`.
- **Output**: Unified weights mapped back to individual assets.

## 3. Data Contracts
### 3.1 Return Vectors
Return series for meta-allocation must be exported to `artifacts/meta/returns/<profile>.pkl` for each participating sleeve.

### 3.2 The Parity Constraint Mandate (v1.4)
To ensure statistical validity in inter-sleeve HRP, all constituent sleeves must adhere to the **Parity Constraint**:
1.  **Temporal Parity**: Sleeves must share identical `lookback_days` (default 500d), `train_window` (default 60d), and `test_window` (default 20d).
2.  **Selection Parity**: All sleeves must use the same `selection_mode` version (standardized on **v4 MLOps**) and share `feat_selection_logmps` and `feat_predictability_vetoes` settings.
3.  **Fidelity Parity**: Backtest simulators (e.g., `cvxportfolio`) and slippage/commission models must be consistent across the meta-boundary.

### 3.3 Institutional Parity Matrix (v1.2)
Participating sleeves in a `meta_production` run must demonstrate a **100% Parameter Overlap** in their `resolved_manifest.json` for the following blocks:
- `features`: Selection engine version (v4) and alpha feature flags.
- `selection`: Quality thresholds and momentum gates.
- `backtest`: Simulation horizons (60/20/20) and friction models.

### 3.4 Crypto Sleeve Parity Exceptions
The crypto sleeve has documented exceptions to the standard parity matrix:

| Parameter | TradFi Value | Crypto Value | Rationale |
|-----------|--------------|--------------|-----------|
| `entropy_max_threshold` | 0.950 | 0.999 | Higher noise tolerance for crypto microstructure |
| `backtest_slippage` | 0.0005 | 0.001 | Higher volatility and wider spreads |
| `backtest_commission` | 0.0001 | 0.0004 | Typical CEX maker/taker fees |
| `feat_dynamic_selection` | true | false | Crypto benefits from stable universe due to rapid regime changes |
| `benchmark_symbols` | `["AMEX:SPY"]` | `["BINANCE:BTCUSDT", "AMEX:SPY"]` | Dual benchmark for cross-asset comparison |

### 3.5 Sleeve Weight Guardrails
To prevent over-concentration in any single sleeve:
- **Maximum sleeve weight**: 50% (no single sleeve dominates meta-allocation)
- **Minimum sleeve weight**: 5% (ensures diversification benefit is captured)

## 4. Operational Workflow
1.  **Stage 1: Sleeve Matrix Execution**
    - Run `make flow-production PROFILE=production`
    - Run `make flow-production PROFILE=institutional_etf`
2.  **Stage 2: Meta-Returns Construction**
    - Script: `scripts/build_meta_returns.py`
    - **Intersection Policy**: The Meta-Returns matrix must only contain dates where ALL constituent sleeves have valid data.
3.  **Stage 3: Meta-Allocation**
    - Script: `scripts/optimize_meta_portfolio.py`
    - Recursively applies the corresponding risk engine to meta-returns.
4.  **Stage 4: Flattening & Reporting**
    - Script: `scripts/flatten_meta_weights.py`
    - Map meta-weights to atomic assets.

## 5. Acceptance Criteria
- **Correlation Benefit**: The Meta-Portfolio must show lower volatility than the best individual sleeve. (Verified: Inter-sleeve correlation of **0.10** observed).
- **Reproducibility**: The meta-allocation must be logged in the `audit.jsonl` of the meta-run.
- **Integrity**: Zero tolerance for weekend padding or calendar drift. (Verified via `audit_data_integrity.py`).
- **TWR Benchmarking**: Annualized returns must be calculated using Time-Weighted Return (TWR) to handle high-volatility compounding artifacts.
- **Weight Bounds**: All sleeves must be within 5%-50% weight range in final meta-allocation.

## 6. Audit Logs (Sample Trace)
The meta-optimization step is recorded in the ledger:
```json
{
  "step": "meta_optimize_hrp",
  "params": {"engine": "custom", "profile": "hrp", "n_sleeves": 2},
  "data": {"weights": {"etfs": 0.4577, "instruments": 0.5423}}
}
```
