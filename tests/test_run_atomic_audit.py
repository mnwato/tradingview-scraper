import json


def test_run_atomic_audit_writes_audit_artifacts_and_fails_on_sign_errors(monkeypatch, tmp_path):
    from tradingview_scraper.settings import get_settings

    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("TV_ARTIFACTS_DIR", str(artifacts_dir))
    get_settings.cache_clear()

    run_id = "atomic_audit_20260121-000000"
    run_dir = artifacts_dir / "summaries" / "runs" / run_id
    (run_dir / "data").mkdir(parents=True, exist_ok=True)
    (run_dir / "config").mkdir(parents=True, exist_ok=True)
    (run_dir / "audit.jsonl").write_text('{"type":"genesis"}\n', encoding="utf-8")

    import scripts.run_atomic_audit as mod
    from scripts.audit_directional_sign_test import SignTestFinding

    monkeypatch.setattr(mod, "validate_atomic_run", lambda *a, **k: 0)
    monkeypatch.setattr(
        mod,
        "run_sign_test_for_run_dir",
        lambda *a, **k: [SignTestFinding(level="ERROR", code="X", run_id=run_id, symbol="SYM", message="boom")],
    )

    rc = mod.run_atomic_audit(run_id=run_id, profile="binance_spot_rating_all_short")
    assert rc == 1

    pre = json.loads((run_dir / "data" / "directional_sign_test_pre_opt_audit.json").read_text(encoding="utf-8"))
    post = json.loads((run_dir / "data" / "directional_sign_test_audit.json").read_text(encoding="utf-8"))
    assert pre["errors"] == 1
    assert post["errors"] == 1


def test_run_atomic_audit_passes_when_sign_and_validation_pass(monkeypatch, tmp_path):
    from tradingview_scraper.settings import get_settings

    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("TV_ARTIFACTS_DIR", str(artifacts_dir))
    get_settings.cache_clear()

    run_id = "atomic_audit_20260121-000001"
    run_dir = artifacts_dir / "summaries" / "runs" / run_id
    (run_dir / "data").mkdir(parents=True, exist_ok=True)
    (run_dir / "audit.jsonl").write_text('{"type":"genesis"}\n', encoding="utf-8")

    import scripts.run_atomic_audit as mod

    monkeypatch.setattr(mod, "validate_atomic_run", lambda *a, **k: 0)
    monkeypatch.setattr(mod, "run_sign_test_for_run_dir", lambda *a, **k: [])

    rc = mod.run_atomic_audit(run_id=run_id, profile="binance_spot_rating_all_long")
    assert rc == 0

    post = json.loads((run_dir / "data" / "directional_sign_test_audit.json").read_text(encoding="utf-8"))
    assert post["errors"] == 0
