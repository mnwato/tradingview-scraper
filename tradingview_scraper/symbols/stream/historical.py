"""Module providing a two function which return python generator contains trades realtime data."""

import re
import sys
import json
import logging
import signal
from time import sleep
from typing import Optional

from websocket import WebSocketConnectionClosedException

from tradingview_scraper.symbols.stream.stream_handler import StreamHandler
from tradingview_scraper.symbols.stream.utils import (
    validate_symbols,
    fetch_tradingview_indicators,
    display_and_select_indicator,
    fetch_indicator_metadata
)
from tradingview_scraper.symbols.utils import save_json_file, save_csv_file

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class HistoricalData:
    def __init__(self, export_result=False, export_type='json', websocket_jwt_token:str="unauthorized_user_token"):

        self.export_result = export_result
        self.export_type = export_type
        self.data_category = ""
        ws_url = "wss://data.tradingview.com/socket.io/websocket?from=chart%2FVEPYsueI%2F&type=chart"
        self.stream = StreamHandler(websocket_url=ws_url, jwt_token=websocket_jwt_token)


    def _add_symbol_to_sessions(self, quote_session: str, chart_session: str, exchange_symbol: str, numb_candles: int = 10):
        resolve_symbol = json.dumps({"adjustment": "splits", "symbol": exchange_symbol})
        self.stream.send_message("quote_add_symbols", [quote_session, f"={resolve_symbol}"])
        self.stream.send_message("resolve_symbol", [chart_session, "sds_sym_1", f"={resolve_symbol}"])
        self.stream.send_message("create_series", [chart_session, "sds_1", "s1", "sds_sym_1", "1", numb_candles, ""])
        self.stream.send_message("quote_fast_symbols", [quote_session, exchange_symbol])


    def _add_indicator_study(self, indicator_study: dict):
        self.stream.send_message("create_study", indicator_study["p"])
        self.stream.send_message("quote_hibernate_all", [self.stream.quote_session])


    def _serialize_ohlc(self, raw_data):
        ohlc_data = raw_data.get('p', [{},{},{}])[1].get('sds_1', {}).get('s', [])

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


    def ohlc(self,
             exchange: str,
             symbol: str,
             numb_candles: int = 10):
        self.data_category = "ohlc_history"
        exchange_symbol = f"{exchange}:{symbol}"

        validate_symbols(exchange_symbol)
        self._add_symbol_to_sessions(self.stream.quote_session,
                                     self.stream.chart_session,
                                     exchange_symbol,
                                     numb_candles)

        for i, pkt in enumerate(self.get_data()):
            if pkt.get('m') == "timescale_update":
                ohlc_json_data = self._serialize_ohlc(pkt)

                # Save results
                if self.export_result is True:
                    self._export(json_data=ohlc_json_data, symbol=symbol)

                return ohlc_json_data
            elif i>10:
                raise Exception("not found")


    def search_tradingview_indicators(self, query: str):
        indicators = fetch_tradingview_indicators(query)
        return display_and_select_indicator(indicators)


    def _serialize_indicator(self, raw_data: dict):
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
            print(f"Error processing packet: {e}")
            return []


    def indicators(self,
                   exchange: str,
                   symbol: str,
                   indicator_id: Optional[str]=None,
                   indicator_version: Optional[str]=None,
                   indicator_name: Optional[str]=None,
                   ):
        self.data_category = "indicator_history"
        exchange_symbol = f"{exchange}:{symbol}"

        validate_symbols(exchange_symbol)

        if indicator_id is None and indicator_name is None:
            raise ValueError("One of indicator name or indicator id must be pass")

        if not indicator_id:
            indicator_id, indicator_version = self.search_tradingview_indicators(query=indicator_name)

        self._add_symbol_to_sessions(self.stream.quote_session,
                                     self.stream.chart_session,
                                     exchange_symbol=exchange_symbol)

        ind_study = fetch_indicator_metadata(script_id=indicator_id,
                                 script_version=indicator_version,
                                 chart_session=self.stream.chart_session)

        self._add_indicator_study(indicator_study=ind_study)

        catch_flag = False
        for i, pkt in enumerate(self.get_data()):
            if pkt.get('m') == "study_loading":
                catch_flag = True
                continue

            if catch_flag is True:
                ind_json_data = self._serialize_indicator(pkt)

                # Save results
                if self.export_result is True:
                    self._export(json_data=ind_json_data, symbol=symbol)

                return ind_json_data

            elif i>10:
                raise Exception("not found")


    def _export(self, json_data, symbol):
        if self.export_type == "json":
            save_json_file(data=json_data, symbol=symbol, data_category=self.data_category)

        elif self.export_type == "csv":
            save_csv_file(data=json_data, symbol=symbol, data_category=self.data_category)


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
                    result = self.stream.ws.recv()
                    # Check if the result is a heartbeat or actual data
                    if re.match(r"~m~\d+~m~~h~\d+$", result):
                        self.stream.ws.recv()  # Echo back the message
                        logging.debug("Received heartbeat: %s", result)
                        self.stream.ws.send(result)
                    else:
                        split_result = [x for x in re.split(r'~m~\d+~m~', result) if x]
                        for item in split_result:
                            if item:
                                yield json.loads(item)  # Yield parsed JSON data

                except WebSocketConnectionClosedException:
                    logging.error("WebSocket connection closed. Attempting to reconnect...")
                    break  # Handle reconnection logic as needed
                except Exception as e:
                    logging.error("An error occurred: %s", str(e))
                    break  # Handle other exceptions as needed
        finally:
            self.stream.ws.close()


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



# Example Usage
if __name__ == "__main__":
    historical_data = HistoricalData()

    # exchange_symbol = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "FXOPEN:XAUUSD"]  # Example symbol
    exchange_symbol = ["BINANCE:BTCUSDT"]  # Example symbol

    data = historical_data.indicators(exchange="BINANCE", symbol="BTCUSDT", indicator_name="rsi")
    # data = historical_data.ohlc(exchange="BINANCE", symbol="BTCUSDT")

    # Iterate over the generator to get real-time data
    for packet in data:
        print('-'*50)
        print(packet)
