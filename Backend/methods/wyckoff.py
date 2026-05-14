import numpy as np
import config


def analyze(features):
    if len(features) < config.WYCKOFF_LOOKBACK:
        return None, 0

    df       = features.copy()
    lookback = config.WYCKOFF_LOOKBACK
    window   = df.iloc[-lookback:]

    close = window['close'].values
    high  = window['high'].values
    low   = window['low'].values
    vol   = window['volume'].values
    price = close[-1]

    range_high = high.max()
    range_low  = low.min()
    range_pct  = (range_high - range_low) / price * 100

    x         = np.arange(len(close))
    slope     = np.polyfit(x, close, 1)[0]
    slope_pct = slope / price * 100

    vol_first  = vol[:lookback // 2].mean()
    vol_second = vol[lookback // 2:].mean()
    vol_trend  = vol_second / (vol_first + 1e-9)

    last_vol_ratio = df['volume_ratio'].iloc[-1] if 'volume_ratio' in df.columns else 1.0

    recent_low  = low[-5:].min()
    recent_high = high[-5:].max()
    spring      = recent_low  < range_low  * 0.999 and price > range_low
    upthrust    = recent_high > range_high * 1.001 and price < range_high

    above_200 = df['above_ema200'].iloc[-1] if 'above_ema200' in df.columns else 0

    is_accumulation = (
        range_pct < 5.0
        and abs(slope_pct) < 0.01
        and vol_trend < 1.0
    )

    is_distribution = (
        range_pct < 5.0
        and abs(slope_pct) < 0.01
        and vol_trend < 1.0
        and above_200 == 1
    )

    is_markup   = slope_pct >  0.02 and vol_trend >= 1.0
    is_markdown = slope_pct < -0.02 and vol_trend >= 1.0

    if is_accumulation and spring:
        return 1, 0.82

    if is_distribution and upthrust:
        return 0, 0.82

    if is_markup:
        return 1, 0.70 if last_vol_ratio > 1.1 else 0.62

    if is_markdown:
        return 0, 0.70 if last_vol_ratio > 1.1 else 0.62

    if is_accumulation:
        return 1, 0.58

    if is_distribution:
        return 0, 0.58

    return None, 0