import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


def generate_selection_report(
    audit_path: str = "data/lakehouse/selection_audit.json",
    output_path: str = "selection_audit.md",
    audit_data: Optional[Dict[str, Any]] = None,
):
    """
    Generates a markdown report summarizing the universe selection process.
    """
    path = Path(audit_path)
    if not path.exists():
        print(f"Selection audit not found at {path}")
        return

    try:
        with open(path, "r") as f:
            full_data = json.load(f)
            # Handle nested 'selection' key if present
            data = full_data.get("selection", full_data)
            # Fallback for candidates if missing in 'selection' but present in root
            if "candidates" not in data and "candidates" in full_data:
                data["candidates"] = full_data["candidates"]
            # Inject selection mode from root if missing
            if "selection_mode" not in data and "final_selection" in full_data:
                data["selection_mode"] = full_data["final_selection"].get("mode")
    except Exception as e:
        print(f"Failed to load selection audit: {e}")
        return

    md = ["# Universe Selection Report", f"Source: `{audit_path}`", ""]

    # 1. Selection Metadata
    md.append("## 1. Selection Context")
    md.append(f"- **Selection Mode**: {data.get('selection_mode', 'N/A')}")
    md.append(f"- **Lookback Days**: {data.get('lookback_days', 'N/A')}")
    md.append(f"- **Lookback Windows**: {data.get('lookbacks_used', data.get('lookbacks', []))}")
    md.append(f"- **Total Candidates**: {data.get('total_raw_symbols', len(data.get('candidates', [])))}")
    md.append(f"- **Selected Winners**: {data.get('total_selected', len(data.get('winners', [])))}")
    md.append("")

    # 2. Winners Table
    if "winners" in data:
        md.append("## 2. Selected Winners")
        winners = data["winners"]
        if winners:
            # Try to enrich with metadata if available in 'candidates' list
            candidate_map = {c["symbol"]: c for c in data.get("candidates", []) if isinstance(c, dict) and "symbol" in c}

            rows = []
            for sym in winners:
                if not isinstance(sym, str):
                    continue
                c_info = candidate_map.get(sym, {})
                rows.append(
                    {
                        "Symbol": sym,
                        "Sector": c_info.get("sector", "N/A"),
                        "Asset Class": c_info.get("asset_class", "N/A"),
                        "Direction": c_info.get("direction", "LONG"),
                    }
                )

            if rows:
                df = pd.DataFrame(rows)
                md.append(str(df.to_markdown(index=False)))
        else:
            md.append("No winners selected.")
    md.append("")

    # 3. Vetoed Assets
    if "vetoes" in data:
        md.append("## 3. Selection Vetoes")
        vetoes = data["vetoes"]
        if vetoes:
            md.append(f"Total Vetoes: {len(vetoes)}")
            # If vetoes is a dict of symbol -> reason
            if isinstance(vetoes, dict):
                v_rows = [{"Symbol": s, "Reason": r} for s, r in vetoes.items()]
                md.append(str(pd.DataFrame(v_rows).to_markdown(index=False)))
            else:
                for v in vetoes:
                    md.append(f"- {str(v)}")

        else:
            md.append("No assets were vetoed.")
        md.append("")

    # 4. Comparison (if history exists)
    history = full_data.get("selection_history", {})
    if len(history) > 1:
        md.append("## 4. Selection Spec Comparison")
        comp_rows = []
        all_syms = set()
        for mode_name, mode_data in history.items():
            all_syms.update(mode_data.get("metrics", {}).get("alpha_scores", {}).keys())

        # Sort symbols for readability
        sorted_syms = sorted(list(all_syms))

        md.append("| Symbol | " + " | ".join([f"Score ({m})" for m in history.keys()]) + " |")
        md.append("| :--- | " + " | ".join([":---:" for _ in history.keys()]) + " |")

        for sym in sorted_syms:
            scores = []
            for mode_name in history.keys():
                s = history[mode_name].get("metrics", {}).get("alpha_scores", {}).get(sym, "N/A")
                if isinstance(s, float):
                    scores.append(f"{s:.4f}")
                else:
                    scores.append(str(s))
            md.append(f"| `{sym}` | " + " | ".join(scores) + " |")
        md.append("")

    # Write output
    try:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w") as f:
            f.write("\n".join(md))
        print(f"Selection report saved to {output_path}")
    except Exception as e:
        print(f"Failed to write selection report: {e}")


if __name__ == "__main__":
    # For standalone testing
    generate_selection_report()
