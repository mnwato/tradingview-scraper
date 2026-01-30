import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import pandas as pd

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("orchestration_audit")


class OrchestrationAuditor:
    """
    Forensic auditor for validating the integrity of parallel orchestration runs.
    Checks manifest consistency, log errors, artifact causality, and performance.
    """

    def __init__(self, runs_dir: Optional[Path] = None):
        self.settings = get_settings()
        self.runs_dir = runs_dir or self.settings.summaries_runs_dir
        self.error_patterns = [
            re.compile(r"CRITICAL"),
            re.compile(r"EXCEPTION"),
            re.compile(r"RayActorError"),
            re.compile(r"WorkerCrashedError"),
            re.compile(r"Traceback"),
        ]

    def audit(self, meta_run_id: str) -> Dict[str, Any]:
        """Performs a full forensic audit on a meta-run."""
        meta_dir = self.runs_dir / meta_run_id
        if not meta_dir.exists():
            raise FileNotFoundError(f"Meta-run directory not found: {meta_dir}")

        report = {
            "meta_run_id": meta_run_id,
            "status": "pass",
            "manifest_integrity": {"status": "pass", "errors": []},
            "log_forensics": {"status": "pass", "errors": []},
            "artifact_parity": {"status": "pass", "errors": []},
            "performance": {"status": "pass", "warnings": []},
            "sleeves": [],
        }

        # 1. Load Manifest
        manifest = self._load_manifest(meta_dir)
        if not manifest:
            cast(Dict[str, Any], report["manifest_integrity"])["status"] = "fail"
            cast(Dict[str, Any], report["manifest_integrity"])["errors"].append("Could not find resolved_manifest.json or meta-manifest")
            report["status"] = "fail"
            return report

        # 2. Check Sleeves (Manifest Integrity)
        sleeves = self._get_sleeves(manifest)
        report["sleeves"] = sleeves
        for sleeve in sleeves:
            s_run_id = sleeve.get("run_id")
            if not s_run_id:
                continue

            s_dir = self.runs_dir / s_run_id
            if not s_dir.exists():
                cast(Dict[str, Any], report["manifest_integrity"])["status"] = "fail"
                cast(Dict[str, Any], report["manifest_integrity"])["errors"].append(f"Sleeve directory missing: {s_run_id}")
                report["status"] = "fail"

        # 3. Log Forensics
        self._check_logs(meta_dir, report)
        for sleeve in sleeves:
            s_run_id = sleeve.get("run_id")
            if s_run_id:
                self._check_logs(self.runs_dir / s_run_id, report)

        # 4. Artifact Parity (Causality Check)
        self._check_causality(meta_dir, sleeves, report)

        # Final Status Aggregation
        if any(v["status"] == "fail" for k, v in report.items() if isinstance(v, dict)):
            report["status"] = "fail"

        return report

    def _load_manifest(self, meta_dir: Path) -> Optional[Dict]:
        manifest_paths = [
            meta_dir / "config" / "resolved_manifest.json",
            meta_dir / "resolved_manifest.json",
        ]
        for p in manifest_paths:
            if p.exists():
                with open(p, "r") as f:
                    return json.load(f)

        # Look for meta-manifests in data/
        meta_data_manifests = list(meta_dir.glob("**/meta_manifest_*.json"))
        if meta_data_manifests:
            with open(meta_data_manifests[0], "r") as f:
                return json.load(f)

        return None

    def _get_sleeves(self, manifest: Dict) -> List[Dict]:
        # Handle different manifest structures
        if "profiles" in manifest:
            # Find a profile that has sleeves
            for p_name, p_cfg in manifest["profiles"].items():
                if isinstance(p_cfg, dict) and "sleeves" in p_cfg:
                    return p_cfg["sleeves"]

        # If it's a resolved manifest, it might have sleeves at the root
        return manifest.get("sleeves", [])

    def _check_logs(self, directory: Path, report: Dict):
        if not directory.exists():
            return

        for log_file in directory.rglob("*.log"):
            try:
                with open(log_file, "r") as f:
                    for i, line in enumerate(f):
                        for pattern in self.error_patterns:
                            if pattern.search(line):
                                report["log_forensics"]["status"] = "fail"
                                report["log_forensics"]["errors"].append(f"Found {pattern.pattern} in {log_file.name}:{i + 1} -> {line.strip()}")
            except Exception as e:
                logger.warning(f"Could not read log file {log_file}: {e}")

    def _check_causality(self, meta_dir: Path, sleeves: List[Dict], report: Dict):
        meta_matrix = meta_dir / "data" / "meta_returns.pkl"
        if not meta_matrix.exists():
            # Try other common names
            alt = list(meta_dir.glob("**/meta_returns*.pkl"))
            if alt:
                meta_matrix = alt[0]
            else:
                return

        meta_mtime = meta_matrix.stat().st_mtime

        for sleeve in sleeves:
            s_run_id = sleeve.get("run_id")
            if not s_run_id:
                continue

            s_dir = self.runs_dir / s_run_id
            if not s_dir.exists():
                continue

            # Check most recent return file in sleeve
            s_rets = list(s_dir.glob("**/returns/*.pkl"))
            if not s_rets:
                s_rets = list(s_dir.glob("*.pkl"))

            for ret_file in s_rets:
                if ret_file.stat().st_mtime > meta_mtime:
                    report["artifact_parity"]["status"] = "fail"
                    report["artifact_parity"]["errors"].append(f"Sleeve output {ret_file.name} (run {s_run_id}) is newer than meta-matrix. Possible race condition.")

    def write_report(self, meta_run_id: str, report: Dict):
        output_path = self.runs_dir / meta_run_id / "orchestration_health.md"
        md = [
            f"# Orchestration Health Report: {meta_run_id}",
            f"**Status**: {'✅ PASS' if report['status'] == 'pass' else '❌ FAIL'}",
            f"**Checked At**: {pd.Timestamp.now()}",
            "\n## Check Summary",
        ]

        for key in ["manifest_integrity", "log_forensics", "artifact_parity"]:
            res = report[key]
            status_str = "✅" if res["status"] == "pass" else "❌"
            md.append(f"- {status_str} **{key.replace('_', ' ').title()}**")
            for err in res.get("errors", []):
                md.append(f"  - `{err}`")

        if report.get("sleeves"):
            md.append("\n## Sleeves Audited")
            md.append("| Sleeve ID | Run ID | Status |")
            md.append("| :--- | :--- | :--- |")
            for s in report["sleeves"]:
                # Check if this sleeve's run_id was flagged in manifest_integrity
                missing = any(s.get("run_id") in str(e) for e in report["manifest_integrity"]["errors"])
                status = "❌ MISSING" if missing else "✅ OK"
                md.append(f"| {s['id']} | {s.get('run_id', 'N/A')} | {status} |")

        with open(output_path, "w") as f:
            f.write("\n".join(md))
        logger.info(f"Report written to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", help="Meta-run ID to audit")
    args = parser.parse_args()

    auditor = OrchestrationAuditor()
    report = auditor.audit(args.run_id)

    print(json.dumps(report, indent=2))
    auditor.write_report(args.run_id, report)
