import os
import sys

import numpy as np
import pandas as pd

# Ensure imports work for local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tradingview_scraper.utils.audit import get_df_hash  # type: ignore


def test_df_hash_determinism():
    """Test that df_hash is deterministic regardless of row/column order."""
    dates = pd.date_range("2023-01-01", periods=5)
    df1 = pd.DataFrame(np.random.randn(5, 3), index=dates, columns=["A", "B", "C"])  # type: ignore

    # Shuffle columns
    df2 = df1[["C", "A", "B"]].copy()

    # Shuffle rows
    df3 = df1.sample(frac=1).copy()

    h1 = get_df_hash(df1)
    h2 = get_df_hash(df2)
    h3 = get_df_hash(df3)

    assert h1 == h2
    assert h1 == h3


def test_df_hash_empty():
    """Test hash of empty DataFrame."""
    df = pd.DataFrame()
    h = get_df_hash(df)
    assert isinstance(h, str)
    assert len(h) == 64


def test_df_hash_change_detection():
    """Test that hash changes when values change."""
    df1 = pd.DataFrame({"A": [1, 2, 3]})
    df2 = pd.DataFrame({"A": [1, 2, 4]})

    assert get_df_hash(df1) != get_df_hash(df2)
