import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd

from tradingview_scraper.settings import get_settings
from tradingview_scraper.telemetry.exporter import get_forensic_summary_md


def draw_bar(weight: float, max_width: int = 15) -> str:
    """Generates a text-based progress bar."""
    filled = int(min(1.0, weight * 4) * max_width)  # scaled so 25% is full-ish
    return "[" + "█" * filled + " " * (max_width - filled) + "]"


def get_market_category(market: str) -> str:
    """Maps granular market labels to broad asset classes."""
    if market is None:
        return "🌐 OTHER"
    m = str(market).upper()
    if "BOND" in m:
        return "🏛️ BONDS"
    if any(x in m for x in ["BINANCE", "BITGET", "BYBIT", "OKX", "CRYPTO"]):
        return "🪙 CRYPTO"
    if any(x in m for x in ["NASDAQ", "NYSE", "AMEX", "US_STOCKS", "US_ETF"]):
        return "📈 EQUITIES"
    if any(x in m for x in ["FUTURES", "CME", "CBOT", "COMEX", "NYMEX"]):
        return "⛓️ FUTURES"
    if "FOREX" in m:
        return "💱 FOREX"
    if "OANDA" in m or "UNKNOWN" in m:
        return "⛓️ COMMODITIES / CFD"
    return "🌐 OTHER"


def calculate_portfolio_vol(assets: List[Dict[str, Any]], returns_df: Optional[pd.DataFrame]) -> float:
    """Calculates estimated annualized portfolio volatility."""
    if returns_df is None or returns_df.empty:
        return 0.0

    weights_map = {str(a["Symbol"]): float(a["Weight"]) for a in assets}
    # Align with returns columns
    common_symbols = [s for s in weights_map.keys() if s in returns_df.columns]
    if not common_symbols:
        return 0.0

    w = np.array([weights_map[s] for s in common_symbols], dtype=float)
    sub_rets = cast(pd.DataFrame, returns_df[common_symbols])

    # Pre-calculate covariance to avoid linter confusion with chain calls
    cov_matrix = sub_rets.cov()
    annual_cov = cov_matrix.values * 252

    # Portfolio variance: w^T * Cov * w
    port_var = float(np.dot(w.T, np.dot(annual_cov, w)))
    return float(np.sqrt(port_var)) if port_var > 0 else 0.0


def calculate_market_sensitivity(assets: List[Dict[str, Any]], returns_df: Optional[pd.DataFrame]) -> Tuple[float, float]:
    """Calculates Beta and Correlation to SPY benchmark."""
    benchmark = "AMEX:SPY"
    if returns_df is None or returns_df.empty or benchmark not in returns_df.columns:
        return 0.0, 0.0

    weights_map = {str(a["Symbol"]): float(a["Weight"]) for a in assets}
    common_symbols = [s for s in weights_map.keys() if s in returns_df.columns]
    if not common_symbols:
        return 0.0, 0.0

    # Portfolio returns series
    sub_rets = cast(pd.DataFrame, returns_df[common_symbols])
    w = np.array([weights_map[s] for s in common_symbols], dtype=float)
    port_rets = (sub_rets * w).sum(axis=1)

    market_rets = returns_df[benchmark]

    # Align
    combined = pd.concat([port_rets, market_rets], axis=1).dropna()
    if len(combined) < 20:
        return 0.0, 0.0

    p_rets = combined.iloc[:, 0]
    m_rets = combined.iloc[:, 1]

    correlation = float(p_rets.corr(m_rets))

    # Beta = Cov(p, m) / Var(m)
    # Ensure shapes are correct (1D arrays of same length > 1)
    if len(p_rets) > 1 and len(m_rets) > 1:
        cov_matrix = np.cov(p_rets, m_rets)
        if cov_matrix.shape == (2, 2):
            cov = cov_matrix[0, 1]
            var_m = np.var(m_rets, ddof=1)  # Standard sample variance
            beta = float(cov / var_m) if var_m > 1e-12 else 0.0
        else:
            beta = 0.0
    else:
        beta = 0.0

    return beta, correlation


def generate_markdown_report(data_path: str, returns_path: str, candidates_path: str, stats_path: str, output_path: str):
    with open(data_path, "r") as f:
        data = json.load(f)

    candidates = []
    if os.path.exists(candidates_path):
        with open(candidates_path, "r") as f:
            candidates = json.load(f)

    stats_df = None
    if os.path.exists(stats_path):
        stats_df = pd.read_json(stats_path)

    returns_df: Optional[pd.DataFrame] = None
    if os.path.exists(returns_path):
        try:
            if str(returns_path).endswith(".parquet"):
                returns_df = pd.read_parquet(returns_path)
            else:
                raw_rets = pd.read_pickle(returns_path)
                if isinstance(raw_rets, pd.DataFrame):
                    returns_df = raw_rets
        except Exception:
            pass

    profiles = data.get("profiles", {})
    cluster_registry = data.get("cluster_registry", {})

    md = []
    md.append("# 📊 Quantitative Portfolio Analysis Dashboard")
    md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(
        "\n**Quick Links:** [Risk Rationale](./research/antifragile_barbell_rationale.md) | [Cluster Hierarchy](./cluster_analysis.md) | [Decision Audit](./selection_audit.md) | [Tail Hedges](./hedge_anchors.md)"
    )
    md.append("\n---")

    # 0. SYSTEM HEALTH SUMMARY
    md.append("## 🏥 System Health & Integrity")

    # Trace Section (Phase 450)
    # Resolve trace file from output_path's sibling data directory
    trace_file = Path(output_path).parent.parent / "data" / "forensic_trace.json"
    md.append(get_forensic_summary_md(trace_file) + "\n")

    health_status = "✅ HEALTHY"
    if returns_df is not None and not returns_df.empty:
        # Use any profile to count intended assets
        profile_names = list(profiles.keys())
        if profile_names:
            total_assets = len(profiles[profile_names[0]]["assets"])
            coverage = len([s for s in [a["Symbol"] for a in profiles[profile_names[0]]["assets"]] if s in returns_df.columns])
            if coverage < total_assets:
                health_status = f"⚠️ DEGRADED ({coverage}/{total_assets} aligned)"

    md.append(f"- **Data Integrity:** {health_status}")
    md.append(f"- **Regime:** {data.get('optimization', {}).get('regime', {}).get('name', 'UNKNOWN')}")
    md.append(f"- **Lookback:** {len(returns_df) if returns_df is not None else 0} Days")
    md.append("\n---")

    # 1. SHARED CLUSTER REFERENCE (The Implementation Grid)
    md.append("## 🧩 Shared Cluster Reference")
    md.append("Hierarchical clustering groups correlated assets into risk units. 'Lead' is the primary instrument; 'Alt' lists redundant venues.")
    md.append("| Cluster | Primary Sector | Size | Lead Asset | Fragility | Implementation Alts |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

    alt_map = {c["symbol"]: c.get("implementation_alternatives", []) for c in candidates}

    for c_id, c_info in sorted(cluster_registry.items(), key=lambda x: int(x[0])):
        syms = c_info.get("symbols", [])
        sector = c_info.get("primary_sector", "N/A")
        lead = syms[0] if syms else "N/A"

        alts = []
        for s in syms:
            venue_list = alt_map.get(s, [])
            alts.extend([v["symbol"] for v in venue_list])

        unique_exchanges = sorted(list(set([a.split(":")[0] for a in alts])))
        alt_str = ", ".join(unique_exchanges[:2]) + (f" (+{len(unique_exchanges) - 2})" if len(unique_exchanges) > 2 else "")
        if not unique_exchanges:
            alt_str = "-"

        fragility_str = "N/A"
        if stats_df is not None:
            c_stats = stats_df[stats_df["Symbol"].isin(syms)]
            if not c_stats.empty:
                f_score = c_stats["Fragility_Score"].mean()
                icon = "🔴" if f_score > 1.2 else "🟡" if f_score > 0.8 else "🟢"
                fragility_str = f"{icon} {f_score:.2f}"

        md.append(f"| **Cluster {c_id}** | {sector} | {len(syms)} | `{lead}` | {fragility_str} | {alt_str} |")

    md.append("\n---")

    # 2. RISK PROFILES
    for profile_name, profile_data in profiles.items():
        pretty_name = profile_name.replace("_", " ").title()
        assets = profile_data.get("assets", [])
        clusters = profile_data.get("clusters", [])

        # Calculate Stats
        vol = calculate_portfolio_vol(assets, returns_df)
        beta, mkt_corr = calculate_market_sensitivity(assets, returns_df)
        unique_clusters = len(clusters)
        top_3_conc = sum(float(c["Gross_Weight"]) for c in clusters[:3]) if clusters else 0.0

        sorted_assets = sorted(assets, key=lambda x: x["Weight"], reverse=True)
        running_w = 0.0
        top_sectors = set()
        for a in sorted_assets:
            top_sectors.add(a.get("Sector", "N/A"))
            running_w += a["Weight"]
            if running_w >= 0.80:
                break
        sector_diversity = len(top_sectors)

        # Sensitivity Flag
        sensitivity_flag = ""
        if profile_name == "min_variance" and beta > 0.5:
            sensitivity_flag = " ⚠️ AGGRESSIVE BETA"

        md.append(f"\n## 📈 {pretty_name} Profile")
        md.append(
            f"> **Strategy Metrics:** Vol: **{vol:.2%}** | Beta (SPY): **{beta:.2f}**{sensitivity_flag} | Corr (SPY): **{mkt_corr:.2f}**\n"
            f"> **Diversity:** Unique Buckets: **{unique_clusters}** | Sector Diversity: **{sector_diversity}** | Top 3 Conc: **{top_3_conc:.2%}**"
        )

        # Cluster Summary Table
        md.append("\n### 🧩 Risk Bucket Allocation (Clusters)")
        md.append("| Cluster | Gross | Net | Concentration | Lead Asset | Assets | Type | Sectors |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

        for cluster in clusters:
            gross = float(cluster["Gross_Weight"])
            net = float(cluster["Net_Weight"])
            if gross < 0.001:
                continue
            bar = draw_bar(gross)
            lead = f"`{cluster['Lead_Asset']}`"
            count = cluster["Asset_Count"]
            risk_type = cluster.get("Type", "CORE")
            sector = cluster.get("Sectors", "N/A")
            if isinstance(sector, list):
                # Filter out None values and convert to string
                sector = ", ".join([str(s) for s in sector if s is not None])

            md.append(f"| {cluster['Cluster_Label']} | **{gross:.2%}** | {net:+.2%} | `{bar}` | {lead} | {count} | {risk_type} | {sector} |")

        # Asset Class Breakdown
        md.append("\n### 💎 Asset Class Breakdown")

        categorized: Dict[str, List[Dict[str, Any]]] = {}
        for a in assets:
            if a["Weight"] < 0.001:
                continue
            cat = get_market_category(a.get("Market", "UNKNOWN"))
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(a)

        for cat in sorted(categorized.keys()):
            md.append(f"#### {cat}")
            md.append("| Symbol | Description | Cluster | Weight | Bar | Direction | Market |")
            md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

            cat_assets = sorted(categorized[cat], key=lambda x: x["Weight"], reverse=True)
            for asset in cat_assets:
                weight = float(asset["Weight"])
                bar = draw_bar(weight, max_width=10)
                direction = f"**{asset['Direction']}**"
                desc = asset.get("Description", "N/A")
                if desc == "N/A":
                    desc = str(asset["Symbol"]).split(":")[-1]
                if len(desc) > 40:
                    desc = desc[:37] + "..."

                md.append(f"| `{asset['Symbol']}` | {desc} | {asset['Cluster_ID']} | {weight:.2%} | `{bar}` | {direction} | {asset.get('Market', 'UNKNOWN')} |")

        md.append("\n---")

    # 3. CANDIDATE UNIVERSE
    if candidates:
        md.append("\n## 🔍 Trend Filtered Candidate Universe")
        md.append("High-liquidity symbols passing multi-timeframe technical filters.")
        md.append("| Symbol | Market | Direction | ADX | ATR% | Trend |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

        sorted_candidates = sorted(candidates, key=lambda x: (get_market_category(x.get("market", "")), -(x.get("adx") or 0)))

        for c in sorted_candidates:
            adx = float(c.get("adx") or 0)
            close = float(c.get("close") or 0)
            atr = float(c.get("atr") or 0)

            atr_pct = f"{(atr / close) * 100:.2f}%" if close > 0 else "N/A"

            trend_icon = "🔥" if adx > 25 else "📈" if adx > 15 else "➡️"
            market_cat = get_market_category(c.get("market", "UNKNOWN")).split(" ")[0]

            md.append(f"| `{c['symbol']}` | {market_cat} | **{c.get('direction', 'LONG')}** | {adx:.1f} | {atr_pct} | {trend_icon} |")

    with open(output_path, "w") as f:
        f.write("\n".join(md))

    print(f"✅ Prettified report generated at: {output_path}")


if __name__ == "__main__":
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    # Use settings.lakehouse_dir instead of hardcoded strings
    default_optimized = run_dir / "data" / "portfolio_optimized_v2.json"
    if not default_optimized.exists():
        default_optimized = settings.lakehouse_dir / "portfolio_optimized_v2.json"

    default_returns = run_dir / "data" / "returns_matrix.parquet"
    if not default_returns.exists():
        default_returns = settings.lakehouse_dir / "portfolio_returns.pkl"

    default_candidates = run_dir / "data" / "portfolio_candidates.json"
    if not default_candidates.exists():
        default_candidates = settings.lakehouse_dir / "portfolio_candidates.json"

    default_stats = run_dir / "data" / "antifragility_stats.json"
    if not default_stats.exists():
        default_stats = settings.lakehouse_dir / "antifragility_stats.json"

    out_p = settings.run_reports_dir / "portfolio" / "report.md"
    out_p.parent.mkdir(parents=True, exist_ok=True)

    generate_markdown_report(
        os.getenv("OPTIMIZED_FILE", str(default_optimized)),
        os.getenv("RETURNS_MATRIX", str(default_returns)),
        os.getenv("CANDIDATES_SELECTED", str(default_candidates)),
        os.getenv("ANTIFRAGILITY_STATS", str(default_stats)),
        str(out_p),
    )
