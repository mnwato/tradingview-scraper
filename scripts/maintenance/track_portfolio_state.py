import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from typing import Optional

import pandas as pd
from rich import box  # type: ignore
from rich.console import Console  # type: ignore
from rich.table import Table  # type: ignore

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("portfolio_state")

STATE_FILE = "data/lakehouse/portfolio_actual_state.json"
OPTIMIZED_FILE_V3 = "data/lakehouse/portfolio_optimized_v3.json"
OPTIMIZED_FILE_V2 = "data/lakehouse/portfolio_optimized_v2.json"


def _load_optimized_data() -> dict:
    target_file = OPTIMIZED_FILE_V3 if os.path.exists(OPTIMIZED_FILE_V3) else OPTIMIZED_FILE_V2
    if not os.path.exists(target_file):
        raise FileNotFoundError("Optimized portfolio file missing (Checked V3 and V2)")

    with open(target_file, "r") as f:
        optimized_data = json.load(f)

    # Multi-Winner V3 format has 'winners' list
    if "winners" in optimized_data:
        profiles = {}
        for w in optimized_data["winners"]:
            rank = w.get("rank", 1)
            eng = w.get("engine", "unknown")
            prof = w.get("profile", "unknown")
            # Create a unique key for the drift report
            key = f"Rank{rank}_{eng}_{prof}"
            profiles[key] = w
        return {"profiles": profiles}

    # V2 format has 'profiles' dict
    if "profiles" in optimized_data:
        return optimized_data

    # Legacy/Single-Winner V3 format has profile at root
    profile_name = optimized_data.get("profile", "barbell")
    return {"profiles": {profile_name: optimized_data}}


def _write_state_snapshot(profiles: dict, *, backup: bool = True) -> str:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    if backup and os.path.exists(STATE_FILE):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{STATE_FILE}.bak_{ts}"
        shutil.copy2(STATE_FILE, backup_path)

    tmp_path = f"{STATE_FILE}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(profiles, f, indent=2)
    os.replace(tmp_path, STATE_FILE)
    return STATE_FILE


def accept_state(*, backup: bool = True) -> int:
    try:
        optimized_data = _load_optimized_data()
        profiles = optimized_data.get("profiles")
        if not isinstance(profiles, dict):
            raise ValueError("Optimized portfolio file has invalid 'profiles' payload")

        _write_state_snapshot(profiles, backup=backup)
        logger.info("Accepted current optimized portfolio as actual state snapshot.")
        return 0
    except Exception as e:
        logger.error(f"Failed to accept state: {e}")
        return 1


def track_drift(min_trade_threshold: float = 0.01, orders_output: Optional[str] = None):
    console = Console()
    try:
        optimized_data = _load_optimized_data()
    except Exception as e:
        logger.error(str(e))
        return

    # If state file doesn't exist, initialize it with current optimal (Snapshot)
    if not os.path.exists(STATE_FILE):
        logger.info("Initializing portfolio state snapshot...")
        profiles = optimized_data.get("profiles")
        if isinstance(profiles, dict):
            _write_state_snapshot(profiles, backup=False)
        console.print("[bold green]Portfolio state initialized.[/] Run again after future optimizations to see drift.")
        return

    with open(STATE_FILE, "r") as f:
        actual_state = json.load(f)

    console.print("\n[bold cyan]📉 Portfolio Rebalancing Drift Analysis[/]")
    settings = get_settings()
    if settings.features.feat_partial_rebalance:
        console.print(f"[dim]Comparing current optimal vs. last implemented state. (Min Trade: {min_trade_threshold:.2%})[/]\n")
    else:
        console.print("[dim]Comparing current optimal vs. last implemented state.[/]\n")

    all_orders = []

    for profile_name in optimized_data["profiles"].keys():
        current_assets = {a["Symbol"]: a for a in optimized_data["profiles"][profile_name]["assets"]}
        last_assets = {a["Symbol"]: a for a in actual_state.get(profile_name, {}).get("assets", [])}

        all_symbols = sorted(set(current_assets.keys()) | set(last_assets.keys()))

        table = Table(title=f"Profile: {profile_name.replace('_', ' ').title()}", box=box.SIMPLE)
        table.add_column("Symbol", style="cyan")
        table.add_column("Last %", justify="right")
        table.add_column("Target %", justify="right", style="bold green")
        table.add_column("Drift", justify="right", style="bold magenta")
        table.add_column("Action", justify="center")
        if settings.features.feat_partial_rebalance:
            table.add_column("Status", justify="center")

        total_drift = 0.0
        significant_drift = 0.0

        for sym in all_symbols:
            w_last = float(last_assets.get(sym, {}).get("Weight", 0.0))
            w_target = float(current_assets.get(sym, {}).get("Weight", 0.0))
            drift = w_target - w_last
            total_drift += abs(drift)

            if abs(drift) < 0.0001:  # Absolute zero check
                continue

            if settings.features.feat_partial_rebalance:
                is_significant = abs(drift) >= min_trade_threshold
                status = "[green]EXECUTE[/]" if is_significant else "[yellow]SKIP (Dust)[/]"

                if is_significant:
                    significant_drift += abs(drift)
                    action = "BUY" if drift > 0 else "SELL"
                    asset_data = current_assets.get(sym) or last_assets.get(sym) or {}
                    all_orders.append(
                        {
                            "Profile": profile_name,
                            "Symbol": sym,
                            "Action": action,
                            "Size": abs(drift),
                            "Target_Weight": w_target,
                            "Market": asset_data.get("Market", "UNKNOWN"),
                            "Description": asset_data.get("Description", "N/A"),
                        }
                    )
                else:
                    action = "HOLD" if drift > 0 else "REDUCE"

                table.add_row(str(sym), f"{w_last:.2%}", f"{w_target:.2%}", f"{drift:+.2%}", f"[bold {'green' if drift > 0 else 'red'}]{action}[/]", status)
            else:
                action = "BUY" if drift > 0 else "SELL"
                table.add_row(str(sym), f"{w_last:.2%}", f"{w_target:.2%}", f"{drift:+.2%}", f"[bold {'green' if drift > 0 else 'red'}]{action}[/]")

        console.print(table)
        if settings.features.feat_partial_rebalance:
            console.print(f"[dim]Total Churn: {total_drift / 2:.2%} | Significant Churn: {significant_drift / 2:.2%}[/]\n")
        else:
            console.print(f"[dim]Total Turnover Required: {total_drift / 2:.2%}[/]\n")

    if orders_output and all_orders:
        orders_df = pd.DataFrame(all_orders)
        orders_df.to_csv(orders_output, index=False)
        console.print(f"[bold green]✅ Generated {len(all_orders)} orders to:[/] {orders_output}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Portfolio drift monitor and state snapshotter")
    parser.add_argument("--accept", action="store_true", help="Overwrite the last implemented state with the current optimized portfolio (use after implementation)")
    parser.add_argument("--no-backup", action="store_true", help="Disable backup when overwriting an existing state file")
    parser.add_argument("--min-trade", type=float, default=0.01, help="Minimum weight change to trigger an order (default: 0.01 / 1%)")
    parser.add_argument("--orders", type=str, help="Path to output rebalance orders as CSV")
    args = parser.parse_args()

    if args.accept:
        sys.exit(accept_state(backup=not args.no_backup))

    track_drift(min_trade_threshold=args.min_trade, orders_output=args.orders)
