# Spec: Pipeline Refactor (Data Pipeline Standard)

## 1. Objective
Modularize the quant pipeline using industry-standard data engineering terminology. Decouple foundational data acquisition and structural analysis (Upstream) from strategy execution and validation (Downstream).

## 2. Pipeline Segments

### Upstream (Discovery & Structural Mapping)
- **`ingest`**: Metadata refresh and global scanners (Crypto, Futures, Forex, Stocks).
- **`prepare-raw`**: Aggregate scanners into a raw candidate pool and perform lightweight (60d) data backfill.
- **`analyze`**: Perform Hierarchical Cluster Analysis (HCA), regime detection, and institutional risk scoring.
- **Artifact**: `portfolio_clusters.json` (The "Candidate Universe" map).

### Downstream (Selection & Strategy Execution)
- **`select`**: Execute Natural Selection (V3) to prune the candidate universe based on `analyze` output.
- **`prepare-final`**: High-integrity alignment (200d+ history) for selected survivors.
- **`optimize`**: Portfolio allocation using dual-sleeve Barbell, HRP, or Max Sharpe engines.
- **`backtest`**: Multi-engine validation tournament.
- **`report`**: Generate unified quantitative reports and sync to Gist.

## 3. Workflow Control
- `make upstream`: Runs `ingest` -> `prepare-raw` -> `analyze`.
- `make downstream`: Runs `select` -> `prepare-final` -> `optimize` -> `backtest` -> `report`.
- `make daily-run`: Executes the full E2E sequence.