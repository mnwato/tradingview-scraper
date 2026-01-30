import json
import logging

from tradingview_scraper.pipeline import QuantitativePipeline


def run_e2e_v1():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("e2e_v1_runner")

    pipeline = QuantitativePipeline()

    # Target Configs: Top 200 equivalent (using multiple Top 50 exchange configs)
    configs = [
        "configs/crypto_cex_trend_binance_spot_daily_long.yaml",
        "configs/crypto_cex_trend_binance_perp_daily_short.yaml",
        "configs/crypto_cex_trend_okx_spot_daily_long.yaml",
        "configs/crypto_cex_trend_okx_perp_daily_short.yaml",
        "configs/crypto_cex_trend_bybit_spot_daily_long.yaml",
        "configs/crypto_cex_trend_bybit_perp_daily_short.yaml",
        "configs/crypto_cex_trend_bitget_spot_daily_long.yaml",
        "configs/crypto_cex_trend_bitget_perp_daily_short.yaml",
        "configs/us_stocks_trend_momentum.yaml",
        "configs/futures_metals_trend_momentum.yaml",
        "configs/forex_trend_momentum.yaml",
    ]

    print("\n" + "=" * 80)
    print("STARTING FULL END-TO-END QUANTITATIVE PIPELINE (V1)")
    print("=" * 80)

    result = pipeline.run_full_pipeline(configs, limit=20)  # Limit per config for this run

    if result["status"] == "success":
        print("\n" + "=" * 80)
        print("PIPELINE EXECUTION SUCCESSFUL")
        print("=" * 80)
        print(f"Regime Detected : {result['regime']}")
        print(f"Total Signals   : {result['total_signals']}")

        # Save detailed portfolio
        with open("outputs/portfolio_daily_execution.json", "w") as f:
            json.dump(result, f, indent=2)
        print("\nDaily Execution Sheet saved to outputs/portfolio_daily_execution.json")

        # Display top allocations
        portfolio = result["portfolio"]
        print("\nTop Portfolio Allocations:")
        for asset in sorted(portfolio, key=lambda x: x["Weight"], reverse=True)[:10]:
            print(f"  - {asset['Symbol']:<20} | Weight: {asset['Weight']:>6.2%} | Type: {asset['Type']}")
    else:
        print(f"\nPipeline failed with status: {result['status']}")


if __name__ == "__main__":
    run_e2e_v1()
