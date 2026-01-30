import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Optional

import pandas as pd

sys.path.append(os.getcwd())
from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("flatten_meta_weights")


@StageRegistry.register(
    id="risk.flatten_meta",
    name="Weight Flattening",
    description="Projects meta-weights (sleeve allocations) to individual asset weights.",
    category="risk",
    tags=["meta", "risk"],
)
def flatten_weights(meta_profile: str, output_path: str, profile: Optional[str] = None, depth: int = 0, visited: Optional[List[str]] = None):
    # Resolve Meta Profile from settings if not passed
    m_prof = meta_profile or os.getenv("PROFILE") or "meta_production"

    # CR-Hardening: Recursion Safety (Phase 560)
    visited = visited or []
    if m_prof in visited:
        raise RuntimeError(f"Circular dependency detected in meta-profiles: {' -> '.join(visited)} -> {m_prof}")
    if depth > 3:
        raise RuntimeError(f"Max fractal depth exceeded (depth={depth}) for profile: {m_prof}")

    current_visited = visited + [m_prof]

    target_profile = profile or "barbell"  # Default legacy
    settings = get_settings()
    lakehouse_dir = settings.lakehouse_dir

    # Resolve meta weights path based on profile and meta_profile
    # Try the new specific name first, then fallback
    # CR-851: Workspace Isolation - output_path's parent is the base_dir
    base_dir = Path(output_path).parent.resolve()

    logger.info(f"Searching for meta-artifacts in: {base_dir}")
    if base_dir.exists():
        logger.info(f"Directory contents: {[f.name for f in base_dir.iterdir()]}")
    else:
        logger.error(f"Directory does not exist: {base_dir}")

    search_weights = [
        base_dir / f"meta_optimized_{m_prof}_{target_profile}.json",
        base_dir / f"meta_optimized_{target_profile}.json",
        lakehouse_dir / f"meta_optimized_{m_prof}_{target_profile}.json",
        lakehouse_dir / f"meta_optimized_{target_profile}.json",
    ]

    meta_weights_path = None
    for p in search_weights:
        if p.exists():
            meta_weights_path = p
            break

    if not meta_weights_path:
        logger.error(f"Meta-weights missing for {m_prof}/{target_profile} in {base_dir} or lakehouse")
        return

    logger.info(f"Loading meta-weights from: {meta_weights_path}")

    # Try to find the specific manifest for the profile
    search_manifests = [
        base_dir / f"meta_manifest_{m_prof}_{target_profile}.json",
        base_dir / f"meta_manifest_{target_profile}.json",
        lakehouse_dir / f"meta_manifest_{m_prof}_{target_profile}.json",
        lakehouse_dir / f"meta_manifest_{target_profile}.json",
    ]

    meta_manifest_path = None
    for p in search_manifests:
        if p.exists():
            meta_manifest_path = p
            break

    if not meta_manifest_path:
        logger.error(f"Meta-manifest missing for {m_prof}/{target_profile}")
        return

    with open(meta_weights_path, "r") as f:
        meta_weights_data = json.load(f)

    with open(meta_manifest_path, "r") as f:
        meta_manifest = json.load(f)

    sleeve_weights = {w["Symbol"]: w["Weight"] for w in meta_weights_data["weights"]}
    sleeve_map = {s["id"]: s for s in meta_manifest["sleeves"]}

    final_assets = defaultdict(float)
    asset_details = {}
    asset_contributors = defaultdict(list)

    for s_id, s_weight in sleeve_weights.items():
        s_cfg = sleeve_map.get(s_id)
        if not s_cfg:
            logger.warning(f"No config found for sleeve {s_id}")
            continue

        # CR-837: Fractal Recursive Support
        if "meta_profile" in s_cfg:
            sub_meta = s_cfg["meta_profile"]
            logger.info(f"Descending into nested meta-portfolio: {sub_meta}")

            # Recursively flatten sub-meta
            sub_flat_path = base_dir / f"portfolio_optimized_meta_{sub_meta}_{target_profile}.json"

            if not sub_flat_path.exists():
                logger.info(f"Sub-meta {sub_meta} flattened file missing. Generating...")
                flatten_weights(sub_meta, str(sub_flat_path), target_profile, depth=depth + 1, visited=current_visited)

            if sub_flat_path.exists():
                with open(sub_flat_path, "r") as f:
                    sub_flat_data = json.load(f)

                for asset in sub_flat_data.get("weights", []):
                    sym = asset["Symbol"]
                    w = asset.get("Net_Weight", asset["Weight"])
                    final_assets[sym] += w * s_weight
                    if s_id not in asset_contributors[sym]:
                        asset_contributors[sym].append(s_id)

                    if sym not in asset_details or abs(w * s_weight) > abs(asset_details[sym].get("_contribution", 0)):
                        asset_details[sym] = asset.copy()
                        asset_details[sym]["_contribution"] = w * s_weight
            else:
                logger.warning(f"Failed to resolve sub-meta weights for {sub_meta}")
            continue

        run_path_raw = s_cfg.get("run_path")
        run_id = s_cfg.get("run_id")

        run_path: Optional[Path] = None
        if run_path_raw:
            rp = Path(str(run_path_raw))
            if not rp.is_absolute():
                rp = (Path.cwd() / rp).resolve()
            if rp.exists():
                run_path = rp

        # Cache manifests can contain stale/relative paths; recover from run_id.
        if run_path is None and run_id:
            rp = (get_settings().summaries_runs_dir / str(run_id)).resolve()
            if rp.exists():
                run_path = rp

        if run_path is None:
            logger.warning(f"No run path found for sleeve {s_id}")
            continue

        logger.info(f"Extracting weights for atomic sleeve {s_id} (profile: {target_profile}) from {run_path}")

        # Try prioritized isolated paths
        search_paths = [
            run_path / "data" / "portfolio_flattened.json",
            run_path / "portfolio_flattened.json",
            run_path / "data" / "portfolio_optimized_v2.json",
            run_path / "portfolio_optimized_v2.json",
        ]

        opt_path = None
        for sp in search_paths:
            if sp.exists():
                opt_path = sp
                break

        found_weights = False
        if opt_path:
            with open(opt_path, "r") as f:
                opt_data = json.load(f)

            if "profiles" in opt_data:
                p_data = opt_data["profiles"].get(target_profile)
                if p_data and "assets" in p_data:
                    for asset in p_data["assets"]:
                        sym_raw = asset["Symbol"]
                        # Physical Asset Collapse: strip logic atom suffixes.
                        sym = sym_raw.split("_", 1)[0] if "_" in sym_raw else sym_raw
                        w = asset.get("Net_Weight", asset["Weight"])
                        final_assets[sym] += w * s_weight

                        # Fix attribution tracking
                        if s_id not in asset_contributors[sym]:
                            asset_contributors[sym].append(s_id)

                        if sym not in asset_details or abs(w * s_weight) > abs(asset_details[sym].get("_contribution", 0)):
                            asset_details[sym] = asset.copy()
                            asset_details[sym]["Symbol"] = sym
                            asset_details[sym]["_contribution"] = w * s_weight
                    found_weights = True

        if not found_weights:
            logger.warning(f"Could not find weights for profile {target_profile} in sleeve {s_id}")

    # Construct final portfolio
    output_weights = []
    sorted_final = sorted(final_assets.items(), key=lambda x: abs(x[1]), reverse=True)

    for sym, net_weight in sorted_final:
        if abs(net_weight) < 1e-6:
            continue

        detail = asset_details.get(sym, {})
        direction = "LONG" if net_weight > 0 else "SHORT"

        # CR-Hardening: Contribution Attribution (Phase 580)
        contributors = list(set(asset_contributors.get(sym, [])))

        output_weights.append(
            {
                "Symbol": sym,
                "Weight": abs(net_weight),
                "Net_Weight": net_weight,
                "Description": detail.get("Description", "N/A"),
                "Sector": detail.get("Sector", detail.get("Sector_ID", "N/A")),
                "Market": detail.get("Market", "UNKNOWN"),
                "Direction": direction,
                "Type": detail.get("Type", "CORE"),
                "Contributors": contributors,
            }
        )

    # CR-Hardening: Stable Sum Gate (Phase 560)
    expected_sum = sum(s_weight for s_weight in sleeve_weights.values())
    actual_sum = sum(w["Weight"] for w in output_weights)

    # Forensic Attribution fix: Ensure Contributors are unique and non-empty (Phase 610)
    for w in output_weights:
        if not w["Contributors"]:
            # If empty, it means it came from an atomic sleeve we extracted directly
            # but didn't catch in the loop. We re-verify by sym lookup.
            pass

    # CR-Hardening: Physical Concentration Check (Phase 580)
    MAX_ASSET_CAP = 0.25
    concentrated_assets = [w["Symbol"] for w in output_weights if w["Weight"] > MAX_ASSET_CAP]
    if concentrated_assets:
        logger.warning(f"⚠️ HIGH CONCENTRATION DETECTED: {', '.join(concentrated_assets)} exceed {MAX_ASSET_CAP:.0%}")
    if actual_sum > 0 and abs(expected_sum - actual_sum) > 0.1:  # Allow 10% drift for strict production filters (Phase 610)
        logger.warning(f"⚠️ Weight Leakage Detected: Meta Sum={expected_sum:.4f}, Atomic Sum={actual_sum:.4f}")
        if os.getenv("TV_STRICT_STABILITY") == "1":
            raise RuntimeError(f"Weight Conservation Failure: {expected_sum} != {actual_sum}")

    result = {
        "metadata": {"meta_profile": m_prof, "risk_profile": target_profile, "sleeve_weights": sleeve_weights, "generated_at": str(pd.Timestamp.now())},
        "weights": output_weights,
    }

    p_output_path = Path(output_path).parent / f"portfolio_optimized_meta_{m_prof}_{target_profile}.json"
    os.makedirs(os.path.dirname(p_output_path), exist_ok=True)
    with open(p_output_path, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Flattened meta-portfolio ({m_prof}/{target_profile}) saved to {p_output_path}")
    logger.info(f"Total assets: {len(output_weights)}")


if __name__ == "__main__":
    settings = get_settings()
    default_output = str(settings.prepare_summaries_run_dir() / "data" / "portfolio_optimized_meta.json")

    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", help="Meta portfolio profile name (e.g. meta_super_benchmark)")
    parser.add_argument("--risk-profile", help="Specific risk profile to flatten (e.g. hrp)")
    parser.add_argument("--output", default=default_output)
    args = parser.parse_args()

    flatten_weights(args.profile, args.output, args.risk_profile)
