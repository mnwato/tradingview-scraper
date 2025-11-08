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
from typing import Optional

from websocket import WebSocketConnectionClosedException

from tradingview_scraper.symbols.stream import StreamHandler
from tradingview_scraper.symbols.stream.utils import (
    validate_symbols,
    fetch_indicator_metadata
)
from tradingview_scraper.symbols.utils import save_json_file, save_csv_file
from tradingview_scraper.symbols.exceptions import DataNotFoundError
from tradingview_scraper.utils import OHLCVConverter

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
        ws_url = "wss://data.tradingview.com/socket.io/websocket?from=chart%2FVEPYsueI%2F&type=chart"
        self.stream_obj = StreamHandler(websocket_url=ws_url, jwt_token=websocket_jwt_token)

    def _add_symbol_to_sessions(
        self,
        quote_session: str,
        chart_session: str,
        exchange_symbol: str,
        numb_candles: int = 10
        ):
        """
        Adds a symbol to the WebSocket session.

        Args:
            quote_session (str): The session identifier for quotes.
            chart_session (str): The session identifier for charts.
            exchange_symbol (str): The symbol in the format "exchange:symbol".
            numb_candles (int): The number of candles to fetch. Default is 10.
        """
        resolve_symbol = json.dumps({"adjustment": "splits", "symbol": exchange_symbol})
        self.stream_obj.send_message("quote_add_symbols", [quote_session, f"={resolve_symbol}"])
        self.stream_obj.send_message("resolve_symbol", [chart_session,
                                                        "sds_sym_1", f"={resolve_symbol}"])
        self.stream_obj.send_message("create_series", [chart_session,
                                                       "sds_1", "s1", "sds_sym_1", "1",
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

    def _add_indicator(self, indicator_id: Optional[str] = None, indicator_version: Optional[str] = None):
        """
        Adds an indicator to the WebSocket session using the provided indicator ID and version.

        Args:
            indicator_id (str, optional): The indicator's ID.
            indicator_version (str, optional): The indicator's version.
        """
        ind_study = fetch_indicator_metadata(script_id=indicator_id,
                                             script_version=indicator_version,
                                             chart_session=self.stream_obj.chart_session)
        self._add_indicator_study(indicator_study=ind_study)

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
                'close': entry['v'][4],
                'volume': entry['v'][5]
            }
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
        Extracts indicator data from the data stream.

        Args:
            pkt (dict): The incoming packet.

        Returns:
            list: A list of indicator data.
        """
        json_data = []
        if pkt.get('m') == "du":
            for item in pkt.get('p', []):
                if isinstance(item, dict):
                    for k, v in pkt.get('p')[1].items():
                        if k.startswith('st') or k.startswith('sds'):
                            if 'st' in v and len(v['st']) > 10:
                                for val in v['st']:
                                    tmp = {"index": val['i'], "timestamp": val['v'][0]}
                                    tmp.update({str(idx): v for idx, v in enumerate(val['v'][1:])})
                                    json_data.append(tmp)

        return json_data

    def stream(
        self,
        exchange: str,
        symbol: str,
        timeframe: str = '1m',
        numb_price_candles: int = 10,
        indicator_id: Optional[str] = None,
        indicator_version: Optional[str] = None
        ):
        """
        Starts streaming data for a given exchange and symbol, with optional indicators.

        Args:
            exchange (str): The exchange to fetch data from.
            symbol (str): The symbol to fetch data for.
            numb_price_candles (int): The number of price candles to retrieve. Default is 10.
            indicator_id (str, optional): The indicator's ID.
            indicator_version (str, optional): The indicator's version.

        Returns:
            dict: A dictionary containing OHLC and indicator data.
        """
        exchange_symbol = f"{exchange}:{symbol}"
        validate_symbols(exchange_symbol)

        tf_converter = OHLCVConverter(target_timeframe=timeframe)

        if indicator_id is not None and indicator_version is not None:
            ind_flag = True
        elif indicator_id is None and indicator_version is None:
            ind_flag = False
        else:
            raise ValueError("Both 'indicator_id' and 'indicator_version' "
                             "must be provided together.")

        self._add_symbol_to_sessions(self.stream_obj.quote_session,
                                     self.stream_obj.chart_session,
                                     exchange_symbol,
                                     numb_price_candles)

        if ind_flag is True:
            self._add_indicator(indicator_id, indicator_version)

        if self.export_result is True:

            ohlc_json_data = []
            indicator_json_data = []
            for i, pkt in enumerate(self.get_data()):

                if not ohlc_json_data:
                    ohlc_json_data = self._extract_ohlc_from_stream(pkt)

                if not indicator_json_data:
                    indicator_json_data = self._extract_indicator_from_stream(pkt)

                if ind_flag is True and len(ohlc_json_data)>0 and len(indicator_json_data)>0:
                    break
                elif ind_flag is False and len(ohlc_json_data)>0:
                    break

                if i > 15:
                    raise DataNotFoundError("No 'OHLC' packet found within the first 15 packets.")

            ohlc_json_data = tf_converter.convert(ohlc_json_data)
            self._export(json_data=ohlc_json_data, symbol=symbol, data_category="ohlc")
            if ind_flag is True:
                indicator_json_data = tf_converter.convert(indicator_json_data)
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
