import json
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from tradingview_scraper.pipelines.selection.base import SelectionContext
from tradingview_scraper.pipelines.selection.pipeline import SelectionPipeline
from tradingview_scraper.pipelines.selection.stages.clustering import ClusteringStage
from tradingview_scraper.pipelines.selection.stages.feature_engineering import FeatureEngineeringStage
from tradingview_scraper.pipelines.selection.stages.inference import InferenceStage
from tradingview_scraper.pipelines.selection.stages.ingestion import IngestionStage
from tradingview_scraper.pipelines.selection.stages.policy import SelectionPolicyStage
from tradingview_scraper.pipelines.selection.stages.synthesis import SynthesisStage


@pytest.fixture
def dummy_context(tmp_path):
    # Create dummy returns
    dates = pd.date_range("2023-01-01", periods=100)
    assets = ["BTC", "ETH", "SOL"]
    returns_df = pd.DataFrame(np.random.normal(0, 0.01, (100, 3)), index=dates, columns=assets)

    # Create dummy candidates
    candidates = [
        {"symbol": "BTC", "adx": 30.0, "value_traded": 1e9, "direction": "LONG"},
        {"symbol": "ETH", "adx": 25.0, "value_traded": 5e8, "direction": "LONG"},
        {"symbol": "SOL", "adx": 40.0, "value_traded": 2e8, "direction": "LONG"},
    ]

    # Save to temp files for IngestionStage
    cands_path = tmp_path / "candidates.json"
    returns_path = tmp_path / "returns.csv"

    with open(cands_path, "w") as f:
        json.dump(candidates, f)
    returns_df.to_csv(returns_path)

    ctx = SelectionContext(run_id="test_run", params={"feature_lookback": 60})
    return ctx, cands_path, returns_path, returns_df, candidates


def test_ingestion_stage(dummy_context):
    ctx, cands_path, returns_path, _, _ = dummy_context
    stage = IngestionStage(str(cands_path), str(returns_path))

    ctx = stage.execute(ctx)

    assert len(ctx.raw_pool) == 3
    assert not ctx.returns_df.empty
    assert list(ctx.returns_df.columns) == ["BTC", "ETH", "SOL"]
    assert "DataLoaded" in [e["event"] for e in ctx.audit_trail]


def test_feature_engineering_stage(dummy_context):
    ctx, _, _, returns_df, candidates = dummy_context
    ctx.returns_df = returns_df
    ctx.raw_pool = candidates

    stage = FeatureEngineeringStage()
    ctx = stage.execute(ctx)

    features = ctx.feature_store
    assert not features.empty
    expected_cols = ["momentum", "stability", "entropy", "efficiency", "hurst_clean", "adx", "liquidity", "antifragility", "survival"]
    for col in expected_cols:
        assert col in features.columns

    assert features.loc["BTC", "adx"] == 30.0


def test_inference_stage(dummy_context):
    ctx, _, _, _, _ = dummy_context
    # Mock Feature Store
    ctx.feature_store = pd.DataFrame({"momentum": [0.1, 0.2, 0.3], "entropy": [0.5, 0.6, 0.7]}, index=["BTC", "ETH", "SOL"])

    weights = {"momentum": 1.0, "entropy": 0.0}  # Ignore entropy
    stage = InferenceStage(weights=weights)
    ctx = stage.execute(ctx)

    scores = ctx.inference_outputs["alpha_score"]
    assert len(scores) == 3
    # With rank method, sorted momentum [0.1, 0.2, 0.3] -> ranks [1, 2, 3] -> probs [0.01, 0.5, 1.0] approx
    # SOL should have highest score
    assert scores["SOL"] > scores["ETH"] > scores["BTC"]


def test_clustering_stage(dummy_context):
    ctx, _, _, returns_df, _ = dummy_context
    ctx.returns_df = returns_df

    # Force params
    ctx.params["cluster_threshold"] = 0.5
    ctx.params["max_clusters"] = 3

    stage = ClusteringStage()
    ctx = stage.execute(ctx)

    assert ctx.clusters
    all_clustered = [s for cluster in ctx.clusters.values() for s in cluster]
    assert len(all_clustered) == 3
    assert set(all_clustered) == {"BTC", "ETH", "SOL"}


def test_policy_stage(dummy_context):
    ctx, _, _, _, candidates = dummy_context
    ctx.raw_pool = candidates
    # Mock inputs
    ctx.feature_store = pd.DataFrame(
        {
            "entropy": [0.1, 0.2, 0.3],
            "efficiency": [0.9, 0.8, 0.7],
            "survival": [1.0, 1.0, 1.0],
            "momentum": [0.1, 0.2, 0.3],  # Used for direction default
            "kurtosis": [5.0, 10.0, 15.0],
            "stability": [1.0, 1.0, 1.0],
        },
        index=["BTC", "ETH", "SOL"],
    )

    ctx.inference_outputs = pd.DataFrame({"alpha_score": [0.5, 0.7, 0.9]}, index=["BTC", "ETH", "SOL"])

    ctx.clusters = {1: ["BTC"], 2: ["ETH", "SOL"]}

    ctx.params = {"top_n": 1, "relaxation_stage": 1, "dynamic_direction": True}

    stage = SelectionPolicyStage()
    ctx = stage.execute(ctx)

    winners = ctx.winners
    assert len(winners) == 2  # 1 from cluster 1, 1 from cluster 2
    syms = {w["symbol"] for w in winners}
    assert "BTC" in syms
    assert "SOL" in syms  # SOL (0.9) beats ETH (0.7) in cluster 2


def test_synthesis_stage(dummy_context):
    ctx, _, _, _, _ = dummy_context
    ctx.winners = [{"symbol": "BTC", "direction": "LONG", "logic": "trend"}, {"symbol": "SOL", "direction": "SHORT", "logic": "reversion"}]

    stage = SynthesisStage()
    ctx = stage.execute(ctx)

    atoms = ctx.strategy_atoms
    assert len(atoms) == 2
    assert atoms[0].asset == "BTC"
    assert atoms[0].direction == "LONG"
    assert atoms[1].asset == "SOL"
    assert atoms[1].direction == "SHORT"

    comp = ctx.composition_map
    btc_id = atoms[0].id
    sol_id = atoms[1].id
    assert comp[btc_id]["BTC"] == 1.0
    assert comp[sol_id]["SOL"] == -1.0  # Synthetic Long normalization


@patch("tradingview_scraper.pipelines.selection.pipeline.get_settings")
def test_pipeline_integration(mock_settings, dummy_context):
    ctx, cands_path, returns_path, _, _ = dummy_context

    # Mock settings weights
    mock_settings.return_value.features.weights_global = {"momentum": 1.0, "adx": 1.0}
    mock_settings.return_value.features.entropy_max_threshold = 0.99
    mock_settings.return_value.features.efficiency_min_threshold = 0.01
    mock_settings.return_value.features.feature_lookback = 60
    mock_settings.return_value.benchmark_symbols = []
    mock_settings.return_value.top_n = 3

    pipeline = SelectionPipeline(run_id="test_int", candidates_path=str(cands_path), returns_path=str(returns_path))

    # Run pipeline
    result_ctx = pipeline.run(overrides={"top_n": 3})

    assert len(result_ctx.winners) == 3
    assert "SynthesisComplete" in [e["event"] for e in result_ctx.audit_trail]
