import pandas as pd
import pytest

from tradingview_scraper.pipelines.meta.aggregator import SleeveAggregator
from tradingview_scraper.pipelines.meta.flattener import WeightFlattener


def test_sleeve_aggregator():
    dates = pd.date_range("2025-01-01", periods=5, freq="D")
    s1 = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01], index=dates, name="s1")
    s2 = pd.Series([0.005, -0.005, 0.01, 0.01, 0.02], index=dates, name="s2")

    # Missing one date in s2
    s2_missing = s2.iloc[:-1]

    aggregator = SleeveAggregator()

    # Test inner join
    meta_df = aggregator.aggregate({"s1": s1, "s2": s2_missing}, join_method="inner")
    assert len(meta_df) == 4
    assert list(meta_df.columns) == ["s1", "s2"]

    # Test outer join
    meta_df_outer = aggregator.aggregate({"s1": s1, "s2": s2_missing}, join_method="outer")
    assert len(meta_df_outer) == 5
    assert pd.isna(meta_df_outer.loc[dates[-1], "s2"])


def test_weight_flattener():
    meta_weights = pd.Series({"s1": 0.6, "s2": 0.4})

    s1_weights = pd.DataFrame({"Symbol": ["BTC", "ETH"], "Weight": [0.7, 0.3], "Direction": ["LONG", "LONG"]})

    s2_weights = pd.DataFrame(
        {
            "Symbol": ["BTC", "SOL"],
            "Weight": [0.5, 0.5],
            "Direction": ["SHORT", "LONG"],  # Overlap BTC with different direction
        }
    )

    flattener = WeightFlattener()
    flattened = flattener.flatten(meta_weights, {"s1": s1_weights, "s2": s2_weights})

    # BTC net weight = (0.7 * 0.6) + (-0.5 * 0.4) = 0.42 - 0.20 = 0.22
    # ETH weight = 0.3 * 0.6 = 0.18
    # SOL weight = 0.5 * 0.4 = 0.20

    # In my current flattener implementation, it groups by (Symbol, Direction)
    # So BTC LONG and BTC SHORT are separate rows if they have different directions.

    btc_long = flattened[(flattened["Symbol"] == "BTC") & (flattened["Direction"] == "LONG")]
    btc_short = flattened[(flattened["Symbol"] == "BTC") & (flattened["Direction"] == "SHORT")]

    assert btc_long["Weight"].iloc[0] == pytest.approx(0.42)
    assert btc_short["Weight"].iloc[0] == pytest.approx(0.20)
    assert btc_short["Net_Weight"].iloc[0] == pytest.approx(-0.20)

    eth = flattened[flattened["Symbol"] == "ETH"]
    assert eth["Weight"].iloc[0] == pytest.approx(0.18)
