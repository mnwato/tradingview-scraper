import requests
from bs4 import BeautifulSoup
import json
import numpy as np
from time import sleep
import pandas as pd
import os

class Ideas:
	"""
	## Note:\n
		In release `0.1.0` and above the name of this class changed from `ClassA` to `Ideas`
	"""
	def __init__(self) -> None:
		self.ideas_url = 'https://www.tradingview.com/ideas/'


	def scraper(self, symbol='btc', wholePage=False, startPage=1, endPage=2, to_csv=False, return_json=False):
		"""
		## Extract ideas of a specified symbol\n
		## Args:\n
			1- symbol name(string):\n
				Like `btc`\n
			2- wholePage(Boolean)\n
				True > crawl all pages\n
				False > crawl first page\n
			3- startPage(int):\n
				This argument defines start page to crawl if `wholePage=True`\n
			4- endPage(int):\n
				This argument defines end page to crawl if `wholePage=True`\n
			5- to_csv(Boolean):\n
				True > Will generate a csv file contains ideas\n
				False > Return a tuple contains symbol's description and ideas dataframe\n
			6- return_json(Boolean):\n
				True > Return ideas as json format instead of default tuple format\n
				False > Return a tuple contains symbol's description and ideas dataframe\n
		## Return:\n
			By default it returns a tuple contains symbol's description and ideas dataframe but\n
			if `return_json=True` it will return ideas as json format

		"""
		if wholePage == True:
			pageList = list(np.arange(startPage, endPage+1))
		else:
			pageList = list(np.arange(1))


		symbol2 = symbol
		socialInfoList = []
		titleList = []
		labelList=[]
		timeFrameList = []
		symbolList = []
		timestampList = []

		for page in pageList:
			symbol = symbol2	### Reset symbol to avoid changing in next page

			if wholePage == True:
				payload = f'/page-{page}/'
			else:
				payload = ''

			x = requests.get(self.ideas_url+ symbol +payload)

			soup = BeautifulSoup(x.text, "html.parser")

			content = soup.find('div', class_='tv-card-container__ideas tv-card-container__ideas--with-padding js-balance-content')  ## 


			######################## Descriptions
			description = content.find('div', class_='tv-widget-description__text')
			if description != None:
				description = description.get_text().strip()

			######################### Social items info
			for i in content.find_all('div', class_='tv-social-row tv-widget-idea__social-row'):
				socialInfoList.append(json.loads(i['data-model']))

			######################### Titles
			for i in content.find_all('div', class_='tv-widget-idea__title-row'):
				titleList.append(i.a.get_text())

			######################### Labels, timeFrame, Symbol

			for i in content.find_all('div', class_='tv-widget-idea__info-row'):
				# print(i.prettify())
				if i.find('span', class_='tv-idea-label tv-widget-idea__label tv-idea-label--long') != None:
					label = 'Long'
				elif i.find('span', class_='tv-idea-label tv-widget-idea__label tv-idea-label--short') != None:
					label = 'Short'
				else:
					label = 'Neutral'

				timeFrame = i.find_all('span', class_='tv-widget-idea__timeframe')[1].text

				symbol = i.find('div', class_='tv-widget-idea__symbol-info').a.text

				symbolList.append(symbol)
				timeFrameList.append(timeFrame)
				labelList.append(label)

			######################### Timestamps
			for i in content.find_all('span', class_='tv-card-stats__time js-time-upd'):
				# print(i.prettify())

				timestampList.append(i['data-timestamp'])
			sleep(5)

		if return_json == True:
			data = {'symbol_description': description}
			for elem in range(len(timestampList)):
				data.update({
					str(elem):{
					'timeStamp': timestampList[elem], 'symbol': symbolList[elem], 'timeFrame': timeFrameList[elem],
					'label': labelList[elem], 'title': titleList[elem], 'socialInfo': socialInfoList[elem]
					}
				})
			if to_csv == True:
				data_copy = data.copy()
				data_copy.pop('symbol_description')
				df = pd.read_json(json.dumps(data_copy), orient='index')
				df.to_csv(f'tradingview_{symbol}.csv', index=False)
			return data
		else:
			data = {
				'timeStamp': timestampList, 'symbol': symbolList, 'timeFrame': timeFrameList, 'label': labelList,
				'title': titleList, 'socialInfo': socialInfoList, 'description': description
			}
			df = pd.DataFrame(data)
			if to_csv == True:
				df.to_csv(f'tradingview_{symbol}.csv', index=False)
			return description, df.drop(columns=['description'])



class Indicators:
	def __init__(self) -> None:
		self.indicators_url = 'https://scanner.tradingview.com/crypto/scan'


	def scraper(self, exchange="BITSTAMP", symbols=["BTCUSD"],
			indicators=["RSI"], allIndicators=False):
		"""
		## Extract symbol indicators
		## Args:\n
			1- exchange(String):\n
			Exchange name like (Default: `BITSTAMP`),`BINANCE`,`BINANCEUS`,`BITCOKE`,`BITFINEX`,\n
			`BITTREX`,`BYBIT`,`CEXIO`,`EXMO`,`FTX`,`GEMINI`,`KRAKEN`,`OKCOIN`,`TIMEX`,\n
			`TRADESTATION`
				
			2- symbols(List of strings):\n
				List of symbols (Default: `BTCUSD`)\n
			3- indicators(List of string):\n
				List of indicators (Default: `RSI`) [Others](https://github.com/mnwato/tradingview-scraper/tree/main/tradingview_scraper/indicatos.txt)\n
			4- allIndicators(Boolean):\n
				True > Extract all indicators Whether the indicators are specified or not\n
				False > Extract only indicators which are apecified in indicators arguments  
		## Return(JSON):\n
			List of indicators for specified symbols
		"""
		symbols = [f"{exchange}:"+x for x in symbols]
		if allIndicators == True:
			with open(os.path.join(os.getcwd(), 'tradingview_scraper', 'indicators.txt'), 'r') as f:
				indicators = f.read().replace('"',"").split(',')
		
		payload = {
			"symbols":{"tickers": symbols, "query":{"types":[]}},
			"columns": indicators
		}
		headers = {
			"authority": "scanner.tradingview.com",
			"method": "POST",
			"path": "/crypto/scan",
			"scheme": "https",
			"accept": "*/*",
			"accept-encoding": "gzip, deflate, br",
			"accept-language": "en-US,en;q=0.9",
			"content-length": "1269",
			"content-type": "application/x-www-form-urlencoded",
			"cookie": "_ga=GA1.2.170692871.1636066864; __gads=ID=eafb0f94683db984:T=1636066978:S=ALNI_MZ-0TZNoN6EUwbt302scWBNrnE-rA; sessionid=n27htwjuhx5678st2mpj5oe66y49lioh; tv_ecuid=f9bf1dfb-91fe-4e97-ada2-7cdcbc502c2e; _sp_ses.cf1a=*; _gid=GA1.2.734511956.1646977393; _gat_gtag_UA_24278967_1=1; _sp_id.cf1a=07117aec-f7ee-4bd8-af59-f80ae57f124d.1643982464.4.1646977457.1645721190.42cd0b0d-4b87-4c86-9350-8d5fea7a8f66",
			"origin": "https://www.tradingview.com",
			"referer": "https://www.tradingview.com/",
			"sec-ch-ua": """Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99""",
			"sec-ch-ua-mobile": "?0",
			"sec-ch-ua-platform": "Windows",
			"sec-fetch-dest": "empty",
			"sec-fetch-mode": "cors",
			"sec-fetch-site": "same-site",
			"user-agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
		}
		res = requests.post(self.indicators_url, headers=headers, json=payload)
		inds = {}
		for elem in res.json()['data']:
			temp = []
			temp = {key:str(val) for key,val in zip(indicators, elem['d'])}
			inds.update({
				elem['s'].split(':')[-1]: temp
			})
		return inds