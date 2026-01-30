# TradingView Scraper
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![MIT License](https://img.shields.io/github/license/mnwato/tradingview-scraper.svg?color=brightgreen)](https://opensource.org/licenses/MIT)

This is an institutional-grade Python framework for multi-asset quantitative portfolio management, built on top of real-time TradingView data scraping. It provides a full-lifecycle pipeline from discovery and risk optimization to high-fidelity backtesting and reporting.

## Key Capabilities

*   **13-Step Production Lifecycle**: Fully automated pipeline covering discovery, tiered pruning, 500-day secular backfill, and de-risked allocation.
*   **Convex Risk Engine (V2)**: Optimization utilizing **cvxpy** with institutional solvers (ECOS/OSQP) and strictly enforced hierarchical cluster caps (25%).
*   **3D Tournament Matrix**: Side-by-side benchmarking of 5 optimization engines (`skfolio`, `Riskfolio-Lib`, `PyPortfolioOpt`, `cvxportfolio`, and `custom`) across idealized and high-fidelity simulators.
*   **High-Fidelity Simulation**: Professional friction modeling (5bps slippage, 1bp commission) via integrated **CVXPortfolio** simulator.
*   **Self-Healing Data Layer**: Automated gap detection, high-intensity repair (`make recover`), and 500-day secular history management.
*   **Markdown Tear-sheets**: Automated generation of strategy performance teardowns (Monthly returns, Drawdown audits) using **QuantStats**.
*   **Market Baseline Engine**: Dedicated engine for Buy & Hold benchmarking, treated as a first-class strategy within the validation matrix.
*   **Decision Trail Audit**: Full post-mortem logs documenting every universe pruning and allocation choice.
*   **Reproducible Manifests**: Workflow profiles defined in schema-validated `configs/manifest.json` for consistent institutional operation.
*   **Live Output Example**: [Institutional Portfolio Implementation Gist](https://gist.github.com/tommy-ca/e888e1eab0b86447c90c26e92ec4dc36)

## Installation

To get started with the TradingView Scraper library, follow these steps:

1. **Install with uv** (recommended):
   ```sh
   # Install uv (if not already installed)
   curl -LsSf https://astral-sh.uv.io/install.sh | sh
   
   # Synchronize environment with all core and optional backends
   uv sync --all-extras
   ```

2. **Run commands with uv**:
   ```sh
   # Run the production pipeline
   uv run python -m scripts.run_production_pipeline --profile production
   
   # Run tests
   uv run pytest
   ```

## Automated Daily Pipeline

The entire production lifecycle is controlled via the `Makefile` and `configs/manifest.json`:

```bash
# Run the institutional production pipeline (Default)
make daily-run

# Run a lightweight development test (fast validation)
make daily-run PROFILE=development

# Run the 3D benchmarking tournament matrix only
make tournament
```

## Available Workflows

| Command | Purpose |
| :--- | :--- |
| `make daily-run` | Standard production entry point. |
| `make tournament` | Run benchmarking matrix (Engine x Simulator x Profile). |
| `make recover` | High-intensity gap repair for degraded assets. |
| `make audit` | Verify logic constraints (Caps, Net Exposure, Weights). |
| `make gist` | Synchronize essential artifacts to private implementation Gist. |

## Research & Documentation

- [Multi-Engine Optimization Benchmarks](docs/specs/multi_engine_optimization_benchmarks.md)
- [Backtest Engine V2 Framework](docs/specs/backtest_framework_v2.md)
- [Workflow Configuration Manifests](docs/specs/workflow_manifests.md)
- [Production Workflow Runbook](docs/production_workflow.md)
- [Portfolio Engine Audit Report (Dec 2025)](docs/research/portfolio_engine_audit_20251230.md)

## License
MIT
