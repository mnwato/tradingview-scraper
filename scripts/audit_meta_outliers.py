import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

import numpy as np

sys.path.append(os.getcwd())
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("meta_outlier_audit")


def calculate_concentration_entropy(weights: List[float]) -> float:
    w = np.array(weights)
    w = w[w > 0]
    if len(w) <= 1:
        return 0.0
    p = w / w.sum()
    return float(-np.sum(p * np.log(p)) / np.log(len(w)))


def audit_meta_outliers(run_id: str):
    settings = get_settings()
    lakehouse = Path("data/lakehouse")

    # 1. Load all meta-optimized profiles
    meta_files = list(lakehouse.glob("meta_optimized_*.json"))

    logger.info(f"🛡️  Deep Meta Audit for Run: {run_id}")
    logger.info(f"Found {len(meta_files)} meta-profiles to audit.")

    audit_results = []

    for f in meta_files:
        with open(f, "r") as f_in:
            data = json.load(f_in)

        prof = data["metadata"]["profile"]
        weights = {w["Symbol"]: w["Weight"] for w in data["weights"]}
        entropy = calculate_concentration_entropy(list(weights.values()))

        logger.info(f"\n--- Profile: {prof} ---")
        logger.info(f"  Concentration Entropy: {entropy:.4f}")

        # Spot dominant outliers
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        for sym, w in sorted_weights[:3]:
            logger.info(f"  Top Asset: {sym} ({w:.2%})")
            if w > 0.25:
                logger.warning(f"  ⚠️  OUTLIER ALERT: {sym} exceeds 25% global cap at meta-layer.")

        audit_results.append({"profile": prof, "entropy": entropy, "top_assets": sorted_weights[:3]})

    # 2. Cross-Sleeve Collision Check
    # Load sub-sleeve winners
    sleeve_assets: Dict[str, Set[str]] = {}
    manifest_files = list(lakehouse.glob("meta_manifest_*.json"))
    if manifest_files:
        with open(manifest_files[0], "r") as f_in:
            manifest = json.load(f_in)

        for sleeve in manifest["sleeves"]:
            s_id = sleeve["id"]
            s_path = Path(sleeve["run_path"])
            cand_path = s_path / "reports" / "selection" / "report.md"  # We'll grep instead

            # Simplified: load from portfolio_optimized_v2.json in run dir
            opt_path = s_path / "data" / "metadata" / "portfolio_optimized_v2.json"
            if opt_path.exists():
                with open(opt_path, "r") as f_opt:
                    opt_data = json.load(f_opt)
                # Take all winners across all sub-profiles
                assets = set()
                for p_name, p_data in opt_data.get("profiles", {}).items():
                    for asset in p_data.get("assets", []):
                        assets.add(asset["Symbol"])
                sleeve_assets[s_id] = assets

    if len(sleeve_assets) >= 2:
        keys = list(sleeve_assets.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                s1, s2 = keys[i], keys[j]
                intersection = sleeve_assets[s1].intersection(sleeve_assets[s2])
                if intersection:
                    logger.warning(f"🚨 COLLISION DETECTED between {s1} and {s2}!")
                    logger.warning(f"   Common Assets: {intersection}")
                else:
                    logger.info(f"✅ Orthogonality Verified: 0 common assets between {s1} and {s2}.")

    logger.info("\nAudit Complete.")


if __name__ == "__main__":
    audit_meta_outliers("latest")
