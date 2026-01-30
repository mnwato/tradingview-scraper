import numpy as np
import pandas as pd
import pytest

from tradingview_scraper.selection_engines import SelectionEngineV2, SelectionEngineV2_0, SelectionEngineV3, SelectionRequest, SelectionResponse, build_selection_engine


def test_get_selection_engine():
    """Verify engine factory retrieves the correct classes."""
    assert isinstance(build_selection_engine("v2.0"), SelectionEngineV2_0)
    assert isinstance(build_selection_engine("v2"), SelectionEngineV2)
    assert isinstance(build_selection_engine("v3"), SelectionEngineV3)
    assert isinstance(build_selection_engine("legacy"), SelectionEngineV2_0)

    with pytest.raises(ValueError):
        build_selection_engine("unknown_engine")


@pytest.fixture
def sample_data():
    symbols = ["S1", "S2"]
    data = np.random.randn(200, 1) * 0.01 + 0.01
    # Perfectly correlated to force same cluster
    returns = pd.DataFrame({"S1": data.flatten(), "S2": data.flatten()}, index=pd.date_range("2023-01-01", periods=200))

    raw_candidates = [
        {"symbol": "S1", "identity": "1", "direction": "LONG", "value_traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "S2", "identity": "2", "direction": "LONG", "value_traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
    ]
    return returns, raw_candidates


def test_engine_v2_direct(sample_data):
    """Directly test SelectionEngineV2."""
    returns, raw_candidates = sample_data
    engine = SelectionEngineV2()
    request = SelectionRequest(top_n=1)

    response = engine.select(returns, raw_candidates, None, request)

    assert isinstance(response, SelectionResponse)
    assert response.spec_version == "2.0"
    assert len(response.winners) == 1
    assert "symbol" in response.winners[0]


def test_engine_v3_direct(sample_data):
    """Directly test SelectionEngineV3."""
    returns, raw_candidates = sample_data
    engine = SelectionEngineV3()
    request = SelectionRequest(top_n=1)

    response = engine.select(returns, raw_candidates, None, request)

    assert isinstance(response, SelectionResponse)
    assert response.spec_version == "3.0"
    assert len(response.winners) == 1
    assert response.winners[0]["symbol"] in ["S1", "S2"]


def test_v2_0_engine_direct(sample_data):
    """Directly test SelectionEngineV2_0 (formerly legacy)."""
    returns, raw_candidates = sample_data
    engine = SelectionEngineV2_0()
    request = SelectionRequest(top_n=1)

    response = engine.select(returns, raw_candidates, None, request)

    assert isinstance(response, SelectionResponse)
    assert response.spec_version == "2.0"
    assert len(response.winners) == 1


def test_v3_veto_isolation(sample_data):
    """Verify v3 engine vetos metadata-missing candidates in isolation."""
    returns, _ = sample_data
    # Symbol S2 is missing metadata
    raw_candidates = [
        {"symbol": "S1", "identity": "1", "direction": "LONG", "value_traded": 1e9, "tick_size": 0.01, "lot_size": 1, "price_precision": 2},
        {"symbol": "S2", "identity": "2", "direction": "LONG", "value_traded": 1e9},
    ]

    engine = SelectionEngineV3()
    request = SelectionRequest(top_n=2)

    response = engine.select(returns, raw_candidates, None, request)

    symbols = [w["symbol"] for w in response.winners]
    assert "S1" in symbols
    assert "S2" not in symbols
    # Verify veto reason
    assert "S2" in response.vetoes
    assert any("Missing metadata" in v for v in response.vetoes["S2"])
