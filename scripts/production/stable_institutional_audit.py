import argparse
import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("institutional_audit")

# Institutional Risk Anchors (v3.6.1)
VOL_BENCHMARKS = {
    "min_variance": 0.35,
    "market_neutral": 0.35,
    "hrp": 0.45,
    "risk_parity": 0.50,
    "erc": 0.50,
    "barbell": 0.50,
    "equal_weight": 0.60,
    "max_sharpe": 0.90,
}


class InstitutionalAuditor:
    """
    Forensic Audit Tool for Quantitative Tournament Data.
    Analyzes selection funnel efficiency and rebalance window stability.
    """

    def __init__(self, run_id_pattern: str = "*", output_prefix: str = "institutional_audit"):
        self.run_id_pattern = run_id_pattern
        self.output_prefix = output_prefix
        # Key: (RunID, Selection, Engine, Profile, Simulator) -> Results
        self.run_results: Dict[Tuple, Dict[str, Any]] = {}
        self.funnel_stats: Dict[str, pd.DataFrame] = {}  # run_id -> DataFrame of windows

    def find_runs(self) -> List[Path]:
        settings = get_settings()
        runs_dir = settings.summaries_runs_dir
        if not runs_dir.exists():
            logger.error("Runs directory not found.")
            return []
        if "*" in self.run_id_pattern:
            return sorted(list(runs_dir.glob(self.run_id_pattern)))
        else:
            specific = runs_dir / self.run_id_pattern
            return [specific] if specific.exists() else []

    def _get_metric(self, metrics: Dict[str, Any], keys: List[str], default: float = 0.0) -> float:
        for k in keys:
            val = metrics.get(k)
            if val is not None:
                try:
                    if isinstance(val, str) and "%" in val:
                        return float(val.replace("%", "")) / 100.0
                    return float(val)
                except (ValueError, TypeError):
                    continue
        return default

    def process_run(self, run_path: Path):
        audit_file = run_path / "audit.jsonl"
        if not audit_file.exists():
            return

        run_id = run_path.name

        config = {}
        with open(audit_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "genesis":
                        config = entry.get("config", {})
                        break
                except Exception:
                    continue

        test_window = int(config.get("test_window", 20))
        step_size = int(config.get("step_size", 20))
        is_continuous = test_window == step_size

        series: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
        funnel_rows = []

        with open(audit_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    step = entry.get("step")
                    status = entry.get("status")
                    ctx = entry.get("context", {})
                    met = entry.get("outcome", {}).get("metrics", {})
                    data = entry.get("data", {})
                    win_idx = ctx.get("window_index")

                    if step == "backtest_select" and status == "success":
                        winners = data.get("winners_meta", [])
                        n_shorts = len([w for w in winners if w.get("direction") == "SHORT"])

                        # Selection Funnel Traceability (v3.6.0 Standard)
                        discovered = met.get("n_discovery_candidates", 0)
                        refined = met.get("n_refinement_candidates", 0)
                        universe = met.get("n_universe_symbols", 0)

                        # Trace MLOps stages for discovered count if missing
                        if discovered == 0 and "pipeline_audit" in data:
                            for stage_event in data["pipeline_audit"]:
                                if stage_event.get("stage") == "Ingestion":
                                    discovered = max(discovered, stage_event.get("data", {}).get("n_candidates", 0))

                        funnel_rows.append(
                            {
                                "Window": win_idx,
                                "Universe": universe,
                                "Refined": refined,
                                "Discovered": discovered,
                                "Selected": met.get("n_winners", 0),
                                "Shorts": n_shorts,
                            }
                        )

                    if step == "backtest_simulate" and status == "success":
                        engine = str(ctx.get("engine", met.get("eng", "unknown")))
                        profile = str(ctx.get("profile", met.get("prof", "unknown")))
                        simulator = str(ctx.get("simulator", met.get("sim", "unknown")))
                        selection_mode = str(ctx.get("selection_mode") or config.get("selection_mode", "unknown"))

                        key = (engine, profile, simulator)
                        if key not in series:
                            series[key] = []

                        # CR-750: Independent Verification Logic
                        daily_returns = data.get("daily_returns", [])
                        verification = {"agreement": True, "details": {}}
                        if daily_returns:
                            # Re-calculate core metrics from raw series
                            dr_series = pd.Series(daily_returns)

                            # Use annualization factor from ledger if available (CR-750)
                            ledger_ann_factor = data.get("ann_factor")

                            # Use existing metrics utility for parity
                            from tradingview_scraper.utils.metrics import calculate_performance_metrics

                            calc = calculate_performance_metrics(dr_series)

                            # Check agreement with reported Sharpe
                            rep_sharpe = self._get_metric(met, ["sharpe"])
                            # If ledger factor differs from detected factor, adjust calculation
                            if ledger_ann_factor and abs(calc.get("ann_factor", 0) - ledger_ann_factor) > 1:
                                # Recalculate using ledger factor
                                calc = calculate_performance_metrics(dr_series, periods=int(ledger_ann_factor))
                                # For now, we log the factor mismatch
                                pass

                            if abs(calc["sharpe"] - rep_sharpe) > 0.01:
                                verification = {"agreement": False, "details": {"diff": calc["sharpe"] - rep_sharpe}}
                                logger.warning(
                                    f"Metric Mismatch at Win {win_idx}: Reported Sharpe {rep_sharpe:.2f} vs Calc {calc['sharpe']:.2f} (Factor: {calc.get('ann_factor', 'N/A')} vs Ledger: {ledger_ann_factor or 'N/A'})"
                                )

                        series[key].append(
                            {
                                "window": win_idx,
                                "ret": self._get_metric(met, ["total_return", "return"]),
                                "ann_ret": self._get_metric(met, ["annualized_return"]),
                                "sharpe": self._get_metric(met, ["sharpe"]),
                                "max_dd": self._get_metric(met, ["max_drawdown"]),
                                "vol": self._get_metric(met, ["annualized_vol", "realized_vol"]),
                                "turnover": self._get_metric(met, ["turnover"]),
                                "selection_mode": selection_mode,
                                "verified": verification["agreement"],
                            }
                        )
                except Exception:
                    continue

        self.funnel_stats[run_id] = pd.DataFrame(funnel_rows)

        for (engine, profile, simulator), windows in series.items():
            if not windows:
                continue

            # Filter out windows with no index (should be rare)
            valid_windows = [w for w in windows if w.get("window") is not None]
            if not valid_windows:
                continue

            sorted_win = sorted(valid_windows, key=lambda x: int(x["window"]))
            rets = [w["ret"] for w in sorted_win]
            sharpes = [w["sharpe"] for w in sorted_win]
            selection_mode = sorted_win[0]["selection_mode"]

            if is_continuous:
                # Compounded Strategy TWR
                cum_ret = np.prod([1 + r for r in rets]) - 1
                total_days = len(rets) * test_window

                if cum_ret <= -1.0:
                    strat_ann_ret = -1.0
                else:
                    try:
                        strat_ann_ret = (1 + cum_ret) ** (365.0 / total_days) - 1 if total_days > 0 else 0.0
                    except (ValueError, OverflowError):
                        strat_ann_ret = -1.0

                equity = np.cumprod([1 + r for r in rets])
                peak = np.maximum.accumulate(equity)
                dd_series = (equity - peak) / (peak + 1e-12)
                strat_max_dd = float(np.min(dd_series))
            else:
                # Discrete averages
                strat_ann_ret = np.mean([np.clip(w["ann_ret"], -1.0, 5.0) for w in sorted_win])
                strat_max_dd = np.mean([w["max_dd"] for w in sorted_win])

            strat_max_dd = max(-1.0, strat_max_dd)

            f_df = self.funnel_stats[run_id]
            avg_discovered = f_df["Discovered"].mean() if not f_df.empty else 0
            avg_selected = f_df["Selected"].mean() if not f_df.empty else 0

            self.run_results[(run_id, selection_mode, engine, profile, simulator)] = {
                "Sharpe": np.mean(sharpes),
                "Stability": np.mean(sharpes) / (np.std(sharpes) + 1e-9),
                "AnnRet": strat_ann_ret,
                "MaxDD": strat_max_dd,
                "Vol": np.mean([w["vol"] for w in sorted_win]),
                "Turnover": np.mean([w["turnover"] for w in sorted_win]),
                "Windows": len(sorted_win),
                "AvgDiscovered": int(avg_discovered),
                "AvgSelected": int(avg_selected),
                "IsContinuous": is_continuous,
                "Integrity": np.mean([w.get("verified", True) for w in sorted_win]),
            }

    def generate_report(self):
        if not self.run_results:
            print("# ❌ No Institutional Audit Data Found")
            return

        rows = []
        for (run_id, selection, engine, profile, simulator), metrics in self.run_results.items():
            rows.append({"RunID": run_id, "Selection": selection, "Profile": profile, "Engine": engine, "Simulator": simulator, **metrics})
        df = pd.DataFrame(rows)

        print("\n# 🏛️ INSTITUTIONAL FORENSIC AUDIT (v3.6.1)")
        print(f"**Generated**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("> Note: 'AnnRet' is compounded TWR for continuous runs, or Window Mean for discrete runs.")

        summary = (
            df.groupby(["Selection", "Profile", "Engine", "Simulator"])
            .agg({"Sharpe": "mean", "Stability": "mean", "AnnRet": "mean", "MaxDD": "mean", "Vol": "mean", "AvgDiscovered": "mean", "AvgSelected": "mean", "Windows": "sum", "Integrity": "mean"})
            .reset_index()
            .sort_values("Sharpe", ascending=False)
        )

        # Volatility Accuracy
        def vol_acc(row):
            target = VOL_BENCHMARKS.get(str(row["Profile"]), 0.50)
            realized = float(row["Vol"])
            if realized <= 0:
                return 0.0
            return 1.0 - min(1.0, abs(realized - target) / (target + 1e-9))

        summary["Vol Accuracy"] = summary.apply(vol_acc, axis=1)

        # Formatting Display
        disp = summary.copy()
        disp["AnnRet"] = disp["AnnRet"].apply(lambda x: f"{x:.1%}")
        disp["MaxDD"] = disp["MaxDD"].apply(lambda x: f"{x:.1%}")
        disp["Vol Accuracy"] = disp["Vol Accuracy"].apply(lambda x: f"{x:.1%}")
        disp["Sharpe"] = disp["Sharpe"].apply(lambda x: f"{x:.3f}")
        disp["Stability"] = disp["Stability"].apply(lambda x: f"{x:.2f}")
        disp["Integrity"] = disp["Integrity"].apply(lambda x: f"{x:.1%}")

        cols = ["Selection", "Profile", "Engine", "Simulator", "Sharpe", "Stability", "AnnRet", "MaxDD", "Vol", "Vol Accuracy", "AvgDiscovered", "AvgSelected", "Integrity"]
        print("\n## 📊 System-Wide Performance Matrix")
        # Force conversion to DataFrame to satisfy type checker if needed
        print(pd.DataFrame(disp)[cols].to_markdown(index=False))

        print("\n## 🌪️ Selection Funnel Forensic Trace")
        for rid, f_df in sorted(self.funnel_stats.items()):
            if f_df.empty:
                continue
            print(f"### Run: {rid}")
            print(pd.DataFrame(f_df).to_markdown(index=False))

        print("\n## 🔍 Anomaly & Outlier Identification")
        # Find runs with MaxDD < -60% or extreme Sharpe drift
        anorms = df[(df["AnnRet"].abs() > 3.0) | (df["MaxDD"] < -0.60)]
        if not anorms.empty:
            print("### 🚨 Strategic Outliers Detected (Extreme Risk/Return)")
            print(pd.DataFrame(anorms)[["RunID", "Profile", "AnnRet", "MaxDD", "Vol"]].to_markdown(index=False))
        else:
            print("- No extreme strategic anomalies detected in composite curves.")

        # Final Export
        settings = get_settings()
        export_dir = settings.artifacts_dir / "reports"
        export_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = export_dir / f"composite_institutional_audit_{ts}.csv"
        df.to_csv(path, index=False)
        logger.info(f"\n[SUCCESS] Composite Audit saved to {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="*", help="Run ID pattern")
    args = parser.parse_args()
    auditor = InstitutionalAuditor(run_id_pattern=args.run_id)
    runs = auditor.find_runs()
    for r in runs:
        auditor.process_run(r)
    auditor.generate_report()


if __name__ == "__main__":
    main()
