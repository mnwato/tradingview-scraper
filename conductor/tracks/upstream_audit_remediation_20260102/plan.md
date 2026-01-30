# Plan: Upstream Pipeline Audit & Remediation

## 1. Profile Resolution
- [ ] **Task**: Update `Makefile` to set `PROFILE ?= ` (empty default). This forces `settings.py` to use `default_profile` from `manifest.json`.

## 2. Discovery Aggregation Standards
- [ ] **Task**: Update `scripts/select_top_universe.py` to support `strategy_selector_*.json` and `universe_selector_*.json` without explicit file-by-file configuration.

## 3. Hedge Anchor Logic
- [ ] **Task**: Refactor `scripts/detect_hedge_anchors.py` to remove hardcoded "BCH" heuristic. Use `market == "CRYPTO"` or `asset_class == "CRYPTO"` from metadata.

## 4. Final Verification
- [ ] **Task**: Run `make upstream PROFILE=production_2026_q1` and review the decision trail in `selection_audit.json`.
