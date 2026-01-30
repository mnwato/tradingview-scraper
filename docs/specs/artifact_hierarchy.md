# Specification: Artifact Hierarchy & Navigation (v1)

## 1. Objective
To transition from a flat "dump" directory to a structured, institutional-grade artifact hierarchy. This structure ensures that large-scale quantitative runs are navigable, auditable, and transparent.

## 2. Standard Run Hierarchy

Every production run directory (`artifacts/summaries/runs/<RUN_ID>/`) shall adhere to the following structure:

```text
<RUN_ID>/
├── config/                 # Snapshot of inputs and environment
│   ├── resolved_manifest.json
│   ├── environment.json    # (New) System info, package versions, git hash
│   └── selection_audit.json
├── reports/                # Human-readable markdown summaries
│   ├── selection/          # Universe pruning & discovery audit
│   ├── portfolio/          # Strategy & alpha isolation
│   ├── engine/             # Multi-simulator tournament comparison
│   └── research/           # Clusters, correlations, and factor maps
├── plots/                  # Visual artifacts (PNG/SVG)
│   ├── clustering/
│   └── risk/
├── data/                   # Structured data for downstream tools
│   ├── tournament_results.json
│   ├── returns/            # (Sub-dir) Raw return pickles
│   └── metadata/           # (Sub-dir) JSON objects for clusters and candidates
├── logs/                   # Execution trace (01_cleanup.log, etc.)
├── tearsheets/             # Individual engine/profile reports
│   └── <simulator>/        # Sub-organized by simulator
├── audit.jsonl             # Immutable execution ledger (Rooted)
└── INDEX.md                # (New) Master entry point for the run
```

## 3. Mapping Table (Current -> New)

| Current File | New Path | Role |
| :--- | :--- | :--- |
| `resolved_manifest.json` | `config/resolved_manifest.json` | Input snapshot |
| `selection_audit.json` | `config/selection_audit.json` | Pruning logic snapshot |
| `selection_audit.md` | `reports/selection/audit.md` | Pruning summary |
| `selection_report.md` | `reports/selection/report.md` | Pruning alpha metrics |
| `data_health_raw.md` | `reports/selection/data_health_raw.md` | Ingestion audit |
| `portfolio_report.md` | `reports/portfolio/report.md` | Strategy summary |
| `alpha_isolation_audit.md` | `reports/portfolio/alpha_isolation.md` | Alpha attribution |
| `engine_comparison_report.md`| `reports/engine/comparison.md` | Tournament summary |
| `cluster_analysis.md` | `reports/research/cluster_analysis.md` | Clustering logic |
| `correlation_report.md` | `reports/research/correlations.md` | Multi-asset alignment |
| `*.png` | `plots/` (Sub-categorized) | Visualizations |
| `tournament_results.json` | `data/tournament_results.json` | Master results blob |
| `returns/*.pkl` | `data/returns/` | Backtest series data |
| `*.log` | `logs/` | Execution traces |
| `meta_returns.pkl` | `data/meta_returns.pkl` | (NEW) Multi-sleeve returns |
| `meta_optimized.json` | `data/meta_optimized.json` | (NEW) Sleeve weights |
| `meta_portfolio_report.md` | `reports/portfolio/meta_report.md` | (NEW) Meta-layer summary |

## 4. Navigation & INDEX.md

The `INDEX.md` serves as the institutional cover sheet for the run. It must contain:
1. **Run Status**: Timestamp, Profile, Git Hash.
2. **Top Performer**: The Profile/Engine/Simulator triplet with the highest Sharpe.
3. **Guardrail Dashboard**: Visual indicators (PASS/FAIL) for Metadata Gate, Data Health, and Baseline Invariance.
4. **Artifact Map**: Clickable links to the sub-directories.

## 5. Implementation Standards

1. **Path Resolvers**: `TradingViewScraperSettings` shall expose properties for all standard subdirectories (e.g., `settings.run_reports_dir`).
2. **Atomic Writes**: All writers must ensure parent directories exist before execution.
3. **Audit Ledger**: The ledger remains in the root of the run directory. All file paths recorded in the ledger shall be **relative** to the run directory root to ensure portability.
4. **Symlink Compatibility**: The `artifacts/summaries/latest` symlink shall continue to point to the root of the latest structured run directory.
