# Design: Meta-Portfolio Pipeline Hardening (v1)

## 1. Objective
To implement numerical and structural "Guardrails" for fractal meta-portfolio construction, ensuring weight conservation and recursion safety.

## 2. Recursion Safety (Cycle Detection)

### 2.1 Depth Limit
Update `build_meta_returns` and `flatten_weights` to accept a `depth: int = 0` parameter.

- **Rule**: If `depth > 3`, raise `FractalRecursionError`.
- **Rule**: Maintain a `visited: Set[str]` of profile IDs in the call stack to detect circular references.

## 3. Numerical Stability (Stable Sum Gate)

### 3.1 Conservation of Weight
Implement a validator in `flatten_meta_weights.py` that executes after projection:

```python
def validate_weight_conservation(meta_weights: Dict[str, float], physical_weights: List[Dict]):
    expected = sum(meta_weights.values())
    actual = sum(w["Net_Weight"] for w in physical_weights)
    if abs(expected - actual) > 1e-6:
        raise WeightConservationError(f"Weight leakage: {expected} != {actual}")
```

## 4. Aggregation Audit

### 4.1 Alignment Metrics
Update `meta.aggregation` to record the "Intersection Loss" in the audit ledger.
- **Metric**: `days_dropped_pct` (Percentage of dates removed during inner join).
- **Veto**: If `days_dropped_pct > 20%`, issue a warning (indicating low overlap between sleeves).

## 5. Implementation Roadmap
1. Build `MetaHardeningValidator` utility.
2. Refactor recursive calls to pass `depth` and `visited`.
3. Add `ConservationCheck` to the flattening stage.
4. Update `build_meta_returns` to log alignment loss.

## 6. TDD Strategy
- **`tests/test_meta_hardening.py`**:
    - Test circular profile detection.
    - Test weight sum check with a dummy meta-portfolio.
