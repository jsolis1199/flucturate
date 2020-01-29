#!/usr/bin/env python3.7

# Kraken WebSocket API
# 
# Usage: ./kraken-producer.py feed [symbols]
# Example: ./kraken-producer.py trade XBT/USD
# Example: ./kraken-producer.py ticker XLM/USD XDG/XBT
# Example: ./kraken-producer.py book ETH/USD DASH/USD REP/EUR
# Example: ./kraken-producer.py openOrders
# Example: ./kraken-producer.py ownTrades

import sys
import platform
import time
import base64
import hashlib
import hmac
import json
from datetime import datetime
from pytz import utc

from websocket import create_connection
import kafka

if int(platform.python_version_tuple()[0]) > 2:
    import urllib.request as urllib2
else:
    import urllib2

api_status = {"ping"}
api_public = {"trade", "book", "ticker", "spread", "ohlc"}
api_private = {"openOrders", "ownTrades"}
api_rest_domain = "https://api.kraken.com"
api_rest_path = "/0/private/GetWebSocketsToken"

if len(sys.argv) < 2:
    api_feed = "ping"
else:
    api_feed = sys.argv[1]

if api_feed in api_status:
    api_domain = "wss://ws.kraken.com/"
    api_data = '{"event":"%(feed)s"}' % {"feed":api_feed}
elif api_feed in api_public:
    if len(sys.argv) < 3:
        print("Usage: %s feed symbols" % sys.argv[0])
        print("Example: %s ticker XBT/USD" % sys.argv[0])
        sys.exit(1)
    api_symbols = sys.argv[2].upper()
    for count in range(3, len(sys.argv)):
        api_symbols = api_symbols + '","' + sys.argv[count].upper()
    api_data = '{"event":"subscribe", "subscription":{"name":"%(feed)s"}, "pair":["%(symbols)s"]}' % {"feed":api_feed, "symbols":api_symbols}
    api_domain = "wss://ws.kraken.com/"
elif api_feed in api_private:
    try:
        api_key = open("API_Public_Key").read().strip()
        api_secret = base64.b64decode(open("API_Private_Key").read().strip())
    except:
        print("API public key and API private key must be in text files called API_Public_Key and API_Private_Key")
        sys.exit(1)
    api_nonce = str(int(time.time()*1000))  
    api_postdata = "nonce=" + api_nonce
    api_postdata = api_postdata.encode('utf-8')
    api_sha256 = hashlib.sha256(api_nonce.encode('utf-8') + api_postdata).digest()
    api_hmacsha512 = hmac.new(api_secret, api_rest_path.encode('utf-8') + api_sha256, hashlib.sha512)
    api_request = urllib2.Request(api_rest_domain + api_rest_path, api_postdata)
    api_request.add_header("API-Key", api_key)
    api_request.add_header("API-Sign", base64.b64encode(api_hmacsha512.digest()))
    api_request.add_header("User-Agent", "Kraken WebSocket API")
    try:
        api_reply = json.loads(urllib2.urlopen(api_request).read().decode())
    except Exception as error:
        print("REST API call (GetWebSocketsToken) failed (%s)" % error)
        sys.exit(1)
    api_token = api_reply['result']['token']
    api_data = '{"event":"subscribe", "subscription":{"name":"%(feed)s", "token":"%(token)s"}}' % {"feed":api_feed, "token":api_token}
    api_domain = "wss://ws-auth.kraken.com/"
else:
    print("Usage: %s feed [symbols]" % sys.argv[0])
    print("Example: %s ticker XBT/USD" % sys.argv[0])
    sys.exit(1)

try:
    ws = create_connection(api_domain)
    print(ws.recv())
except Exception as error:
    print("WebSocket connection failed (%s)" % error)
    sys.exit(1)

try:
    ws.send(api_data)
    print(ws.recv())
except Exception as error:
    print("WebSocket subscription failed (%s)" % error)
    ws.close()
    sys.exit(1)

host = 'localhost:9092'
producer = kafka.KafkaProducer(bootstrap_servers=host)
kafka.KafkaClient(host).ensure_topic_exists('all')
while True:
    try:
        api_data = json.loads(ws.recv())
        if isinstance(api_data, list) and api_data[-2] == 'trade':
            base, quote = api_data[-1].split('/')
            for e in api_data[1]:
                p, q, t = e[:3]
                t = datetime.fromtimestamp(float(t), tz=utc)
                key = ','.join((str(t), base, quote, 'kraken')).encode()
                value = ','.join((str(p), str(q))).encode()
                producer.send('all', key=key, value=value)
        else:
            print(api_data)
    except KeyboardInterrupt:
        ws.close()
        sys.exit(0)
    except Exception as error:
        print("WebSocket message failed (%s)" % error)
        ws.close()
        sys.exit(1)

ws.close()
sys.exit(1)
