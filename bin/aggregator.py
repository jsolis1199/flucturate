#!/usr/bin/env python3.7

from os import environ

from pyspark.sql import SparkSession
import pyspark.sql.functions as F

def writeBatch(batch, identifier):
    batch \
            .write \
            .mode('append') \
            .format('org.apache.spark.sql.cassandra') \
            .options(table='trades', keyspace='flucturate') \
            .save()

spark = SparkSession.builder.appName('Aggregator').getOrCreate()
host = f'{environ["KAFKA_MASTER"]}:9092'
df = spark \
        .readStream \
        .format('kafka') \
        .option('kafka.bootstrap.servers', host) \
        .option('subscribe', 'all') \
        .option('startingOffsets', 'earliest') \
        .load() \
        .selectExpr('CAST(key AS STRING)', 'CAST(value AS STRING)')
df = df \
        .selectExpr(
        'CAST(SPLIT(key, ",")[0] AS TIMESTAMP) AS time',
        'SPLIT(key, ",")[1] AS base',
        'SPLIT(key, ",")[2] AS quote',
        'SPLIT(key, ",")[3] AS exchange',
        'CAST(SPLIT(value, ",")[0] AS DOUBLE) AS price',
        'CAST(SPLIT(value, ",")[1] AS DOUBLE) AS quantity',
        ) \
        .withWatermark('time', '1 minute')
allQuery = df \
        .writeStream \
        .foreachBatch(writeBatch) \
        .start()
df = df \
        .groupBy(F.window('time', '1 minute'), 'base', 'quote', 'exchange') \
        .agg((F.sum(df.price * df.quantity)/F.sum(df.quantity)).alias('value'))
df = df.selectExpr(
        'CONCAT(window.start, ",", base, ",", quote, ",", exchange) AS key',
        'CAST(value AS STRING)'
        )
aggQuery = df \
        .writeStream \
        .format('kafka') \
        .option('kafka.bootstrap.servers', host) \
        .option('topic', 'agg') \
        .option('checkpointLocation', 'ckpt/') \
        .start()
allQuery.awaitTermination()
aggQuery.awaitTermination()
