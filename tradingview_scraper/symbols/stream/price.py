"""Module providing a two function which return python generator contains trades realtime data."""

import re
import json
from typing import List
import string
import logging
import signal
import time
from time import sleep
import secrets

from websocket import create_connection, WebSocketConnectionClosedException
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class RealTimeData:
    def __init__(self):
        """
        Initializes the RealTimeData class, setting up the WebSocket connection 
        and request headers for TradingView data streaming.
        """
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
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
        }
        self.ws_url = "wss://data.tradingview.com/socket.io/websocket?from=screener%2F&date={date}"
        self.ws_url = "wss://data.tradingview.com/socket.io/websocket?from=screener%2F"
        self.validate_url = "https://scanner.tradingview.com/symbol?symbol={exchange}%3A{symbol}&fields=market&no_404=false"
        self.ws = create_connection(self.ws_url, headers=self.request_header)

    def validate_symbols(self, exchange_symbol):
        """
        Validates the provided exchange symbols.

        Args:
            exchange_symbol (str or list): A single symbol or a list of symbols 
                                            in the format 'EXCHANGE:SYMBOL'.

        Raises:
            Exception: If the symbol format is invalid or if the symbol is not valid.

        Returns:
            bool: True if all symbols are valid.
        """
        if not exchange_symbol:
            raise ValueError("exchange_symbol could not be empty")
        
        if isinstance(exchange_symbol, str):
            exchange_symbol = [exchange_symbol]
            
        for item in exchange_symbol:
            if len(item.split(':')) != 2:
                raise ValueError(f"Invalid symbol format '{item}'. Must be like 'BINANCE:BTCUSDT'")

            exchange, symbol = item.split(':')
            retries = 3
            for attempt in range(retries):
                try:
                    res = requests.get(self.validate_url.format(exchange=exchange, symbol=symbol), timeout=5)
                    res.raise_for_status()
                    break  # Exit the retry loop on success

                except requests.RequestException as e:
                    if res.status_code == 404:
                        raise ValueError(f"Invalid exchange:symbol '{item}' after {retries} attempts") from e

                    logging.warning("Attempt %d failed to validate exchange:symbol '%s': %s", attempt + 1, item, e)

                    if attempt < retries - 1:
                        time.sleep(1)  # Optional: wait before retrying
                    else:
                        raise ValueError(f"Invalid exchange:symbol '{item}' after {retries} attempts") from e
        return True


    def generate_session(self, prefix: str) -> str:
        """
        Generates a random session identifier.

        Args:
            prefix (str): The prefix to prepend to the random string.

        Returns:
            str: A session identifier consisting of the prefix and a random string.
        """
        random_string = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(12))
        return prefix + random_string


    def prepend_header(self, message: str) -> str:
        """
        Prepends the message with a header indicating its length.

        Args:
            message (str): The message to be sent.

        Returns:
            str: The message prefixed with its length.
        """
        message_length = len(message)
        return f"~m~{message_length}~m~{message}"


    def construct_message(self, func: str, param_list: list) -> str:
        """
        Constructs a message in JSON format.

        Args:
            func (str): The function name to be called.
            param_list (list): The list of parameters for the function.

        Returns:
            str: The constructed JSON message.
        """
        return json.dumps({"m": func, "p": param_list}, separators=(',', ':'))

    def create_message(self, func: str, param_list: list) -> str:
        """
        Creates a complete message with a header and a JSON body.

        Args:
            func (str): The function name to be called.
            param_list (list): The list of parameters for the function.

        Returns:
            str: The complete message ready to be sent.
        """
        return self.prepend_header(self.construct_message(func, param_list))

    def send_message(self, func: str, args: list):
        """
        Sends a message to the WebSocket server.

        Args:
            func (str): The function name to be called.
            args (list): The arguments for the function.
        """
        message = self.create_message(func, args)
        logging.debug("Sending message: %s", message)
        
        try:
            self.ws.send(message)
        except (ConnectionError, TimeoutError) as e:  # Catch specific exceptions
            logging.error("Failed to send message: %s", e)
        
    
    def get_ohlcv(self, exchange_symbol: str):
        """
        Returns a generator that yields OHLC data for a specified symbol in real-time.

        Args:
            exchange_symbol (str): The symbol in the format 'EXCHANGE:SYMBOL'.

        Returns:
            generator: A generator yielding OHLC data as JSON objects.
        """
        #self.validate_symbols(exchange_symbol)
        quote_session = self.generate_session(prefix="qs_")
        chart_session = self.generate_session(prefix="cs_")
        logging.info(f"Quote session generated: {quote_session}, Chart session generated: {chart_session}")

        self._initialize_sessions(quote_session, chart_session)
        self._add_symbol_to_sessions(quote_session, chart_session, exchange_symbol)
        
        return self.get_data()

    def _initialize_sessions(self, quote_session: str, chart_session: str):
        """
        Initializes the WebSocket sessions for quotes and charts.
        """
        self.send_message("set_auth_token", ["unauthorized_user_token"])
        self.send_message("set_locale", ["en", "US"])
        self.send_message("chart_create_session", [chart_session, ""])
        self.send_message("quote_create_session", [quote_session])
        self.send_message("quote_set_fields", [quote_session, *self._get_quote_fields()])
        self.send_message("quote_hibernate_all", [quote_session])

    def _get_quote_fields(self):
        """
        Returns the fields to be set for the quote session.
        
        Returns:
            list: A list of fields for the quote session.
        """
        return ["ch", "chp", "current_session", "description", "local_description", 
                "language", "exchange", "fractional", "is_tradable", "lp", 
                "lp_time", "minmov", "minmove2", "original_name", "pricescale", 
                "pro_name", "short_name", "type", "update_mode", "volume", 
                "currency_code", "rchp", "rtc"]

    def _add_symbol_to_sessions(self, quote_session: str, chart_session: str, exchange_symbol: str):
        """
        Adds the specified symbol to the quote and chart sessions.
        """
        resolve_symbol = json.dumps({"adjustment": "splits", "symbol": exchange_symbol})
        self.send_message("quote_add_symbols", [quote_session, f"={resolve_symbol}"])
        self.send_message("resolve_symbol", [chart_session, "sds_sym_1", f"={resolve_symbol}"])
        self.send_message("create_series", [chart_session, "sds_1", "s1", "sds_sym_1", "1", 10, ""])
        self.send_message("quote_fast_symbols", [quote_session, exchange_symbol])
        self.send_message("create_study", [chart_session, "st1", "st1", "sds_1", 
                            "Volume@tv-basicstudies-246", {"length": 20, "col_prev_close": "false"}])
        self.send_message("quote_hibernate_all", [quote_session])

        
    def get_latest_trade_info(self, exchange_symbol: List[str]):
        """
        Returns summary information about multiple symbols including last changes, 
        change percentage, and last trade time.

        Args:
            exchange_symbol (List[str]): A list of symbols in the format 'EXCHANGE:SYMBOL'.

        Returns:
            generator: A generator yielding summary information as JSON objects.
        """
        quote_session = self.generate_session(prefix="qs_")
        chart_session = self.generate_session(prefix="cs_")
        logging.info(f"Session generated: {quote_session}, Chart session generated: {chart_session}")

        self._initialize_sessions(quote_session, chart_session)
        self._add_multiple_symbols_to_sessions(quote_session, exchange_symbol)

        return self.get_data()

    def _add_multiple_symbols_to_sessions(self, quote_session: str, exchange_symbols: List[str]):
        """
        Adds multiple symbols to the quote session.
        """
        resolve_symbol = json.dumps({"adjustment": "splits", "currency-id": "USD", "session": "regular", "symbol": exchange_symbols[0]})
        self.send_message("quote_add_symbols", [quote_session, f"={resolve_symbol}"])
        self.send_message("quote_fast_symbols", [quote_session, f"={resolve_symbol}"])
        
        self.send_message("quote_add_symbols", [quote_session]+exchange_symbols)
        self.send_message("quote_fast_symbols", [quote_session]+exchange_symbols)


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
                    result = self.ws.recv()
                    # Check if the result is a heartbeat or actual data
                    if re.match(r"~m~\d+~m~~h~\d+$", result):
                        self.ws.recv()  # Echo back the message
                        logging.debug(f"Received heartbeat: {result}")
                        self.ws.send(result)
                    else:
                        split_result = [x for x in re.split(r'~m~\d+~m~', result) if x]
                        for item in split_result:
                           if item:
                                try:
                                    yield json.loads(item)  # Yield parsed JSON data
                                except Exception as e:
                                    logging.error(f"Failed to parse JSON data: {item} - Error: {e}")
                                    continue

                except WebSocketConnectionClosedException:
                    logging.error("WebSocket connection closed. Attempting to reconnect...")
                    break  # Handle reconnection logic as needed
                except Exception as e:
                    logging.error(f"An error occurred: {e}")
                    break  # Handle other exceptions as needed
        finally:
            self.ws.close()

        
# Signal handler for keyboard interrupt
def signal_handler(sig, frame):
    """
    Handles keyboard interrupt signals to gracefully close the WebSocket connection.

    Args:
        sig: The signal number.
        frame: The current stack frame.
    """
    logging.info("Keyboard interrupt received. Closing WebSocket connection.")
    exit(0)


# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)



# Example Usage
if __name__ == "__main__":
    real_time_data = RealTimeData()

    exchange_symbol = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "FXOPEN:XAUUSD"]  # Example symbol

    data_generator = real_time_data.get_latest_trade_info(exchange_symbol=exchange_symbol)

    # data_generator = real_time_data.get_ohlcv(exchange_symbol="BINANCE:BTCUSDT")

    # Iterate over the generator to get real-time data
    for packet in data_generator:
        print('-'*50)
        print(packet)

