# FluctuRate

A tool to measure inconsistencies in the cryptocurrency markets

## Usage

```
bin/coinbase-producer.py `tr '\n' ' ' < tmp/coinbase-pairs.txt` >> log/coinbase.log 2>&1
bin/kraken-producer.py trade `tr '\n' ' ' < tmp/kraken-pairs.txt` >> log/kraken.log 2>&1
```
