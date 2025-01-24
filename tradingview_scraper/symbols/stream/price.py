from websocket import create_connection, WebSocketConnectionClosedException
import json
import string
import re
import logging
import signal
import requests
import secrets
from typing import List, Optional
from time import sleep
import time
import traceback

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
        self.ws_url = "wss://data.tradingview.com/socket.io/websocket?from=screener%2F"
        self.validate_url = "https://scanner.tradingview.com/symbol?symbol={exchange}%3A{symbol}&fields=market&no_404=false"
        self.ws: Optional[create_connection] = None
        self.data_type: Optional[str] = None  # 'ohlcv' or 'trade_info'
        self.current_symbol: Optional[str] = None
        self.current_symbols: Optional[List[str]] = None
        self.connect()


    def connect(self):
        """Establish initial WebSocket connection."""
        try:
            self.ws = create_connection(self.ws_url, headers=self.request_header)
        except Exception as e:
            logging.error(f"Failed to establish WebSocket connection: {e}")
            raise

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
            raise ValueError("exchange_symbol cannot be empty")
        
        if isinstance(exchange_symbol, str):
            exchange_symbol = [exchange_symbol]
            
        for item in exchange_symbol:
            if len(item.split(':')) != 2:
                raise ValueError(f"Invalid symbol format '{item}'. Must be like 'BINANCE:BTCUSDT'")

            exchange, symbol = item.split(':')
            retries = 3
            for attempt in range(retries):
                try:
                    res = requests.get(self.validate_url.format(exchange=exchange, symbol=symbol))
                    res.raise_for_status()
                    break  # Exit the retry loop on success

                except requests.RequestException as e:
                    if res.status_code == 404:
                        raise ValueError(f"Invalid symbol '{item}' after {retries} attempts")
                    else:
                        logging.warning(f"Attempt {attempt + 1} failed to validate symbol '{item}': {e}")

                    if attempt < retries - 1:
                        time.sleep(1)  # Optional: wait before retrying
                    else:
                        raise ValueError(f"Invalid symbol '{item}' after {retries} attempts")
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
        logging.debug(f"Sending message: {message}")
        try:
            self.ws.send(message)
        except Exception as e:
            logging.error(f"Failed to send message: {e}")
        

    def get_ohlcv(self, exchange_symbol: str):
        """
        Returns a generator that yields OHLC data for a specified symbol in real-time.

        Args:
            exchange_symbol (str): The symbol in the format 'EXCHANGE:SYMBOL'.

        Returns:
            generator: A generator yielding OHLC data as JSON objects.
        """
        self.validate_symbols(exchange_symbol)
        self.data_type = 'ohlcv'
        self.current_symbol = exchange_symbol

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
        self.data_type = 'trade_info'
        self.current_symbols = exchange_symbol

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


    def reconnect(self, max_retries=5, initial_delay=1, backoff=2):
        """
        Attempts to reconnect to the WebSocket server.

        Args:
            max_retries (int): Maximum number of reconnection attempts.
            initial_delay (int): Initial delay before retrying (in seconds).
        
        Returns:
            bool: True if reconnected successfully, False otherwise.
        """
        retry_delay = initial_delay
        for attempt in range(max_retries):
            try:
                self.connect()
                logging.info(f"Reconnected successfully on attempt {attempt + 1}.")
                return True
            except Exception as e:
                logging.error(f"Reconnection attempt {attempt + 1} failed: {e}")
                sleep(retry_delay)
                retry_delay *= backoff
        logging.error("Max reconnection attempts reached.")
        return False
    
    
    def _reinitialize_sessions(self):
        """
        Reinitializes sessions and re-adds symbols after reconnection.
        """
        if self.data_type is None:
            logging.error("Cannot reinitialize sessions: No data type specified.")
            return False

        quote_session = self.generate_session(prefix="qs_")
        chart_session = self.generate_session(prefix="cs_")
        logging.info(f"Reinitializing sessions: quote={quote_session}, chart={chart_session}")

        self._initialize_sessions(quote_session, chart_session)

        try:
            if self.data_type == 'ohlcv':
                if not self.current_symbol:
                    raise ValueError("No symbol stored for OHLCV data.")
                self._add_symbol_to_sessions(quote_session, chart_session, self.current_symbol)
            elif self.data_type == 'trade_info':
                if not self.current_symbols:
                    raise ValueError("No symbols stored for trade info data.")
                self._add_multiple_symbols_to_sessions(quote_session, self.current_symbols)
            else:
                raise ValueError(f"Unknown data type: {self.data_type}")
        except Exception as e:
            logging.error(f"Failed to reinitialize sessions: {e}")
            return False

        return True


    def get_data(self):
        """
        Continuously receives data from the TradingView server via the WebSocket connection.

        Yields:
            dict: Parsed JSON data received from the server.
        """
        try:
            while True:
                try:
                    result = self.ws.recv()

                    if re.match(r"~m~\d+~m~~h~\d+$", result):
                        logging.debug(f"Received heartbeat: {result}")
                        try:
                            self.ws.send(result)  # Echo heartbeat
                        except (WebSocketConnectionClosedException, BrokenPipeError) as e:
                            logging.error("WebSocket error during heartbeat: {e}")
                            if not self.reconnect() or not self._reinitialize_sessions():
                                break
                    else:
                        split_result = [x for x in re.split(r'~m~\d+~m~', result) if x]
                        for item in split_result:
                            if item:
                                yield json.loads(item)

                except WebSocketConnectionClosedException:
                    logging.error("WebSocket connection closed. Reconnecting...")
                    if not self.reconnect() or not self._reinitialize_sessions():
                        break
                except Exception as e:
                    logging.error(f"Unexpected error: {e}")
                    logging.error(traceback.format_exc())
                    break

        except Exception as e:
            logging.error(traceback.format_exc())
            raise
        finally:
            if self.ws:
                self.ws.close()


def signal_handler(sig, frame):
    """
    Handles keyboard interrupt signals to gracefully close the WebSocket connection.
    """
    logging.info("Keyboard interrupt received. Closing WebSocket connection.")
    exit(0)


signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    real_time_data = RealTimeData()
    exchange_symbols = ["FOREXCOM:XAUUSD", "FOREXCOM:EURUSD", "FOREXCOM:GBPJPY"]
    data_generator = real_time_data.get_latest_trade_info(exchange_symbols)
    # data_generator = real_time_data.get_ohlcv(exchange_symbol="BINANCE:BTCUSDT")
    
    for packet in data_generator:
        print('-'*50)
        print('Packet type:', packet.get('m'))