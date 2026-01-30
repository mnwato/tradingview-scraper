import asyncio
import logging
import os

from tradingview_scraper.pipeline import QuantitativePipeline


async def verify():
    logging.basicConfig(level=logging.INFO)
    pipeline = QuantitativePipeline()

    # Create temp permissive configs
    with open("configs/temp_long.yaml", "w") as f:
        f.write("markets: [crypto]\nexchanges: [BINANCE]\nvolume: {value_traded_min: 0}\nlimit: 5")
    with open("configs/temp_short.yaml", "w") as f:
        f.write("markets: [crypto]\nexchanges: [BINANCE]\nvolume: {value_traded_min: 0}\nlimit: 5")

    configs = ["configs/temp_long.yaml", "configs/temp_short.yaml"]

    try:
        print("\nStarting Parallel Discovery (using temp permissive configs)...")
        signals = await pipeline.run_discovery_async(configs)

        print(f"\nGenerated {len(signals)} signals total.")
        for s in signals:
            print(f"  - {s['symbol']} ({s['direction']})")

        # Cleanup
        if os.path.exists("configs/temp_long.yaml"):
            os.remove("configs/temp_long.yaml")
        if os.path.exists("configs/temp_short.yaml"):
            os.remove("configs/temp_short.yaml")
    except Exception as e:
        print(f"Error: {e}")
        if os.path.exists("configs/temp_long.yaml"):
            os.remove("configs/temp_long.yaml")
        if os.path.exists("configs/temp_short.yaml"):
            os.remove("configs/temp_short.yaml")


if __name__ == "__main__":
    asyncio.run(verify())
