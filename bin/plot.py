#!/usr/bin/env python3.7

from pathlib import Path
from datetime import timedelta

from dash import Dash
import dash.dependencies as dd
import dash_core_components as dcc
import dash_html_components as html
from cassandra.cluster import Cluster
from pandas import DataFrame

from standardize import standardize

def read_file(filename):
    with open(filename, 'r') as f:
        contents = [e.replace('\n', '') for e in f.readlines()]
    return contents

path = str(Path(__file__).parent.parent.absolute()) + '/tmp'
default_exchange = 'coinbase'
default_pair = 'XBT/USD'
formatted_exchanges = {
        'binance': 'Binance',
        'binance_jersey': 'Binance Jersey',
        'binance_us': 'Binance US',
        'bitfinex': 'Bitfinex',
        'coinbase': 'Coinbase',
        'hitbtc': 'HitBTC',
        'kraken': 'Kraken'
        }
exchange_options = [{'label': formatted_exchanges[e], 'value': e} for e in formatted_exchanges]
cluster = Cluster()
session = cluster.connect('flucturate')
colors = {
    'background': '#FFFFFF',
    'text': '#000000' #'#7FDBFF'
}
app = Dash()
app.layout = html.Div(
        style={'backgroundColor': colors['background']},
        children=[
            html.H1(
                children='FluctuRate',
                style={
                    'textAlign': 'center',
                    'color': colors['text']
                    }
                ),
            html.Div(
                children='Evaluating the Cryptocurrency Market',
                style={
                    'textAlign': 'center',
                    'color': colors['text']
                    }
                ),
            html.Div(
                children=[
                    dcc.Dropdown(
                        clearable=False,
                        id='exchange-dropdown',
                        options=exchange_options,
                        value=default_exchange
                        ),
                    dcc.Dropdown(
                        clearable=False,
                        id='pair-dropdown',
                        value=default_pair
                        )
                    ]
                ),
            dcc.Graph(id='flucturate-plot')
            ]
        )

@app.callback(
        dd.Output('pair-dropdown', 'options'),
        [dd.Input('exchange-dropdown', 'value')]
        )
def update_pairs(dropdown_exchange):
    if dropdown_exchange[:7] == 'binance' or dropdown_exchange == 'hitbtc':
        bases = read_file(f'{path}/{dropdown_exchange}.base')
        quotes = read_file(f'{path}/{dropdown_exchange}.quote')
        options = zip(bases, quotes)
        if dropdown_exchange == 'hitbtc':
            options = [
                    (
                        'USDT' if b == 'USD' else b,
                        'USDT' if q == 'USD' else q
                        )
                    for b, q in options
                    ]
    else:
        options = read_file(f'{path}/{dropdown_exchange}.pair')
        if dropdown_exchange == 'bitfinex':
            options = [
                    (pair[:3], pair[3:])
                    if len(pair) == 6
                    else pair.split(':') 
                    for pair in options
                    ]
        elif dropdown_exchange == 'coinbase':
            options = [pair.split('-') for pair in options]
        elif dropdown_exchange == 'kraken':
            options = [pair.split('/') for pair in options]
    options = [standardize(*pair) for pair in options]
    options = ['/'.join(pair) for pair in options]
    options = [{'label': pair, 'value': pair} for pair in sorted(options)] 
    return options

@app.callback(
        dd.Output('flucturate-plot', 'figure'),
        [
            dd.Input('pair-dropdown', 'value'),
            dd.Input('exchange-dropdown', 'value')
            ]
        )
def update_graph(dropdown_pair, dropdown_exchange):
    dropdown_base, dropdown_quote = dropdown_pair.split('/')
    # prepare data
    data = []
    avgs_cql = f'SELECT start, exchange, price FROM averages WHERE base = \'{dropdown_base}\' and quote = \'{dropdown_quote}\' ORDER BY start DESC;'
    avgs = DataFrame(session.execute(avgs_cql), columns=('start', 'exchange', 'price'))
    avgs = avgs[avgs['exchange'] == dropdown_exchange]
    avgs = avgs[['start', 'price']]
    diffs_cql = f'SELECT start, exchanges, diff FROM diffs WHERE base = \'{dropdown_base}\' and quote = \'{dropdown_quote}\' ORDER BY start DESC;'
    # diffs
    diffs = [
            (
                start,
                exchanges.split()[1 - exchanges.split().index(dropdown_exchange)],
                diff
                )
            for start, exchanges, diff
            in session.execute(diffs_cql)
            if dropdown_exchange in exchanges.split()
            ]
    diffs = DataFrame(diffs, columns=('start', 'exchange', 'diff'))
    if diffs.shape[0]:
        diffs = avgs.merge(diffs, on='start', how='left').dropna()
        diffs['start'] = diffs['start'] - timedelta(hours=5)
        diffs['diff'] = diffs['diff'] / diffs['price']
        for exchange in diffs['exchange'].unique():
            df = diffs[diffs['exchange'] == exchange]
            data.append(
                    {
                        'x': df['start'],
                        'y': -1 * df['diff'] if dropdown_exchange > exchange else df['diff'],
                        'type': 'line',
                        'name': formatted_exchanges[exchange]
                        }
                    )
    # prepare layout
    layout = {
        'title': f'Deviation of exchange prices from {formatted_exchanges[dropdown_exchange]} price',
        'height': '700',
        'xaxis': {'title': 'UTC - 05:00', 'type': 'Linear'},
        'yaxis': {
            'title': f'Relative difference in {dropdown_pair} price',
            'type': 'Linear'
            },
        'plot_bgcolor': colors['background'],
        'paper_bgcolor': colors['background'],
        'font': {
            'color': colors['text']
        }
    }
    return {'data': data, 'layout': layout}

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', debug=True, port=8080)
