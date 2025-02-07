"""
Module providing functionality to connect to TradingView's WebSocket API 
for real-time trade data streaming. This module includes classes and methods 
to manage WebSocket connections, send messages, and handle session management.
"""

import json
import string
import logging
import secrets

from websocket import create_connection

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class StreamHandler:
    """
    Class for managing a WebSocket connection to a trading data service.

    This class handles establishing the connection, generating unique session
    identifiers for quotes and charts, initializing sessions, and constructing
    and sending properly formatted messages to the server.
    """

    def __init__(self, websocket_url: str, jwt_token: str = "unauthorized_user_token"):
        """
        Initializes the StreamData instance, setting up the WebSocket connection
        and initializing sessions for quotes and charts.

        Args:
            websocket_url (str): The URL of the WebSocket server.
            jwt_token (str, optional): JWT token for authentication. Defaults to "unauthorized_user_token".
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
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
            )
        }
        self.ws = create_connection(websocket_url, headers=self.request_header)
        self._initialize(jwt_token=jwt_token)

    def _initialize(self, jwt_token: str):
        """
        Initializes the quote and chart sessions and sets up authentication.

        This method generates unique session identifiers for both quote and chart streams,
        logs the generated sessions, and initializes the sessions by sending the necessary
        setup messages to the WebSocket server.

        Args:
            jwt_token (str): JWT token for authentication.
        """
        quote_session = self.generate_session(prefix="qs_")
        chart_session = self.generate_session(prefix="cs_")
        logging.info("Quote session generated: %s, Chart session generated: %s",
                     quote_session, chart_session)

        self._initialize_sessions(quote_session, chart_session, jwt_token)
        self.quote_session = quote_session
        self.chart_session = chart_session

    def generate_session(self, prefix: str) -> str:
        """
        Generates a random session identifier.

        The session identifier is composed of a given prefix followed by a random sequence
        of 12 lowercase letters.

        Args:
            prefix (str): The prefix to prepend to the random string.

        Returns:
            str: A unique session identifier.
        """
        random_string = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(12))
        return prefix + random_string

    def prepend_header(self, message: str) -> str:
        """
        Prepends a header to the message that indicates its length.

        The header is in the format: "~m~<length>~m~", where <length> is the length of the message.

        Args:
            message (str): The message to be sent.

        Returns:
            str: The message prefixed with its length.
        """
        message_length = len(message)
        return f"~m~{message_length}~m~{message}"

    def construct_message(self, func: str, param_list: list) -> str:
        """
        Constructs a JSON-formatted message for the specified function and parameters.

        Args:
            func (str): The name of the function or command.
            param_list (list): A list of parameters for the function.

        Returns:
            str: A JSON string representing the message.
        """
        return json.dumps({"m": func, "p": param_list}, separators=(',', ':'))

    def create_message(self, func: str, param_list: list) -> str:
        """
        Creates a complete message by combining a header and a JSON body.

        The complete message is ready to be sent to the WebSocket server.

        Args:
            func (str): The function or command name.
            param_list (list): A list of parameters for the function.

        Returns:
            str: The complete message with a header and JSON body.
        """
        return self.prepend_header(self.construct_message(func, param_list))

    def send_message(self, func: str, args: list):
        """
        Sends a message to the WebSocket server.

        The message is constructed with the specified function name and arguments, and then sent.
        If sending fails due to connection-related errors, an error is logged.

        Args:
            func (str): The function or command name.
            args (list): The arguments to be sent with the message.
        """
        message = self.create_message(func, args)
        logging.debug("Sending message: %s", message)

        try:
            self.ws.send(message)
        except (ConnectionError, TimeoutError) as e:
            logging.error("Failed to send message: %s", e)

    def _initialize_sessions(self, quote_session: str, chart_session: str, jwt_token: str):
        """
        Initializes WebSocket sessions for quotes and charts by sending setup messages.

        This method configures the authentication token, locale settings, and creates
        the sessions for chart and quote data. It also sets the required fields for the quote session
        and puts the session into a hibernation state if needed.

        Args:
            quote_session (str): The identifier for the quote session.
            chart_session (str): The identifier for the chart session.
            jwt_token (str): JWT token for authentication.
        """
        self.send_message("set_auth_token", [jwt_token])
        self.send_message("set_locale", ["en", "US"])
        self.send_message("chart_create_session", [chart_session, ""])
        self.send_message("quote_create_session", [quote_session])
        self.send_message("quote_set_fields", [quote_session, *self._get_quote_fields()])
        self.send_message("quote_hibernate_all", [quote_session])

    def _get_quote_fields(self) -> list:
        """
        Retrieves the list of fields to be used for the quote session.

        These fields specify the data attributes to be included in the real-time quote updates.

        Returns:
            list: A list of field names for the quote session.
        """
        return [
            "ch", "chp", "current_session", "description", "local_description",
            "language", "exchange", "fractional", "is_tradable", "lp",
            "lp_time", "minmov", "minmove2", "original_name", "pricescale",
            "pro_name", "short_name", "type", "update_mode", "volume",
            "currency_code", "rchp", "rtc"
        ]
