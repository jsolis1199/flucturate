#!/usr/bin/env python3.7

import os
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

os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.0,com.datastax.spark:spark-cassandra-connector_2.11:2.3.0 --conf spark.cassandra.connection.host=localhost pyspark-shell'
spark = SparkSession.builder.appName('Consumer').getOrCreate()
host = 'localhost:9092'
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
exchanges = ('bitfinex', 'coinbase', 'kraken')
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
            .foreachBatch(writeBatch) \
            .start()
query.awaitTermination()
