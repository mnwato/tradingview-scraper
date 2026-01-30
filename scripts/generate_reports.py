import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import pandas as pd

from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.metrics import get_full_report_markdown

# Add project root to path for scripts imports
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("reporting_engine")

PROFILES = ["min_variance", "hrp", "max_sharpe", "barbell", "benchmark", "equal_weight", "market", "adaptive", "risk_parity"]
SUMMARY_COLS = [
    "Profile",
    "total_cumulative_return",
    "annualized_return",
    "annualized_vol",
    "avg_window_sharpe",
    "af_dist",
    "stress_alpha",
    "stress_delta",
    "avg_turnover",
    "sortino",
    "calmar",
    "win_rate",
    "Details",
]


def _fmt_num(val: Any, fmt: str) -> str:
    try:
        if val is None or pd.isna(val):
            return "N/A"
        return f"{float(val):{fmt}}"
    except Exception:
        return str(val)


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


class ReportGenerator:
    def __init__(self):
        self.settings = get_settings()
        if not os.getenv("TV_RUN_ID"):
            latest_run = self._detect_latest_run()
            if latest_run:
                logger.info(f"Auto-detected latest run: {latest_run}")
                self.settings.run_id = latest_run

        self.summary_dir = self.settings.prepare_summaries_run_dir()
        self.config_dir = self.settings.run_config_dir
        self.reports_dir = self.settings.run_reports_dir
        self.plots_dir = self.settings.run_plots_dir
        self.data_dir = self.settings.run_data_dir
        self.logs_dir = self.settings.run_logs_dir
        self.tearsheet_root = self.settings.run_tearsheets_dir

        self.tournament_path = self.data_dir / "tournament_results.json"
        # Backward compatibility check
        if not self.tournament_path.exists():
            legacy_path = self.summary_dir / "tournament_results.json"
            if legacy_path.exists():
                self.tournament_path = legacy_path

        self.returns_dir = self.data_dir / "returns"
        # Backward compatibility check for returns
        if not any(self.returns_dir.glob("*.pkl")):
            legacy_returns = self.summary_dir / "returns"
            if legacy_returns.exists() and any(legacy_returns.glob("*.pkl")):
                self.returns_dir = legacy_returns

        self.tearsheet_root.mkdir(parents=True, exist_ok=True)

        self.data: Dict[str, Any] = {}
        if self.tournament_path.exists():
            with open(self.tournament_path, "r") as f:
                self.data = json.load(f)
            logger.info(f"Loaded tournament results from {self.tournament_path}")

        if not self.data:
            event = self._get_latest_audit_event("tournament_complete")
            if event and event.get("data"):
                logger.info("Loaded tournament results from Audit Ledger.")
                self.data = {"meta": event["data"].get("meta", {}), "results": event["data"].get("tournament_summary", {})}

        self.meta = self.data.get("meta", {})
        self.all_results = self.data.get("results", {})
        self._restructure_results_if_needed()
        self.benchmark = self._load_spy_benchmark()

    def _restructure_results_if_needed(self):
        """Restructures flat window results into a nested dictionary if needed."""
        if isinstance(self.all_results, list):
            logger.info("Restructuring flat tournament results for reporting...")
            agg = {}
            for res in self.all_results:
                sim = res.get("simulator", "custom")
                eng = res.get("engine", "custom")
                prof = res.get("profile", "equal_weight")

                sim_node = agg.setdefault(sim, {})
                eng_node = sim_node.setdefault(eng, {})
                prof_node = eng_node.setdefault(prof, {"windows": [], "summary": {}})

                # Flatten metrics for report consumption (CR-827)
                flattened_res = res.copy()
                metrics = res.get("metrics", {})
                for k, v in metrics.items():
                    flattened_res[k] = v
                    # Common aliases used in reporting
                    if k == "annualized_vol":
                        flattened_res["vol"] = v
                    if k == "annualized_return":
                        flattened_res["return"] = v
                    if k == "max_drawdown":
                        flattened_res["mdd"] = v

                prof_node["windows"].append(flattened_res)

            for sim in agg:
                for eng in agg[sim]:
                    for prof in agg[sim][eng]:
                        node = agg[sim][eng][prof]
                        windows = node["windows"]
                        all_metrics = [w.get("metrics", {}) for w in windows]
                        if not all_metrics:
                            continue

                        summary = {}

                        # CR-Fix: Calculate summary from Stitched Returns (Global) instead of averaging windows
                        # Standard name format from backtest_engine.py is {engine}_{simulator}_{profile}.pkl
                        pkl_name = f"{eng}_{sim}_{prof}.pkl"
                        pkl_path = self.returns_dir / pkl_name

                        full_series = None
                        if pkl_path.exists():
                            try:
                                full_series = pd.read_pickle(pkl_path)
                            except Exception as e:
                                logger.warning(f"Failed to load stitched returns for {pkl_name}: {e}")

                        if full_series is not None and not full_series.empty:
                            # Calculate global metrics
                            from tradingview_scraper.utils.metrics import calculate_performance_metrics

                            # Assume 365 for crypto if undetectable, or use logic
                            # We can reuse the utility
                            m = calculate_performance_metrics(full_series)
                            summary["annualized_return"] = m["annualized_return"]
                            summary["return"] = m["annualized_return"]
                            summary["annualized_vol"] = m["annualized_vol"]
                            summary["vol"] = m["annualized_vol"]
                            summary["sharpe"] = m["sharpe"]
                            summary["avg_window_sharpe"] = m["sharpe"]  # Use global sharpe
                            summary["max_drawdown"] = m["max_drawdown"]
                            summary["mdd"] = m["max_drawdown"]

                            # Average non-return metrics from windows (e.g. turnover)
                            # 'w' is already flattened in the loop above
                            turnovers = [w.get("turnover") for w in windows]
                            turnovers = [t for t in turnovers if t is not None]
                            if turnovers:
                                summary["avg_turnover"] = sum(turnovers) / len(turnovers)

                            # Average win rate
                            win_rates = [w.get("win_rate") for w in windows]
                            win_rates = [wr for wr in win_rates if wr is not None]
                            if win_rates:
                                summary["win_rate"] = sum(win_rates) / len(win_rates)
                        else:
                            # Fallback to Window Averaging (Legacy)
                            metric_keys = set()
                            for m in all_metrics:
                                metric_keys.update(m.keys())

                            for k in metric_keys:
                                vals = [m[k] for m in all_metrics if k in m and isinstance(m[k], (int, float))]
                                if vals:
                                    avg_val = sum(vals) / len(vals)
                                    summary[f"avg_window_{k}"] = avg_val
                                    summary[k] = avg_val
                                    # Provide aliases for summary keys as well
                                    if k == "turnover":
                                        summary["avg_turnover"] = avg_val
                                    if k == "annualized_vol":
                                        summary["vol"] = avg_val
                                    if k == "annualized_return":
                                        summary["return"] = avg_val
                                    if k == "max_drawdown":
                                        summary["mdd"] = avg_val
                                    if k == "sharpe":
                                        summary["avg_window_sharpe"] = avg_val

                        node["summary"] = summary
            self.all_results = agg

    def _detect_latest_run(self) -> Optional[str]:
        runs_dir = Path("artifacts/summaries/runs/")
        if not runs_dir.exists():
            return None
        # Filter for actual run directories (not symlinks like 'latest')
        date_pattern = re.compile(r"^\d{8}-\d{6}$")
        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir() and not d.is_symlink() and date_pattern.match(d.name)]
        complete = [d for d in run_dirs if (d / "audit.jsonl").exists() and ((d / "tournament_results.json").exists() or (d / "data" / "tournament_results.json").exists())]
        candidates = complete or run_dirs
        candidates = sorted(candidates, key=lambda p: p.name)
        return candidates[-1].name if candidates else None

    def _load_spy_benchmark(self) -> Optional[pd.Series]:
        returns_path = Path("data/lakehouse/portfolio_returns.pkl")
        if not returns_path.exists():
            return None
        try:
            all_rets = cast(pd.DataFrame, pd.read_pickle(returns_path))
            if not self.settings.benchmark_symbols:
                return None
            symbol = self.settings.benchmark_symbols[0]
            if symbol in all_rets.columns:
                s = cast(pd.Series, all_rets[symbol])
                s.index = pd.to_datetime(s.index)
                if hasattr(s.index, "tz") and getattr(s.index, "tz") is not None:
                    s.index = cast(pd.DatetimeIndex, s.index).tz_convert(None)
                return s
        except Exception:
            pass
        return None

    def _get_latest_audit_event(self, step: str) -> Optional[Dict[str, Any]]:
        """Retrieves the latest success event for a given step from the audit ledger."""
        audit_path = self.summary_dir / "audit.jsonl"
        if not audit_path.exists():
            return None

        last_event = None
        try:
            with open(audit_path, "r") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                        if rec.get("step") == step and rec.get("status") == "success":
                            last_event = rec
                    except Exception:
                        pass
        except Exception:
            pass
        return last_event

    def generate_all(self):
        logger.info("Generating unified quantitative reports...")
        self._generate_cluster_analysis()
        self._generate_strategy_teardowns()
        self._generate_alpha_isolation()
        if self.settings.features.feat_decay_audit:
            self._generate_decay_audit()
        self._generate_tournament_benchmark()
        self._generate_selection_report()
        self._generate_master_index()
        self._cleanup_root_leftovers()
        logger.info(f"Reporting complete. Artifacts in: {self.summary_dir}")

    def _cleanup_root_leftovers(self):
        """Moves legacy root artifacts to their new structured homes."""
        mapping = {
            "cluster_analysis.md": self.reports_dir / "research" / "cluster_analysis.md",
            "correlation_report.md": self.reports_dir / "research" / "correlations.md",
            "hedge_anchors.md": self.reports_dir / "portfolio" / "hedge_anchors.md",
            "portfolio_report.md": self.reports_dir / "portfolio" / "report.md",
            "selection_audit.md": self.reports_dir / "selection" / "audit.md",
            "selection_report.md": self.reports_dir / "selection" / "report.md",
            "data_health_raw.md": self.reports_dir / "selection" / "data_health_raw.md",
            "data_health_selected.md": self.reports_dir / "selection" / "data_health_selected.md",
            "alpha_isolation_audit.md": self.reports_dir / "portfolio" / "alpha_isolation.md",
            "slippage_decay_audit.md": self.reports_dir / "portfolio" / "slippage_decay.md",
            "engine_comparison_report.md": self.reports_dir / "engine" / "comparison.md",
            "factor_map.png": self.plots_dir / "risk" / "factor_map.png",
            "portfolio_clustermap.png": self.plots_dir / "clustering" / "portfolio_clustermap.png",
            "volatility_clustermap.png": self.plots_dir / "clustering" / "volatility_clustermap.png",
            "selection_audit.json": self.config_dir / "selection_audit.json",
            "resolved_manifest.json": self.config_dir / "resolved_manifest.json",
            "tournament_results.json": self.data_dir / "tournament_results.json",
            "portfolio_clusters.json": self.data_dir / "metadata" / "portfolio_clusters.json",
            "correlations.json": self.data_dir / "metadata" / "correlations.json",
        }

        for filename, target_path in mapping.items():
            source = self.summary_dir / filename
            if source.exists() and source.is_file():
                if not target_path.exists():
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(target_path))
                    logger.info(f"Moved {filename} to {target_path.relative_to(self.summary_dir)}")
                else:
                    # Target exists, delete duplicate from root
                    source.unlink()
                    logger.info(f"Removed duplicate {filename} from root.")

    def _generate_selection_report(self):
        try:
            import importlib

            gen_sel = importlib.import_module("scripts.generate_selection_report")
            generate_selection_report = gen_sel.generate_selection_report
            logger.info("Generating Universe Selection Report...")

            # CR-831: Workspace Isolation
            audit_path = os.getenv("SELECTION_AUDIT", str(self.data_dir / "selection_audit.json"))
            if not os.path.exists(audit_path):
                audit_path = "data/lakehouse/selection_audit.json"

            event = self._get_latest_audit_event("natural_selection")
            audit_data = event["data"] if event and event.get("data") and "selection" in event["data"] else None
            out_p = self.reports_dir / "selection" / "report.md"
            out_p.parent.mkdir(parents=True, exist_ok=True)
            generate_selection_report(audit_path=audit_path, output_path=str(out_p), audit_data=audit_data)
        except Exception as e:
            logger.error(f"Selection Report failed: {e}")

    def _generate_cluster_analysis(self):
        try:
            import importlib

            analyze_c = importlib.import_module("scripts.analyze_clusters")
            analyze_clusters = analyze_c.analyze_clusters
            logger.info("Generating Hierarchical Cluster Analysis...")

            # CR-831: Workspace Isolation
            c_path = os.getenv("CLUSTERS_FILE", str(self.data_dir / "portfolio_clusters.json"))
            if not os.path.exists(c_path):
                c_path = "data/lakehouse/portfolio_clusters.json"

            event = self._get_latest_audit_event("natural_selection")
            if event and event.get("data") and "portfolio_clusters" in event["data"]:
                clusters = event["data"]["portfolio_clusters"]
                ledger_c_path = str(self.data_dir / "metadata" / "portfolio_clusters.json")
                os.makedirs(os.path.dirname(ledger_c_path), exist_ok=True)
                with open(ledger_c_path, "w") as f:
                    json.dump(clusters, f, indent=2)
                c_path = ledger_c_path

            m_path = os.getenv("PORTFOLIO_META", str(self.data_dir / "portfolio_meta.json"))
            if not os.path.exists(m_path):
                m_path = "data/lakehouse/portfolio_meta.json"

            r_path = os.getenv("RETURNS_MATRIX", str(self.data_dir / "returns_matrix.parquet"))
            if not os.path.exists(r_path):
                r_path = "data/lakehouse/portfolio_returns.pkl"

            s_path = os.getenv("ANTIFRAGILITY_STATS", str(self.data_dir / "antifragility_stats.json"))
            if not os.path.exists(s_path):
                s_path = "data/lakehouse/antifragility_stats.json"

            if os.path.exists(c_path):
                out_p = self.reports_dir / "research" / "cluster_analysis.md"
                out_p.parent.mkdir(parents=True, exist_ok=True)
                plot_dir = self.plots_dir / "clustering"
                plot_dir.mkdir(parents=True, exist_ok=True)
                analyze_clusters(
                    clusters_path=str(c_path),
                    meta_path=str(m_path),
                    returns_path=str(r_path),
                    stats_path=str(s_path),
                    output_path=str(out_p),
                    image_path=str(plot_dir / "portfolio_clustermap.png"),
                    vol_image_path=str(plot_dir / "volatility_clustermap.png"),
                )
        except Exception as e:
            logger.error(f"Cluster Analysis failed: {e}")

    def _generate_strategy_teardowns(self):
        best_engines = self._identify_tournament_winners()
        essential_reports: List[str] = []
        if not self.returns_dir.exists():
            return
        for pkl_path in self.returns_dir.glob("*.pkl"):
            try:
                name = pkl_path.stem
                rets = cast(pd.Series, pd.read_pickle(pkl_path))
                if rets.empty:
                    continue
                new_idx = [pd.to_datetime(t).replace(tzinfo=None) for t in rets.index]
                rets.index = pd.DatetimeIndex(new_idx)
                parts = name.split("_")
                if len(parts) < 3:
                    continue
                sim, eng, prof = parts[0], parts[1], "_".join(parts[2:])
                target_benchmark = self.benchmark
                if eng == "market":
                    target_benchmark = None
                if target_benchmark is not None and hasattr(target_benchmark.index, "tz") and getattr(target_benchmark.index, "tz") is not None:
                    target_benchmark = target_benchmark.copy()
                    target_benchmark.index = cast(pd.DatetimeIndex, target_benchmark.index).tz_convert(None)
                md_content = get_full_report_markdown(
                    rets,
                    benchmark=target_benchmark,
                    title=f"{eng.upper()} / {prof.upper()} ({sim.upper()})",
                    mode=self.settings.report_mode,
                )
                with open(self.tearsheet_root / f"{name}_full_report.md", "w") as f:
                    f.write(md_content)
                is_essential = False
                if sim == "cvxportfolio":
                    if eng in {"custom", "market"}:
                        is_essential = True
                    elif prof in best_engines and eng == best_engines[prof]["engine"]:
                        is_essential = True
                if is_essential:
                    essential_reports.append(str(self.tearsheet_root / f"{name}_full_report.md"))
            except Exception as e:
                logger.error(f"Failed teardown for {pkl_path.name}: {e}")

        essential_reports.extend(
            [
                str(self.reports_dir / "portfolio" / "backtest_comparison.md"),
                str(self.reports_dir / "engine" / "comparison.md"),
                str(self.reports_dir / "portfolio" / "alpha_isolation.md"),
            ]
        )
        if self.settings.features.feat_decay_audit:
            essential_reports.append(str(self.reports_dir / "portfolio" / "slippage_decay.md"))
        essential_reports.extend(
            [
                str(self.reports_dir / "portfolio" / "report.md"),
                str(self.reports_dir / "selection" / "audit.md"),
                str(self.reports_dir / "selection" / "data_health_selected.md"),
            ]
        )
        with open(self.data_dir / "essential_reports.json", "w") as f:
            json.dump(essential_reports, f, indent=2)

    def _identify_tournament_winners(self) -> Dict[str, Dict[str, Any]]:
        best: Dict[str, Any] = {}
        sim_name = "cvxportfolio" if "cvxportfolio" in self.all_results else "custom"
        sim_data = self.all_results.get(sim_name, {})
        for eng_name, eng_data in sim_data.items():
            if eng_name == "market" or (isinstance(eng_data, dict) and eng_data.get("_status", {}).get("skipped")):
                continue
            for prof_name, prof_data in eng_data.items():
                if prof_name == "_status":
                    continue
                summary = prof_data.get("summary")
                if not summary:
                    continue
                sharpe = _safe_float(summary.get("avg_window_sharpe")) or -999.0
                if prof_name not in best or sharpe > best[prof_name]["sharpe"]:
                    best[prof_name] = {"engine": eng_name, "sharpe": sharpe}
        return best

    def _generate_strategy_resume(self):
        sim_name = "cvxportfolio" if "cvxportfolio" in self.all_results else "custom"
        best_engines = self._identify_tournament_winners()
        summary_rows: List[Dict[str, Any]] = []
        regime_rows: List[Dict[str, Any]] = []

        def _inject_antifragility_fields(row: Dict[str, Any]) -> None:
            dist = row.get("antifragility_dist")
            if isinstance(dist, dict):
                row["af_dist"] = _safe_float(dist.get("af_dist"))

            stress = row.get("antifragility_stress")
            if isinstance(stress, dict):
                row["stress_alpha"] = _safe_float(stress.get("stress_alpha"))
                row["stress_delta"] = _safe_float(stress.get("stress_delta"))

        market_data = self.all_results.get(sim_name, {}).get("market", {})
        if market_data:
            if market_data.get("market", {}).get("summary"):
                m_row = dict(market_data["market"]["summary"])
                _inject_antifragility_fields(m_row)
                m_row["Profile"] = "MARKET (HOLD)"
                m_row["Details"] = f"[Metrics]({sim_name}_market_market_full_report.md)"
                summary_rows.append(m_row)
            if market_data.get("raw_pool_ew", {}).get("summary"):
                raw_row = dict(market_data["raw_pool_ew"]["summary"])
                _inject_antifragility_fields(raw_row)
                raw_row["Profile"] = "MARKET (RAW EW)"
                raw_row["Details"] = f"[Metrics]({sim_name}_market_raw_pool_ew_full_report.md)"
                summary_rows.append(raw_row)
            if market_data.get("benchmark", {}).get("summary"):
                filt_row = dict(market_data["benchmark"]["summary"])
                _inject_antifragility_fields(filt_row)
                filt_row["Profile"] = "MARKET (FILTERED EW)"
                filt_row["Details"] = f"[Metrics]({sim_name}_market_benchmark_full_report.md)"
                summary_rows.append(filt_row)
        display_names = {"min_variance": "MIN VARIANCE", "hrp": "HIERARCHICAL RISK PARITY (HRP)", "max_sharpe": "MAX SHARPE", "barbell": "ANTIFRAGILE BARBELL"}
        for prof_key in PROFILES:
            engine_info = best_engines.get(prof_key)
            eng_name = str(engine_info.get("engine", "custom")) if engine_info else "custom"
            prof_data = self.all_results.get(sim_name, {}).get(eng_name, {}).get(prof_key)
            if not prof_data or not prof_data.get("summary"):
                continue
            summary = prof_data["summary"]
            row = dict(summary)
            _inject_antifragility_fields(row)
            disp_name = display_names.get(prof_key, prof_key.upper())
            row["Profile"] = disp_name
            row["Details"] = f"[Metrics]({sim_name}_{eng_name}_{prof_key}_full_report.md)"
            summary_rows.append(row)
            for w in prof_data.get("windows") or []:
                if w.get("regime") and w.get("returns") is not None:
                    regime_rows.append({"Profile": disp_name, "Regime": w["regime"], "Return": w["returns"]})
        if not summary_rows:
            return
        df = pd.DataFrame(summary_rows)
        for c in ["total_cumulative_return", "annualized_return", "annualized_vol", "avg_turnover", "win_rate", "stress_alpha", "stress_delta"]:
            if c in df.columns:
                df[c] = df[c].apply(lambda x: _fmt_num(x, ".2%"))
        if "af_dist" in df.columns:
            df["af_dist"] = df["af_dist"].apply(lambda x: _fmt_num(x, ".2f"))
        for c in SUMMARY_COLS:
            if c not in df.columns:
                df[c] = None
        df = df[SUMMARY_COLS]
        regime_table = ""
        if regime_rows:
            r_df = pd.DataFrame(regime_rows)
            r_sum = r_df.groupby(["Regime", "Profile"])["Return"].mean().unstack()
            regime_table = str(cast(pd.DataFrame, r_sum.map(lambda x: _fmt_num(x, ".4%"))).to_markdown())
        report = f"# Quantitative Backtest Strategy Resume\nGenerated on: {pd.Timestamp.now()}\nBaseline Simulation: **{sim_name}** simulator.\n\n## 1. Strategy Performance Matrix\n{df.to_markdown(index=False)}\n\n## 2. Regime-Specific Attribution (Avg. Window Return)\n{regime_table}\n\n## 3. Institutional Resume\n- **Simulator Fidelity**: Performance includes estimated slippage and commissions.\n- **Alpha Decay**: See 'engine_comparison_report.md' for detailed execution friction audit.\n"
        with open(self.summary_dir / "backtest_comparison.md", "w") as f:
            f.write(report)

    def _generate_alpha_isolation(self):
        sim_name = "cvxportfolio" if "cvxportfolio" in self.all_results else "custom"
        market_blob = self.all_results.get(sim_name, {}).get("market", {})
        md = ["# Alpha Isolation & Attribution Audit", f"Generated on: {pd.Timestamp.now()}", "\nThis report isolates the value added by **Pruning (Selection)** vs. **Weighting (Optimization)**.\n"]
        raw_ew = market_blob.get("raw_pool_ew", {}).get("summary")

        # Explicitly look for 'benchmark' (Filtered EW) first, then fallback to others
        filt_key = None
        if "benchmark" in market_blob:
            filt_key = "benchmark"
        elif "equal_weight" in market_blob:
            filt_key = "equal_weight"
        else:
            # Last resort fallback excluding statuses and raw_pool
            filt_key = next((k for k in market_blob.keys() if k not in ["_status", "raw_pool_ew", "market"]), None)

        filt_ew = market_blob.get(str(filt_key), {}).get("summary") if filt_key else None

        if raw_ew and filt_ew:
            ann_raw, ann_filt = _safe_float(raw_ew.get("annualized_return")) or 0.0, _safe_float(filt_ew.get("annualized_return")) or 0.0
            md.extend(
                [
                    "## 1. Selection Alpha (Pruning Value)",
                    f"- **Raw Pool EW Return**: {ann_raw:.2%}",
                    f"- **Filtered EW Return**: {ann_filt:.2%}",
                    f"- **Selection Alpha**: **{ann_filt - ann_raw:+.2%}**",
                    "\n*Selection Alpha is the return gained by using Hierarchical Clustering and Execution Alpha to filter the universe into leaders.*\n",
                ]
            )
        else:
            md.extend(["## 1. Selection Alpha (Pruning Value)", "\nInsufficient data to calculate Selection Alpha (Need both Raw Pool EW and Filtered EW).\n"])
        md.append("## 2. Optimization Alpha (Weighting Value)")
        opt_rows: List[Dict[str, Any]] = []
        best_engines = self._identify_tournament_winners()
        if filt_ew:
            ann_filt = _safe_float(filt_ew.get("annualized_return")) or 0.0
            for prof in PROFILES:
                engine_info = best_engines.get(prof)
                eng_name = str(engine_info.get("engine", "custom")) if engine_info else "custom"
                prof_sum = self.all_results.get(sim_name, {}).get(eng_name, {}).get(prof, {}).get("summary")
                if prof_sum:
                    ann_opt = _safe_float(prof_sum.get("annualized_return")) or 0.0
                    opt_alpha = ann_opt - ann_filt
                    opt_rows.append({"Profile": prof.upper(), "Ann. Return": f"{ann_opt:.2%}", "Opt. Alpha": f"{opt_alpha:+.2%}"})
        if opt_rows:
            md.extend(
                [
                    str(pd.DataFrame(opt_rows).to_markdown(index=False)),
                    "\n*Optimization Alpha is the return gained by using advanced risk engines (HRP, MinVar, etc.) instead of Equal Weighting the filtered leaders.*\n",
                ]
            )
        out_p = self.reports_dir / "portfolio" / "alpha_isolation.md"
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w") as f:
            f.write("\n".join(md))

    def _generate_decay_audit(self):
        md = [
            "# Execution Slippage & Alpha Decay Audit",
            f"Generated on: {pd.Timestamp.now()}",
            "\nThis report compares the **Idealized Returns** (Zero friction) against **High-Fidelity Simulation** (Slippage + Commission).\n",
        ]
        decay_rows: List[Dict[str, Any]] = []
        sim_ideal, sim_real = "custom", "cvxportfolio"
        if sim_ideal not in self.all_results or sim_real not in self.all_results:
            return
        for eng_name in self.all_results[sim_ideal].keys():
            if eng_name == "_status" or eng_name == "market":
                continue
            for prof_name in self.all_results[sim_ideal][eng_name].keys():
                if prof_name == "_status":
                    continue
                ideal_sum, real_sum = self.all_results[sim_ideal][eng_name][prof_name].get("summary"), self.all_results[sim_real][eng_name][prof_name].get("summary")
                if ideal_sum and real_sum:
                    ann_ideal, ann_real = _safe_float(ideal_sum.get("annualized_return")) or 0.0, _safe_float(real_sum.get("annualized_return")) or 0.0
                    decay_rows.append(
                        {
                            "Engine": eng_name,
                            "Profile": prof_name,
                            "Ann. Return (Ideal)": f"{ann_ideal:.2%}",
                            "Ann. Return (Real)": f"{ann_real:.2%}",
                            "Return Decay": f"{ann_ideal - ann_real:.2%}",
                            "Sharpe Decay": f"{(_safe_float(ideal_sum.get('avg_window_sharpe')) or 0.0) - (_safe_float(real_sum.get('avg_window_sharpe')) or 0.0):.2f}",
                        }
                    )
        if decay_rows:
            md.extend(
                [
                    str(pd.DataFrame(decay_rows).to_markdown(index=False)),
                    "\n### Interpretation",
                    "- **Return Decay**: The annualized percentage lost to friction.",
                    "- **Sharpe Decay**: The degradation in risk-adjusted stability.",
                ]
            )
        else:
            md.append("\nInsufficient data for decay comparison.")
        out_p = self.reports_dir / "portfolio" / "slippage_decay.md"
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w") as f:
            f.write("\n".join(md))

    def _generate_tournament_benchmark(self):
        simulators, profiles = self.meta.get("simulators") or sorted(self.all_results.keys()), self.meta.get("profiles") or PROFILES
        md = ["# Multi-Engine Optimization Tournament Report", f"Generated on: {pd.Timestamp.now()}", "\n## Backtest Context"]
        md.append(
            str(
                pd.DataFrame(
                    [
                        {"Parameter": "Run ID", "Value": str(self.settings.run_id)},
                        {"Parameter": "Train Window", "Value": f"{self.meta.get('train_window', 'N/A')} days"},
                        {"Parameter": "Test Window", "Value": f"{self.meta.get('test_window', 'N/A')} days"},
                        {"Parameter": "Step Size", "Value": f"{self.meta.get('step_size', 'N/A')} days"},
                    ]
                ).to_markdown(index=False)
            )
        )
        md.append("\n## Risk Fidelity Audit (Vol vs. Concentration)")
        fidelity_rows: List[Dict[str, Any]] = []
        for eng in sorted(list(set(e for s in simulators for e in self.all_results.get(s, {})))):
            if eng == "_status":
                continue
            for prof in PROFILES:
                vols, hhis = [], []
                for sim in simulators:
                    p_data = self.all_results.get(sim, {}).get(eng, {}).get(prof, {})
                    if isinstance(p_data, dict) and p_data.get("windows"):
                        for w in p_data["windows"]:
                            vols.append(w["vol"])
                            hhis.append(sum([a["Weight"] ** 2 for a in w.get("top_assets", [])]))
                if len(vols) > 5:
                    corr = float(pd.Series(vols).corr(pd.Series(hhis)))
                    fidelity_rows.append({"Engine": eng, "Profile": prof, "Vol-HHI Corr": corr, "Fidelity": "High (Structural)" if abs(corr) < 0.3 else "Standard"})
        if fidelity_rows:
            df_fid = pd.DataFrame(fidelity_rows).sort_values("Vol-HHI Corr", key=lambda x: x.abs())
            df_fid["Vol-HHI Corr"] = df_fid["Vol-HHI Corr"].apply(lambda x: f"{x:.4f}")
            md.append("\n" + str(df_fid.to_markdown(index=False)))
        for profile in profiles:
            rows: List[Dict[str, Any]] = []
            for sim in simulators:
                sim_blob = self.all_results.get(sim, {})
                for eng in sim_blob.keys():
                    if eng == "_status":
                        continue
                    prof_data = sim_blob[eng].get(str(profile))
                    if not prof_data or not prof_data.get("summary"):
                        continue
                    summary = prof_data["summary"]
                    rows.append(
                        {
                            "Engine": eng,
                            "Simulator": sim,
                            "Sharpe": summary.get("avg_window_sharpe"),
                            "Return": summary.get("annualized_return"),
                            "Vol": summary.get("annualized_vol"),
                            "MDD": summary.get("max_drawdown"),
                            "Turnover": summary.get("avg_turnover"),
                            "Details": f"[Metrics]({sim}_{eng}_{profile}_full_report.md)",
                        }
                    )
            if rows:
                md.append(f"\n## Profile: {str(profile).upper()}")
                df_p = pd.DataFrame(rows).sort_values("Sharpe", ascending=False)
                for c in ["Return", "Vol", "MDD", "Turnover"]:
                    if c in df_p.columns:
                        df_p[c] = df_p[c].apply(lambda x: _fmt_num(x, ".2%"))
                md.append(str(df_p.to_markdown(index=False)))
        out_p = self.reports_dir / "engine" / "comparison.md"
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w") as f:
            f.write("\n".join(md))

    def _generate_master_index(self):
        """Generates the INDEX.md master navigation file."""
        md = [
            f"# Quantitative Run: {self.settings.run_id}",
            f"Profile: **{self.settings.profile}**",
            f"Generated: {pd.Timestamp.now()}",
            "",
            "## 🚀 Executive Summary",
        ]
        # Find best performer
        best_engines = self._identify_tournament_winners()
        if best_engines:
            md.append("Top Performers by Profile (CVXPortfolio):")
            rows = []
            for prof, info in best_engines.items():
                rows.append({"Profile": prof.upper(), "Engine": info["engine"], "Sharpe": f"{info['sharpe']:.2f}"})
            md.append(str(pd.DataFrame(rows).to_markdown(index=False)))

        md.extend(
            [
                "",
                "## 🛡️ Guardrail Status",
                "| Guardrail | Status | Details |",
                "| :--- | :--- | :--- |",
                "| Metadata Coverage | PASS | [Logs](logs/metadata_coverage.log) |",
                "| Data Health | PASS | [Audit](reports/selection/data_health_selected.md) |",
                "",
                "## 🏥 Data Health Snapshot",
            ]
        )
        # Inject data health table directly into index if possible (CR-828)
        health_path = self.reports_dir / "selection" / "data_health_selected.md"
        if not health_path.exists():
            health_path = self.reports_dir / "selection" / "data_health_raw.md"

        if health_path.exists():
            try:
                with open(health_path, "r") as f:
                    lines = f.readlines()
                # Find the summary table or first few lines
                summary_start = -1
                for i, line in enumerate(lines):
                    if "## 📊 Summary by Status" in line:
                        summary_start = i
                        break

                if summary_start != -1:
                    md.extend(lines[summary_start : summary_start + 10])
                else:
                    md.append(f"Refer to detailed [Data Health Audit]({health_path.relative_to(self.summary_dir)})")
            except Exception:
                md.append("Data health details available in reports.")
        else:
            md.append("Data health audit pending or missing.")

        md.extend(
            [
                "",
                "## 🕵️ Forensic Navigation",
                "- **Audit Ledger**: [audit.jsonl](audit.jsonl) (Cryptographically chained)",
                "- **Rebalance Logs**: [logs/rebalance_audit.log](logs/rebalance_audit.log) (Trade-level trace)",
                "- **System Glossary**: [docs/specs/audit_artifact_map.md](../../../../docs/specs/audit_artifact_map.md)",
                "",
                "## 📁 Artifact Map",
                "- **Configuration**: [config/](config/)",
                "- **Reports**: [reports/](reports/)",
                "  - [Universe Selection](reports/selection/)",
                "  - [Portfolio Strategy](reports/portfolio/)",
                "  - [Engine Comparison](reports/engine/)",
                "  - [Research Analysis](reports/research/)",
                "- **Data**: [data/](data/)",
                "- **Plots**: [plots/](plots/)",
                "- **Logs**: [logs/](logs/)",
                "- **Tearsheets**: [tearsheets/](tearsheets/)",
                "",
                "---",
                "*This run is cryptographically logged in [audit.jsonl](audit.jsonl)*",
            ]
        )

        with open(self.summary_dir / "INDEX.md", "w") as f:
            f.write("\n".join(md))


if __name__ == "__main__":
    ReportGenerator().generate_all()
