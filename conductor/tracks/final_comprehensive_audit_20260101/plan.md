# Plan: Final Comprehensive Audit & Benchmark (Legacy V3 & Nautilus)

**Track ID**: `final_comprehensive_audit_20260101`
**Date**: 2026-01-01
**Goal**: Run one final, exhaustive benchmark including the deprecated `v3` selection and the `nautilus` simulator to provide a complete historical comparison and audit the entire pipeline before freezing the configuration.

## Problem Statement
The previous "Grand Validation" omitted `v3` (Legacy) and `nautilus` (Simulator) to save time. To ensure complete rigorousness and document exactly *why* `v3` is deprecated and *how* `nautilus` aligns with other simulators, we need one final run.

## Objectives
1.  **Full Simulator Consistency**:
    *   Compare `custom`, `cvxportfolio`, and `nautilus` results.
    *   *Metric*: Do they produce the same Equity Curve for the same weights?
2.  **Legacy V3 Baseline**:
    *   Include `v3` in the report to explicitly show its underperformance vs `v3.1` and `v2`.
3.  **Comprehensive Report**:
    *   Generate a "Final Report" aggregating all dimensions: Selection (3), Engine (3), Profile (5+), Simulator (3).

## Execution Plan

### Phase 1: Configuration
- [ ] **Step 1**: Update `scripts/run_4d_tournament.py` to include:
    *   `selection_modes`: `["v2", "v3", "v3.1"]`.
    *   `simulators`: `["custom", "cvxportfolio", "nautilus"]`.
    *   `profiles`: All relevant profiles.

### Phase 2: Execution
- [ ] **Step 2**: Run the Tournament (Expect high duration).

### Phase 3: Audit & Reporting
- [ ] **Step 3**: Run `scripts/generate_risk_report.py`.
- [ ] **Step 4**: Run `scripts/generate_selection_report.py`.
- [ ] **Step 5**: Create `scripts/audit_simulator_fidelity.py` to compare equity curves between simulators for a specific (Mode, Engine, Profile) tuple.
- [ ] **Step 6**: Final synthesis.
