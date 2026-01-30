from unittest.mock import MagicMock, patch

import pytest

from tradingview_scraper.pipelines.discovery.base import CandidateMetadata
from tradingview_scraper.pipelines.discovery.pipeline import DiscoveryPipeline


@pytest.fixture
def mock_manifest(tmp_path):
    manifest_content = {
        "profiles": {
            "test_profile": {
                "discovery": {"pipelines": {"p1": {"scanners": ["crypto/binance_spot_long_trend"], "interval": "1d"}}, "strategies": {"s1": {"scanners": ["crypto/binance_perp_long_trend"]}}}
            }
        }
    }
    manifest_path = tmp_path / "manifest.json"
    import json

    with open(manifest_path, "w") as f:
        json.dump(manifest_content, f)
    return manifest_path


@patch("tradingview_scraper.pipelines.discovery.pipeline.get_settings")
@patch("tradingview_scraper.pipelines.discovery.tradingview.TradingViewDiscoveryScanner.discover")
def test_discovery_pipeline_run_profile(mock_discover, mock_get_settings, mock_manifest):
    mock_s = MagicMock()
    mock_s.manifest_path = mock_manifest
    mock_get_settings.return_value = mock_s

    # Mock result from scanner
    mock_discover.return_value = [
        CandidateMetadata(symbol="BINANCE:BTCUSDT", exchange="BINANCE", asset_type="spot", metadata={"volume": 1e9}),
        CandidateMetadata(symbol="BINANCE:ETHUSDT.P", exchange="BINANCE", asset_type="perp", metadata={"volume": 5e8}),
    ]

    pipeline = DiscoveryPipeline(run_id="test_discovery")
    candidates = pipeline.run_profile("test_profile")

    # 2 scanners * 2 candidates = 4 candidates total
    assert len(candidates) == 4

    # Check CandidateMetadata mapping
    btc = candidates[0]
    assert isinstance(btc, CandidateMetadata)
    assert btc.symbol == "BINANCE:BTCUSDT"
    assert btc.exchange == "BINANCE"
    assert btc.asset_type == "spot"

    # Check logic injection for strategies
    # Strategies are s1, so candidates 2 and 3 should have logic="s1"
    assert candidates[2].metadata["logic"] == "s1"
    assert candidates[3].metadata["logic"] == "s1"


def test_discovery_save_candidates(tmp_path):
    pipeline = DiscoveryPipeline(run_id="test_save")
    candidates = [CandidateMetadata(symbol="BTC", exchange="BINANCE", asset_type="spot", metadata={"foo": "bar"})]

    output_dir = tmp_path / "export"
    pipeline.save_candidates(candidates, output_dir=output_dir)

    saved_file = output_dir / "candidates.json"
    assert saved_file.exists()

    import json

    with open(saved_file, "r") as f:
        data = json.load(f)
    assert data[0]["symbol"] == "BTC"
    assert data[0]["metadata"]["foo"] == "bar"
