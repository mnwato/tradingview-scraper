import logging
from pathlib import Path
from typing import cast

import pandas as pd

from scripts.backtest_engine import BacktestEngine
from tradingview_scraper.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("grand_tournament")


def run_grand_tournament():
    settings = get_settings()
    bt = BacktestEngine()

    # --- TOURNAMENT DIMENSIONS ---
    selection_modes = ["v2.0", "v2.1", "v3.1", "v3.2", "v3"]
    risk_profiles = ["min_variance", "hrp", "max_sharpe"]
    simulators = ["cvxportfolio"]
    engines = ["custom"]

    logger.info(f"🏆 Initializing Grand Tournament | Selection Modes: {selection_modes}")

    results = []

    # Pre-calculated benchmarks for the whole period
    pool_ew_returns = bt.returns.mean(axis=1)
    spy_returns = bt.returns["AMEX:SPY"] if "AMEX:SPY" in bt.returns.columns else pd.Series(0, index=bt.returns.index)

    for mode in selection_modes:
        logger.info(f"\n🚀 Evaluating Selection Mode: {mode}")

        # Override selection mode in settings
        settings.features.selection_mode = mode

        # Run the engine's tournament logic
        res = bt.run_tournament(train_window=126, test_window=21, step_size=21, profiles=risk_profiles, engines=engines, simulators=simulators)

        # Extract results
        for sim in simulators:
            for eng in engines:
                for prof in risk_profiles:
                    prof_data = res["results"].get(sim, {}).get(eng, {}).get(prof, {})
                    summary = prof_data.get("summary")

                    # Strategy Returns series for Alpha calculation
                    # The res['returns'] dict has keys like 'cvxportfolio_custom_min_variance'
                    ret_key = f"{sim}_{eng}_{prof}"
                    strat_returns_raw = res.get("returns", {}).get(ret_key)

                    if summary and strat_returns_raw is not None:
                        # Strategy returns are returned as pd.Series from run_tournament
                        strat_returns = cast(pd.Series, strat_returns_raw)

                        # Slice benchmarks to match strategy period
                        common_idx = strat_returns.index
                        pool_period = pool_ew_returns.loc[common_idx]
                        spy_period = spy_returns.loc[common_idx]

                        # Cumulative Alpha
                        strat_cum = (1 + strat_returns).prod()
                        pool_cum = (1 + pool_period).prod()
                        spy_cum = (1 + spy_period).prod()

                        selection_alpha = strat_cum - pool_cum
                        spy_alpha = strat_cum - spy_period

                        results.append(
                            {
                                "selection": mode,
                                "risk": prof,
                                "sharpe": summary.get("sharpe", 0),
                                "ann_ret": summary.get("annualized_return", 0),
                                "ann_vol": summary.get("annualized_vol", 0),
                                "mdd": summary.get("max_drawdown", 0),
                                "sel_alpha": selection_alpha,
                                "spy_alpha": spy_alpha,
                                "turnover": summary.get("avg_turnover", 0),
                                "win_rate": summary.get("win_rate", 0),
                            }
                        )

    df_results = pd.DataFrame(results)
    output_dir = Path("artifacts/tournament")
    output_dir.mkdir(parents=True, exist_ok=True)
    df_results.to_csv(output_dir / "grand_tournament_results_v3.csv", index=False)

    print("\n🏁 Grand Tournament Standings (Sorted by Sharpe):")
    print(df_results.sort_values("sharpe", ascending=False).to_string(index=False))


if __name__ == "__main__":
    run_grand_tournament()
