def analyze(features):
    """
    Método C: Ruptura de Volatilidad (Breakout).
    Detecta impulsos fuertes usando Bandas de Bollinger.
    Usa los alias estándar BB_upper / BB_lower generados por DataEngine.
    """
    last_row = features.iloc[-1]
    price = last_row['close']

    # DataEngine normaliza siempre a estos nombres
    if 'BB_upper' not in last_row.index or 'BB_lower' not in last_row.index:
        return None, 0

    upper_band = last_row['BB_upper']
    lower_band = last_row['BB_lower']

    if price > upper_band:
        return 1, 0.85  # Ruptura alcista

    elif price < lower_band:
        return 0, 0.85  # Ruptura bajista

    return None, 0
