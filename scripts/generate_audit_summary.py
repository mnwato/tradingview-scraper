import json
import os

from tradingview_scraper.settings import get_settings

AUDIT_FILE = "data/lakehouse/selection_audit.json"
OUTPUT_FILENAME = "selection_audit.md"


def generate_summary():
    if not os.path.exists(AUDIT_FILE):
        print("Audit file missing.")
        return

    with open(AUDIT_FILE, "r") as f:
        data = json.load(f)

    md = []
    md.append("# 📝 Selection & Optimization Decision Audit")
    md.append(f"**Audit Timestamp:** {data.get('timestamp', 'N/A')}")
    md.append("\n---")

    # Stage 1: Discovery
    disc = data.get("discovery", {})
    md.append("\n## 🛰️ Stage 1: Discovery & Scans")
    md.append(f"- **Total Files Scanned:** {disc.get('total_scanned_files')}")
    md.append(f"- **Total Raw Symbols Found:** {disc.get('total_symbols_found')}")

    md.append("\n### 📂 Category Breakdown")
    md.append("| Category | Long | Short | Total |")
    md.append("| :--- | :--- | :--- | :--- |")
    for cat, stats in disc.get("categories", {}).items():
        md.append(f"| {cat} | {stats['long']} | {stats['short']} | {stats['total']} |")

    # Stage 2: Merging
    merging = data.get("merging", {})
    md.append("\n## 🧩 Stage 2: Canonical Merging")
    md.append(f"- **Total Unique Economic Identities:** {merging.get('total_unique_identities')}")
    md.append(f"- **Redundant Symbols Merged:** {merging.get('redundant_symbols_merged')}")
    md.append("\n*Note: Redundant symbols are preserved as implementation alternatives.*")

    # Stage 3: Natural Selection
    sel = data.get("selection", {})
    md.append("\n## 🧬 Stage 3: Natural Selection (Clustering)")
    md.append(f"- **Lookbacks Used:** {sel.get('lookbacks_used')}")
    md.append(f"- **Total Selected Winners:** {sel.get('total_selected')}")

    md.append("\n### 🧩 Cluster Selection Rationale")
    md.append("| Cluster | Size | Selected Winners |")
    md.append("| :--- | :--- | :--- |")
    for c_id, c_stats in sorted(sel.get("clusters", {}).items(), key=lambda x: int(x[0])):
        winners = ", ".join([f"`{s}`" for s in c_stats["selected"]])
        md.append(f"| Cluster {c_id} | {c_stats['size']} | {winners} |")

    # Stage 4: Optimization
    opt = data.get("optimization", {})
    if opt:
        md.append("\n## ⚖️ Stage 4: Portfolio Optimization")
        md.append(f"- **Detected Regime:** {opt.get('regime', {}).get('name')} (Score: {opt.get('regime', {}).get('score'):.2f})")
        md.append(f"- **Constraint - Cluster Cap:** {opt.get('constraints', {}).get('cluster_cap'):.1%}")

        md.append("\n### 📈 Profile Summaries")
        md.append("| Profile | Assets | Primary Cluster |")
        md.append("| :--- | :--- | :--- |")
        for name, stats in opt.get("profiles", {}).items():
            md.append(f"| {name.replace('_', ' ').title()} | {stats['assets']} | Cluster {stats['top_cluster']} |")

    settings = get_settings()
    output_dir = settings.run_reports_dir / "selection"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "audit.md"
    with open(output_file, "w") as f:
        f.write("\n".join(md))

    print(f"✅ Audit summary report generated at: {output_file}")


if __name__ == "__main__":
    generate_summary()
