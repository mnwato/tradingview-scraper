import json
from pathlib import Path

import pandas as pd


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_minimal_atomic_artifacts(run_dir: Path) -> None:
    (run_dir / "config").mkdir(parents=True, exist_ok=True)
    (run_dir / "data").mkdir(parents=True, exist_ok=True)

    # Minimal snapshot / audit
    _write_json(run_dir / "config" / "resolved_manifest.json", {"features": {"feat_directional_sign_test_gate_atomic": True}})
    (run_dir / "audit.jsonl").write_text('{"type":"genesis","profile":"x"}\n', encoding="utf-8")

    # Minimal data
    idx = pd.date_range("2026-01-01", periods=5, freq="D")
    pd.DataFrame({"BINANCE:AAA": [0.01, -0.02, 0.0, 0.03, -0.01]}, index=idx).to_parquet(run_dir / "data" / "returns_matrix.parquet")
    pd.DataFrame({"BINANCE:AAA_strategy_LONG": [0.01, -0.02, 0.0, 0.03, -0.01]}, index=idx).to_parquet(run_dir / "data" / "synthetic_returns.parquet")

    _write_json(run_dir / "data" / "portfolio_optimized_v2.json", {"profiles": {"hrp": {"assets": [{"Symbol": "BINANCE:AAA", "Weight": 1.0}]}}})
    _write_json(run_dir / "data" / "portfolio_flattened.json", {"weights": [{"Symbol": "BINANCE:AAA", "Weight": 1.0, "Net_Weight": 1.0, "Direction": "LONG"}]})


def test_validate_atomic_run_enforces_sign_artifacts_when_gate_enabled(monkeypatch, tmp_path):
    from scripts.validate_atomic_run import validate_atomic_run
    from tradingview_scraper.settings import get_settings

    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("TV_ARTIFACTS_DIR", str(artifacts_dir))
    get_settings.cache_clear()

    run_id = "atomic_20260121-000000"
    run_dir = artifacts_dir / "summaries" / "runs" / run_id
    _build_minimal_atomic_artifacts(run_dir)

    # Gate enabled via resolved_manifest.json, but sign-test artifacts missing -> FAIL
    rc = validate_atomic_run(run_id=run_id, profile="binance_spot_rating_all_short")
    assert rc == 1

    # Pre-opt present but failing -> FAIL
    _write_json(run_dir / "data" / "directional_sign_test_pre_opt.json", {"errors": 1, "warnings": 0, "findings": []})
    _write_json(run_dir / "data" / "directional_sign_test.json", {"errors": 0, "warnings": 0, "findings": []})
    rc = validate_atomic_run(run_id=run_id, profile="binance_spot_rating_all_short")
    assert rc == 1

    # Both present and passing -> PASS
    _write_json(run_dir / "data" / "directional_sign_test_pre_opt.json", {"errors": 0, "warnings": 0, "findings": []})
    _write_json(run_dir / "data" / "directional_sign_test.json", {"errors": 0, "warnings": 0, "findings": []})
    rc = validate_atomic_run(run_id=run_id, profile="binance_spot_rating_all_short")
    assert rc == 0
