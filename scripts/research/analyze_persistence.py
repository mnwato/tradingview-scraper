import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.predictability import (
    calculate_correlation_structure,
    calculate_half_life,
    calculate_hurst_exponent,
    calculate_memory_depth,
    calculate_trend_duration,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analyze_persistence")


def analyze_persistence():
    settings = get_settings()
    # CR-831: Workspace Isolation - Infer returns path from run context
    run_dir = settings.summaries_runs_dir / settings.run_id if settings.run_id else None

    returns_path = None
    if run_dir:
        returns_path = run_dir / "data" / "returns_matrix.parquet"

    if not returns_path or not returns_path.exists():
        # Fallback to env or legacy lakehouse
        returns_path = Path(os.getenv("PORTFOLIO_RETURNS_PATH", "data/lakehouse/portfolio_returns.pkl"))

    # meta_path is usually not used here, but for isolation:
    # meta_path = Path(os.getenv("PORTFOLIO_META_PATH", "data/lakehouse/portfolio_meta.json"))

    if not returns_path.exists():
        logger.error(f"Returns matrix missing at {returns_path}")
        return

    logger.info(f"Loading returns from {returns_path}")
    if str(returns_path).endswith(".parquet"):
        returns_df = pd.read_parquet(returns_path)
    else:
        returns_df = cast(pd.DataFrame, pd.read_pickle(returns_path))

    if returns_df.empty:
        logger.error("Returns matrix is empty.")
        return

    n_bars = len(returns_df)
    if n_bars < 500:
        logger.warning(f"Lookback is only {n_bars} bars. Specs recommend 500+ for persistence stability.")

    # Reconstruct price paths (normalized to 1.0)
    # Using cumprod of (1 + returns)
    price_df = (1 + returns_df.fillna(0)).cumprod()

    results = []

    def process_symbol(symbol: str):
        try:
            rets = cast(np.ndarray, returns_df[symbol].values)
            prices = cast(np.ndarray, price_df[symbol].values)

            hurst = calculate_hurst_exponent(rets)
            half_life = calculate_half_life(prices)
            duration = calculate_trend_duration(prices, window=50)
            ac_structure = calculate_correlation_structure(rets, max_lags=3)
            memory_depth = calculate_memory_depth(rets)

            # Classification
            regime = "NEUTRAL"
            if hurst > 0.55:
                if ac_structure[1] > 0.05:
                    regime = "STRONG_TREND"
                else:
                    regime = "TRENDING"
            elif hurst < 0.45:
                if ac_structure[1] < -0.05:
                    regime = "STRONG_MR"
                else:
                    regime = "MEAN_REVERTING"

            return {
                "symbol": symbol,
                "hurst": round(hurst, 4),
                "ac_lag1": round(ac_structure[1], 4),
                "memory_depth": memory_depth,
                "half_life": round(half_life, 2) if np.isfinite(half_life) else None,
                "trend_duration": duration,
                "regime": regime,
                "persistence_score": round(hurst * (1 + np.log1p(duration / 100)), 4) if hurst > 0.5 else round((1 - hurst) / (1 + np.log1p(max(0, half_life))), 4),
            }
        except Exception as e:
            logger.error(f"Failed to process {symbol}: {e}")
            return None

    logger.info(f"Processing {len(returns_df.columns)} symbols...")
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        futures = [executor.submit(process_symbol, str(s)) for s in returns_df.columns]
        for f in futures:
            res = f.result()
            if res:
                results.append(res)

    # Sort by persistence score
    results.sort(key=lambda x: x["persistence_score"], reverse=True)

    # Save JSON
    # CR-831: Workspace Isolation - Save to run data if available
    out_json = Path("data/lakehouse/persistence_metrics.json")
    if run_dir:
        out_json = run_dir / "data" / "persistence_metrics.json"

    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved metrics to {out_json}")

    # Generate Report
    if run_dir:
        report_path = run_dir / "reports" / "research" / "persistence_report.md"
    else:
        report_path = settings.prepare_summaries_run_dir() / "persistence_report.md"

    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Persistence & Duration Analysis (v2 - AC Enhanced)",
        f"Analyzed {len(results)} assets over {n_bars} bars.",
        "",
        "## Top Persistent Trends (Hurst > 0.55)",
        "| Symbol | Hurst | AC(1) | Memory | Duration | Score |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    trends = [r for r in results if "TREND" in r["regime"]]
    for r in trends[:15]:
        lines.append(f"| {r['symbol']} | {r['hurst']} | {r['ac_lag1']} | {r['memory_depth']} | {r['trend_duration']} | {r['persistence_score']} |")

    lines.extend(
        [
            "",
            "## Strongest Mean Reverters (Hurst < 0.45)",
            "| Symbol | Hurst | AC(1) | Half-Life | Score |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
    )

    mrs = [r for r in results if "MR" in r["regime"]]
    mrs.sort(key=lambda x: x["persistence_score"], reverse=True)
    for r in mrs[:15]:
        lines.append(f"| {r['symbol']} | {r['hurst']} | {r['ac_lag1']} | {r['half_life']} | {r['persistence_score']} |")

    report_path.write_text("\n".join(lines))
    logger.info(f"Report generated at {report_path}")


if __name__ == "__main__":
    analyze_persistence()
