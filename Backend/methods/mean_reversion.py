def analyze(features):
    # BUG MEDIO CORREGIDO #6:
    # El acceso directo features.iloc[-1]['RSI'] lanzaba KeyError si la columna
    # RSI no estaba presente en el DataFrame (por ejemplo si DataEngine falló
    # al calcularla o la vela tiene datos insuficientes).
    # A diferencia de breakout_logic.py que sí tenía guard, esta función no lo tenía.
    last_row = features.iloc[-1]

    if 'RSI' not in last_row.index:
        return None, 0

    rsi = last_row['RSI']

    # Protección adicional contra NaN que numpy puede generar con series cortas
    try:
        rsi = float(rsi)
    except (TypeError, ValueError):
        return None, 0

    if rsi >= 75:
        return 0, 0.85

    elif rsi <= 25:
        return 1, 0.85

    return None, 0