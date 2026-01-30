# Design: Engine-Candidate Context Bundle

## 1. Objective
To provide downstream engines with a "Battery-Included" data package that minimizes re-computation and initialization errors.

## 2. The Context Schema (`portfolio_candidates_v3.json`)
The output of `natural_selection.py` will now include an `engine_context` block for each symbol:

```json
{
  "symbol": "BINANCE:BTCUSDT.P",
  "identity": "BTC",
  "alpha_risk_score": 0.82,
  "engine_context": {
    "nautilus": {
      "instrument_id": "BTCUSDT.BINANCE",
      "price_precision": 2,
      "quantity_precision": 3,
      "tick_size": "0.1",
      "lot_size": "0.001"
    },
    "cvxportfolio": {
      "risk_free_rate": 0.05,
      "bid_ask_spread": 0.0001,
      "borrow_cost": 0.0002
    },
    "skfolio": {
      "cluster_id": 4,
      "is_anchor": true
    }
  }
}
```

## 3. The "Shadow Optimization" Pass
- **Location**: Final step of `natural_selection.py`.
- **Logic**: 
    1. Construct a temporary `skfolio` Portfolio object.
    2. Check the condition number of the covariance matrix.
    3. If $\kappa > 10^6$, find the two symbols with the highest Mutual Information.
    4. Remove the one with the lower `alpha_risk_score`.
    5. Repeat until the matrix is "Well-Conditioned."

## 4. Implementation Path
- **Update**: `scripts/enrich_candidates_metadata.py` to fetch exchange-specific lot/tick sizes.
- **Update**: `scripts/natural_selection.py` to perform the matrix health-check.
