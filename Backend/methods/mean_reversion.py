def analyze(features):
    rsi = features.iloc[-1]['RSI']

    if rsi >= 75:
        return 0, 0.85

    elif rsi <= 25:
        return 1, 0.85

    return None, 0