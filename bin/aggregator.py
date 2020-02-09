#!/usr/bin/env python3.7

from os import environ

from pyspark.sql import SparkSession
import pyspark.sql.functions as F

def writeBatch(batch, identifier, table):
    batch \
            .write \
            .mode('append') \
            .format('org.apache.spark.sql.cassandra') \
            .options(table=table, keyspace='flucturate') \
            .save()

def writeBatchToTrades(batch, identifier):
    writeBatch(batch, identifier, 'trades')

def writeBatchToAverages(batch, identifier):
    writeBatch(batch, identifier, 'averages')

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
        .option('checkpointLocation', f'hdfs://{environ["HADOOP_MASTER"]}:9000/ckpt/trades') \
        .foreachBatch(writeBatchToTrades) \
        .start()
df = df \
        .groupBy(F.window('time', '1 minute'), 'base', 'quote', 'exchange') \
        .agg((F.sum(df.price * df.quantity)/F.sum(df.quantity)).alias('price')) \
        .selectExpr('window.start AS start', 'base', 'quote', 'exchange', 'price')
avgQuery = df \
        .writeStream \
        .option('checkpointLocation', f'hdfs://{environ["HADOOP_MASTER"]}:9000/ckpt/averages') \
        .foreachBatch(writeBatchToAverages) \
        .start()
df = df.selectExpr(
        'CONCAT(start, ",", base, ",", quote, ",", exchange) AS key',
        'CAST(price AS STRING) AS value'
        )
aggQuery = df \
        .writeStream \
        .option('checkpointLocation', f'hdfs://{environ["HADOOP_MASTER"]}:9000/ckpt/agg') \
        .format('kafka') \
        .option('kafka.bootstrap.servers', host) \
        .option('topic', 'agg') \
        .start()
allQuery.awaitTermination()
avgQuery.awaitTermination()
aggQuery.awaitTermination()
