import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional


def _resolve_export_dir(run_id: Optional[str] = None) -> Path:
    export_root = Path("export")
    run_id = run_id or os.getenv("TV_EXPORT_RUN_ID") or ""

    if run_id:
        candidate = export_root / run_id
        if candidate.exists():
            return candidate

    if export_root.exists():
        best_dir: Optional[Path] = None
        best_mtime = -1.0
        for subdir in export_root.iterdir():
            if not subdir.is_dir():
                continue
            matches = list(subdir.glob("universe_selector_*.json"))
            if not matches:
                continue
            newest = max(p.stat().st_mtime for p in matches)
            if newest > best_mtime:
                best_mtime = newest
                best_dir = subdir
        if best_dir is not None:
            return best_dir

    return export_root


def load_json(filepath):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return None


def normalize_name(name):
    """Normalize asset name by removing common suffixes."""
    if not name:
        return ""
    # Handle dot suffixes first (e.g., AUDNOK.P -> AUDNOK)
    if "." in name:
        name = name.split(".")[0]

    # Strip continuous contract suffix (e.g., SI1! -> SI)
    if name.endswith("1!"):
        return name[:-2]

    # Strip futures contract month/year codes (e.g., SIH2026 -> SI)
    # Month codes: F,G,H,J,K,M,N,Q,U,V,X,Z followed by 4-digit year
    match = re.match(r"^(.+?)[FGHJKMNQUVXZ]\d{4}$", name)
    if match:
        return match.group(1)

    return name


def main():
    export_dir = _resolve_export_dir()
    # Grab all selector output files
    files = sorted(list(export_dir.glob("universe_selector_*.json")))

    if not files:
        print("No result files found in export/")
        return

    # Categorize files
    grouped = defaultdict(list)
    for f in files:
        name = f.name
        # Match keys from config filenames
        if "futures_trend_momentum" in name and "metals" not in name and "short" not in name:
            grouped["futures_long"].append(f)
        elif "futures_trend_momentum_short" in name and "metals" not in name:
            grouped["futures_short"].append(f)
        elif "futures_mean_reversion" in name and "short" not in name:
            grouped["futures_mr_long"].append(f)
        elif "futures_mean_reversion_short" in name:
            grouped["futures_mr_short"].append(f)
        elif "futures_metals_trend_momentum" in name and "short" not in name:
            grouped["metals_long"].append(f)
        elif "futures_metals_trend_momentum_short" in name:
            grouped["metals_short"].append(f)
        elif "cfd_trend_momentum" in name and "short" not in name:
            grouped["cfd_long"].append(f)
        elif "cfd_trend_momentum_short" in name:
            grouped["cfd_short"].append(f)
        elif "forex_mtf_monthly_weekly_daily" in name and "short" not in name:
            grouped["forex_mtf_long"].append(f)
        elif "forex_mtf_monthly_weekly_daily_short" in name:
            grouped["forex_mtf_short"].append(f)
        elif "forex_mtf_weekly_daily_daily" in name and "short" not in name:
            grouped["forex_mtf_long"].append(f)
        elif "forex_mtf_weekly_daily_daily_short" in name:
            grouped["forex_mtf_short"].append(f)
        elif "forex_trend_momentum" in name and "short" not in name:
            grouped["forex_long"].append(f)
        elif "forex_trend_momentum_short" in name:
            grouped["forex_short"].append(f)
        elif "forex_mean_reversion" in name and "short" not in name:
            grouped["forex_mr_long"].append(f)
        elif "forex_mean_reversion_short" in name:
            grouped["forex_mr_short"].append(f)
        elif "us_etf_trend_momentum" in name and "short" not in name:
            grouped["etf_long"].append(f)
        elif "us_etf_trend_momentum_short" in name:
            grouped["etf_short"].append(f)
        elif "us_stocks_trend_momentum" in name and "short" not in name:
            grouped["stocks_long"].append(f)
        elif "us_stocks_trend_momentum_short" in name:
            grouped["stocks_short"].append(f)
        elif "us_stocks_mean_reversion" in name and "short" not in name:
            grouped["stocks_mr_long"].append(f)
        elif "us_stocks_mean_reversion_short" in name:
            grouped["stocks_mr_short"].append(f)

    # Define display order
    order_map = [
        ("futures_long", ("Futures", "Trend", "L")),
        ("futures_short", ("Futures", "Trend", "S")),
        ("futures_mr_long", ("Futures", "MR", "L")),
        ("futures_mr_short", ("Futures", "MR", "S")),
        ("metals_long", ("Metals", "Trend", "L")),
        ("metals_short", ("Metals", "Trend", "S")),
        ("cfd_long", ("CFD", "Trend", "L")),
        ("cfd_short", ("CFD", "Trend", "S")),
        ("forex_mtf_long", ("Forex", "MTF", "L")),
        ("forex_mtf_short", ("Forex", "MTF", "S")),
        ("forex_long", ("Forex", "Trend", "L")),
        ("forex_short", ("Forex", "Trend", "S")),
        ("forex_mr_long", ("Forex", "MR", "L")),
        ("forex_mr_short", ("Forex", "MR", "S")),
        ("etf_long", ("US ETF", "Trend", "L")),
        ("etf_short", ("US ETF", "Trend", "S")),
        ("stocks_long", ("US Stocks", "Trend", "L")),
        ("stocks_short", ("US Stocks", "Trend", "S")),
        ("stocks_mr_long", ("US Stocks", "MR", "L")),
        ("stocks_mr_short", ("US Stocks", "MR", "S")),
    ]

    print(f"{'Market':<10} | {'Type':<6} | {'Dir':<3} | {'Symbol':<18} | {'Name':<15} | {'Close':<10} | {'Change%':<8} | {'Rec':<5} | {'ADX':<5} | {'Vol.D':<6} | {'Sector'}")
    print("-" * 120)

    for market_key, (market, type_, direction) in order_map:
        file_list = grouped.get(market_key, [])
        if not file_list:
            continue

        # Sort by mtime desc to get latest run
        file_list.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_file = file_list[0]

        data = load_json(latest_file)
        if not data:
            continue

        if isinstance(data, dict):
            items = data.get("data", [])
        elif isinstance(data, list):
            items = data
        else:
            items = []

        filtered_items = [item for item in items if item.get("passes", {}).get("all", False)]

        aggregated = {}
        for item in filtered_items:
            raw_name = item.get("name", "")
            if not raw_name:
                continue

            norm_name = normalize_name(raw_name)

            vol_current = item.get("volume") or 0
            if norm_name in aggregated:
                vol_existing = aggregated[norm_name].get("volume") or 0
                if vol_current > vol_existing:
                    aggregated[norm_name] = item
            else:
                aggregated[norm_name] = item

        sorted_items = sorted(aggregated.values(), key=lambda x: x.get("volume") or 0, reverse=True)

        for item in sorted_items:
            symbol = item.get("symbol", "")
            name = item.get("name", "")
            norm_name = normalize_name(name)
            display_name = norm_name[:15]

            close = item.get("close", 0)
            change = item.get("change", 0)
            rec = item.get("Recommend.All", 0)
            adx = item.get("ADX", 0)
            vol = item.get("Volatility.D", 0)
            sector = item.get("sector") or "-"

            fmt_close = f"{close:.2f}"
            fmt_change = f"{change:+.2f}%"
            fmt_rec = f"{rec:.2f}"
            fmt_adx = f"{adx:.1f}" if adx else "-"
            fmt_vol = f"{vol:.1f}%" if vol else "-"

            # Truncate sector for display
            display_sector = sector[:15]

            print(f"{market:<10} | {type_:<6} | {direction:<3} | {symbol:<18} | {display_name:<15} | {fmt_close:<10} | {fmt_change:<8} | {fmt_rec:<5} | {fmt_adx:<5} | {fmt_vol:<6} | {display_sector}")


if __name__ == "__main__":
    main()
