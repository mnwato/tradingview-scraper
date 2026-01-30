import json

import pytest


def test_production_pipeline_sign_test_gate_fails_fast_and_writes_preopt(monkeypatch, tmp_path):
    from tradingview_scraper.settings import get_settings

    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("TV_ARTIFACTS_DIR", str(artifacts_dir))
    monkeypatch.setenv("TV_FEATURES__FEAT_DIRECTIONAL_SIGN_TEST_GATE_ATOMIC", "1")
    get_settings.cache_clear()

    from scripts.audit_directional_sign_test import SignTestFinding
    from scripts.run_production_pipeline import ProductionPipeline

    pipeline = ProductionPipeline(profile="binance_spot_rating_all_short", run_id="atomic_gate_fail", skip_analysis=True, skip_validation=True)

    monkeypatch.setattr(pipeline, "snapshot_resolved_manifest", lambda: None)
    monkeypatch.setattr(pipeline, "run_step", lambda *a, **k: True)

    import scripts.audit_directional_sign_test as signmod

    monkeypatch.setattr(
        signmod,
        "run_sign_test_for_run_dir",
        lambda *a, **k: [SignTestFinding(level="ERROR", code="SIGNTEST_SHORT_NOT_INVERTED", run_id="x", symbol="SYM_SHORT", message="boom")],
    )

    with pytest.raises(RuntimeError):
        pipeline.execute(start_step=1)

    out = artifacts_dir / "summaries" / "runs" / "atomic_gate_fail" / "data" / "directional_sign_test_pre_opt.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["errors"] == 1


def test_production_pipeline_sign_test_gate_writes_postopt_when_preopt_passes(monkeypatch, tmp_path):
    from tradingview_scraper.settings import get_settings

    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("TV_ARTIFACTS_DIR", str(artifacts_dir))
    monkeypatch.setenv("TV_FEATURES__FEAT_DIRECTIONAL_SIGN_TEST_GATE_ATOMIC", "1")
    get_settings.cache_clear()

    from scripts.audit_directional_sign_test import SignTestFinding
    from scripts.run_production_pipeline import ProductionPipeline

    pipeline = ProductionPipeline(profile="binance_spot_rating_all_long", run_id="atomic_gate_postopt_fail", skip_analysis=True, skip_validation=True)

    monkeypatch.setattr(pipeline, "snapshot_resolved_manifest", lambda: None)
    monkeypatch.setattr(pipeline, "run_step", lambda *a, **k: True)

    import scripts.audit_directional_sign_test as signmod

    def _fake_sign_test(*args, **kwargs):
        if kwargs.get("require_optimizer_normalization"):
            return [SignTestFinding(level="ERROR", code="SIGNTEST_OPTIMIZER_NOT_NORMALIZED", run_id="x", symbol="SYM_SHORT", message="bad")]
        return []

    monkeypatch.setattr(signmod, "run_sign_test_for_run_dir", _fake_sign_test)

    with pytest.raises(RuntimeError):
        pipeline.execute(start_step=1)

    pre = artifacts_dir / "summaries" / "runs" / "atomic_gate_postopt_fail" / "data" / "directional_sign_test_pre_opt.json"
    post = artifacts_dir / "summaries" / "runs" / "atomic_gate_postopt_fail" / "data" / "directional_sign_test.json"
    assert json.loads(pre.read_text(encoding="utf-8"))["errors"] == 0
    assert json.loads(post.read_text(encoding="utf-8"))["errors"] == 1


def test_production_pipeline_runs_atomic_validation_after_reporting(monkeypatch, tmp_path):
    from tradingview_scraper.settings import get_settings

    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("TV_ARTIFACTS_DIR", str(artifacts_dir))
    monkeypatch.setenv("TV_FEATURES__FEAT_DIRECTIONAL_SIGN_TEST_GATE_ATOMIC", "1")
    get_settings.cache_clear()

    from scripts.run_production_pipeline import ProductionPipeline

    pipeline = ProductionPipeline(profile="binance_spot_rating_all_long", run_id="atomic_gate_validate", skip_analysis=True, skip_validation=True)

    monkeypatch.setattr(pipeline, "snapshot_resolved_manifest", lambda: None)

    # Make run_step always succeed so we exercise the gate hooks.
    monkeypatch.setattr(pipeline, "run_step", lambda *a, **k: True)

    # Sign test passes for both pre/post so we reach Reporting.
    import scripts.audit_directional_sign_test as signmod

    monkeypatch.setattr(signmod, "run_sign_test_for_run_dir", lambda *a, **k: [])

    # Validate_atomic_run is invoked after Reporting.
    import scripts.validate_atomic_run as vmod

    called = {"n": 0}

    def _fake_validate_atomic_run(*args, **kwargs):
        called["n"] += 1
        return 0

    monkeypatch.setattr(vmod, "validate_atomic_run", _fake_validate_atomic_run)

    pipeline.execute(start_step=1)
    assert called["n"] == 1
