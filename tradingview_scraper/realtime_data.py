
import asyncio
import websockets
import json



class RealTimeData:
	def __init__(self):
		self.request_header = {
			"Accept-Encoding": "gzip, deflate, br",
			"Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
			"Cache-Control": "no-cache",
			"Connection": "Upgrade",
			"Host": "data.tradingview.com",
			"Origin": "https://www.tradingview.com",
			"Pragma": "no-cache",
			"Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
			# "Sec-WebSocket-Key": "Fn1bGdYySux+ji+A7oo6Fg==",
			# "Sec-WebSocket-Version": "13",
			"Upgrade": "websocket",
			"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
			}
		self.url = "wss://data.tradingview.com/socket.io/websocket?from={}&date={}".format(
			"symbols%2FCOMEX-GCZ2022%2F", 
			"2022_11_03-11_39")


	async def price(self):
		try:
			async with websockets.connect(self.url, extra_headers=self.request_header, timeout=10, ping_interval=None) as websocket:
				# await websocket.send("""~m~36~m~{"m":"set_data_quality","p":["low"]}""")
				
				await websocket.send("""~m~36~m~{"m":"set_data_quality","p":["low"]}""")
				recv_msg1 = await websocket.recv()
				# await websocket.send("""~m~54~m~{"m":"set_auth_token","p":["unauthorized_user_token"]}""")
				# recv_msg2 = await websocket.recv()
				# await websocket.send("""~m~73~m~{"m":"chart_create_session","p":["cs_kcWr3I7hXvQW","disable_statistics"]}""")
				# recv_msg3 = await websocket.recv()
				# await websocket.send("""~m~118~m~{"m":"resolve_symbol","p":["cs_kcWr3I7hXvQW","sds_sym_1","={\"adjustment\":\"splits\",\"symbol\":\"COMEX:GCZ2022\"}"]}""")
				# recv_msg4 = await websocket.recv()
				# await websocket.send("""~m~86~m~{"m":"create_series","p":["cs_kcWr3I7hXvQW","sds_1","s1","sds_sym_1","1D",1000,"12M"]}""")
				# recv_msg5 = await websocket.recv()
				await websocket.send("""~m~52~m~{"m":"quote_create_session","p":["qs_PCY0BwDsczZA"]}""")
				recv_msg6 = await websocket.recv()
				await websocket.send("""~m~735~m~{"m":"quote_set_fields","p":["qs_PCY0BwDsczZA","base-currency-logoid","ch","chp","currency-logoid","currency_code","currency_id","base_currency_id","current_session","description","exchange","format","fractional","is_tradable","language","local_description","listed_exchange","logoid","lp","lp_time","minmov","minmove2","original_name","pricescale","pro_name","short_name","type","typespecs","update_mode","volume","value_unit_id","ask","bid","fundamentals","high_price","is_tradable","low_price","open_price","prev_close_price","rch","rchp","rtc","rtc_time","status","basic_eps_net_income","beta_1_year","earnings_per_share_basic_ttm","industry","market_cap_basic","price_earnings_ttm","sector","volume","dividends_yield","timezone"]}""")
				recv_msg7 = await websocket.recv()
				await websocket.send("""~m~65~m~{"m":"quote_add_symbols","p":["qs_PCY0BwDsczZA","COMEX:GCZ2022"]}""")
				recv_msg8 = await websocket.recv()

				# if recv_msg == '{"message": "sub to price info"}':
				# 	await websocket.send(json.dumps({"method":"sub_to_market","id":_id}))
				# 	recv_msg = await websocket.recv()
				# 	print(recv_msg)
				# 	counter = 1 

				# 	task = asyncio.create_task(self.ping_func(websocket))

				counter = 1
				while True:
					msg = await websocket.recv()
					print('--', msg)
					await self.ping_func(websocket, counter)  ## Return recieved message
					counter+=1
		except Exception as e:
			print(str(e))

	
	async def ping_func(self, websocket, counter):
			try:
				while True:
					tx_msg = '~m~4~m~~h~{}'.format(counter)
					await websocket.send(tx_msg)
					print('------ ping')
					msg = await asyncio.sleep(10)
					if msg == tx_msg:
						continue
					else:
						print('--', msg)
						raise Exception
			except Exception as e:
				print('Error in ping_func.', str(e))


	# async def get_result(self):
	# 		while True:
	# 			# print('---get_result---', self.result)
	# 			await asyncio.sleep(1)
	# 			yield self.result


if __name__ == "__main__":
	obj = RealTimeData()
	asyncio.run(obj.price())