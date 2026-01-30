# Design: Meta-Portfolio Resilience & Forensic Accuracy (v1)

## 1. Objective
To implement numerical safety bounds and enhanced forensic visibility for multi-sleeve meta-portfolios.

## 2. Numerical Safety Bounds

### 2.1 `ReturnScalingGuard`
A new utility to be used during return aggregation (`meta.aggregation`).

- **Logic**: Clip all input return series to a physical range.
- **Bounds**:
  - `min_ret = -1.0` (Cannot lose more than 100%).
  - `max_ret = 5.0` (500% daily cap to catch toxic spikes).
- **Implementation**: `series.clip(lower=-1.0, upper=5.0)`.

### 2.2 Post-Flattening Concentration Gate
Ensures the meta-portfolio respects the 25% global asset cap.

1. **Calculate**: $W_{physical} = \sum W_{atoms}$ for each asset.
2. **Check**: If any $W_{physical} > 0.25$:
   - Log a warning.
   - **Optional**: Re-normalize (requires careful handling of LONG/SHORT mix).
3. **Initial Implementation**: Veto/Warning only.

## 3. Forensic Enhancements

### 3.1 Diversity Metrics (Effective N)
Report the "Effective Number of Sleeves" using the inverse Herfindahl-Hirschman Index (HHI).

$$ N_{eff} = \frac{1}{\sum w_i^2} $$

- If $N_{eff} \approx 1$, the meta-portfolio is dominated by a single sleeve.
- If $N_{eff} \approx N$, it is well-diversified.

### 3.2 Contribution Attribution
Update the "Top 10 Assets" table to include contributing sleeves.

| Rank | Symbol | Total Weight | Contributors |
| :--- | :--- | :--- | :--- |
| 1 | `BTC` | 22.0% | `crypto_long`, `crypto_ma` |

## 4. TDD Strategy
- **`tests/test_meta_resilience.py`**:
    - Mock a sleeve with a 600% return and verify clipping.
    - Mock two sleeves each giving `BTC` 15% weight and verify the flattened `BTC` weight is 30% (and flagged).
