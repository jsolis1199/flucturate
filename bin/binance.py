#!/usr/bin/env python3.7

import sys
from pathlib import Path
from os import environ
from json import loads
from datetime import datetime

from pytz import utc
from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
import kafka

from standardize import standardize

exchanges = {
        'com': 'binance',
        'je': 'binance_jersey',
        'us': 'binance_us'
        }
if len(sys.argv) < 3:
    print(f'Usage: {sys.argv[0]} ext symbols')
    sys.exit(1)
elif sys.argv[1] not in exchanges:
    print(f'{sys.argv[1]} is not a valid extension')
    sys.exit(1)
ext = sys.argv[1]
path = str(Path(__file__).parent.parent.absolute()) + '/tmp'
with open(f'{path}/{exchanges[ext]}.pair', 'r') as f:
    split_symbols = [e.replace('\n', '') for e in f.readlines()]
with open(f'{path}/{exchanges[ext]}.base', 'r') as f:
    bases = [e.replace('\n', '') for e in f.readlines()]
with open(f'{path}/{exchanges[ext]}.quote', 'r') as f:
    quotes = [e.replace('\n', '') for e in f.readlines()]
split_symbols = zip(split_symbols, bases, quotes)
split_symbols = {s: (b, q) for s, b, q in split_symbols}
manager = BinanceWebSocketApiManager(exchange=f'binance.{ext}')
pairs = sys.argv[2:]
manager.create_stream('trade', pairs)
host = f'{environ["KAFKA_MASTER"]}:9092'
producer = kafka.KafkaProducer(bootstrap_servers=host)
kafka.KafkaClient(host).ensure_topic_exists('all')
try:
    while True:
        payload = manager.pop_stream_data_from_stream_buffer()
        if payload:
            data = loads(payload)['data']
            t = datetime.fromtimestamp(data['T'] / 1000, tz=utc)
            p = data['p']
            q = data['q']
            s = data['s']
            base, quote = split_symbols[s]
            base, quote = standardize(base, quote)
            key = ','.join((str(t), base, quote, exchanges[ext])).encode()
            value = ','.join((p, q)).encode()
            producer.send('all', key=key, value=value)
except KeyboardInterrupt:
    manager.stop_manager_with_all_streams()
    sys.exit(0)
