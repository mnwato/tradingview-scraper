import json
from pathlib import Path

import pytest

from tradingview_scraper.settings import TradingViewScraperSettings


def _write_manifest(
    tmp_path: Path,
    *,
    defaults_lookback: int = 100,
    dev_lookback: int = 60,
    defaults_backtest: tuple[int, int, int] = (120, 20, 20),
    dev_backtest: tuple[int, int, int] = (30, 10, 10),
    defaults_cluster_cap: float = 0.25,
    dev_cluster_cap: float | None = None,
) -> Path:
    default_train, default_test, default_step = defaults_backtest
    dev_train, dev_test, dev_step = dev_backtest
    manifest = {
        "default_profile": "production",
        "defaults": {
            "data": {"lookback_days": defaults_lookback},
            "backtest": {"train_window": default_train, "test_window": default_test, "step_size": default_step},
            "risk": {"cluster_cap": defaults_cluster_cap},
        },
        "profiles": {
            "development": {
                "data": {"lookback_days": dev_lookback},
                "backtest": {"train_window": dev_train, "test_window": dev_test, "step_size": dev_step},
                **({"risk": {"cluster_cap": dev_cluster_cap}} if dev_cluster_cap is not None else {}),
            },
            "production": {},
        },
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _base_env(monkeypatch, manifest_path: Path, profile: str = "development") -> None:
    monkeypatch.setenv("TV_MANIFEST_PATH", str(manifest_path))
    monkeypatch.setenv("TV_PROFILE", profile)


def test_cli_init_overrides_dotenv_env_manifest(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path)
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TV_LOOKBACK_DAYS=80\n", encoding="utf-8")
    monkeypatch.setenv("TV_LOOKBACK_DAYS", "90")

    settings = TradingViewScraperSettings(lookback_days=70)
    assert settings.lookback_days == 70


def test_dotenv_overrides_env(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path)
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TV_LOOKBACK_DAYS=80\n", encoding="utf-8")
    monkeypatch.setenv("TV_LOOKBACK_DAYS", "90")

    settings = TradingViewScraperSettings()
    assert settings.lookback_days == 80


def test_env_overrides_manifest_when_no_dotenv(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path)
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    monkeypatch.setenv("TV_LOOKBACK_DAYS", "90")

    settings = TradingViewScraperSettings()
    assert settings.lookback_days == 90


def test_manifest_profile_overrides_defaults(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path, defaults_lookback=100, dev_lookback=60)
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    monkeypatch.delenv("TV_LOOKBACK_DAYS", raising=False)

    settings = TradingViewScraperSettings()
    assert settings.lookback_days == 60


def test_manifest_defaults_when_profile_no_override(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path, defaults_lookback=100, dev_lookback=60)
    _base_env(monkeypatch, manifest_path, profile="production")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    monkeypatch.delenv("TV_LOOKBACK_DAYS", raising=False)

    settings = TradingViewScraperSettings()
    assert settings.lookback_days == 100


def test_portfolio_lookback_override_env(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path)
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    monkeypatch.setenv("TV_PORTFOLIO_LOOKBACK_DAYS", "120")

    settings = TradingViewScraperSettings()
    assert settings.resolve_portfolio_lookback_days() == 120


def test_portfolio_lookback_falls_back_to_lookback(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path, defaults_lookback=100, dev_lookback=60)
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    monkeypatch.delenv("TV_PORTFOLIO_LOOKBACK_DAYS", raising=False)

    settings = TradingViewScraperSettings()
    assert settings.resolve_portfolio_lookback_days() == 60


def test_backtest_cli_init_overrides_dotenv_env_manifest(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path, dev_backtest=(30, 10, 10))
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TV_TRAIN_WINDOW=80\n", encoding="utf-8")
    monkeypatch.setenv("TV_TRAIN_WINDOW", "90")

    settings = TradingViewScraperSettings(train_window=70)
    assert settings.train_window == 70


def test_backtest_dotenv_overrides_env_manifest(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path, dev_backtest=(30, 10, 10))
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TV_TRAIN_WINDOW=80\n", encoding="utf-8")
    monkeypatch.setenv("TV_TRAIN_WINDOW", "90")

    settings = TradingViewScraperSettings()
    assert settings.train_window == 80


def test_backtest_manifest_profile_overrides_defaults(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path, defaults_backtest=(120, 20, 20), dev_backtest=(30, 10, 10))
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    monkeypatch.delenv("TV_TRAIN_WINDOW", raising=False)

    settings = TradingViewScraperSettings()
    assert settings.train_window == 30
    assert settings.test_window == 10
    assert settings.step_size == 10


def test_cluster_cap_dotenv_overrides_env_manifest(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path, defaults_cluster_cap=0.25, dev_cluster_cap=0.2)
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TV_CLUSTER_CAP=0.22\n", encoding="utf-8")
    monkeypatch.setenv("TV_CLUSTER_CAP", "0.33")

    settings = TradingViewScraperSettings()
    assert settings.cluster_cap == pytest.approx(0.22)


def test_backtest_simulators_dotenv_overrides_env(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path)
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TV_BACKTEST_SIMULATORS=custom,cvxportfolio\n", encoding="utf-8")
    monkeypatch.setenv("TV_BACKTEST_SIMULATORS", "custom,vectorbt")

    settings = TradingViewScraperSettings()
    assert settings.backtest_simulators == "custom,cvxportfolio"


def test_profile_init_overrides_dotenv_env(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path)
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TV_PROFILE=development\n", encoding="utf-8")
    monkeypatch.setenv("TV_PROFILE", "production")

    settings = TradingViewScraperSettings(profile="canary")
    assert settings.profile == "canary"


def test_profile_dotenv_overrides_env(tmp_path, monkeypatch):
    manifest_path = _write_manifest(tmp_path)
    _base_env(monkeypatch, manifest_path, profile="development")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TV_PROFILE=development\n", encoding="utf-8")
    monkeypatch.setenv("TV_PROFILE", "production")

    settings = TradingViewScraperSettings()
    assert settings.profile == "development"
