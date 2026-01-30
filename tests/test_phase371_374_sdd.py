import json
from pathlib import Path

import pandas as pd
import pytest

from tradingview_scraper.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _write_dummy_run(tmp_path: Path, *, run_id: str) -> Path:
    run_dir = tmp_path / "runs" / run_id
    (run_dir / "data").mkdir(parents=True, exist_ok=True)
    (run_dir / "reports" / "validation").mkdir(parents=True, exist_ok=True)
    return run_dir


def test_validate_meta_parity_uses_settings_runs_dir_and_no_padding(tmp_path, monkeypatch):
    import scripts.validate_meta_parity as vmp

    run_id = "meta_run_1"
    runs_root = tmp_path / "runs"
    run_dir = _write_dummy_run(tmp_path, run_id=run_id)

    # returns with a NaN row (should be dropped, not padded to 0)
    returns = pd.DataFrame(
        {
            "A": [0.01, float("nan"), 0.02],
            "B": [0.01, 0.01, 0.02],
        },
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
    )
    returns.to_parquet(run_dir / "data" / "returns_matrix.parquet")
    weights = {"weights": [{"Symbol": "A", "Weight": 0.5}, {"Symbol": "B", "Weight": 0.5}]}
    (run_dir / "data" / "portfolio_optimized_meta_hrp.json").write_text(json.dumps(weights), encoding="utf-8")

    class FakeSettings:
        summaries_runs_dir = runs_root
        lakehouse_dir = tmp_path / "lakehouse"

    monkeypatch.setattr(vmp, "get_settings", lambda: FakeSettings())

    seen = {}

    class FakeReturnsSimulator:
        def simulate(self, *, returns: pd.DataFrame, weights_df: pd.DataFrame, initial_holdings=None):
            seen["rows"] = int(len(returns))
            seen["has_nan"] = bool(returns.isna().any().any())
            # If code incorrectly pads, the NaN row would become 0 and length would remain 3.
            return {"sharpe": 0.0, "annualized_return": 0.0, "annualized_vol": 0.0, "max_drawdown": 0.0}

    monkeypatch.setattr(vmp, "ReturnsSimulator", lambda: FakeReturnsSimulator())
    monkeypatch.setattr(vmp, "run_nautilus_backtest", lambda **_kwargs: {"sharpe": 0.0, "annualized_return": 0.0, "annualized_vol": 0.0, "max_drawdown": 0.0})

    # Should not error and should drop the NaN row (rows -> 2).
    vmp.validate_meta_parity(run_id, profile="hrp")
    assert seen["has_nan"] is False
    assert seen["rows"] == 2


def test_prepare_portfolio_data_defaults_to_lakehouse_only(tmp_path, monkeypatch):
    import scripts.prepare_portfolio_data as ppd

    candidates_file = tmp_path / "cands.json"
    candidates_file.write_text(json.dumps([{"symbol": "BINANCE:BTCUSDT"}]), encoding="utf-8")

    # Ensure env does NOT set PORTFOLIO_DATA_SOURCE (we're testing the default).
    monkeypatch.delenv("PORTFOLIO_DATA_SOURCE", raising=False)
    monkeypatch.setenv("CANDIDATES_FILE", str(candidates_file))
    monkeypatch.setenv("PORTFOLIO_RETURNS_PATH", str(tmp_path / "returns.parquet"))
    monkeypatch.setenv("PORTFOLIO_META_PATH", str(tmp_path / "meta.json"))

    class FakeSettings:
        def prepare_summaries_run_dir(self):
            return tmp_path / "run_dir"

        features = type("F", (), {"feat_audit_ledger": False})()
        min_days_floor = 0
        portfolio_batch_size = 1
        portfolio_dedupe_base = False

        def resolve_portfolio_lookback_days(self):
            return 10

    monkeypatch.setattr(ppd, "get_settings", lambda: FakeSettings())

    class FakeLoader:
        def load(self, *_args, **_kwargs):
            ts = [pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-01-02", tz="UTC"), pd.Timestamp("2026-01-03", tz="UTC")]
            return pd.DataFrame({"timestamp": [int(t.timestamp()) for t in ts], "close": [100.0, 101.0, 102.0]})

    monkeypatch.setattr(ppd, "PersistentDataLoader", lambda *args, **kwargs: FakeLoader())

    # This should complete without attempting network ingestion.
    ppd.prepare_portfolio_universe()


def test_prepare_portfolio_data_fails_fast_on_network_mode(tmp_path, monkeypatch):
    import scripts.prepare_portfolio_data as ppd

    candidates_file = tmp_path / "cands.json"
    candidates_file.write_text(json.dumps([{"symbol": "BINANCE:BTCUSDT"}]), encoding="utf-8")

    monkeypatch.setenv("PORTFOLIO_DATA_SOURCE", "fetch")
    monkeypatch.setenv("CANDIDATES_FILE", str(candidates_file))
    monkeypatch.setenv("PORTFOLIO_RETURNS_PATH", str(tmp_path / "returns.parquet"))
    monkeypatch.setenv("PORTFOLIO_META_PATH", str(tmp_path / "meta.json"))

    class FakeSettings:
        def prepare_summaries_run_dir(self):
            return tmp_path / "run_dir"

        features = type("F", (), {"feat_audit_ledger": False})()
        min_days_floor = 0
        portfolio_batch_size = 1
        portfolio_dedupe_base = False

        def resolve_portfolio_lookback_days(self):
            return 10

    monkeypatch.setattr(ppd, "get_settings", lambda: FakeSettings())

    with pytest.raises(RuntimeError, match="flow-data"):
        ppd.prepare_portfolio_universe()


def test_meta_scripts_do_not_hardcode_lakehouse_paths():
    repo_root = Path(__file__).resolve().parents[1]
    for rel_path in [
        Path("scripts/optimize_meta_portfolio.py"),
        Path("scripts/flatten_meta_weights.py"),
    ]:
        content = (repo_root / rel_path).read_text(encoding="utf-8")
        assert "data/lakehouse" not in content
