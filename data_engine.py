import pandas as pd
import numpy as np
import pandas_ta as ta


class DataEngine:
    def __init__(self):
        self._bb_upper_col = None
        self._bb_lower_col = None

    def prepare_features(self, df):
        df = df.copy()

        # ── 1. TENDENCIA ────────────────────────────────────────────────────
        df['EMA_20']        = ta.ema(df['close'], length=20)
        df['EMA_50']        = ta.ema(df['close'], length=50)
        df['EMA_200']       = ta.ema(df['close'], length=200)
        df['EMA_diff']      = df['EMA_20'] - df['EMA_50']
        df['EMA_diff_norm'] = df['EMA_diff'] / (df['close'] * 0.001 + 1e-9)

        # ── 2. MOMENTUM ─────────────────────────────────────────────────────
        df['RSI']  = ta.rsi(df['close'], length=14)
        macd_df    = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            df['MACD']        = macd_df.iloc[:, 0]
            df['MACD_signal'] = macd_df.iloc[:, 1]
            df['MACD_hist']   = macd_df.iloc[:, 2]
        else:
            df['MACD'] = df['MACD_signal'] = df['MACD_hist'] = 0

        # ── 3. VOLATILIDAD ──────────────────────────────────────────────────
        df['ATR']     = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['ATR_pct'] = df['ATR'] / df['close'] * 100

        bbands = ta.bbands(df['close'], length=20, std=2.0)
        df = pd.concat([df, bbands], axis=1)

        if self._bb_upper_col is None:
            for u, l in [
                ('BBU_20_2.0', 'BBL_20_2.0'),
                ('BBU_20_2',   'BBL_20_2'),
                ('BBU_20',     'BBL_20'),
            ]:
                if u in df.columns and l in df.columns:
                    self._bb_upper_col, self._bb_lower_col = u, l
                    break

        if self._bb_upper_col:
            df['BB_upper']    = df[self._bb_upper_col]
            df['BB_lower']    = df[self._bb_lower_col]
            df['BB_width']    = (df['BB_upper'] - df['BB_lower']) / df['close'] * 100
            df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 1e-9)

        # ── 4. VOLUMEN ──────────────────────────────────────────────────────
        df['volume_ma']    = ta.ema(df['volume'], length=20)
        df['volume_ratio'] = df['volume'] / (df['volume_ma'] + 1e-9)

        # ── 5. SEÑALES BINARIAS ──────────────────────────────────────────────
        df['trend_signal']    = (df['EMA_20']   > df['EMA_50']).astype(int)
        df['above_ema200']    = (df['close']     > df['EMA_200']).astype(int)
        df['momentum_signal'] = (df['MACD_hist'] > 0).astype(int)

        # ── 6. VWAP ─────────────────────────────────────────────────────────
        typical_price  = (df['high'] + df['low'] + df['close']) / 3
        cum_tp_vol     = (typical_price * df['volume']).cumsum()
        cum_vol        = df['volume'].cumsum()
        df['VWAP']     = cum_tp_vol / (cum_vol + 1e-9)
        df['VWAP_dist'] = (df['close'] - df['VWAP']) / df['VWAP'] * 100

        # ── 7. ORDERFLOW DELTA ──────────────────────────────────────────────
        candle_range      = df['high'] - df['low'] + 1e-9
        close_position    = (df['close'] - df['low']) / candle_range
        df['delta']       = (close_position - 0.5) * 2 * df['volume']
        df['delta_cum5']  = df['delta'].rolling(5).sum()
        df['delta_cum10'] = df['delta'].rolling(10).sum()
        price_change5     = df['close'].diff(5)
        df['delta_div']   = np.sign(price_change5) * np.sign(df['delta_cum5'])

        # ── 8. WYCKOFF ──────────────────────────────────────────────────────
        df['price_slope'] = df['close'].diff(10) / (df['close'].shift(10) + 1e-9) * 100
        df['range_pct']   = (df['high'].rolling(20).max() - df['low'].rolling(20).min()) / df['close'] * 100

        # ── 9. ESTRUCTURA SMC ────────────────────────────────────────────────
        df['struct_high']      = df['high'].rolling(20).max()
        df['struct_low']       = df['low'].rolling(20).min()
        df['near_struct_high'] = (abs(df['close'] - df['struct_high']) / df['close'] < 0.002).astype(int)
        df['near_struct_low']  = (abs(df['close'] - df['struct_low'])  / df['close'] < 0.002).astype(int)

        return df.dropna()

    def get_feature_columns(self):
        return [
            'RSI', 'ATR', 'ATR_pct',
            'EMA_diff', 'EMA_diff_norm',
            'MACD', 'MACD_hist',
            'BB_width', 'BB_position',
            'volume_ratio',
            'trend_signal', 'above_ema200', 'momentum_signal',
            'VWAP_dist',
            'delta_cum5', 'delta_div',
            'price_slope', 'range_pct',
            'near_struct_high', 'near_struct_low',
        ]