import asyncio

import aiohttp


async def debug():
    url = "https://scanner.tradingview.com/crypto/scan"
    payload = {
        "columns": ["close", "volume"],
        "options": {"lang": "en"},
        "range": [0, 10],
    }
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession() as session:
        print(f"Hitting {url}...")
        async with session.post(url, json=payload, headers=headers) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(f"Raw Count: {len(data.get('data', []))}")
            if data.get("data"):
                print(f"First Item: {data['data'][0]}")


if __name__ == "__main__":
    asyncio.run(debug())
