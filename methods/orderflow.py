def analyze(features):
    if len(features) < 10:
        return None, 0

    df    = features.copy()
    close = df['close'].values
    high  = df['high'].values
    low   = df['low'].values
    vol   = df['volume'].values

    candle_range   = high - low + 1e-9
    close_position = (close - low) / candle_range
    delta          = (close_position - 0.5) * 2 * vol

    cum_delta_5  = delta[-5:].sum()
    cum_delta_10 = delta[-10:].sum()
    price_change_5  = close[-1] - close[-6]
    price_change_10 = close[-1] - close[-11]

    last_vol_ratio = df['volume_ratio'].iloc[-1] if 'volume_ratio' in df.columns else 1.0

    bearish_div = price_change_5 > 0 and cum_delta_5 < 0 and last_vol_ratio > 1.0
    bullish_div = price_change_5 < 0 and cum_delta_5 > 0 and last_vol_ratio > 1.0

    if bearish_div:
        conf = 0.80 if (price_change_10 > 0 and cum_delta_10 < 0) else 0.68
        return 0, conf

    if bullish_div:
        conf = 0.80 if (price_change_10 < 0 and cum_delta_10 > 0) else 0.68
        return 1, conf

    if cum_delta_5 > 0 and price_change_5 > 0 and last_vol_ratio > 1.3:
        return 1, 0.65

    if cum_delta_5 < 0 and price_change_5 < 0 and last_vol_ratio > 1.3:
        return 0, 0.65

    return None, 0