import numpy as np
import config


def _get_psych_step(price: float) -> float:
    """
    BUG MEDIO CORREGIDO #8:
    El paso para niveles psicológicos estaba hardcodeado en 500, lo cual
    solo es apropiado para BTC (~60k+). Para ETH (~3k) debería ser 100 o 50,
    y para BNB (~600) debería ser 10 o 25.

    Ahora el paso se calcula dinámicamente según el precio del activo:
    - precio >= 10 000 : paso de 500   (BTC)
    - precio >= 1 000  : paso de 100   (ETH)
    - precio >= 100    : paso de 10    (BNB, SOL, etc.)
    - precio <  100    : paso de 1     (activos de bajo precio)
    """
    if price >= 10_000:
        return 500.0
    elif price >= 1_000:
        return 100.0
    elif price >= 100:
        return 10.0
    else:
        return 1.0


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

    step         = _get_psych_step(price)
    round_level  = round(price / step) * step
    psych_levels = [round_level - step, round_level, round_level + step]

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