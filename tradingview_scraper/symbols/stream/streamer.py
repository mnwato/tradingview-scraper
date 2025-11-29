"""
Module providing functions to return a Python generator that contains real-time trades data.

This module connects to a WebSocket to receive real-time market data,
including OHLC (Open, High, Low, Close) data and indicator values.
It offers functionality to export the data in either JSON or CSV formats.

Classes:
    Streamer: Handles the connection and data retrieval from TradingView WebSocket streams.
"""

import re
import sys
import json
import logging
import signal
from time import sleep
from typing import Optional, Union, List, Tuple

from websocket import WebSocketConnectionClosedException

from tradingview_scraper.symbols.stream import StreamHandler
from tradingview_scraper.symbols.stream.utils import (
    validate_symbols,
    fetch_indicator_metadata
)
from tradingview_scraper.symbols.utils import save_json_file, save_csv_file
from tradingview_scraper.symbols.exceptions import DataNotFoundError

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


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
        export_type='json',
        websocket_jwt_token:str="unauthorized_user_token"
        ):
        """
        Initializes the Streamer class with export options and WebSocket authentication token.

        Args:
            export_result (bool): Flag to determine if the result should be exported.
            export_type (str): Type of export ('json' or 'csv').
            websocket_jwt_token (str): WebSocket JWT token for authentication.
        """
        self.export_result = export_result
        self.export_type = export_type
        self.study_id_to_name_map = {}  # Maps study IDs (st9, st10) to indicator names
        ws_url = "wss://data.tradingview.com/socket.io/websocket?from=chart%2FVEPYsueI%2F&type=chart"
        self.stream_obj = StreamHandler(websocket_url=ws_url, jwt_token=websocket_jwt_token)

    def _add_symbol_to_sessions(
        self,
        quote_session: str,
        chart_session: str,
        exchange_symbol: str,
        timeframe: str = "1m",
        numb_candles: int = 10
        ):
        """
        Adds a symbol to the WebSocket session.

        Args:
            quote_session (str): The session identifier for quotes.
            chart_session (str): The session identifier for charts.
            exchange_symbol (str): The symbol in the format "exchange:symbol".
            timeframe (str): The timeframe for the data (e.g., '1m', '5m'). Default is '1m'.
            numb_candles (int): The number of candles to fetch. Default is 10.
        """
        timeframe_map = {
            '1m': '1',
            '5m': '5', 
            '15m': '15',
            '30m': '30',
            '1h': '60',
            '2h': '120',
            '4h': '240',
            '1d': '1D',
            '1w': '1W',
            '1M': '1M'
        }
        resolve_symbol = json.dumps({"adjustment": "splits", "symbol": exchange_symbol})
        self.stream_obj.send_message("quote_add_symbols", [quote_session, f"={resolve_symbol}"])
        self.stream_obj.send_message("resolve_symbol", [chart_session,
                                                        "sds_sym_1", f"={resolve_symbol}"])
        self.stream_obj.send_message("create_series", [chart_session,
                                                       "sds_1", "s1", "sds_sym_1", timeframe_map.get(timeframe, "1"),
                                                       numb_candles, ""])
        self.stream_obj.send_message("quote_fast_symbols", [quote_session, exchange_symbol])

    def _add_indicator_study(self, indicator_study: dict):
        """
        Adds an indicator study to the WebSocket session.

        Args:
            indicator_study (dict): The indicator study metadata.
        """
        self.stream_obj.send_message("create_study", indicator_study["p"])
        self.stream_obj.send_message("quote_hibernate_all", [self.stream_obj.quote_session])

    def _add_indicators(self, indicators: List[Tuple[str, str]]):
        """
        Adds one or more indicators to the WebSocket session.

        Args:
            indicators (list): List of tuples, each containing (indicator_id, indicator_version).
                              Example: [("STD;RSI", "37.0"), ("STD;MACD", "31.0")]
        """
        for idx, (indicator_id, indicator_version) in enumerate(indicators):
            logging.info(f"Processing indicator {idx + 1}/{len(indicators)}: {indicator_id} v{indicator_version}")
            
            ind_study = fetch_indicator_metadata(script_id=indicator_id,
                                                 script_version=indicator_version,
                                                 chart_session=self.stream_obj.chart_session)
            
            # Check if indicator metadata was successfully fetched
            if not ind_study or 'p' not in ind_study:
                logging.error(f"Failed to fetch metadata for indicator {indicator_id} v{indicator_version}")
                continue
            
            study_id = f'st{9 + idx}'
            # Modify study ID for additional indicators (st9, st10, st11, etc.)
            ind_study['p'][1] = study_id
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

    def _serialize_ohlc(self, raw_data):
        """
        Serializes OHLC data from the raw packet.

        Args:
            raw_data (dict): The raw data packet.

        Returns:
            list: A list of serialized OHLC data.
        """
        ohlc_data = raw_data.get('p', [{}, {}, {}])[1].get('sds_1', {}).get('s', [])

        json_data = []
        for entry in ohlc_data:
            json_entry = {
                'index': entry['i'],
                'timestamp': entry['v'][0],
                'open': entry['v'][1],
                'high': entry['v'][2],
                'low': entry['v'][3],
                'close': entry['v'][4]
            }
            #some packets may not have volume data to avoid KeyError
            if len(entry['v'][5]) > 5: json_entry["volume"] = entry['v'][5]
            json_data.append(json_entry)
        return json_data

    def _serialize_indicator(self, raw_data: dict):
        """
        Serializes indicator data from the raw packet.

        Args:
            raw_data (dict): The raw data packet.

        Returns:
            list: A list of serialized indicator data or an empty list if an error occurs.
        """
        try:
            indicator_data = raw_data['p'][1]['st9']['st']

            converted_data = []
            for item in indicator_data:
                timestamp, smoothing, close, *other_values = item['v']
                converted_data.append({
                    'index': item['i'],
                    'timestamp': timestamp,
                    "smoothing": smoothing,
                    "close": close
                })

            return converted_data
        except (KeyError, TypeError) as e:
            logging.error("Error processing packet: %s", e)
            return []

    def _extract_ohlc_from_stream(self, pkt: dict):
        """
        Extracts OHLC data from the data stream.

        Args:
            pkt (dict): The incoming packet.

        Raises:
            DataNotFoundError: If no 'OHLC' packet is found within the first 15 packets.
        """
        json_data = []
        if pkt.get('m') == "timescale_update":
            json_data = self._serialize_ohlc(pkt)
        return json_data

    def _extract_indicator_from_stream(self, pkt: dict):
        """
        Extracts indicator data from the data stream for multiple indicators.

        Args:
            pkt (dict): The incoming packet.

        Returns:
            dict: A dictionary with indicator IDs as keys and their data as values.
        """
        indicator_data = {}
        if pkt.get('m') == "du":
            for item in pkt.get('p', []):
                if isinstance(item, dict):
                    for k, v in pkt.get('p')[1].items():
                        if k.startswith('st') and k in self.study_id_to_name_map:
                            if 'st' in v and len(v['st']) > 10:
                                indicator_name = self.study_id_to_name_map[k]
                                json_data = []
                                for val in v['st']:
                                    tmp = {"index": val['i'], "timestamp": val['v'][0]}
                                    tmp.update({str(idx): v for idx, v in enumerate(val['v'][1:])})
                                    json_data.append(tmp)
                                
                                indicator_data[indicator_name] = json_data
                                logging.debug(f"Indicator {indicator_name} (study {k}) data extracted: {len(json_data)} points")

        return indicator_data

    def stream(
        self,
        exchange: str,
        symbol: str,
        timeframe: str = '1m',
        numb_price_candles: int = 10,
        indicators: Optional[List[Tuple[str, str]]] = None
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

        Returns:
            dict: A dictionary containing OHLC and indicator data.
        """
        exchange_symbol = f"{exchange}:{symbol}"
        validate_symbols(exchange_symbol)

        ind_flag = indicators is not None and len(indicators) > 0

        self._add_symbol_to_sessions(self.stream_obj.quote_session,
                                     self.stream_obj.chart_session,
                                     exchange_symbol,
                                     timeframe,
                                     numb_price_candles)

        if ind_flag:
            self._add_indicators(indicators)

        if self.export_result is True:

            ohlc_json_data = []
            indicator_json_data = {}
            expected_indicator_count = len(indicators) if ind_flag else 0
            
            logging.info(f"Starting data collection for {numb_price_candles} candles and {expected_indicator_count} indicators")
            
            for i, pkt in enumerate(self.get_data()):
                # Extract OHLC data
                received_data = self._extract_ohlc_from_stream(pkt)
                if received_data:
                    ohlc_json_data = received_data
                    logging.debug(f"OHLC data updated: {len(ohlc_json_data)} candles")

                # Extract indicator data
                received_indicator_data = self._extract_indicator_from_stream(pkt)
                if received_indicator_data:
                    indicator_json_data.update(received_indicator_data)
                    logging.info(f"Indicator data received: {len(indicator_json_data)}/{expected_indicator_count} indicators")
                
                # Check if we have sufficient data
                ohlc_ready = len(ohlc_json_data) >= numb_price_candles
                indicators_ready = not ind_flag or len(indicator_json_data) >= expected_indicator_count

                # if ind_flag is True and len(ohlc_json_data)>0 and len(indicator_json_data)>0:
                #     break
                # elif ind_flag is False and len(ohlc_json_data)>0:
                #     break

                # Check if we have sufficient data
                if ohlc_ready and indicators_ready:
                    break

                if i > 15:
                    logging.warning(f"Timeout reached after {i} packets. Collected: OHLC={len(ohlc_json_data)}, Indicators={len(indicator_json_data)}")
                    if not ohlc_json_data:
                        raise DataNotFoundError("No 'OHLC' packet found within the timeout period.")
                    break
            
            # Check for empty indicator data and log errors
            if ind_flag:
                for indicator_id, _ in indicators:
                    if indicator_id not in indicator_json_data:
                        logging.error(f"❌ Unable to scrape indicator: {indicator_id} - No data received")
                    elif not indicator_json_data[indicator_id]:
                        logging.error(f"❌ Unable to scrape indicator: {indicator_id} - Empty data")
            
            logging.info(f"Data collection complete: {len(ohlc_json_data)} OHLC candles, {len(indicator_json_data)} indicators")
            
            self._export(json_data=ohlc_json_data, symbol=symbol, data_category="ohlc")
            if ind_flag is True:
                self._export(
                    json_data=indicator_json_data,
                    symbol=symbol,
                    data_category="indicator"
                    )

            return {"ohlc": ohlc_json_data, "indicator": indicator_json_data}

        return self.get_data()

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
        try:
            while True:
                try:
                    sleep(1)
                    result = self.stream_obj.ws.recv()
                    # Check if the result is a heartbeat or actual data
                    if re.match(r"~m~\d+~m~~h~\d+$", result):
                        self.stream_obj.ws.recv()  # Echo back the message
                        logging.debug("Received heartbeat: %s", result)
                        self.stream_obj.ws.send(result)
                    else:
                        split_result = [x for x in re.split(r'~m~\d+~m~', result) if x]
                        for item in split_result:
                            if item:
                                yield json.loads(item)  # Yield parsed JSON data

                except WebSocketConnectionClosedException:
                    logging.error("WebSocket connection closed. Attempting to reconnect...")
                    break
                except Exception as e:
                    logging.error("An error occurred: %s", str(e))
                    break
        finally:
            self.stream_obj.ws.close()


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
