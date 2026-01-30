import asyncio
import json
import logging
import secrets
import string
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class AsyncStreamHandler:
    """
    Asynchronous class for managing a WebSocket connection to TradingView.
    """

    def __init__(self, websocket_url: str, jwt_token: str = "unauthorized_user_token"):
        self.websocket_url = websocket_url
        self.jwt_token = jwt_token
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.quote_session = ""
        self.chart_session = ""
        self.data_queue = asyncio.Queue()
        self._listen_task: Optional[asyncio.Task] = None

        self.request_header = {
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "Upgrade",
            "Host": "data.tradingview.com",
            "Origin": "https://www.tradingview.com",
            "Pragma": "no-cache",
            "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
            "Upgrade": "websocket",
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        }

    async def connect(self):
        """
        Establishes the WebSocket connection and initializes sessions.
        """
        if self.session is None:
            self.session = aiohttp.ClientSession()

        self.ws = await self.session.ws_connect(self.websocket_url, headers=self.request_header)
        await self._initialize()

    async def _initialize(self):
        """
        Generates session IDs and sends initialization messages.
        """
        self.quote_session = self.generate_session(prefix="qs_")
        self.chart_session = self.generate_session(prefix="cs_")
        logger.info(f"Quote session: {self.quote_session}, Chart session: {self.chart_session}")

        await self._initialize_sessions(self.quote_session, self.chart_session, self.jwt_token)

    def generate_session(self, prefix: str) -> str:
        random_string = "".join(secrets.choice(string.ascii_lowercase) for _ in range(12))
        return prefix + random_string

    def prepend_header(self, message: str) -> str:
        return f"~m~{len(message)}~m~{message}"

    def _extract_packets(self, raw_data: str) -> list[tuple[str, str]]:
        packets: list[tuple[str, str]] = []
        i = 0
        while i < len(raw_data):
            if not raw_data.startswith("~m~", i):
                break
            start = i
            i += 3
            header_end = raw_data.find("~m~", i)
            if header_end == -1:
                break
            length_str = raw_data[i:header_end]
            if not length_str.isdigit():
                break
            length = int(length_str)
            i = header_end + 3
            payload = raw_data[i : i + length]
            packets.append((raw_data[start : i + length], payload))
            i += length

        if packets:
            return packets
        return [(raw_data, raw_data)]

    def construct_message(self, func: str, param_list: list) -> str:
        return json.dumps({"m": func, "p": param_list}, separators=(",", ":"))

    def create_message(self, func: str, param_list: list) -> str:
        return self.prepend_header(self.construct_message(func, param_list))

    async def send_message(self, func: str, args: list):
        if self.ws:
            message = self.create_message(func, args)
            logger.debug(f"Sending message: {message}")
            await self.ws.send_str(message)

    async def _initialize_sessions(self, quote_session: str, chart_session: str, jwt_token: str):
        await self.send_message("set_auth_token", [jwt_token])
        await self.send_message("set_locale", ["en", "US"])
        await self.send_message("chart_create_session", [chart_session, ""])
        await self.send_message("quote_create_session", [quote_session])
        await self.send_message("quote_set_fields", [quote_session, *self._get_quote_fields()])
        await self.send_message("quote_hibernate_all", [quote_session])

    def _get_quote_fields(self) -> list:
        return [
            "ch",
            "chp",
            "current_session",
            "description",
            "local_description",
            "language",
            "exchange",
            "fractional",
            "is_tradable",
            "lp",
            "lp_time",
            "minmov",
            "minmove2",
            "original_name",
            "pricescale",
            "pro_name",
            "short_name",
            "type",
            "update_mode",
            "volume",
            "currency_code",
            "rchp",
            "rtc",
        ]

    async def start_listening(self):
        """
        Starts the background task to listen for messages and handle heartbeats.
        """
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self):
        heartbeat_count = 0
        while True:
            if not self.ws or self.ws.closed:
                break

            try:
                msg = await self.ws.receive()

                if msg.type == aiohttp.WSMsgType.TEXT:
                    raw_data = msg.data

                    packets = self._extract_packets(raw_data)
                    if not packets:
                        continue

                    has_data = False
                    for packet, payload in packets:
                        if payload.startswith("~h~"):
                            logger.debug(f"Received heartbeat: {payload}, echoing back")
                            await self.ws.send_str(packet)
                            heartbeat_count += 1
                        else:
                            try:
                                await self.data_queue.put(json.loads(payload))
                                has_data = True
                            except json.JSONDecodeError:
                                logger.error(f"Failed to decode message: {payload}")

                    if has_data:
                        heartbeat_count = 0

                    if heartbeat_count >= 5:
                        logger.warning("Received 5 consecutive heartbeats without data. Triggering reconnection.")
                        break

                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSING):
                    break
            except Exception as e:
                logger.error(f"Error in async listen loop: {e}")
                break

        await self.data_queue.put(None)  # Signal end of stream/connection lost

    async def get_next_message(self) -> Dict[str, Any]:
        """
        Retrieves the next data message from the queue.
        """
        return await self.data_queue.get()

    async def close(self):
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
