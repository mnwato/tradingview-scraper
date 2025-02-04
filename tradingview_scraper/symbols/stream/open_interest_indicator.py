"""Module providing a two function which return python generator contains trades realtime data."""

import re
import json
import string
import logging
import signal
from typing import Optional
from time import sleep
import secrets

from websocket import create_connection, WebSocketConnectionClosedException

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')



class RealTimeData:
    def __init__(self, auth_token: Optional[str]=None):
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
        self.ws_url = "wss://data.tradingview.com/socket.io/websocket?from=chart%2FVEPYsueI%2F&type=chart"
        self.ws = create_connection(self.ws_url, headers=self.request_header)
        self.auth_token = auth_token


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
        
    
    def get_open_interest(self, exchange_symbol: str):
        """
        Returns a generator that yields OHLC data for a specified symbol in real-time.

        Args:
            exchange_symbol (str): The symbol in the format 'EXCHANGE:SYMBOL'.

        Returns:
            generator: A generator yielding OHLC data as JSON objects.
        """
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
        if self.auth_token is None:
            self.auth_token = "unauthorized_user_token"
        self.send_message("set_auth_token", [self.auth_token])
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
        self.send_message("create_series", [chart_session, "sds_1", "s1", "sds_sym_1", "1", 30, ""])
        self.send_message("quote_fast_symbols", [quote_session, exchange_symbol])
        self.send_message("create_study", [chart_session, "st1", "sessions_1", "sds_1", 
                            "Script@tv-scripting-101!", {"pineFeatures": {"f": True, "t": "text", "v": "{\"indicator\":1,\"plot\":1,\"str\":1,\"request.security\":1}"},
                                                         "pineId": "STD;Open%Interest",
                                                         "pineVersion": "6.0",
                                                         "text": "bmI9Ks46_rhzUW20VteBQlCTSlTfqDg==_IYY8RRrNlr7hWtEv3Qj+Q7nRvehgpgwKBnJfpw740qvHa2M/92c1gseSN6xz6NPpaI95/373YW+fxjGyFGAwxCPjpgZyiM+wRE7UYPBzkfoDOYpusLRyiJ3eGR+9Edm+twT1KCOh5P4HO7sbbhrNNNqXM3CX4BJVMZjXn3DQ3/C/18w5PpEvMhIl0W8f8c6efdCRImyoGjewYsYVRM+aGSetvD9ivLGqr5ShZLq3p0zY+/R+8JtIZWmOSCyK8bkP4liXWGU5kIUjV8VTwExoE7qHsSit9nowAGRf0JpI1rnnESCaD02k/bZ++MX4CZnSZA5lgcTLlOrPHSeUWNffFNhtBq1rMLWoV48v69Esw7kKc8+dVfQh8JXpaXbM7O/x+MMgSBxkEXEmyHn+/R2UmlIimL0j3dAfJliBPjh1kNJIYf6LvpzzOKazKu9mkexDaS9CErbCx8rL0aOiZxOCBs7kd5oiWOI9POJkZfUA98u77YeFrzejU9hZmEuc8iXHbvema2gjB705EE8aKwOq0h8D50uooSkNXHqUm5ayG+BxjQHM+W75S11gdyaJhgDAgRkbhBTwPrpAlcXifcaJiEvbvt/3mz6BhRTFd1SJuj/hknDSqH1FWwbttMp3q6ZCV/SbtOBXIr+/YgQdjQTzJsf3q+MOUGkHczdoWW3mutT0yhAJwfYG0dcNIRlLXYYNxTdk/2S80lMiMSNoGmI+WM4k7vyXuM0EqWo60FWhfdyjK99hM8hygUQzgw2Xl9+wioqeMFDiHnHiw+r70PKgCe33JRXvq3OotP64XJmX/cthsFdkfi4GwdiP7tZYd1fGIfKG8+MVB/MfA44PZ0gPGraL9aB9vu5cnfya6xqsL0bJHPBswxQf1RBaYikv9ZZI7YeHteFT/rDpHHe1VLmU65oepDl7wdZtG/yLaN3MbD3bOXWuul/VpNasfiwFiri1Qc8AYXdYaLWx1ghUmLeA86xOR4x7RSGXW9e76eZXlKZLRBqKwQZlSvd7xIHrY9/zq14wZOTioSOYkE/+UwCrfAL69zzp6TmYiImqwnxaW7rx+FvWWEJ+3In2PcV6Yhzyxr9CNVO0JDeYytIuq1JOIDld0Q8othcCsFcz6rgznp/7o2sMAgPNvewTVE+ZOMdGuc8rb0iIO65ay5D3O2VNzZ0MfpuK8wlpIiUCXT4EnFJyKFjahzSYR8FHc1R/EQo+g4HCVzgw/W8rMEWPQBrf6vWLhld+Q8kGqX60KbUopgnEry2qq9A9UCaCjL+umh/5wQHxJjbq9KEcG/y3EosMW7OyxMsmJzd6Lc8M9gyhhhko7tbarXSS2y1agc63iCcqw1wFxYtS6CsEws0RJ3hqZaLPAD1/rOe6UHzcq/6VsMc1ApPADFXDNhRLlT7XbAKnGsUFhSljTMvkzuJHjEhpwmtslpopc8Fg+wVr2hSuAwYIqsmVGMe8yfzgYNGADobm/nAmREEaqJvDeUVZ/lmQaLeZAedYFrmrFVF5qSlT5dh3CzN+X6AbKmPh9/8=",
                                                         "__profile": {"f": True, "t": "bool", "v": False}}])

        self.send_message("quote_hibernate_all", [quote_session])

    
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
                                yield json.loads(item)  # Yield parsed JSON data

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
    TOKEN = "Your-Tradingview-JWT-Token"
    real_time_data = RealTimeData(auth_token=TOKEN)

    exchange_symbol = "BINANCE:BTCUSDT.P"

    data_generator = real_time_data.get_open_interest(exchange_symbol=exchange_symbol)

    # Iterate over the generator to get real-time data
    for packet in data_generator:
        print('-'*50)
        print(packet)

