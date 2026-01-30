import json
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_meta_flatten_collapses_to_physical_assets(tmp_path):
    """
    Spec-driven test: Physical Asset Collapse (Fractal Meta v1)

    - meta.flatten output MUST consist of physical assets only (no logic-atom suffixes)
    - weights for the same physical asset across sleeves MUST be summed
    - when `portfolio_flattened.json` exists in the sleeve run, it should be preferred
      over `portfolio_optimized_v2.json` to avoid atom leakage.
    """
    from scripts.flatten_meta_weights import flatten_weights

    meta_profile = "meta_test"
    risk_profile = "hrp"

    run_dir = tmp_path / "meta_run"
    meta_dir = run_dir / "data"
    meta_dir.mkdir(parents=True, exist_ok=True)

    sleeve1_dir = tmp_path / "sleeve1"
    sleeve2_dir = tmp_path / "sleeve2"

    # Meta optimize says: 60% sleeve1, 40% sleeve2
    _write_json(
        meta_dir / f"meta_optimized_{meta_profile}_{risk_profile}.json",
        {"metadata": {"meta_profile": meta_profile, "profile": risk_profile}, "weights": [{"Symbol": "s1", "Weight": 0.6}, {"Symbol": "s2", "Weight": 0.4}]},
    )

    _write_json(
        meta_dir / f"meta_manifest_{meta_profile}_{risk_profile}.json",
        {
            "meta_profile": meta_profile,
            "risk_profile": risk_profile,
            "sleeves": [
                {"id": "s1", "profile": "p1", "run_id": "r1", "run_path": str(sleeve1_dir)},
                {"id": "s2", "profile": "p2", "run_id": "r2", "run_path": str(sleeve2_dir)},
            ],
        },
    )

    # Sleeve 1:
    # - portfolio_optimized_v2 has atom symbols (intentionally different weights)
    # - portfolio_flattened has physical symbols and should be used
    _write_json(
        sleeve1_dir / "data" / "portfolio_optimized_v2.json",
        {
            "profiles": {
                risk_profile: {
                    "assets": [
                        {"Symbol": "BINANCE:BTCUSDT_rating_all_long_LONG", "Weight": 0.9, "Net_Weight": 0.9},
                        {"Symbol": "BINANCE:ETHUSDT_rating_all_long_LONG", "Weight": 0.1, "Net_Weight": 0.1},
                    ]
                }
            }
        },
    )
    _write_json(
        sleeve1_dir / "data" / "portfolio_flattened.json",
        {
            "profiles": {
                risk_profile: {
                    "assets": [
                        {"Symbol": "BINANCE:BTCUSDT", "Weight": 0.5, "Net_Weight": 0.5, "Direction": "LONG"},
                        {"Symbol": "BINANCE:ETHUSDT", "Weight": 0.5, "Net_Weight": 0.5, "Direction": "LONG"},
                    ]
                }
            }
        },
    )

    # Sleeve 2 includes BTC again + SOL, and uses physical symbols already.
    _write_json(
        sleeve2_dir / "data" / "portfolio_flattened.json",
        {
            "profiles": {
                risk_profile: {
                    "assets": [
                        {"Symbol": "BINANCE:BTCUSDT", "Weight": 0.25, "Net_Weight": 0.25, "Direction": "LONG"},
                        {"Symbol": "BINANCE:SOLUSDT", "Weight": 0.75, "Net_Weight": 0.75, "Direction": "LONG"},
                    ]
                }
            }
        },
    )
    _write_json(
        sleeve2_dir / "data" / "portfolio_optimized_v2.json",
        {
            "profiles": {
                risk_profile: {
                    "assets": [
                        {"Symbol": "BINANCE:BTCUSDT_rating_ma_long_LONG", "Weight": 0.01, "Net_Weight": 0.01},
                        {"Symbol": "BINANCE:SOLUSDT_rating_ma_long_LONG", "Weight": 0.99, "Net_Weight": 0.99},
                    ]
                }
            }
        },
    )

    out_stub = meta_dir / "portfolio_optimized_meta.json"
    flatten_weights(meta_profile, str(out_stub), risk_profile)

    out_path = meta_dir / f"portfolio_optimized_meta_{meta_profile}_{risk_profile}.json"
    assert out_path.exists()
    out = json.loads(out_path.read_text(encoding="utf-8"))

    symbols = [w["Symbol"] for w in out["weights"]]
    assert "BINANCE:BTCUSDT" in symbols
    assert "BINANCE:ETHUSDT" in symbols
    assert "BINANCE:SOLUSDT" in symbols

    # Physical-asset-only: no atom suffix leakage
    assert all("_" not in s for s in symbols)

    # BTC should be summed across sleeves: 0.6*0.5 + 0.4*0.25 = 0.3 + 0.1 = 0.4
    btc = [w for w in out["weights"] if w["Symbol"] == "BINANCE:BTCUSDT"][0]
    assert float(btc["Net_Weight"]) == pytest.approx(0.4)

    # Ensure we used portfolio_flattened (not portfolio_optimized_v2) for sleeve1:
    # If it had used portfolio_optimized_v2 atom weights, BTC contribution would have been 0.6*0.9=0.54.
    assert float(btc["Net_Weight"]) != pytest.approx(0.54)


def test_meta_flatten_fallback_collapses_atom_symbols(tmp_path):
    """
    Spec-driven hardening:
    Even if a sleeve lacks `portfolio_flattened.json`, meta.flatten MUST still
    output physical assets (no atom suffixes) when falling back to
    `portfolio_optimized_v2.json`.
    """
    from scripts.flatten_meta_weights import flatten_weights

    meta_profile = "meta_test_atoms"
    risk_profile = "hrp"

    run_dir = tmp_path / "meta_run"
    meta_dir = run_dir / "data"
    meta_dir.mkdir(parents=True, exist_ok=True)

    sleeve_dir = tmp_path / "sleeve_atoms"

    _write_json(
        meta_dir / f"meta_optimized_{meta_profile}_{risk_profile}.json",
        {"metadata": {"meta_profile": meta_profile, "profile": risk_profile}, "weights": [{"Symbol": "s1", "Weight": 1.0}]},
    )
    _write_json(
        meta_dir / f"meta_manifest_{meta_profile}_{risk_profile}.json",
        {"meta_profile": meta_profile, "risk_profile": risk_profile, "sleeves": [{"id": "s1", "profile": "p1", "run_id": "r1", "run_path": str(sleeve_dir)}]},
    )

    # Only portfolio_optimized_v2 exists (atom symbols).
    _write_json(
        sleeve_dir / "data" / "portfolio_optimized_v2.json",
        {
            "profiles": {
                risk_profile: {
                    "assets": [
                        {"Symbol": "BINANCE:BTCUSDT_rating_all_long_LONG", "Weight": 0.7, "Net_Weight": 0.7},
                        {"Symbol": "BINANCE:ETHUSDT_rating_all_long_LONG", "Weight": 0.3, "Net_Weight": 0.3},
                    ]
                }
            }
        },
    )

    out_stub = meta_dir / "portfolio_optimized_meta.json"
    flatten_weights(meta_profile, str(out_stub), risk_profile)

    out_path = meta_dir / f"portfolio_optimized_meta_{meta_profile}_{risk_profile}.json"
    out = json.loads(out_path.read_text(encoding="utf-8"))
    symbols = [w["Symbol"] for w in out["weights"]]

    assert "BINANCE:BTCUSDT" in symbols
    assert "BINANCE:ETHUSDT" in symbols
    assert all("_" not in s for s in symbols)
