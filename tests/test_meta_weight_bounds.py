import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


def test_project_bounded_simplex_basic():
    from scripts.optimize_meta_portfolio import _project_bounded_simplex

    w = np.array([0.9, 0.1], dtype=float)
    res = _project_bounded_simplex(w, min_weight=0.05, max_weight=0.5)

    assert res.sum() == pytest.approx(1.0)
    assert (res >= 0.05 - 1e-12).all()
    assert (res <= 0.5 + 1e-12).all()
    assert res[0] == pytest.approx(0.5)
    assert res[1] == pytest.approx(0.5)


def test_project_bounded_simplex_three_assets_caps_and_floor():
    from scripts.optimize_meta_portfolio import _project_bounded_simplex

    w = np.array([0.98, 0.01, 0.01], dtype=float)
    res = _project_bounded_simplex(w, min_weight=0.05, max_weight=0.5)

    assert res.sum() == pytest.approx(1.0)
    assert (res >= 0.05 - 1e-12).all()
    assert (res <= 0.5 + 1e-12).all()

    assert res[0] == pytest.approx(0.5)
    assert res[1] == pytest.approx(0.25)
    assert res[2] == pytest.approx(0.25)


def test_project_bounded_simplex_invalid_bounds_raises():
    from scripts.optimize_meta_portfolio import _project_bounded_simplex

    with pytest.raises(ValueError):
        _project_bounded_simplex(np.array([0.3, 0.3, 0.4]), min_weight=0.4, max_weight=0.6)


def test_optimize_meta_applies_manifest_meta_allocation_bounds(tmp_path, monkeypatch):
    """
    Spec-driven test:
    - meta profile has meta_allocation min/max bounds
    - meta optimize must respect those bounds in the saved artifact
    """
    from scripts import optimize_meta_portfolio as omp

    meta_profile = "meta_test_profile"
    risk_profile = "hrp"

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "profiles": {
                    meta_profile: {
                        "sleeves": [
                            {"id": "a", "profile": "p1", "run_id": "r1"},
                            {"id": "b", "profile": "p2", "run_id": "r2"},
                            {"id": "c", "profile": "p3", "run_id": "r3"},
                        ],
                        "meta_allocation": {"engine": "custom", "profile": "hrp", "min_weight": 0.05, "max_weight": 0.5},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    # Minimal settings stub
    run_dir = tmp_path / "runs" / "meta_run"
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    settings_stub = SimpleNamespace(
        manifest_path=manifest_path,
        run_id="meta_run",
        features=SimpleNamespace(feat_audit_ledger=False),
        prepare_summaries_run_dir=lambda: run_dir,
    )
    monkeypatch.setattr(omp, "get_settings", lambda: settings_stub)

    # Fake engine that returns extreme weights (violating max_weight)
    class FakeEngine:
        def optimize(self, *, returns, clusters, meta, stats, request):
            df = pd.DataFrame(
                [
                    {"Symbol": "a", "Weight": 0.9, "Net_Weight": 0.9, "Direction": "LONG"},
                    {"Symbol": "b", "Weight": 0.05, "Net_Weight": 0.05, "Direction": "LONG"},
                    {"Symbol": "c", "Weight": 0.05, "Net_Weight": 0.05, "Direction": "LONG"},
                ]
            )
            return SimpleNamespace(weights=df)

    monkeypatch.setattr(omp, "build_engine", lambda name: FakeEngine())

    # Create the expected meta returns file
    rets = pd.DataFrame(
        {
            "a": [0.01, -0.01, 0.02],
            "b": [0.0, 0.005, -0.002],
            "c": [0.003, 0.001, 0.0],
        },
        index=pd.date_range("2025-01-01", periods=3, freq="D"),
    )
    rets_path = data_dir / f"meta_returns_{meta_profile}_{risk_profile}.pkl"
    rets.to_pickle(rets_path)

    out_path = data_dir / "meta_optimized.json"
    omp.optimize_meta(str(rets_path), str(out_path), profile=risk_profile, meta_profile=meta_profile)

    saved = json.loads((data_dir / f"meta_optimized_{meta_profile}_{risk_profile}.json").read_text(encoding="utf-8"))
    weights = saved["weights"]
    w_vals = [float(w["Weight"]) for w in weights]

    assert sum(w_vals) == pytest.approx(1.0)
    assert max(w_vals) <= 0.5 + 1e-12
    assert min(w_vals) >= 0.05 - 1e-12
