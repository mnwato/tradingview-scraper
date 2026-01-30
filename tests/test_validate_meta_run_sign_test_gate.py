import json
from pathlib import Path

import pandas as pd


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_minimal_meta_artifacts(base_dir: Path, *, meta_profile: str, risk_profile: str) -> None:
    idx = pd.date_range("2026-01-01", periods=5, freq="D")
    meta_rets = pd.DataFrame({"long_all": [0.01, 0.0, -0.01, 0.02, 0.0], "short_all": [0.0, 0.01, 0.0, -0.01, 0.02]}, index=idx)
    meta_rets.to_pickle(base_dir / f"meta_returns_{meta_profile}_{risk_profile}.pkl")

    _write_json(
        base_dir / f"meta_optimized_{meta_profile}_{risk_profile}.json",
        {
            "metadata": {"meta_profile": meta_profile, "risk_profile": risk_profile},
            "weights": [{"Symbol": "long_all", "Weight": 0.5}, {"Symbol": "short_all", "Weight": 0.5}],
        },
    )
    _write_json(
        base_dir / f"meta_cluster_tree_{meta_profile}_{risk_profile}.json",
        {"weights": [{"Symbol": "long_all", "Weight": 0.5}, {"Symbol": "short_all", "Weight": 0.5}]},
    )
    _write_json(
        base_dir / f"portfolio_optimized_meta_{meta_profile}_{risk_profile}.json",
        {
            "metadata": {"meta_profile": meta_profile, "risk_profile": risk_profile},
            "weights": [{"Symbol": "BINANCE:BTCUSDT", "Weight": 0.10, "Net_Weight": 0.10, "Direction": "LONG"}],
        },
    )


def test_validate_meta_run_requires_sign_test_when_enabled(monkeypatch, tmp_path):
    from scripts.validate_meta_run import validate_meta_run
    from tradingview_scraper.settings import get_settings

    artifacts_dir = tmp_path / "artifacts"
    monkeypatch.setenv("TV_ARTIFACTS_DIR", str(artifacts_dir))
    get_settings.cache_clear()

    meta_profile = "meta_crypto_only"
    risk_profile = "hrp"

    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "default_profile": "production",
            "defaults": {},
            "profiles": {meta_profile: {"features": {"feat_directional_sign_test_gate": True}}},
        },
    )

    run_id = "meta_crypto_only_20260121-000000"
    run_dir = artifacts_dir / "summaries" / "runs" / run_id
    base_dir = run_dir / "data"
    base_dir.mkdir(parents=True, exist_ok=True)
    _build_minimal_meta_artifacts(base_dir, meta_profile=meta_profile, risk_profile=risk_profile)

    rc = validate_meta_run(run_id=run_id, meta_profile=meta_profile, risk_profiles=[risk_profile], manifest_path=manifest_path)
    assert rc == 1

    out_json = run_dir / "reports" / "validation" / f"meta_validation_{meta_profile}_{run_id}.json"
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    codes = [c["code"] for c in payload["checks"]]
    assert "META_SIGN_TEST_MISSING" in codes

    _write_json(base_dir / "directional_sign_test.json", {"errors": 1, "warnings": 0, "findings": []})
    rc = validate_meta_run(run_id=run_id, meta_profile=meta_profile, risk_profiles=[risk_profile], manifest_path=manifest_path)
    assert rc == 1

    _write_json(base_dir / "directional_sign_test.json", {"errors": 0, "warnings": 0, "findings": []})
    rc = validate_meta_run(run_id=run_id, meta_profile=meta_profile, risk_profiles=[risk_profile], manifest_path=manifest_path)
    assert rc == 0
