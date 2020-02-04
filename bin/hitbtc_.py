#!/usr/bin/env python3.7

from pathlib import Path
from time import sleep
from sys import argv
from os import environ
from queue import Empty
from datetime import datetime

from hitbtc import HitBTC
import kafka

from standardize import standardize

path = str(Path(__file__).parent.parent.absolute()) + '/tmp'
with open(f'{path}/hitbtc.pair', 'r') as f:
    split_symbols = [e.replace('\n', '') for e in f.readlines()]
with open(f'{path}/hitbtc.base', 'r') as f:
    bases = [e.replace('\n', '') for e in f.readlines()]
with open(f'{path}/hitbtc.quote', 'r') as f:
    quotes = [e.replace('\n', '') for e in f.readlines()]
split_symbols = zip(split_symbols, bases, quotes)
split_symbols = {s: (b, q) for s, b, q in split_symbols}
split_symbols = {
        s: (split_symbols[s][0], 'USDT')
        if s[-4:] == 'USDT' and split_symbols[s][1] == 'USD'
        else split_symbols[s]
        for s in split_symbols
        }
host = f'{environ["KAFKA_MASTER"]}:9092'
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
