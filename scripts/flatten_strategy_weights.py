import json
import logging
import os
from collections import defaultdict

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("weight_flattener")


def flatten_strategy_weights():
    """
    Step 14.5: Weight Flattening
    Converts 'Logic Atom' weights (from Optimization) into 'Physical Asset' weights (for Execution/Validation).

    Logic:
    - Atom: BINANCE:BTCFDUSD_rating_all_long_LONG
    - Weight: 0.1
    - Direction: LONG -> Net: 0.1, Gross: 0.1

    - Atom: BINANCE:BTCFDUSD_rating_all_short_SHORT
    - Weight: 0.1
    - Direction: SHORT -> Net: -0.1, Gross: 0.1

    Aggregates net weights per physical symbol.
    """
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # 1. Load Logic Weights (Optimized)
    # CR-831: Workspace Isolation
    input_path = os.getenv("OPTIMIZED_FILE") or str(run_dir / "data" / "portfolio_optimized_v2.json")
    if not os.path.exists(input_path):
        # Fallback
        input_path = "data/lakehouse/portfolio_optimized_v2.json"

    if not os.path.exists(input_path):
        logger.error(f"Optimized portfolio not found at {input_path}")
        return

    logger.info(f"Loading logic weights from {input_path}")
    with open(input_path, "r") as f:
        opt_data = json.load(f)

    # 2. Load Candidates (Logic Definitions) to resolve Atom -> Physical + Direction
    candidates_path = os.getenv("CANDIDATES_SELECTED") or str(run_dir / "data" / "portfolio_candidates.json")
    if not os.path.exists(candidates_path):
        candidates_path = os.getenv("CANDIDATES_RAW") or str(run_dir / "data" / "portfolio_candidates_raw.json")

    atom_map = {}  # atom_id -> {physical, direction}
    if os.path.exists(candidates_path):
        with open(candidates_path, "r") as f:
            candidates = json.load(f)
            for c in candidates:
                atom_id = c.get("atom_id")
                # Fallback reconstruction if atom_id missing
                if not atom_id:
                    phys = c.get("physical_symbol") or c.get("symbol")
                    logic = c.get("logic", "trend")
                    direction = c.get("direction", "LONG")
                    atom_id = f"{phys}_{logic}_{direction}"

                atom_map[atom_id] = {"physical": c.get("physical_symbol") or c.get("symbol"), "direction": c.get("direction", "LONG"), "market": c.get("market"), "sector": c.get("sector")}
    else:
        logger.warning(f"Candidates file not found at {candidates_path}. Flattening will rely on heuristic parsing.")

    # 3. Flatten
    flat_profiles = {}

    profiles = opt_data.get("profiles", {})
    for profile_name, p_data in profiles.items():
        if "assets" not in p_data:
            continue

        assets = p_data["assets"]
        # Aggregators
        phys_net = defaultdict(float)
        phys_gross = defaultdict(float)
        phys_meta = {}
        phys_cluster = {}  # Keep track of cluster ID (dominant)

        for item in assets:
            atom = item["Symbol"]
            weight = item["Weight"]
            cluster_id = item.get("Cluster_ID", "N/A")

            # Resolve Metadata
            if atom in atom_map:
                meta = atom_map[atom]
                phys = meta["physical"]
                direction = meta["direction"]
            else:
                # Heuristic Parse: SYMBOL_logic_DIRECTION
                parts = atom.split("_")
                if len(parts) >= 3 and parts[-1] in ["LONG", "SHORT"]:
                    direction = parts[-1]
                    phys = "_".join(parts[:-2])  # Rough guess
                else:
                    # Assume strictly physical or unknown
                    phys = atom
                    direction = "LONG"

                meta = {"market": "UNKNOWN", "sector": "UNKNOWN"}

            # Apply Logic
            sign = -1.0 if direction == "SHORT" else 1.0

            phys_net[phys] += weight * sign
            phys_gross[phys] += abs(weight)

            if phys not in phys_meta:
                phys_meta[phys] = meta

            # Assign Cluster ID from the largest constituent so far?
            # Or just overwrite. Usually an asset is dominated by one strategy.
            # Ideally we check max weight.
            if abs(weight) > abs(phys_gross[phys] - abs(weight)):  # If this atom adds more weight than previous total? No.
                # Simplified: Just overwrite.
                phys_cluster[phys] = cluster_id

        # Construct Flattened Assets List
        flat_assets = []
        for phys, net_w in phys_net.items():
            meta = phys_meta.get(phys, {})
            direction_str = "LONG" if net_w > 0 else "SHORT" if net_w < 0 else "FLAT"
            flat_assets.append(
                {
                    "Symbol": phys,
                    "Weight": phys_gross[phys],  # Optimization often uses Gross Weight for constraints, but Simulator needs Net.
                    "Net_Weight": net_w,
                    "Gross_Weight": phys_gross[phys],
                    "Direction": direction_str,
                    "Cluster_ID": phys_cluster.get(phys, "N/A"),
                    "Market": meta.get("market", "UNKNOWN"),
                    "Sector": meta.get("sector", "N/A"),
                }
            )

        flat_profiles[profile_name] = {
            "assets": flat_assets,
            "clusters": [],  # Clusters are hard to map back 1:1 if logic atoms split clusters. Omit or recalculate.
        }

    # 4. Save
    output_data = opt_data.copy()
    output_data["profiles"] = flat_profiles
    output_data["metadata"]["flattened"] = True

    output_path = os.getenv("FLATTENED_FILE") or str(run_dir / "data" / "portfolio_flattened.json")
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"Flattened portfolio saved to {output_path}")


if __name__ == "__main__":
    flatten_strategy_weights()
