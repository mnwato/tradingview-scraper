import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

# Add the project root to the path so we can import internal modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingview_scraper.settings import get_settings
from tradingview_scraper.telemetry.logging import setup_logging
from tradingview_scraper.telemetry.tracing import trace_span
from tradingview_scraper.utils.audit import AuditLedger

setup_logging()
logger = logging.getLogger("production_pipeline")


class ProductionPipeline:
    def __init__(self, profile: str = "production", manifest: str = "configs/manifest.json", run_id: Optional[str] = None, skip_analysis: bool = False, skip_validation: bool = False):
        self.profile = profile
        self.manifest_path = Path(manifest)
        self.run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.skip_analysis = skip_analysis
        self.skip_validation = skip_validation
        self.console = Console()

        # Initialize environment BEFORE loading settings
        os.environ["TV_PROFILE"] = profile
        os.environ["TV_MANIFEST_PATH"] = str(self.manifest_path)
        os.environ["TV_RUN_ID"] = self.run_id
        os.environ["TV_EXPORT_RUN_ID"] = self.run_id

        # Promote common override env vars to TV_ prefixed settings vars
        self._promote_env_overrides()

        # CR-FIX: Ensure settings are reloaded with the new environment variables
        # This is critical for Ray/Worker reuse scenarios.
        get_settings.cache_clear()
        self.settings = get_settings()

        # Override specific settings instance fields if needed (though env vars should drive this)
        self.settings.run_id = self.run_id
        self.settings.profile = profile
        self.settings.manifest_path = self.manifest_path

        # Setup Audit Ledger
        self.run_dir = self.settings.prepare_summaries_run_dir()
        self.log_dir = self.run_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.ledger = None
        if self.settings.features.feat_audit_ledger:
            self.ledger = AuditLedger(self.run_dir)

            # Record Genesis
            manifest_hash = self._get_file_hash(self.manifest_path)
            self.ledger.record_genesis(self.run_id, self.profile, manifest_hash)

    def _promote_env_overrides(self) -> None:
        """Map non-prefixed override env vars to TV_ prefixed settings vars."""
        overrides = {
            "LOOKBACK": "TV_LOOKBACK_DAYS",
            "PORTFOLIO_LOOKBACK_DAYS": "TV_PORTFOLIO_LOOKBACK_DAYS",
            "BACKTEST_TRAIN": "TV_TRAIN_WINDOW",
            "BACKTEST_TEST": "TV_TEST_WINDOW",
            "BACKTEST_STEP": "TV_STEP_SIZE",
            "BACKTEST_SIMULATOR": "TV_BACKTEST_SIMULATOR",
            "BACKTEST_SIMULATORS": "TV_BACKTEST_SIMULATORS",
            "RAW_POOL_UNIVERSE": "TV_RAW_POOL_UNIVERSE",
        }
        for src, dst in overrides.items():
            val = os.getenv(src)
            if val and not os.getenv(dst):
                os.environ[dst] = val

    def _get_file_hash(self, path: Path) -> str:
        if not path.exists():
            return "0" * 64
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def run_directional_sign_test_gate(self, *, require_optimizer_normalization: bool, output_name: str) -> None:
        from scripts.audit_directional_sign_test import run_sign_test_for_run_dir, write_findings_json

        findings = run_sign_test_for_run_dir(
            self.run_dir,
            atol=0.0,
            require_optimizer_normalization=bool(require_optimizer_normalization),
            risk_profile="hrp",
        )
        out_path = self.run_dir / "data" / output_name
        write_findings_json(findings, out_path)

        if any(f.level == "ERROR" for f in findings):
            raise RuntimeError(f"Directional Sign Test failed ({out_path.name})")

    @trace_span("pipeline.run_step")
    def run_step(
        self,
        name: str,
        command: List[str],
        step_num: int = 0,
        env: Optional[Dict[str, str]] = None,
        validate_fn: Optional[Callable[[], Any]] = None,
        progress: Optional[Progress] = None,
        task_id: Optional[Any] = None,
    ):
        if progress:
            progress.console.print(f"[bold blue]>>> Step {step_num if step_num else ''}: {name}[/]")
        else:
            logger.info(f">>> Step {step_num if step_num else ''}: {name}")

        # Setup step-specific log file
        safe_name = name.lower().replace(" ", "_").replace("&", "and")
        log_file_path = self.log_dir / f"{step_num:02d}_{safe_name}.log" if step_num else self.log_dir / f"{safe_name}.log"

        # Log Intent
        if self.ledger:
            self.ledger.record_intent(step=name.lower(), params={"cmd": " ".join(command), "log_file": str(log_file_path)}, input_hashes={})

        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        try:
            # Use Popen to capture output incrementally
            process = subprocess.Popen(
                command,
                env=full_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout for simple logging
                text=True,
                bufsize=1,  # Line buffered
            )

            stdout_lines = []

            with open(log_file_path, "w", encoding="utf-8") as log_file:
                # Read stdout incrementally
                if process.stdout:
                    for line in iter(process.stdout.readline, ""):
                        # Write to log file
                        log_file.write(line)
                        log_file.flush()

                        clean_line = line.strip()
                        if clean_line:
                            stdout_lines.append(clean_line)
                            if progress and task_id is not None:
                                # Update progress bar with current activity
                                display_line = clean_line[:80] + "..." if len(clean_line) > 80 else clean_line
                                progress.update(task_id, description=f"[cyan]{name}[/] [dim]({display_line})[/]")

                                # Optional: Parse progress markers like [5/100] or 5% or Processing 5/100
                                import re

                                match = re.search(r"(\d+)/(\d+)", clean_line)
                                if match:
                                    current, total = map(int, match.groups())
                                    progress.update(task_id, completed=current, total=total)
                                elif "%" in clean_line:
                                    pct_match = re.search(r"(\d+)%", clean_line)
                                    if pct_match:
                                        progress.update(task_id, completed=int(pct_match.group(1)), total=100)

            process.wait()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command, output="\n".join(stdout_lines))

            # Post-run validation and metric extraction
            metrics: Dict[str, Any] = {"stdout_len": len("\n".join(stdout_lines)), "log_file": str(log_file_path)}
            output_hashes: Dict[str, str] = {}
            if validate_fn:
                try:
                    val_res = validate_fn()
                    if isinstance(val_res, dict):
                        metrics.update(val_res.get("metrics", {}))
                        output_hashes.update(val_res.get("hashes", {}))
                except Exception as ve:
                    if progress:
                        progress.console.print(f"[yellow]Validation hook failed for '{name}': {ve}[/]")
                    else:
                        logger.warning(f"Validation hook failed for '{name}': {ve}")

            # Log Outcome
            if self.ledger:
                self.ledger.record_outcome(step=name.lower(), status="success", output_hashes=output_hashes, metrics=metrics)

            if progress and task_id is not None:
                progress.update(task_id, description=f"[green]{name}[/] [bold green]COMPLETE[/]", completed=1)

            return True
        except Exception as e:
            if progress:
                progress.console.print(f"[bold red]Step '{name}' failed: {e}[/]")
            else:
                logger.error(f"Step '{name}' failed: {e}")

            if self.ledger:
                err_msg = str(e)[-500:]
                self.ledger.record_outcome(step=name.lower(), status="failure", output_hashes={}, metrics={"error": err_msg})
            return False

    def validate_discovery(self) -> Dict[str, Any]:
        """Discovery Gate: Verify export directory contains results."""
        settings = get_settings()
        export_dir = settings.export_dir / self.run_id
        if not export_dir.exists():
            # Try finding the latest directory if ID mismatch (discovery scripts sometimes use their own ts)
            dirs = sorted(settings.export_dir.glob("*"), key=os.path.getmtime, reverse=True)
            if dirs:
                export_dir = dirs[0]

        files = list(export_dir.glob("*.json"))
        return {"metrics": {"n_discovery_files": len(files)}}

    def validate_selection(self) -> Dict[str, Any]:
        """Selection Gate: Ensure enough symbols survived."""
        # CR-831: Workspace Isolation
        path = self.run_dir / "data" / "portfolio_candidates.json"
        if not path.exists():
            # Fallback to shared location for legacy support
            path = self.settings.lakehouse_dir / "portfolio_candidates.json"

        if not path.exists():
            return {}
        with open(path, "r") as f:
            data = json.load(f)
        return {"metrics": {"n_selected_symbols": len(data)}}

    def validate_health(self) -> Dict[str, Any]:
        """Health Gate: Check for gaps and stale assets.

        Returns metrics dict with health_gate status and counts.
        If STALE or DEGRADED assets found, returns trigger_recovery=True.
        """
        # CR-831: Search in both run-specific and legacy locations
        report_path = self.run_dir / "reports" / "selection" / "data_health_selected.md"
        if not report_path.exists():
            report_path = self.run_dir / "data_health_selected.md"

        if not report_path.exists():
            return {"metrics": {"health_gate": "report_missing"}}

        # Grep for critical failures in the report
        try:
            with open(report_path, "r") as f:
                content = f.read()

            missing = 0
            stale = 0
            degraded = 0

            for line in content.split("\n"):
                if "MISSING" in line:
                    missing += 1
                if "STALE" in line:
                    stale += 1
                if "DEGRADED" in line:
                    degraded += 1

            metrics = {
                "health_gate": "checked",
                "n_missing": missing,
                "n_stale": stale,
                "n_degraded": degraded,
            }

            # CRITICAL FIX: Trigger auto-recovery if stale or degraded data found
            # Issue: https://github.com/anomalyco/tradingview-scraper/issues/XXX
            # Audit: docs/audit/crypto_production_funnel_audit_20260112.md
            if stale > 0 or degraded > 0:
                metrics["trigger_recovery"] = True
                metrics["recovery_reason"] = []
                if stale > 0:
                    metrics["recovery_reason"].append(f"{stale} STALE assets")
                if degraded > 0:
                    metrics["recovery_reason"].append(f"{degraded} DEGRADED assets")

            return {"metrics": metrics}
        except Exception as e:
            return {"metrics": {"health_gate": f"error: {str(e)}"}}

    def validate_optimization(self) -> Dict[str, Any]:
        """Optimization Gate: Verify all profiles were generated."""
        # CR-831: Workspace Isolation
        path = self.run_dir / "data" / "portfolio_optimized_v2.json"
        if not path.exists():
            # Fallback to shared location for legacy support
            path = self.settings.lakehouse_dir / "portfolio_optimized_v2.json"

        if not path.exists():
            return {}
        try:
            # Archival: Ensure the optimized portfolio is persisted in the run dir metadata
            import shutil

            archive_path = self.run_dir / "data" / "metadata" / "portfolio_optimized_v2.json"
            if path != archive_path:
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, archive_path)

            with open(path, "r") as f:
                data = json.load(f)
            profiles = list(data.get("profiles", {}).keys())
            return {"metrics": {"optimized_profiles": profiles}}
        except Exception as e:
            logger.warning(f"Optimization archival failed: {e}")
            return {}

    def snapshot_resolved_manifest(self):
        """Generates a fully resolved manifest snapshot for replayability."""
        import hashlib
        import subprocess

        settings = get_settings()
        resolved = settings.model_dump(exclude={"summaries_dir"})

        # Add Replay Context
        resolved["replay_context"] = {"run_id": self.run_id, "timestamp": datetime.now().isoformat(), "git_commit": "unknown", "manifest_source": str(self.manifest_path), "foundation_hashes": {}}

        # Hash Foundation Files (Index lists)
        # Use settings-derived paths for index files (Phase 540)
        index_dir = self.settings.data_dir / "index"
        foundation_files = ["sp500_symbols.txt", "nasdaq100_symbols.txt", "dw30_symbols.txt"]
        for f_name in foundation_files:
            p = index_dir / f_name
            if p.exists():
                sha = hashlib.sha256(p.read_bytes()).hexdigest()
                resolved["replay_context"]["foundation_hashes"][str(p)] = sha

        try:
            resolved["replay_context"]["git_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.STDOUT).decode().strip()
        except Exception:
            pass

        snapshot_path = self.settings.run_config_dir / "resolved_manifest.json"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        with open(snapshot_path, "w") as f:
            json.dump(resolved, f, indent=2, default=str)

        self.console.print(f"[dim]Snapshot:[/] [green]✓[/] {snapshot_path.name}")

    def execute(self, start_step: int = 1):
        from tradingview_scraper.telemetry.tracing import get_tracer

        tracer = get_tracer()
        with tracer.start_as_current_span(
            f"pipeline:{self.profile}",
            attributes={"profile": self.profile, "run_id": self.run_id, "type": "production"},
        ):
            self._execute_impl(start_step)

    def _execute_impl(self, start_step: int = 1):
        from tradingview_scraper.orchestration.sdk import QuantSDK

        self.console.print("\n[bold cyan]🚀 Starting Production Pipeline[/]")
        self.console.print(f"[dim]Profile:[/] {self.profile} | [dim]Run ID:[/] {self.run_id} | [dim]Start Step:[/] {start_step}\n")

        # L1 Ingestion Gate: Foundation Validation
        if not QuantSDK.validate_foundation():
            self.console.print("[bold red]Foundation Gate FAILED. Aborting.[/]")
            raise RuntimeError("Foundation Gate failed")

        # CR-855: Lakehouse Immutability (Snapshot)
        if os.getenv("TV_STRICT_ISOLATION") == "1":
            QuantSDK.create_snapshot(self.run_id)

        # Pillar Verification (Crypto Only)
        if self.profile == "crypto_production":
            self.console.print("[bold yellow]Production Pillars Analysis (Forensic Standards):[/]")
            self.console.print(f"  - [cyan]Regime Alignment:[/] step_size={self.settings.step_size}d (Target: 20d)")
            self.console.print(f"  - [cyan]Tail-Risk Mitigation:[/] test_window={self.settings.test_window}d (Target: 40d)")
            self.console.print(f"  - [cyan]Alpha Capture:[/] selection_mode={self.settings.features.selection_mode} (Target: v3.2)")
            self.console.print("")

        lightweight_lookback = os.getenv("LOOKBACK") or os.getenv("TV_LOOKBACK_DAYS") or "60"
        lightweight_batch = os.getenv("BATCH") or "5"
        high_integrity_lookback = (
            os.getenv("PORTFOLIO_LOOKBACK_DAYS")
            or os.getenv("TV_PORTFOLIO_LOOKBACK_DAYS")
            or os.getenv("LOOKBACK")
            or os.getenv("TV_LOOKBACK_DAYS")
            or str(self.settings.resolve_portfolio_lookback_days())
        )

        make_base = ["make", f"PROFILE={self.profile}", f"MANIFEST={self.manifest_path}"]

        # CRITICAL FIX: Production profiles MUST enforce STRICT_HEALTH=1 (no override allowed)
        # Issue: https://github.com/anomalyco/tradingview-scraper/issues/XXX
        # Audit: docs/audit/crypto_production_funnel_audit_20260112.md
        production_profiles = ["production", "crypto_production", "production_2026_q1", "institutional_etf"]

        strict_health_arg = "STRICT_HEALTH=1"
        if self.profile in production_profiles:
            # Production profiles: ALWAYS enforce STRICT_HEALTH=1
            strict_health_arg = "STRICT_HEALTH=1"
            if os.getenv("TV_STRICT_HEALTH") == "0" or os.getenv("STRICT_HEALTH") == "0":
                self.console.print(
                    f"[bold yellow]WARNING:[/] Environment override STRICT_HEALTH=0 detected. "
                    f"Profile '{self.profile}' is a production profile and REQUIRES STRICT_HEALTH=1. "
                    f"Ignoring override and enforcing STRICT_HEALTH=1."
                )
        else:
            # Development/experimental profiles: Allow override for fast iteration
            if os.getenv("TV_STRICT_HEALTH") == "0" or os.getenv("STRICT_HEALTH") == "0":
                strict_health_arg = "STRICT_HEALTH=0"

        if self.profile.startswith("meta_"):
            # Meta-Portfolio Pipeline (Sleeve Aggregation)
            # --------------------------------------------
            # 1. Build Meta-Returns (Aggregate Sleeves)
            # 2. Optimize Meta-Allocation (Risk Parity across Sleeves)
            # 3. Flatten Weights (Meta -> Physical)
            # 4. Generate Meta-Report

            target_risk_profiles = "min_variance,hrp,max_sharpe,equal_weight,barbell"

            # Step 4: Meta Construction (Replaces Aggregation/Prep)
            meta_steps = [
                ("Cleanup", [*make_base, "clean-run"], None),
                ("Environment Check", [*make_base, "env-check"], None),
                (
                    "Meta Construction",
                    [
                        "uv",
                        "run",
                        "scripts/build_meta_returns.py",
                        f"--profile={self.profile}",
                        f"--output={self.run_dir}/data/meta_returns.pkl",
                        f"--profiles={target_risk_profiles}",
                    ],
                    None,
                ),
                (
                    "Meta Optimization",
                    [
                        "uv",
                        "run",
                        "scripts/optimize_meta_portfolio.py",
                        f"--returns={self.run_dir}/data/meta_returns.pkl",
                        f"--output={self.run_dir}/data/meta_optimized.json",
                    ],
                    None,  # Optimization loops through all found meta_returns_*.pkl
                ),
            ]

            # Flattening steps for each risk profile (for validation/reporting)
            # For simplicity in the pipeline visual, we flatten the primary 'hrp' or 'min_variance'
            # but ideally we'd flatten all. Let's flatten the manifest default or HRP.

            # We will use a wrapper script or just run flatten for HRP as the "Production" output
            # But we want reporting for all.
            # Let's add a "Meta Reporting" step that handles all.

            meta_steps.append(("Meta Reporting", ["uv", "run", "scripts/generate_meta_report.py", f"--meta-dir={self.run_dir}/data", f"--output={self.run_dir}/reports/portfolio/report.md"], None))

            # Gist Sync is optional
            if os.getenv("GIST_SYNC") == "1":
                meta_steps.append(("Gist Sync", [*make_base, "report-sync"], None))

            all_steps = meta_steps

        else:
            # Standard Asset Pipeline (Read-Only Alpha Cycle)
            all_steps: List[Tuple[str, List[str], Any]] = [
                ("Cleanup", [*make_base, "clean-run"], None),
                ("Environment Check", [*make_base, "env-check"], None),
                # Discovery and Data Ingestion are removed from Alpha Cycle.
                # They must run beforehand via 'make flow-data'.
                ("Aggregation", [*make_base, "data-prep-raw"], None),
                ("Natural Selection", [*make_base, "port-select"], self.validate_selection),
                (
                    "Enrichment",
                    [
                        "uv",
                        "run",
                        "scripts/enrich_candidates_metadata.py",
                        f"--candidates={self.run_dir}/data/portfolio_candidates.json",
                        f"--returns={self.run_dir}/data/returns_matrix.parquet",
                    ],
                    None,
                ),
                ("Strategy Synthesis", ["uv", "run", "scripts/synthesize_strategy_matrix.py"], None),
                ("Health Audit", [*make_base, "data-audit", strict_health_arg], self.validate_health),
                ("Persistence Analysis", [*make_base, "research-persistence"], None),
                # SPLIT: Critical Pre-Opt Analysis
                ("Pre-Opt Analysis", [*make_base, "port-pre-opt", f"RETURNS_MATRIX={self.run_dir}/data/synthetic_returns.parquet"], None),
                ("Optimization", [*make_base, "port-optimize", f"RETURNS_MATRIX={self.run_dir}/data/synthetic_returns.parquet"], self.validate_optimization),
                (
                    "Weight Flattening",
                    [
                        "uv",
                        "run",
                        "scripts/flatten_strategy_weights.py",
                        f"OPTIMIZED_FILE={self.run_dir}/data/portfolio_optimized_v2.json",
                        f"FLATTENED_FILE={self.run_dir}/data/portfolio_flattened.json",
                        f"CANDIDATES_SELECTED={self.run_dir}/data/portfolio_candidates.json",
                    ],
                    None,
                ),
                ("Reporting", [*make_base, "port-report", f"OPTIMIZED_FILE={self.run_dir}/data/portfolio_flattened.json"], None),
            ]

            # Optional Validation Step
            if not self.skip_validation:
                all_steps.append(
                    ("Validation", [*make_base, "port-test", f"OPTIMIZED_FILE={self.run_dir}/data/portfolio_flattened.json", f"RETURNS_MATRIX={self.run_dir}/data/returns_matrix.parquet"], None)
                )

            # Optional Deep Analysis Step
            if not self.skip_analysis:
                all_steps.append(("Post-Analysis", [*make_base, "port-post-analysis", f"RETURNS_MATRIX={self.run_dir}/data/synthetic_returns.parquet"], None))

            if os.getenv("GIST_SYNC") == "1":
                all_steps.append(("Gist Sync", [*make_base, "report-sync"], None))

        steps_to_run = all_steps[start_step - 1 :]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            expand=True,
        ) as progress:
            pipeline_task = progress.add_task("[bold green]Pipeline Progress", total=len(all_steps))
            progress.advance(pipeline_task, start_step - 1)

            for idx, (name, cmd, val_fn) in enumerate(steps_to_run):
                # Calculate the absolute step index (start_step + current relative index)
                absolute_step = start_step + idx

                step_task = progress.add_task(f"[cyan]{name}", total=None)  # indeterminate by default
                success = self.run_step(name, cmd, step_num=absolute_step, validate_fn=val_fn, progress=progress, task_id=step_task)

                # Snapshot the manifest after Cleanup (Step 1)
                if absolute_step == 1 and success:
                    self.snapshot_resolved_manifest()

                # Directional Sign Test Gate (Atomic)
                # - Pre-opt: proves inversion correctness at the sleeve boundary (post-synthesis).
                # - Post-opt: adds optimizer normalization sanity once weights exist.
                if self.settings.features.feat_directional_sign_test_gate_atomic and success:
                    if name == "Strategy Synthesis":
                        progress.console.print("[bold blue]>>> Gate: Directional Sign Test (Pre-Opt)[/]")
                        self.run_directional_sign_test_gate(require_optimizer_normalization=False, output_name="directional_sign_test_pre_opt.json")
                    if name == "Optimization":
                        progress.console.print("[bold blue]>>> Gate: Directional Sign Test (Post-Opt)[/]")
                        self.run_directional_sign_test_gate(require_optimizer_normalization=True, output_name="directional_sign_test.json")
                    if name == "Reporting":
                        progress.console.print("[bold blue]>>> Gate: Atomic Validation (Artifacts + Sign Test)[/]")
                        from scripts.validate_atomic_run import validate_atomic_run

                        rc = validate_atomic_run(run_id=self.run_id, profile=self.profile, manifest_path=self.manifest_path)
                        if int(rc) != 0:
                            raise RuntimeError("Atomic validation failed")

                # Integrated Recovery is REMOVED to enforce Strict Pipeline Separation
                # If Health Audit fails, the pipeline fails. Recovery must be done via 'flow-data'.
                if name == "Health Audit" and not success:
                    progress.console.print("[bold red]Health Audit failed. Aborting pipeline.[/]\n[yellow]Run 'make data-repair' or 'make flow-data' to fix the Lakehouse.[/]")
                    raise RuntimeError("Health Audit failed")

                if not success:
                    progress.console.print(f"[bold red]Pipeline aborted at step '{name}' due to failure.[/]")
                    raise RuntimeError(f"Pipeline failed at step: {name}")

                progress.advance(pipeline_task)

        self.console.print("\n[bold green]✅ Pipeline completed successfully.[/]\n")


if __name__ == "__main__":
    # Suppress internal noise during progress-bar execution
    logging.getLogger("tradingview_scraper").setLevel(logging.WARNING)
    logging.getLogger("backtest_simulators").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="Institutional Production Pipeline")
    parser.add_argument("--profile", default="production", help="Workflow profile to use")
    parser.add_argument("--manifest", default="configs/manifest.json", help="Path to manifest file")
    parser.add_argument("--start-step", type=int, default=1, help="Step number to start from (1-14)")
    parser.add_argument("--run-id", help="Explicit run ID to use (for resuming)")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip heavy post-optimization analysis (Visuals)")
    parser.add_argument("--skip-validation", action="store_true", help="Skip validation backtests")
    parser.add_argument("--sdk", action="store_true", help="Use the new SDK-driven DAG orchestrator")
    args = parser.parse_args()

    if args.sdk:
        from tradingview_scraper.orchestration.sdk import QuantSDK

        QuantSDK.run_pipeline("alpha.full", profile=args.profile, run_id=args.run_id)
        sys.exit(0)

    pipeline = ProductionPipeline(profile=args.profile, manifest=args.manifest, run_id=args.run_id, skip_analysis=args.skip_analysis, skip_validation=args.skip_validation)
    pipeline.execute(start_step=args.start_step)
