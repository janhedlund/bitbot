import requests as rq 
import json

stat='get_stats'
header='get_block_header'
data = 'get_block_data'
trans = 'get_transaction_data'
spent = 'is_key_image_spent'

def call(params):
	base_url = 'https://moneroblocks.info/api'
	for param in params:
		base_url+='/{}'.format(str(param))
	base_url+='/'
	data = rq.get(base_url).json()
	return data

def stats():
	params=[stat]
	return call(params)

def height():
	return(stats()['height'])

def difficulty():
	return(stats()['difficulty'])

def hashrate():
	return(stats()['hashrate'])

def reward():
	return(stats()['last_reward'])

def header_by_height(someheight):
	params=[header, someheight]
	return call(params)

def header_by_hash(hashstring):
	params=[header, hashstring]
	return call(params)

def block_by_height(someheight):
	params=[data, someheight]
	return call(params)

def block_by_hash(hashstring):
	params=[data, hashstring]
	return call(params)

def transaction(hashstring):
	params=[trans, hashstring]
	return call(params)

def is_spent(keyimage):
	params=[spent, keyimage]
	return call(params)

def time_by_height(someheight):
	return header_by_height(someheight)['block_header']['timestamp']

def time_by_hash(hashstring):
	return header_by_hash(hashstring)['block_header']['timestamp']






