import json

import numpy as np
import pandas as pd

from scripts.research.tournament_scoreboard import (
    CandidateThresholds,
    _beta_corr,
    _load_optimize_metrics,
    build_scoreboard,
)


def _win(end_date: str, *, sharpe: float, returns: float, regime: str = "NORMAL"):
    return {"end_date": end_date, "sharpe": sharpe, "returns": returns, "regime": regime}


def _summary(*, sharpe: float, ann_ret: float, mdd: float, cvar: float, turnover: float, af_dist: float, stress_alpha: float):
    return {
        "avg_window_sharpe": sharpe,
        "annualized_return": ann_ret,
        "annualized_vol": 0.10,
        "max_drawdown": mdd,
        "cvar_95": cvar,
        "avg_turnover": turnover,
        "antifragility_dist": {"af_dist": af_dist},
        "antifragility_stress": {"stress_alpha": stress_alpha, "stress_delta": 0.0, "reference": "market"},
    }


def test_beta_corr_simple_relationship():
    idx = pd.date_range("2024-01-01", periods=50, freq="D")
    mkt = pd.Series(np.linspace(-0.01, 0.01, len(idx)), index=idx)
    strat = 2.0 * mkt

    beta, corr = _beta_corr(strat, mkt)
    assert beta is not None and abs(beta - 2.0) < 1e-6
    assert corr is not None and corr > 0.99


def test_load_optimize_metrics_computes_jaccard_and_hhi(tmp_path):
    audit = tmp_path / "audit.jsonl"

    rec0 = {
        "type": "action",
        "status": "success",
        "step": "backtest_optimize",
        "context": {"selection_mode": "v3.2", "rebalance_mode": "window", "engine": "skfolio", "profile": "hrp", "window_index": 0},
        "outcome": {"output_hashes": {}, "metrics": {}},
        "data": {"weights": {"A": 0.5, "B": 0.5}},
    }
    rec1 = {
        "type": "action",
        "status": "success",
        "step": "backtest_optimize",
        "context": {"selection_mode": "v3.2", "rebalance_mode": "window", "engine": "skfolio", "profile": "hrp", "window_index": 1},
        "outcome": {"output_hashes": {}, "metrics": {}},
        "data": {"weights": {"A": 0.5, "C": 0.5}},
    }

    audit.write_text("\n".join([json.dumps(rec0), json.dumps(rec1)]) + "\n", encoding="utf-8")

    m = _load_optimize_metrics(audit)
    key = ("v3.2", "window", "skfolio", "hrp")
    assert key in m
    assert abs(float(m[key]["selection_jaccard"]) - (1 / 3)) < 1e-9
    assert abs(float(m[key]["hhi"]) - 0.5) < 1e-9


def test_build_scoreboard_candidate_flag_fails_on_friction_decay():
    # Baseline market windows/summary
    mkt_windows = [_win("2024-01-10", sharpe=1.0, returns=0.01), _win("2024-01-20", sharpe=1.0, returns=-0.01)]
    mkt_summary = _summary(sharpe=1.0, ann_ret=0.05, mdd=-0.10, cvar=-0.02, turnover=0.10, af_dist=0.0, stress_alpha=0.0)

    # Strategy windows/summary
    strat_windows = [_win("2024-01-10", sharpe=2.0, returns=0.02), _win("2024-01-20", sharpe=2.0, returns=-0.01)]

    results = {
        "custom": {
            "market": {"market": {"summary": mkt_summary, "windows": mkt_windows}},
            "skfolio": {"hrp": {"summary": _summary(sharpe=3.0, ann_ret=0.10, mdd=-0.10, cvar=-0.02, turnover=0.20, af_dist=0.10, stress_alpha=0.01), "windows": strat_windows}},
        },
        "cvxportfolio": {
            "market": {"market": {"summary": mkt_summary, "windows": mkt_windows}},
            "skfolio": {"hrp": {"summary": _summary(sharpe=2.0, ann_ret=0.09, mdd=-0.10, cvar=-0.02, turnover=0.20, af_dist=0.10, stress_alpha=0.01), "windows": strat_windows}},
        },
        "nautilus": {
            "market": {"market": {"summary": mkt_summary, "windows": mkt_windows}},
            "skfolio": {"hrp": {"summary": _summary(sharpe=2.0, ann_ret=0.091, mdd=-0.10, cvar=-0.02, turnover=0.20, af_dist=0.10, stress_alpha=0.01), "windows": strat_windows}},
        },
    }

    audit_opt = {("v3.2", "window", "skfolio", "hrp"): {"selection_jaccard": 0.5}}
    thresholds = CandidateThresholds(max_friction_decay=0.30)

    df = build_scoreboard(
        results,
        selection_mode="v3.2",
        rebalance_mode="window",
        audit_opt=audit_opt,
        returns_dir=None,
        thresholds=thresholds,
        allow_missing=False,
    )

    row = df[(df["engine"] == "skfolio") & (df["profile"] == "hrp") & (df["simulator"] == "cvxportfolio")].iloc[0]
    assert bool(row["is_candidate"]) is False
    assert "friction_decay" in str(row["candidate_failures"])


def test_build_scoreboard_populates_selection_jaccard_for_baselines_when_present():
    mkt_windows = [_win("2024-01-10", sharpe=1.0, returns=0.01), _win("2024-01-20", sharpe=1.0, returns=-0.01)]
    mkt_summary = _summary(sharpe=1.0, ann_ret=0.05, mdd=-0.10, cvar=-0.02, turnover=0.10, af_dist=0.0, stress_alpha=0.0)

    results = {
        "custom": {
            "market": {
                "market": {"summary": mkt_summary, "windows": mkt_windows},
                "benchmark": {"summary": mkt_summary, "windows": mkt_windows},
                "raw_pool_ew": {"summary": mkt_summary, "windows": mkt_windows},
            }
        }
    }

    audit_opt = {
        ("v3.2", "window", "market", "market"): {"selection_jaccard": 0.90},
        ("v3.2", "window", "market", "benchmark"): {"selection_jaccard": 0.80},
        ("v3.2", "window", "market", "raw_pool_ew"): {"selection_jaccard": 0.70},
    }

    df = build_scoreboard(
        results,
        selection_mode="v3.2",
        rebalance_mode="window",
        audit_opt=audit_opt,
        returns_dir=None,
        thresholds=CandidateThresholds(),
        allow_missing=False,
    )

    for profile, expected in [("market", 0.90), ("benchmark", 0.80), ("raw_pool_ew", 0.70)]:
        row = df[(df["engine"] == "market") & (df["profile"] == profile) & (df["simulator"] == "custom")].iloc[0]
        assert abs(float(row["selection_jaccard"]) - expected) < 1e-12
        assert "missing:selection_jaccard" not in str(row["candidate_failures"])
