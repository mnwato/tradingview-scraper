from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from tradingview_scraper.pipelines.selection.adapter import SelectionPipelineAdapter
from tradingview_scraper.selection_engines.base import SelectionRequest, SelectionResponse


@pytest.fixture
def adapter():
    return SelectionPipelineAdapter()


@pytest.fixture
def mock_data():
    dates = pd.date_range("2023-01-01", periods=100)
    assets = ["BTC", "ETH"]
    returns = pd.DataFrame(np.random.normal(0, 0.01, (100, 2)), index=dates, columns=assets)

    candidates = [{"symbol": "BTC", "adx": 30.0, "value_traded": 1e9, "direction": "LONG"}, {"symbol": "ETH", "adx": 25.0, "value_traded": 5e8, "direction": "LONG"}]
    return returns, candidates


@patch("tradingview_scraper.pipelines.selection.pipeline.SelectionPipeline.run_with_data")
def test_adapter_select(mock_run, adapter, mock_data):
    returns, candidates = mock_data

    # Mock Pipeline Context Output
    mock_context = MagicMock()
    mock_context.winners = [{"symbol": "BTC", "alpha_score": 0.9}]
    mock_context.clusters = {1: ["BTC", "ETH"]}
    mock_context.inference_outputs = pd.DataFrame({"alpha_score": [0.9, 0.8]}, index=["BTC", "ETH"])
    mock_context.feature_store = pd.DataFrame({"momentum": [0.1, 0.2]}, index=["BTC", "ETH"])
    mock_context.audit_trail = [{"stage": "test", "event": "done"}]
    mock_context.params = {"relaxation_stage": 2}

    mock_run.return_value = mock_context

    request = SelectionRequest(top_n=1, threshold=0.6, max_clusters=5, params={"foo": "bar"})

    response = adapter.select(returns, candidates, None, request)

    # Check Pipeline Invocation
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["returns_df"].equals(returns)
    assert kwargs["raw_candidates"] == candidates
    assert kwargs["overrides"]["top_n"] == 1
    assert kwargs["overrides"]["cluster_threshold"] == 0.6
    assert kwargs["overrides"]["foo"] == "bar"

    # Check Response Mapping
    assert isinstance(response, SelectionResponse)
    assert len(response.winners) == 1
    assert response.winners[0]["symbol"] == "BTC"

    # Check Cluster Mapping
    # Winner is BTC. Cluster 1 has BTC and ETH.
    # Selected in cluster should be [BTC].
    audit_clusters = response.audit_clusters
    assert 1 in audit_clusters
    assert audit_clusters[1]["size"] == 2
    assert audit_clusters[1]["selected"] == ["BTC"]

    # Check Metrics
    assert "alpha_scores" in response.metrics
    assert "BTC" in response.metrics["alpha_scores"]
    assert response.metrics["alpha_scores"]["BTC"] == 0.9
    assert response.metrics["pipeline_audit"][0]["event"] == "done"
    assert response.relaxation_stage == 2
