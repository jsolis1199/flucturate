# FluctuRate

The cryptocurrency market evaluator

## Setup
Install third-party packages (to install specifically for `python3.7` replace `pip3` with `python3.7 -m pip`)
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
kafka-server-start.sh "${KAFKA_HOME}/config/server.properties" >> log/kafka.log 2>&1
```

Start producers
```shell
bin/binance.py com `tr '\n' ' ' < tmp/binance.pair` >> log/binance.log 2>&1
bin/binance.py je `tr '\n' ' ' < tmp/binance_jersey.pair` >> log/binance_jersey.log 2>&1
bin/binance.py us `tr '\n' ' ' < tmp/binance_us.pair` >> log/binance_us.log 2>&1
bin/bitfinex.py `tr '\n' ' ' < tmp/bitfinex.pair` >> log/bitfinex.log 2>&1
bin/coinbase.py `tr '\n' ' ' < tmp/coinbase.pair` >> log/coinbase.log 2>&1
bin/hitbtc_.py `tr '\n' ' ' < tmp/hitbtc.pair` >> log/hitbtc.log 2>&1
bin/kraken.py trade `tr '\n' ' ' < tmp/kraken.pair` >> log/kraken.log 2>&1
```

Start aggregator and consumer
```shell
spark-submit --master "spark://${AGGREGATOR_MASTER}:7077" --packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.0,com.datastax.spark:spark-cassandra-connector_2.11:2.3.0 --conf spark.cassandra.connection.host="${CASSANDRA_MASTER}" bin/aggregator.py >> log/aggregator.log 2>&1
spark-submit --master "spark://${CONSUMER_MASTER}:7077" --packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.0,com.datastax.spark:spark-cassandra-connector_2.11:2.3.0 --conf spark.cassandra.connection.host="${CASSANDRA_MASTER}" bin/consumer.py >> log/consumer.log 2>&1
```
