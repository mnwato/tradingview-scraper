import os
from datetime import datetime

import pandas as pd
import pytest


def test_portfolio_returns_freshness():
    """Verify that all assets in the returns matrix reach the current market date."""
    returns_path = "data/lakehouse/portfolio_returns.pkl"
    assert os.path.exists(returns_path), "Returns matrix missing"

    df = pd.read_pickle(returns_path)
    last_date = pd.to_datetime(df.index.max()).tz_localize(None)

    # Current date (approximate for test validation)
    # We expect 2026-01-09 or 2026-01-08 depending on session close
    expected_min_date = datetime(2026, 1, 8)
    assert last_date >= expected_min_date, f"Data is stale: last date {last_date} < {expected_min_date}"


def test_no_stale_assets_in_returns():
    """Verify that no individual column in the returns matrix is stale."""
    returns_path = "data/lakehouse/portfolio_returns.pkl"
    df = pd.read_pickle(returns_path)

    # Check each column's last non-nan value date
    for col in df.columns:
        last_val_date = pd.to_datetime(df[col].dropna().index.max()).tz_localize(None)
        assert last_val_date >= datetime(2026, 1, 7), f"Asset {col} is stale: last date {last_val_date}"


def test_secular_depth():
    """Verify that the returns matrix has sufficient depth (e.g. > 300 days)."""
    returns_path = "data/lakehouse/portfolio_returns.pkl"
    df = pd.read_pickle(returns_path)

    assert len(df) >= 300, f"Insufficient depth: {len(df)} rows"


def test_selection_audit_integrity():
    """Verify that the selection audit ledger exists and records recent recovery actions."""
    audit_path = "data/lakehouse/selection_audit.json"
    assert os.path.exists(audit_path), "Selection audit ledger missing"

    import json

    with open(audit_path, "r") as f:
        audit = json.load(f)

    # Check if there are any entries (if it's a dict, check if it's non-empty)
    if isinstance(audit, dict):
        assert len(audit) > 0, "Audit ledger dictionary is empty"
    elif isinstance(audit, list):
        assert len(audit) > 0, "Audit ledger list is empty"
    else:
        pytest.fail(f"Unexpected audit ledger type: {type(audit)}")

    # Verify it's valid JSON
    assert audit is not None
