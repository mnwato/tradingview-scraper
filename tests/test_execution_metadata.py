import os

import pytest

from tradingview_scraper.execution.metadata import ExecutionLimits, ExecutionMetadataCatalog, MissingMetadataError


@pytest.fixture
def temp_catalog_path(tmp_path):
    return str(tmp_path)


def test_initialization(temp_catalog_path):
    catalog = ExecutionMetadataCatalog(base_path=temp_catalog_path)
    assert catalog._df.empty
    # We don't strictly require the file to exist on init anymore, but let's check it doesn't crash
    catalog.save()
    assert os.path.exists(os.path.join(temp_catalog_path, "execution.parquet"))


def test_upsert_and_retrieval(temp_catalog_path):
    catalog = ExecutionMetadataCatalog(base_path=temp_catalog_path)

    limits_data = [
        {
            "symbol": "BINANCE:BTCUSDT",
            "venue": "BINANCE",
            "lot_size": 0.00001,
            "min_notional": 5.0,
            "step_size": 0.00001,
            "tick_size": 0.01,
            "maker_fee": 0.001,
            "taker_fee": 0.001,
            "contract_size": 1.0,
        }
    ]

    catalog.upsert_limits(limits_data)

    # Test Retrieval
    limits = catalog.get_limits("BINANCE:BTCUSDT", "BINANCE")
    assert isinstance(limits, ExecutionLimits)
    assert limits.symbol == "BINANCE:BTCUSDT"
    assert limits.lot_size == 0.00001
    assert limits.min_notional == 5.0

    # Test Persistence (reload)
    catalog2 = ExecutionMetadataCatalog(base_path=temp_catalog_path)
    limits2 = catalog2.get_limits("BINANCE:BTCUSDT", "BINANCE")
    assert limits2.min_notional == 5.0


def test_update_existing(temp_catalog_path):
    catalog = ExecutionMetadataCatalog(base_path=temp_catalog_path)

    # Initial insert
    catalog.upsert_limits([{"symbol": "BINANCE:BTCUSDT", "venue": "BINANCE", "min_notional": 5.0}])

    # Update with new value
    catalog.upsert_limits([{"symbol": "BINANCE:BTCUSDT", "venue": "BINANCE", "min_notional": 10.0}])

    limits = catalog.get_limits("BINANCE:BTCUSDT", "BINANCE")
    assert limits.min_notional == 10.0
    # Should only have one entry for this symbol/venue combo
    assert len(catalog._df) == 1


def test_strict_mode(temp_catalog_path):
    catalog = ExecutionMetadataCatalog(base_path=temp_catalog_path)

    # Missing symbol
    assert catalog.get_limits("UNKNOWN", "BINANCE", strict=False) is None

    with pytest.raises(MissingMetadataError):
        catalog.get_limits("UNKNOWN", "BINANCE", strict=True)


def test_empty_catalog_strict(temp_catalog_path):
    catalog = ExecutionMetadataCatalog(base_path=temp_catalog_path)
    # Ensure empty catalog raises error in strict mode
    with pytest.raises(MissingMetadataError):
        catalog.get_limits("ANYTHING", "ANYWHERE", strict=True)
