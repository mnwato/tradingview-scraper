# Specification: Workflow Configuration Manifests

This document defines the architecture and usage of the JSON-based workflow manifest system, designed to ensure institutional reproducibility and type-safety for multi-asset quantitative pipelines.

## 1. Overview

The manifest system replaces static environment variables and scattered `.env` files with a single, schema-validated JSON configuration. It allows for defining multiple **Profiles** (e.g., `production`, `repro_dev`, `crypto_heavy`) that group all parameters required for a full lifecycle run.

## 2. Profile Aliasing and Hierarchy

To maintain institutional stability while allowing for experimental iterations, the manifest supports a hierarchical profile structure, string-based aliasing, and global defaults.

### 2.1 Standardized Profiles
| Profile Name | Role | Description |
| :--- | :--- | :--- |
| **`production`** | **Alias** | Points to the currently validated institutional snapshot (e.g., `production_2026_q1`). |
| **`canary`** | **Snapshot** | Experimental environment for testing new quantitative features (e.g., Spectral Regimes). |
| **`development`** | **Snapshot** | Optimized for speed and rapid iteration (Short lookback, small universe). |
| **`production_YYYY_QX`** | **Snapshot** | Immutable historical snapshots of audited production settings. |

### 2.2 Global Defaults (`defaults`)
The manifest includes a top-level `defaults` block containing parameters shared by all profiles. Profiles only need to define the "delta" from these defaults.

### 2.3 The 6-Layer Resolution Order (Effective Precedence)
1.  **CLI Flags / Init Settings**: Highest priority tactical overrides passed by CLIs.
2.  **Dotenv Settings**: Values from `.env` treated as environment overrides.
3.  **Environment Variables**: OS-level `TV_` prefixed variables.
4.  **Active Profile**: Profile-specific overrides inside `profiles.<name>` in the manifest.
5.  **Manifest Defaults**: Global baseline under `defaults`.
6.  **Code Defaults**: Safety fallbacks in `TradingViewScraperSettings`.

> Note: The manifest contributes two layers: profile overrides first, then defaults.

### 2.4 CLI -> Env -> Manifest Mapping (Common Knobs)
The platform supports both direct CLI overrides and environment-driven settings. The manifest is the canonical source for profile/default values, and the Makefile bridges those values into env vars for legacy scripts.

| CLI Arg | Env Var | Manifest Key | Notes |
| :--- | :--- | :--- | :--- |
| `--train` | `BACKTEST_TRAIN` | `backtest.train_window` | CLI overrides settings at runtime for tournaments; Makefile maps to `TV_TRAIN_WINDOW` for `--export-env`. |
| `--test` | `BACKTEST_TEST` | `backtest.test_window` | Same precedence as `--train`; Makefile maps to `TV_TEST_WINDOW`. |
| `--step` | `BACKTEST_STEP` | `backtest.step_size` | Same precedence as `--train`; Makefile maps to `TV_STEP_SIZE`. |
| `PROFILE=development` | `TV_PROFILE` | `profiles.development` | Selects the active manifest profile. |
| `MANIFEST=...` | `TV_MANIFEST_PATH` | *(manifest file path)* | Chooses the manifest file. |
| *(n/a)* | `LOOKBACK` | `data.lookback_days` | Used by data prep and health audits; Makefile maps to `TV_LOOKBACK_DAYS`. |
| *(n/a)* | `PORTFOLIO_LOOKBACK_DAYS` | `data.lookback_days` | Explicit portfolio override; falls back to lookback; Makefile maps to `TV_PORTFOLIO_LOOKBACK_DAYS`. |
| *(n/a)* | `BACKTEST_SIMULATOR` / `BACKTEST_SIMULATORS` | `backtest.simulators` | Simulator list for tournaments; Makefile maps to `TV_BACKTEST_SIMULATOR` / `TV_BACKTEST_SIMULATORS`. |
| *(n/a)* | `CLUSTER_CAP` | `risk.cluster_cap` | Overrides risk cluster cap; Makefile maps to `TV_CLUSTER_CAP`. |

> The Makefile uses `python -m tradingview_scraper.settings --export-env` to translate manifest values into env vars for script compatibility.
> Shorthand envs (e.g. `BACKTEST_*`, `LOOKBACK`, `CLUSTER_CAP`) are normalized into `TV_*` variables before export.

## 3. Manifest Schema

The manifest adheres to `configs/manifest.schema.json`. Key sections include:

- **`defaults`**: The secular institutional baseline for all settings.
- **`integrations`**: External service IDs (e.g., Gist IDs).
- **`execution_env`**: Lists mandatory environment variables and secrets.
- **`discovery`**: Composable discovery pipelines using L0-L4 hierarchy.
- **`data`**: Parameters for data discovery, batching, historical lookback, and health gates.
- **`selection`**: Natural selection and pruning thresholds (Top N per cluster).
- **`risk`**: Hierarchical risk constraints (e.g., global cluster weight caps).
- **`backtest`**: Walk-forward validation windows (Train/Test/Step) and simulator settings.
- **`features`**: Gradual rollout feature gates for 2026 Quantitative roadmap features.
- **`sleeves`**: (Optional) Definitions for multi-sleeve meta-portfolios, mapping sub-profiles to sleeve identifiers.

## 4. Usage

### CLI Selection
The active profile can be controlled via the `PROFILE` variable in `make`:

```bash
# Run with the institutional production profile (Default)
make flow-production

# Run with the lightweight development profile
make flow-production PROFILE=development
```

### Custom Manifests
To use an entirely different manifest file:

```bash
make daily-run MANIFEST=configs/research_experiment_v1.json PROFILE=aggressive
```

## 5. Implementation Details

- **Discovery Bridge**: Universe selectors (e.g., `FuturesUniverseSelector`) support loading configurations directly from the active profile. This ensures that market-specific filters (e.g., ADX thresholds, volume minimums) are perfectly reproducible.
- **Pydantic Integration**: The `ManifestSettingsSource` in `tradingview_scraper/settings.py` automatically injects manifest values into the application settings.
- **Makefile Bridge**: The Makefile uses a Python helper (`python -m tradingview_scraper.settings --export-env`) to ingest JSON settings into the shell environment for legacy script support.
- **Validation**: IDEs supporting JSON Schema will automatically provide autocompletion and validation when editing `configs/manifest.json`.

## 6. Institutional Reproducibility Features

### 6.1 Manifest Archiving
Every run automatically snapshots the active `manifest.json` into its run-scoped directory (`artifacts/summaries/runs/<RUN_ID>/manifest.json`). This ensures that every implemented portfolio is accompanied by its full historical configuration context.

### 6.1.1 Audit Ledger Defaults (Recommended)
The institutional default manifest (`configs/manifest.json`) enables `features.feat_audit_ledger` by default so that every run produces an `audit.jsonl` decision trail suitable for strict tournament gating and reproducibility audits.

- **Default**: `features.feat_audit_ledger: true` (via `defaults.features`)
- **Override (local-only)**: set `TV_FEATURES__FEAT_AUDIT_LEDGER=0` to disable audit writes for perf/debug runs

### 6.2 Target Row Enforcement
The system uses `PORTFOLIO_MIN_DAYS_FLOOR` to ensure that only assets with sufficient history (e.g., 320 days for a 500-day lookback) are allowed into the implementation universe, guaranteeing the integrity of long-duration backtests.

### 6.3 Hard Health Gates
In `production` mode (`strict_health: true`), the pipeline will fail-fast if any selected symbols have unresolved data gaps after the automated recovery phase, preventing capital allocation on degraded data.

### 6.4 Metadata Coverage Gate (Pre-Selection & Pre-Tournament)
Selection and tournament vetoes rely on candidate manifest metadata (not `portfolio_meta*.json`), so metadata enrichment is a hard prerequisite:
- **Required fields**: `tick_size`, `lot_size`, `price_precision`
- **When**: Immediately after `data-prep-raw` and after `port-select`
- **Enrichment command**: `uv run scripts/enrich_candidates_metadata.py`
- **Gate**: Fail the run if metadata coverage drops below a defined threshold (recommended ≥95% of active symbols)
- **Automated guard**: `scripts/metadata_coverage_guardrail.py` is now run by `make data-prep-raw` (canonical) and `make port-select` (selected); it reruns `enrich_candidates_metadata.py` when coverage dips, logs the percentage for each catalog, and fails the pipeline if the threshold cannot be reached.

### 6.5 Optional Automation (Recommended)
To reduce operator error, add dedicated workflow steps/targets:
- `make metadata-refresh`: run `scripts/enrich_candidates_metadata.py` after candidate generation
- `make metadata-audit`: assert coverage for required fields and fail fast below threshold
- `make invariance-check`: run matched tournaments with the same universe source across selection modes and compare summaries

### 6.6 Baseline Readiness Gate (Pre-Tournament)
To ensure a **solid benchmark baseline** for backtesting risk profiles, enforce the following checks before tournament runs:
- **Benchmark symbols present**: `settings.benchmark_symbols` must exist in the returns matrix; otherwise the `market` baseline is empty by design.
- **`benchmark` baseline availability**: The active universe must have sufficient coverage to produce equal-weight weights for the full window.
- **`raw_pool_ew` invariance**: If enabled, `raw_pool_ew` must be selection-mode invariant for the **same universe source** (canonical or selected). Log a warning or fail if drift is detected.

Suggested automation targets:
- `make baseline-audit`: validate `market` + `benchmark` availability and report coverage
- `make flow-binance-spot-rating-all-ls`: run both Binance Spot Rating ALL long/short atomic pipelines + audits
- `make baseline-guardrail`: compare `raw_pool_ew` summaries across selection modes for the same universe source
- `make atomic-validate RUN_ID=<RUN_ID> PROFILE=<PROFILE>`: validate a single sleeve run against the atomic artifact contract
- `make atomic-audit RUN_ID=<RUN_ID> PROFILE=<PROFILE>`: run sign test + atomic validation (writes `*_audit.json` artifacts)

## 7. Schema Reference

### Selection Settings
| Field | Type | Description |
| :--- | :--- | :--- |
| `top_n` | int | Maximum number of assets to select. |
| `threshold` | float | Minimum alpha score required for selection. |
| `selection_mode` | str | Engine version (`v3.2`, `v3.4`, `v4`). |
| `ranking.method` | str | Metric to sort by (default: `alpha_score`). |
| `ranking.direction` | str | Sort order: `descending` (High Score) or `ascending` (Low Score). |

### Feature Flags (Partial List)
| Field | Type | Description |
| :--- | :--- | :--- |
| `dominant_signal` | str | Signal to prioritize in Log-MPS (e.g., `recommend_ma`). |
| `dominant_signal_weight` | float | Weight multiplier for dominant signal (Default: 3.0). |
| `feat_directional_sign_test_gate` | bool | Meta-only: if enabled, `run_meta_pipeline.py` runs the Directional Correction Sign Test and fails fast on violations; persists `directional_sign_test.json` in the meta run directory. |
| `feat_directional_sign_test_gate_atomic` | bool | Atomic-only: if enabled, `run_production_pipeline.py` runs the Directional Correction Sign Test as a fail-fast gate (after synthesis and again post-optimization) and persists JSON artifacts in the sleeve run directory. |
