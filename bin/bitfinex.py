#!/usr/bin/env python3

from sys import argv
from datetime import datetime
from pytz import utc

from bfxapi import Client
import kafka

pairs = argv[1:]
bfx = Client()
host = 'localhost:9092'
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
    base = 'XBT' if base == 'BTC' else base
    quote = 'XBT' if quote == 'BTC' else quote
    key = ','.join((str(t), base, quote, 'bitfinex')).encode()
    value = ','.join((str(p), str(q))).encode()
    producer.send('all', key=key, value=value)
    
async def start():
    for e in pairs:
        await bfx.ws.subscribe('trades', 't' + e)

bfx.ws.on('connected', start)
#try:
bfx.ws.run()
#except KeyboardInterrupt:
#    bfx.ws.unsubscribe_all()
