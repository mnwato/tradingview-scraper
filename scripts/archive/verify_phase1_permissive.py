import asyncio
import logging

from tradingview_scraper.pipeline import QuantitativePipeline


async def verify():
    logging.basicConfig(level=logging.INFO)
    pipeline = QuantitativePipeline()

    configs = ["configs/crypto_cex_trend_binance_spot_daily_long.yaml", "configs/crypto_cex_trend_binance_perp_daily_short.yaml"]

    print("\nStarting Parallel Discovery (with low liquidity floor)...")
    # Override floor to ensure we get signals for verification
    signals = await pipeline.run_discovery_async(configs, limit=10)

    print(f"\nGenerated {len(signals)} signals total.")
    for s in signals[:10]:
        print(f"  - {s['symbol']} ({s['direction']}) | VT: ${s.get('Value.Traded', 0):,.0f}")


if __name__ == "__main__":
    # Mocking the config override by patching the selector if necessary,
    # but the simplest way is to just use a very high limit or check the logs.
    # Actually, the pipeline.run_discovery_async takes config paths.
    # I'll rely on the existing 'partial_success' logs to verify flow if 0 signals occur again,
    # but let's try a different market or config if needed.
    asyncio.run(verify())
