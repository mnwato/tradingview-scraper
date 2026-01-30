import asyncio
import logging

from tradingview_scraper.pipeline import QuantitativePipeline


async def verify():
    logging.basicConfig(level=logging.INFO)
    pipeline = QuantitativePipeline()

    # Using base configs which have lower floors to verify data flow
    configs = ["configs/crypto_cex_base_top50_binance.yaml", "configs/crypto_cex_base_top50_binance_perp.yaml"]

    print("\nStarting Parallel Discovery (using base configs for flow verification)...")
    signals = await pipeline.run_discovery_async(configs, limit=5)

    print(f"\nGenerated {len(signals)} signals total.")
    for s in signals:
        print(f"  - {s['symbol']} ({s['direction']}) | VT: ${s.get('Value.Traded', 0):,.0f}")


if __name__ == "__main__":
    asyncio.run(verify())
