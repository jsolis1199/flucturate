#!/usr/bin/env python3.7

from sys import argv
from os import environ
from datetime import datetime

from bfxapi import Client
from pytz import utc
import kafka

from standardize import standardize

pairs = argv[1:]
bfx = Client()
host = f'{environ["KAFKA_MASTER"]}:9092'
producer = kafka.KafkaProducer(bootstrap_servers=host)
kafka.KafkaClient(host).ensure_topic_exists('all')

@bfx.ws.on('error')
def log_error(err):
    print("Error: {}".format(err))

@bfx.ws.on('new_trade')
def log_trade(trade):
    t = datetime.fromtimestamp(trade['mts'] / 1000, tz=utc)
    p = trade['price']
    q = abs(trade['amount'])
    s = trade['symbol'][1:]
    if len(s) == 6:
        base = s[:3]
        quote = s[3:]
    else:
        base, quote = s.split(':')
    base, quote = standardize(base, quote)
    key = ','.join((str(t), base, quote, 'bitfinex')).encode()
    value = ','.join((str(p), str(q))).encode()
    producer.send('all', key=key, value=value)
    
async def start():
    for e in pairs:
        await bfx.ws.subscribe('trades', 't' + e)

bfx.ws.on('connected', start)
bfx.ws.run()
