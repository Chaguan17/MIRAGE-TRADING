import pandas as pd
import pandas_ta as ta

class DataEngine:
    def __init__(self):
        pass

    def prepare_features(self, df):
        """
        Transforma datos de precio en indicadores técnicos.
        """
        # 1. Indicadores de tendencia
        df['EMA_20'] = ta.ema(df['close'], length=20)
        df['EMA_50'] = ta.ema(df['close'], length=50)
        
        # 2. Indicadores de impulso (Momentum)
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        # 3. Volatilidad (Fundamental para ajustar el Stop Loss)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # 4. Creamos señales lógicas (ej: 1 si EMA20 > EMA50, 0 si no)
        df['trend_signal'] = (df['EMA_20'] > df['EMA_50']).astype(int)
        
        # Limpiamos filas con valores vacíos (NaN) que genera el cálculo inicial
        return df.dropna()

    def create_labels(self, df):
        """
        Esto es para el ENTRENAMIENTO. 
        Le dice al bot: "Si compraste aquí y el precio subió en la siguiente vela, hiciste bien".
        """
        # Si el precio de cierre de la siguiente vela es mayor al actual, la etiqueta es 1 (Ganar)
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        return df.dropna()