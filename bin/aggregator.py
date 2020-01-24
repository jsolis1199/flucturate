#!/usr/bin/env python3

import os

from pyspark.sql import SparkSession
import pyspark.sql.functions as F

os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.4.0 pyspark-shell'
spark = SparkSession.builder.appName('Aggregator').getOrCreate()
host = 'localhost:9092'
df = spark \
        .readStream \
        .format('kafka') \
        .option('kafka.bootstrap.servers', host) \
        .option('subscribe', 'all') \
        .option('startingOffsets', 'earliest') \
        .load() \
        .selectExpr('CAST(key AS STRING)', 'CAST(value AS STRING)')
df = df.selectExpr(
        'key',
        'CAST(SPLIT(value, " ")[0] AS DOUBLE) AS p',
        'CAST(SPLIT(value, " ")[1] AS DOUBLE) AS q',
        )
df = df.groupBy('key').agg((F.sum(df.p * df.q)/F.sum(df.q)).alias('value'))
df = df.selectExpr('key', 'CAST(value AS STRING)')
query = df \
        .writeStream \
        .outputMode('update') \
        .format('kafka') \
        .option('kafka.bootstrap.servers', host) \
        .option('topic', 'agg') \
        .option('checkpointLocation', 'ckpt/') \
        .start()
query.awaitTermination()
