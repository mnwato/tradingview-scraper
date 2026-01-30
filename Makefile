SHELL := /bin/bash
PY ?= uv run

# Workflow Manifest (JSON)
MANIFEST ?= configs/manifest.json
PROFILE ?= $(or $(TV_PROFILE),production)
export PROFILE
export TV_PROFILE := $(PROFILE)

# Bridge JSON Manifest to Shell Environment

ifneq ($(wildcard $(MANIFEST)),)
ENV_OVERRIDES := \
	$(if $(LOOKBACK),TV_LOOKBACK_DAYS=$(LOOKBACK)) \
	$(if $(PORTFOLIO_LOOKBACK_DAYS),TV_PORTFOLIO_LOOKBACK_DAYS=$(PORTFOLIO_LOOKBACK_DAYS)) \
	$(if $(BACKTEST_TRAIN),TV_TRAIN_WINDOW=$(BACKTEST_TRAIN)) \
	$(if $(BACKTEST_TEST),TV_TEST_WINDOW=$(BACKTEST_TEST)) \
	$(if $(BACKTEST_STEP),TV_STEP_SIZE=$(BACKTEST_STEP)) \
	$(if $(BACKTEST_SIMULATOR),TV_BACKTEST_SIMULATOR=$(BACKTEST_SIMULATOR)) \
	$(if $(BACKTEST_SIMULATORS),TV_BACKTEST_SIMULATORS=$(BACKTEST_SIMULATORS)) \
	$(if $(CLUSTER_CAP),TV_CLUSTER_CAP=$(CLUSTER_CAP)) \
	$(if $(SELECTION_MODE),TV_FEATURES__SELECTION_MODE=$(SELECTION_MODE)) \
	$(if $(MIN_DAYS_FLOOR),TV_MIN_DAYS_FLOOR=$(MIN_DAYS_FLOOR))
ENV_VARS = $(shell TV_MANIFEST_PATH=$(MANIFEST) TV_PROFILE=$(PROFILE) $(ENV_OVERRIDES) $(PY) -m tradingview_scraper.settings --export-env | sed 's/export //')
$(foreach var,$(ENV_VARS),$(eval $(var)))
$(foreach var,$(ENV_VARS),$(eval export $(shell echo "$(var)" | cut -d= -f1)))

# Promote institutional (non-TV_) env var names to TV_-prefixed equivalents so
# `get_settings()` consumers see Make/manifest overrides.
#
# - The settings model uses `env_prefix="TV_"`.
# - `--export-env` intentionally prints human-friendly/institutional var names.
# - Without this promotion, `make ... BACKTEST_TRAIN=...` updates the exported
#   `BACKTEST_*` vars but not `TV_*`, so window overrides won't take effect.
ifeq ($(origin TV_LOOKBACK_DAYS), undefined)
export TV_LOOKBACK_DAYS := $(LOOKBACK)
endif
ifeq ($(origin TV_PORTFOLIO_LOOKBACK_DAYS), undefined)
export TV_PORTFOLIO_LOOKBACK_DAYS := $(PORTFOLIO_LOOKBACK_DAYS)
endif
ifeq ($(origin TV_TRAIN_WINDOW), undefined)
export TV_TRAIN_WINDOW := $(BACKTEST_TRAIN)
endif
ifeq ($(origin TV_TEST_WINDOW), undefined)
export TV_TEST_WINDOW := $(BACKTEST_TEST)
endif
ifeq ($(origin TV_STEP_SIZE), undefined)
export TV_STEP_SIZE := $(BACKTEST_STEP)
endif
ifeq ($(origin TV_BACKTEST_SIMULATOR), undefined)
export TV_BACKTEST_SIMULATOR := $(BACKTEST_SIMULATOR)
endif
ifeq ($(origin TV_BACKTEST_SIMULATORS), undefined)
export TV_BACKTEST_SIMULATORS := $(BACKTEST_SIMULATORS)
endif
ifeq ($(origin TV_CLUSTER_CAP), undefined)
export TV_CLUSTER_CAP := $(CLUSTER_CAP)
endif
ifeq ($(origin TV_RAW_POOL_UNIVERSE), undefined)
export TV_RAW_POOL_UNIVERSE := $(RAW_POOL_UNIVERSE)
endif
ifeq ($(origin TV_FEATURES__SELECTION_MODE), undefined)
export TV_FEATURES__SELECTION_MODE := $(SELECTION_MODE)
endif
ifeq ($(origin TV_THRESHOLD), undefined)
export TV_THRESHOLD := $(THRESHOLD)
endif
ifeq ($(origin TV_TOP_N), undefined)
export TV_TOP_N := $(TOP_N)
endif
ifeq ($(origin TV_MIN_MOMENTUM_SCORE), undefined)
export TV_MIN_MOMENTUM_SCORE := $(MIN_MOMENTUM_SCORE)
endif
ifeq ($(origin TV_MIN_DAYS_FLOOR), undefined)
ifneq ($(PORTFOLIO_MIN_DAYS_FLOOR),)
export TV_MIN_DAYS_FLOOR := $(PORTFOLIO_MIN_DAYS_FLOOR)
else
export TV_MIN_DAYS_FLOOR := $(MIN_DAYS_FLOOR)
endif
endif
endif

# Paths (Phase 540: Workspace Isolation)
LAKEHOUSE ?= $(or $(TV_LAKEHOUSE_DIR),data/lakehouse)
ARTIFACTS_DIR ?= $(or $(TV_ARTIFACTS_DIR),data/artifacts)
SUMMARIES_ROOT ?= $(ARTIFACTS_DIR)/summaries
SUMMARY_DIR ?= $(SUMMARIES_ROOT)/latest
SUMMARY_RUN_DIR ?= $(SUMMARIES_ROOT)/runs/$(TV_RUN_ID)
META_CATALOG_PATH ?= $(LAKEHOUSE)/symbols.parquet
TARGETED_CANDIDATES ?= $(LAKEHOUSE)/portfolio_candidates_targeted.json
TARGETED_LOOKBACK ?= 200
TARGETED_BATCH ?= 2

# Run ID Logic
ifneq ($(origin TV_RUN_ID), undefined)
RUN_ID := $(TV_RUN_ID)
else ifneq ($(origin TV_EXPORT_RUN_ID), undefined)
RUN_ID := $(TV_EXPORT_RUN_ID)
else ifeq ($(origin RUN_ID), undefined)
RUN_ID := $(shell date +%Y%m%d-%H%M%S)
endif

export RUN_ID
export TV_RUN_ID := $(RUN_ID)
export TV_EXPORT_RUN_ID := $(RUN_ID)

# Run workspace paths
RUN_DATA_DIR ?= $(SUMMARIES_ROOT)/runs/$(RUN_ID)/data

# Artifacts
CANDIDATES_RAW := $(RUN_DATA_DIR)/portfolio_candidates_raw.json
CANDIDATES_SELECTED := $(RUN_DATA_DIR)/portfolio_candidates.json
RETURNS_MATRIX := $(RUN_DATA_DIR)/returns_matrix.parquet
PORTFOLIO_META := $(RUN_DATA_DIR)/portfolio_meta.json
SELECTION_AUDIT := $(RUN_DATA_DIR)/selection_audit.json
CLUSTERS_FILE := $(RUN_DATA_DIR)/portfolio_clusters.json

# Environment promotion
export CANDIDATES_RAW
export CANDIDATES_SELECTED
export RETURNS_MATRIX
export PORTFOLIO_META
export SELECTION_AUDIT
export CLUSTERS_FILE
export LAKEHOUSE_DIR := $(LAKEHOUSE)

data-prep-raw: ## Aggregate scans and initialize raw pool (Read-Only from Lakehouse)
	$(PY) scripts/select_top_universe.py --mode raw
	CANDIDATES_FILE=$(CANDIDATES_RAW) PORTFOLIO_RETURNS_PATH=$(RETURNS_MATRIX) PORTFOLIO_META_PATH=$(PORTFOLIO_META) PORTFOLIO_DATA_SOURCE=lakehouse_only $(PY) scripts/prepare_portfolio_data.py
	$(PY) scripts/metadata_coverage_guardrail.py --target canonical:$(CANDIDATES_RAW):$(RETURNS_MATRIX)

port-foundation-gate: ## [Alpha] Lightweight validation of the foundation matrix (L0)
	$(PY) scripts/validate_portfolio_artifacts.py --mode foundation --only-health

port-select: ## Natural selection and pruning
	$(PY) scripts/natural_selection.py
	$(PY) scripts/metadata_coverage_guardrail.py --target selected:$(CANDIDATES_SELECTED):$(RETURNS_MATRIX)


port-optimize: ## Strategic asset allocation (Convex)
	$(PY) scripts/optimize_clustered_v2.py

port-test: ## Execute 3D benchmarking tournament
	@echo ">>> Running Multi-Engine Tournament Mode..."
	$(PY) scripts/backtest_engine.py --mode research

port-drift: ## Monitor portfolio drift vs last implemented state
	$(PY) scripts/maintenance/track_portfolio_state.py

port-shadow-fill: ## Simulate paper execution (Shadow Loop) to reconcile drift
	$(PY) scripts/maintenance/shadow_loop_sim.py

port-pre-opt: ## [Fast] Critical pre-optimization analysis (Regime, Clusters, Stats)
	$(PY) scripts/correlation_report.py --hrp
	$(PY) scripts/audit_antifragility.py
	$(PY) scripts/research_regime_v3.py

port-post-analysis: ## [Slow] Deep dive analysis and visualizations (Optional)
	$(PY) scripts/analyze_clusters.py
	$(PY) scripts/visualize_factor_map.py
	$(PY) scripts/detect_hedge_anchors.py
	$(PY) scripts/monitor_cluster_drift.py

port-analyze: ## Full analysis suite (Pre + Post)
	$(MAKE) port-pre-opt
	$(MAKE) port-post-analysis

research-persistence: ## Analyze trend/MR persistence (Requires LOOKBACK=500)
	$(PY) scripts/research/analyze_persistence.py

# --- REPORT Namespace ---
port-report: ## Generate unified quant reports and tear-sheets
	$(PY) scripts/generate_reports.py
	$(PY) scripts/generate_portfolio_report.py
	$(PY) scripts/generate_audit_summary.py

port-deep-audit: ## Generate deep forensic report (Run ID required)
	$(PY) scripts/production/generate_deep_report.py $(RUN_ID)

tournament-scoreboard: ## Generate tournament scoreboard (latest run)
	$(PY) scripts/research/tournament_scoreboard.py --run-id latest

tournament-scoreboard-run: ## Generate tournament scoreboard for RUN_ID
	$(PY) scripts/research/tournament_scoreboard.py --run-id $(RUN_ID)

baseline-audit: ## Validate baseline availability (market/benchmark/raw_pool_ew)
	@STRICT_ARG=""; if [ "$(STRICT_BASELINE)" = "1" ] || [ "$(TV_STRICT_BASELINE)" = "1" ]; then STRICT_ARG="--strict"; fi; \
	RAW_ARG=""; if [ "$(REQUIRE_RAW_POOL)" = "1" ] || [ "$(TV_REQUIRE_RAW_POOL)" = "1" ]; then RAW_ARG="--require-raw-pool"; fi; \
	$(PY) scripts/baseline_audit.py --run-id $(RUN_ID) $$STRICT_ARG $$RAW_ARG

baseline-guardrail: ## Compare raw_pool_ew invariance across two runs (RUN_A, RUN_B)
	@if [ -z "$(RUN_A)" ] || [ -z "$(RUN_B)" ]; then \
		echo "Set RUN_A and RUN_B to run IDs for invariance check."; \
		exit 1; \
	fi
	$(PY) scripts/raw_pool_invariance_guardrail.py --run-a $(RUN_A) --run-b $(RUN_B)

atomic-validate: ## Validate an atomic sleeve run (RUN_ID + PROFILE required)
	@if [ -z "$(RUN_ID)" ] || [ -z "$(PROFILE)" ]; then \
		echo "Set RUN_ID and PROFILE (e.g. RUN_ID=20260118-161253 PROFILE=binance_spot_rating_all_long)."; \
		exit 1; \
	fi
	$(PY) python scripts/validate_atomic_run.py --run-id $(RUN_ID) --profile $(PROFILE) --manifest-path $(MANIFEST)

atomic-audit: ## Audit an atomic sleeve run (sign test + atomic validation) (RUN_ID + PROFILE required)
	@if [ -z "$(RUN_ID)" ] || [ -z "$(PROFILE)" ]; then \
		echo "Set RUN_ID and PROFILE (e.g. RUN_ID=20260118-161253 PROFILE=binance_spot_rating_all_long)."; \
		exit 1; \
	fi
	$(PY) python scripts/run_atomic_audit.py --run-id $(RUN_ID) --profile $(PROFILE) --manifest-path $(MANIFEST)

report-sync: ## Synchronize artifacts to private Gist
	@echo ">>> Preparing Gist Payload..."
	@rm -rf data/artifacts/gist_payload && mkdir -p data/artifacts/gist_payload
	@cp $(MANIFEST) data/artifacts/gist_payload/run_manifest.json 2>/dev/null || true
	@find -L data/artifacts/summaries/latest -maxdepth 1 -name "*.md" -exec cp {} data/artifacts/gist_payload/ \;
	@find -L data/artifacts/summaries/latest -maxdepth 1 -name "*.png" -exec cp {} data/artifacts/gist_payload/ \;
	@find -L data/artifacts/summaries/latest -maxdepth 1 -name "*.json" -exec cp {} data/artifacts/gist_payload/ \;
	@SUMMARY_DIR=data/artifacts/gist_payload GIST_ID=$(GIST_ID) bash scripts/push_summaries_to_gist.sh

# --- ENV Namespace ---
env-sync: ## Synchronize dependencies using uv
	uv sync --all-extras

env-check: ## Validate manifest and configuration integrity
	$(PY) scripts/validate_manifest.py

# --- TEST Namespace ---
test-parity: ## Run Nautilus parity validation gate
	$(PY) scripts/validate_parity.py

grand-tournament: ## Run multi-dimensional Grand Tournament (Production Mode)
	$(PY) scripts/grand_tournament.py --profile $(PROFILE) --selection-modes "v3.2,v2.1" --mode production

grand-4d: ## Run deep research sweep (Research Mode)
	$(PY) scripts/grand_tournament.py --profile $(PROFILE) --selection-modes "v3.2,v2.1" --rebalance-modes "window,daily" --mode research

live-shadow: ## Run Nautilus in SHADOW mode (Read-only real-time)
	$(PY) scripts/live/run_nautilus_shadow.py --profile $(PROFILE)

smoke-test-nautilus: ## End-to-End Nautilus Parity Smoke Test
	@echo ">>> STAGE: NAUTILUS SMOKE TEST"
	$(MAKE) clean-run
	$(MAKE) flow-production PROFILE=nautilus_parity
	$(MAKE) test-parity

# --- SCAN Namespace ---
scan-run: ## Execute composable discovery scanners
	@echo ">>> STAGE: DISCOVERY (Composable Pipelines)"
	TV_EXPORT_RUN_ID=$(RUN_ID) $(PY) scripts/compose_pipeline.py --profile $(PROFILE)

scan-audit: ## Lint scanner configurations
	$(PY) scripts/lint_universe_configs.py --configs-dir configs

crypto-scan-audit: ## Validate crypto scanner configurations
	$(PY) scripts/lint_universe_configs.py --path configs/scanners/crypto/
	$(PY) scripts/lint_universe_configs.py --path 'configs/base/universes/binance*.yaml'
	$(PY) scripts/lint_universe_configs.py --path 'configs/base/templates/crypto*.yaml'

# --- DATA Namespace ---
data-audit: ## [DataOps] Session-Aware health check of the active candidates (Scoped)
	@echo ">>> Auditing Lakehouse Foundation Health..."
	@CAND_PATH="data/lakehouse/portfolio_candidates.json"; \
	if [ -n "$(RUN_ID)" ] && [ -f "data/export/$(RUN_ID)/candidates_validated.json" ]; then \
		CAND_PATH="data/export/$(RUN_ID)/candidates_validated.json"; \
	elif [ -n "$(TV_EXPORT_RUN_ID)" ] && [ -f "data/export/$(TV_EXPORT_RUN_ID)/candidates_validated.json" ]; then \
		CAND_PATH="data/export/$(TV_EXPORT_RUN_ID)/candidates_validated.json"; \
	fi; \
	echo ">>> Auditing Scope: $$CAND_PATH"; \
	CANDIDATES_RAW=$$CAND_PATH \
	$(PY) scripts/validate_portfolio_artifacts.py --mode raw --strict

data-repair: ## [DataOps] High-intensity gap repair for degraded assets (Scoped)
	@CAND_PATH=""; \
	if [ -n "$(RUN_ID)" ] && [ -f "data/export/$(RUN_ID)/candidates.json" ]; then \
		CAND_PATH="data/export/$(RUN_ID)/candidates.json"; \
	elif [ -n "$(TV_EXPORT_RUN_ID)" ] && [ -f "data/export/$(TV_EXPORT_RUN_ID)/candidates.json" ]; then \
		CAND_PATH="data/export/$(TV_EXPORT_RUN_ID)/candidates.json"; \
	fi; \
	if [ -z "$$CAND_PATH" ]; then \
		echo ">>> WARNING: No scoped candidates found for repair. Skipping global repair."; \
	else \
		echo ">>> Repairing candidates: $$CAND_PATH"; \
		$(PY) scripts/services/repair_data.py --max-fills 15 --candidates $$CAND_PATH; \
	fi

flow-data: ## [DataOps] Full Data Cycle: Discovery -> Ingestion -> Repair -> Audit -> Meta -> Features -> Lakehouse
	$(MAKE) scan-run
	sleep 10
	$(MAKE) data-ingest
	sleep 5
	$(MAKE) data-repair
	sleep 5
	$(MAKE) data-audit
	sleep 5
	$(MAKE) meta-ingest CANDIDATES_FILE=$(CANDIDATES_SELECTED)
	sleep 5
	$(MAKE) feature-ingest
	sleep 5
	$(MAKE) feature-backfill

data-ingest: ## [DataOps] Ingest data for all candidates generated by scans
	@echo ">>> Ingesting data for candidate lists in data/export/$(RUN_ID)..."
	@# Find all candidate files from the scan run and execute in parallel (max 8 processes)
	@find data/export/$(RUN_ID) -name "candidates.json" -print0 | xargs -0 -P 2 -I {} $(PY) scripts/services/ingest_data.py --candidates "{}"
	@echo ">>> Consolidating and Enriching candidates..."
	$(PY) scripts/services/consolidate_candidates.py --run-id $(RUN_ID) --output $(CANDIDATES_SELECTED)
	$(PY) scripts/enrich_candidates_metadata.py --candidates $(CANDIDATES_SELECTED)

meta-ingest: ## [DataOps] Refresh global metadata catalogs (Structural + Execution)
	@echo ">>> Ingesting Metadata (TradingView + CCXT)..."
	@if [ -n "$(CANDIDATES_FILE)" ] && [ -f "$(CANDIDATES_FILE)" ]; then \
		echo ">>> Scoped Metadata Refresh: $(CANDIDATES_FILE)"; \
		$(PY) scripts/build_metadata_catalog.py --candidates-file $(CANDIDATES_FILE); \
	else \
		echo ">>> Global Metadata Refresh (Full Catalog)"; \
		$(PY) scripts/build_metadata_catalog.py --from-catalog; \
	fi
	$(PY) scripts/fetch_execution_metadata.py --candidates $(CANDIDATES_SELECTED)

feature-ingest: ## [DataOps] Ingest TradingView Technicals for current candidates
	@echo ">>> Ingesting Technical Features..."
	@# Find all candidate files and execute feature ingestion in parallel (max 8 processes)
	@find data/export/$(RUN_ID) -name "*.json" -print0 | xargs -0 -P 2 -I {} $(PY) scripts/services/ingest_features.py --candidates "{}"

feature-backfill: ## [DataOps] Backfill historical technical ratings for dynamic backtesting
	@echo ">>> Backfilling Historical Features (Point-in-Time)..."
	@# CR-890: Scoped Backfill Isolation. Default to run-specific candidates if RUN_ID/EXPORT_RUN_ID is set.
	@CAND_PATH=""; \
	if [ -n "$(RUN_ID)" ] && [ -f "data/export/$(RUN_ID)/candidates_validated.json" ]; then \
		CAND_PATH="data/export/$(RUN_ID)/candidates_validated.json"; \
	elif [ -n "$(TV_EXPORT_RUN_ID)" ] && [ -f "data/export/$(TV_EXPORT_RUN_ID)/candidates_validated.json" ]; then \
		CAND_PATH="data/export/$(TV_EXPORT_RUN_ID)/candidates_validated.json"; \
	elif [ "$(FORCE_GLOBAL_BACKFILL)" = "1" ]; then \
		CAND_PATH="data/lakehouse/portfolio_candidates.json"; \
	fi; \
	if [ -z "$$CAND_PATH" ]; then \
		echo ">>> ERROR: No run-specific candidates found. Global backfill is forbidden by default."; \
		echo ">>> Set FORCE_GLOBAL_BACKFILL=1 or provide RUN_ID."; \
		exit 1; \
	fi; \
	echo ">>> Using candidates: $$CAND_PATH"; \
	$(PY) scripts/services/backfill_features.py \
		--candidates $$CAND_PATH \
		--output data/lakehouse/features_matrix.parquet \
		--lakehouse data/lakehouse \
		--strict-scope

# --- FLOW Namespace ---
flow-production: ## Full institutional production lifecycle (Alpha Cycle Only - Requires flow-data)
	$(PY) python -m scripts.run_production_pipeline --profile $(PROFILE) --manifest $(MANIFEST) --run-id $(TV_RUN_ID)

flow-crypto: ## Full crypto-only production run (BINANCE-only)
	$(MAKE) flow-production PROFILE=crypto_production

flow-prelive: ## Production pre-live workflow (including slow Nautilus simulator)
	$(MAKE) flow-production BACKTEST_SIMULATORS=custom,cvxportfolio,vectorbt,nautilus

flow-dev: ## Rapid iteration development execution
	$(MAKE) flow-production PROFILE=development

flow-binance-spot-rating-all-ls: ## Run Binance Spot Rating ALL long+short atomic pipelines + audits
	@echo ">>> Preconditions: run \"make flow-data\" first for fresh lakehouse inputs."
	@ts=$$(date +%Y%m%d-%H%M%S); \
	run_long=binance_spot_rating_all_long_$${ts}; \
	run_short=binance_spot_rating_all_short_$${ts}; \
	echo ">>> RUN_LONG=$$run_long"; \
	echo ">>> RUN_SHORT=$$run_short"; \
	TV_RUN_ID=$$run_long $(MAKE) flow-production PROFILE=binance_spot_rating_all_long; \
	TV_RUN_ID=$$run_short $(MAKE) flow-production PROFILE=binance_spot_rating_all_short; \
	$(MAKE) atomic-audit RUN_ID=$$run_long PROFILE=binance_spot_rating_all_long; \
	$(MAKE) atomic-audit RUN_ID=$$run_short PROFILE=binance_spot_rating_all_short

flow-meta-production: ## Run multi-sleeve meta-portfolio flow (Streamlined Fractal Tree)
	@echo ">>> STAGE: META-PORTFOLIO PIPELINE (Fractal Matrix)"
	$(PY) scripts/run_meta_pipeline.py --profile $(PROFILE)


# --- CLEAN Namespace ---
clean-run: ## Wipe current run artifacts
	rm -f summaries
	# Preserved Lakehouse Master Files: portfolio_candidates.json, foundation_health.json
	rm -f data/lakehouse/portfolio_meta.json
	rm -f data/lakehouse/portfolio_clusters*.json data/lakehouse/portfolio_optimized_v2.json
	rm -f data/lakehouse/antifragility_stats.json data/lakehouse/selection_audit.json data/lakehouse/cluster_drift.json data/lakehouse/tmp_bt_*
	rm -f data/lakehouse/meta_manifest_*.json data/lakehouse/meta_returns_*.pkl data/lakehouse/meta_optimized_*.json
	rm -f data/lakehouse/meta_cluster_tree_*.json data/lakehouse/portfolio_optimized_meta_*.json
	rm -f data/lakehouse/candidates_v*.json data/lakehouse/stale_*.json data/lakehouse/stale_*.txt

clean-archive: ## Archive old run artifacts (Keep 10 latest)
	$(PY) scripts/maintenance/archive_runs.py --keep 10

check-archive: ## Dry run archive to see what would be deleted
	$(PY) scripts/maintenance/archive_runs.py --keep 10 --dry-run

check-isolation: ## [Audit] Scan Lakehouse for policy violations
	@echo ">>> Scanning data/lakehouse for forbidden artifacts..."
	@find data/lakehouse -maxdepth 1 -name "meta_*" -print
	@find data/lakehouse -maxdepth 1 -name "portfolio_optimized_*.json" -print
	@find data/lakehouse -maxdepth 1 -name "selection_audit.json" -print
	@find data/lakehouse -maxdepth 1 -name "regime_audit.jsonl" -print
	@find data/lakehouse -maxdepth 1 -name "orders" -type d -print
	@echo ">>> Audit Complete."

clean-all: clean-run ## Deep wipe including exports and all summaries
	rm -rf data/export/*.csv data/export/*.json data/export/*/*.csv data/export/*/*.json
	rm -rf $(SUMMARIES_ROOT)

# --- META Namespace ---
meta-refresh: ## Rebuild symbol metadata for current candidates
	$(PY) scripts/build_metadata_catalog.py --candidates-file data/lakehouse/portfolio_candidates.json

meta-refresh-all: ## Rebuild entire symbol metadata catalog (Maintenance)
	$(PY) scripts/build_metadata_catalog.py --from-catalog --catalog-path $(META_CATALOG_PATH)

meta-fetch: ## Fetch execution metadata (lot sizes, min notionals) from exchanges via CCXT
	$(PY) scripts/fetch_execution_metadata.py

meta-audit: ## Verify metadata integrity and timezones
	$(PY) scripts/audit_metadata_pit.py
	$(PY) scripts/audit_metadata_timezones.py
	$(PY) scripts/audit_metadata_catalog.py
