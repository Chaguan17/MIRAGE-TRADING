import numpy as np
import config


def analyze(features):
    if len(features) < 20:
        return None, 0

    close = features['close'].values
    high  = features['high'].values
    low   = features['low'].values
    vol   = features['volume'].values

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

    # Optimización: Solo verificamos el cruce con respecto a la vela anterior para mayor precisión
    prev_price = close[-2]
    prev_vwap_val = vwap[-2]
    crossed_up = prev_price <= prev_vwap_val and last_price > last_vwap
    crossed_down = prev_price >= prev_vwap_val and last_price < last_vwap

    if crossed_up and last_vol_ratio > 1.2:
        return 1, 0.82

    if crossed_down and last_vol_ratio > 1.2:
        return 0, 0.82

    # BUG CRÍTICO CORREGIDO #3:
    # Las condiciones originales eran imposibles de cumplir:
    #   - "above_vwap AND precio <= banda_inferior" es contradictorio porque
    #     la banda inferior siempre está POR DEBAJO del vwap.
    #   - "below_vwap AND precio >= banda_superior" es igualmente imposible.
    # Estas dos ramas NUNCA emitían señal.
    #
    # Lógica correcta:
    #   - Si el precio está BAJO el vwap y toca/cruza la banda inferior → señal de compra
    #     (rebote desde zona de soporte)
    #   - Si el precio está SOBRE el vwap y toca/cruza la banda superior → señal de venta
    #     (rechazo en zona de resistencia)
    if below_vwap and last_price <= last_lower * 1.001:
        return 1, 0.72 if last_vol_ratio > 1.0 else 0.62

    if above_vwap and last_price >= last_upper * 0.999:
        return 0, 0.72 if last_vol_ratio > 1.0 else 0.62

    return None, 0