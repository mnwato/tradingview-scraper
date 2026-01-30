import json
from pathlib import Path

from tradingview_scraper.settings import TradingViewScraperSettings, get_settings


def _write_min_manifest(tmp_path: Path, *, profile: str = "p", defaults: dict | None = None, profiles: dict | None = None) -> Path:
    manifest = {"default_profile": profile, "defaults": defaults or {}, "profiles": profiles or {profile: {}}}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _base_env(monkeypatch, *, tmp_path: Path, manifest_path: Path, profile: str = "p") -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TV_MANIFEST_PATH", str(manifest_path))
    monkeypatch.setenv("TV_PROFILE", profile)
    monkeypatch.delenv("TV_FEATURES__SELECTION_MODE", raising=False)
    get_settings.cache_clear()


def test_selection_mode_default_is_stable(tmp_path, monkeypatch):
    manifest_path = _write_min_manifest(tmp_path, defaults={}, profiles={"p": {}})
    _base_env(monkeypatch, tmp_path=tmp_path, manifest_path=manifest_path, profile="p")

    settings = TradingViewScraperSettings()
    assert settings.features.selection_mode == "v4"


def test_selection_mode_manifest_then_env_override(tmp_path, monkeypatch):
    manifest_path = _write_min_manifest(tmp_path, defaults={"features": {"selection_mode": "v3.2"}}, profiles={"p": {}})
    _base_env(monkeypatch, tmp_path=tmp_path, manifest_path=manifest_path, profile="p")

    settings = TradingViewScraperSettings()
    assert settings.features.selection_mode == "v3.2"

    monkeypatch.setenv("TV_FEATURES__SELECTION_MODE", "v2.1")
    settings2 = TradingViewScraperSettings()
    assert settings2.features.selection_mode == "v2.1"


def test_production_validate_discovery_uses_settings_export_dir(tmp_path, monkeypatch):
    from scripts.run_production_pipeline import ProductionPipeline

    run_id = "run_123"
    export_dir = tmp_path / "export_root"
    (export_dir / run_id).mkdir(parents=True, exist_ok=True)
    (export_dir / run_id / "a.json").write_text("{}", encoding="utf-8")
    (export_dir / run_id / "b.json").write_text("{}", encoding="utf-8")

    manifest_path = _write_min_manifest(tmp_path, defaults={}, profiles={"p": {}})
    monkeypatch.setenv("TV_EXPORT_DIR", str(export_dir))
    _base_env(monkeypatch, tmp_path=tmp_path, manifest_path=manifest_path, profile="p")

    pipeline = ProductionPipeline(profile="p", manifest=str(manifest_path), run_id=run_id)
    res = pipeline.validate_discovery()
    assert res["metrics"]["n_discovery_files"] == 2


def test_ingestion_service_plumbs_lakehouse_path(tmp_path, monkeypatch):
    import scripts.services.ingest_data as ingest_data

    manifest_path = _write_min_manifest(tmp_path, defaults={}, profiles={"p": {}})
    _base_env(monkeypatch, tmp_path=tmp_path, manifest_path=manifest_path, profile="p")

    seen: dict = {}

    class FakePersistentDataLoader:
        def __init__(self, lakehouse_path: str = "data/lakehouse", **_kwargs):
            seen["lakehouse_path"] = lakehouse_path

    monkeypatch.setattr(ingest_data, "PersistentDataLoader", FakePersistentDataLoader)

    lakehouse_dir = tmp_path / "custom_lakehouse"
    service = ingest_data.IngestionService(lakehouse_dir=lakehouse_dir)
    assert seen["lakehouse_path"] == str(lakehouse_dir)
    assert service.lakehouse_dir == lakehouse_dir


def test_meta_pipeline_uses_settings_manifest_path_for_execute_sleeves(tmp_path, monkeypatch):
    import scripts.run_meta_pipeline as rmp

    manifest = {
        "default_profile": "meta_test",
        "defaults": {},
        "profiles": {
            "meta_test": {
                "sleeves": [
                    {"id": "s1", "profile": "p1", "run_id": ""},
                ],
                "meta_allocation": {"engine": "custom", "profile": "hrp", "min_weight": 0.05, "max_weight": 0.95},
            }
        },
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    _base_env(monkeypatch, tmp_path=tmp_path, manifest_path=manifest_path, profile="meta_test")

    called: dict = {}

    def fake_load_manifest(path: Path) -> dict:
        called["path"] = path
        return json.loads(path.read_text(encoding="utf-8"))

    monkeypatch.setattr(rmp, "_load_manifest", fake_load_manifest)

    class FakeRayComputeEngine:
        def execute_sleeves(self, sleeves_to_run):
            return [{"profile": s["profile"], "status": "success", "duration": 0.01} for s in sleeves_to_run]

    monkeypatch.setattr(rmp, "RayComputeEngine", FakeRayComputeEngine)

    class FakeSDK:
        @staticmethod
        def run_stage(_id: str, **_params):
            return None

    import tradingview_scraper.orchestration.sdk as sdk_mod

    monkeypatch.setattr(sdk_mod, "QuantSDK", FakeSDK)

    rmp.run_meta_pipeline("meta_test", execute_sleeves=True, run_id="meta_test_run", manifest=str(manifest_path))
    assert called["path"] == manifest_path


def test_tradingview_discovery_normalizes_identity(monkeypatch):
    from tradingview_scraper.pipelines.discovery import tradingview as tv_mod
    from tradingview_scraper.pipelines.discovery.tradingview import TradingViewDiscoveryScanner

    monkeypatch.setattr(tv_mod, "load_config", lambda _src: {})

    class FakeSelector:
        def __init__(self, _cfg):
            pass

        def run(self):
            return {"status": "success", "data": [{"symbol": "BINANCE:BTCUSDT", "type": "spot"}]}

    monkeypatch.setattr(tv_mod, "FuturesUniverseSelector", FakeSelector)

    scanner = TradingViewDiscoveryScanner()
    cands = scanner.discover({"config_path": "dummy.yaml"})
    assert len(cands) == 1
    assert cands[0].symbol == "BINANCE:BTCUSDT"
    assert cands[0].identity == "BINANCE:BTCUSDT"
