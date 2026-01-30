# Workflow Configuration Manifest

This directory contains the structured configuration for institutional workflows.

## Files

- **`manifest.json`**: The central multi-profile manifest.
- **`manifest.schema.json`**: JSON Schema for validation and IDE autocompletion.

## Using Profiles

Profiles allow you to switch between different operational modes (e.g., production vs. dev) while ensuring reproducibility.

```bash
# Run with the default 'production' profile
make daily-run

# Run with the 'repro_dev' profile (faster, lightweight)
make daily-run PROFILE=repro_dev

# Run with a custom profile from a custom manifest
make daily-run MANIFEST=configs/my_custom.json PROFILE=research
```

## Manifest Structure

The manifest is organized into logical sections:
- `data`: Scoping for data discovery and prep (lookback, batching).
- `selection`: Natural selection and pruning thresholds.
- `risk`: Hierarchical risk constraints (cluster caps).
- `backtest`: Walk-forward validation windows.
- `tournament`: Multi-engine benchmarking settings.
- `env`: Environment variable overrides (e.g., GIST_ID, META_REFRESH).

## Adding a Profile

1. Open `configs/manifest.json`.
2. Add a new key under `profiles`.
3. Adhere to the `manifest.schema.json` structure.
4. (Optional) Run `uv run python -m tradingview_scraper.settings --export-env` with `TV_PROFILE` to verify loading.

## Reproducibility

To perfectly reproduce a run:
1. Snapshot the specific profile settings into a separate JSON file.
2. Commit the file to the repository.
3. Reference it via `MANIFEST=path/to/snapshot.json PROFILE=name`.
