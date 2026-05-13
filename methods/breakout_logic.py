def analyze(features):
    last_row = features.iloc[-1]
    price    = last_row['close']

    if 'BB_upper' not in last_row.index or 'BB_lower' not in last_row.index:
        return None, 0

    if price > last_row['BB_upper']:
        return 1, 0.85

    elif price < last_row['BB_lower']:
        return 0, 0.85

    return None, 0