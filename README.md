# FluctuRate

A tool to measure inconsistencies in the cryptocurrency markets

## Usage

Start Kafka
```
kafka-server-start.sh $KAFKA_HOME/config/server.properties >> log/kafka.log 2>&1
```

Start Producers
```
bin/coinbase-producer.py `tr '\n' ' ' < tmp/coinbase.txt` >> log/coinbase.log 2>&1
bin/kraken-producer.py trade `tr '\n' ' ' < tmp/kraken.txt` >> log/kraken.log 2>&1
```
