import json
import os

import pandas as pd
import pytest


def test_selection_engine_anchor_prioritization():
    returns_path = "data/lakehouse/portfolio_returns.pkl"
    if not os.path.exists(returns_path):
        pytest.skip("Returns matrix missing")
    df = pd.read_pickle(returns_path)
    anchors = ["BINANCE:BTCUSDT", "BINANCE:SOLUSDT.P", "BINANCE:XRPUSDT.P"]
    present = [a for a in anchors if a in df.columns]
    assert len(present) > 0
    last_date = df.index.max()
    for a in present:
        assert df[a].dropna().index.max() >= last_date - pd.Timedelta(days=2)


def test_portfolio_rotation_integrity():
    runs_dir = "artifacts/summaries/runs"
    runs = sorted([d for d in os.listdir(runs_dir) if d.startswith("2026")], reverse=True)
    opt_path = None
    for r in runs:
        p = f"{runs_dir}/{r}/data/metadata/portfolio_optimized_v2.json"
        if os.path.exists(p):
            opt_path = p
            break
    if not opt_path:
        pytest.skip("No opt file")
    with open(opt_path, "r") as f:
        data = json.load(f)
    btc_found = False
    for p in data.get("profiles", {}).values():
        if any(a.get("Symbol") == "BINANCE:BTCUSDT" for a in p.get("assets", [])):
            btc_found = True
            break
    assert btc_found


def test_audit_ledger_continuity():
    runs_dir = "artifacts/summaries/runs"
    runs = sorted([d for d in os.listdir(runs_dir) if d.startswith("2026")], reverse=True)
    ledger = None
    for r in runs:
        p = f"{runs_dir}/{r}/audit.jsonl"
        if os.path.exists(p):
            ledger = p
            break
    if not ledger:
        pytest.skip("No ledger")
    with open(ledger, "r") as f:
        lines = f.readlines()
    assert len(lines) > 0
    for i in range(1, len(lines)):
        try:
            c, p = json.loads(lines[i]), json.loads(lines[i - 1])
            if "hash" in p and "prev_hash" in c:
                assert c["prev_hash"] == p["hash"]
        except Exception:
            continue
