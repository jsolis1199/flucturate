#!/usr/bin/env python3

from sys import argv
from asyncio import get_event_loop
from datetime import datetime # .fromisoformat requires python3.7+

from copra.websocket import Client as COPRAClient
from copra.websocket import Channel
import kafka

class Client(COPRAClient):
    def __init__(self, loop, channels, feed_url='wss://ws-feed.pro.coinbase.com:443', auth=False, key='', secret='', passphrase='', auto_connect=True, auto_reconnect=True, name='WebSocket Client'):
        COPRAClient.__init__(self, loop, channels, feed_url=feed_url, auth=auth, key=key, secret=secret, passphrase=passphrase, auto_connect=auto_connect, auto_reconnect=auto_reconnect, name=name)

    def on_message(self, message):
        if message['type'] == 'match':
            t = datetime.fromisoformat(message['time'].replace('Z', '+00:00'))
            p = message['price']
            q = message['size']
            base, quote = message['product_id'].split('-')
            base = 'XBT' if base == 'BTC' else base
            quote = 'XBT' if quote == 'BTC' else quote
            key = ','.join((str(t), base, quote, 'coinbase')).encode()
            value = ','.join((str(p), str(q))).encode()
            producer.send('all', key=key, value=value)
        else:
            print(message)

pairs = argv[1:]
host = 'localhost:9092'
producer = kafka.KafkaProducer(bootstrap_servers=host)
kafka.KafkaClient(host).ensure_topic_exists('all')
loop = get_event_loop()
client = Client(loop, Channel('matches', pairs))

try:
    loop.run_forever()
except KeyboardInterrupt:
    loop.run_until_complete(client.close())
    loop.close()
