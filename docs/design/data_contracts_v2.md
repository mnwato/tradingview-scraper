# Design: Advanced Data Contract Enforcement (v2)

## 1. Objective
To implement formal, declarative data contracts using Pandera to ensure the numerical integrity of L0-L4 data artifacts throughout the pipeline lifecycle.

## 2. L0-L4 Schema Hierarchy

| Layer | Artifact | Contractual Invariants |
| :--- | :--- | :--- |
| **L0** | `returns_matrix` | No missing values (ffill'd), $|r| \le 1.0$, DatetimeIndex. |
| **L1** | `features_matrix` | Column-level type enforcement, PIT-consistency. |
| **L3** | `synthetic_returns` | Inverted short streams, no logic suffixes. |
| **L4** | `portfolio_weights` | Simplex constraint ($\sum |w| = 1$), non-negative weights for LONG logic. |

## 3. Pandera Integration

### 3.1 Schema Definitions
Schema models will be centralized in `tradingview_scraper/pipelines/contracts.py`.

```python
import pandera as pa

ReturnsSchema = pa.DataFrameSchema({
    "*": pa.Column(float, checks=[
        pa.Check.greater_than_or_equal_to(-1.0),
        pa.Check.less_than_or_equal_to(1.0)
    ])
}, index=pa.Index(pa.DateTime))
```

### 3.2 Validation Checkpoints
Validation will be injected at:
1.  **Foundation Gate**: Pre-flight audit of Lakehouse Parquets.
2.  **Synthesis**: Post-transformation check of the synthetic matrix.
3.  **Optimization**: Pre-solver check of the risk parameters.

## 4. TDD Strategy
- **`tests/test_pandera_contracts.py`**:
    - Verify that `ReturnsSchema.validate()` raises `pa.errors.SchemaError` for toxic data.
    - Verify that `WeightsSchema` detects weight leakage $> 10^{-4}$.

## 5. Implementation Roadmap
1. Create `tradingview_scraper/pipelines/contracts.py`.
2. Implement schema decorators or explicit `validate()` calls in `IngestionValidator`.
3. Update `QuantSDK.run_stage` to optionally enforce input/output contracts based on stage metadata.
