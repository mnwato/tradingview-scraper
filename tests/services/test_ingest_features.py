import json
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.append(os.getcwd())

from scripts.services.ingest_features import FeatureIngestionService


@pytest.fixture
def temp_lakehouse(tmp_path):
    lake_dir = tmp_path / "data" / "lakehouse"
    lake_dir.mkdir(parents=True)
    return lake_dir


def test_fetch_technicals_single(temp_lakehouse):
    """Test fetching technicals for a single symbol."""
    service = FeatureIngestionService(lakehouse_dir=temp_lakehouse)

    # Mock Overview
    mock_data = {"status": "success", "data": {"Recommend.All": 0.5, "RSI": 60.0}}

    with patch.object(service.overview, "get_symbol_overview", return_value=mock_data) as mock_get:
        res = service.fetch_technicals_single("BINANCE:BTCUSDT")

        assert res is not None
        assert res["symbol"] == "BINANCE:BTCUSDT"
        assert res["recommend_all"] == 0.5
        assert res["rsi"] == 60.0

        # Verify call args
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "BINANCE:BTCUSDT"
        assert "RSI" in kwargs["fields"] or "RSI" in kwargs.get("fields", [])  # Depends on how Overview is mocked/called


def test_ingest_batch_writes_parquet(temp_lakehouse):
    """Test that ingest_batch writes a parquet file."""
    service = FeatureIngestionService(lakehouse_dir=temp_lakehouse)

    # Mock single fetch to return dummy data
    with patch.object(service, "fetch_technicals_single") as mock_fetch:
        mock_fetch.side_effect = lambda sym: {"symbol": sym, "rsi": 50.0}

        service.ingest_batch(["BINANCE:ETHUSDT"])

        # Check file creation
        feat_dir = temp_lakehouse / "features" / "tv_technicals_1d"
        # Find the date partition directory
        date_dirs = list(feat_dir.glob("date=*"))
        assert len(date_dirs) == 1

        # Find the parquet file
        parquet_files = list(date_dirs[0].glob("*.parquet"))
        assert len(parquet_files) == 1

        # Verify content
        df = pd.read_parquet(parquet_files[0])
        assert len(df) == 1
        assert df.iloc[0]["symbol"] == "BINANCE:ETHUSDT"
        assert df.iloc[0]["rsi"] == 50.0
        assert "timestamp" in df.columns


def test_process_candidate_file(temp_lakehouse):
    """Test loading candidates from file."""
    c_path = temp_lakehouse / "candidates.json"
    data = {"data": [{"symbol": "BINANCE:SOLUSDT"}, {"symbol": "BINANCE:AVAXUSDT"}]}
    with open(c_path, "w") as f:
        json.dump(data, f)

    service = FeatureIngestionService(lakehouse_dir=temp_lakehouse)

    with patch.object(service, "ingest_batch") as mock_ingest:
        service.process_candidate_file(c_path)

        mock_ingest.assert_called_once()
        args, _ = mock_ingest.call_args
        symbols = args[0]
        assert len(symbols) == 2
        assert "BINANCE:SOLUSDT" in symbols
