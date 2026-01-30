# Baseline & Guardrail Report (Run 20260103-223836)

## Executive summary
- The production run `20260103-223836` finished with complete artifacts and successfully validated the Jan 2026 institutional fidelity fixes (no truncation, zero lookahead).
- Human-readable guardrail reporting now documents the canonical vs selected universes, the canonical/selected invariance passes, and the stability of the latest production run.
- This report references `docs/specs/plan.md` as the canonical spec; use the plan for the detailed risk-profile table, baseline-spec Q&A, and ongoing action items.

## Guardrail results
| Guardrail command | Universe pairing | result | key metrics (windows / annualized return / vol / win rate) |
| --- | --- | --- | --- |
| `make baseline-guardrail RUN_A=20260103-182051 RUN_B=20260103-223836` | selected vs selected | **PASS** | Both runs: 11 / 0.2797840635 / 0.1843112227 / 81.82%. |
| `make baseline-guardrail RUN_A=20260103-171913 RUN_B=20260103-182051` | canonical (A) vs selected (B) | **FAIL (sentinel)** | Run A: 11 / 0.1894 / 0.1137 / 63.6% vs Run B: 11 / 0.2798 / 0.1843 / 81.8% → mismatch because universes differ and is now treated as an expected sentinel. |
| `make baseline-guardrail RUN_A=20260103-171756 RUN_B=20260103-171913` | canonical vs canonical | **PASS** | Both runs: 11 / 0.1894294957 / 0.1137406122 / 63.64%. |
| `make baseline-guardrail RUN_A=20260103-172054 RUN_B=20260103-182051` | selected vs selected | **PASS** | Both runs: 11 / 0.2797840635 / 0.1843112227 / 81.82%. |

## Guardrail narrative
1. The mismatched command (canonical vs selected) intentionally fails because raw_pool summaries drift when the universe source differs; the delta is +0.0903546 annualized return, +0.0705706 vol, and +18.18% win rate, providing a built-in sentinel for universe misalignment. The guardrail now inspects universe metadata (selection mode, source, symbol count, hash) and returns success after logging a sentinel notice when that mismatch is detected.
2. The canonical pass (RUNs `171756` & `171913`) certifies that canonical `raw_pool_ew` summaries are invariant within 1e-9 when the raw pool remains the same even if selection mode toggles (v3 vs v3.2).
3. The selected pass (RUNs `172054` & `182051`) shows the same invariance holds for the active universe; guardrail commands should reuse these RUN_ID pairs as their canonical pass cases.

## Baseline facts (derived from `docs/specs/plan.md`)
- `market` is the noise-free institutional hurdle: long-only equal weight across `settings.benchmark_symbols` (SPY), no fallbacks, logs the symbol hash, and is reported identically across all engines (`market_baseline` alias included for legacy dashboards).
- `benchmark` is the research baseline equal weight over the natural-selected universe; it logs universe source + count, provides the comparator for risk profiles, and is unaffected by selection-mode heuristics.
- `raw_pool_ew` is the selection-alpha baseline: asset-level equal weight over the raw pool (controlled by `TV_RAW_POOL_UNIVERSE`), excludes benchmark symbols, requires at least `train+test+1` rows, records `raw_pool_symbol_count` and `raw_pool_returns_hash`, and is only considered a full baseline when coverage and invariance both pass (otherwise treat it as a diagnostic).
- Legacy aliases `market_baseline` and `benchmark_baseline` mirror the corresponding baselines within the `custom` engine outputs so historical dashboards stay stable.

## Baseline-spec Q&A
1. **Keep baselines to market & benchmark without noise**: the taxonomy restricts baseline profiles to `market` and `benchmark` (per `docs/specs/optimization_engine_v2.md`); every other label (e.g., `equal_weight`, `raw_pool_ew`) belongs to risk-profile diagnostics.
2. **Baseline requirements**: `market` must fail fast with empty weights if benchmarks are missing and log the symbol hash; `benchmark` must log the selected universe source and count; `raw_pool_ew` must document `TV_RAW_POOL_UNIVERSE`, coverage, symbol count, hash, and guardrail results.
3. **Canonical vs natural-selected**: canonical returns come from `portfolio_returns_raw.pkl`/`portfolio_candidates_raw.json`, while natural-selected uses `portfolio_returns.pkl`/`portfolio_candidates.json`; every audit entry must record `selection_mode`, `universe_source`, and the `selection_audit.json` hash so traceability survives guardrail checks.
4. **Benchmark vs raw_pool**: `benchmark` controls the risk-profile comparator over the active universe, while `raw_pool_ew` is the selection baseline sitting above the raw pool; they should never be conflated.

## Risk-profile summary (see `docs/specs/plan.md` for the full table)
| Profile | Category | Universe | Weighting / Optimization | Notes |
| --- | --- | --- | --- | --- |
| `market` | Baseline | Benchmark symbols | Equal weight, long-only | Institutional hurdle; shared across engines via `market_profile_unification`. |
| `benchmark` | Baseline | Natural-selected universe | Asset-level equal weight | Risk-profile comparator; logs source + count. |
| `raw_pool_ew` | Baseline (diagnostic) | Canonical/selected via `TV_RAW_POOL_UNIVERSE` | Asset-level equal weight across raw pool, excludes benchmark symbols | Only a baseline when coverage + invariance pass; raw pool guardrails ensure stability. |
| `equal_weight` | Risk | Natural-selected | Hierarchical equal weight (HERC 2.0 intra) | Neutral, low-friction comparison. |
| `min_variance` | Risk | Natural-selected | Cluster-level min variance | Defensive profile; HERC intra weighting. |
| `hrp` | Risk | Natural-selected | Hierarchical risk parity | Structural resilience. |
| `max_sharpe` | Risk | Natural-selected | Max Sharpe mean-variance | Growth regime focus; cluster cap compliance. |
| `barbell` | Strategy | Natural-selected | Core HRP + aggressor sleeve | Convexity + antifragility; backed by `multi_engine_optimization_benchmarks`. |

## Data references
- `tournament_results.json` (run `20260103-182051`) shows each engine’s `market`, `benchmark`, and `raw_pool_ew` summaries with the tournament-level windows; `raw_pool_ew` windows are 11 in this run and are audited in `audit.jsonl` under `raw_pool_symbol_count` / `raw_pool_returns_hash`.
- `selection_audit.json` (run `20260103-182051`) documents 44 raw candidates, 13 selected winners, the `[60,120,200]` lookbacks, the canonical clusters/winners, and the stable veto list after metadata enrichment.

## Verification
- Validation consists of rerunning the guardrail command against the canonical and selected pairs to confirm pass/fail expectations. The `make baseline-guardrail` runs displayed above are the authoritative evidence supporting every claim in this report.
- For future reports, reuse the same RUN_ID pairs (`171756/171913` and `172054/182051`) plus the mismatched pair to show how invariance behaves when universes differ.
