import pandas as pd
import pandas_ta as ta


class DataEngine:
    def __init__(self):
        self._bb_upper_col = None
        self._bb_lower_col = None

    def prepare_features(self, df):
        """Transforma datos de precio en indicadores técnicos."""
        df = df.copy()

        # 1. Tendencia y Momentum
        df['EMA_20'] = ta.ema(df['close'], length=20)
        df['EMA_50'] = ta.ema(df['close'], length=50)
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # 2. Bandas de Bollinger — detectamos el nombre de columna que genera tu versión
        bbands = ta.bbands(df['close'], length=20, std=2.0)
        df = pd.concat([df, bbands], axis=1)

        # Detectar y normalizar los nombres de columna de Bollinger una sola vez
        if self._bb_upper_col is None:
            for upper_key, lower_key in [
                ('BBU_20_2.0', 'BBL_20_2.0'),
                ('BBU_20_2', 'BBL_20_2'),
                ('BBU_20', 'BBL_20'),
            ]:
                if upper_key in df.columns and lower_key in df.columns:
                    self._bb_upper_col = upper_key
                    self._bb_lower_col = lower_key
                    break

        # Alias estándar para que el resto del código no dependa del nombre exacto
        if self._bb_upper_col:
            df['BB_upper'] = df[self._bb_upper_col]
            df['BB_lower'] = df[self._bb_lower_col]

        # 3. Diferenciales para el Brain
        df['EMA_diff'] = df['EMA_20'] - df['EMA_50']
        df['trend_signal'] = (df['EMA_20'] > df['EMA_50']).astype(int)

        return df.dropna()

    def create_labels(self, df):
        """Etiquetado para entrenamiento."""
        df = df.copy()
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        return df.dropna()
