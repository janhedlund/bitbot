#NOTE: All returned objects returned as JSON files.

import time as t
import hmac
import hashlib
from urllib.parse import urlencode # was in a a try/except
from Crypto.Cipher import AES #was in a try/except/else ; else remains below and is needed for other things.
import requests as rq
import getpass
import ast
import json

encrypted = True

#ORDERBOOK ARGS
buybook = 'buy'
sellbook = 'sell'
wholebook = 'both'

#CANDLE WIDTHS
minute = 'oneMin'
fivemin = 'fiveMin'
thirtymin = 'thirtyMin'
hour = 'hour'
day = 'Day'

#LIMIT OR MARKET
limit = 'LIMIT'
market = 'MARKET'

#TIME IN EFFECT
good_til_cancel = 'GOOD_TIL_CANCELLED'
immediate_or_cancel = 'IMMEDIATE_OR_CANCEL'
fill_kill = 'FILL_OR_KILL'

#CONDITION TYPES
none = 'NONE'
grth = 'GREATER_THAN'
leth = 'LESS_THAN'
stoploss_fixed = 'STOP_LOSS_FIXED'
stoploss_per = 'STOP_LOSS_PERCENTAGE'

#API VERSIONS
v1 = 'v1.1'
v2 = 'v2.0'

#BASE URLS CORRESPONDNG TO API VERSIONS
url_v1 = 'https://bittrex.com/api/v1.1{path}?'
url_v2 = 'https://bittrex.com/api/v2.0{path}?'

#PROTECTION TYPES (i.e. encrypted or non)
pub = 'pub'  # public methods
prv = 'prv'  # authenticated methods


def encrypt(api_key, api_secret, export=True, export_fn='secrets.json'):
    cipher = AES.new(getpass.getpass(
        'Input encryption password (string will not show)'))
    api_key_n = cipher.encrypt(api_key)
    api_secret_n = cipher.encrypt(api_secret)
    api = {'key': str(api_key_n), 'secret': str(api_secret_n)}
    if export:
        with open(export_fn, 'w') as outfile:
            json.dump(api, outfile)
    return api

def using_requests(request_url, apisign):
    return rq.get(
        request_url,
        headers={"apisign": apisign}
    ).json()


class Bittrex(object):

    def __init__(self, api_key, api_secret, calls_per_second=1, dispatch=using_requests, api_version=v1):
        self.api_key = str(api_key) if api_key is not None else ''
        self.api_secret = str(api_secret) if api_secret is not None else ''
        self.dispatch = dispatch
        self.call_rate = 1.0 / calls_per_second
        self.last_call = None
        self.api_version = api_version

    def decrypt(self):
        cipher = AES.new(getpass.getpass(
            'Input decryption password (string will not show)'))
        try:
            if isinstance(self.api_key, str):
                self.api_key = ast.literal_eval(self.api_key)
            if isinstance(self.api_secret, str):
                self.api_secret = ast.literal_eval(self.api_secret)
        except Exception:
            pass
        self.api_key = cipher.decrypt(self.api_key).decode()
        self.api_secret = cipher.decrypt(self.api_secret).decode()


    def wait(self):
        if self.last_call is None:
            self.last_call = t.time()
        else:
            now = t.time()
            passed = now - self.last_call
            if passed < self.call_rate:
                # print("sleep")
                t.sleep(self.call_rate - passed)

            self.last_call = t.time()

    def _api_query(self, protection=None, path_dict=None, options=None):
       #Sends request to bittrex; builds request url based on what function called it.
       # rtype: dict

        if not options:
            options = {}

        #if self.api_version not in path_dict:
        #    raise Exception('method call not available under API version {}'.format(self.api_version))

        request_url = url_v2 if self.api_version == v2 else url_v1
        request_url = request_url.format(path=path_dict[self.api_version])

        nonce = str(int(t.time() * 1000))

        if protection != pub:
            request_url = "{0}apikey={1}&nonce={2}&".format(request_url, self.api_key, nonce)

        request_url += urlencode(options)

        try:
            apisign = hmac.new(self.api_secret.encode(),
                               request_url.encode(),
                               hashlib.sha512).hexdigest()

            self.wait()

            return self.dispatch(request_url, apisign)

        except Exception:
            return {
                'success': False,
                'message': 'No Response',
                'result': None
            }

    def get_markets(self):
        #api v1.1 only
        return self._api_query(path_dict={
            v1: '/public/getmarkets',
        }, protection=pub)

    def get_currencies(self):
        # v1.1 and v2.0 : returns all supported currencies and respective metadata as dict.
        return self._api_query(path_dict={
            v1: '/public/getcurrencies',
            v2: '/pub/Currencies/GetCurrencies'
        }, protection=pub)

    def get_ticker(self, market):
        # api v1.1 only - for v2.0 use get_candles(). Returns latest data - last,bid,ask
        # rtype: dict
        return self._api_query(path_dict={
            v1: '/public/getticker',
        }, options={'market': market}, protection=pub)

    def get_market_summaries(self):
        # api v1.1 and v2.0. Returns vast summary of all active exchanges.
        # rtype: dict. Very excessive. Didn't like.
        return self._api_query(path_dict={
            v1: '/public/getmarketsummaries',
            v2: '/pub/Markets/GetMarketSummaries'
        }, protection=pub)

    def get_marketsummary(self, market):
        # api v1.1 and v2.0.
        # market takes a string literal (ie 'btc-ltc'), returns summary of that market
        # rtype: dict. Much more manageable than above, still better methods below imo.
        return self._api_query(path_dict={
            v1: '/public/getmarketsummary',
            v2: '/pub/Market/GetMarketSummary'
        }, options={'market': market, 'marketname': market}, protection=pub)

    def get_orderbook(self, market, depth_type=wholebook):
        # api v1.1 and v2.0.
        # depth_type takes buybook|sellbook|wholebook
        # rtype: dict
        return self._api_query(path_dict={
            v1: '/public/getorderbook',
            v2: '/pub/Market/GetMarketOrderBook'
        }, options={'market': market, 'marketname': market, 'type': depth_type}, protection=pub)

    def get_market_history(self, market):
        # api v1.1 only.
        # market takes string literal (ie 'btc-ltc'). Returns latest trades for that market as dict.
        return self._api_query(path_dict={
            v1: '/public/getmarkethistory',
        }, options={'market': market, 'marketname': market}, protection=pub)

    def buy_limit(self, market, quantity, rate):
        # api v1.1. For v2.0, use trade_buy() for limit|market buys.
        # market : str (i.e. 'btc-ltc')
        # quantity&rate : float 
        # rtype: dict
        return self._api_query(path_dict={
            v1: '/market/buylimit',
        }, options={'market': market,
                    'quantity': quantity,
                    'rate': rate}, protection=prv)

    def sell_limit(self, market, quantity, rate):
        # api v1.1. For v2.0, use trade_sell() for limit|market sales.
        # market : str (i.e. 'btc-ltc')
        # quantity&rate : float 
        # rtype: dict
        return self._api_query(path_dict={
            v1: '/market/selllimit',
        }, options={'market': market,
                    'quantity': quantity,
                    'rate': rate}, protection=prv)

    def cancel(self, uuid):
        # api v1.1 and v2.0.
        # takes buy/sell order uuid as str and cancels it.
        # rtype: dict
        return self._api_query(path_dict={
            v1: '/market/cancel',
            v2: '/key/market/tradecancel'
        }, options={'uuid': uuid, 'orderid': uuid}, protection=prv)

    def get_open_orders(self, market=None):
        # api v1.1 and v2.0.
        # market takes string literal (ie 'btc-ltc') - returns account's open orders in that market. 
        # rtype: dict  - If market=None, returns all.
        return self._api_query(path_dict={
            v1: '/market/getopenorders',
            v2: '/key/market/getopenorders'
        }, options={'market': market, 'marketname': market} if market else None, protection=prv)

    def get_balances(self):
        # api v1.1 and v2.0. - returns all account balances.
        # rtype: dict 
        return self._api_query(path_dict={
            v1: '/account/getbalances',
            v2: '/key/balance/getbalances'
        }, protection=prv)

    def get_balance(self, currency):
        # api v1.1 and v2.0.
        # currency takes a string literal (ie 'btc'), returns account balance of that currency.
        # rtype: dict
        return self._api_query(path_dict={
            v1: '/account/getbalance',
            v2: '/key/balance/getbalance'
        }, options={'currency': currency, 'currencyname': currency}, protection=prv)

    def get_deposit_address(self, currency):
        # api v1.1 and v2.0.
        # currency takes a string literal - generates or retrieves deposit address for currency 
        # rtyped: dict
        return self._api_query(path_dict={
            v1: '/account/getdepositaddress',
            v2: '/key/balance/getdepositaddress'
        }, options={'currency': currency, 'currencyname': currency}, protection=prv)

    def withdraw(self, currency, quantity, address):
        # api v1.1 and v2.0.
        # currency & address take strings - quantity takes float
        # withdraws {quantity} of {currency} to {address}
        # rtype: dict
        return self._api_query(path_dict={
            v1: '/account/withdraw',
            v2: '/key/balance/withdrawcurrency'
        }, options={'currency': currency, 'quantity': quantity, 'address': address}, protection=prv)

    def get_order_history(self, market=None):
        # api v1.1 and v2.0.
        # market takes string literal (ie 'btc-ltc'). Returns account's order history for that market
        # rtype: dict - If market=None, returns all.
        if market:
            return self._api_query(path_dict={
                v1: '/account/getorderhistory',
                v2: '/key/market/GetOrderHistory'
            }, options={'market': market, 'marketname': market}, protection=prv)
        else:
            return self._api_query(path_dict={
                v1: '/account/getorderhistory',
                v2: '/key/orders/getorderhistory'
            }, protection=prv)

    def get_order(self, uuid):
        # api v1.1 and v2.0. Takes the uuid of a buy or sell order as a string.
        # returns data rtype: dict
        return self._api_query(path_dict={
            v1: '/account/getorder',
            v2: '/key/orders/getorder'
        }, options={'uuid': uuid, 'orderid': uuid}, protection=prv)

    def get_withdrawal_history(self, currency=None):
        # api v1.1 and v2.0. Currency takes a string literal. If currency=None, returns all. 
        # rtype: dict
        return self._api_query(path_dict={
            v1: '/account/getwithdrawalhistory',
            v2: '/key/balance/getwithdrawalhistory'
        }, options={'currency': currency, 'currencyname': currency} if currency else None,
            protection=prv)

    def get_deposit_history(self, currency=None):
        # api v1.1 and v2.0. Currency takes a strign literal. If currency=None, returns all.
        # rtype: dict.
        return self._api_query(path_dict={
            v1: '/account/getdeposithistory',
            v2: '/key/balance/getdeposithistory'
        }, options={'currency': currency, 'currencyname': currency} if currency else None,
            protection=prv)

    def list_markets_by_currency(self, currency):
        # api v1.1 and v2.0 - Takes a string literal (ie. 'ltc').
        # returns all markets for that currency (ie ['BTC-LTC', 'ETH-LTC', 'USDT-LTC']) as a list of strings.
        return [market['MarketName'] for market in self.get_markets()['result']
                if market['MarketName'].lower().endswith(currency.lower())]

    def get_wallet_health(self):
        # api v2.0 only
        return self._api_query(path_dict={
            v2: '/pub/Currencies/GetWalletHealth'
        }, protection=pub)

    def get_balance_distribution(self):
        # api v2.0 only
        return self._api_query(path_dict={
            v2: '/pub/Currency/GetBalanceDistribution'
        }, protection=pub)

    def get_pending_withdrawals(self, currency=None):
        # api v2.0 only, does what it says on the tin
        # if currency takes a string literal. if currency=None, returns all. 
        return self._api_query(path_dict={
            v2: '/key/balance/getpendingwithdrawals'
        }, options={'currencyname': currency} if currency else None,
            protection=prv)

    def get_pending_deposits(self, currency=None):
        # see 'get_pending_withdrawls()' above
        return self._api_query(path_dict={
            v2: '/key/balance/getpendingdeposits'
        }, options={'currencyname': currency} if currency else None,
            protection=prv)

    def generate_deposit_address(self, currency):
        # api v2.0 only. creates new deposit address for currency (takes string literal)
        # returns dict
        return self._api_query(path_dict={
            v2: '/key/balance/getpendingdeposits'
        }, options={'currencyname': currency}, protection=prv)

    def trade_sell(self, market=None, order_type=None, quantity=None, rate=None, time_in_effect=None,
                   condition_type=None, target=0.0):
        '''
        api v2.0 only. 
        market takes ie 'btc-ltc', order_types takes 'limit'|'market'
        quantity & rate take float - rate isn't needed for 'limit'
        time_in_effect takes fill_kill|immediate_or_cancel|good_til_cancel
        see condition_types at top.
        Target takes a float - only used if condition_type is also used (target of the condition)
        returns a dict
        '''
        return self._api_query(path_dict={
            v2: '/key/market/tradesell'
        }, options={
            'marketname': market,
            'ordertype': order_type,
            'quantity': quantity,
            'rate': rate,
            'timeInEffect': time_in_effect,
            'conditiontype': condition_type,
            'target': target
        }, protection=prv)

    def trade_buy(self, market=None, order_type=None, quantity=None, rate=None, time_in_effect=None,
                  condition_type=None, target=0.0):
        # see 'trade_sell()' above
        return self._api_query(path_dict={
            v2: '/key/market/tradebuy'
        }, options={
            'marketname': market,
            'ordertype': order_type,
            'quantity': quantity,
            'rate': rate,
            'timeInEffect': time_in_effect,
            'conditiontype': condition_type,
            'target': target
        }, protection=prv)

    def get_candles(self, market, width):
        # api v2.0 only, returns all candles of size 'width' 
        # starts with oldest, returns O,H,L,C,Vol,T,BV
        return self._api_query(path_dict={
            v2: '/pub/market/GetTicks'
        }, options={
            'marketName': market, 'tickInterval': width
        }, protection=pub)

    def get_latest_candle(self, market, width):
        # api v2.0 only.
        #returns latest candle of type 'width' - O,H,L,C,V,T,BV (V=candle vol, BV=BTC vol daily)
        return self._api_query(path_dict={
            v2: '/pub/market/GetLatestTick'
        }, options={
            'marketName': market, 'tickInterval': width
        }, protection=pub)


#example:
bot=Bittrex(None,None,1,using_requests,v2)
coins=bot.get_currencies()['result']
for coin in coins:
    print('{}:{}'.format(coins.index(coin)+1, coin['Currency']))











