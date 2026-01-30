import numpy as np
import pandas as pd


def audit_meta_tail_risk(returns_path: str):
    df = pd.read_pickle(returns_path)

    # Sleeve weights (assuming equal weight for this super-meta test)
    # The report showed 25% each
    w = np.array([0.25, 0.25, 0.25, 0.25])

    # Align columns
    cols = ["long_ma", "short_ma", "long_all", "short_all"]
    available = [c for c in cols if c in df.columns]

    if len(available) < 4:
        print(f"Missing columns: {set(cols) - set(available)}")
        return

    port_rets = (df[available] * 0.25).sum(axis=1)

    skew = port_rets.skew()
    kurt = port_rets.kurtosis()

    print("\n# Meta-Portfolio Tail Risk Audit")
    print(f"- **Skewness:** {skew:.4f} ({'✅ POSITIVE' if skew > 0 else '⚠️ NEGATIVE'})")
    print(f"- **Kurtosis:** {kurt:.4f} ({'✅ STABLE' if kurt < 3 else '⚠️ FAT-TAILED'})")

    # 5% VaR
    var_95 = port_rets.quantile(0.05)
    print(f"- **5% VaR:** {var_95:.2%}")


if __name__ == "__main__":
    audit_meta_tail_risk("data/lakehouse/meta_returns_hrp.pkl")
