import config


def analyze(features):
    if len(features) < config.SMC_LOOKBACK + 5:
        return None, 0

    df       = features.copy()
    lookback = config.SMC_LOOKBACK
    last     = df.iloc[-1]
    price    = last['close']

    window      = df.iloc[-(lookback + 1):-1]
    struct_high = window['high'].max()
    struct_low  = window['low'].min()
    prev_high   = df.iloc[-(lookback + 1):-lookback // 2]['high'].max()
    prev_low    = df.iloc[-(lookback + 1):-lookback // 2]['low'].min()
    recent_high = df.iloc[-lookback // 2:-1]['high'].max()
    recent_low  = df.iloc[-lookback // 2:-1]['low'].min()

    bos_long  = price > struct_high and recent_high > prev_high
    bos_short = price < struct_low  and recent_low  < prev_low

    trend_up    = last.get('trend_signal', 0) == 1
    trend_down  = last.get('trend_signal', 0) == 0
    choch_short = trend_up   and price < recent_low
    choch_long  = trend_down and price > recent_high

    ob_long = ob_short = False
    for i in range(-5, -1):
        candle      = df.iloc[i]
        next_candle = df.iloc[i + 1]
        move_pct    = abs(next_candle['close'] - candle['close']) / (candle['close'] + 1e-9)

        if move_pct >= config.SMC_OB_STRENGTH:
            if candle['close'] < candle['open']:
                ob_long  = price >= candle['low'] and price <= candle['high']
            if candle['close'] > candle['open']:
                ob_short = price >= candle['low'] and price <= candle['high']

    if bos_long or choch_long:
        conf = 0.80 if (bos_long and ob_long) else 0.70
        return 1, conf

    if bos_short or choch_short:
        conf = 0.80 if (bos_short and ob_short) else 0.70
        return 0, conf

    return None, 0