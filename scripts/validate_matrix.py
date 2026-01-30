import json
import logging
from typing import List

import pandas as pd

# Import Simulators
from tradingview_scraper.portfolio_engines.backtest_simulators import CVXPortfolioSimulator, NautilusSimulator, ReturnsSimulator
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("validate_matrix")


def generate_market_weights(symbols: List[str], window_len: int) -> pd.DataFrame:
    """Generates Equal-Weight allocations for the window."""
    dates = pd.date_range("2024-01-01", periods=window_len, freq="D", tz="UTC")
    weight = 1.0 / len(symbols)

    data = []
    # Generate single target vector (static weights)
    # Simulators expect unique Symbol index for target weights
    for sym in symbols:
        data.append({"Date": dates[0], "Symbol": sym, "Weight": weight})

    df = pd.DataFrame(data)
    # Ensure correct format for simulators (Date/Symbol/Weight)
    return df


def generate_synthetic_returns(symbols: List[str], window_len: int) -> pd.DataFrame:
    """Generates synthetic returns (1% daily) for consistency."""
    dates = pd.date_range("2024-01-01", periods=window_len, freq="D", tz="UTC")
    df = pd.DataFrame(0.01, index=dates, columns=symbols)
    return df


def run_shootout():
    logger.info("Starting Simulator Matrix Shootout...")

    # 1. Setup
    symbols = ["ASSET:A", "ASSET:B", "ASSET:C", "ASSET:D", "ASSET:E"]
    window = 60  # 2 months

    returns = generate_synthetic_returns(symbols, window)
    weights = generate_market_weights(symbols, window)

    # Mock Settings to enforce friction parity
    settings = get_settings()
    settings.backtest_slippage = 0.0005  # 5 bps
    settings.backtest_commission = 0.0001  # 1 bps
    settings.features.feat_rebalance_mode = "daily"  # Force daily rebalance to maximize friction impact

    results = {}

    # 2. Run L0: ReturnsSimulator
    logger.info("Running L0: ReturnsSimulator...")
    l0 = ReturnsSimulator()
    res0 = l0.simulate(returns, weights)
    results["L0"] = res0

    # 3. Run L1: CVXPortfolio
    logger.info("Running L1: CVXPortfolioSimulator...")
    l1 = CVXPortfolioSimulator()
    if l1.cvp:
        res1 = l1.simulate(returns, weights)
        results["L1"] = res1
    else:
        logger.warning("CVXPortfolio not available, skipping L1.")

    # 4. Run L2: Nautilus
    logger.info("Running L2: NautilusSimulator...")
    l2 = NautilusSimulator()
    # Nautilus requires more setup (mocking settings usually handled by backtest_engine)
    # But validate_parity.py showed we can run it.
    try:
        res2 = l2.simulate(returns, weights)
        results["L2"] = res2
    except Exception as e:
        logger.error(f"Nautilus failed: {e}")

    # 5. Compare & Report
    report = {"metrics": {}, "divergence": {}}

    for key, res in results.items():
        report["metrics"][key] = {
            "cagr": res.get("annualized_return", 0.0),
            "volatility": res.get("annualized_vol", 0.0),
            "turnover": res.get("turnover", 0.0),
            "sharpe": res.get("sharpe", 0.0),
        }

    # Calculate Divergence vs L0 (Baseline)
    base = report["metrics"].get("L0")
    if base:
        for key in results.keys():
            if key == "L0":
                continue
            tgt = report["metrics"][key]
            div_cagr = abs(tgt["cagr"] - base["cagr"])
            div_to = abs(tgt["turnover"] - base["turnover"])

            report["divergence"][f"{key}_vs_L0"] = {
                "cagr_diff": div_cagr,
                "turnover_diff": div_to,
                "passed": div_cagr < 0.02,  # 2% tolerance
            }

    print(json.dumps(report, indent=2))

    # Save Artifact
    with open("artifacts/audit/simulator_matrix_shootout.json", "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    run_shootout()
