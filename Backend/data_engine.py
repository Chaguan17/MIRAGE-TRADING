import pandas as pd
import numpy as np
import pandas_ta as ta


class DataEngine:
    def __init__(self):
        self._bb_upper_col = None
        self._bb_lower_col = None
        self._fng_cache = None
        self._fng_last_fetch = 0
        
    def _get_fear_and_greed(self):
        import time
        import requests
        now = time.time()
        if self._fng_cache is None or (now - self._fng_last_fetch) > 3600 * 12:
            try:
                r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
                data = r.json()
                val = int(data['data'][0]['value'])
                self._fng_cache = val
                self._fng_last_fetch = now
            except Exception:
                if self._fng_cache is None:
                    self._fng_cache = 50
        return self._fng_cache

    def prepare_features(self, df, df_1h=None, df_4h=None):
        df = df.copy()

        # ── 0. MULTI-TIMEFRAME (MTF) ────────────────────────────────────────
        df['MTF_1h_trend'] = 0
        df['MTF_4h_trend'] = 0
        
        if 'timestamp' in df.columns:
            df_sorted = df.sort_values('timestamp')
            
            if df_1h is not None and not df_1h.empty and 'timestamp' in df_1h.columns:
                ema50_1h = ta.ema(df_1h['close'], length=50)
                if ema50_1h is not None:
                    df_1h_temp = pd.DataFrame({'EMA50_1h': ema50_1h})
                    df_1h_temp['timestamp'] = df_1h['timestamp']
                    df_1h_temp = df_1h_temp.dropna().sort_values('timestamp')
                    if not df_1h_temp.empty:
                        df_sorted = pd.merge_asof(df_sorted, df_1h_temp, on='timestamp', direction='backward')
                        df_sorted['MTF_1h_trend'] = (df_sorted['close'] > df_sorted['EMA50_1h']).astype(int)
                        df_sorted = df_sorted.drop(columns=['EMA50_1h'])

            if df_4h is not None and not df_4h.empty and 'timestamp' in df_4h.columns:
                ema50_4h = ta.ema(df_4h['close'], length=50)
                if ema50_4h is not None:
                    df_4h_temp = pd.DataFrame({'EMA50_4h': ema50_4h})
                    df_4h_temp['timestamp'] = df_4h['timestamp']
                    df_4h_temp = df_4h_temp.dropna().sort_values('timestamp')
                    if not df_4h_temp.empty:
                        df_sorted = pd.merge_asof(df_sorted, df_4h_temp, on='timestamp', direction='backward')
                        df_sorted['MTF_4h_trend'] = (df_sorted['close'] > df_sorted['EMA50_4h']).astype(int)
                        df_sorted = df_sorted.drop(columns=['EMA50_4h'])
                        
            df = df_sorted.sort_index()

        # ── 1. TENDENCIA ────────────────────────────────────────────────────
        ema20 = ta.ema(df['close'], length=20)
        df['EMA_20'] = ema20 if ema20 is not None else pd.Series(np.nan, index=df.index)
        
        ema50 = ta.ema(df['close'], length=50)
        df['EMA_50'] = ema50 if ema50 is not None else pd.Series(np.nan, index=df.index)
        
        ema200 = ta.ema(df['close'], length=200)
        df['EMA_200'] = ema200 if ema200 is not None else pd.Series(np.nan, index=df.index)
        
        df['EMA_diff']      = df['EMA_20'] - df['EMA_50']
        df['EMA_diff_norm'] = df['EMA_diff'] / (df['close'] * 0.001 + 1e-9)

        # ── 2. MOMENTUM ─────────────────────────────────────────────────────
        rsi = ta.rsi(df['close'], length=14)
        df['RSI'] = rsi if rsi is not None else pd.Series(np.nan, index=df.index)
        
        macd_df    = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            df['MACD']        = macd_df.iloc[:, 0]
            df['MACD_signal'] = macd_df.iloc[:, 1]
            df['MACD_hist']   = macd_df.iloc[:, 2]
        else:
            df['MACD'] = df['MACD_signal'] = df['MACD_hist'] = 0

        # ── 7. ALTERNATIVE DATA (Institucional) ─────────────────────────────
        if 'funding_rate' not in df.columns:
            df['funding_rate'] = 0.0
        df['funding_rate'] = df['funding_rate'].fillna(0.0)
        df['fear_and_greed'] = self._get_fear_and_greed()

        # ── LIMPIEZA FINAL ──────────────────────────────────────────────────
        df = df.replace([np.inf, -np.inf], np.nan)

        # ── 3. VOLATILIDAD ──────────────────────────────────────────────────
        atr = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['ATR'] = atr if atr is not None else pd.Series(np.nan, index=df.index)
        df['ATR_pct'] = df['ATR'] / df['close'] * 100

        bbands = ta.bbands(df['close'], length=20, std=2.0)
        if bbands is not None:
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
        volume_ma = ta.ema(df['volume'], length=20)
        df['volume_ma'] = volume_ma if volume_ma is not None else pd.Series(np.nan, index=df.index)
        df['volume_ratio'] = df['volume'] / (df['volume_ma'] + 1e-9)

        # ── 5. SEÑALES BINARIAS ──────────────────────────────────────────────
        df['trend_signal']    = (df['EMA_20']   > df['EMA_50']).astype(int)
        df['above_ema200']    = (df['close']     > df['EMA_200']).astype(int)
        df['momentum_signal'] = (df['MACD_hist'] > 0).astype(int)

        # ── 6. VWAP ─────────────────────────────────────────────────────────
        typical_price  = (df['high'] + df['low'] + df['close']) / 3
        window = 100
        cum_tp_vol = (
            typical_price * df['volume']
        ).rolling(window).sum()
        cum_vol = (
            df['volume']
        ).rolling(window).sum()
        df['VWAP']     = cum_tp_vol / (cum_vol + 1e-9)
        df['VWAP_dist'] = (df['close'] - df['VWAP']) / (df['VWAP'] + 1e-9) * 100

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
            'funding_rate', 'fear_and_greed',
        ]