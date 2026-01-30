import json
import os

path = "artifacts/summaries/runs/20260109-135050/data/tournament_results.json"
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)

    print(f"Meta: {data['meta']}")
    print("\nOptimized 10-day window results (custom/custom):")
    results = data["results"]["custom"]["custom"]
    for profile, res in results.items():
        if "summary" in res:
            m = res["summary"]
            # print(f"Summary keys: {list(m.keys())}")
            # print(m)
            s = m.get("sharpe", 0)
            r = m.get("annualized_return", m.get("total_return", 0))
            print(f"{profile:15}: {s:.2f} Sharpe | {r:.1%}")


else:
    print("File not found.")
