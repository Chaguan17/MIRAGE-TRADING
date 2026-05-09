def analyze(features):
    """
    Método B: Scalping por Reversión a la Media.
    Busca rebotes cuando el precio está muy alejado de su promedio.
    """
    rsi = features.iloc[-1]['RSI']
    
    # Lógica de agotamiento:
    # Si el RSI está por encima de 75, el precio está 'caliente' (Sobrecarga)
    if rsi >= 75:
        return 0, 0.85  # Sugiere SHORT con alta confianza de rebote
        
    # Si el RSI está por debajo de 25, el precio está 'congelado'
    elif rsi <= 25:
        return 1, 0.85  # Sugiere LONG
        
    return None, 0