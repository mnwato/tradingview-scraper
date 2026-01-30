import pandas as pd
from pathlib import Path


def inspect_stitched(run_id, filename):
    path = Path(f"artifacts/summaries/runs/{run_id}/data/returns/{filename}")
    if not path.exists():
        print(f"File not found: {path}")
        return

    s = pd.read_pickle(path)
    print(f"--- {filename} ---")
    print(f"Count: {len(s)}")
    print(f"Mean: {s.mean():.6f}")
    print(f"Std:  {s.std():.6f}")
    print(f"Max:  {s.max():.6f}")
    print(f"Min:  {s.min():.6f}")
    print(f"NaNs: {s.isna().sum()}")
    print(f"Stale (0): {(s == 0).sum()}")

    # Calculate Sharpe manually (annualized)
    ann_factor = 365.0
    vol = s.std() * (ann_factor**0.5)
    ret = s.mean() * ann_factor
    sharpe = ret / vol if vol > 1e-12 else 0
    print(f"Manual Ann Vol:    {vol:.2%}")
    print(f"Manual Ann Return: {ret:.2%}")
    print(f"Manual Sharpe:     {sharpe:.4f}")


if __name__ == "__main__":
    inspect_stitched("final_long_all_v4", "custom_cvxportfolio_min_variance.pkl")
    inspect_stitched("final_long_all_v4", "custom_vectorbt_min_variance.pkl")
