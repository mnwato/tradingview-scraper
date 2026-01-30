import argparse
import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from tqdm import tqdm

from tradingview_scraper.regime import MarketRegimeDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("research_regime_direction")


class RegimeDirectionResearch:
    def __init__(self):
        self.detector = MarketRegimeDetector(enable_audit_log=False)

    def analyze_symbol(self, symbol: str, returns: pd.Series, lookahead_days: List[int] = [5, 10, 20]) -> List[Dict]:
        """
        Rolling analysis of regime vs future returns.
        """
        results = []
        window_size = 64  # Requirement for turbulence
        stride = 5  # Optimization: check every 5 days

        if len(returns) < window_size + max(lookahead_days):
            return []

        # Pre-calculate rolling forward returns
        fwd_returns = {}
        for d in lookahead_days:
            # Shift backwards to align T with T+d return
            # Rolling sum of log returns? Or product of simple returns?
            # Returns matrix is simple returns usually.
            # (1+r).rolling(d).apply(np.prod) - 1
            # But simple rolling sum is good approximation for small returns.
            # Let's be precise:
            fwd_returns[d] = (1 + returns).rolling(window=d).apply(np.prod, raw=True).shift(-d) - 1

        # Iterate
        indices = range(window_size, len(returns) - max(lookahead_days), stride)

        for i in indices:
            # Context window for Regime
            hist_window = returns.iloc[i - window_size : i]

            # Detect Regime
            try:
                df_slice = pd.DataFrame({"asset": hist_window})
                regime, score, quadrant = self.detector.detect_regime(df_slice)
            except Exception:
                continue

            date = returns.index[i]

            row = {
                "date": date,
                "symbol": symbol,
                "regime": regime,
                "score": score,
                "quadrant": quadrant,
            }

            # Add future returns
            for d in lookahead_days:
                val = fwd_returns[d].iloc[i]
                row[f"fwd_ret_{d}d"] = val

            results.append(row)

        return results

    def run(self, returns_path: Path, output_path: Path):
        """
        Main execution flow.
        """
        if not returns_path.exists():
            logger.error(f"Returns file not found: {returns_path}")
            return

        logger.info(f"Loading returns from {returns_path}...")
        if str(returns_path).endswith(".parquet"):
            returns_df = pd.read_parquet(returns_path)
        else:
            returns_df = pd.read_pickle(returns_path)

        logger.info(f"Loaded {returns_df.shape[1]} symbols, {returns_df.shape[0]} days.")

        # Select subset for speed if needed? Or run full if parallelized.
        # Let's pick top 20 symbols by non-null count (liquidity proxy)
        valid_counts = returns_df.notna().sum().sort_values(ascending=False)
        top_symbols = valid_counts.head(50).index.tolist()

        logger.info(f"Analyzing top {len(top_symbols)} symbols...")

        all_results = []

        for sym in tqdm(top_symbols):
            try:
                series = returns_df[sym].dropna()
                if len(series) < 100:
                    continue
                res = self.analyze_symbol(sym, series)
                all_results.extend(res)
            except Exception as e:
                logger.error(f"Error processing {sym}: {e}")

        if not all_results:
            logger.warning("No results generated.")
            return

        df_res = pd.DataFrame(all_results)

        # Ensure output dir
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_res.to_parquet(output_path)
        logger.info(f"Saved research data to {output_path}")

        # Generate Summary Report
        self.generate_report(df_res, output_path.parent / "regime_direction_report.md")

    def generate_report(self, df: pd.DataFrame, report_path: Path):
        """
        Generates Markdown report with conditional expectations.
        """
        lines = ["# Regime Directional Efficacy Report", "\n"]

        lines.append(f"**Sample Size**: {len(df)} observations across {df['symbol'].nunique()} assets.\n")

        # 1. Regime Distribution
        dist = df["regime"].value_counts(normalize=True)
        lines.append("## 1. Regime Distribution")
        lines.append(dist.to_markdown())
        lines.append("\n")

        # 2. Conditional Returns (Forward 10d)
        lines.append("## 2. Conditional Forward Returns (10-Day)")

        # Group by Regime
        grp = df.groupby("regime")["fwd_ret_10d"].agg(["mean", "median", "std", "count"])
        # Win Rate (>0)
        grp["win_rate"] = df.groupby("regime")["fwd_ret_10d"].apply(lambda x: (x > 0).mean())

        lines.append(grp.to_markdown())
        lines.append("\n")

        # 3. Conditional Returns (Quadrant)
        lines.append("## 3. Conditional Forward Returns (Quadrant)")
        grp_q = df.groupby("quadrant")["fwd_ret_10d"].agg(["mean", "median", "count"])
        grp_q["win_rate"] = df.groupby("quadrant")["fwd_ret_10d"].apply(lambda x: (x > 0).mean())
        lines.append(grp_q.to_markdown())
        lines.append("\n")

        # 4. Extreme Score Analysis (>1.5)
        lines.append("## 4. Extreme Score Analysis (Score > 1.5)")
        extreme = df[df["score"] > 1.5]
        if not extreme.empty:
            stats = extreme["fwd_ret_10d"].agg(["mean", "median", "count"])
            wr = (extreme["fwd_ret_10d"] > 0).mean()
            lines.append(f"- **Mean Return**: {stats['mean']:.2%}")
            lines.append(f"- **Win Rate**: {wr:.1%}")
            lines.append(f"- **Count**: {stats['count']}")
        else:
            lines.append("No extreme scores found.")

        with open(report_path, "w") as f:
            f.write("\n".join(lines))

        logger.info(f"Report generated at {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--returns", default="data/lakehouse/returns_matrix.parquet")
    parser.add_argument("--output", default="data/research/regime_direction.parquet")
    args = parser.parse_args()

    researcher = RegimeDirectionResearch()
    researcher.run(Path(args.returns), Path(args.output))
