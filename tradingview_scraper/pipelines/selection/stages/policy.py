import logging
from typing import Any, Dict, List, Optional, Set

from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.pipelines.selection.base import BasePipelineStage, SelectionContext
from tradingview_scraper.pipelines.selection.filters.base import BaseFilter
from tradingview_scraper.pipelines.selection.filters.darwinian import DarwinianFilter
from tradingview_scraper.pipelines.selection.filters.friction import FrictionFilter
from tradingview_scraper.pipelines.selection.filters.predictability import PredictabilityFilter
from tradingview_scraper.settings import get_settings

logger = logging.getLogger("pipelines.selection.policy")


@StageRegistry.register(id="alpha.policy", name="Selection Policy", description="HTR recruitment and veto policy", category="alpha")
class SelectionPolicyStage(BasePipelineStage):
    """
    Stage 5: Selection Policy.
    Applies vetoes, executes Top-N recruitment per cluster, and handles HTR fallbacks.
    """

    def __init__(self, filters: Optional[List[BaseFilter]] = None):
        self.filters = filters or [DarwinianFilter(), PredictabilityFilter(), FrictionFilter()]

    @property
    def name(self) -> str:
        return "SelectionPolicy"

    def execute(self, context: SelectionContext) -> SelectionContext:
        settings = get_settings()
        params = context.params

        # 1. Gather Inputs
        if context.inference_outputs.empty or "alpha_score" not in context.inference_outputs.columns:
            logger.warning("SelectionPolicyStage: No alpha scores found. Returning empty winners.")
            context.winners = []
            return context

        scores = context.inference_outputs["alpha_score"]
        features = context.feature_store
        clusters = context.clusters

        # CR-823: Metadata Map (Standard: symbol=Atom ID)
        candidate_map: Dict[str, Any] = {str(c["symbol"]): c for c in context.raw_pool}

        relaxation_stage = int(params.get("relaxation_stage", 1))
        top_n = int(params.get("top_n", 2))

        # 2. Apply Vetoes (Modular Filter Chain)
        disqualified: Set[str] = set()
        for f in self.filters:
            _, vetoed = f.apply(context)
            disqualified.update(vetoed)

        # Ensure benchmark exemption
        for b_idx in settings.benchmark_symbols:
            b = str(b_idx)
            if b in disqualified:
                disqualified.remove(b)

        # Ensure we only consider candidates from the provided raw_pool (Intent Preservation)
        eligible_pool = set(candidate_map.keys())
        logger.info(f"DEBUG: Policy Stage Eligible Pool Size: {len(eligible_pool)}")
        if len(eligible_pool) > 0:
            logger.info(f"DEBUG: Eligible Sample: {list(eligible_pool)[:5]}")

        # 3. Recruitment Loop
        recruitment_buffer: Set[str] = set()

        # CR-835: Pluggable Ranking (v3.6.4)
        # Delegate sorting logic to the configured Ranker
        from tradingview_scraper.pipelines.selection.rankers.factory import RankerFactory

        ranker_method = settings.ranking.method
        ranker_config = {}
        # Special case: If method is "signal" but not configured, check dominant signal?
        # But 'ranking' in settings is just (method, direction).
        # We can map 'dominant_signal' to a SignalRanker if method is 'mps' but dominant_signal is set?
        # NO, stick to the plan: MPS is default. Signal Dominance is handled inside MPS scoring.
        # But user requested "default to original mps alpha score ranking, for ratings ma, use ratings ma as primary drive".
        # This is already handled by the MPS weight override in inference.py.
        # So we just need to use the Ranker interface to wrap the sort.

        ranker = RankerFactory.get_ranker(ranker_method, ranker_config)
        is_ascending = settings.ranking.direction == "ascending"

        def _get_score(s_id: str) -> float:
            val = scores.get(s_id)
            return float(val) if val is not None else -1.0

        # Cluster Recruitment
        for cid, symbols in clusters.items():
            # Prune symbols not in eligible pool or vetoed
            non_vetoed = [str(s) for s in symbols if str(s) in eligible_pool and str(s) not in disqualified]
            if not non_vetoed:
                # STAGE 3: Force Representative if Cluster Empty
                if relaxation_stage >= 3 and symbols:
                    sym_list = [str(s) for s in symbols]
                    # Use Ranker
                    all_ranked = ranker.rank(sym_list, context, ascending=is_ascending)
                    for s in all_ranked:
                        # Defensive float conversion for entropy
                        ent = 1.0
                        if s in features.index:
                            try:
                                ent_val = features.loc[s, "entropy"]
                                ent = float(ent_val) if ent_val is not None else 1.0
                            except (TypeError, ValueError):
                                ent = 1.0
                        if ent <= 0.999:
                            recruitment_buffer.add(s)
                            break
                continue

            # Identity-Based Deduplication (CR-231)
            # Ensures we don't pick multiple logic-atoms for the same asset in one cluster
            id_to_best: Dict[str, str] = {}
            for s in non_vetoed:
                ident = str(candidate_map.get(s, {}).get("identity", s))

                # Robust score retrieval
                c_val = scores.get(s)
                current_score = float(c_val) if c_val is not None else -1.0

                update = False
                if ident not in id_to_best:
                    update = True
                else:
                    b_val = scores.get(id_to_best[ident])
                    best_score = float(b_val) if b_val is not None else -1.0

                    if is_ascending:
                        # Better = Lower
                        if current_score < best_score:
                            update = True
                    else:
                        # Better = Higher (Default)
                        if current_score > best_score:
                            update = True

                if update:
                    id_to_best[ident] = s
            uniques = list(id_to_best.values())

            # Directional Recruitment (Pillar 1 Parity with v3.4)
            # Pick Top-N per direction per cluster
            longs = []
            shorts = []
            for s in uniques:
                item_meta = candidate_map.get(s, {})
                # CR-823: Respect Discovery Intent for recruitment partitioning
                item_dir = str(item_meta.get("direction") or "").upper()
                if item_dir not in ["LONG", "SHORT"]:
                    mom = float(features.loc[s, "momentum"]) if s in features.index else 0.0
                    item_dir = "LONG" if mom >= 0 else "SHORT"

                if item_dir == "LONG":
                    longs.append(s)
                else:
                    shorts.append(s)

            if longs:
                # Use Ranker
                ranked_longs = ranker.rank(longs, context, ascending=is_ascending)
                recruitment_buffer.update(ranked_longs[:top_n])

            # CR-822: Directional Integrity
            # Only recruit SHORTS if specifically enabled in settings
            if shorts and settings.features.feat_short_direction:
                ranked_shorts = ranker.rank(shorts, context, ascending=is_ascending)
                recruitment_buffer.update(ranked_shorts[:top_n])

        # STAGE 4: Balanced Fallback
        # CR-825: Enforce strict floor of 15 assets to prevent optimizer degeneration
        target_floor = 15
        if len(recruitment_buffer) < target_floor and relaxation_stage >= 4:
            needed = target_floor - len(recruitment_buffer)

            # CR-822/CR-823: Directional-Aware Fallback
            def _is_allowed(s_id: str) -> bool:
                if not settings.features.feat_short_direction:
                    # If SHORTS disabled, verify item isn't short
                    # First check discovery intent
                    meta = candidate_map.get(s_id, {})
                    if str(meta.get("direction")).upper() == "SHORT":
                        return False
                    # Then check momentum if intent missing
                    if not meta.get("direction"):
                        mom = float(features.loc[s_id, "momentum"]) if s_id in features.index else 0.0
                        if mom < 0:
                            return False
                return True

            valid_pool = [str(s) for s in scores.index if str(s) in eligible_pool and str(s) not in recruitment_buffer and str(s) not in disqualified and _is_allowed(str(s))]
            global_ranked = ranker.rank(valid_pool, context, ascending=is_ascending)
            recruitment_buffer.update(global_ranked[:needed])

            # CR-826: Absolute Scarcity Fallback (Ignore Vetoes if still under floor)
            if len(recruitment_buffer) < target_floor:
                needed_now = target_floor - len(recruitment_buffer)
                desperation_pool = [str(s) for s in scores.index if str(s) in eligible_pool and str(s) not in recruitment_buffer and _is_allowed(str(s))]
                desperation_ranked = ranker.rank(desperation_pool, context, ascending=is_ascending)
                recruitment_buffer.update(desperation_ranked[:needed_now])

        # 4. Finalize Winners & Apply Pool Sizing (Pillar 1)
        winners = []

        # Sort buffer by absolute conviction
        sorted_buffer = ranker.rank(list(recruitment_buffer), context, ascending=is_ascending)

        # Institutional Cap: Max 25 assets to maintain high weight fidelity
        # Delegation: Directional balance and other risk constraints are handled in Pillar 3
        target_size = min(25, len(sorted_buffer))
        final_selected = sorted_buffer[:target_size]

        for s in final_selected:
            meta = candidate_map.get(s, {"symbol": s}).copy()

            # Robust score retrieval
            score_val = scores.get(s)
            meta["alpha_score"] = float(score_val) if score_val is not None else 0.0

            # CR-831: Preserve Canonical Identity
            # symbol=Atom ID, physical_symbol=Exchange:Ticker
            # Both are already in meta from SelectTopUniverse

            # CR-823: Respect Discovery Direction
            discovery_direction = meta.get("direction")
            if discovery_direction and str(discovery_direction).upper() in ["LONG", "SHORT"]:
                meta["direction"] = str(discovery_direction).upper()
            else:
                mom = float(features.loc[s, "momentum"]) if s in features.index else 0.0
                meta["direction"] = "LONG" if mom >= 0 else "SHORT"

            logger.info(f"DEBUG: Winner {s} Direction: {meta['direction']} (Disc: {discovery_direction})")
            winners.append(meta)

        context.winners = winners
        n_shorts_final = len([w for w in winners if w["direction"] == "SHORT"])
        logger.info(f"Policy Result: {len(winners)} winners recruited ({n_shorts_final} shorts).")
        context.log_event(self.name, "SelectionComplete", {"stage": relaxation_stage, "n_winners": len(winners), "n_vetoed": len(disqualified), "n_shorts": n_shorts_final})

        return context
