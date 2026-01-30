# Lakehouse Isolation Policy

## 1. Principles
The `data/lakehouse/` directory is a **Shared Read-Only Resource** for the research and production environment. It MUST NOT be used as a scratchpad for individual runs or transient artifacts.

## 2. Allow List
Only the following file types are permitted in `data/lakehouse/`:

### A. Market Data (Persistent Cache)
- `*_1d.parquet`: OHLCV daily data (e.g., `BINANCE_BTCUSDT_1d.parquet`).
- `*_1h.parquet`: OHLCV hourly data.
- `*_1m.parquet`: OHLCV minute data.

### B. Global Metadata (Catalog)
- `symbols.parquet`: Master symbol universe definitions.
- `exchanges.parquet`: Exchange metadata.
- `execution.parquet`: Execution details (tick size, min lot).

### C. Global Configuration & State
- `candidates_fetch.json`: Input candidate lists for data ingestion.
- `hedge_anchors.json`: Static hedge instrument definitions.
- `combined_symbols.txt`: Legacy symbol list.
- `hpo_feature_cache.parquet`: Shared feature engineering cache (expensive to recompute).
- `optuna_*.db`: Shared hyperparameter optimization history (if configured for persistence).

## 3. Forbidden (Move to Run Directory)
All run-specific outputs must be written to `data/artifacts/summaries/runs/<RUN_ID>/`.

| Forbidden File | Correct Location |
| :--- | :--- |
| `selection_audit.json` | `<RUN_ID>/data/selection_audit.json` |
| `regime_audit.jsonl` | `<RUN_ID>/logs/regime_audit.jsonl` (or `data/logs/`) |
| `portfolio_candidates.json` | `<RUN_ID>/data/portfolio_candidates.json` |
| `returns_matrix.parquet` | `<RUN_ID>/data/returns_matrix.parquet` |
| `portfolio_optimized_v2.json` | `<RUN_ID>/data/portfolio_optimized_v2.json` |
| `meta_*.pkl/json` | `<RUN_ID>/data/meta_*.pkl/json` |
| `orders/*.csv` | `data/artifacts/orders/` |

## 4. Enforcement
Run `make check-isolation` to scan for policy violations.
