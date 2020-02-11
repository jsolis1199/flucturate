# FluctuRate: Evaluating the Cryptocurrency Market

## Table of Contents

1. [Motivation](README.md#motivation)
1. [File Overview](README.md#file-overview)
1. [Assumptions](README.md#assumptions)
1. [Setup](README.md#setup)
1. [Starting the pipeline](README.md#starting-the-pipeline)
1. [Contact Information](README.md#contact-information)

## Motivation

After Bitcoin's source code was made open source in 2009, thousands of
cryptocurrencies were created. A decade later, it is estimated that there 
are still over 1600 active cryptocurrencies available in the global market.
In addition, there are hundred of cryptocurrency exchanges across the world,
making it difficult for new traders to navigate the market.

FluctuRate is a data pipeline that consumes live trade data from 5
cryptocurrency exchanges, computes rate differences for currency pairs that
are common among the exchanges, and plots the differences. This way, traders
can determine what exchange offers the best rate to trade their
cryptocurrencies.

## File Overview

### bin/

`bin/` contains all of FluctuRate's executables, which are meant to be run with
`python3.7` or higher. The main executables can be grouped into producer scripts and
PySpark scripts. `bin/` also contains a `standardize.py` module that is
imported by the producers and a Dash front-end called `plot.py`.

#### Producer Scripts

FluctuRate consumes trades from the following 5 exchanges.

1. Binance
1. Bitfinex
1. Coinbase
1. HitBTC
1. Kraken

The exchanges each have a producer script of the same name that creates a connection
to the exchange's WebSocket API, subscribes to the trade channels of the currency
pairs supplied as command line arguments, and publishes incoming trades to the Kafka topic
`all`.

#### PySpark Scripts

Ingested trades are sent to `aggregator.py` to be binned into 1-minute windows
and used to compute an average price for each currency pair at each exchange.
`aggregator.py` publishes the averages to the Kafka topic `agg` and writes the
trades and their averages to their respective Cassandra column families.

`subtractor.py` then consumes the averages and splits the stream into a stream
for every pair of exchanges. Those streams are then used to compute exchange
rate differences, which are saved to the `diff` column family.

#### standardize.py

Source code for the `standardize` helper function that standardizes ticker symbols.
Currently, the only problematic symbols are those for Bitcoin and Dogecoin, which are 
standardized to `XBT` and `XDG` respectively.

#### Front-end

`plot.py` generates a plot of percentage differences in exchange rates for a particular
currency pair relative to a particular exchange. The currency pair and exchange are selected
via drop-down lists. 

### tmp/

`tmp/` contains text files that list the currency pairs available at the exchanges. 
The `.pair` files contain the pair symbols in the format accepted by the respective exchange.
Binance and HitBTC do not use a delimiter to separate the base and quote cryptocurrencies
appearing in their symbols, so those exchanges have additional `.base` and `.quote` files
to split each symbol into their base and quote.

### log/

`log/` is provided as a convenience directory to redirect the output of FluctuRate's executables.
It's usage is optional and can be ignored.

## Assumptions

* Each Spark cluster has a Hadoop Distributed File System with a `/ckpt` directory
* The lists in `tmp/` contain all the currency pairs traded at the exchanges  (may not be true after several months)

## Setup

If using [Pegasus](https://github.com/InsightDataScience/pegasus/) to provision
your cluster, set the framework variables in `install/download_tech` to the following.
```shell
CASSANDRA_VER=3.11.5
HADOOP_VER=2.7.6
KAFKA_VER=2.4.0
KAFKA_SCALA_VER=2.13
SPARK_VER=2.4.4
SPARK_HADOOP_VER=2.7
ZOOKEEPER_VER=3.4.13
```

### Setup Cassandra Cluster

Install and start Cassandra
```shell
peg install cassandra-cluster cassandra
peg service cassandra-cluster start
```

Initialize Cassandra keyspace
```sql
CREATE KEYSPACE flucturate WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 2};
CREATE TABLE trades(base text, quote text, time timestamp, exchange text, price double, quantity double, PRIMARY KEY ((base, quote), time, exchange));
CREATE TABLE averages(base text, quote text, start timestamp, exchange text, price double, PRIMARY KEY ((base, quote), start, exchange));
CREATE TABLE diffs(base text, quote text, start timestamp, exchanges text, diff double, PRIMARY KEY ((base, quote), start, exchanges));
```

Install producer dependencies (to install specifically for `python3.7` replace `pip3` with `python3.7 -m pip`)
```shell
pip3 install kafka-python pytz unicorn-binance-websocket-api bitfinex-api-py copra hitbtc
pip3 uninstall websocket-client
pip3 install websocket-client==0.40.0
```
The default `websocket-client` dependency (v0.57.0 at time of writing) installed via `pip3 install hitbtc` causes the HitBTC producer to fail.

Install front-end dependencies
```shell
pip3 install dash cassandra-driver 
```

Add environment variables
```shell
echo 'export PYSPARK_PYTHON=/usr/bin/python3.7' >> $SPARK_HOME/conf/spark-env.sh
echo 'export KAFKA_MASTER=<KAFKA_MASTER>' >> ~/.profile
source ~/.profile
```

### Setup the Spark Clusters (Aggregator and Consumer)

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
echo 'export PYSPARK_PYTHON=/usr/bin/python3.7' >> $SPARK_HOME/conf/spark-env.sh
echo 'export KAFKA_MASTER=<KAFKA_MASTER>' >> ~/.profile
echo 'export CASSANDRA_MASTER=<CASSANDRA_MASTER>' >> ~/.profile
source ~/.profile
```

### Setup the Kafka Clusters

Install and start Zookeeper and Kafka
```shell
peg install kafka-cluster zookeeper
peg install kafka-cluster kafka
peg service kafka-cluster zookeeper start
peg service kafka-cluster kafka start
```

## Starting the pipeline

On the Cassandra cluster, start the producers
```shell
bin/binance.py com `tr '\n' ' ' < tmp/binance.pair` >> log/binance.log 2>&1 &
bin/binance.py je `tr '\n' ' ' < tmp/binance_jersey.pair` >> log/binance_jersey.log 2>&1 &
bin/binance.py us `tr '\n' ' ' < tmp/binance_us.pair` >> log/binance_us.log 2>&1 &
bin/bitfinex.py `tr '\n' ' ' < tmp/bitfinex.pair` >> log/bitfinex.log 2>&1 &
bin/coinbase.py `tr '\n' ' ' < tmp/coinbase.pair` >> log/coinbase.log 2>&1 &
bin/hitbtc_.py `tr '\n' ' ' < tmp/hitbtc.pair` >> log/hitbtc.log 2>&1 &
bin/kraken.py trade `tr '\n' ' ' < tmp/kraken.pair` >> log/kraken.log 2>&1 &
```
On the aggregator cluster, create `ckpt` directory in HDFS and submit the `aggregator.py` job
```shell
hdfs dfs -mkdir /ckpt
spark-submit \
  --master "spark://${AGGREGATOR_MASTER}:7077" \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.0,com.datastax.spark:spark-cassandra-connector_2.11:2.3.0 \
  --conf spark.cassandra.connection.host="${CASSANDRA_MASTER}" \
  bin/aggregator.py >> log/aggregator.log 2>&1 &
```

On the consumer cluster, create `ckpt` directory in HDFS and submit the `consumer.py` job
```shell
hdfs dfs -mkdir /ckpt
spark-submit \
  --master "spark://${CONSUMER_MASTER}:7077" \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.0,com.datastax.spark:spark-cassandra-connector_2.11:2.3.0 \
  --conf spark.cassandra.connection.host="${CASSANDRA_MASTER}" \
  bin/consumer.py >> log/consumer.log 2>&1 &
```

## Contact Information
* [Joel Solis](https://www.linkedin.com/in/jsolis1199)
* jsolis@alum.mit.edu
* 956.459.4809
