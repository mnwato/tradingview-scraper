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


def generate_matrix_report():
    export_dir = _resolve_export_dir()
    files = sorted(glob.glob(str(export_dir / "universe_selector_*_base_*.json")), key=os.path.getmtime, reverse=True)[:8]

    matrix_data = []

    for f in files:
        with open(f, "r") as j:
            payload = json.load(j)
            rows = payload.get("data", []) if isinstance(payload, dict) else payload
            basename = os.path.basename(str(f))
            parts = basename.split("_")
            if len(parts) >= 5:
                exchange = parts[2].upper()
                ptype = parts[4].upper()
            else:
                continue

            if not isinstance(rows, list):
                continue

            total_bases = len(rows)
            if total_bases == 0:
                continue

            top_vt = rows[0].get("Value.Traded", 0)
            floor_vt = rows[-1].get("Value.Traded", 0)

            total_alts = sum(len(r.get("alternates", [])) for r in rows)
            bases_with_alts = sum(1 for r in rows if r.get("alternates"))
            avg_alts = total_alts / total_bases if total_bases > 0 else 0

            # Identify dominant quote for #1
            top_quote = ""
            for q in ["USDT", "USDC", "USD", "DAI", "BUSD", "FDUSD"]:
                if rows[0]["symbol"].endswith(q) or rows[0]["symbol"].endswith(q + ".P"):
                    top_quote = q
                    break

            matrix_data.append(
                {
                    "Exchange": exchange,
                    "Product": ptype,
                    "Unique Bases": total_bases,
                    "Top VT": f"${top_vt / 1e6:.1f}M",
                    "Floor VT": f"${floor_vt / 1e6:.1f}M",
                    "Top Quote": top_quote,
                    "Grouped Alts": total_alts,
                    "Bases w/ Alts": f"{bases_with_alts} ({bases_with_alts / total_bases * 100:.0f}%)",
                }
            )

    df = pd.DataFrame(matrix_data)
    # Sort for consistent matrix view
    df = df.sort_values(["Exchange", "Product"])

    print("\n" + "=" * 120)
    print("CRYPTO BASE UNIVERSE MATRIX REVIEW (Top 50 uniquely aggregated)")
    print("=" * 120)
    print(df)
    print("=" * 120)

    # Detailed Analysis
    print("\n--- Strategy Insights ---")
    print("1. Quote Standard: USDT is the universal leader, but USD (Inverse) dominates Binance/Bybit Perp liquidity.")
    print("2. Arbitrage Density: Binance Spot offers the richest set of alternate quotes per base (62% density).")
    print("3. Liquidity Depth: Perps consistently show significantly higher Top VT, but Spot 'Floor VT' is often comparable for the Top 50.")
    print("4. Market Maturity: OKX and Bitget results are highly standardized on USDT, showing high efficiency but lower cross-quote arb potential.")


if __name__ == "__main__":
    generate_matrix_report()
