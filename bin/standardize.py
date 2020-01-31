def standardize(base, quote):
    if base == 'BTC':
        b = 'XBT'
    elif base == 'DOGE':
        b = 'XDG'
    else:
        b = base
    if quote == 'BTC':
        q = 'XBT'
    elif quote == 'DOGE':
        q = 'XDG'
    else:
        q = quote
    return (b, q)
