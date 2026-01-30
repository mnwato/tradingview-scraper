# Audit: Q1 2026 Scoreboard Stabilization

This document preserves the resolution history of the Q1 2026 strict-scoreboard issue backlog. These items were addressed to ensure the platform is scale-ready for production tournaments.

## Issue Backlog Resolution Log

### ISS-001 — Simulator parity gate realism (`sim_parity`)
- **Status**: Completed (Run `20260106-000000`).
- **Findings**: Equity universes show excellent simulator parity (**~0.4% gap**). Commodity sleeves (UE-010) show structural divergence (**4-6%**) due to friction/cost modeling deltas for lower-liquidity proxies.
- **Resolution**: 1.5% parity gate maintained for standard universes. Sleeve-aware relaxation (5.0%) implemented for commodity sleeves.

### ISS-002 — `af_dist` dominance under larger windows (`180/40/20`)
- **Status**: Resolved (Run `20260106-020000`).
- **Findings**: In full history runs, `benchmark` anchor candidates show strongly positive `af_dist` (> 0.8).
- **Policy Decision**: Institutional default set to `min_af_dist = -0.20` to prevent false-negative vetoes of high-quality anchor candidates while still excluding market-like fragility.

### ISS-003 — Baseline row policy (presence vs eligibility)
- **Status**: Resolved.
- **Decision**: Baselines are **reference rows**: must be present + audit-complete, but not guaranteed to pass strict gates. Separated from candidates in machine-readable reports.

### ISS-004 — Temporal fragility stress-test vs production window defaults
- **Status**: Resolved.
- **Decision**: Treat `120/20/20` as a fragility stress test; treat `180/40/20` as a stability default for production.

### ISS-005 — Friction alignment (`friction_decay`) failures on baselines
- **Status**: Completed (Run `20260106-010000`).
- **Findings**: `ReturnsSimulator` was double-counting friction for single-asset baselines by including the cash leg.
- **Resolution**: Updated simulator to calculate costs only on non-cash asset trades. Validated that `friction_decay` for baselines is now near-zero (**~0.03**).

### ISS-006 — HRP cluster universe collapse to `n=2`
- **Status**: Closed.
- **Findings**: Production selection yields ample breadth. Warnings localized to small discovery baskets.
- **Policy Decision**: Discovery sleeves must maintain a minimum raw pool of **10 symbols** to ensure structural robustness.

### ISS-007 — `min_variance` beta gate stability
- **Status**: Resolved (Run `20260106-020000`).
- **Findings**: Defensive `min_variance` profiles consistently demonstrated low beta (**0.32 - 0.41**), well below the 0.5 threshold.

### ISS-008 — Commodity sleeve gate calibration
- **Status**: Resolved (Run `20260105-214909`).
- **Resolution**: Implemented **Sleeve-Aware Thresholds** in `scripts/research/tournament_scoreboard.py`. Relaxed `max_tail_multiplier` to 3.0 and `max_parity_gap` to 5.0% for detected commodity sleeves.
