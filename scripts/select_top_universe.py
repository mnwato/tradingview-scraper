import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import pandas as pd

from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("select_top_universe")


def get_default_audit_file() -> str:
    settings = get_settings()
    # Prefer run-scoped audit if TV_RUN_ID is set (which select_top_universe should have)
    if settings.run_id and settings.run_id != "default_run":
        return str(settings.summaries_runs_dir / settings.run_id / "data" / "selection_audit.json")
    return str(settings.logs_dir / "selection_audit.json")


AUDIT_FILE = os.getenv("SELECTION_AUDIT", get_default_audit_file())


def _resolve_export_dir(run_id: Optional[str] = None) -> Path:
    settings = get_settings()
    # Allow override via env var for isolation (e.g. symlinked export dir)
    # Default to settings.export_dir instead of hardcoded "export"
    export_root = Path(os.getenv("TV_SCAN_DIR", str(settings.export_dir)))
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
            matches = []
            for p in ["universe_selector_*.json", "strategy_selector_*.json", "strategy_alpha_*.json", "universe_foundation_*.json"]:
                matches.extend(list(subdir.glob(p)))

            if not matches:
                continue
            newest = max(p.stat().st_mtime for p in matches)
            if newest > best_mtime:
                best_mtime = newest
                best_dir = subdir
        if best_dir is not None:
            return best_dir

    return export_root


def get_asset_identity(symbol: str, asset_class: str = "") -> str:
    """
    Extracts canonical identity of an asset to group redundant venues.
    Groups different stablecoin variations into one economic unit.
    """
    try:
        raw = symbol.split(":")[-1].upper()
        # 1. Handle Futures (strip contract dates)
        for prefix in ["GC", "SI", "HG", "PL", "PA", "ZC", "ZS", "ZW"]:
            if raw.startswith(prefix):
                return prefix

        asset_class_upper = (asset_class or "").upper()

        # 2. Handle Crypto (base/quote) + shared normalization
        # Remove common suffixes
        clean = raw.replace(".P", "").replace(".F", "").replace("-SWAP", "").replace("-SPOT", "")

        # Forex pairs should remain pair-identified (e.g. EURUSD), not base-identified (EUR).
        if asset_class_upper == "FOREX" or (len(clean) == 6 and clean.isalpha()):
            if "." in clean:
                clean = clean.split(".", 1)[0]
            clean = re.sub(r"[^A-Z0-9]", "", clean)
            return clean

        # Handle dashes
        if "-" in clean:
            parts = clean.split("-")
            return parts[0]

        # Heuristic for base/quote (e.g. BTCUSDT -> BTC)
        # Iteratively strip common stable and fiat quotes
        quotes = ["USDT", "USDC", "BUSD", "DAI", "FDUSD", "TUSD", "USDS", "USD", "EUR", "GBP", "JPY", "IDR", "TRY", "UAH", "ARS", "BRL", "ZAR", "VND", "THB", "PHP"]
        changed = True
        while changed:
            changed = False
            for quote in quotes:
                if clean.endswith(quote) and len(clean) > len(quote):
                    clean = clean[: -len(quote)]
                    changed = True
                    break
        return clean
    except Exception:
        return symbol


def get_asset_class(category: str, symbol: str = "") -> str:
    """Maps granular categories to broad institutional asset classes."""
    c = category.upper()
    s = symbol.upper()

    if "BOND" in c:
        return "FIXED_INCOME"

    if "ETF" in c:
        # Heuristic for Equity ETFs
        if any(x in s for x in ["SPY", "QQQ", "IWM", "DIA", "VTI", "VXUS", "VEA", "VWO"]):
            return "EQUITIES"
        # Heuristic for Bond ETFs
        if any(x in s for x in ["TLT", "IEF", "AGG", "BND", "HYG", "LQD", "TIP"]):
            return "FIXED_INCOME"
        return "EQUITIES"  # Default ETFs to Equities if unknown

    if any(x in c for x in ["BINANCE", "BYBIT", "OKX", "BITGET", "CRYPTO"]):
        return "CRYPTO"
    if any(x in c for x in ["NASDAQ", "NYSE", "AMEX", "US_STOCKS"]):
        return "EQUITIES"
    if any(x in c for x in ["CME", "COMEX", "NYMEX", "CBOT", "FUTURES"]):
        return "FUTURES"
    if "FOREX" in c:
        return "FOREX"
    return "OTHER"


def select_top_universe(mode: str = "raw"):
    """
    Discovery Stage Consolidator.
    Groups results from all scanners, picks the most liquid venue per identity,
    and passes a broad "Raw Pool" to the Selection Engine.
    """
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    export_dir = _resolve_export_dir()

    # Support both legacy and new scanner naming conventions
    patterns = ["universe_selector_*.json", "strategy_selector_*.json", "strategy_alpha_*.json", "universe_foundation_*.json"]
    files = []
    for p in patterns:
        files.extend([f for f in export_dir.glob(p) if "_base_universe" not in f.name])

    # Type-hinted audit structure to satisfy linter
    audit_discovery: Dict[str, Any] = {"total_scanned_files": len(files), "categories": {}, "total_symbols_found": 0}
    audit_data: Dict[str, Any] = {"timestamp": str(pd.Timestamp.now()), "discovery": audit_discovery}

    # 1. Load All Items
    all_items = []
    for f in files:
        try:
            with open(f, "r") as j:
                raw_data = json.load(j)
        except Exception as e:
            logger.error(f"Error reading {f}: {e}")
            continue

        meta: Dict[str, Any] = {}
        items: List[Dict[str, Any]] = []
        if isinstance(raw_data, dict):
            meta = cast(Dict[str, Any], raw_data.get("meta") or {})
            items = cast(List[Dict[str, Any]], raw_data.get("data", []))
        elif isinstance(raw_data, list):
            items = cast(List[Dict[str, Any]], raw_data)

        # 0. Context Mapping (Category extraction)
        category = str(meta.get("data_category", "UNKNOWN")).upper()
        if category == "UNKNOWN":
            if "binance_perp" in f.name.lower():
                category = "BINANCE_PERP"
            elif "binance_spot" in f.name.lower():
                category = "BINANCE_SPOT"

        # 1. Prefer embedded metadata; fall back to filename heuristics.
        file_direction = "SHORT" if "_short" in f.name.lower() else "LONG"
        file_logic = "trend"
        if "_rating_all" in f.name.lower():
            file_logic = "rating_all"
        elif "_rating_ma" in f.name.lower():
            file_logic = "rating_ma"
        elif "_rating_osc" in f.name.lower():
            file_logic = "rating_osc"
        elif "_vol_breakout" in f.name.lower():
            file_logic = "vol_breakout"

        meta_direction = meta.get("direction") or (meta.get("trend") or {}).get("direction")
        # Priority 1: logic field from manifest/config injection
        # Priority 2: filename heuristic
        meta_logic = meta.get("logic") or file_logic

        # DEBUG:
        print(f"DEBUG: Processing {f.name} - Logic: {meta_logic}")

        for i in items:
            if isinstance(i, dict) and "symbol" in i:
                i["_direction"] = meta_direction or file_direction
                i["_logic"] = meta_logic
                i["_category"] = category

                i["_asset_class"] = get_asset_class(category, i["symbol"])
                i["_identity"] = get_asset_identity(i["symbol"], i["_asset_class"])
                all_items.append(i)

    # 2. Basic Deduplication by Atom (Symbol + Logic + Direction)
    # Allows the same physical asset to be recruited under different alpha modules.
    unique_atoms = {}
    for item in all_items:
        key = (item["symbol"], item["_logic"], item["_direction"])
        if key not in unique_atoms:
            unique_atoms[key] = item

    # 3. Canonical Consolidation (Best Venue per Identity per Logic per Direction)
    identity_groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for item in unique_atoms.values():
        ident_key = (item["_identity"], item["_logic"], item["_direction"])
        if ident_key not in identity_groups:
            identity_groups[ident_key] = []
        identity_groups[ident_key].append(item)

    merged_pool = []
    redundancy_count = 0
    for ident_key, group in identity_groups.items():
        if len(group) > 1:
            redundancy_count += len(group) - 1

        # Use Value.Traded as the primary venue tie-breaker
        group.sort(key=lambda x: float(x.get("Value.Traded", 0) or 0), reverse=True)
        primary = group[0]

        # Track alternatives (other venues for the SAME logic/direction)
        primary["implementation_alternatives"] = [
            {"symbol": x["symbol"], "market": x["_category"], "asset_class": x["_asset_class"], "value_traded": float(x.get("Value.Traded", 0) or 0)} for x in group[1:]
        ]

        merged_pool.append(primary)

    audit_data["merging"] = {"total_unique_atoms": len(merged_pool), "redundant_venues_merged": redundancy_count}

    # 4. Global Pool Limit (Relaxed for Downstream Clustering)
    # We no longer calculate _alpha_score here; we rely on Value.Traded for discovery-stage priority
    merged_pool.sort(key=lambda x: float(x.get("Value.Traded", 0) or 0), reverse=True)

    # Increase Raw Pool capacity to 200 to give Log-MPS enough room to filter
    total_limit = int(os.getenv("UNIVERSE_TOTAL_LIMIT", "200"))
    final_candidates = merged_pool[:total_limit]

    audit_data["final_selection"] = {
        "mode": mode,
        "total_candidates": len(final_candidates),
        "class_breakdown": {ac: len([x for x in final_candidates if x["_asset_class"] == ac]) for ac in ["CRYPTO", "EQUITIES", "FUTURES", "FOREX", "FIXED_INCOME", "OTHER"]},
    }

    # Map to final format
    output_universe = []
    for item in final_candidates:
        phys_sym = item["symbol"]
        logic = item["_logic"]
        direction = item["_direction"]
        # CR-831: Canonical Atom Identity
        # atom_id = f"{phys_sym}_{logic}_{direction}"
        # CR-Update: Use physical symbol as primary key to streamline data pipeline
        # The Atom ID is preserved as 'atom_id' for downstream synthesis
        atom_id = f"{phys_sym}_{logic}_{direction}"

        output_universe.append(
            {
                "symbol": phys_sym,  # Changed from atom_id to phys_sym
                "atom_id": atom_id,
                "physical_symbol": phys_sym,
                "description": item.get("description", item.get("name", "N/A")),
                "sector": item.get("sector", "N/A"),
                "market": item["_category"],
                "asset_class": item["_asset_class"],
                "identity": item["_identity"],
                "close": item.get("close", 0),
                "value_traded": item.get("Value.Traded", 0),
                "adx": item.get("ADX", 0),
                "atr": item.get("ATR", 0),
                "volatility_d": item.get("Volatility.D", 0),
                "volume_change_pct": item.get("volume_change", 0),
                "roc": item.get("ROC", 0),
                "recommend_all": item.get("Recommend.All"),
                "recommend_ma": item.get("Recommend.MA"),
                "recommend_other": item.get("Recommend.Other"),
                # Include performance fields for Log-MPS
                "Perf.W": item.get("Perf.W"),
                "Perf.1M": item.get("Perf.1M"),
                "Perf.3M": item.get("Perf.3M"),
                "Perf.6M": item.get("Perf.6M"),
                "logic": logic,
                "direction": direction,
                "alpha_score": 1.0,  # Placeholder, Log-MPS will calculate real statistical score
                "implementation_alternatives": item.get("implementation_alternatives", []),
            }
        )

    # CR-831: Workspace Isolation
    os.makedirs(run_dir / "data", exist_ok=True)
    default_output = run_dir / "data" / ("portfolio_candidates_raw.json" if mode == "raw" else "portfolio_candidates.json")
    output_file = os.getenv("CANDIDATES_RAW" if mode == "raw" else "CANDIDATES_SELECTED", str(default_output))

    with open(output_file, "w") as f_out:
        json.dump(output_universe, f_out, indent=2)

    # Save audit trail to run dir
    default_audit = run_dir / "data" / "selection_audit.json"
    run_audit_file = os.getenv("SELECTION_AUDIT", str(default_audit))
    with open(run_audit_file, "w") as f_audit:
        json.dump(audit_data, f_audit, indent=2)

    logger.info(f"Saved {len(output_universe)} candidates to {output_file}")
    logger.info(f"Audit log updated: {run_audit_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["raw", "top"], default="raw")
    args = parser.parse_args()
    select_top_universe(mode=args.mode)
