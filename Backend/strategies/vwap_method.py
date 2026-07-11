"""
vwap_method.py — Mirage Trading
BUG CRÍTICO CORREGIDO: 'df' no estaba definido (se usaba 'features').
"""
import numpy as np
import config


def analyze(features):
    if len(features) < 100 or 'VWAP' not in features.columns:
        return None, 0

    import pandas as pd

    close = features['close'].values
    high  = features['high'].values
    low   = features['low'].values
    vol   = features['volume'].values

    # Obtener el VWAP alineado de 100 periodos precalculado por el DataEngine
    vwap = features['VWAP'].values

    # Calcular desviación estándar rodante de 100 periodos ponderada por volumen
    typical_price = (high + low + close) / 3
    vol_diff_sq = vol * (typical_price - vwap) ** 2
    
    rolling_vol_diff_sq = pd.Series(vol_diff_sq).rolling(100, min_periods=1).sum().values
    rolling_vol = pd.Series(vol).rolling(100, min_periods=1).sum().values
    
    variance   = rolling_vol_diff_sq / (rolling_vol + 1e-9)
    std_dev    = np.sqrt(np.abs(variance))
    upper_band = vwap + (config.VWAP_BAND_MULT * std_dev)
    lower_band = vwap - (config.VWAP_BAND_MULT * std_dev)

    last_price = close[-1]
    last_vwap  = vwap[-1]
    last_upper = upper_band[-1]
    last_lower = lower_band[-1]

    # BUG CORREGIDO: era 'df' pero la variable se llama 'features'
    last_vol_ratio = features['volume_ratio'].iloc[-1] if 'volume_ratio' in features.columns else 1.0

    above_vwap = last_price > last_vwap
    below_vwap = last_price < last_vwap

    prev_price    = close[-2]
    prev_vwap_val = vwap[-2]
    crossed_up    = prev_price <= prev_vwap_val and last_price > last_vwap
    crossed_down  = prev_price >= prev_vwap_val and last_price < last_vwap

    if crossed_up and last_vol_ratio > 1.2:
        return 1, 0.82

    if crossed_down and last_vol_ratio > 1.2:
        return 0, 0.82

    # Lógica corregida: rebote en bandas VWAP
    if below_vwap and last_price <= last_lower * 1.001:
        return 1, 0.72 if last_vol_ratio > 1.0 else 0.62

    if above_vwap and last_price >= last_upper * 0.999:
        return 0, 0.72 if last_vol_ratio > 1.0 else 0.62

    return None, 0
