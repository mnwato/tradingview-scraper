# Design: Multi-Engine Selection (v1)

## 1. Objective
To enhance candidate selection conviction by ensembling multiple independent ranking engines into a single "Weight of Evidence" (WoE) score.

## 2. Multi-Ranker Ensemble

### 2.1 The Ensemble Policy
A new selection policy that delegates scoring to a list of configured rankers.

| Ranker | Primary Metric | Rationale |
| :--- | :--- | :--- |
| `mps_ranker` | Log-Probability | Measures statistical conviction of the underlying model. |
| `signal_ranker` | Signal Strength | Measures the raw alpha intensity (e.g., trend ADX). |
| `regime_ranker` | Regime Fit | Measures how well the asset fits the current volatility quadrant. |

### 2.2 Weight of Evidence (WoE)
The ensemble score is calculated as a weighted sum of normalized ranker outputs:

$$ S_{woe} = \sum_{i=1}^N w_i \times \text{Norm}(R_i) $$

Where:
- $R_i$ is the output of ranker $i$.
- $w_i$ is the weight assigned to ranker $i$ (default = $1/N$).
- $\text{Norm}$ is a standard scaler (e.g., Rank or Z-Score).

## 3. Implementation

### 3.1 `EnsembleRanker`
A meta-ranker that inherits from `BaseRanker` and wraps multiple sub-rankers.

```python
class EnsembleRanker(BaseRanker):
    def score(self, context, candidates):
        # 1. Collect scores from all sub-rankers
        # 2. Normalize and aggregate
        # 3. Return ensembled scores
```

### 3.2 Stage Update (`alpha.policy`)
Update the policy stage to instantiate the `EnsembleRanker` if `ensemble_weights` are provided in the manifest.

## 4. TDD Strategy
- **`tests/test_ensemble_selection.py`**:
    - Mock two rankers (A and B).
    - Assign weights (0.7, 0.3).
    - Verify that the ensembled score matches the expected weighted average.

## 5. Security & Stability
- If any sub-ranker fails, the ensemble should log an error and fallback to a default (Equal Weight) of the remaining healthy rankers.
- Enforced SSP (Selection Scarcity Protocol) still applies to the final ensembled winners.
