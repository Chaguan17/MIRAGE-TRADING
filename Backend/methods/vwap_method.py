import numpy as np
import config


def analyze(features):
    if len(features) < 20:
        return None, 0

    df    = features.copy()
    close = df['close'].values
    high  = df['high'].values
    low   = df['low'].values
    vol   = df['volume'].values

    typical_price = (high + low + close) / 3
    cum_tp_vol    = np.cumsum(typical_price * vol)
    cum_vol       = np.cumsum(vol)
    vwap          = cum_tp_vol / (cum_vol + 1e-9)

    variance   = np.cumsum(vol * (typical_price - vwap) ** 2) / (cum_vol + 1e-9)
    std_dev    = np.sqrt(np.abs(variance))
    upper_band = vwap + (config.VWAP_BAND_MULT * std_dev)
    lower_band = vwap - (config.VWAP_BAND_MULT * std_dev)

    last_price     = close[-1]
    last_vwap      = vwap[-1]
    last_upper     = upper_band[-1]
    last_lower     = lower_band[-1]
    last_vol_ratio = df['volume_ratio'].iloc[-1] if 'volume_ratio' in df.columns else 1.0

    above_vwap = last_price > last_vwap
    below_vwap = last_price < last_vwap

    prev_prices = close[-6:-1]
    prev_vwaps  = vwap[-6:-1]
    crossed_up   = any(prev_prices[i] < prev_vwaps[i] and close[-1] > last_vwap
                       for i in range(len(prev_prices)))
    crossed_down = any(prev_prices[i] > prev_vwaps[i] and close[-1] < last_vwap
                       for i in range(len(prev_prices)))

    if crossed_up and last_vol_ratio > 1.2:
        return 1, 0.82

    if crossed_down and last_vol_ratio > 1.2:
        return 0, 0.82

    if above_vwap and last_price <= last_lower * 1.001:
        return 1, 0.72 if last_vol_ratio > 1.0 else 0.62

    if below_vwap and last_price >= last_upper * 0.999:
        return 0, 0.72 if last_vol_ratio > 1.0 else 0.62

    return None, 0