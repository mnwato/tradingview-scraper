import json
from pathlib import Path

import pandas as pd


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_sign_test_passes_when_shorts_are_inverted(tmp_path):
    from scripts.audit_directional_sign_test import run_sign_test_for_run_dir

    run_dir = tmp_path / "run_x"
    (run_dir / "data").mkdir(parents=True, exist_ok=True)

    idx = pd.date_range("2026-01-01", periods=5, freq="D")
    raw = pd.DataFrame({"BINANCE:AAA": [0.01, -0.02, 0.0, 0.03, -0.01]}, index=idx)
    syn = pd.DataFrame(
        {
            "BINANCE:AAA_strategy_LONG": raw["BINANCE:AAA"],
            "BINANCE:AAA_strategy_SHORT": -raw["BINANCE:AAA"],
        },
        index=idx,
    )

    raw.to_parquet(run_dir / "data" / "returns_matrix.parquet")
    syn.to_parquet(run_dir / "data" / "synthetic_returns.parquet")
    _write_json(
        run_dir / "data" / "portfolio_optimized_v2.json",
        {
            "profiles": {
                "hrp": {
                    "assets": [
                        {"Symbol": "BINANCE:AAA_strategy_SHORT", "Weight": 1.0, "Net_Weight": 1.0, "Direction": "LONG"},
                    ]
                }
            }
        },
    )

    findings = run_sign_test_for_run_dir(run_dir, atol=0.0, risk_profile="hrp")
    assert [f for f in findings if f.level == "ERROR"] == []


def test_sign_test_fails_when_shorts_are_not_inverted(tmp_path):
    from scripts.audit_directional_sign_test import run_sign_test_for_run_dir

    run_dir = tmp_path / "run_x"
    (run_dir / "data").mkdir(parents=True, exist_ok=True)

    idx = pd.date_range("2026-01-01", periods=5, freq="D")
    raw = pd.DataFrame({"BINANCE:AAA": [0.01, -0.02, 0.0, 0.03, -0.01]}, index=idx)
    # BUG: SHORT is not inverted (equals raw)
    syn = pd.DataFrame(
        {
            "BINANCE:AAA_strategy_SHORT": raw["BINANCE:AAA"],
        },
        index=idx,
    )

    raw.to_parquet(run_dir / "data" / "returns_matrix.parquet")
    syn.to_parquet(run_dir / "data" / "synthetic_returns.parquet")

    findings = run_sign_test_for_run_dir(run_dir, atol=0.0, risk_profile="hrp", require_optimizer_normalization=False)
    assert any(f.code == "SIGNTEST_SHORT_NOT_INVERTED" for f in findings)


def test_sign_test_flags_optimizer_not_normalized(tmp_path):
    from scripts.audit_directional_sign_test import run_sign_test_for_run_dir

    run_dir = tmp_path / "run_x"
    (run_dir / "data").mkdir(parents=True, exist_ok=True)

    idx = pd.date_range("2026-01-01", periods=5, freq="D")
    raw = pd.DataFrame({"BINANCE:AAA": [0.01, -0.02, 0.0, 0.03, -0.01]}, index=idx)
    syn = pd.DataFrame(
        {
            "BINANCE:AAA_strategy_SHORT": -raw["BINANCE:AAA"],
        },
        index=idx,
    )

    raw.to_parquet(run_dir / "data" / "returns_matrix.parquet")
    syn.to_parquet(run_dir / "data" / "synthetic_returns.parquet")
    _write_json(
        run_dir / "data" / "portfolio_optimized_v2.json",
        {
            "profiles": {
                "hrp": {
                    "assets": [
                        # Direction/Net_Weight indicate non-normalized shorts (should be LONG + positive)
                        {"Symbol": "BINANCE:AAA_strategy_SHORT", "Weight": 1.0, "Net_Weight": -1.0, "Direction": "SHORT"},
                    ]
                }
            }
        },
    )

    findings = run_sign_test_for_run_dir(run_dir, atol=0.0, risk_profile="hrp", require_optimizer_normalization=True)
    assert any(f.code == "SIGNTEST_OPTIMIZER_NOT_NORMALIZED" for f in findings)


def test_sign_test_allows_short_loss_cap(tmp_path):
    from scripts.audit_directional_sign_test import run_sign_test_for_run_dir

    run_dir = tmp_path / "run_x"
    (run_dir / "data").mkdir(parents=True, exist_ok=True)

    idx = pd.date_range("2026-01-01", periods=3, freq="D")
    # A +131% day should cap synthetic short at -100% (a short can't lose more than 100%).
    raw = pd.DataFrame({"BINANCE:AAA": [0.05, 1.312883, -0.10]}, index=idx)
    syn = pd.DataFrame(
        {
            "BINANCE:AAA_strategy_SHORT": [-0.05, -1.0, 0.10],
        },
        index=idx,
    )

    raw.to_parquet(run_dir / "data" / "returns_matrix.parquet")
    syn.to_parquet(run_dir / "data" / "synthetic_returns.parquet")

    findings = run_sign_test_for_run_dir(run_dir, atol=0.0, risk_profile="hrp", require_optimizer_normalization=False)
    assert [f for f in findings if f.level == "ERROR"] == []


def test_sign_test_writer_emits_json(tmp_path):
    from scripts.audit_directional_sign_test import SignTestFinding, write_findings_json

    out = tmp_path / "directional_sign_test.json"
    findings = [
        SignTestFinding(level="WARN", code="X", run_id="run_x", symbol="SYM", message="hello"),
        SignTestFinding(level="ERROR", code="Y", run_id="run_x", symbol="SYM2", message="boom"),
    ]
    write_findings_json(findings, out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["errors"] == 1
    assert payload["warnings"] == 1
    assert isinstance(payload["findings"], list)
