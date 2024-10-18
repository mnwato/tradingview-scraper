import json
import random
import string
import re
import logging
from time import sleep
from websocket import create_connection, WebSocketConnectionClosedException
import signal

# Configure logging
logging.basicConfig(level=logging.INFO,
					format='%(asctime)s - %(levelname)s - %(message)s')


class RealTimeData:
	def __init__(self):
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
		self.url = "wss://data.tradingview.com/socket.io/websocket"

	def generate_session(self, prefix: str) -> str:
		random_string = ''.join(random.choice(
			string.ascii_lowercase) for _ in range(12))
		return prefix + random_string

	def prepend_header(self, message: str) -> str:
		return f"~m~{len(message)}~m~{message}"

	def construct_message(self, func: str, param_list: list) -> str:
		return json.dumps({"m": func, "p": param_list}, separators=(',', ':'))

	def create_message(self, func: str, param_list: list) -> str:
		return self.prepend_header(self.construct_message(func, param_list))

	def send_message(self, ws, func: str, args: list):
		message = self.create_message(func, args)
		ws.send(message)

	def get_data(self, exchange_symbol: str):
		ws = create_connection(self.url, headers=self.request_header)

		session = self.generate_session(prefix="qs_")
		logging.info(f"Session generated: {session}")

		chart_session = self.generate_session(prefix="cs_")
		logging.info(f"Chart session generated: {chart_session}")

		self.send_message(ws, "set_auth_token", ["unauthorized_user_token"])
		self.send_message(ws, "chart_create_session", [chart_session, ""])
		self.send_message(ws, "quote_create_session", [session])
		self.send_message(ws, "quote_set_fields", [session, "ch", "chp", "current_session", "description",
												   "local_description", "language", "exchange", "fractional",
												   "is_tradable", "lp", "lp_time", "minmov", "minmove2",
												   "original_name", "pricescale", "pro_name", "short_name",
												   "type", "update_mode", "volume", "currency_code", "rchp", "rtc"])
		self.send_message(ws, "quote_add_symbols", [
			session, exchange_symbol, {"flags": ['force_permission']}])

		resolve_symbol = json.dumps(
			{"symbol": exchange_symbol, "adjustment": "splits"})
		self.send_message(ws, "resolve_symbol", [
			chart_session, "symbol_1", f"={resolve_symbol}"])
		self.send_message(ws, "create_series", [
			chart_session, "s1", "s1", "symbol_1", "1", 300])
		self.send_message(ws, "quote_fast_symbols", [session, exchange_symbol])
		self.send_message(ws, "create_study", [chart_session, "st1", "st1", "s1", "Volume@tv-basicstudies-118",
											   {"length": 20, "col_prev_close": "false"}])
		self.send_message(ws, "quote_hibernate_all", [session])

		try:
			while True:
				try:
					sleep(1)
					result = ws.recv()
					if re.match(r"~m~\d+~m~~h~\d+$", result):
						ws.recv()  # Echo back the message
						logging.info(f"Received message: {result}")
					else:
						split_result = [x for x in re.split(
							r'~m~\d+~m~', result) if x]
						for item in split_result:
							if item:
								# Yield each data item as JSON
								item = json.loads(item)
								yield item

				except WebSocketConnectionClosedException:
					logging.error(
						"WebSocket connection closed. Attempting to reconnect...")
					break  # Handle reconnection logic as needed
				except Exception as e:
					logging.error(f"An error occurred: {e}")
					break  # Handle other exceptions as needed
		finally:
			ws.close()

# Signal handler for keyboard interrupt


def signal_handler(sig, frame):
	logging.info("Keyboard interrupt received. Closing WebSocket connection.")
	exit(0)


# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)


# Example Usage
if __name__ == "__main__":
	exchange_symbol = "BINANCE:BTCUSDT"  # Example symbol
	# exchange_symbol = "FXOPEN:XAUUSD"  # Example symbol
	# exchange_symbol = "NASDAQ:AAPL"  # Example symbol
	real_time_data = RealTimeData()

	# Create a generator to fetch real-time data
	data_generator = real_time_data.get_data(exchange_symbol)

	# Iterate over the generator to get real-time data
	for packet in data_generator:
		print(packet)