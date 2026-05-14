def analyze(features):
    last_row = features.iloc[-1]
    rsi      = last_row['RSI']
    ema_diff = last_row['EMA_20'] - last_row['EMA_50']

    if ema_diff > 0 and 50 < rsi < 70:
        return 1, 0.75

    elif ema_diff < 0 and 30 < rsi < 50:
        return 0, 0.75

    return None, 0