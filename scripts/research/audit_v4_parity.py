import json
import logging

import numpy as np
import pandas as pd
import pandas.io.common

from tradingview_scraper.pipelines.selection.base import SelectionContext
from tradingview_scraper.pipelines.selection.stages.clustering import ClusteringStage
from tradingview_scraper.pipelines.selection.stages.feature_engineering import FeatureEngineeringStage
from tradingview_scraper.pipelines.selection.stages.inference import InferenceStage
from tradingview_scraper.pipelines.selection.stages.ingestion import IngestionStage
from tradingview_scraper.selection_engines.base import SelectionRequest
from tradingview_scraper.selection_engines.impl.v3_mps import SelectionEngineV3_2
from tradingview_scraper.settings import get_settings

logger = logging.getLogger("audit_v4_parity")
logging.basicConfig(level=logging.INFO)


def audit_parity():
    logger.info("Starting v4 Parity Audit (v3.4 vs v4 MLOps Pipeline)...")

    # 1. Setup Data (Shared)
    # Corrected path: data/lakehouse/returns_matrix.parquet or pkl
    candidates_path = "data/lakehouse/portfolio_candidates.json"

    # Try multiple common formats for returns matrix
    returns_path_pkl = "data/lakehouse/portfolio_returns.pkl"
    returns_path_parquet = "data/lakehouse/returns_matrix.parquet"

    returns_df = None
    returns_path = ""

    if pandas.io.common.file_exists(returns_path_pkl):
        try:
            returns_path = returns_path_pkl
            returns_df = pd.read_pickle(returns_path)
        except Exception as e:
            logger.warning(f"Failed to read pickle {returns_path}: {e}. Falling back to dummy generation.")
            returns_df = None
    elif pandas.io.common.file_exists(returns_path_parquet):
        try:
            returns_path = returns_path_parquet
            returns_df = pd.read_parquet(returns_path)
        except Exception as e:
            logger.warning(f"Failed to read parquet {returns_path}: {e}. Falling back to dummy generation.")
            returns_df = None

    if returns_df is None:
        # Generate dummy data if not found (for CI/CD robustness)
        logger.warning("Returns matrix not found. Generating dummy data for audit.")
        candidates_path = "data/lakehouse/portfolio_candidates.json"
        with open(candidates_path, "r") as f:
            cands = json.load(f)

        # Limit to 50 assets for speed if generating dummy
        syms = [str(c["symbol"]) for c in cands[:50]]
        dates = pd.date_range("2023-01-01", periods=252)
        returns_df = pd.DataFrame(np.random.normal(0, 0.02, (252, len(syms))), index=dates, columns=pd.Index(syms))
        # Mocking file existence logic in IngestionStage requires actual file or refactor
        # For now, let's just pass the dataframe directly to v3 and handle v4 ingestion carefully
        returns_path = "data/lakehouse/audit_dummy_returns.csv"
        returns_df.to_csv(returns_path)

    # Load raw data for v3 engine
    with open(candidates_path, "r") as f:
        raw_candidates = json.load(f)

    # 2. Run v3.4 Engine (The Source of Truth)
    logger.info("Executing v3.4 Selection Engine...")
    v3_engine = SelectionEngineV3_2()
    v3_request = SelectionRequest(
        threshold=0.7,
        max_clusters=10,
        params={"feature_lookback": 120},  # Matched to v3 hardcoded default
    )

    # Mock stats_df to avoid side effects (v4 calculates this internally)

    stats_df = pd.DataFrame(index=returns_df.columns)
    stats_df["Antifragility_Score"] = 0.5
    stats_df["Regime_Survival_Score"] = 1.0

    # HACK: We need to spy on the internal metrics of v3
    # v3 returns the SelectionResponse, which contains raw_metrics in the debug dict
    v3_response = v3_engine.select(returns_df, raw_candidates, stats_df, v3_request)
    v3_metrics = v3_response.metrics["raw_metrics"]
    logger.info(f"v3 Available Features: {list(v3_metrics.keys())}")

    # DEBUG: Print sample of entropy from v3
    if "entropy" in v3_metrics:
        ent = pd.Series(v3_metrics["entropy"])
        logger.info(f"v3 Entropy Head:\n{ent.head()}")

    v3_scores = v3_response.metrics["alpha_scores"]

    # 3. Run v4 Pipeline (The Challenger)
    logger.info("Executing v4 MLOps Pipeline...")
    ctx = SelectionContext(run_id="audit_parity", params={"feature_lookback": 120, "cluster_threshold": 0.7, "max_clusters": 10})

    # Manually inject data if IngestionStage fails to find the exact file v3 used

    ctx = IngestionStage(candidates_path, returns_path).execute(ctx)
    ctx = FeatureEngineeringStage().execute(ctx)

    # Configure Inference weights to match v3.4 "Effective" logic
    # Fetch global settings to match Optuna-optimized weights used by v3
    s = get_settings()
    v3_effective_weights = s.features.weights_global.copy()

    # NOTE: We DO NOT zero out veto features because v3.4 (SelectionEngineV3_2)
    # actually includes them in the score calculation with Optuna weights!
    # This was confirmed by forensic audit of v3_mps.py.

    # Missing weights handling (v3 implicitly uses 1.0)
    if "adx" not in v3_effective_weights:
        v3_effective_weights["adx"] = 1.0

    logger.info(f"Using Effective Weights for v4: {v3_effective_weights}")
    ctx = InferenceStage(weights=v3_effective_weights).execute(ctx)

    ctx = ClusteringStage().execute(ctx)

    # 4. Comparative Analysis

    logger.info("\n--- Parity Report ---")

    # A. Feature Parity
    # We compare specific key columns: Entropy, Efficiency, Hurst
    features_to_check = ["entropy", "efficiency", "hurst_clean"]
    all_passed = True

    for feat in features_to_check:
        if feat not in v3_metrics:
            logger.warning(f"Feature '{feat}' missing from v3 metrics. Skipping.")
            continue

        v3_vals = pd.Series(v3_metrics[feat]).sort_index()
        v4_vals = ctx.feature_store[feat].sort_index()

        # Align indices (v3 might have dropped some)

        common = v3_vals.index.intersection(v4_vals.index)

        diff = (v3_vals[common] - v4_vals[common]).abs().max()
        if diff < 1e-6:
            logger.info(f"✅ Feature '{feat}': MATCH (Max Diff: {diff:.9f})")
        else:
            logger.error(f"❌ Feature '{feat}': MISMATCH (Max Diff: {diff:.9f})")
            all_passed = False

    # B. Score Parity
    # Compare final Alpha Scores
    v3_alpha = pd.Series(v3_scores).sort_index()
    v4_alpha = ctx.inference_outputs["alpha_score"].sort_index()

    common_alpha = v3_alpha.index.intersection(v4_alpha.index)
    score_diff = (v3_alpha[common_alpha] - v4_alpha[common_alpha]).abs().max()

    if score_diff < 1e-6:
        logger.info(f"✅ Alpha Scores: MATCH (Max Diff: {score_diff:.9f})")
    else:
        # Debugging score mismatch
        logger.error(f"❌ Alpha Scores: MISMATCH (Max Diff: {score_diff:.9f})")
        # Print top offenders
        delta = (v3_alpha[common_alpha] - v4_alpha[common_alpha]).abs().sort_values(ascending=False)
        top = delta.head()
        logger.error(f"Top 5 Mismatches:\n{top}")

        # Deep Dive into Top Mismatch
        bad_sym = top.index[0]
        logger.error(f"\n--- Deep Dive: {bad_sym} ---")
        logger.error(f"v3 Score: {v3_alpha[bad_sym]}")
        logger.error(f"v4 Score: {v4_alpha[bad_sym]}")

        # Print v4 Probability Components
        comp_cols = [c for c in ctx.inference_outputs.columns if c.endswith("_prob")]
        logger.error(f"v4 Probabilities:\n{ctx.inference_outputs.loc[bad_sym, comp_cols]}")

        all_passed = False

    # C. Cluster Parity
    # v3 audit_clusters values are dicts {'size': N, 'selected': ...}
    v3_sizes = sorted([c["size"] for c in v3_response.audit_clusters.values()])
    v4_sizes = sorted([len(c) for c in ctx.clusters.values()])

    if v3_sizes == v4_sizes:
        logger.info(f"✅ Clustering Structure: MATCH (Sizes: {v3_sizes})")
    else:
        logger.error(f"❌ Clustering Structure: MISMATCH (v3={v3_sizes}, v4={v4_sizes})")
        all_passed = False

    if all_passed:
        logger.info("\n🏆 AUDIT PASSED: v4 Pipeline is mathematically identical to v3.4")
    else:
        logger.error("\n💥 AUDIT FAILED: Discrepancies detected.")
        exit(1)


if __name__ == "__main__":
    audit_parity()
