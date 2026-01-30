import json
import os

import pandas as pd


def audit_spectral_vetoes():
    returns_path = "data/lakehouse/portfolio_returns.pkl"
    audit_path = "data/lakehouse/selection_audit.json"

    if not os.path.exists(returns_path) or not os.path.exists(audit_path):
        print("Data missing.")
        return

    returns = pd.read_pickle(returns_path)
    with open(audit_path, "r") as f:
        audit = json.load(f)

    selection = audit.get("selection", {})
    vetoes = selection.get("vetoes", {})
    selected = []
    for c in selection.get("clusters", {}).values():
        selected.extend(c.get("selected", []))

    selected = list(set(selected))

    # Calculate returns for selected vs vetoed
    # We use simple average returns for the audit period (assumed to be the full returns matrix)
    mean_returns = returns.mean() * 252  # Annualized

    selected_returns = mean_returns.reindex(selected).dropna()
    vetoed_symbols = list(vetoes.keys())
    vetoed_returns = mean_returns.reindex(vetoed_symbols).dropna()

    print("--- Opportunity Cost Audit ---")
    print(f"Total Selected: {len(selected)} | Avg Annualized Return: {selected_returns.mean():.2%}")
    print(f"Total Vetoed: {len(vetoed_symbols)} | Avg Annualized Return: {vetoed_returns.mean():.2%}")

    # Identify "Missed Alpha" (Vetoed assets with returns > selected average)
    threshold = selected_returns.mean()
    missed_alpha = vetoed_returns[vetoed_returns > threshold]

    print(f"\nMissed Alpha (Vetoed assets > Selected Avg): {len(missed_alpha)}")
    for sym, ret in missed_alpha.sort_values(ascending=False).items():
        reason = vetoes.get(sym, ["Unknown"])[0]
        print(f"- {sym}: {ret:.2%} (Reason: {reason})")


if __name__ == "__main__":
    audit_spectral_vetoes()
