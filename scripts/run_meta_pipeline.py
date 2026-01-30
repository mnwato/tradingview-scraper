import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

sys.path.append(os.getcwd())
from scripts.audit_directional_sign_test import run_sign_test_for_meta_profile, write_findings_json
from tradingview_scraper.orchestration.compute import RayComputeEngine
from tradingview_scraper.pipelines.meta.base import MetaContext
from tradingview_scraper.settings import get_settings
from tradingview_scraper.telemetry.logging import setup_logging
from tradingview_scraper.telemetry.tracing import trace_span

setup_logging()
logger = logging.getLogger("run_meta_pipeline")


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@trace_span("run_meta_pipeline")
def run_meta_pipeline(
    meta_profile: str,
    profiles: Optional[List[str]] = None,
    execute_sleeves: bool = False,
    use_native_ray: bool = False,
    run_id: Optional[str] = None,
    manifest: str = "configs/manifest.json",
):
    """
    Streamlined Meta-Portfolio Pipeline (Alpha Flow).
    Executes Build -> Optimize -> Flatten -> Report in one go.
    Supports fractal recursion via build_meta_returns.
    """
    # Meta pipelines treat the meta_profile as the active profile so per-profile feature flags apply.
    os.environ["TV_PROFILE"] = meta_profile
    os.environ["TV_MANIFEST_PATH"] = str(manifest)

    # CR-851: Meta-Run Isolation (Phase 242)
    import datetime

    if not run_id:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        run_id = f"{meta_profile}_{ts}"

    # CR-FIX: Ensure global context for internal modules (AuditLedger, Settings)
    os.environ["TV_RUN_ID"] = run_id
    get_settings.cache_clear()
    settings = get_settings()
    target_profiles = profiles or settings.profiles.split(",")

    # Establish Isolated Workspace
    run_dir = (settings.summaries_runs_dir / run_id).resolve()

    run_data_dir = run_dir / "data"
    run_data_dir.mkdir(parents=True, exist_ok=True)

    # Initialize MetaContext
    context = MetaContext(run_id=run_id, meta_profile=meta_profile, sleeve_profiles=target_profiles)

    logger.info(f"🚀 Starting Meta-Portfolio Pipeline: {meta_profile}")
    logger.info(f"📂 Workspace: {run_dir}")
    logger.info(f"📂 Data Dir: {run_data_dir}")

    from tradingview_scraper.orchestration.sdk import QuantSDK

    # CR-855: Lakehouse Immutability (Snapshot)
    if os.getenv("TV_STRICT_ISOLATION") == "1":
        QuantSDK.create_snapshot(run_id)

    # CR-850: Parallel Sleeve Execution (Phase 223/345)
    if execute_sleeves:
        logger.info(">>> STAGE 0: Parallel Sleeve Production (Ray Compute Engine)")

        # Load manifest to find sleeves that need execution
        manifest_data = _load_manifest(settings.manifest_path)

        meta_cfg = manifest_data.get("profiles", {}).get(meta_profile)
        if meta_cfg:
            sleeves_to_run = []
            for s in meta_cfg.get("sleeves", []):
                # If run_id is a placeholder or missing, we execute it
                if "baseline" in str(s.get("run_id", "")) or not s.get("run_id"):
                    import datetime

                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_run_id = f"ray_{s['profile']}_{ts}"
                    s["run_id"] = new_run_id
                    sleeves_to_run.append({"profile": s["profile"], "run_id": new_run_id})

            if sleeves_to_run:
                engine = RayComputeEngine()
                results = engine.execute_sleeves(sleeves_to_run)

                failed_sleeves = []
                for res in results:
                    if res["status"] == "success":
                        logger.info(f"✅ Sleeve {res['profile']} complete ({res['duration']:.1f}s)")
                    else:
                        logger.error(f"❌ Sleeve {res['profile']} FAILED: {res.get('error', 'Unknown Error')}")
                        failed_sleeves.append(f"{res['profile']} ({res.get('error', 'Unknown Error')})")

                if failed_sleeves:
                    error_msg = f"Sleeve production failed for: {', '.join(failed_sleeves)}"
                    logger.critical(f"🛑 {error_msg}. Aborting meta-pipeline.")
                    raise RuntimeError(error_msg)

                logger.info("Parallel execution phase complete.")

    # Stage 0.5: Directional Correction Audit Gate (Sign Test)
    if settings.features.feat_directional_sign_test_gate:
        logger.info(">>> STAGE 0.5: Directional Correction Gate (Sign Test)")
        risk_profile = "hrp" if "hrp" in [p.strip() for p in target_profiles] else str(target_profiles[0]).strip()
        findings = run_sign_test_for_meta_profile(meta_profile, manifest_path=settings.manifest_path, risk_profile=risk_profile, atol=0.0)
        write_findings_json(findings, run_data_dir / "directional_sign_test.json")
        if any(f.level == "ERROR" for f in findings):
            logger.critical("🛑 Directional Sign Test FAILED. Aborting meta-pipeline.")
            raise RuntimeError("Directional Sign Test failed")
        logger.info("✅ Directional Sign Test PASS")

    # 1. Build Returns (Recursive)
    logger.info(">>> STAGE 1: Aggregating Sleeve Returns")
    # Output to isolated run directory
    QuantSDK.run_stage(
        "meta.aggregation",
        meta_profile=meta_profile,
        output_path=str(run_data_dir / "meta_returns.pkl"),
        profiles=target_profiles,
        manifest_path=settings.manifest_path,
        base_dir=run_data_dir,
    )

    # 2. Optimize
    logger.info(">>> STAGE 2: Meta-Optimization")
    # optimize_meta infers base_dir from input path (run_data_dir / "meta_returns.pkl")
    QuantSDK.run_stage(
        "risk.optimize_meta",
        returns_path=str(run_data_dir / "meta_returns.pkl"),
        output_path=str(run_data_dir / "meta_optimized.json"),
        meta_profile=meta_profile,
    )

    # 3. Flatten
    logger.info(">>> STAGE 3: Recursive Weight Flattening")
    for prof in target_profiles:
        prof = prof.strip()
        # flatten_weights needs to know where to look. We pass the output path in run_data_dir.
        QuantSDK.run_stage("risk.flatten_meta", meta_profile=meta_profile, output_path=str(run_data_dir / "portfolio_optimized_meta.json"), profile=prof)

    # 4. Reporting
    logger.info(">>> STAGE 4: Generating Forensic Report")
    # Generate report inside the run directory AND latest summary
    report_path = run_dir / "reports" / "meta_portfolio_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    QuantSDK.run_stage("risk.report_meta", meta_dir=run_data_dir, output_path=str(report_path), profiles=target_profiles, meta_profile=meta_profile)

    # Also update 'latest'
    latest_path = settings.artifacts_dir / "summaries/latest/meta_portfolio_report.md"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import shutil

        shutil.copy(report_path, latest_path)
    except Exception as e:
        logger.warning(f"Failed to update latest report: {e}")

    logger.info(f"✅ Meta-Portfolio Pipeline COMPLETE: {meta_profile}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, help="Meta portfolio profile name")
    parser.add_argument("--profiles", help="Comma-separated risk profiles to process")
    parser.add_argument("--execute-sleeves", action="store_true", help="Execute sub-sleeves in parallel using Ray")
    parser.add_argument("--use-native-ray", action="store_true", help="Use Ray Native Actors instead of Subprocess")
    parser.add_argument("--run-id", help="Explicit Run ID")
    parser.add_argument("--manifest", default="configs/manifest.json", help="Manifest path (default: configs/manifest.json)")
    parser.add_argument("--sdk", action="store_true", help="Use the new SDK-driven DAG orchestrator")
    args = parser.parse_args()

    if args.sdk:
        from tradingview_scraper.orchestration.sdk import QuantSDK

        QuantSDK.run_pipeline("meta.full", profile=args.profile, run_id=args.run_id, profiles=args.profiles)
        sys.exit(0)

    target_profs = args.profiles.split(",") if args.profiles else None
    run_meta_pipeline(args.profile, target_profs, execute_sleeves=args.execute_sleeves, use_native_ray=args.use_native_ray, run_id=args.run_id, manifest=args.manifest)
