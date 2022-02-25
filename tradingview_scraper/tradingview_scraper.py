import requests
from bs4 import BeautifulSoup
import json
import numpy as np
from time import sleep
import pandas as pd


class ClassA:
	global base_url
	base_url = 'https://www.tradingview.com/ideas/'

	def scraper(symbol='btc', wholePage=False, startPage=1, endPage=2, to_csv=False, return_json=False):

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

			x = requests.get(base_url+ symbol +payload)

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

