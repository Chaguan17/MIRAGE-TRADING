import pandas as pd
import pandas_ta as ta

class DataEngine:
    def __init__(self):
        pass

    def prepare_features(self, df):
        """Transforma datos de precio en indicadores técnicos."""
        # 1. Tendencia y Momentum
        df['EMA_20'] = ta.ema(df['close'], length=20)
        df['EMA_50'] = ta.ema(df['close'], length=50)
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # 2. Bandas de Bollinger (Para el nuevo Método C)
        bbands = ta.bbands(df['close'], length=20, std=2.0)
        df = pd.concat([df, bbands], axis=1)
        
        # 3. Diferencial para el Brain
        df['EMA_diff'] = df['EMA_20'] - df['EMA_50']
        df['trend_signal'] = (df['EMA_20'] > df['EMA_50']).astype(int)
        
        return df.dropna()

    def create_labels(self, df):
        """Etiquetado para entrenamiento."""
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        return df.dropna()