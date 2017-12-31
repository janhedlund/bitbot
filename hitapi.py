import time as t 
import json
import requests as rq
import random as rd
import urllib.parse as urlp
from websocket import create_connection
import hashlib
import hmac

pub = 'public'
acc = 'account'
hist = 'history'
order = 'order'
trade = 'trading'
st = 'streaming'


def argmake(method, params=None, call_id=None):
	call_dict = {'method':method}
	if call_id is not None: call_dict.update({'id':call_id})
	if params is not None:
		call_dict.update({'params':{}})
		for param in params:
			call_dict['params'].update({param:params[param]})
	return call_dict

def total(balance):
	a=float(balance['available'])
	b=float(balance['reserved'])
	balance.update({'total':str(a+b)})
	return balance

class HitBot(object):
	
	def __init__(self, api_key=None, api_secret=None, calls_per_sec=1, streaming_api=False, stream=None, next_id=1):
		self.api_key = str(api_key) if api_key is not None else None
		self.api_secret = str(api_secret) if api_secret is not None else None
		self.call_rate = 1/calls_per_sec
		self.latest_call_time = None
		self.go = rq.session()
		self.go.auth = (self.api_key, self.api_secret)
		self.streaming_api = streaming_api # RESTful api by default; 'stream' for streaming data.
		self.stream = stream
		self.next_id = next_id
		self.ws=None

		if self.streaming_api==True:
			self.ws = create_connection('wss://api.hitbtc.com/api/2/ws')

	def wait(self, protection=pub):
		#This function doesn't show up anywhere, but call it right before the RESTful returns of pub_call() and auth_call() if you want to use it.
		if self.latest_call_time is not None:
			remaining = self.call_time - (t.time()-self.latest_call_time)
			if remaining>0: 
				t.sleep(remaining)
		self.latest_call_time = t.time()

	def pub_call(self, args=None, call_dict={}):
		url = 'https://api.hitbtc.com/api/2/public'
		if self.streaming_api==True: 
			if call_dict=={}: 
				raise Exception('Errno 103: No call_dict given. \
								Websocket API calls must include \
								call parameter dictionary object.')
			self.ws.send(json.dumps(call_dict))
			return json.loads(self.ws.recv())
		if args is None: 
			raise Exception('Errno 104: No args list given. \
							RESTful API calls must include URL extension list object.')
		for arg in args:
			url+='/{}'.format(arg)
		return rq.get(url, call_dict).json()
		

	def auth_call(self, args=None, orderData=None, rq_method=None, call_dict={}):
		if None in [self.api_key, self.api_secret]: 
			raise Exception('Errno 101: No API key permissions passed to HitBot instance.')

		if self.streaming_api==True:
			if call_dict=={}: 
				raise Exception(
					'Errno 103: Websocket API calls must submit call parameter dictionary object.')
			self.ws.send(json.dumps(call_dict))
			return self.ws.recv()

		url = 'https://api.hitbtc.com/api/2'
		for arg in args: 
			url+='/{}'.format(arg)

		if rq_method is None:
			if orderData is None: 
				return self.go.get(url, call_dict).json()
			else: 
				return self.go.get(url, data=orderData)
		elif rq_method=='post': 
			return self.go.post(url, data=orderData)

		elif rq_method=='del': 
			return self.go.delete(url)

	#METHODS FOR GETTING DATA ABOUT A GIVEN COIN
	def coin_data(self, coin=None): #if coin is none, returns all coins traded on hitBTC
		if self.streaming_api==False:
			args = ['currency']
			if coin is not None: 
				args.append(str(coin))
			return self.pub_call(args)

		'''
		method: getCurrency 
		params: currency:'ETH' 
		id: some_number
		'''

	def all_coins(self):
		if self.streaming_api==False:
			allcoins = self.coin_data()
			return [coin['id'] for coin in allcoins]
		'''
		method: getCurrencies
		params: none
		id: some_number
		'''

	def is_ICO(self, coin):
		return not self.coin_data(coin)['crypto']

	def all_ICO(self):
		allcoins = self.coin_data()
		return [coin['id'] for coin in allcoins if coin['crypto']==False]

	#METHODS FOR GETTING ALL TRADING PAIRS
	def all_pairs_data(self):
		if self.streaming_api==False:
			args = ['symbol']
			return self.pub_call(args)
		call_dict = argmake(getSymbols, params=None)
		self.next_id+=1
		return self.pub_call(call_dict=call_dict)
		'''
		method: getSymbols
		params: none
		id: some_number
		'''

	def all_pairs(self):
		allpairs = self.all_pairs_data()
		pairs =[pair['id'] for pair in allpairs]
		return pairs

	def btc_pairs(self):
		allpairs = self.all_pairs_data()
		return [pair['id'] for pair in allpairs if pair['quoteCurrency'] == 'BTC']

	def eth_pairs(self):
		allpairs = self.all_pairs_data()
		return [pair['id'] for pair in allpairs if pair['quoteCurrency'] == 'ETH']
		
	def usd_pairs(self):
		allpairs = self.all_pairs_data()
		return [pair['id'] for pair in allpairs if pair['quoteCurrency'] == 'USD']


	#METHODS FOR GETTING SPECS ABOUT A MARKET (data unrelated to price, recent trades, etc.)
	def market_specs(self, pair):
		if self.streaming_api==False:
			args = ['symbol', str(pair)]
			return self.pub_call(args)
		'''
		method: getSymbol
		params: symbol:NETETH
		id: some_number
		'''

	def market_inc(self, pair):
		return self.market_specs(pair)['quantityIncrement']

	def maker_comission(self, pair):
		return self.market_specs(pair)['provideLiquidityRate']

	def taker_comission(self, pair):
		return self.market_specs(pair)['takeLiquidityRate']


	#METHODS FOR GETTING DATA ABOUT A SPECIFIC MARKET'S HISTORY
	def market_data(self, market):
		#All market data methods until stream_ticker() for RESTful API use only. For streaming, those below stream_ticker().
		if self.streaming_api==False:
			args = ['ticker', str(market)]
			return self.pub_call(args=args)

	def last_price(self, market):
		return self.market_data(market)['last']

	def best_ask(self, market):
		return self.market_data(market)['ask']

	def best_bid(self, market):
		return self.market_data(market)['bid']

	def daylow(self, market):
		return self.market_data(market)['low']

	def dayhigh(self, market):
		return self.market_data(market)['high']

	def dayvol(self, market):
		return self.market_data(market)['volume']

	def stream_ticker(self, symbol, child):
		#Not really to be called by the user, but rather by its child-functions.
		child_lookup = {1:'subscribeTicker',
						2:'unsubscribeTicker',
						3:'ticker',
						}
		call_dict = argmake(child_lookup[child], {'symbol':symbol})
		if child in [1,2,3]:
			call_dict.update({'id':self.next_id})
			self.next_id+=1
		return self.pub_call(call_dict=call_dict)

	def sub_ticker(self, symbol):
		return self.stream_ticker(symbol, 1)

	def unsub_ticker(self, symbol):
		return self.stream_ticker(symbol, 2)

	def quick_ticker(self, symbol):
		#Notification method; contains no call id
		return self.stream_ticker(symbol, 3)


	#METHODS FOR GETTING DATA ABOUT TRADES IN GIVEN MARKET
	def trade_data(self, market):
		'''
		API can also take: 
		sortmethod='DESC'|'ASC',
		sortby='id'|'timestamp', 
		from=str(datetime|id), 
		till=str(datetime|id), 
		limit=str(int(x)), 
		offset=str(int(x)
	
		Functionality not built in, but easy to take a look at the API and add it if so desired.
		'''
		#Only for use with RESTful API. For streaming, use one of the trade data methods below.
		args = ['trades', str(market)]
		return self.pub_call(args)

	def stream_trades(self, symbol, child):
		#Not really to be called by the user, but rather by its child-functions.
		child_lookup = {1:'subscribeTrades',
						2:'unsubscribeTrades',
						3:'snapshotTrades',
						4:'updateTrades',
						}
		call_dict = argmake('subscribeTrades', {'symbol':symbol})
		if child in [1,2]:
			call_dict.update({'id':self.next_id})
			self.next_id+=1
		return self.pub_call(call_dict)

	def sub_trades(self, symbol):
		self.stream_trades(symbol, 1)

	def unsub_trades(self, symbol):
		self.stream_trades(symbol, 2)
		
	def quick_trades(self, symbol):
		#Notification method; contains no call id
		self.stream_trades(symbol, 3)
		
	def update_trades(self, symbol):
		#Notification method; contains no call id
		self.stream_trades(symbol, 4)

	def get_trades(self, symbol, limit=100, sort='DESC', by='id'):
		#Notification method; contains no call id
		params = {'symbol':symbol}
		params.update({'limit':limit}) if limit!=100 else None
		params.update({'sort':sort}) if sort!='DESC' else None
		params.update({'by':by}) if by!='id' else None
		call_dict = argmake('getTrades', params)
		return self.pub_call(call_dict=call_dict)


	#METHODS FOR GETTING ORDERBOOK DATA
	def orderbook(self, market, limit=100):
		#Only for use with RESTful API. For streaming, use one of the orderbook methods below.
		args = ['orderbook', str(market)]
		call_dict = {}
		call_dict.update({'limit':limit}) if limit!=100 else None
		return self.pub_call(args, call_dict)

	def buy_orders(self, market, limit=100):
		#Only for use with RESTful API. For streaming, use one of the orderbook methods below.
		raw_orders = self.orderbook(market, limit)['bid']
		clean_orders = {}
		for order in raw_orders:
			clean_orders.update({order['price']:order['size']})
		return clean_orders

	def sell_orders(self, market, limit=100):
		#Only for use with RESTful API. For streaming, use one of the orderbook methods below.
		orders = self.orderbook(market, limit)
		raw_orders = self.orderbook(market, limit)['ask']
		clean_orders = {}
		for order in raw_orders:
			clean_orders.update({order['price']:order['size']})
		return clean_orders

	def stream_orderbook(self, symbol, child, limit=100):
		#Not really to be called by the user, but rather by its child-functions.
		child_lookup = {1:'subscribeOrderbook',
						2:'unsubscribeOrderbook',
						3:'snapshotOrderbook',
						4:'updateOrderbook',
						}
		call_dict = argmake(child_lookup[child], {'symbol':symbol, 'limit':limit})
		if child in [1,2]: 
			call_dict.update({'id':self.next_id})
			self.next_id+=1
		return self.pub_call(call_dict=call_dict)
		
	def sub_orderbook(self, symbol, limit=100):
		return self.stream_orderbook(symbol, 1)

	def unsub_orderbook(self, symbol, limit=100):
		return self.stream_orderbook(symbol, 2)

	def quick_orderbook(self, symbol, limit=100):
		#Notification method; contains no call id
		return self.stream_orderbook(symbol, 3).json()

	def update_orderbook(self, symbol, limit=100):
		#Notification method; contains no call id
		return self.stream_orderbook(symbol, 4, limit)

	#METHODS FOR GETTING CANDLE DATA
	def candle_data(self, market, limit=100, period='M30'):
		#Only for use with RESTful API. For streaming, use one of the candle methods below.
		args = ['public', 'candles', str(market)]#, str(limit), str(period)]
		call_dict = {}
		call_dict.update({'limit':limit}) if limit!=100 else None 
		call_dict.update({'period':period}) if period!='M30' else None
		return self.pub_call(agrs=args, call_dict=call_dict)

	def stream_candles(self, symbol, period, child):
		#Not really to be called by the user, but rather by its child-functions.
		child_lookup = {1:'subscribeCandles',
						2:'unsubscribeCandles',
						3:'snapshotCandles',
						4:'updateCandles',
						}
		params = {'symbol':symbol}
		params.update({'period':period}) if period!='M30' else None
		call_dict = argmake(child_lookup[child], params)
		if child in [1,2]:
			call_dict.update({'id':self.next_id})
			self.next_id+=1
		return self.auth_call(call_dict=call_dict)

	def sub_candles(self, symbol, period='M30'):
		return self.stream_orderbook(symbol, period, 1)

	def unsub_candles(self, symbol, period='M30'):
		return self.stream_orderbook(symbol, period, 2)
		
	def quick_candles(self, symbol, period):
		#Notification method; contains no call id
		return self.stream_orderbook(symbol, period, 3)

	def update_candles(self, symbol, period):
		#Notification method; contains no call id
		return self.stream_orderbook(symbol, period, 4)
		

	'''
	Every method ABOVE this point is PUBLIC. To use them, it is sufficient to create an instance of hitbot
	such as myBot = HitBot(None,None,100).

	Every method BELOW this point is PERMISSIONED. This means that they have to do with details specific to the user's account.
	Therefore, the 'None, None' won't do and must be replaced with user-created permissioned API keys.
	This can be done on the hitBTC website on your personal account. 

	FOR STREAMING WEBSOCKET API
		Before using any of the below permissioned methods, one must first 'login'
		This is done under encryption by default.

		*************************************************************************
		***       IF USING API KEYS WITH TRADE OR WITHDRAWL PERMISSIONS,	  *** 
		***  IT IS -$$-HIGHLY-$$- RECOMMENDED THAT YOU USE THE HS256 DEFAULT  ***
		*************************************************************************

		But if you really to pass your secret keys around the internet without encryption,
		be my guest; pass 'BASIC' to login().
	'''
	#AUTHENTICATE SESSION WITH OPTIONAL (DEFAULT) NONCE-SALTED HS256 ENCRYPTION 
	def login(self, algo='HS256'):
		#I AM NOT ACCOUNTABLE GOD DAMN IT 
		if algo=='BASIC': 
			print('If you say so, dude.')
			call_dict = argmake('login', {'algo':algo, 'pKey':self.api_key, 
								'sKey':self.api_secret}, self.next_id)
			self.next_id+=1
			return self.auth_call(call_dict=call_dict)
		nonce = hex(int(''.join([str(rd.randint(0,16)) for i in range(32)])))
		message = bytearray(nonce, 'utf8')
		secret = bytearray(self.api_secret, 'utf8')
		signature = hmac.new(secret, message, digestmod=hashlib.sha256).hexdigest()
		call_dict = argmake('login', {'algo':'HS256', 'pKey':self.api_key,
							'nonce':nonce, 'signature':signature}, self.next_id)
		self.next_id+=1
		return self.auth_call(call_dict=call_dict)


	#METHODS FOR CHECKING ACCOUNT BALANCES		
	def balance(self, loc, coin=None, total_only=False): #loc = 'account'|'trading'
		if self.streaming_api==False:
			args = [loc,'balance']
			balance_data = self.auth_call(args)
			if coin is None: return balance_data
			for coin_balance in balance_data: 
				if coin_balance['currency']==str(coin).upper():
					coin_balance = total(coin_balance)
					if total_only==False: return coin_balance
					return {coin_balance['currency']:float(coin_balance['total'])}
		'''
		method: getTradingBalance
		params: {}
		id: some_number
		'''

	def nonzero_balances(self, loc):
		args = [loc, 'balance']
		balance_data = self.auth_call(args)
		result = []
		for coin in balance_data: 
			if not (float(coin['available'])==0 and float(coin['reserved'])==0): 
				result.append(total(coin))
		return result

	#METHODS FOR CHECKING ACCOUNT ACTIVE ORDERS
	def active_orders(self, symbol=None, clientOrderId=None):
		if self.streaming_api==False:
			call_args=['order']
			if symbol is not None: call_args.append(symbol)
			elif clientOrderId is not None: call_args.append(clientOrderId)
			return self.auth_call(call_args)
		'''
		method: getOrders
		params: {} #symbol:NETETH optional
		id: some_number
		'''


	#METHOD FOR GETTING TRADING FEES
	def fees(self, symbol):
		call_args=['trading', 'fees', 'symbol']
		return self.auth_call(call_args)

	#METHODS FOR GETTING ORDER (O) AND TRADE (T) HISTORY
	def O_hist(self, symbol=None, clientOrderId=None, orderData={}):
		call_args = ['history', 'order']
		if clientOrderId is not None: orderData.update({'clientOrderId':clientOrderId})
		elif symbol is not None: orderData.update({'symbol':symbol})
		return self.auth_call(call_args, orderData)

	def T_hist(self, symbol=None, limit=100, orderData={}):
		call_args = ['history', 'trades']
		orderData.update({'symbol':symbol}) if symbol is not None else None 
		orderData.update({'limit':limit}) if limit!=100 else None 
		return self.auth_call(call_args, orderData)

	def trade_data(self, orderId):
		call_args = ['history', 'order', 'orderId', 'trades']
		return self.auth_call(call_args)


	'''
	#METHODS FOR CREATING NEW ORDERS

	Creating an order will return some data including the order's ID.
	This ID will be generated by the server. It is possible to choose one's own orderId for each order.
	Functionality for doing this is not, at time of writing, included in this wrapper.
	If you want to do that, take a look at the API documentation; shouldn't be too hard :3
	'''

	def order(self, orderData):
		call_args = ['order']
		return self.auth_call(call_args, orderData, 'post')

	def limit_order(self, symbol, side, quantity, price, 
					timeInForce=None, expireTime=None, strictValidate=None):
		orderData = {'symbol':symbol, 'side':side, 'quantity':str(quantity), 'price':str(price)}
		if timeInForce is not None: orderData.update({'timeInForce':timeInForce})
		if expireTime is not None: orderData.update({'expireTime':expireTime})
		if strictValidate is not None: orderData.update({'strictValidate':strictValidate})
		return self.order(orderData)

	def FOK(self, symbol, side, quantity, price, strictValidate=None):
		return self.limit_order(symbol, side, quantity, price, 'FOK', strictValidate=strictValidate)

	def IOC(self, symbol, side, quantity, price, strictValidate=None):
		return self.limit_order(symbol, side, quantity, price, 'IOC', strictValidate=strictValidate)

	def GTD(self, symbol, side, quantity, price, expireTime, strictValidate=None):
		return self.limit_order(symbol, side, quantity, price, 'GTD', expireTime, strictValidate)

	def day_order(self, symbol, side, quantity, price, strictValidate=None):
		return self.limit_order(symbol, side, quantity, price, 'Day', strictValidate=strictValidate)

	def market_order(self, symbol, side, quantity, strictValidate=None):
		orderData={'symbol':symbol, 'side':side, 'type':'market', 'quantity':str(quantity)}
		if strictValidate is not None: orderData.update({'strictValidate':strictValidate})
		return self.order(orderData)

	def stop_limit(self, symbol, side, quantity, price, stopPrice, strictValidate=None):
		orderData={'symbol':symbol, 'side':side, 'type':'stopLimit', 
				   'quantity':str(quantity), 'price':str(price), 'stopPrice':str(stopPrice)}
		if strictValidate is not None: orderData.update({'strictValidate':strictValidate})
		return self.order(orderData)

	def stop_market(self, symbol, side, quantity, stopPrice, strictValidate=None):
		orderData={'symbol':symbol, 'side':side, 'type':'stopMarket', 
				   'quantity':str(quantity), 'stopPrice':str(stopPrice)}
		if strictValidate is not None: orderData.update({'strictValidate':strictValidate})
		return self.order(orderData)


	#METHODS FOR CANCELING EXISTING ORDERS
	def cancel(self, pair=None, clientOrderId=None): 
		#IMPORTANT: If pair and clientOrderId are both None, this will cancel ALL ORDERS.
		#Therefore it is recommended that one uses the methods below for specific types of cancellation.
		call_args=['order']
		if pair is not None: call_args.append(pair)
		elif clientOrderId is not None: call_args.append(clientOrderId)
		return self.auth_call(args)

	def cancel_all(self):
		return self.cancel()

	def cancel_all_of_pair(pair):
		return self.cancel(pair)

	def cancel_ID(self, clientOrderId):
		if self.streaming_api==False:
			return self.cancel(clientOrderId=clientOrderId)
		pass
		'''
		methods: cancelOrder
		params: clientOrderId: your_order_id
		id: some_number
		'''

	def cancel_replace(self, clientOrderId, requestClientId, quantity, price, strictValidate=None):
		if self.streaming_api==False: 
			raise Exception('Errno 102: Method only available for websocket API.')

		'''
		method: cancelReplaceOrder
		params: clientOrderId:your_order_id, requestClientId:previous_request_id, 
				quantity:some_number, price:some_number
				optional--strictValidate:boolean (if None then False)
		id: some_number
		'''

	'''	
	SOME NOTES:

	EX:
	orderData = {'symbol':'ethbtc', 'side': 'sell', 'quantity': '0.063', 'price': '0.046016' }
    r = requests.post('https://api.hitbtc.com/api/2/order', data = orderData, auth=('ff20f250a7b3a414781d1abe11cd8cee', 'fb453577d11294359058a9ae13c94713'))        
    print(r.json())

	TRADING: 
	POST /api/2/order
	PUT /api/2/order/{clientOrderId}

	price and quantity; price must be divisible by ticksize without remainder.

	need to assemble orderData as a dict:
	{'symbol':'ethbtc', 'side':'sell', 'quantity':'0.063', 'price':'0.046016'}
		OPTIONAL
			'type':'limit'|'market'|'stopLimit'|'stopMarket' -default is limit
			'timeInForce':'GTC'|'IOC'|'FOK'|'Day'|'GTD' -default is GTC
			'price':'some number' --required on non-market orders.
			'stopPrice':'some number' --required on stopX orders.
			'expireTime':'some DateTime' -- requited for GTD and timeInForce orders.
			'strictValidate':'True'|'False' -- checks tick-size compliance. 
				If False|None and _uncompliant_ server rounds down price &| quantity and order is placed.
				If True and _uncompliant_ server returns invalid error and order is not placed.

	The request is then submitted in the form of .go.post(url, data=orderData) and auth is taken care of by the session auth.
	
	Cancel orders 
	DELETE /api/2/order - deletes all orders
		Optional:
			/pair - filters orders by pair
			/clientOrderId - specify order by id

	Get trading comissions
	GET /api/2/trading/fee/symbol - returns personal fees for that symbol
		This will be the standard rate unless you're on a hitBTC market maker contract.

	Get personal order history
	GET /api/2/history/order - returns all open orders
		Optional: orderData dict format as above
			'symbol': 'pair'
			'clientOrderId': 'some id'
			'from': 'Datetime'
			'till': 'Datetime'
			'limit': 'some number' #number of responses desired
			'offset': 'some number' # ?? not sure what this does


	Get personal trade history
	GET /api/2/history/trades - returns trade history
		Optional: orderData dict form as with history with additions of:
			'sort':'DESC'|'ASC' - default is Descending
			'by': 'timestamp'|'id' - default is timestamp

	Get trades by order
	GET /api/2/history/order/{orderId}/trades - returns trade (or trades if sold in partials) for that orderId
		takes only str(int(orderId))

	OTHER THINGS TO BUILD LATER:
		get addresses
		create new addresses
		withdraw to some address
		transfer from account to trading balance
		get transaction history (withdrawls and deposits)

	The wss api is based around the construction of a dictionary request.
	It's send alongside the baseurl wss://api.hitbtc.com/api/2/ws

	The dictionary follows this architecture: 
	{'method':'some_method', 'params':{param_keyword1:param1, param_keyword2:param2, etc}}
	
	'''




