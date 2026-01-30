import json
from collections import defaultdict


def audit_tail_risk_concentration(weights_path: str):
    with open(weights_path, "r") as f:
        data = json.load(f)

    weights = data["weights"]

    # 1. Identity Consolidation
    phys_concentration = defaultdict(float)
    atom_count = len(weights)

    for w in weights:
        symbol = w["Symbol"]
        weight = w["Weight"]

        # Extract physical symbol
        if "_" in symbol:
            phys = symbol.split("_")[0]
        else:
            phys = symbol

        phys_concentration[phys] += weight

    # 2. Report
    print("\n# Meta-Portfolio Concentration Audit")
    print(f"Total Atoms: {atom_count}")
    print(f"Total Physical Assets: {len(phys_concentration)}")
    print("\n## Top 10 Physical Asset Concentration")
    print("| Physical Asset | Total Weight | Status |")
    print("| :--- | :--- | :--- |")

    sorted_phys = sorted(phys_concentration.items(), key=lambda x: x[1], reverse=True)
    for phys, weight in sorted_phys[:10]:
        status = "❌ OVER LIMIT" if weight > 0.15 else "✅ OK"
        print(f"| {phys} | {weight:.2%} | {status} |")

    # 3. Directional Balance
    long_w = sum(w["Weight"] for w in weights if "_long_LONG" in w["Symbol"] or "LONG" in w.get("Direction", ""))
    short_w = sum(w["Weight"] for w in weights if "_short_SHORT" in w["Symbol"] or "SHORT" in w.get("Direction", ""))

    print("\n## Directional Exposure")
    print(f"- **Gross Long:** {long_w:.2%}")
    print(f"- **Gross Short:** {short_w:.2%}")
    print(f"- **Net Exposure:** {long_w - short_w:.2%}")


if __name__ == "__main__":
    audit_tail_risk_concentration("data/lakehouse/portfolio_optimized_meta_hrp.json")
