from unittest.mock import patch

import pandas as pd
import pytest

# Import the script's function
from scripts.maintenance.cleanup_metadata_catalog import cleanup_metadata_catalog


@pytest.fixture
def mock_catalogs(tmp_path):
    """Sets up mock MetadataCatalog and ExchangeCatalog with temporary paths."""
    with patch("scripts.maintenance.cleanup_metadata_catalog.MetadataCatalog") as MockMeta, patch("scripts.maintenance.cleanup_metadata_catalog.ExchangeCatalog") as MockEx:
        # Mock MetadataCatalog
        meta_inst = MockMeta.return_value
        meta_inst._df = pd.DataFrame(
            columns=[
                "symbol",
                "exchange",
                "base",
                "quote",
                "type",
                "subtype",
                "profile",
                "description",
                "sector",
                "industry",
                "country",
                "pricescale",
                "minmov",
                "tick_size",
                "lot_size",
                "contract_size",
                "timezone",
                "session",
                "active",
                "updated_at",
                "valid_from",
                "valid_until",
            ]
        )

        # Mock ExchangeCatalog
        ex_inst = MockEx.return_value
        ex_inst._df = pd.DataFrame(columns=["exchange", "country", "timezone", "is_crypto", "description", "updated_at"])
        ex_inst.get_exchange.side_effect = lambda name: None  # Simulate FOREX missing

        yield MockMeta, MockEx, meta_inst, ex_inst


def test_cleanup_metadata_catalog_injects_forex(mock_catalogs):
    """Test that cleanup_metadata_catalog injects FOREX metadata if missing."""
    MockMeta, MockEx, meta_inst, ex_inst = mock_catalogs

    # We need to mock ExchangeCatalog within the script's execution context if it's imported there
    # or ensure cleanup_metadata_catalog uses it.
    # Looking at cleanup_metadata_catalog.py, it doesn't currently use ExchangeCatalog.
    # This test WILL FAIL until we implement the requirement.

    cleanup_metadata_catalog()

    # Verify that upsert_exchange was called with FOREX
    calls = [call for call in ex_inst.upsert_exchange.call_args_list if call.args[0]["exchange"] == "FOREX"]
    assert len(calls) > 0, "FOREX metadata was not injected into ExchangeCatalog"

    forex_data = calls[0].args[0]
    assert forex_data["timezone"] == "America/New_York"
    assert forex_data["is_crypto"] is False


def test_cleanup_metadata_catalog_resolves_scd_duplicates(mock_catalogs):
    """Test that cleanup_metadata_catalog correctly resolves SCD Type 2 duplicates."""
    MockMeta, MockEx, meta_inst, ex_inst = mock_catalogs

    # Create duplicates: 3 records for the same symbol, 2 are "active" (missing valid_until)
    ts1 = pd.Timestamp("2025-01-01 10:00:00")
    ts2 = pd.Timestamp("2025-01-01 11:00:00")
    ts3 = pd.Timestamp("2025-01-01 12:00:00")

    cols = [
        "symbol",
        "exchange",
        "base",
        "quote",
        "type",
        "subtype",
        "profile",
        "description",
        "sector",
        "industry",
        "country",
        "pricescale",
        "minmov",
        "tick_size",
        "lot_size",
        "contract_size",
        "timezone",
        "session",
        "active",
        "updated_at",
        "valid_from",
        "valid_until",
    ]

    meta_inst._df = pd.DataFrame(
        [
            {"symbol": "TEST:SYM", "exchange": "TEST", "updated_at": ts1, "valid_from": ts1, "valid_until": None, "active": True, "pricescale": 100, "minmov": 1},
            {"symbol": "TEST:SYM", "exchange": "TEST", "updated_at": ts2, "valid_from": ts2, "valid_until": None, "active": True, "pricescale": 100, "minmov": 1},
            {"symbol": "TEST:SYM", "exchange": "TEST", "updated_at": ts3, "valid_from": ts3, "valid_until": None, "active": True, "pricescale": 100, "minmov": 1},
        ],
        columns=cols,
    )

    cleanup_metadata_catalog()

    # After cleanup, we should have:
    # 1. The latest record (ts3) remains active (valid_until is None)
    # 2. Older records (ts1, ts2) have valid_until set
    # 3. valid_until of ts1 should be valid_from of ts2
    # 4. valid_until of ts2 should be valid_from of ts3

    # Note: cleanup_metadata_catalog saves the catalog, so we check meta_inst._df if it was modified in place
    # or if catalog.save() was called with a new df.
    # The current implementation of cleanup_metadata_catalog does:
    # catalog._df = cleaned_df
    # catalog.save()

    cleaned_df = meta_inst._df
    assert len(cleaned_df) == 3

    # Sort by valid_from to check sequence
    cleaned_df = cleaned_df.sort_values("valid_from")

    records = cleaned_df.to_dict("records")

    assert records[2]["valid_from"] == ts3
    assert pd.isna(records[2]["valid_until"])  # Latest is active

    assert records[1]["valid_from"] == ts2
    assert records[1]["valid_until"] == ts3  # Previous record ends when next starts

    assert records[0]["valid_from"] == ts1
    assert records[0]["valid_until"] == ts2  # First record ends when second starts
