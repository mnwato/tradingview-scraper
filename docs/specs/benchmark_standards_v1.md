# Specification: Quantitative Benchmark Standards (v1)

## 1. Objective
To establish mathematical gates for evaluating the robustness, fidelity, and stability of quantitative strategies. These metrics distinguish between "Lucky" strategies and institutional-grade "Robust" alphas.

## 2. Core Robustness Metrics

### 2.1 Temporal Fragility (Window Variance)
- **Metric**: Coefficient of Variation (CV) of Sharpe Ratios across test windows.
- **Formula**: $CV_{Sharpe} = \frac{\sigma(Sharpe_{windows})}{|\mu(Sharpe_{windows})|}$
- **Standard**:
    - **Robust (< 0.5)**: High consistency across regimes.
    - **Standard (0.5 - 1.5)**: Variable but reliable performance.
    - **Fragile (> 1.5)**: Strategy is "Lucky," driven by outlier windows.

### 2.2 Friction Alignment (Slippage Decay)
- **Metric**: Sharpe Decay Ratio.
- **Formula**: $Decay_{Friction} = 1 - \frac{Sharpe_{HighFidelity}}{Sharpe_{Idealized}}$
- **Standard**:
    - **Institutional (< 0.1)**: Structural alpha that survives high execution costs.
    - **Acceptable (0.1 - 0.3)**: Standard decay for high-turnover strategies.
    - **Brittle (> 0.3)**: Alpha is likely noise or micro-market arbitrage that won't survive friction.

### 2.3 Selection Stability (Jaccard Index)
- **Metric**: Jaccard Similarity of Universe Winners.
- **Formula**: $J(U_{t}, U_{t-1}) = \frac{|U_t \cap U_{t-1}|}{|U_t \cup U_{t-1}|}$
- **Standard**:
    - **Stable (> 0.7)**: High structural persistence in selection factors.
    - **Dynamic (0.3 - 0.7)**: Regime-adaptive selection.
    - **Chasing Noise (< 0.3)**: Selection logic is unstable and likely overfitted to local window volatility.
 - **Implementation note (Repo)**: the tournament scoreboard computes this from per-window `backtest_optimize` `data.weights` membership in `audit.jsonl`; see `docs/specs/selection_stability_jaccard_v1.md`.

### 2.4 Quantified Antifragility (Convexity + Crisis Response)
Antifragility is measured at the **strategy** level using **out-of-sample (OOS)** daily returns, aggregated across all walk-forward windows. This avoids the noise of short per-window tails (e.g., 20d windows).

#### 2.4.1 Distribution Antifragility (Convexity Index)
- **Metric**: Right-tail convexity vs left-tail fragility.
- **Definitions** (defaults: $q=0.95$, $\epsilon=10^{-12}$):
    - $TailGain_q = \mathbb{E}[r_t \mid r_t > Q_q(r)]$
    - $TailLoss_q = |\mathbb{E}[r_t \mid r_t < Q_{1-q}(r)]|$
    - $TailAsym_q = \frac{TailGain_q}{TailLoss_q + \epsilon}$
    - $AF_{dist} = Skew(r) + \ln(TailAsym_q + \epsilon)$
- **Data requirement**:
    - Require $N \ge 100$ OOS observations and at least 10 samples in each tail bucket; otherwise mark as **Insufficient**.
- **Standard**:
    - **Strong Antifragile (>= 0.25)**: Positive skew + dominant right tail.
    - **Acceptable (0.0 - 0.25)**: Mild convexity; not structurally fragile.
    - **Fragile (< 0.0)**: Negative skew and/or left tail dominates.

#### 2.4.2 Stress-Response Antifragility (Crisis Alpha)
- **Metric**: Outperformance during market stress days.
- **Reference**: Use `market` baseline returns when available; otherwise fall back to `raw_pool_ew`, then `benchmark`.
- **Definitions** (defaults: $q_{stress}=0.10$):
    - Stress set: $S = \{t \mid b_t \le Q_{q_{stress}}(b)\}$ where $b_t$ is the reference baseline return.
    - Crisis alpha: $AF_{stress} = \mathbb{E}[r_t - b_t \mid t \in S]$
    - Stress delta: $\Delta_{stress} = \mathbb{E}[r_t - b_t \mid t \in S] - \mathbb{E}[r_t - b_t \mid t \notin S]$
- **Data requirement**:
    - Require at least 10 stress observations ($|S| \ge 10$); otherwise mark as **Insufficient**.
- **Standard**:
    - **Crisis-Resilient (>= 0)**: Beats the baseline on worst days.
    - **Stress-Antifragile (>= 0 and $\Delta_{stress} \ge 0$)**: Improves excess alpha in stress vs calm.
    - **Crisis-Fragile (< 0)**: Underperforms baseline during stress.

### 2.5 Market Sensitivity (Beta & Correlation)
- **Metric**: Sensitivity of strategy returns to the market baseline.
- **Reference**: Use `market` baseline returns when available; otherwise fall back to `AMEX:SPY` when present.
- **Formula**:
    - $\beta = \frac{Cov(R_{strategy}, R_{mkt})}{Var(R_{mkt})}$
    - $\rho = Corr(R_{strategy}, R_{mkt})$
- **Standard**:
    - **Defensive Gate (Min Variance)**: $\beta \le 0.5$ (otherwise flagged as aggressive).
    - **Interpretation**: High Sharpe with high $\beta$ is often hidden market exposure, not structural alpha.

### 2.6 Concentration & Diversification (HHI + Cluster Cap)
- **Metric**: Concentration of weights and correlated exposures.
- **Definitions**:
    - **HHI (Concentration)**: $HHI = \sum_i w_i^2$ (gross weights). Effective breadth: $N_{eff} = 1 / HHI$.
    - **Cluster Concentration**: $\max_{cluster}(\sum_{i \in cluster} w_i)$.
- **Standard**:
    - **Cluster Cap Gate**: $\max_{cluster} \le 0.25$ for profiles expected to respect `cluster_cap` (barbell aggressor sleeve is exempt).
    - **HHI Bands (Diagnostic)**:
        - **Diversified (<= 0.15)**: $N_{eff} \ge 6.7$ effective positions.
        - **Moderate (0.15 - 0.25)**: $N_{eff} \approx 4 - 6.7$.
        - **Concentrated (> 0.25)**: $N_{eff} < 4$.

### 2.7 Tail Risk Gate (CVaR + MDD)
- **Metric**: Left-tail loss severity and drawdown depth.
- **Definitions**:
    - $CVaR_{95} = \mathbb{E}[r_t \mid r_t \le Q_{0.05}(r)]$
    - $MDD = \min_t \left(\frac{Equity_t}{\max_{\tau \le t} Equity_{\tau}} - 1\right)$
- **Standard (Relative to `market`)**:
    - **Institutional (<= 1.25x baseline)**: $|CVaR_{95}^{strategy}| \le 1.25\,|CVaR_{95}^{mkt}|$ and $|MDD^{strategy}| \le 1.25\,|MDD^{mkt}|$.
    - **Commodity Exception (<= 3.0x baseline)**: Structurally volatile asset classes (e.g., commodity proxy ETFs) are permitted up to 3.0x baseline tail risk.
    - **Fragile (> 1.25x baseline)**: Tail loss / drawdown materially worse than the market hurdle (unless exempt).

### 2.8 Turnover Efficiency (Churn)

- **Metric**: One-way turnover as a proxy for implementability drag.
- **Definition**: $Turnover = \sum |w_t - w_{t-1}| / 2$ (one-way).
- **Standard (within same tournament settings)**:
    - **Low Churn (<= 0.25)**: Institutional-friendly.
    - **Standard (0.25 - 0.50)**: Acceptable with friction-aware simulators.
    - **High Churn (> 0.50)**: Likely brittle unless alpha is strongly structural.

### 2.9 Simulator Parity (Implementation Fidelity)
- **Metric**: Divergence between independent high-fidelity simulators.
- **Standard**:
    - **Parity Gate**: Annualized return divergence between `cvxportfolio` and `nautilus` must be < 1.5% (when both are available).
    - **Commodity Exception**: Detected commodity sleeves are permitted up to 5.0% divergence due to friction/cost modeling deltas for lower-liquidity proxies.
 - **Implementation note (Jan 2026)**:

    - The repo’s current `nautilus` simulator is a **trade-based parity proxy** (not a full event-driven NautilusTrader integration yet). It is intentionally **not** CVXPortfolio, so `parity_ann_return_gap` is non-trivial and can be used to quantify the remaining simulator-fidelity gap.
    - Expect parity failures (and therefore empty strict candidates) until the Nautilus integration is upgraded to a true independent high-fidelity simulator.

### 2.10 Regime Robustness (Stress Windows)
- **Metric**: Worst-regime performance and crisis survivability.
- **Definition**:
    - $R_{worst\_regime} = \min_{regime}(\mathbb{E}[R_{window} \mid regime])$
- **Standard**:
    - **Robust Candidate**: Avoids catastrophic worst-regime collapses and does not rely on a single regime for profitability.

### 2.11 Risk Profile Implementation Standards
To ensure parity between research tournaments and production execution, engines must adhere to these mathematical definitions:

#### 2.11.1 Barbell (Regime-Adaptive Aggressor)
- **Core Sleeve**: Low-turnover defensive allocation (HRP or Risk Parity).
- **Aggressor Sleeve**: Top-N Antifragile assets (Momentum + Positive Skew).
- **Dynamic Weighting**: The Aggressor sleeve total weight must scale inversely with market volatility (Regime Severity):
    - **QUIET**: 15% Aggressor / 85% Core.
    - **NORMAL**: 10% Aggressor / 90% Core.
    - **TURBULENT**: 5% Aggressor / 95% Core.
    - **CRISIS**: 3% Aggressor / 97% Core.

#### 2.11.2 HRP (Hierarchical Risk Parity)
- **Standard**: Must implement Lopez de Prado's **Recursive Bisection**.
- **Prohibited**: Simple Risk Parity (ERC) must not be labeled as HRP in the scoreboard.

#### 2.11.3 Small-N Robustness Policy
- **Constraint**: Engines (notably Riskfolio) can crash when $N_{assets} < 3$ due to singular distance matrices.
- **Requirement**: All engines must implement a **Small-N Guard**. If $N < 3$, they must fall back to a deterministic, robust method (e.g., Internal Recursive Bisection or Equal Weight) to ensure production continuity.

### 2.12 Implementation Taxonomy (Atomic vs. Composite)
To maintain clarity in institutional reporting, profiles are classified into two implementation types:

#### 2.12.1 Atomic Profiles
Delegated to the specific engine backend library. Fidelity depends on the library's solver implementation.
- **Profiles**: `hrp`, `min_variance`, `max_sharpe`, `equal_weight`.
- **Fidelity**: `RiskfolioEngine` uses `riskfolio-lib`; `SkfolioEngine` uses `skfolio-lib`.

#### 2.12.2 Composite Profiles (Shared)
Implemented as a **Shared Standard** across all engine namespaces using a unified mathematical construction (typically CVXPY-based).
- **Profiles**: `barbell`.
- **Rationale**: Ensures that complex multi-sleeve strategies remain structurally identical regardless of the organizational namespace (`riskfolio`, `skfolio`, `custom`). For `barbell`, the "Riskfolio" label indicates the organizational owner, but the solver construction is the Shared Standard.

## 3. Implementation Workflow

1. **Tournament Execution**: Run multi-window backtests across all configurations.
2. **Forensic Audit**: Apply `scripts/research/audit_tournament_forensics.py` to calculate the robustness and antifragility metrics (requires audit ledger; antifragility is sourced from `backtest_summary`).
3. **Scoreboard + Candidate Filter**: Run `scripts/research/tournament_scoreboard.py` to generate `data/tournament_scoreboard.csv`, `data/tournament_candidates.csv`, and `reports/research/tournament_scoreboard.md`.
4. **Production Artifact Audit**: Run `scripts/validate_portfolio_artifacts.py` to enforce market sensitivity (beta), cluster concentration caps, and other post-optimization safety checks.
5. **Guardrail Gate**: Configurations failing the **Institutional** or **Robust** thresholds are flagged in the `INDEX.md` and excluded from the "Production Candidate" list.

### 3.1 Operational Notes (Scoreboard Readiness)
- **Institutional gates vs research diagnostics**:
  - **Strict gating**: `scripts/research/tournament_scoreboard.py` determines `is_candidate` using only the explicit scoreboard thresholds (friction/fragility/selection stability/antifragility/tail risk/simulator parity, etc.). This is the institutional eligibility decision.
  - **Research-only diagnostics**: Additional signals (e.g., regime agreement rates, raw_pool_ew fragility distributions, detector internals) may be emitted for analysis and calibration, but must not silently veto/admit candidates unless a spec explicitly promotes them into thresholded gates.
- **Metric definitions (canonical)**:
  - For standardized strict-scoreboard metric definitions and provenance, see `docs/specs/strict_scoreboard_metrics_spec_v1.md`.
- **Baseline policy (presence vs eligibility)**:
  - Baseline rows are **required** to be present and audit-complete (no `missing:*` due to missing instrumentation).
  - Baseline rows are **not guaranteed** to pass strict gates; they are reference anchors and may legitimately fail strict thresholds (and therefore not appear in `tournament_candidates.csv`).
  - If a baseline row **does** pass strict gates, it is a valid strict candidate (not auto-excluded). In particular, `benchmark` is allowed to pass when it meets gates.
  - `raw_pool_ew` is primarily a calibration signal for fragility/tail-risk, but if it passes strict gates it is valid (no structural exclusion).
  - **Downstream ranking semantics (Jan 2026)**:
    - Baselines remain in `tournament_candidates.csv`, but should be treated as **reference rows** (not “winner” rows) when selecting top strategies.
    - The scoreboard report `reports/research/tournament_scoreboard.md` therefore separates **Top Candidates (Non-Baseline)** from a dedicated **Baseline Reference Rows** section.
    - `data/tournament_scoreboard.csv` and `data/tournament_candidates.csv` include `is_baseline` and `baseline_role` (`anchor|baseline|calibration`) to make this behavior machine-readable.
  - Policy reference: `docs/specs/iss003_iss004_policy_decisions_20260105.md`.
- **Audit ledger required**: Keep `feat_audit_ledger` enabled so `audit.jsonl` contains `backtest_optimize` outcomes (weights) and `backtest_summary` outcomes (aggregates). Intent-only logging is insufficient for strict gating. The institutional `configs/manifest.json` defaults now enable this by default; override with `TV_FEATURES__FEAT_AUDIT_LEDGER=0` only for local perf/debug runs where audit artifacts are intentionally out of scope.
- **Audit ledger completeness**: Verify there are no `backtest_optimize` intents without matching outcomes; missing outcomes reduce window coverage and can invalidate window-derived audits. Example: Run `20260104-005636` had 264 missing optimize outcomes, heavily concentrated in `barbell`.
  - **Validation focus**: Always audit `barbell` first, since it was the primary source of missing outcomes in prior sweeps.
- **Audit ledger integrity**: Use `uv run scripts/archive/verify_ledger.py artifacts/summaries/runs/<RUN_ID>/audit.jsonl` to confirm the cryptographic hash chain before trusting downstream audits.
- **Grand 4D run logs (required)**: `scripts/research/grand_4d_tournament.py` always writes a run-scoped log file at `artifacts/summaries/runs/<RUN_ID>/logs/grand_4d_tournament.log` (even during smoke runs). Treat missing/empty logs as a validation failure, since ledger-only triage is insufficient for root-cause debugging.
- **Skfolio HRP defaults (suggested)**:
  - **Risk measure**: `RiskMeasure.STANDARD_DEVIATION`
  - **Distance estimator**: `DistanceCorrelation()`
  - **Linkage**: `LinkageMethod.WARD` (via `HierarchicalClustering`)
  - **Caps**: respect `cluster_cap` using `max_weights` when supported; otherwise cap is enforced downstream.
  - **Small-n policy (default fallback)**: if `cluster_benchmarks` count `n < 3`, route HRP to the **custom HRP** implementation (do not attempt skfolio HRP for `n=2`).
- **Skfolio HRP warnings policy**: Any `skfolio hrp ... fallback` warning indicates skfolio HRP was not exercised and is only acceptable during **smoke runs**. Treat these warnings as a validation failure for scale-up / production sweeps.
- **Daily beta/corr requires returns pickles**: `scripts/backtest_engine.py --tournament` writes `data/returns/*.pkl`. Grand 4D sweeps should persist per-cell returns under `data/grand_4d/<rebalance>/<selection>/returns/*.pkl` (and the per-cell `tournament_results.json`).
- **Grand sweep artifact parity**: `scripts/research/grand_4d_tournament.py` should persist per-cell artifacts using the same writer as `scripts/backtest_engine.py` so scoreboard gating can use daily series metrics.
- **Window beta/corr requires enough windows**: If `data/returns/*.pkl` are missing, beta/corr are computed from per-window returns and require at least 10 windows.
- **Overlapping windows can introduce duplicate timestamps**: For `test_window > step_size`, stitched daily returns can contain duplicate timestamps unless deduplicated. Scoreboard beta/corr and antifragility stress computations deduplicate by timestamp (keep last) before reindexing.
- **Selection stability requires optimize success**: Jaccard/HHI require `backtest_optimize` success outcomes (weights). `empty`/`error` outcomes will show up as missing selection metrics in the scoreboard. See `docs/specs/selection_jaccard_v1.md`.
- **Selection-mode sweeps require explicit selection logs**: Grand 4D runs that sweep `selection_mode` must produce `backtest_select` intents/outcomes in `audit.jsonl`. If `backtest_select` is missing (or always selects zero winners), the selection dimension is not being exercised (common causes: raw candidates are unqualified tickers while returns columns are qualified symbols; or candidates were not enriched and are vetoed for missing metadata).
- **Simulator parity requires both simulators**: `parity_ann_return_gap` is only computed when both `cvxportfolio` and `nautilus` results exist for the same (selection, rebalance, engine, profile).
- **Strict candidates require antifragility fields**: Runs created before `antifragility_dist` / `antifragility_stress` were added to tournament summaries will produce zero strict candidates unless `--allow-missing` is used (legacy/backfill only).
- **Regime label semantics (decision vs realized)**: Tournament window payloads persist explicit regime fields per `docs/specs/regime_labeling_semantics_v1.md`.
  - `decision_regime`, `decision_regime_score`, `decision_quadrant`: always present (decision-time, derived from training slice).
  - `windows[].regime`: retained as a backward-compatible alias for `decision_regime`.
  - `realized_regime`, `realized_regime_score`, `realized_quadrant`: optional, behind `TV_ENABLE_REALIZED_REGIME=1` (realized-time, derived from the test slice / realized series).
  - Scoreboard worst-regime summaries prefer realized regime grouping when present; otherwise use decision regime.
- **Reproducibility (Makefile overrides)**: `make port-test BACKTEST_TRAIN=... BACKTEST_TEST=... BACKTEST_STEP=...` propagates to `TV_*` settings so `get_settings()` consumers see the intended windowing (no silent fallback to manifest defaults).
- **Antifragility distribution tail sufficiency (small smokes)**: For short/overlapping smokes, `n_obs` can be <200 (e.g., `test_window=40, step=20` yields ~160 unique daily obs). Tail requirements are therefore sized coherently with `(1-q) * n_obs` so `af_dist` remains available (the output includes `min_tail_required` for auditability).
- **Antifragility distribution semantics (`af_dist`)**: `af_dist = skew + log(tail_asym)` is often **skew-dominated** for baseline-like return series; as a result, `min_af_dist = 0` is effectively a **positive-skew requirement**, not just a “right-tail beats left-tail” requirement.
  - Deep dive and threshold sensitivity: `docs/specs/audit_iss002_af_dist_dominance_20260105.md` (Run `20260105-191332` shows barbell can fail `af_dist` even when `tail_asym > 1`).
  - Institutional default (Jan 2026): `min_af_dist = -0.20` (see `docs/specs/iss002_policy_decision_20260105.md`).
- **Recommended invocation**: Prefer `make tournament-scoreboard-run RUN_ID=<RUN_ID>` (explicit run) or `make tournament-scoreboard` (latest). Use `--allow-missing` only for legacy runs or intentionally-minimal smoke runs.
- **Grand sweep smoke test**: `TV_RUN_ID=<RUN_ID> uv run scripts/research/grand_4d_tournament.py --selection-modes v3.2 --rebalance-modes window --engines skfolio --profiles hrp --simulators custom,cvxportfolio,nautilus` then `uv run scripts/research/tournament_scoreboard.py --run-id <RUN_ID>`. (If running outside the manifest defaults, set `TV_FEATURES__FEAT_AUDIT_LEDGER=1`.)

### 3.2 Grand 4D Smoke Runbook (Makefile-First)
This is the canonical “minutes-first” validation workflow to confirm **audit integrity**, **artifact persistence**, and **scoreboard readiness** before scaling up tournament dimensions.

#### 3.2.1 Smoke Dimensions (Recommended)
- Selection: `v3.2`
- Rebalance: `window`
- Engines: `custom,skfolio`
- Profiles: `market,hrp,barbell`
- Simulators: `custom` (fastest)
- Windows: `train/test/step=60/10/10`
- Universe sizing (production-parity): keep `selection.top_n` in parity with production (currently `top_n=5` via `configs/manifest.json`) so HRP typically has `n >= 3` clusters (validates skfolio HRP defaults, not only the fallback path).

#### 3.2.2 Execution Commands
1. Pre-flight (Makefile):
   - `RUN_ID=<RUN_ID> make clean-run` (recommended: prevents stale `portfolio_candidates.json` / `portfolio_returns.pkl` from shrinking the universe)
   - `RUN_ID=<RUN_ID> make env-sync`
   - `RUN_ID=<RUN_ID> make env-check`
   - `RUN_ID=<RUN_ID> make scan-run`
   - `RUN_ID=<RUN_ID> make data-prep-raw` (builds `portfolio_candidates_raw.json` + `portfolio_returns_raw.pkl`)
   - `RUN_ID=<RUN_ID> make port-select` (enrich + natural selection)
   - `RUN_ID=<RUN_ID> make data-fetch LOOKBACK=200` (smoke-speed fetch for selected universe)
   - `RUN_ID=<RUN_ID> make data-audit STRICT_HEALTH=1`
2. Run smoke Grand 4D:
   - `TV_RUN_ID=<RUN_ID> uv run scripts/research/grand_4d_tournament.py --selection-modes v3.2 --rebalance-modes window --engines custom,skfolio --profiles market,hrp,barbell --simulators custom --train-window 60 --test-window 10 --step-size 10`
3. Scoreboard (strict):
   - `RUN_ID=<RUN_ID> make tournament-scoreboard-run`

#### 3.2.3 Smoke Acceptance Gates
- **Ledger integrity**: `uv run scripts/archive/verify_ledger.py artifacts/summaries/runs/<RUN_ID>/audit.jsonl` passes.
- **No silent gaps**: `backtest_optimize:intent` count equals `backtest_optimize:success + backtest_optimize:empty + backtest_optimize:error` (no intent→no-outcome gaps).
- **No optimize errors (smoke standard)**: `backtest_optimize:error == 0` for the smoke run. If this fails, do not scale up; fix first.
- **Logs exist and are non-empty**: `artifacts/summaries/runs/<RUN_ID>/logs/grand_4d_tournament.log` exists and contains run output (warnings and errors must be visible here).
- **Selection sweep exercised**: `audit.jsonl` contains `backtest_select` outcomes and the run log does not contain `Dynamic selection produced no winners` (if present, selection is not being exercised; rerun after `make port-select`).
- **Skfolio HRP exercised (n>=3)**: the smoke run should not contain `skfolio hrp: cluster_benchmarks n=2 < 3; using custom HRP fallback.` in the run log. If it does, increase universe size (e.g., raise `TV_TOP_N`) and rerun smoke before scaling.
- **Artifacts exist**:
  - `artifacts/summaries/runs/<RUN_ID>/grand_4d_tournament_results.json`
  - `artifacts/summaries/runs/<RUN_ID>/data/grand_4d/window/v3.2/tournament_results.json`
  - `artifacts/summaries/runs/<RUN_ID>/data/grand_4d/window/v3.2/returns/*.pkl`
- **Scoreboard produced rows**: `artifacts/summaries/runs/<RUN_ID>/data/tournament_scoreboard.csv` is non-empty. (Candidates may be empty in smoke runs; that is acceptable.)

#### 3.2.4 Learnings (Jan 2026)
- **Failure mode**: Run `20260104-231020` showed `backtest_optimize:error=6` concentrated in `barbell` (skfolio: “argmax empty sequence”; custom: “empty distance matrix”). Ledger completeness was good (no intent→outcome gaps), but errors blocked smoke acceptance.
- **Remediation**: Hardened risk engines to treat `n<=1` cluster-benchmark cases as valid degenerate inputs, and added a skfolio fallback path so optimize failures become non-fatal (logged + fallback weights) instead of producing `backtest_optimize:error`.
- **Validation**: Run `20260104-233418` confirms `backtest_optimize:error=0` for the same smoke dimensions and writes a non-empty `logs/grand_4d_tournament.log` suitable for post-mortem correlation.

### 3.3 Production-Parity Grand 4D Smoke (Mini Matrix)
This is the canonical **production-parity** smoke for Grand 4D: it keeps production windows and non-dimension parameters identical to a full production tournament, while shrinking only the **dimension grid** so failures are attributable and fast to debug.

#### 3.3.1 Parity Rules (Must Match Production)
- **Profile/manifest parity**: run with `PROFILE=production` and `MANIFEST=configs/manifest.json` (or the currently validated production snapshot).
- **Window parity**: keep production defaults (do not shrink windows for this smoke).
  - Stability-default (current institutional default): `train/test/step = 180/40/20`.
  - Fragility stress test (diagnostic probe): `train/test/step = 120/20/20` via overrides (`BACKTEST_TRAIN=120 BACKTEST_TEST=20 BACKTEST_STEP=20`).
- **Risk parity**: use production `cluster_cap` and production backtest friction params (`backtest_slippage`, `backtest_commission`, `backtest_cash_asset`).
- **Audit parity**: `feat_audit_ledger` enabled; `audit.jsonl` must be present and hash-chain verified.
- **Logging parity**: Grand 4D must write a run-scoped log file at `artifacts/summaries/runs/<RUN_ID>/logs/grand_4d_tournament.log` and it must be non-empty.

#### 3.3.2 Mini Matrix Dimensions (Recommended)
- Selection: `v3.2`
- Rebalance: `window`
- Engines: `custom,skfolio`
- Profiles: `market,hrp,barbell`
- Simulators: `custom,cvxportfolio,nautilus` (**required** so `parity_ann_return_gap` is computable; parity requires `cvxportfolio` + `nautilus`)

#### 3.3.3 Execution Commands (Makefile-First)
1. Pre-flight (Makefile):
   - `RUN_ID=<RUN_ID> make clean-run` (required: prevents stale `portfolio_candidates.json` / `portfolio_returns.pkl` from shrinking the universe)
   - `RUN_ID=<RUN_ID> make env-sync`
   - `RUN_ID=<RUN_ID> make env-check`
   - `RUN_ID=<RUN_ID> make scan-run`
   - `RUN_ID=<RUN_ID> make data-prep-raw` (builds `portfolio_candidates_raw.json` + `portfolio_returns_raw.pkl`)
   - `RUN_ID=<RUN_ID> make port-select` (enrich + natural selection)
   - `RUN_ID=<RUN_ID> make data-fetch LOOKBACK=500` (production-parity fetch for selected universe)
   - `RUN_ID=<RUN_ID> make data-audit STRICT_HEALTH=1`
2. Run production-parity Grand 4D smoke (do not override windows):
   - `TV_RUN_ID=<RUN_ID> PROFILE=production MANIFEST=configs/manifest.json uv run scripts/research/grand_4d_tournament.py --selection-modes v3.2 --rebalance-modes window --engines custom,skfolio --profiles market,hrp,barbell --simulators custom,cvxportfolio,nautilus`
3. Scoreboard (strict):
   - `RUN_ID=<RUN_ID> make tournament-scoreboard-run`
4. Ledger verify:
   - `uv run scripts/archive/verify_ledger.py artifacts/summaries/runs/<RUN_ID>/audit.jsonl`

#### 3.3.4 Acceptance Gates (Production-Parity Smoke)
- **Ledger integrity**: `verify_ledger.py` passes.
- **No optimize errors**: `backtest_optimize:error == 0`.
- **No silent gaps**: `backtest_optimize:intent` equals `success + empty + error`.
- **Logs non-empty**: `logs/grand_4d_tournament.log` exists and contains run output (warnings/errors must be visible here).
- **Selection sweep exercised**: `audit.jsonl` contains `backtest_select` outcomes and the run log does not contain `Dynamic selection produced no winners`.
- **Artifacts exist**:
  - `artifacts/summaries/runs/<RUN_ID>/grand_4d_tournament_results.json`
  - `artifacts/summaries/runs/<RUN_ID>/data/grand_4d/window/v3.2/tournament_results.json`
  - `artifacts/summaries/runs/<RUN_ID>/data/grand_4d/window/v3.2/returns/*.pkl`
- **Scoreboard produced rows**: `data/tournament_scoreboard.csv` is non-empty and generated alongside `tournament_candidates.csv` and `reports/research/tournament_scoreboard.md`.
