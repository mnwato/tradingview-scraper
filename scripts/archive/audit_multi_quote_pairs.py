import glob
import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd


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


def audit_multi_quote():
    export_dir = _resolve_export_dir()

    # 1. Get latest base universe files for Binance
    spot_base_file = sorted(
        glob.glob(str(export_dir / "universe_selector_binance_top50_spot_base_*.json")),
        key=os.path.getmtime,
        reverse=True,
    )[0]
    perp_base_file = sorted(
        glob.glob(str(export_dir / "universe_selector_binance_top50_perp_base_*.json")),
        key=os.path.getmtime,
        reverse=True,
    )[0]

    # 2. Get latest trend scan files for Binance
    trend_files = glob.glob(str(export_dir / "universe_selector_binance_*_*.json"))
    trend_symbols = set()
    for f in trend_files:
        if "base" in f:
            continue
        with open(f, "r") as j:
            data = json.load(j)
            if isinstance(data, list):
                for item in data:
                    trend_symbols.add(item["symbol"])
            elif isinstance(data, dict) and "data" in data:
                for item in data["data"]:
                    trend_symbols.add(item["symbol"])

    results = []

    def process_base(file_path, ptype):
        with open(file_path, "r") as j:
            data = json.load(j)
            # Standardize to list if it's in the wrapper format
            items = data["data"] if isinstance(data, dict) and "data" in data else data

            for item in items:
                if item.get("alternates") and len(item["alternates"]) > 0:
                    symbol = item["symbol"]
                    alts = item["alternates"]

                    # Check if primary or ANY alternate is in trend symbols
                    in_trend = symbol in trend_symbols or any(alt in trend_symbols for alt in alts)

                    results.append({"Type": ptype, "Primary": symbol, "Alternates": ", ".join(alts), "In Trend": in_trend, "Total VT": item.get("Value.Traded", 0)})

    process_base(spot_base_file, "SPOT")
    process_base(perp_base_file, "PERP")

    df = pd.DataFrame(results)

    print("\n" + "=" * 100)
    print("BINANCE MULTI-QUOTE PAIRS AUDIT")
    print("=" * 100)

    # Filter for those actually in trend for focused research
    trend_focused = df[df["In Trend"] == True].sort_values("Total VT", ascending=False)  # type: ignore

    if not trend_focused.empty:
        print("\n>>> Trend-Filtered Candidates (High Priority) <<<")
        print(trend_focused[["Type", "Primary", "Alternates", "Total VT"]].to_string(index=False))

    print("\n>>> All Multi-Quote Pairs <<<")
    print(df.sort_values(["Type", "Total VT"], ascending=[True, False])[["Type", "Primary", "Alternates", "In Trend"]].to_string(index=False))

    # Export mapping for Phase 2
    mapping = {}
    for _, row in df.iterrows():
        mapping[str(row["Primary"])] = str(row["Alternates"]).split(", ")

    with open("export/multi_quote_mapping.json", "w") as f:
        json.dump(mapping, f, indent=2)
    print("\n[INFO] Mapping exported to export/multi_quote_mapping.json")


if __name__ == "__main__":
    audit_multi_quote()
