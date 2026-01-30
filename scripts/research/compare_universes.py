import json
import os
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


def load_symbols(filepath):
    try:
        with open(filepath, "r") as f:
            data = json.load(f)

            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("data", [])

            # Normalize symbols: Remove Exchange: prefix and handle .P suffix if needed (though spot shouldn't have it)
            symbols = set()
            for item in items:
                sym = item.get("symbol", "").split(":")[-1]
                symbols.add(sym)
            return symbols
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return set()


def main():
    base_dir = _resolve_export_dir()

    # Find the latest files
    trend_files = sorted(list(base_dir.glob("universe_selector_binance_spot_short_*.json")), reverse=True)
    base_files = sorted(list(base_dir.glob("universe_selector_binance_top50_spot_base_*.json")), reverse=True)

    if not trend_files or not base_files:
        print("Missing files.")
        return

    trend_path = trend_files[0]
    base_path = base_files[0]

    print(f"Comparing Trend File: {trend_path.name}")
    print(f"With Base File: {base_path.name}")

    trend_syms = load_symbols(trend_path)
    base_syms = load_symbols(base_path)

    print(f"\nTrend Symbols ({len(trend_syms)}): {sorted(list(trend_syms))}")
    print(f"Base Symbols ({len(base_syms)}): {sorted(list(base_syms))}")

    in_base = trend_syms.intersection(base_syms)
    not_in_base = trend_syms.difference(base_syms)

    print(f"\nIn Base Universe: {sorted(list(in_base))}")
    print(f"NOT in Base Universe: {sorted(list(not_in_base))}")

    if not not_in_base:
        print("\nSUCCESS: All trend results are in the Top 50 Base Universe.")
    else:
        print("\nFAILURE: Some trend results are NOT in the Top 50 Base Universe.")


if __name__ == "__main__":
    main()
