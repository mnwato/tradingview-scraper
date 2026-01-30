# Sleeve Audit Report: `prod_ma_long_v3` (2026-01-17)

## 1. Finding
The `hrp` profile **IS** correctly generated and persisted for the `prod_ma_long_v3` run.
- **Optimization**: `portfolio_optimized_v2.json` contains `hrp`.
- **Flattening**: `portfolio_flattened.json` contains `hrp`.
- **Backtest**: `data/returns/custom_cvxportfolio_hrp.pkl` exists (size 8503 bytes).

## 2. The Disconnect
If the file exists, why did `build_meta_returns.py` report "HRP returns missing"?

**Hypothesis**: The timestamp of the file.
- The logs showed: `[long_ma] HRP returns missing. Falling back to MinVariance proxy.` at `2026-01-17 13:54:xx`.
- The file timestamp is `Jan 17 03:10`.
- Wait. `13:54` UTC vs `03:10` local?
- Or maybe `build_meta_returns.py` is looking in a different place?
- `build_meta_returns.py` uses `find_latest_run_for_profile` unless `run_id` is explicit.
- In `manifest.json`, `meta_super_benchmark` points to `prod_ma_long_v3`.
- `build_meta_returns.py` resolves this to `artifacts/summaries/runs/prod_ma_long_v3/data/returns/`.

**Investigation**:
Check `scripts/build_meta_returns.py` logic for file matching.
It looks for `f"*_{prof}.pkl"`.
For `prof="hrp"`, it looks for `*_hrp.pkl`.
`custom_cvxportfolio_hrp.pkl` matches.

**Is it possible the re-run fixed it?**
I re-ran `prod_ma_long_v3` optimization/backtest in the *previous turn*.
The `ls -l` shows `Jan 17 03:10`. Current time is assumed to be later.
If I ran `make flow-meta-production` *after* the fix, it should have found it.

**Let's check the logs of the LAST meta run**.
I ran `make flow-meta-production` in the previous turn.
The logs said:
`[long_ma] Found returns: custom_cvxportfolio_hrp.pkl`
**WAIT.** The previous turn logs said:
```
🔨 Building Meta-Matrix for profile: hrp
  [long_ma] Found returns: custom_cvxportfolio_hrp.pkl
```
It **FOUND** it.

So `prod_ma_long_v3` IS fixed.

**What about `barbell`?**
Previous log:
```
🔨 Building Meta-Matrix for profile: barbell
  [long_ma] barbell returns missing. Falling back to min_variance proxy.
```
**Conclusion**: `hrp` is fixed. `barbell` is missing.

## 3. Fixing Barbell
**Reason**: `barbell` is a Meta-Profile in the atomic sleeve (combines HRP + Aggressor).
- `optimize_clustered_v2.py` generates `barbell` weights.
- `flatten_strategy_weights.py` flattens them.
- `backtest_engine.py` needs to simulate them.
- **Root Cause**: `configs/manifest.json` for `binance_spot_rating_ma_long` defines:
  `"profiles": "hrp,min_variance,max_sharpe,equal_weight"`
  **It is MISSING `barbell`**.

## 4. Action Plan
1.  **Update Manifest**: Add `barbell` to the `profiles` list for *all* production profiles (`binance_spot_rating_*`).
2.  **Rerun**: Trigger `port-test` (backtest only) for `prod_ma_long_v3` to generate the missing `barbell` returns. We don't need to re-optimize because optimization *already* ran for barbell (the script defaults to running barbell internally even if not requested? No, the script iterates `[min_variance, hrp, max_sharpe, equal_weight]` AND then explicitly runs `barbell` at the end: `logger.info("Optimizing profile: barbell")`).
    - So `portfolio_optimized_v2.json` HAS barbell.
    - `portfolio_flattened.json` HAS barbell.
    - `backtest_engine` only runs what is passed in `--profiles` or defaults to config.
    - So if config lacks `barbell`, backtest skips it.

**Corrective Action**:
1. Update `manifest.json`.
2. Run `backtest_engine.py` explicitly or via `make port-test` to generate `barbell` pkl.
3. Rerun Meta-Portfolio.
