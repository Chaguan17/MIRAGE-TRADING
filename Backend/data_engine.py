import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def _calc_ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _calc_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1.0 / length, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1.0 / length, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    return 100.0 - (100.0 / (1.0 + rs))


def _calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_sig = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - macd_sig
    return macd_line, macd_sig, macd_hist


def _calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / length, adjust=False).mean()


def _calc_bbands(close: pd.Series, length: int = 20, std: float = 2.0):
    sma = close.rolling(length, min_periods=1).mean()
    rstd = close.rolling(length, min_periods=1).std().fillna(0.0)
    bbu = sma + (std * rstd)
    bbl = sma - (std * rstd)
    return bbu, bbl


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
                r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=2)
                data = r.json()
                val = int(data['data'][0]['value'])
                self._fng_cache = val
                self._fng_last_fetch = now
            except Exception as e:
                logger.warning(f"Error consultando Fear & Greed API: {e}")
                if self._fng_cache is None:
                    self._fng_cache = 50
                # Evitar reintentos inmediatos en cada ciclo de 2s si la API falla o da timeout
                self._fng_last_fetch = now - (3600 * 11)  # Reintentar dentro de 1h
        return self._fng_cache

    def prepare_features(self, df, df_1h=None, df_4h=None):
        df = df.copy()

        # ── 0. MULTI-TIMEFRAME (MTF) ────────────────────────────────────────
        df['MTF_1h_trend'] = 0
        df['MTF_4h_trend'] = 0
        
        if 'timestamp' in df.columns:
            df_sorted = df.sort_values('timestamp')
            
            if df_1h is not None and not df_1h.empty and 'timestamp' in df_1h.columns:
                ema50_1h = _calc_ema(df_1h['close'], length=50)
                if ema50_1h is not None:
                    df_1h_temp = pd.DataFrame({'EMA50_1h': ema50_1h})
                    df_1h_temp['timestamp'] = df_1h['timestamp']
                    df_1h_temp = df_1h_temp.dropna().sort_values('timestamp')
                    if not df_1h_temp.empty:
                        df_sorted = pd.merge_asof(df_sorted, df_1h_temp, on='timestamp', direction='backward')
                        df_sorted['MTF_1h_trend'] = (df_sorted['close'] > df_sorted['EMA50_1h']).astype(int)
                        df_sorted = df_sorted.drop(columns=['EMA50_1h'])

            if df_4h is not None and not df_4h.empty and 'timestamp' in df_4h.columns:
                ema50_4h = _calc_ema(df_4h['close'], length=50)
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
        df['EMA_20'] = _calc_ema(df['close'], length=20)
        df['EMA_50'] = _calc_ema(df['close'], length=50)
        df['EMA_200'] = _calc_ema(df['close'], length=200)
        
        df['EMA_diff']      = df['EMA_20'] - df['EMA_50']
        df['EMA_diff_norm'] = df['EMA_diff'] / (df['close'] * 0.001 + 1e-9)

        # ── 2. MOMENTUM ─────────────────────────────────────────────────────
        df['RSI'] = _calc_rsi(df['close'], length=14)
        
        macd_line, macd_sig, macd_hist = _calc_macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD']        = macd_line
        df['MACD_signal'] = macd_sig
        df['MACD_hist']   = macd_hist

        # ── 7. ALTERNATIVE DATA (Institucional) ─────────────────────────────
        if 'funding_rate' not in df.columns:
            df['funding_rate'] = 0.0
        df['funding_rate'] = df['funding_rate'].fillna(0.0)
        df['fear_and_greed'] = self._get_fear_and_greed()

        # ── 3. VOLATILIDAD ──────────────────────────────────────────────────
        df['ATR'] = _calc_atr(df['high'], df['low'], df['close'], length=14)
        df['ATR_pct'] = df['ATR'] / df['close'] * 100

        bbu, bbl = _calc_bbands(df['close'], length=20, std=2.0)
        df['BB_upper']    = bbu
        df['BB_lower']    = bbl
        df['BB_width']    = (df['BB_upper'] - df['BB_lower']) / df['close'] * 100
        df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 1e-9)

        # ── 4. VOLUMEN ──────────────────────────────────────────────────────
        df['volume_ma'] = _calc_ema(df['volume'], length=20)
        df['volume_ratio'] = df['volume'] / (df['volume_ma'] + 1e-9)

        # ── 5. SEÑALES BINARIAS ──────────────────────────────────────────────
        df['trend_signal']    = (df['EMA_20']   > df['EMA_50']).astype(int)
        df['above_ema200']    = (df['close']     > df['EMA_200']).astype(int)
        df['momentum_signal'] = (df['MACD_hist'] > 0).astype(int)

        # ── 6. VWAP ─────────────────────────────────────────────────────────
        typical_price  = (df['high'] + df['low'] + df['close']) / 3
        window = min(100, len(df))
        cum_tp_vol = (
            typical_price * df['volume']
        ).rolling(window, min_periods=1).sum()
        cum_vol = (
            df['volume']
        ).rolling(window, min_periods=1).sum()
        df['VWAP']     = cum_tp_vol / (cum_vol + 1e-9)
        df['VWAP_dist'] = (df['close'] - df['VWAP']) / (df['VWAP'] + 1e-9) * 100

        # ── 7. ORDERFLOW DELTA ──────────────────────────────────────────────
        candle_range      = df['high'] - df['low'] + 1e-9
        close_position    = (df['close'] - df['low']) / candle_range
        df['delta']       = (close_position - 0.5) * 2 * df['volume']
        df['delta_cum5']  = df['delta'].rolling(5, min_periods=1).sum()
        df['delta_cum10'] = df['delta'].rolling(10, min_periods=1).sum()
        price_change5     = df['close'].diff(5).fillna(0)
        df['delta_div']   = np.sign(price_change5) * np.sign(df['delta_cum5'])

        # ── 8. WYCKOFF ──────────────────────────────────────────────────────
        df['price_slope'] = df['close'].diff(10).fillna(0) / (df['close'].shift(10).fillna(df['close']) + 1e-9) * 100
        df['range_pct']   = (df['high'].rolling(20, min_periods=1).max() - df['low'].rolling(20, min_periods=1).min()) / df['close'] * 100

        # ── 9. ESTRUCTURA SMC ────────────────────────────────────────────────
        df['struct_high']      = df['high'].rolling(20, min_periods=1).max()
        df['struct_low']       = df['low'].rolling(20, min_periods=1).min()
        df['near_struct_high'] = (abs(df['close'] - df['struct_high']) / df['close'] < 0.002).astype(int)
        df['near_struct_low']  = (abs(df['close'] - df['struct_low'])  / df['close'] < 0.002).astype(int)

        # ── LIMPIEZA FINAL: Preservar la última vela viva en tiempo real ──
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.ffill().bfill().fillna(0.0)

        return df

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