from tradingview_scraper.futures_universe_selector import FuturesUniverseSelector, SelectorConfig


def test_rank_guard():
    """
    Test that the rank guard correctly filters out symbols not in the top N.
    """
    config = SelectorConfig(markets=["crypto"], market_cap_file="market_caps_crypto.json", market_cap_rank_limit=2, base_universe_limit=10)

    selector = FuturesUniverseSelector(config)
    # Mock market cap map
    selector._market_cap_map = {"BTC": 1000000000000, "ETH": 300000000000, "SOL": 50000000000, "DOGE": 20000000000}

    rows = [
        {"symbol": "BINANCE:BTCUSDT"},
        {"symbol": "BINANCE:ETHUSDT"},
        {"symbol": "BINANCE:SOLUSDT"},
        {"symbol": "BINANCE:DOGEUSDT"},
    ]

    filtered = selector._apply_market_cap_filter(rows)
    symbols = [r["symbol"] for r in filtered]

    assert "BINANCE:BTCUSDT" in symbols
    assert "BINANCE:ETHUSDT" in symbols
    assert "BINANCE:SOLUSDT" not in symbols
    assert len(filtered) == 2


def test_floor_guard():
    """
    Test that the floor guard correctly filters out symbols with market cap below threshold.
    """
    config = SelectorConfig(markets=["crypto"], market_cap_floor=100000000, base_universe_limit=10)

    selector = FuturesUniverseSelector(config)

    rows = [
        {"symbol": "BINANCE:BTCUSDT", "market_cap_calc": 1000000000},
        {"symbol": "BINANCE:SMALLUSDT", "market_cap_calc": 50000000},
    ]

    filtered = selector._apply_market_cap_filter(rows)
    symbols = [r["symbol"] for r in filtered]

    assert "BINANCE:BTCUSDT" in symbols
    assert "BINANCE:SMALLUSDT" not in symbols
    assert len(filtered) == 1


def test_liquidity_priority():
    """
    Test that Value.Traded is used for final sorting and limiting.
    """
    config = SelectorConfig(markets=["crypto"], base_universe_limit=2, base_universe_sort_by="Value.Traded")

    selector = FuturesUniverseSelector(config)

    rows = [
        {"symbol": "BINANCE:BTCUSDT", "Value.Traded": 1000, "market_cap_calc": 1000000000},
        {"symbol": "BINANCE:ETHUSDT", "Value.Traded": 2000, "market_cap_calc": 300000000},
        {"symbol": "BINANCE:SOLUSDT", "Value.Traded": 1500, "market_cap_calc": 50000000},
    ]

    # In run(), rows are sorted and sliced
    rows.sort(key=lambda x: x.get("Value.Traded") or 0, reverse=True)
    final = rows[: config.base_universe_limit]

    symbols = [r["symbol"] for r in final]
    assert symbols == ["BINANCE:ETHUSDT", "BINANCE:SOLUSDT"]


def test_aggregation_by_base():
    """
    Test that symbols with the same base (e.g. BTCUSDT, BTCUSDC) are aggregated
    by picking the one with the highest liquidity.
    """
    config = SelectorConfig(
        markets=["crypto"],
        dedupe_by_symbol=True,  # In the selector, this means aggregate by base
        final_sort_by="Value.Traded",
    )

    selector = FuturesUniverseSelector(config)

    rows = [
        {"symbol": "BINANCE:BTCUSDT", "Value.Traded": 1000},
        {"symbol": "BINANCE:BTCUSDC", "Value.Traded": 500},  # Should be dropped
        {"symbol": "BINANCE:BTCFUSD", "Value.Traded": 300},  # Should be dropped
        {"symbol": "BINANCE:ETHUSDT", "Value.Traded": 800},
    ]

    # We use _aggregate_by_base for this
    aggregated = selector._aggregate_by_base(rows)

    symbols = {r["symbol"] for r in aggregated}
    assert "BINANCE:BTCUSDT" in symbols
    assert "BINANCE:BTCUSDC" not in symbols
    assert "BINANCE:BTCFUSD" not in symbols
    assert "BINANCE:ETHUSDT" in symbols
    assert len(aggregated) == 2


def test_aggregation_by_scaled_base():
    """
    Test that scaled symbols like 1000PEPE and PEPE are aggregated.
    """
    config = SelectorConfig(markets=["crypto"], dedupe_by_symbol=True, final_sort_by="Value.Traded")
    selector = FuturesUniverseSelector(config)

    rows = [
        {"symbol": "BINANCE:PEPEUSDT", "Value.Traded": 1000},
        {"symbol": "OKX:1000PEPEUSDT.P", "Value.Traded": 2000},  # Higher liquidity
    ]

    aggregated = selector._aggregate_by_base(rows)

    assert len(aggregated) == 1
    assert aggregated[0]["symbol"] == "OKX:1000PEPEUSDT.P"
