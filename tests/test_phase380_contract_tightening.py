import json
from pathlib import Path

import pytest


def _write_export_file(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_consolidate_candidates_normalizes_to_canonical_schema(tmp_path, monkeypatch):
    from scripts.services import consolidate_candidates as cc

    run_id = "run_380"
    export_dir = tmp_path / "export" / run_id
    lakehouse_root = tmp_path / "lakehouse"

    # Mixed legacy formats + fields:
    # - "Symbol"/"Exchange"
    # - missing identity/metadata
    _write_export_file(
        export_dir / "legacy.json",
        [
            {"Symbol": "BTCUSDT", "Exchange": "BINANCE", "type": "spot", "extra_field": 123},
        ],
    )
    _write_export_file(
        export_dir / "enveloped.json",
        {"data": [{"symbol": "BINANCE:BTCUSDT", "asset_type": "spot", "metadata": {"source": "tv"}}]},
    )

    FakeSettings = type(
        "FakeSettings",
        (),
        {"export_dir": tmp_path / "export", "lakehouse_dir": lakehouse_root, "strict_health": False},
    )

    monkeypatch.setattr(cc, "get_settings", lambda: FakeSettings())

    out_path = tmp_path / "out" / "portfolio_candidates.json"
    cc.consolidate(run_id, str(out_path))

    consolidated = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(consolidated) == 1
    cand = consolidated[0]

    # Canonical keys expected by downstream modular pipelines.
    assert cand["symbol"] == "BINANCE:BTCUSDT"
    assert cand["exchange"] == "BINANCE"
    assert cand["asset_type"] == "spot"
    assert cand["identity"] == "BINANCE:BTCUSDT"
    assert isinstance(cand["metadata"], dict)
    # Legacy extra fields should be preserved under metadata.
    assert cand["metadata"].get("extra_field") == 123


def test_consolidate_candidates_strict_schema_raises_on_invalid_records(tmp_path, monkeypatch):
    from scripts.services import consolidate_candidates as cc

    run_id = "run_380_strict"
    export_dir = tmp_path / "export" / run_id
    _write_export_file(export_dir / "bad.json", [{"exchange": "BINANCE"}])

    class FakeSettings:
        export_dir = tmp_path / "export"
        lakehouse_dir = tmp_path / "lakehouse"
        strict_health = True

    monkeypatch.setattr(cc, "get_settings", lambda: FakeSettings())
    monkeypatch.setenv("TV_STRICT_CANDIDATE_SCHEMA", "1")

    out_path = tmp_path / "out" / "portfolio_candidates.json"
    with pytest.raises(ValueError, match="symbol"):
        cc.consolidate(run_id, str(out_path))
