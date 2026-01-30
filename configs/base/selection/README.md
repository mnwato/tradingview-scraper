# Selection Configuration

This directory contains parameter files for the selection engine that ranks and filters candidates across different universes.

## Files

- **`etf_params.json`**: Selection parameters for ETF universe (e.g., Log-MPS weights, normalization methods).
- **`instruments_params.json`**: Selection parameters for instruments universe (e.g., stocks, forex, futures).

## Parameter Structure

Both files follow the same structure:

```json
{
  "features": {
    "feat_partial_rebalance": true,
    "feat_turnover_penalty": true,
    "feat_xs_momentum": false,
    "feat_spectral_regimes": true,
    "feat_decay_audit": true,
    "feat_audit_ledger": true,
    "feat_pit_fidelity": true,
    "feat_rebalance_mode": "window",
    "feat_rebalance_tolerance": false,
    "rebalance_drift_limit": 0.05,
    "feat_short_costs": true,
    "short_borrow_cost": 0.02,
    "feat_dynamic_selection": true,
    "feat_regime_survival": false,
    "feat_predictability_vetoes": true,
    "feat_efficiency_scoring": true,
    "feat_selection_logmps": true,
    "entropy_max_threshold": 0.9,
    "efficiency_min_threshold": 0.1,
    "hurst_random_walk_min": 0.45,
    "hurst_random_walk_max": 0.55,
    "weights_global": {
      "momentum": 1.7469,
      "stability": 0.0458,
      "liquidity": 0.2946,
      "antifragility": 0.6263,
      "survival": 1.4,
      "efficiency": 1.5348,
      "entropy": 0.0322,
      "hurst_clean": 0.3485
    },
    "top_n_global": 5,
    "weights_v2_1_global": {
      "momentum": 0.2055,
      "stability": 0.0882,
      "liquidity": 0.1697,
      "antifragility": 0.0988,
      "survival": 0.2273,
      "efficiency": 0.1027,
      "entropy": 0.006,
      "hurst_clean": 0.1018
    },
    "normalization_methods_v2_1": {
      "momentum": "logistic",
      "stability": "logistic",
      "liquidity": "zscore",
      "antifragility": "rank",
      "survival": "rank",
      "efficiency": "rank",
      "entropy": "zscore",
      "hurst_clean": "zscore"
    },
    "clipping_sigma_v2_1": 3.49,
    "top_n_v2_1": 2,
    "selection_mode": "v3.2"
  },
  "selection": null,
  "backtest": null
}
```

## Selection Modes

- **v3.2 (Log-MPS)**: Log-Multiplicative Probability Scoring with additive log-probabilities for numerical stability and HPO optimization. Global robust with highest 2025 Annualized Return (29.2%) and Sharpe (2.35).
- **v2.1 (CARS)**: Additive Rank-Sum (CARS 2.1) with Multi-Method Normalization (Logistic/Z-score/Rank). Optimized for lower volatility and maximum drawdown protection.

## Feature Flags

| Feature | Description |
|---------|-------------|
| `feat_partial_rebalance` | Enable partial rebalancing to avoid noisy small trades |
| `feat_turnover_penalty` | Minimize churn to maintain Sharpe ratio stability |
| `feat_xs_momentum` | Cross-sectional momentum signals |
| `feat_spectral_regimes` | Spectral (DWT) and entropy metrics for regime detection |
| `feat_decay_audit` | Audit decay factors in returns |
| `feat_audit_ledger` | Enable audit ledger for decision tracking |
| `feat_pit_fidelity` | Point-in-time fidelity for backtests |
| `feat_predictability_vetoes` | Strict alpha-predictability filters |
| `feat_efficiency_scoring` | Market efficiency metrics |
| `feat_selection_logmps` | Use Log-MPS selection algorithm |

## Weights

Each factor (momentum, stability, liquidity, etc.) has configurable weights that determine its contribution to the composite score. Different selection modes use different weight sets (e.g., `weights_global` for v3.2, `weights_v2_1_global` for v2.1).

## Normalization Methods

Factors can be normalized using different methods:
- **logistic**: Sigmoid transformation
- **zscore**: Standard score normalization
- **rank**: Percentile ranking

Clipping (`clipping_sigma_v2_1`) is applied to normalize outliers before final ranking.

## Usage

These files are referenced by the manifest system and can be overridden via environment variables. See `configs/README.md` for details on profile-based configuration.
