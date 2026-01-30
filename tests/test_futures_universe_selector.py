import pytest

from tradingview_scraper.futures_universe_selector import (
    FuturesUniverseSelector,
    ScreenConfig,
    SelectorConfig,
    _format_markdown_table,
    load_config,
)


class DummyScreener:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def screen(self, **kwargs):
        self.calls.append(kwargs)
        return self.payload


def test_load_config_overrides():
    cfg = load_config(None, overrides={"limit": 5, "volume": {"min": 123}})
    assert isinstance(cfg, SelectorConfig)
    assert cfg.limit == 5
    assert cfg.volume.min == 123


def test_dry_run_returns_payload():
    selector = FuturesUniverseSelector(
        config={"limit": 10, "pagination_size": 5},
        screener=DummyScreener({"status": "success", "data": []}),
    )

    result = selector.run(dry_run=True)
    assert result["status"] == "dry_run"
    assert result["payloads"]
    first_payload = result["payloads"][0]
    assert first_payload["limit"] == 10
    assert first_payload["pagination_size"] == 5


def test_selector_filters_and_passes():
    screener = DummyScreener(
        {
            "status": "success",
            "data": [
                {
                    "symbol": "NYMEX:CL1!",
                    "name": "WTI",
                    "close": 80.0,
                    "volume": 5000,
                    "change": 1.2,
                    "Recommend.All": 0.4,
                    "ADX": 25,
                    "Volatility.D": 5.0,
                    "Perf.1M": 0.02,
                    "Perf.3M": 0.10,
                },
                {
                    "symbol": "CME:ES1!",
                    "name": "ES",
                    "close": 5000.0,
                    "volume": 500,
                    "change": 0.5,
                    "Recommend.All": 0.5,
                    "ADX": 30,
                    "Volatility.D": 3.0,
                    "Perf.1M": 0.01,
                    "Perf.3M": 0.02,
                },
                {
                    "symbol": "ICEUS:SB1!",
                    "name": "Sugar",
                    "close": 20.0,
                    "volume": 4000,
                    "change": 0.3,
                    "Recommend.All": 0.35,
                    "ADX": 22,
                    "ATR": 1.0,
                    "Perf.1M": 0.03,
                    "Perf.3M": 0.04,
                },
            ],
            "total": 3,
        }
    )

    selector = FuturesUniverseSelector(
        config={
            "limit": 10,
            "volume": {"min": 1000},
            "volatility": {"max": 6.0, "atr_pct_max": 0.1},
            "trend": {
                "logic": "AND",
                "recommendation": {"min": 0.3},
                "adx": {"min": 20},
                "momentum": {"horizons": {"Perf.1M": 0, "Perf.3M": 0}},
            },
        },
        screener=screener,
    )

    result = selector.run()
    assert result["status"] == "success"
    assert result["total_candidates"] == 3
    assert result["total_selected"] == 2

    symbols = {row["symbol"] for row in result["data"]}
    assert "NYMEX:CL1!" in symbols
    assert "ICEUS:SB1!" in symbols
    assert "CME:ES1!" not in symbols  # filtered by liquidity

    for row in result["data"]:
        assert row.get("passes", {}).get("all") is True
        if row["symbol"] == "ICEUS:SB1!":
            # ATR fallback used to compute atr_pct
            assert pytest.approx(row.get("atr_pct"), rel=1e-3) == 0.05


def test_daily_timeframe_defaults_change_and_perf_w():
    screener = DummyScreener(
        {
            "status": "success",
            "data": [
                {
                    "symbol": "TEST:FX1!",
                    "name": "FX1!",
                    "close": 100.0,
                    "volume": 20000,
                    "change": 1.0,
                    "Perf.W": 1.5,
                    "Recommend.All": 0.5,
                    "ADX": 30.0,
                }
            ],
        }
    )

    selector = FuturesUniverseSelector(
        config={
            "limit": 5,
            "trend": {
                "timeframe": "daily",
                "recommendation": {"min": 0.3},
                "adx": {"min": 20},
            },
        },
        screener=screener,
    )

    result = selector.run()
    assert result["status"] == "success"
    assert result["total_selected"] == 1
    passes = result["data"][0].get("passes", {})
    assert passes.get("trend_momentum") is True


def test_format_markdown_table():
    rows = [
        {
            "symbol": "COMEX:GC1!",
            "name": "Gold",
            "close": 4373.91234,
            "volume": 205686,
            "Recommend.All": 0.5575757,
        },
        {
            "symbol": "COMEX:SI1!",
            "name": "Silver",
            "close": 66.901,
            "volume": 145011,
            "Recommend.All": 0.60303,
        },
    ]

    table = _format_markdown_table(rows, ["symbol", "name", "close", "volume", "Recommend.All"])

    lines = table.splitlines()
    assert lines[0].startswith("| symbol | name | close | volume | Recommend.All |")
    assert "4373.91" in table
    assert "145011" in table


def test_multi_screen_passes_all():
    payload = {
        "status": "success",
        "data": [
            {
                "symbol": "CME:GC1!",
                "name": "Gold",
                "close": 4375.0,
                "volume": 5000,
                "Recommend.All": 0.5,
                "ADX": 25,
                "Volatility.D": 4.0,
                "Perf.W": 1.2,
                "Perf.1M": 2.5,
                "Perf.3M": 5.0,
                "RSI": 60,
            }
        ],
    }

    cfg = SelectorConfig(
        volume={"min": 0},
        volatility={"min": None, "max": None, "fallback_use_atr_pct": False},
        trend={
            "recommendation": {"enabled": False},
            "adx": {"enabled": False},
            "momentum": {"enabled": False},
            "confirmation_momentum": {"enabled": False},
        },
        trend_screen=ScreenConfig(
            timeframe="daily",
            direction="long",
            recommendation={"enabled": True, "min": 0.2},
            adx={"enabled": True, "min": 10},
            momentum={"enabled": True, "horizons": {"Perf.W": 0.5}},
            osc={"enabled": True, "horizons": {"RSI": 70}},
        ),
        confirm_screen=ScreenConfig(
            timeframe="daily",
            direction="long",
            momentum={"enabled": True, "horizons": {"Perf.1M": 1.0}},
        ),
        execute_screen=ScreenConfig(
            timeframe="daily",
            direction="long",
            momentum={"enabled": True, "horizons": {"Perf.W": 0.5}},
            osc={"enabled": True, "horizons": {"RSI": 70}},
        ),
    )

    selector = FuturesUniverseSelector(config=cfg, screener=DummyScreener(payload))
    result = selector.run()
    assert result["status"] == "success"
    assert result["total_selected"] == 1
    row = result["data"][0]
    assert row["passes"]["all"] is True
    assert row["passes"].get("trend_screen_combined") is True
    assert row["passes"].get("confirm_screen_combined") is True
    assert row["passes"].get("execute_screen_combined") is True


def test_multi_screen_fails_confirmation():
    payload = {
        "status": "success",
        "data": [
            {
                "symbol": "CME:GC1!",
                "name": "Gold",
                "close": 4375.0,
                "volume": 5000,
                "Recommend.All": 0.5,
                "ADX": 25,
                "Volatility.D": 4.0,
                "Perf.W": 0.2,
                "Perf.1M": 0.1,
                "Perf.3M": 0.2,
                "RSI": 60,
            }
        ],
    }

    cfg = SelectorConfig(
        volume={"min": 0},
        volatility={"min": None, "max": None, "fallback_use_atr_pct": False},
        trend={
            "recommendation": {"enabled": False},
            "adx": {"enabled": False},
            "momentum": {"enabled": False},
        },
        trend_screen=ScreenConfig(
            timeframe="daily",
            direction="long",
            recommendation={"enabled": True, "min": 0.2},
            momentum={"enabled": True, "horizons": {"Perf.W": 0.1}},
        ),
        confirm_screen=ScreenConfig(
            timeframe="daily",
            direction="long",
            momentum={"enabled": True, "horizons": {"Perf.1M": 0.5}},
        ),
    )

    selector = FuturesUniverseSelector(config=cfg, screener=DummyScreener(payload))
    result = selector.run()
    assert result["status"] == "success"
    assert result["total_selected"] == 0
    assert result["data"] == []


def test_dedupe_by_symbol_keeps_best_volume():
    payload = {
        "status": "success",
        "data": [
            {
                "symbol": "BYBIT:ABCUSDT",
                "name": "ABC",
                "close": 1.0,
                "volume": 100,
                "Recommend.All": 0.5,
                "Perf.W": 1.0,
                "Perf.1M": 1.0,
                "Perf.3M": 1.0,
            },
            {
                "symbol": "OKX:ABCUSDT",
                "name": "ABC",
                "close": 1.1,
                "volume": 500,
                "Recommend.All": 0.4,
                "Perf.W": 0.5,
                "Perf.1M": 0.5,
                "Perf.3M": 0.5,
            },
        ],
    }

    cfg = SelectorConfig(
        volume={"min": 0},
        volatility={"min": None, "max": None, "fallback_use_atr_pct": False},
        dedupe_by_symbol=True,
        trend={
            "recommendation": {"min": 0.0},
            "adx": {"enabled": False},
            "momentum": {"enabled": False},
            "confirmation_momentum": {"enabled": False},
        },
        final_sort_by="volume",
    )

    selector = FuturesUniverseSelector(config=cfg, screener=DummyScreener(payload))
    result = selector.run()
    assert result["status"] == "success"
    assert result["total_selected"] == 1
    assert result["data"][0]["symbol"].startswith("OKX:ABCUSDT")


def test_process_data():
    cfg = SelectorConfig(
        volume={"min": 0},
        trend={"recommendation": {"enabled": False}, "adx": {"enabled": False}, "momentum": {"enabled": False}},
    )
    selector = FuturesUniverseSelector(config=cfg)
    raw_data = [
        {"symbol": "BINANCE:BTCUSDT", "Value.Traded": 10000000, "Volatility.D": 1.0, "Recommend.All": 0.5, "name": "BTC", "close": 50000, "volume": 100},
        {"symbol": "BINANCE:ETHUSDT", "Value.Traded": 5000000, "Volatility.D": 1.0, "Recommend.All": 0.5, "name": "ETH", "close": 3000, "volume": 100},
    ]
    result = selector.process_data(raw_data)
    assert result["status"] == "success"
    assert len(result["data"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__])
