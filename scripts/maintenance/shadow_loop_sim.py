import json
import logging
import os
import shutil
import sys
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("shadow_loop")

STATE_FILE = "data/lakehouse/portfolio_actual_state.json"
OPTIMIZED_FILE = "data/lakehouse/portfolio_optimized_v3.json"
SHADOW_LOG = "data/lakehouse/shadow_fills.jsonl"


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def save_json(path: str, data: dict, backup: bool = True):
    if backup and os.path.exists(path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, f"{path}.bak_{ts}")

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def log_shadow_trade(trade: dict):
    with open(SHADOW_LOG, "a") as f:
        f.write(json.dumps(trade) + "\n")


def run_shadow_loop(min_trade_threshold: float = 0.01):
    """
    Simulates rebalance execution (Shadow Fills).
    Calculates drift between actual and optimized state, then updates actual.
    """
    optimized_data = load_json(OPTIMIZED_FILE)
    actual_state = load_json(STATE_FILE)

    if not optimized_data:
        logger.error(f"Optimized file missing: {OPTIMIZED_FILE}")
        return

    # Normalize V3 Multi-Winner format
    target_profiles = {}
    if "winners" in optimized_data:
        for w in optimized_data["winners"]:
            rank = w.get("rank", 1)
            eng = w.get("engine", "unknown")
            prof = w.get("profile", "unknown")
            key = f"Rank{rank}_{eng}_{prof}"
            target_profiles[key] = w
    else:
        # Fallback to single profile
        prof = optimized_data.get("profile", "barbell")
        target_profiles[prof] = optimized_data

    if not actual_state:
        logger.warning("Actual state file missing. Initializing from current optimized targets.")
        save_json(STATE_FILE, target_profiles, backup=False)
        return

    updated_state = actual_state.copy()
    now_ts = datetime.now().isoformat()
    fills_count = 0

    for profile_key, target_payload in target_profiles.items():
        logger.info(f"Analyzing drift for profile: {profile_key}")

        current_assets = {a["Symbol"]: a for a in target_payload.get("assets", [])}
        last_assets_list = actual_state.get(profile_key, {}).get("assets", [])
        last_assets = {a["Symbol"]: a for a in last_assets_list}

        all_symbols = sorted(set(current_assets.keys()) | set(last_assets.keys()))

        new_actual_assets = []

        for sym in all_symbols:
            w_target = current_assets.get(sym, {}).get("Weight", 0.0)
            w_actual = last_assets.get(sym, {}).get("Weight", 0.0)
            drift = w_target - w_actual

            if abs(drift) >= min_trade_threshold:
                # Execute shadow fill
                logger.info(f"✨ [FILL] {profile_key} | {sym}: {w_actual:.2%} -> {w_target:.2%} (Drift: {drift:+.2%})")

                trade_record = {"timestamp": now_ts, "profile": profile_key, "symbol": sym, "last_weight": w_actual, "target_weight": w_target, "drift": drift, "type": "shadow_fill"}
                log_shadow_trade(trade_record)

                # Update to target weight
                filled_asset = current_assets.get(sym, {}).copy()
                new_actual_assets.append(filled_asset)
                fills_count += 1
            else:
                # Keep existing weight
                existing_asset = last_assets.get(sym, {}).copy()
                if not existing_asset:
                    # New asset but below threshold? Should still probably be in actual if it's in target
                    # but maybe with 0 weight if we didn't buy it yet.
                    # For shadow sim, let's keep it consistent.
                    if w_target > 0:
                        logger.debug(f"Dust asset {sym} at {w_target:.4f} ignored.")
                else:
                    new_actual_assets.append(existing_asset)

        updated_state[profile_key] = {"assets": new_actual_assets, "updated_at": now_ts}

    if fills_count > 0:
        save_json(STATE_FILE, updated_state)
        logger.info(f"✅ Shadow loop complete. Applied {fills_count} fills.")
    else:
        logger.info("No significant drift detected. No shadow fills applied.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.01, help="Min drift threshold for shadow fill")
    args = parser.parse_args()

    run_shadow_loop(min_trade_threshold=args.threshold)
