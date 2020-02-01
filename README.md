# FluctuRate

The cryptocurrency market evaluator

## Setup
Install third-party packages
```shell
pip3 install websocket-client==0.40.0
pip3 install kafka-python pyspark pytz bitfinex-api-py copra hitbtc 
```
The default `websocket-client` dependency (v0.57.0 at time of writing) installed via `pip3 install hitbtc` causes the HitBTC producer to fail.

Initialize Cassandra keyspace
```sql
CREATE KEYSPACE flucturate WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 2};
CREATE TABLE trades(base text, quote text, time timestamp, exchange text, price double, quantity double, PRIMARY KEY ((base, quote), time, exchange));
CREATE TABLE diffs(base text, quote text, start timestamp, exchanges text, diff double, PRIMARY KEY ((base, quote), start, exchanges));
```

## Usage

Enter directory
```shell
cd flucturate
```

Start Kafka
```shell
kafka-server-start.sh $KAFKA_HOME/config/server.properties >> log/kafka.log 2>&1
```

Start producers
```shell
bin/bitfinex.py `tr '\n' ' ' < tmp/bitfinex.txt` >> log/bitfinex.log 2>&1
bin/coinbase.py `tr '\n' ' ' < tmp/coinbase.txt` >> log/coinbase.log 2>&1
bin/hitbtc_.py `tr '\n' ' ' < tmp/hitbtc.txt` >> log/hitbtc.log 2>&1
bin/kraken.py trade `tr '\n' ' ' < tmp/kraken.txt` >> log/kraken.log 2>&1
```

Start aggregator and consumer
```shell
bin/aggregator.py >> log/aggregator.log 2>&1
bin/consumer.py >> log/consumer.log 2>&1
```
