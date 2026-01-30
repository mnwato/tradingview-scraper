import glob
import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd

# Targeted Crypto Venues
CRYPTO_EXCHANGES = {"BINANCE", "OKX", "BYBIT", "BITGET"}


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


def summarize_crypto_signals():
    # Capture all latest results
    export_dir = _resolve_export_dir()
    files = sorted(glob.glob(str(export_dir / "universe_selector_*.json")), key=os.path.getmtime, reverse=True)

    seen_categories = set()
    latest_files = []
    for f in files:
        basename = os.path.basename(str(f)).upper()
        parts = basename.split("_")
        if len(parts) < 5:
            continue

        # We only want strategy signals: LONG or SHORT
        direction = parts[4]
        if direction not in ["LONG", "SHORT"]:
            continue

        # Filter for Crypto only
        if not any(ex in basename for ex in CRYPTO_EXCHANGES):
            continue

        category = "_".join(parts[2:-1])
        if category not in seen_categories:
            latest_files.append(f)
            seen_categories.add(category)

    crypto_groups = {}

    for f in latest_files:
        with open(f, "r") as j:
            try:
                payload = json.load(j)
            except (json.JSONDecodeError, OSError):
                continue

            rows = payload.get("data", []) if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                continue

            basename = os.path.basename(str(f)).upper()
            parts = basename.split("_")
            exchange = parts[2]
            ptype = parts[3]
            direction = parts[4]

            key = (exchange, ptype)
            if key not in crypto_groups:
                crypto_groups[key] = []

            for r in rows:
                if not isinstance(r, dict):
                    continue
                op = {
                    "Symbol": r.get("symbol"),
                    "Direction": direction,
                    "Total VT": r.get("Value.Traded") or r.get("volume", 0),
                    "Perf.W": r.get("Perf.W", 0),
                    "Perf.1M": r.get("Perf.1M", 0),
                    "Rec": r.get("Recommend.All", 0),
                    "Alts": ", ".join(r.get("alternates", [])) if r.get("alternates") else "-",
                }
                crypto_groups[key].append(op)

    print("\n" + "=" * 140)
    print("CRYPTO TREND SIGNALS REVIEW (Long/Short Strategy Only)")
    print("=" * 140)

    for exchange, ptype in sorted(crypto_groups.keys()):
        ops = crypto_groups[(exchange, ptype)]
        if not ops:
            continue
        print(f"\n>>> {exchange} {ptype} <<<")
        df = pd.DataFrame(ops).sort_values(["Direction", "Total VT"], ascending=[False, False])

        # Total VT formatting
        df["Total VT"] = df["Total VT"].apply(lambda x: f"${x / 1e6:.1f}M" if x > 1000 else f"{x:.0f}")

        print(df[["Symbol", "Direction", "Total VT", "Perf.W", "Perf.1M", "Rec", "Alts"]].to_string(index=False))
        print("-" * 120)

    # Matrix Table
    print("\n" + "=" * 80)
    print("CRYPTO SIGNAL MATRIX")
    print("=" * 80)
    matrix_data = []
    for (ex, pt), ops in crypto_groups.items():
        longs = sum(1 for o in ops if o["Direction"] == "LONG")
        shorts = sum(1 for o in ops if o["Direction"] == "SHORT")
        matrix_data.append({"Exchange": ex, "Type": pt, "Longs": longs, "Shorts": shorts, "Total": len(ops)})

    if matrix_data:
        print(pd.DataFrame(matrix_data).sort_values("Exchange").to_string(index=False))
    print("=" * 80)


if __name__ == "__main__":
    summarize_crypto_signals()
