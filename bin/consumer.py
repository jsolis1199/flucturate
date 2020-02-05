#!/usr/bin/env python3.7

from os import environ
from itertools import combinations

from pyspark.sql import SparkSession
from pyspark.sql.types import TimestampType
import pyspark.sql.functions as F

spark = SparkSession.builder.appName('Consumer').getOrCreate()
host = f'{environ["KAFKA_MASTER"]}:9092'
df = spark \
        .readStream \
        .format('kafka') \
        .option('kafka.bootstrap.servers', host) \
        .option('subscribe', 'agg') \
        .option('startingOffsets', 'earliest') \
        .load() \
        .selectExpr('CAST(key AS STRING)', 'CAST(value AS STRING)') \
        .selectExpr(
        'CAST(SPLIT(key, ",")[0] AS TIMESTAMP) AS start', 
        'SPLIT(key, ",")[1] AS base',
        'SPLIT(key, ",")[2] AS quote',
        'SPLIT(key, ",")[3] AS exchange',
        'CAST(value AS DOUBLE) AS p'
        ) \
        .withWatermark('start', '1 minute')
exchanges = ('binance', 'binance_jersey', 'binance_us', 'bitfinex', 'coinbase', 'hitbtc', 'kraken')
for x, y in combinations(exchanges, 2):
    filtered = df.filter((df.exchange == x) | (df.exchange == y))
    filtered = filtered \
            .groupBy(F.window('start', '1 minute'), 'base', 'quote') \
            .agg((F.max(df.p) - F.min(df.p)).alias('diff')) \
            .withColumn('exchanges', F.lit(' '.join(sorted([x, y])))) \
            .selectExpr('base', 'quote', 'window.start', 'exchanges', 'diff')
    filtered = filtered.filter(filtered.diff != 0)
    query = filtered \
            .writeStream \
            .option('checkpointLocation', f'hdfs://{environ["HADOOP_MASTER"]}:9000/ckpt/') \
            .format("org.apache.spark.sql.cassandra") \
            .options(table='diffs', keyspace='flucturate') \
            .start()
query.awaitTermination()
