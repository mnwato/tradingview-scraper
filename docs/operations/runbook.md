# Operational Runbook

## 1. Daily Production Schedule
The system operates on a 24-hour cycle driven by `cron` or `systemd`.

### 1.1 Data Cycle (00:00 UTC)
**Goal**: Update the Lakehouse with the latest market data and features.
```bash
# Runs Discovery -> Ingestion -> Meta -> Feature
make flow-data RUN_ID=$(date +\%Y\%m\%d)
```

### 1.2 Alpha Cycle (01:00 UTC)
**Goal**: Generate optimized portfolios using the fresh Lakehouse data.
```bash
# Runs Selection -> Optimization -> Reporting
make flow-production PROFILE=production_2026_q1 RUN_ID=$(date +\%Y\%m\%d)
```

### 1.3 Crypto Cycle (02:00 UTC)
**Goal**: Generate high-frequency crypto portfolios.
```bash
make flow-crypto RUN_ID=$(date +\%Y\%m\%d)
```

## 2. Maintenance Tasks

### 2.1 Gap Repair (Weekly)
Scan the Lakehouse for missing candles and force-repair.
```bash
make data-repair
```

### 2.2 Deep Archive (Monthly)
Archive old run artifacts to save space.
```bash
make clean-archive
```

## 3. Troubleshooting

### 3.1 Missing Data in Production
If `flow-production` fails with "Missing data", it means `flow-data` failed or didn't run.
**Fix**:
1. Check `flow-data` logs.
2. Manually run ingestion for the specific profile:
   ```bash
   make scan-run PROFILE=...
   make data-ingest
   ```

### 3.2 Toxic Data Spikes
If backtests show >1000% returns:
1. Run `uv run scripts/audit_data_spikes.py`.
2. Delete corrupted files (`--delete`).
3. Re-run `make data-repair`.
