import json
import logging
import os
from pathlib import Path
from typing import Dict, List

import pandas as pd
from tradingview_scraper.symbols.screener import Screener
from tradingview_scraper.utils.technicals import TechnicalRatings
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("feature_parity_audit")


def audit_feature_parity(symbols: List[str]):
    """
    Compares replicated technical ratings against ground truth from TradingView.
    """
    settings = get_settings()
    screener = Screener(export_result=False)

    # 1. Fetch Ground Truth from TradingView Screener
    logger.info(f"Fetching ground truth for {len(symbols)} symbols...")
    cols = ["name", "Recommend.All", "Recommend.MA", "Recommend.Other"]

    # Correct filter for symbols
    filters = [{"left": "name", "operation": "in_range", "right": [s.split(":")[1] for s in symbols]}]

    response = screener.screen(market="crypto", filters=filters, columns=cols, limit=len(symbols))

    if response.get("status") != "success":
        logger.error(f"Failed to fetch ground truth from TradingView: {response.get('error')}")
        return

    gt_data = {f"BINANCE:{r['name']}": r for r in response.get("data", [])}

    # 2. Calculate Replicated Ratings
    audit_results = []
    for symbol in symbols:
        safe_sym = symbol.replace(":", "_")
        ohlcv_path = settings.lakehouse_dir / f"{safe_sym}_1d.parquet"

        if not ohlcv_path.exists():
            logger.warning(f"OHLCV data missing for {symbol} at {ohlcv_path}")
            continue

        df = pd.read_parquet(ohlcv_path)
        # Normalize columns
        df.columns = [c.lower() for c in df.columns]

        replicated = {
            "symbol": symbol,
            "rep_all": TechnicalRatings.calculate_recommend_all(df),
            "rep_ma": TechnicalRatings.calculate_recommend_ma(df),
            "rep_osc": TechnicalRatings.calculate_recommend_other(df),
        }

        gt = gt_data.get(symbol)
        if gt:
            res = {
                "symbol": symbol,
                "replicated": replicated,
                "ground_truth": {"all": gt.get("Recommend.All"), "ma": gt.get("Recommend.MA"), "osc": gt.get("Recommend.Other")},
                "delta": {
                    "all": abs(replicated["rep_all"] - (gt.get("Recommend.All") or 0)),
                    "ma": abs(replicated["rep_ma"] - (gt.get("Recommend.MA") or 0)),
                    "osc": abs(replicated["rep_osc"] - (gt.get("Recommend.Other") or 0)),
                },
            }
            audit_results.append(res)

            logger.info(f"Audit {symbol}: Delta_All={res['delta']['all']:.4f}, Delta_MA={res['delta']['ma']:.4f}")

    # 3. Save Audit Results
    audit_dir = settings.lakehouse_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    out_file = audit_dir / "feature_parity_results.json"

    with open(out_file, "w") as f:
        json.dump(audit_results, f, indent=2)

    logger.info(f"Audit complete. Results saved to {out_file}")

    # 4. Final Summary
    if audit_results:
        from scipy import stats
        import numpy as np

        gt_vec = np.array([r["ground_truth"]["all"] or 0 for r in audit_results])
        rep_vec = np.array([r["replicated"]["rep_all"] or 0 for r in audit_results])

        avg_delta = sum(r["delta"]["all"] for r in audit_results) / len(audit_results)

        # Rank Correlation
        corr, p_val = stats.spearmanr(gt_vec, rep_vec)

        # Sign Accuracy
        sign_match = np.mean(np.sign(gt_vec) == np.sign(rep_vec))

        logger.info(f"--- FINAL SUMMARY ---")
        logger.info(f"Sample Size: {len(audit_results)}")
        logger.info(f"Average Delta (MAE): {avg_delta:.4f}")
        logger.info(f"Rank Correlation: {corr:.4f} (p={p_val:.4f})")
        logger.info(f"Sign Accuracy: {sign_match:.2%}")

        if corr > 0.9:
            logger.info("✅ PASS: Rank Correlation is fit for Alpha Generation.")
        elif avg_delta < 0.05:
            logger.info("✅ PASS: Scalar Parity achieved.")
        else:
            logger.warning("❌ FAIL: Correlation and Parity below thresholds.")


if __name__ == "__main__":
    test_symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT", "BINANCE:BNBUSDT", "BINANCE:XRPUSDT", "BINANCE:AVAXUSDT", "BINANCE:DOGEUSDT", "BINANCE:ADAUSDT", "BINANCE:LINKUSDT"]
    audit_feature_parity(test_symbols)
