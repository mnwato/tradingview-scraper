import asyncio
import json
import logging
import re
import secrets
import string

import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("async_ws_proto")


def generate_session():
    return "qs_" + "".join(secrets.choice(string.ascii_lowercase) for _ in range(12))


async def test_async_ws():
    uri = "wss://data.tradingview.com/socket.io/websocket?from=chart%2FVEPYsueI%2F&type=chart"
    headers = {"Origin": "https://www.tradingview.com", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(uri, headers=headers) as ws:
                logger.info("Connected to TradingView WebSocket via aiohttp")

                # 1. Handshake
                auth_msg = json.dumps({"m": "set_auth_token", "p": ["unauthorized_user_token"]}, separators=(",", ":"))
                formatted_auth = f"~m~{len(auth_msg)}~m~{auth_msg}"
                await ws.send_str(formatted_auth)
                logger.info("Sent auth token message")

                # 2. Listen
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        raw_data = msg.data
                        parts = [x for x in re.split(r"~m~\d+~m~", raw_data) if x]
                        for p in parts:
                            if p.startswith("~h~"):
                                logger.info(f"Received Heartbeat: {p}")
                                echo_msg = f"~m~{len(p)}~m~{p}"
                                await ws.send_str(echo_msg)
                                logger.info("Echoed Heartbeat")
                            else:
                                logger.info(f"Received Data: {p[:100]}...")
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        break

    except Exception as e:
        logger.error(f"WS Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_async_ws())
