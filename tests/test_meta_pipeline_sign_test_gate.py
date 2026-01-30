import json

import pytest


def test_meta_pipeline_sign_test_gate_fails_fast_and_persists_json(monkeypatch, tmp_path):
    from tradingview_scraper.settings import get_settings

    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("TV_ARTIFACTS_DIR", str(artifacts_dir))
    monkeypatch.setenv("TV_FEATURES__FEAT_DIRECTIONAL_SIGN_TEST_GATE", "1")
    get_settings.cache_clear()

    from scripts import run_meta_pipeline as meta
    from scripts.audit_directional_sign_test import SignTestFinding

    def _fake_sign_test(*args, **kwargs):
        return [SignTestFinding(level="ERROR", code="SIGNTEST_SHORT_NOT_INVERTED", run_id="x", symbol="SYM_SHORT", message="boom")]

    monkeypatch.setattr(meta, "run_sign_test_for_meta_profile", _fake_sign_test)

    run_id = "meta_crypto_only_test_fail"
    with pytest.raises(RuntimeError):
        meta.run_meta_pipeline("meta_crypto_only", profiles=["hrp"], execute_sleeves=False, run_id=run_id)

    out = artifacts_dir / "summaries" / "runs" / run_id / "data" / "directional_sign_test.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["errors"] == 1


def test_meta_pipeline_sign_test_gate_passes_and_continues(monkeypatch, tmp_path):
    from tradingview_scraper.settings import get_settings

    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("TV_ARTIFACTS_DIR", str(artifacts_dir))
    monkeypatch.setenv("TV_FEATURES__FEAT_DIRECTIONAL_SIGN_TEST_GATE", "1")
    get_settings.cache_clear()

    from scripts import run_meta_pipeline as meta

    monkeypatch.setattr(meta, "run_sign_test_for_meta_profile", lambda *a, **k: [])

    # Avoid running the real meta stages in this unit test.
    from tradingview_scraper.orchestration import sdk as sdk_mod

    monkeypatch.setattr(sdk_mod.QuantSDK, "run_stage", lambda *a, **k: None)

    run_id = "meta_crypto_only_test_pass"
    meta.run_meta_pipeline("meta_crypto_only", profiles=["hrp"], execute_sleeves=False, run_id=run_id)

    out = artifacts_dir / "summaries" / "runs" / run_id / "data" / "directional_sign_test.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["errors"] == 0
