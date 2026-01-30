import logging
from typing import Dict, Optional

import pandas as pd

from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.pipelines.selection.base import BasePipelineStage, SelectionContext
from tradingview_scraper.utils.scoring import calculate_mps_score, map_to_probability

logger = logging.getLogger("pipelines.selection.inference")


@StageRegistry.register(id="alpha.inference", name="Inference", description="Conviction scoring using Log-MPS", category="alpha")
class InferenceStage(BasePipelineStage):
    """
    Stage 3: Conviction Scoring (Inference).
    Applies the Log-MPS (Multiplicative Probability Scoring) model to the Feature Store.
    """

    @property
    def name(self) -> str:
        return "Inference"

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        # Default Weights (v3.5.9 Standard)
        self.weights = weights or {
            "momentum": 1.5,
            "stability": 1.0,
            "liquidity": 0.5,
            "entropy": 1.0,
            "efficiency": 0.5,
            "hurst_clean": 0.5,
            "adx": 1.0,
            "recommend_all": 1.0,
            "recommend_ma": 1.0,
            "survival": 1.0,
            "antifragility": 0.5,
            "skew": 0.5,  # Penalize asymmetry via rank_desc
            "kurtosis": 1.0,  # Heavily penalize fat tails via rank_desc
            "cvar": 1.0,
        }

        # Mapping Methods (v3.5.9 Standard)
        self.methods = {
            "survival": "cdf",
            "liquidity": "cdf",
            "momentum": "rank",
            "stability": "rank",
            "antifragility": "rank",
            "efficiency": "cdf",
            "entropy": "rank_desc",
            "hurst_clean": "rank",
            "adx": "cdf",
            "recommend_all": "rank",
            "recommend_ma": "rank",
            "skew": "rank_desc",  # Larger absolute skew is worse
            "kurtosis": "rank_desc",  # Larger kurtosis is worse
            "cvar": "cdf",
        }

    def execute(self, context: SelectionContext) -> SelectionContext:
        features = context.feature_store
        if features.empty:
            logger.warning("InferenceStage: Feature store is empty. Skipping.")
            return context

        logger.info("Executing Log-MPS Inference...")

        # 1. Map Features to Probabilities
        # We only map features that exist in both the store and our config
        active_features = [str(f) for f in features.columns if f in self.weights]

        # Helper: Get series for scoring
        metrics_dict: Dict[str, pd.Series] = {}
        for f in active_features:
            f_str = str(f)
            val = features[f_str]
            if isinstance(val, pd.Series):
                metrics_dict[f_str] = val
            elif isinstance(val, pd.DataFrame):
                metrics_dict[f_str] = val.iloc[:, 0]
            else:
                metrics_dict[f_str] = pd.Series(val)

        # 2. Calculate Final Alpha Score
        # This reuses the validated logic from utils.scoring
        alpha_scores = calculate_mps_score(metrics=metrics_dict, weights=self.weights, methods=self.methods)

        # 3. Store Results
        # We store both the final score and the component probabilities for explainability
        outputs = pd.DataFrame(index=features.index)
        outputs["alpha_score"] = alpha_scores

        # Add component probabilities for audit
        for f in active_features:
            f_str = str(f)
            s_val = metrics_dict[f_str]
            outputs[f"{f_str}_prob"] = map_to_probability(s_val, method=self.methods.get(f_str, "rank"))

        context.inference_outputs = outputs

        context.model_metadata = {"model": "Log-MPS-v4", "weights": self.weights, "methods": self.methods}

        context.log_event(self.name, "ScoringComplete", {"mean_score": float(alpha_scores.mean()), "max_score": float(alpha_scores.max())})

        return context
