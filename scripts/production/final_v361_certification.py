import argparse
import datetime
import logging
import os
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("v361_final_cert")


def run_cmd(cmd, env=None):
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=f"cert_v361_{datetime.datetime.now().strftime('%m%d_%H%M')}")
    args = parser.parse_args()

    run_id = args.run_id
    logger.info(f"Starting Final v3.6.1 Certification: {run_id}")

    # 1. Backtest Tournament Matrix
    selection_modes = ["v4", "v3.4", "baseline"]
    profiles = ["max_sharpe", "hrp", "market_neutral"]
    engines = ["skfolio", "riskfolio", "custom"]
    simulator = "cvxportfolio"

    run_ids = {}
    for mode in selection_modes:
        logger.info(f"==> Launching Certification: Selection={mode} (Run ID: {run_id}_{mode})")
        backtest_cmd = [
            "uv",
            "run",
            "scripts/backtest_engine.py",
            "--train-window",
            "60",
            "--test-window",
            "20",
            "--step-size",
            "40",
            "--selection-mode",
            mode,
            "--profiles",
            ",".join(profiles),
            "--engines",
            ",".join(engines),
            "--simulators",
            simulator,
        ]

        env = os.environ.copy()
        env["TV_RUN_ID"] = f"{run_id}_{mode}"
        env["TV_FEATURES__FEAT_AUDIT_LEDGER"] = "1"
        env["TV_FEATURES__FEAT_MARKET_NEUTRAL"] = "1"
        env["TV_FEATURES__FEAT_DYNAMIC_DIRECTION"] = "1"
        env["TV_FEATURES__FEAT_PREDICTABILITY_VETOES"] = "1"

        try:
            run_cmd(backtest_cmd, env=env)
            run_ids[mode] = f"{run_id}_{mode}"
        except subprocess.CalledProcessError as e:
            logger.error(f"Backtest failed for {mode}: {e.stderr}")
            continue

    # 2. Institutional Audit Report
    logger.info("Generating Final Certification Matrix...")
    audit_cmd = ["uv", "run", "scripts/production/stable_institutional_audit.py", "--run-id", f"{run_id}_*"]
    try:
        report = run_cmd(audit_cmd)
        print(report)
    except subprocess.CalledProcessError as e:
        logger.error(f"Audit failed: {e.stderr}")

    logger.info(f"Certification Complete for {run_id}")


if __name__ == "__main__":
    main()
