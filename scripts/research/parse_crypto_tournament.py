import json

import pandas as pd


def parse_tournament_results(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)

    rows = []
    results = data.get("results", {})
    for simulator, engines in results.items():
        for engine, profiles in engines.items():
            if engine == "market":
                continue
            for profile, details in profiles.items():
                summary = details.get("summary")
                if summary:
                    rows.append(
                        {
                            "Simulator": simulator,
                            "Engine": engine,
                            "Profile": profile,
                            "Sharpe": summary.get("sharpe"),
                            "Ann. Return": summary.get("annualized_return"),
                            "Ann. Vol": summary.get("annualized_vol"),
                            "Max DD": summary.get("max_drawdown"),
                            "Sortino": summary.get("sortino"),
                            "Calmar": summary.get("calmar"),
                        }
                    )

    df = pd.DataFrame(rows)
    return df


if __name__ == "__main__":
    file_path = "/home/tommyk/projects/quant/data-sources/market-data/tradingview-scraper/artifacts/summaries/runs/20260108-120529/data/tournament_results.json"
    df = parse_tournament_results(file_path)
    # Filter for interesting profiles and engines
    # Usually we care about the 'custom' or 'cvxportfolio' simulator
    # and the engines like 'skfolio' or 'adaptive'

    # Sort by Sharpe for the 'custom' simulator
    custom_sim = df[df["Simulator"] == "custom"].sort_values("Sharpe", ascending=False)
    print("Tournament Results (Custom Simulator):")
    print(custom_sim.to_markdown(index=False))

    # Check cvxportfolio simulator
    cvx_sim = df[df["Simulator"] == "cvxportfolio"].sort_values("Sharpe", ascending=False)
    print("\nTournament Results (CvxPortfolio Simulator):")
    print(cvx_sim.to_markdown(index=False))
