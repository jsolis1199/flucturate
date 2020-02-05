# FluctuRate

Evaluating the Cryptocurrency Market

## Setup Cassandra Cluster

Install and start Cassandra
```shell
peg install cassandra-cluster cassandra
peg service cassandra-cluster start
```

Initialize Cassandra keyspace
```sql
CREATE KEYSPACE flucturate WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 2};
CREATE TABLE trades(base text, quote text, time timestamp, exchange text, price double, quantity double, PRIMARY KEY ((base, quote), time, exchange));
CREATE TABLE diffs(base text, quote text, start timestamp, exchanges text, diff double, PRIMARY KEY ((base, quote), start, exchanges));
```

Install producer dependencies (to install specifically for `python3.7` replace `pip3` with `python3.7 -m pip`)
```shell
pip3 install pytz unicorn-binance-websocket-api bitfinex-api-py copra hitbtc
pip3 uninstall websocket-client
pip3 install websocket-client==0.40.0
```
The default `websocket-client` dependency (v0.57.0 at time of writing) installed via `pip3 install hitbtc` causes the HitBTC producer to fail.

Add environment variables
```shell
export KAFKA_MANAGER=<KAFKA_MANAGER>
```

## Setup the Spark Clusters (Aggregator and Consumer)

Install and start Hadoop and Spark
```shell
peg install <spark-cluster> hadoop
peg install <spark-cluster> spark
peg service <spark-cluster> hadoop start
peg service <spark-cluster> spark start
```

Install pyspark
```shell
pip3 install pyspark
```

Add environment variables
```shell
export KAFKA_MANAGER=<KAFKA_MANAGER>
export CASSANDRA_MANAGER=<CASSANDRA_MANAGER>
```

## Setup the Kafka Clusters

Install and start Zookeeper and Kafka
```shell
peg install kafka-cluster zookeeper
peg install kafka-cluster kafka
peg service kafka-cluster zookeeper start
peg service kafka-cluster kafka start
```

Install kafka-python
```shell
pip3 install kafka-python
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
