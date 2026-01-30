import json

from tradingview_scraper.cfd_universe_selector import main as cfd_main
from tradingview_scraper.futures_universe_selector import (
    FuturesUniverseSelector,
    SelectorConfig,
)


class DummyScreener:
    def __init__(self, data=None):
        self.data = data or []
        self.calls = []

    def screen(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": "success", "data": self.data}


def test_market_cap_floor_filter(tmp_path):
    # Mock market cap file
    mc_file = tmp_path / "market_caps.json"
    mc_data = [
        {"symbol": "BTCUSD", "market_cap": 1000000},
        {"symbol": "ETHUSD", "market_cap": 500000},
        {"symbol": "DOGEUSD", "market_cap": 100000},
    ]
    mc_file.write_text(json.dumps(mc_data))

    raw_data = [
        {"symbol": "BINANCE:BTCUSDT", "Value.Traded": 1000, "volume": 100, "close": 50000, "Recommend.All": 0.5, "name": "Bitcoin"},
        {"symbol": "BINANCE:ETHUSDT", "Value.Traded": 1000, "volume": 100, "close": 3000, "Recommend.All": 0.5, "name": "Ethereum"},
        {"symbol": "BINANCE:DOGEUSDT", "Value.Traded": 1000, "volume": 100, "close": 0.1, "Recommend.All": 0.5, "name": "Dogecoin"},
    ]

    # Test floor: only BTC and ETH should pass if floor is 200,000
    cfg = SelectorConfig(
        market_cap_file=str(mc_file),
        market_cap_floor=200000,
        volume={"min": 0},
        trend={"recommendation": {"enabled": False}, "adx": {"enabled": False}, "momentum": {"enabled": False}},
    )

    selector = FuturesUniverseSelector(config=cfg, screener=DummyScreener(raw_data))
    result = selector.run()

    assert result["status"] == "success"
    assert result["total_selected"] == 2
    symbols = {r["symbol"] for r in result["data"]}
    assert "BINANCE:BTCUSDT" in symbols
    assert "BINANCE:ETHUSDT" in symbols
    assert "BINANCE:DOGEUSDT" not in symbols


def test_market_cap_rank_limit(tmp_path):
    # Mock market cap file
    mc_file = tmp_path / "market_caps.json"
    mc_data = [
        {"symbol": "BTCUSD", "market_cap": 1000000},
        {"symbol": "ETHUSD", "market_cap": 500000},
        {"symbol": "DOGEUSD", "market_cap": 100000},
    ]
    mc_file.write_text(json.dumps(mc_data))

    raw_data = [
        {"symbol": "BINANCE:BTCUSDT", "Value.Traded": 1000, "volume": 100, "close": 50000, "Recommend.All": 0.5, "name": "Bitcoin"},
        {"symbol": "BINANCE:ETHUSDT", "Value.Traded": 1000, "volume": 100, "close": 3000, "Recommend.All": 0.5, "name": "Ethereum"},
        {"symbol": "BINANCE:DOGEUSDT", "Value.Traded": 1000, "volume": 100, "close": 0.1, "Recommend.All": 0.5, "name": "Dogecoin"},
    ]

    # Test rank limit: only top 2 by market cap
    cfg = SelectorConfig(
        market_cap_file=str(mc_file),
        market_cap_rank_limit=2,
        volume={"min": 0},
        trend={"recommendation": {"enabled": False}, "adx": {"enabled": False}, "momentum": {"enabled": False}},
    )

    selector = FuturesUniverseSelector(config=cfg, screener=DummyScreener(raw_data))
    result = selector.run()

    assert result["status"] == "success"
    assert result["total_selected"] == 2
    symbols = {r["symbol"] for r in result["data"]}
    assert "BINANCE:BTCUSDT" in symbols
    assert "BINANCE:ETHUSDT" in symbols
    assert "BINANCE:DOGEUSDT" not in symbols


def test_recent_perf_filter():
    raw_data = [
        {"symbol": "BINANCE:BTCUSDT", "Value.Traded": 1000, "volume": 100, "close": 50000, "Recommend.All": 0.5, "name": "Bitcoin", "Perf.W": 5.0, "Perf.1M": 10.0},
        {"symbol": "BINANCE:ETHUSDT", "Value.Traded": 1000, "volume": 100, "close": 3000, "Recommend.All": 0.5, "name": "Ethereum", "Perf.W": 1.0, "Perf.1M": 20.0},
    ]

    # Required fields and absolute min
    cfg = SelectorConfig(
        recent_perf={"enabled": True, "required_fields": ["Perf.W", "Perf.1M"], "abs_min": {"Perf.W": 2.0}},
        volume={"min": 0},
        trend={"recommendation": {"enabled": False}, "adx": {"enabled": False}, "momentum": {"enabled": False}},
    )

    selector = FuturesUniverseSelector(config=cfg, screener=DummyScreener(raw_data))
    result = selector.run()

    assert result["status"] == "success"
    assert result["total_selected"] == 1
    assert result["data"][0]["symbol"] == "BINANCE:BTCUSDT"


def test_cfd_selector_main_smoke():
    # Just a smoke test for cfd_universe_selector.main
    # We use --dry-run to avoid actual network calls
    res = cfd_main(["--dry-run", "--limit", "5"])
    assert res == 0


def test_extract_base_quote_debug():
    from tradingview_scraper.futures_universe_selector import FuturesUniverseSelector

    base, quote = FuturesUniverseSelector._extract_base_quote("BINANCE:BTCUSDT")
    assert base == "BTC"
    assert quote == "USDT"

    base, quote = FuturesUniverseSelector._extract_base_quote("BINANCE:ETHUSDT")
    assert base == "ETH"
    assert quote == "USDT"


def test_momentum_composite():
    raw_data = [
        {"symbol": "S1", "Perf.W": 1.0, "Perf.1M": 2.0, "Value.Traded": 100, "volume": 10, "close": 10, "Recommend.All": 0.5},
        {"symbol": "S2", "Perf.W": 2.0, "Perf.1M": 4.0, "Value.Traded": 100, "volume": 10, "close": 10, "Recommend.All": 0.5},
        {"symbol": "S3", "Perf.W": 3.0, "Perf.1M": 6.0, "Value.Traded": 100, "volume": 10, "close": 10, "Recommend.All": 0.5},
    ]

    cfg = SelectorConfig(
        momentum_composite_fields=["Perf.W", "Perf.1M"],
        momentum_composite_field_name="zscore",
        volume={"min": 0},
        trend={"recommendation": {"enabled": False}, "adx": {"enabled": False}, "momentum": {"enabled": False}},
    )

    selector = FuturesUniverseSelector(config=cfg, screener=DummyScreener(raw_data))
    result = selector.run()

    assert result["status"] == "success"
    # S3 should have highest zscore
    zscores = {r["symbol"]: r["zscore"] for r in result["data"]}
    assert zscores["S3"] > zscores["S2"] > zscores["S1"]


def test_attach_perp_counterparts():
    raw_data = [
        {"symbol": "BINANCE:BTCUSDT", "Value.Traded": 1000, "volume": 100, "close": 50000, "Recommend.All": 0.5, "name": "Bitcoin"},
        {"symbol": "BINANCE:BTCUSDT.P", "Value.Traded": 2000, "volume": 200, "close": 50000, "Recommend.All": 0.5, "name": "Bitcoin Perp"},
        {"symbol": "BINANCE:ETHUSDT", "Value.Traded": 1000, "volume": 100, "close": 3000, "Recommend.All": 0.5, "name": "Ethereum"},
    ]

    cfg = SelectorConfig(
        attach_perp_counterparts=True,
        limit=2,  # Limit 2 spot symbols
        volume={"min": 0},
        trend={"recommendation": {"enabled": False}, "adx": {"enabled": False}, "momentum": {"enabled": False}},
    )

    selector = FuturesUniverseSelector(config=cfg, screener=DummyScreener(raw_data))
    result = selector.run()

    assert result["status"] == "success"
    # Should include BTC spot, ETH spot, AND BTC perp
    symbols = {r["symbol"] for r in result["data"]}
    assert "BINANCE:BTCUSDT" in symbols
    assert "BINANCE:ETHUSDT" in symbols
    assert "BINANCE:BTCUSDT.P" in symbols
