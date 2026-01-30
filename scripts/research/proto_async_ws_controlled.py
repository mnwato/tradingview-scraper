import asyncio
import json
import logging

import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("async_ws_controlled")


async def test_async_ws_controlled():
    uri = "wss://data.tradingview.com/socket.io/websocket?from=chart%2FVEPYsueI%2F&type=chart"
    headers = {"Origin": "https://www.tradingview.com", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    packet_count = 0
    max_packets = 10  # Stop after 10 data/heartbeat packets

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(uri, headers=headers) as ws:
                logger.info("Connected to TradingView WebSocket")

                # Handshake
                auth_msg = json.dumps({"m": "set_auth_token", "p": ["unauthorized_user_token"]}, separators=(",", ":"))
                formatted_auth = f"~m~{len(auth_msg)}~m~{auth_msg}"
                await ws.send_str(formatted_auth)

                try:
                    while packet_count < max_packets:
                        msg = await asyncio.wait_for(ws.receive(), timeout=30)
                        packet_count += 1
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            raw_data = msg.data
                            if "~h~" in raw_data:
                                logger.info(f"[{packet_count}] Heartbeat received, echoing...")
                                await ws.send_str(raw_data)
                            else:
                                logger.info(f"[{packet_count}] Data received: {raw_data[:50]}...")

                        if packet_count >= max_packets:
                            logger.info(f"Reached max packets ({max_packets}). Stopping.")
                            break
                except asyncio.TimeoutError:
                    logger.warning("Test timed out.")

                await ws.close()
                logger.info("WebSocket closed gracefully.")

    except Exception as e:
        logger.error(f"WS Controlled Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_async_ws_controlled())
