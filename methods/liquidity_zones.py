import numpy as np
import config


def analyze(features):
    if len(features) < config.LIQ_LOOKBACK + 5:
        return None, 0

    df      = features.copy()
    close   = df['close'].values
    high    = df['high'].values
    low     = df['low'].values
    price   = close[-1]
    tol     = config.LIQ_CLUSTER_PCT
    lookback = config.LIQ_LOOKBACK

    liq_highs = []
    liq_lows  = []

    window = high[-lookback:-1]
    for i in range(1, len(window) - 1):
        if window[i] >= window[i-1] and window[i] >= window[i+1]:
            liq_highs.append(window[i])

    window = low[-lookback:-1]
    for i in range(1, len(window) - 1):
        if window[i] <= window[i-1] and window[i] <= window[i+1]:
            liq_lows.append(window[i])

    round_level  = round(price / 500) * 500
    psych_levels = [round_level - 500, round_level, round_level + 500]

    all_highs = liq_highs + [l for l in psych_levels if l > price]
    all_lows  = liq_lows  + [l for l in psych_levels if l < price]

    if not all_highs or not all_lows:
        return None, 0

    nearest_high = min(all_highs, key=lambda x: abs(x - price))
    nearest_low  = min(all_lows,  key=lambda x: abs(x - price))
    dist_to_high = abs(price - nearest_high) / price
    dist_to_low  = abs(price - nearest_low)  / price

    prev_close = close[-2]
    hunt_high  = prev_close > nearest_high and price < nearest_high
    hunt_low   = prev_close < nearest_low  and price > nearest_low

    if hunt_high:
        return 0, 0.85

    if hunt_low:
        return 1, 0.85

    vol_ratio = df['volume_ratio'].iloc[-1] if 'volume_ratio' in df.columns else 1.0

    if dist_to_high < tol * 2:
        return 0, 0.65 if vol_ratio > 1.1 else 0.58

    if dist_to_low < tol * 2:
        return 1, 0.65 if vol_ratio > 1.1 else 0.58

    return None, 0