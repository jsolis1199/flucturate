#!/usr/bin/env python3.7

from os import environ
from itertools import combinations

from pyspark.sql import SparkSession
from pyspark.sql.types import TimestampType
import pyspark.sql.functions as F

def writeBatch(batch, identifier):
    batch \
            .write \
            .mode('append') \
            .format('org.apache.spark.sql.cassandra') \
            .options(table='diffs', keyspace='flucturate') \
            .save()

spark = SparkSession.builder.appName('Subtractor').getOrCreate()
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
for e in combinations(exchanges, 2):
    x, y = sorted(e)
    filtered = df.filter((df.exchange == x) | (df.exchange == y))
    filtered = filtered \
            .withColumn('p', F.when(filtered.exchange == x, -1 * filtered.p).otherwise(filtered.p)) \
            .drop('exchange')
    filtered = filtered \
            .groupBy(F.window('start', '1 minute'), 'base', 'quote') \
            .agg(F.sum(filtered.p).alias('diff'), (F.max(F.abs(filtered.p)) - F.min(F.abs(filtered.p))).alias('condition')) \
            .withColumn('exchanges', F.lit(f'{x} {y}')) \
            .selectExpr('base', 'quote', 'window.start', 'exchanges', 'diff', 'condition')
    filtered = filtered \
            .filter(filtered.condition != 0) \
            .drop('condition')
    query = filtered \
            .writeStream \
            .option('checkpointLocation', f'hdfs://{environ["HADOOP_MASTER"]}:9000/ckpt/{x}-{y}') \
            .foreachBatch(writeBatch) \
            .start()
query.awaitTermination()
