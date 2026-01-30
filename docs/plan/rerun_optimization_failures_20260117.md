# Remediation Plan: Optimization Failures (2026-01-17)

## 1. Issue
The `long_ma` sleeve (Run ID `prod_ma_long_v3`) and `short_all` sleeve (Run ID `prod_short_all_v3`) failed to generate returns for specific risk profiles:
- `long_ma`: Missing `hrp`, `barbell`, `risk_parity`, `market`, `benchmark`.
- `short_all`: Missing `hrp`.

This necessitated a "Best Effort Proxy" fallback in the Meta-Portfolio aggregator.

## 2. Root Cause Analysis
- **HRP**: Likely failed due to **Numerical Instability**. The "Rating MA Long" universe might be highly correlated (all trending together) or sparse, causing the hierarchical clustering distance matrix to contain NaNs or infinite values.
- **Barbell**: Depends on HRP (Core) + MaxSharpe (Satellite). Failure of HRP cascades to Barbell.
- **Benchmarks**: `market` and `benchmark` profiles likely failed due to insufficient history overlap or data gaps in the specific universe subset selected by `long_ma`.

## 3. Immediate Remediation (Rerun)
We will attempt to re-optimize these specific sleeves with relaxed constraints or simply retry to rule out transient issues.

### 3.1 Rerun `prod_ma_long_v3` Optimization
```bash
export TV_PROFILE=binance_spot_rating_ma_long 
uv run scripts/run_production_pipeline.py --profile binance_spot_rating_ma_long --manifest configs/manifest.json --run-id prod_ma_long_v3 --start-step 11
```

### 3.2 Rerun `prod_short_all_v3` Optimization
```bash
export TV_PROFILE=binance_spot_rating_all_short
uv run scripts/run_production_pipeline.py --profile binance_spot_rating_all_short --manifest configs/manifest.json --run-id prod_short_all_v3 --start-step 11
```

### 3.3 Verify Outputs
Check `data/returns/` in the respective run directories for the missing `.pkl` files.

## 4. Meta-Portfolio Re-Aggregation
Once the base sleeves are repaired, re-run the Meta-Portfolio pipeline to use the genuine profiles instead of proxies.
```bash
make flow-meta-production PROFILE=meta_super_benchmark
```
