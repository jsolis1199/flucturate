#!/usr/bin/env python3.7

from time import sleep
from sys import argv
from queue import Empty
from datetime import datetime

from hitbtc import HitBTC
import kafka

from standardize import standardize

def split_symbol(symbol):
    if symbol[-6:] == 'USDT20':
        return symbol[:-6], symbol[-6:]
    elif symbol[-5:] == 'EOSDT':
        return symbol[:-5], symbol[-5:]
    elif symbol[-4:] in ['EURS', 'IDRT', 'KRWB', 'USDT', 'USDC']:
        return symbol[:-4], symbol[-4:]
    elif symbol[-4:] == 'TUSD' and symbol[:-4] in ['ETH', 'BTC', 'LTC', 'XMR', 'ZRX', 'NEO', 'USD', 'EURS', 'DGB', 'BCH']:
        return symbol[:-4], symbol[-4:]
    elif symbol[-4:] == 'GUSD' and symbol[:-4] in ['USDT', 'BTC', 'ETH', 'EOS']:
        return symbol[:-4], symbol[-4:]
    elif (symbol[:-4], symbol[-4:]) == ('BTC', 'BUSD'):
        return symbol[:-4], symbol[-4:]
    else:
        return symbol[:-3], symbol[-3:]

host = 'localhost:9092'
producer = kafka.KafkaProducer(bootstrap_servers=host)
kafka.KafkaClient(host).ensure_topic_exists('all')
client = HitBTC()
client.start()
sleep(2)
pairs = argv[1:]
custom_id = 0
for symbol in pairs:
    custom_id += 1
    client.subscribe_trades(symbol=symbol, custom_id=custom_id)
while True:
    try:
        response = client.recv()
    except Empty:
        continue
    type_, symbol, payload = response
    if type_ == 'updateTrades':
        for message in payload['data']:
            t = datetime.fromisoformat(message['timestamp'].replace('Z', '+00:00'))
            p = message['price']
            q = message['quantity']
            base, quote = split_symbol(symbol)
            base, quote = standardize(base, quote)
            key = ','.join((str(t), base, quote, 'hitbtc')).encode()
            value = ','.join((str(p), str(q))).encode()
            producer.send('all', key=key, value=value)

client.stop()
