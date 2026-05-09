# methods/trend_follower.py

def analyze(features):
    """
    Método A: Seguimiento de Tendencia.
    Busca alineación entre EMAs y RSI.
    """
    last_row = features.iloc[-1]
    rsi = last_row['RSI']
    ema_diff = last_row['EMA_20'] - last_row['EMA_50']
    
    # Lógica de tendencia: 
    # Si la EMA rápida está sobre la lenta y el RSI tiene espacio para subir
    if ema_diff > 0 and 50 < rsi < 70:
        return 1, 0.75  # LONG con 75% de confianza interna
    
    # Si la EMA rápida está bajo la lenta y el RSI tiene espacio para bajar
    elif ema_diff < 0 and 30 < rsi < 50:
        return 0, 0.75  # SHORT con 75% de confianza interna
        
    return None, 0  # Sin señal clara para este método