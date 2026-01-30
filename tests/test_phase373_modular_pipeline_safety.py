import json
from pathlib import Path

import pandas as pd
import pytest


def _write_run_inputs(run_dir: Path) -> None:
    (run_dir / "data").mkdir(parents=True, exist_ok=True)
    (run_dir / "data" / "portfolio_candidates.json").write_text(json.dumps([{"symbol": "X"}]), encoding="utf-8")
    pd.DataFrame({"X": [0.01]}, index=pd.to_datetime(["2026-01-01"])).to_parquet(run_dir / "data" / "returns_matrix.parquet")


def test_ingestion_stage_prefers_run_dir_over_lakehouse(tmp_path, monkeypatch):
    from tradingview_scraper.pipelines.selection.base import SelectionContext
    from tradingview_scraper.pipelines.selection.stages.ingestion import IngestionStage

    # Create run-dir artifacts and also a conflicting lakehouse candidates file.
    run_id = "r1"
    runs_root = tmp_path / "runs"
    run_dir = runs_root / run_id
    _write_run_inputs(run_dir)

    lakehouse_dir = tmp_path / "lakehouse"
    lakehouse_dir.mkdir(parents=True, exist_ok=True)
    (lakehouse_dir / "portfolio_candidates.json").write_text(json.dumps([{"symbol": "LAKE"}]), encoding="utf-8")
    pd.DataFrame({"LAKE": [0.99]}, index=pd.to_datetime(["2026-01-01"])).to_parquet(lakehouse_dir / "returns_matrix.parquet")

    class FakeSettings:
        def __init__(self):
            self.summaries_runs_dir = runs_root
            self.lakehouse_dir = lakehouse_dir

    monkeypatch.setattr("tradingview_scraper.pipelines.selection.stages.ingestion.get_settings", lambda: FakeSettings())

    ctx = SelectionContext(run_id=run_id, params={})
    stage = IngestionStage()
    out = stage.execute(ctx)

    # Must load the run-dir candidates, not the lakehouse fallback.
    assert out.raw_pool and out.raw_pool[0]["symbol"] == "X"
    assert "X" in out.returns_df.columns


def test_ingestion_stage_strict_isolation_denies_lakehouse_fallback(tmp_path, monkeypatch):
    from tradingview_scraper.pipelines.selection.base import SelectionContext
    from tradingview_scraper.pipelines.selection.stages.ingestion import IngestionStage

    run_id = "r_missing"
    runs_root = tmp_path / "runs"
    (runs_root / run_id).mkdir(parents=True, exist_ok=True)

    lakehouse_dir = tmp_path / "lakehouse"
    lakehouse_dir.mkdir(parents=True, exist_ok=True)
    (lakehouse_dir / "portfolio_candidates.json").write_text(json.dumps([{"symbol": "LAKE"}]), encoding="utf-8")

    class FakeSettings:
        def __init__(self):
            self.summaries_runs_dir = runs_root
            self.lakehouse_dir = lakehouse_dir

    monkeypatch.setattr("tradingview_scraper.pipelines.selection.stages.ingestion.get_settings", lambda: FakeSettings())
    monkeypatch.setenv("TV_STRICT_ISOLATION", "1")

    ctx = SelectionContext(run_id=run_id, params={})
    stage = IngestionStage()

    with pytest.raises(FileNotFoundError):
        stage.execute(ctx)
