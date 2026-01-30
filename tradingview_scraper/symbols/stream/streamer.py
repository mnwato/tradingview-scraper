"""
Module providing functions to return a Python generator that contains real-time trades data.

This module connects to a WebSocket to receive real-time market data,
including OHLC (Open, High, Low, Close) data and indicator values.
It offers functionality to export the data in either JSON or CSV formats.

Classes:
    Streamer: Handles the connection and data retrieval from TradingView WebSocket streams.
"""

import json
import logging
import re
import signal
import sys
from datetime import datetime
from time import sleep
from typing import List, Optional, Tuple

from websocket import WebSocketConnectionClosedException

from tradingview_scraper.symbols.exceptions import DataNotFoundError
from tradingview_scraper.symbols.stream import StreamHandler
from tradingview_scraper.symbols.stream.retry import RetryHandler
from tradingview_scraper.symbols.stream.utils import (
    extract_indicator_from_stream,
    extract_ohlc_from_stream,
    fetch_indicator_metadata,
    validate_symbols,
)
from tradingview_scraper.symbols.utils import save_csv_file, save_json_file

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


class Streamer:
    """
    A class to handle streaming of real-time market data from TradingView.

    Attributes:
        export_result (bool): Flag to determine if the result should be exported.
        export_type (str): Type of export (either 'json' or 'csv').
        stream_obj (StreamHandler): The StreamHandler object to handle WebSocket communication.

    Methods:
        stream(exchange, symbol, numb_price_candles, indicator_id, indicator_version):
            Starts the data stream for a given exchange and symbol with optional indicator support.
        get_data():
            Yields parsed real-time data from the TradingView WebSocket connection.
    """

    def __init__(
        self,
        export_result=False,
        export_type="json",
        websocket_jwt_token: str = "unauthorized_user_token",
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        idle_packet_limit: int = 5,
        max_packet_limit: int = 60,
        idle_timeout_seconds: float = 15.0,
    ):
        """
        Initializes the Streamer class with export options and WebSocket authentication token.

        Args:
            export_result (bool): Flag to determine if the result should be exported.
            export_type (str): Type of export ('json' or 'csv').
            websocket_jwt_token (str): WebSocket JWT token for authentication.
            max_retries (int): Maximum number of reconnection attempts.
            initial_delay (float): Initial delay for exponential backoff.
            max_delay (float): Maximum delay for exponential backoff.
            backoff_factor (float): Factor for exponential backoff.
        """
        self.export_result = export_result
        self.export_type = export_type
        self.websocket_jwt_token = websocket_jwt_token
        self.retry_handler = RetryHandler(max_retries=max_retries, initial_delay=initial_delay, max_delay=max_delay, backoff_factor=backoff_factor)
        self.study_id_to_name_map = {}  # Maps study IDs (st9, st10) to indicator names
        self.ws_url = "wss://data.tradingview.com/socket.io/websocket?from=chart%2FVEPYsueI%2F&type=chart"
        self.stream_obj = None
        self.idle_packet_limit = idle_packet_limit
        self.max_packet_limit = max_packet_limit
        self.idle_timeout_seconds = idle_timeout_seconds

        # State for reconnection/subscription tracking
        self._current_subscription = None
        self._current_indicators = None

        # Always start with a fresh connection
        self._reset_stream_handler()

    def _reset_stream_handler(self):
        """Close any existing handler and open a fresh WebSocket."""
        try:
            if self.stream_obj:
                self.stream_obj.close()
        except Exception as e:
            logging.debug("Error closing previous stream handler: %s", e)
        self.stream_obj = StreamHandler(websocket_url=self.ws_url, jwt_token=self.websocket_jwt_token)
        self.study_id_to_name_map = {}
        self._current_subscription = None
        self._current_indicators = None

    def _is_connection_active(self) -> bool:
        """Check whether the current StreamHandler WebSocket is connected."""
        return bool(self.stream_obj and getattr(self.stream_obj, "ws", None) and getattr(self.stream_obj.ws, "connected", False))

    def _add_symbol_to_sessions(self, quote_session: str, chart_session: str, exchange_symbol: str, timeframe: str = "1m", numb_candles: int = 10):
        """
        Adds a symbol to the WebSocket session.

        Args:
            quote_session (str): The session identifier for quotes.
            chart_session (str): The session identifier for charts.
            exchange_symbol (str): The symbol in the format "exchange:symbol".
            timeframe (str): The timeframe for the data (e.g., '1m', '5m'). Default is '1m'.
            numb_candles (int): The number of candles to fetch. Default is 10.
        """
        self._current_subscription = (exchange_symbol, timeframe, numb_candles)
        timeframe_map = {"1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30", "45m": "45", "1h": "60", "2h": "120", "3h": "180", "4h": "240", "1d": "1D", "1w": "1W", "1M": "1M"}
        resolve_symbol = json.dumps({"adjustment": "splits", "symbol": exchange_symbol})

        obj = self.stream_obj
        if obj and hasattr(obj, "send_message"):
            obj.send_message("quote_add_symbols", [quote_session, f"={resolve_symbol}"])
            obj.send_message("resolve_symbol", [chart_session, "sds_sym_1", f"={resolve_symbol}"])
            obj.send_message("create_series", [chart_session, "sds_1", "s1", "sds_sym_1", timeframe_map.get(timeframe, "1"), numb_candles, ""])
            obj.send_message("quote_fast_symbols", [quote_session, exchange_symbol])

    def _add_indicator_study(self, indicator_study: dict):
        """
        Adds an indicator study to the WebSocket session.

        Args:
            indicator_study (dict): The indicator study metadata.
        """
        obj = self.stream_obj
        if obj and hasattr(obj, "send_message"):
            obj.send_message("create_study", indicator_study["p"])
            obj.send_message("quote_hibernate_all", [getattr(obj, "quote_session", "")])

    def _add_indicators(self, indicators: List[Tuple[str, str]]):
        """
        Adds one or more indicators to the WebSocket session.

        Args:
            indicators (list): List of tuples, each containing (indicator_id, indicator_version).
                              Example: [("STD;RSI", "37.0"), ("STD;MACD", "31.0")]
        """
        self._current_indicators = indicators
        obj = self.stream_obj
        if not obj:
            return

        for idx, (indicator_id, indicator_version) in enumerate(indicators):
            logging.info(f"Processing indicator {idx + 1}/{len(indicators)}: {indicator_id} v{indicator_version}")

            chart_session = getattr(obj, "chart_session", "")
            ind_study = fetch_indicator_metadata(script_id=indicator_id, script_version=indicator_version, chart_session=chart_session)

            # Check if indicator metadata was successfully fetched
            if not ind_study or "p" not in ind_study:
                logging.error(f"Failed to fetch metadata for indicator {indicator_id} v{indicator_version}")
                continue

            study_id = f"st{9 + idx}"
            # Modify study ID for additional indicators (st9, st10, st11, etc.)
            ind_study["p"][1] = study_id
            logging.info(f"Assigned study ID '{study_id}' to indicator {indicator_id}")

            # Store full indicator_id as the key (e.g., "STD;RSI")
            self.study_id_to_name_map[study_id] = indicator_id
            logging.debug(f"Stored mapping: {study_id} -> {indicator_id}")

            try:
                self._add_indicator_study(indicator_study=ind_study)
                logging.info(f"Successfully added indicator {indicator_id} v{indicator_version}")
            except Exception as e:
                logging.error(f"Failed to add indicator {indicator_id} v{indicator_version}: {e}")
                continue

    def _extract_ohlc_from_stream(self, pkt: dict):
        return extract_ohlc_from_stream(pkt)

    def _extract_indicator_from_stream(self, pkt: dict):
        return extract_indicator_from_stream(pkt, self.study_id_to_name_map)

    def stream(
        self,
        exchange: str,
        symbol: str,
        timeframe: str = "1m",
        numb_price_candles: int = 10,
        indicators: Optional[List[Tuple[str, str]]] = None,
        auto_close: bool = False,
        total_timeout: Optional[float] = None,
    ):
        """
        Starts streaming data for a given exchange and symbol, with optional indicators.

        Args:
            exchange (str): The exchange to fetch data from.
            symbol (str): The symbol to fetch data for.
            timeframe (str): The timeframe for the data. Default is '1m'.
            numb_price_candles (int): The number of price candles to retrieve. Default is 10.
            indicators (list, optional): List of tuples, each containing (indicator_id, indicator_version).
                                        Example: [("STD;RSI", "37.0"), ("STD;MACD", "31.0")]
            auto_close (bool): If True, closes the connection after the stream is complete. Default is False.
            total_timeout (float, optional): Maximum seconds to spend on this stream.

        Returns:
            dict: A dictionary containing OHLC and indicator data.
        """
        exchange_symbol = f"{exchange}:{symbol}"
        validate_symbols(exchange_symbol)

        ind_flag = bool(indicators)
        start_time = datetime.now()

        # Always start each subscription with a fresh connection to avoid stale state when reusing the Streamer.
        if self._current_subscription is not None or not self._is_connection_active():
            logging.debug("Resetting stream connection before subscribing to %s", exchange_symbol)
            self._reset_stream_handler()

        obj = self.stream_obj
        if obj:
            self._add_symbol_to_sessions(obj.quote_session, obj.chart_session, exchange_symbol, timeframe, numb_price_candles)

        if ind_flag and indicators:
            self._add_indicators(indicators)

        if self.export_result is True:
            ohlc_json_data = []
            indicator_json_data = {}
            expected_indicator_count = len(indicators or []) if ind_flag else 0

            logging.info(f"Starting data collection for {numb_price_candles} candles and {expected_indicator_count} indicators")

            idle_packets = 0
            has_any_data = False
            for i, pkt in enumerate(self.get_data()):
                received_data = self._extract_ohlc_from_stream(pkt)
                received_indicator_data = self._extract_indicator_from_stream(pkt)

                if received_data:
                    ohlc_json_data = received_data
                    has_any_data = True
                    idle_packets = 0
                    logging.debug(f"OHLC data updated: {len(ohlc_json_data)} candles")
                if received_indicator_data:
                    indicator_json_data.update(received_indicator_data)
                    has_any_data = True
                    idle_packets = 0
                    logging.info(f"Indicator data received: {len(indicator_json_data)}/{expected_indicator_count} indicators")

                ohlc_ready = len(ohlc_json_data) >= numb_price_candles
                indicators_ready = not ind_flag or len(indicator_json_data) >= expected_indicator_count

                if ohlc_ready and indicators_ready:
                    break

                # Check total timeout
                if total_timeout:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed >= total_timeout:
                        logging.warning(f"Total timeout ({total_timeout}s) reached for {exchange_symbol}. Returning partial data.")
                        break

                if has_any_data and not received_data and not received_indicator_data:
                    idle_packets += 1

                if has_any_data and idle_packets >= self.idle_packet_limit:
                    logging.warning(
                        "Idle timeout after %s packets without new data. Collected: OHLC=%s, Indicators=%s",
                        idle_packets,
                        len(ohlc_json_data),
                        len(indicator_json_data),
                    )
                    if not ohlc_json_data:
                        raise DataNotFoundError("No 'OHLC' packet found within idle timeout.")
                    break

                if i + 1 >= self.max_packet_limit:
                    logging.warning(
                        "Reached max packet limit (%s). Collected: OHLC=%s, Indicators=%s",
                        self.max_packet_limit,
                        len(ohlc_json_data),
                        len(indicator_json_data),
                    )
                    if not ohlc_json_data:
                        raise DataNotFoundError("No 'OHLC' packet found before max packet limit.")
                    break

            # Check for empty indicator data and log errors
            if ind_flag:
                for indicator_id, _ in indicators or []:
                    if indicator_id not in indicator_json_data:
                        logging.error(f"❌ Unable to scrape indicator: {indicator_id} - No data received")
                    elif not indicator_json_data[indicator_id]:
                        logging.error(f"❌ Unable to scrape indicator: {indicator_id} - Empty data")

            logging.info(f"Data collection complete: {len(ohlc_json_data)} OHLC candles, {len(indicator_json_data)} indicators")

            self._export(json_data=ohlc_json_data, symbol=symbol, data_category="ohlc")
            if ind_flag is True:
                self._export(json_data=indicator_json_data, symbol=symbol, data_category="indicator")

            if auto_close:
                self.close()

            return {"ohlc": ohlc_json_data, "indicator": indicator_json_data}

        return self.get_data()

    def close(self):
        """Closes the WebSocket connection."""
        obj = self.stream_obj
        if obj:
            obj.close()

        self._current_subscription = None
        self._current_indicators = None

    def _export(self, json_data, symbol, data_category):
        """
        Exports data to a specified format (JSON or CSV).

        Args:
            json_data (list): The data to export.
            symbol (str): The symbol for which data is being exported.
            data_category (str): The category of data ('ohlc' or 'indicator').
        """
        if self.export_type == "json":
            save_json_file(data=json_data, symbol=symbol, data_category=data_category)
        elif self.export_type == "csv":
            save_csv_file(data=json_data, symbol=symbol, data_category=data_category)

    def get_data(self):
        """
        Continuously receives data from the TradingView server via the WebSocket connection.

        Yields:
            dict: Parsed JSON data received from the server.
        """
        attempt = 0
        idle_packets = 0
        last_data_time = None
        while True:
            try:
                while True:
                    try:
                        sleep(0.1)
                        obj = self.stream_obj
                        if not (obj and hasattr(obj, "ws") and obj.ws):
                            break
                        result = obj.ws.recv()
                        result_str = result.decode() if isinstance(result, (bytes, bytearray)) else str(result)
                        # Split messages (TradingView sometimes batches them)
                        # Messages look like ~m~<length>~m~<content>
                        # Content can be a heartbeat (~h~<id>) or a JSON object
                        split_result = [x for x in re.split(r"~m~\d+~m~", result_str) if x]

                        if not split_result:
                            idle_packets += 1
                        else:
                            for item in split_result:
                                if not item:
                                    continue

                                if item.startswith("~h~"):
                                    # Handle heartbeat inside split
                                    idle_packets += 1
                                    logging.debug("Received heartbeat: %s (idle_packets=%s/%s)", item, idle_packets, self.idle_packet_limit)
                                    # We need to wrap it in the header to echo back correctly
                                    # But TradingView expects the EXACT same packet for echo
                                    # If it was part of a batch, we'd have to reconstruct it.
                                    # Most heartbeats are single packets matched by re.match above.
                                    # For safety, we just echo the item if it's a heartbeat.
                                    if obj and hasattr(obj, "ws") and obj.ws and hasattr(obj, "prepend_header"):
                                        obj.ws.send(obj.prepend_header(item))
                                    idle_packets += 1
                                else:
                                    try:
                                        parsed = json.loads(item)
                                        idle_packets = 0
                                        last_data_time = datetime.now().timestamp()
                                        yield parsed
                                    except json.JSONDecodeError:
                                        logging.error("Failed to decode JSON packet: %s", item)
                                        idle_packets += 1
                        # Reset attempt counter on successful receive
                        attempt = 0

                        now_ts = datetime.now().timestamp()
                        if last_data_time is None:
                            last_data_time = now_ts
                        if now_ts - last_data_time >= self.idle_timeout_seconds:
                            if last_data_time is not None:
                                logging.warning("Idle timeout reached, but data collected. Stopping stream.")
                                return
                            raise DataNotFoundError("Idle timeout: no data packets received within time limit.")
                        if idle_packets >= self.idle_packet_limit and last_data_time is not None and now_ts - last_data_time >= 1:
                            # Only trigger packet-based idle if we have waited at least 1s since last data
                            logging.debug("Idle limit reached (%s packets, mostly heartbeats). Triggering reconnection.", idle_packets)
                            break

                    except WebSocketConnectionClosedException:
                        logging.error("WebSocket connection closed. Attempting to reconnect...")
                        break
                    except DataNotFoundError:
                        raise
                    except Exception as e:
                        logging.error("An error occurred during receive: %s", str(e))
                        break

                # Reconnection logic
                if attempt >= self.retry_handler.max_retries:
                    logging.error("Max retries reached. Stopping stream.")
                    break

                delay = self.retry_handler.get_delay(attempt)
                logging.info("Waiting %.2f seconds before reconnection attempt %d/%d...", delay, attempt + 1, self.retry_handler.max_retries)
                sleep(delay)
                attempt += 1
                idle_packets = 0
                last_data_time = None

                # Re-establish connection
                self.stream_obj = StreamHandler(websocket_url=self.ws_url, jwt_token=self.websocket_jwt_token)

                # Re-subscribe
                if self._current_subscription:
                    quote_sess = getattr(self.stream_obj, "quote_session", "")
                    chart_sess = getattr(self.stream_obj, "chart_session", "")
                    self._add_symbol_to_sessions(quote_sess, chart_sess, *self._current_subscription)
                if self._current_indicators:
                    self._add_indicators(self._current_indicators)

            except DataNotFoundError:
                raise
            except Exception as e:
                logging.error(f"Failed to reconnect: {e}")
                if attempt >= self.retry_handler.max_retries:
                    break
                attempt += 1
                idle_packets = 0
                last_data_time = None
                sleep(self.retry_handler.get_delay(attempt))


# Signal handler for keyboard interrupt
def signal_handler(sig, frame):
    """
    Handles keyboard interrupt signals to gracefully close the WebSocket connection.

    Args:
        sig: The signal number.
        frame: The current stack frame.
    """
    logging.info("Keyboard interrupt received. Closing WebSocket connection.")
    sys.exit()


# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)
