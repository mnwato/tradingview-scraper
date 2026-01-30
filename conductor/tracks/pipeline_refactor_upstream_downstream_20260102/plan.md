# Plan: Pipeline Refactor (Standardized Data Pipelines)

## Phase 1: Modular Target Definition
- [ ] **Task**: Define `ingest` target: Handles metadata refresh and universe scanning via `uv run scripts/run_local_scans.sh` (and similar).
- [ ] **Task**: Define `prepare-raw` target: Aggregates raw results into `portfolio_candidates_raw.json` and runs `uv run scripts/prepare_portfolio_data.py` for lightweight mapping.
- [ ] **Task**: Define `analyze` target: Executes `uv run scripts/correlation_report.py` and `uv run scripts/research_regime_v2.py` to map the candidate universe.
- [ ] **Task**: Define `select` target: Prunes the universe into the final portfolio candidates using `uv run scripts/natural_selection.py`.
- [ ] **Task**: Define `prepare-final` target: Performs high-integrity data alignment (200d+) for survivors via `uv run scripts/prepare_portfolio_data.py`.
- [ ] **Task**: Define `optimize` target: Executes `uv run scripts/optimize_clustered_v2.py`.
- [ ] **Task**: Define `backtest` target: Executes `uv run scripts/backtest_engine.py` in tournament mode.
- [ ] **Task**: Define `report` target: Unified reporting and Gist synchronization.

## Phase 2: Pipeline Orchestration
- [ ] **Task**: Group targets into `upstream` (Ingest -> Prepare-Raw -> Analyze).
- [ ] **Task**: Group targets into `downstream` (Select -> Prepare-Final -> Optimize -> Backtest -> Report).
- [ ] **Task**: Refactor `daily-run` to execute `upstream` followed by `downstream`.

## Phase 3: Verification & Integrity
- [ ] **Task**: Run `make upstream` and verify artifact handovers.
- [ ] **Task**: Run `make downstream` and verify portfolio finalization.
- [ ] **Task**: verify full `make daily-run`.
