import logging
from typing import Dict, cast

import numpy as np
import pandas as pd

from tradingview_scraper.selection_engines.base import (
    BaseSelectionEngine,
    SelectionRequest,
    SelectionResponse,
    get_hierarchical_clusters,
    get_robust_correlation,
)
from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.predictability import (
    calculate_efficiency_ratio,
    calculate_hurst_exponent,
    calculate_permutation_entropy,
)
from tradingview_scraper.utils.scoring import calculate_liquidity_score, calculate_mps_score

logger = logging.getLogger("selection_engines")


class SelectionEngineV3(BaseSelectionEngine):
    """
    Multiplicative Probability Scoring (MPS 3.0) + Operation Darwin Vetoes.
    Now enhanced with Spectral Predictability Filters (PE, Hurst, ER).
    """

    def __init__(self):
        super().__init__()
        self.kappa_threshold = 1e6
        self.eci_hurdle = 0.02
        self.spec_version = "3.0"

    @property
    def name(self) -> str:
        return "v3"

    def select(self, returns, raw_candidates, stats_df, request):
        return self._select_v3_core(returns, raw_candidates, stats_df, request)

    def _get_active_thresholds(self, request: SelectionRequest) -> Dict[str, float]:
        s = get_settings()
        return {
            "entropy_max": request.params.get("entropy_max_threshold", s.features.entropy_max_threshold),
            "efficiency_min": request.params.get("efficiency_min_threshold", s.features.efficiency_min_threshold),
            "hurst_rw_min": request.params.get("hurst_random_walk_min", s.features.hurst_random_walk_min),
            "hurst_rw_max": request.params.get("hurst_random_walk_max", s.features.hurst_random_walk_max),
            "eci_hurdle": request.params.get("eci_hurdle", self.eci_hurdle),
            "kappa_max": request.params.get("kappa_shrinkage_threshold", s.features.kappa_shrinkage_threshold),
            "shr_init": request.params.get("default_shrinkage_intensity", s.features.default_shrinkage_intensity),
        }

    def _calculate_alpha_scores(self, mps_metrics, methods, frag_penalty):
        s = get_settings()
        f_m = {k: v for k, v in mps_metrics.items() if k not in ["efficiency", "entropy", "hurst_clean"]}
        if s.features.feat_efficiency_scoring:
            f_m["efficiency"] = mps_metrics["efficiency"]
        return calculate_mps_score(f_m, methods=methods) * (1.0 - frag_penalty)

    def _select_v3_core(self, returns, raw_candidates, stats_df, request):
        candidate_map = {c["symbol"]: c for c in raw_candidates}
        settings, selection_warnings, metrics, vetoes = get_settings(), [], {}, {}
        thresholds = self._get_active_thresholds(request)
        relaxation_stage = int(request.params.get("relaxation_stage", 1))

        cluster_ids, _ = get_hierarchical_clusters(returns, request.threshold, request.max_clusters)
        clusters = {}
        for sym, c_id in zip(returns.columns, cluster_ids):
            clusters.setdefault(int(c_id), []).append(str(sym))

        mom_all = cast(pd.Series, returns.mean() * 252)
        vol_all = pd.Series({s: float(returns[s].dropna().std() * np.sqrt(252)) if len(returns[s].dropna()) > 1 else 0.0 for s in returns.columns})
        stab_all, liq_all = 1.0 / (vol_all + 1e-9), pd.Series({s: calculate_liquidity_score(str(s), candidate_map) for s in returns.columns})
        af_all, frag_all, regime_all = pd.Series(0.5, index=returns.columns), pd.Series(0.0, index=returns.columns), pd.Series(1.0, index=returns.columns)

        lookback = min(len(returns), 120)
        pe_all = pd.Series({s: calculate_permutation_entropy(returns[s].tail(lookback).to_numpy(), order=5) for s in returns.columns})
        er_all = pd.Series({s: calculate_efficiency_ratio(returns[s].tail(lookback).to_numpy()) for s in returns.columns})
        hurst_all = pd.Series({s: calculate_hurst_exponent(returns[s].to_numpy()) for s in returns.columns})

        if stats_df is not None:
            common = [s for s in returns.columns if s in stats_df.index]
            for s in common:
                af_all.loc[s] = stats_df.loc[s, "Antifragility_Score"]
                if "Fragility_Score" in stats_df.columns:
                    frag_all.loc[s] = stats_df.loc[s, "Fragility_Score"]
                if "Regime_Survival_Score" in stats_df.columns:
                    regime_all.loc[s] = stats_df.loc[s, "Regime_Survival_Score"]

        af_all = af_all * (returns.count() / 252.0).clip(upper=1.0)

        # Pillar 1: Discovery Metadata Preservation
        adx_all = pd.Series({s: float(candidate_map.get(s, {}).get("adx") or 0) for s in returns.columns})

        mps_metrics = {
            "momentum": mom_all,
            "stability": stab_all,
            "liquidity": liq_all,
            "antifragility": af_all,
            "survival": regime_all,
            "efficiency": er_all,
            "entropy": (1.0 - pe_all.fillna(1.0)).clip(0, 1),
            "hurst_clean": (1.0 - (hurst_all.fillna(0.5) - 0.5).abs() * 2.0).clip(0, 1),
            "adx": adx_all,
        }
        methods = {
            "survival": "cdf",
            "liquidity": "cdf",
            "momentum": "rank",
            "stability": "rank",
            "antifragility": "rank",
            "efficiency": "cdf",
            "entropy": "rank",
            "hurst_clean": "rank",
            "adx": "cdf",
        }

        max_f = float(frag_all.max())
        frag_penalty = (frag_all / (max_f if max_f != 0 else 1.0)).fillna(0) * 0.5
        alpha_s = self._calculate_alpha_scores(mps_metrics, methods, frag_penalty)
        alpha_scores_clean = (alpha_s if isinstance(alpha_s, pd.Series) else pd.Series(alpha_s, index=returns.columns)).copy()
        alpha_scores = alpha_scores_clean.copy()

        # CR-270: Strategy-Specific Regime Ranking
        from tradingview_scraper.pipelines.selection.rankers.regime import StrategyRegimeRanker

        ranker = StrategyRegimeRanker(enable_audit_log=False)
        # Apply ranking to the whole active universe to adjust alpha scores
        active_candidates = [{"symbol": s} for s in returns.columns]
        ranked_cands = ranker.rank(active_candidates, returns, strategy=request.strategy)

        # Create adjustment series
        # Map rank_score from [-1, 1] to a multiplier like [0.5, 1.5]
        rank_map = {c["symbol"]: c for c in ranked_cands}
        for s in alpha_scores_clean.index:
            if s in rank_map:
                r_score = rank_map[s]["rank_score"]
                # 1.0 + r_score (where r_score is usually -0.6 to 1.0 in current impl)
                multiplier = max(0.1, 1.0 + r_score)
                alpha_scores_clean.loc[s] *= multiplier
                # Store metadata for audit
                if s in candidate_map:
                    candidate_map[s].update(
                        {"rank_score": r_score, "asset_regime": rank_map[s]["asset_regime"], "asset_quadrant": rank_map[s]["asset_quadrant"], "asset_hurst": rank_map[s]["asset_hurst"]}
                    )

        shrinkage, kappa_thresh, kappa = thresholds["shr_init"], thresholds["kappa_max"], 1e20
        corr = get_robust_correlation(returns, shrinkage=shrinkage)
        if not corr.empty:
            while shrinkage <= 0.1:
                evs = np.linalg.eigvalsh(corr.values)
                kappa = float(evs.max() / (np.abs(evs).min() + 1e-15))
                if kappa <= kappa_thresh:
                    break
                shrinkage += 0.01
                corr = get_robust_correlation(returns, shrinkage=shrinkage)

        disqualified = set()

        def _record_veto(sym, reason):
            vetoes.setdefault(sym, []).append(reason)
            disqualified.add(sym)

        for s in returns.columns:
            if regime_all[s] < 0.1:
                _record_veto(str(s), "Failed Darwinian Health Gate")

        if settings.features.feat_predictability_vetoes:
            for s in returns.columns:
                if str(s) in disqualified:
                    continue
                pe, er, h = pe_all[s], er_all[s], hurst_all[s]
                if pe is not None and not np.isnan(pe) and pe > thresholds["entropy_max"]:
                    _record_veto(str(s), f"High Entropy ({pe:.4f})")
                if er is not None and not np.isnan(er) and er < thresholds["efficiency_min"]:
                    _record_veto(str(s), f"Low Efficiency ({er:.4f})")
                if h is not None and not np.isnan(h) and not candidate_map.get(str(s), {}).get("is_benchmark", False):
                    if thresholds["hurst_rw_min"] < h < thresholds["hurst_rw_max"]:
                        _record_veto(str(s), f"Random Walk (H={h:.4f})")
                if h is not None and not np.isnan(h) and h > 0.55 and mom_all[s] < 0:
                    _record_veto(str(s), f"Toxic Persistence (H={h:.4f})")

        for s in returns.columns:
            if str(s) in disqualified:
                continue
            meta = candidate_map.get(str(s)) or next((c for c in raw_candidates if c.get("identity") == str(s) or c.get("symbol") == str(s)), {})
            if any(f not in meta for f in ["tick_size", "lot_size", "price_precision"]):
                _record_veto(str(s), "Missing metadata")

        for s in returns.columns:
            if str(s) in disqualified:
                continue
            meta = candidate_map.get(str(s)) or next((c for c in raw_candidates if c.get("identity") == str(s) or c.get("symbol") == str(s)), {})
            adv = float(meta.get("value_traded") or 1e8)
            eci_raw = float(vol_all[s] * np.sqrt(1e6 / (adv if adv > 0 else 1e8)))
            current_hurdle = min(thresholds["eci_hurdle"], request.min_momentum_score - 0.05) if request.min_momentum_score < 0 else thresholds["eci_hurdle"]
            if (mom_all[s] - eci_raw) < current_hurdle and not (mom_all[s] > 1.0 and (mom_all[s] - eci_raw) >= (current_hurdle * 1.25)):
                _record_veto(str(s), f"High friction (ECI={eci_raw:.4f})")

        # Benchmark Exemption
        benchmarks = settings.benchmark_symbols
        for b in benchmarks:
            if b in returns.columns and b in disqualified:
                disqualified.remove(b)
                if b in vetoes:
                    del vetoes[b]

        for s in disqualified:
            alpha_scores.loc[s] = -1.0

        selected_symbols_dict, audit_clusters = {}, {}
        m_win_all = (1 + returns.tail(60).fillna(0.0)).prod() - 1

        for c_id, symbols in clusters.items():
            non_vetoed = [s for s in symbols if s not in disqualified]

            # STAGE 3: Factor Representation Floor
            if not non_vetoed and relaxation_stage >= 3:
                # Find best representative in cluster that isn't hard-vetoed
                candidates = [s for s in symbols if not any(v in vetoes.get(s, []) for v in ["Darwinian", "metadata"])]
                if candidates:
                    # Enforce Entropy ceiling even in Stage 3
                    valid_c = [c for c in candidates if not returns[c].dropna().empty and pe_all[c] <= 0.999]
                    if valid_c:
                        best_s = alpha_scores_clean.loc[valid_c].idxmax()
                        non_vetoed = [best_s]
                        logger.info(f"Stage 3: Forced representative {best_s} for cluster {c_id}")

            if not non_vetoed:
                continue

            # Pillar 2 - Dynamic Directions (moved from orchestrator for selection logic aware)
            # This allows Pillar 2 to influence Pillar 1 winners if enabled.
            if settings.features.feat_dynamic_direction:
                for s in non_vetoed:
                    new_dir = "LONG" if m_win_all.get(s, 0) >= 0 else "SHORT"
                    if s in candidate_map:
                        candidate_map[s]["direction"] = new_dir
                        if new_dir == "SHORT":
                            m_win_all[s] = -1.0 * m_win_all[s]

            sub_rets = returns[non_vetoed]
            actual_top_n = max(5, request.top_n)
            if settings.features.feat_dynamic_selection and len(non_vetoed) > 1:
                mean_c = float(get_robust_correlation(sub_rets, shrinkage=shrinkage).values[np.triu_indices(len(non_vetoed), k=1)].mean())
                actual_top_n = max(1, int(round(request.top_n * (1.0 - mean_c) + 0.5)))

            id_to_best = {}
            for s in non_vetoed:
                ident = candidate_map.get(s, {}).get("identity", s)
                if ident not in id_to_best or alpha_scores_clean[s] > alpha_scores_clean[id_to_best[ident]]:
                    id_to_best[ident] = s
            uniques = list(id_to_best.values())

            longs = [s for s in uniques if candidate_map.get(s, {}).get("direction", "LONG") == "LONG" and m_win_all.get(s, 0) >= request.min_momentum_score]
            shorts = [s for s in uniques if candidate_map.get(s, {}).get("direction") == "SHORT" and m_win_all.get(s, 0) >= request.min_momentum_score]

            # Protect benchmarks
            for b in benchmarks:
                if b in non_vetoed and b not in longs and b not in shorts:
                    if candidate_map.get(b, {}).get("direction", "LONG") == "LONG":
                        longs.append(b)
                    else:
                        shorts.append(b)

            c_sel = []
            if longs:
                c_sel.extend(alpha_scores_clean.loc[longs].sort_values(ascending=False).head(actual_top_n).index.tolist())
            if shorts:
                c_sel.extend(alpha_scores_clean.loc[shorts].sort_values(ascending=False).head(actual_top_n).index.tolist())
            for s_key in c_sel:
                selected_symbols_dict[s_key] = 1
            audit_clusters[int(c_id)] = {"size": len(symbols), "selected": c_sel}

        selected_symbols = list(selected_symbols_dict.keys())
        winners = [
            ({**candidate_map[s], "alpha_score": float(alpha_scores_clean[s])} if s in candidate_map else {"symbol": s, "direction": "LONG", "alpha_score": float(alpha_scores_clean[s])})
            for s in selected_symbols
        ]

        # STAGE 4: Alpha-Leader Fallback (Balanced Selection)
        if len(winners) < 15 and relaxation_stage >= 4:
            current_syms = {w["symbol"] for w in winners}
            qualified = [
                s
                for s in alpha_scores_clean.index
                if s not in current_syms and not any(v in vetoes.get(s, []) for v in ["Darwinian", "metadata"]) and not returns[s].dropna().empty and pe_all[s] <= 0.999
            ]
            others = alpha_scores_clean.loc[qualified].sort_values(ascending=False).head(15 - len(winners))
            for s, score in others.items():
                winners.append({**candidate_map.get(s, {"symbol": s, "direction": "LONG"}), "alpha_score": float(score), "selection_note": "Added via Balanced Selection fallback"})

        metrics = {"alpha_scores": alpha_scores_clean.to_dict(), "kappa": kappa, "shrinkage": shrinkage, "raw_metrics": {k: v.to_dict() for k, v in mps_metrics.items()}}
        return SelectionResponse(
            winners=winners,
            audit_clusters=audit_clusters,
            spec_version=self.spec_version,
            warnings=selection_warnings,
            vetoes=vetoes,
            metrics=metrics,
            relaxation_stage=relaxation_stage,
            active_thresholds=thresholds,
        )


class SelectionEngineV3_1(SelectionEngineV3):
    @property
    def name(self) -> str:
        return "v3.1"

    def __init__(self):
        super().__init__()
        self.kappa_threshold, self.eci_hurdle, self.spec_version = 1e20, 0.005, "3.1"


class SelectionEngineV3_2(SelectionEngineV3_1):
    @property
    def name(self) -> str:
        return "v3.2"

    def __init__(self):
        super().__init__()
        self.spec_version, self.weights = (
            "3.2",
            {
                "momentum": 1.0,
                "stability": 1.0,
                "liquidity": 1.0,
                "antifragility": 1.0,
                "survival": 1.0,
                "efficiency": 1.0,
                "adx": 1.0,
            },
        )

    def select(self, returns, raw_candidates, stats_df, request):
        s = get_settings()
        self.weights = s.features.weights_global
        return self._select_v3_core(returns, raw_candidates, stats_df, request)

    def _calculate_alpha_scores(self, mps_metrics, methods, frag_penalty):
        from tradingview_scraper.utils.scoring import map_to_probability

        probs = {n: map_to_probability(s, method=methods.get(n, "rank")) for n, s in mps_metrics.items()}
        floor, log_score = 1e-9, pd.Series(0.0, index=frag_penalty.index)
        for n, p in probs.items():
            log_score += self.weights.get(n, 1.0) * np.log(p.fillna(0.5).clip(lower=floor))

        return cast(pd.Series, np.exp(log_score + np.log((1.0 - frag_penalty).clip(lower=floor))))
