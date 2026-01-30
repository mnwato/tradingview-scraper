# Binance Ratings Profiles Rerun Plan (2026-01-16)

## 1. Objective
Rerun full production pipelines for Binance ratings-based profiles to align with Q1 2026 Institutional Standards (Crypto Sleeve Requirements v3.6.1).

## 2. Target Profiles
The following profiles have been updated and are targeted for execution:
1.  `binance_spot_rating_all_long` (Rating All - Long)
2.  `binance_spot_rating_all_short` (Rating All - Short)
3.  `binance_spot_rating_ma_long` (Rating MA - Long)
4.  `binance_spot_rating_ma_short` (Rating MA - Short)

## 3. Configuration Updates
The profiles in `configs/manifest.json` have been hardened with the following "Production Pillars":

| Parameter | Old Value | New Value | Rationale |
| :--- | :--- | :--- | :--- |
| `top_n` | 10 | **15** | Ensure minimum candidate pool (SSP compliance, CR-212) |
| `min_days_floor` | 320 | **90** | Align with Crypto Production standards (CR-114) |
| `entropy_max_threshold` | 0.95 (default) | **0.999** | Allow higher entropy for crypto assets (CR-230) |
| `step_size` | 10 | **10** | Confirmed Regime Alignment (Bi-Weekly) |

## 4. Execution Pipeline
For each profile, the execution sequence is:

### 4.1 Data Operations (`flow-data`)
Executes Discovery (Scanners) -> Ingestion -> Metadata -> Features.
```bash
make flow-data PROFILE=<PROFILE_NAME>
```

### 4.2 Production Lifecycle (`flow-production`)
Executes Selection -> Clustering -> Backtesting (Vectorized Simulators).
```bash
make flow-production PROFILE=<PROFILE_NAME>
```

## 5. Execution Commands

### Batch 1: Rating All (Long/Short)
```bash
# Long
make flow-data PROFILE=binance_spot_rating_all_long
make flow-production PROFILE=binance_spot_rating_all_long

# Short
make flow-data PROFILE=binance_spot_rating_all_short
make flow-production PROFILE=binance_spot_rating_all_short
```

### Batch 2: Rating MA (Long/Short)
```bash
# Long
make flow-data PROFILE=binance_spot_rating_ma_long
make flow-production PROFILE=binance_spot_rating_ma_long

# Short
make flow-data PROFILE=binance_spot_rating_ma_short
make flow-production PROFILE=binance_spot_rating_ma_short
```

## 6. Verification
After execution, verify results in `artifacts/summaries/runs/<RUN_ID>/` and check `audit.jsonl` for:
- `candidate_count >= 15`
- `min_history >= 90`
