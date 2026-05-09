def analyze(features):
    """
    Método C: Ruptura de Volatilidad (Breakout).
    Detecta impulsos fuertes usando Bandas de Bollinger.
    """
    last_row = features.iloc[-1]
    price = last_row['close']
    
    # Nombres generados por pandas_ta: BBU (Upper), BBL (Lower)
    upper_band = last_row['BBU_20_2.0']
    lower_band = last_row['BBL_20_2.0']
    
    # Ruptura Alcista
    if price > upper_band:
        return 1, 0.85  # LONG con 85% de confianza técnica
        
    # Ruptura Bajista
    elif price < lower_band:
        return 0, 0.85  # SHORT con 85% de confianza técnica
        
    return None, 0