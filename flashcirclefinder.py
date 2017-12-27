from hitapi import *

dimbot = HitBot(None, None, 100, 'stream')


class CurBot(object):
	
	def __init__(self, asks, bids, market):
		self.market = str(market)
		self.asks = dimbot.sell_orders(self.market)
		self.bids = dimbot.buy_orders(self.market)

	def bestask(self):
		return float(sorted(self.asks)[0])

	def bestbid(self):
		return float(sorted(self.bids)[-1])

	def volask(self):
		return float(self.asks[self.bestask()])

	def volbid(self):
		return float(self.bids[self.bestbid()])

def clock(oneask, twobid, threeask):
	#return 'DimPriceUSD: {} || Transform: {}'.format(oneask, twobid/threeask)
	if oneask*1.001 < (twobid*0.999)/(threeask*1.001): return True
	return False
	

def counter(oneask, twobid, threeask):
	#return 'DimPriceUSD: {} || Transform: {}'.format(oneask, twobid*threeask)
	if oneask*1.001 < twobid*threeask*0.999**2: return True
	return False

def test(pairs):
	loops=0
	while True:
		one = CurBot(0,0,pairs[0])
		two = CurBot(0,0,pairs[2])
		three = CurBot(0,0,pairs[1])
		one1=one.bestask()
		two1=two.bestbid()
		one2=two.bestask()
		two2=one.bestbid()
		three=three.bestask()
		if clock(one1, two1, three) or counter(one2, two2, three):
			break
		else: loops+=1
		if loops%10==0:
			print(loops)
		if loops>=5000:
			return False

xvg = ['xvgeth', 'ethusd', 'xvgusd']
dim = ['dimeth', 'ethusd', 'dimusd']
naga = ['ngceth', 'ethusd', 'ngcusd']
dimbit = ['dimeth', 'ethbit', 'dimbit']
print(test(dim))



