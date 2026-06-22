def analyze(features):
    # BUG MEDIO CORREGIDO #7:
    # El acceso directo a last_row['RSI'], last_row['EMA_20'] y last_row['EMA_50']
    # lanzaba KeyError si alguna de esas columnas no existía en el DataFrame.
    # Añadimos la misma comprobación que tiene breakout_logic.py.
    last_row = features.iloc[-1]

    required_cols = ('RSI', 'EMA_20', 'EMA_50')
    for col in required_cols:
        if col not in last_row.index:
            return None, 0

    try:
        rsi      = float(last_row['RSI'])
        ema_diff = float(last_row['EMA_20']) - float(last_row['EMA_50'])
    except (TypeError, ValueError):
        return None, 0

    if ema_diff > 0 and 50 < rsi < 70:
        return 1, 0.75

    elif ema_diff < 0 and 30 < rsi < 50:
        return 0, 0.75

    return None, 0