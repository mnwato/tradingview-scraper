import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from scripts.backtest_engine import BacktestEngine, persist_tournament_artifacts
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("grand_tournament")


# --- Helper Classes for Research Mode ---
class _TeeTextIO:
    def __init__(self, *streams):
        self._streams = [s for s in streams if s is not None]
        self.encoding = "utf-8"

    def write(self, data):
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        for s in self._streams:
            try:
                s.write(data)
            except Exception:
                pass
        return len(data)

    def flush(self):
        for s in self._streams:
            try:
                s.flush()
            except Exception:
                pass


def _parse_csv(val: Optional[str]) -> List[str]:
    if not val:
        return []
    return [s.strip() for s in val.split(",") if s.strip()]


# --- Production Mode Logic (Subprocess) ---
def run_production_pass(profile: str, selection_mode: str, rebalance_mode: Optional[str] = None, extra_args: List[str] = []) -> str:
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    cmd = ["uv", "run", "python", "-m", "scripts.run_production_pipeline", "--profile", profile, "--run-id", run_id]
    cmd.extend(extra_args)

    env = os.environ.copy()
    env["TV_FEATURES__SELECTION_MODE"] = selection_mode
    if rebalance_mode:
        env["TV_FEATURES__FEAT_REBALANCE_MODE"] = rebalance_mode

    dim_str = f"Selection={selection_mode}"
    if rebalance_mode:
        dim_str += f", Rebalance={rebalance_mode}"

    logger.info(f"🏆 [PROD PASS] Starting: {dim_str} | Run ID = {run_id}")
    try:
        subprocess.check_call(cmd, env=env)
        return run_id
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Pass Failed: {e}")
        return ""


# --- Research Mode Logic (Internal Loop) ---
def run_research_sweep(
    profile: str,
    selection_modes: List[str],
    rebalance_modes: List[str],
    train_window: Optional[int] = None,
    test_window: Optional[int] = None,
    step_size: Optional[int] = None,
    cluster_cap: Optional[float] = None,
    engines: Optional[List[str]] = None,
    profiles: Optional[List[str]] = None,
    simulators: Optional[List[str]] = None,
) -> str:
    """Runs a matrix of research backtests in-process."""
    # Ensure profile is set in environment so get_settings() can load it (CR-821)
    if profile:
        os.environ["TV_PROFILE"] = profile

    # Clear cache to ensure fresh settings for the requested profile
    get_settings.cache_clear()
    settings = get_settings()

    run_id = settings.run_id
    run_dir = settings.prepare_summaries_run_dir()

    log_path = settings.run_logs_dir / "grand_tournament_research.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    all_results: dict = {}
    orig_reb = settings.features.feat_rebalance_mode
    orig_sel = settings.features.selection_mode
    orig_dynamic = settings.dynamic_universe
    settings.dynamic_universe = True

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    logger.info(f"🧪 [RESEARCH MODE] Starting sweep in {run_dir}")

    with open(log_path, "a", encoding="utf-8", buffering=1) as log_f:
        log_f.write(f"\n--- grand_tournament research start (run_id={settings.run_id}) ---\n")
        sys.stdout = _TeeTextIO(original_stdout, log_f)
        sys.stderr = _TeeTextIO(original_stderr, log_f)
        try:
            for reb_mode in rebalance_modes:
                all_results[reb_mode] = {}
                settings.features.feat_rebalance_mode = reb_mode
                os.environ["TV_FEATURES__FEAT_REBALANCE_MODE"] = reb_mode

                for sel_mode in selection_modes:
                    logger.info(f"\n🔬 RESEARCH CELL: Rebalance={reb_mode}, Selection={sel_mode}")
                    settings.features.selection_mode = sel_mode
                    os.environ["TV_FEATURES__SELECTION_MODE"] = sel_mode

                    bt = BacktestEngine()
                    cap = float(cluster_cap) if cluster_cap is not None else float(settings.cluster_cap)

                    res = bt.run_tournament(
                        train_window=train_window or int(settings.train_window),
                        test_window=test_window or int(settings.test_window),
                        step_size=step_size or int(settings.step_size),
                        engines=engines,
                        profiles=profiles,
                        simulators=simulators,
                        cluster_cap=cap,
                        selection_mode=sel_mode,
                    )

                    cell_data_dir = settings.run_data_dir / "grand_4d" / reb_mode / sel_mode
                    persist_tournament_artifacts(res, cell_data_dir)
                    all_results[reb_mode][sel_mode] = res["results"]

            # Final Save
            output = {
                "meta": {
                    "run_id": settings.run_id,
                    "profile": profile,
                    "dimensions": {
                        "rebalance": rebalance_modes,
                        "selection": selection_modes,
                    },
                },
                "rebalance_audit_results": all_results,
            }
            out_path = run_dir / "grand_4d_tournament_results.json"
            with open(out_path, "w") as f:
                json.dump(output, f, indent=2)

            settings.promote_summaries_latest()
            return settings.run_id
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            settings.features.feat_rebalance_mode = orig_reb
            settings.features.selection_mode = orig_sel
            settings.dynamic_universe = orig_dynamic


# --- CLI Entry ---
def main():
    parser = argparse.ArgumentParser(description="Grand Tournament: Unified Production & Research Orchestrator")
    parser.add_argument("--mode", choices=["production", "research"], default="production", help="Run mode")
    parser.add_argument("--profile", default="institutional_etf", help="Configuration profile")
    parser.add_argument("--selection-modes", default="v3.2,v2.1", help="Comma-separated selection modes")
    parser.add_argument("--rebalance-modes", default="window", help="Comma-separated rebalance modes")

    # Research Overrides
    parser.add_argument("--train-window", type=int)
    parser.add_argument("--test-window", type=int)
    parser.add_argument("--step-size", type=int)
    parser.add_argument("--cluster-cap", type=float)
    parser.add_argument("--lookback", type=int)
    parser.add_argument("--engines", help="Comma-separated list of engines")
    parser.add_argument("--profiles", help="Comma-separated list of profiles")
    parser.add_argument("--simulators", help="Comma-separated list of simulators")

    args, unknown = parser.parse_known_args()
    sel_modes = _parse_csv(args.selection_modes)
    reb_modes = _parse_csv(args.rebalance_modes)
    engines = _parse_csv(args.engines)
    profiles = _parse_csv(args.profiles)
    simulators = _parse_csv(args.simulators)

    console = Console()

    console.print("\n[bold gold1]🏟️ Grand Tournament Orchestrator[/]")
    console.print(f"[dim]Profile:[/] {args.profile} | [dim]Mode:[/] {args.mode.upper()}")

    if args.mode == "production":
        run_results = []
        extra = unknown
        if args.lookback:
            extra.extend(["--lookback", str(args.lookback)])

        for reb in reb_modes:
            for sel in sel_modes:
                run_id = run_production_pass(args.profile, sel, reb, extra)
                if run_id:
                    run_results.append({"sel": sel, "reb": reb, "id": run_id})

        if run_results:
            table = Table(title="Grand Tournament Summary")
            table.add_column("Selection")
            table.add_column("Rebalance")
            table.add_column("Run ID")
            for r in run_results:
                table.add_row(r["sel"], r["reb"], r["id"])
            console.print(table)
    else:
        # Research Mode
        run_id = run_research_sweep(
            profile=args.profile,
            selection_modes=sel_modes,
            rebalance_modes=reb_modes,
            train_window=args.train_window,
            test_window=args.test_window,
            step_size=args.step_size,
            cluster_cap=args.cluster_cap,
            engines=engines,
            profiles=profiles,
            simulators=simulators,
        )
        console.print(f"[bold green]✅ Research Sweep Complete:[/] {run_id}")


if __name__ == "__main__":
    main()
