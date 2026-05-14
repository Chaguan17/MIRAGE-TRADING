import config


def analyze(features, btc_features=None):
    if btc_features is None or len(btc_features) < 10:
        return None, 0

    if len(features) < 10:
        return None, 0

    alt_close   = features['close'].values[-10:]
    alt_returns = [(alt_close[i] - alt_close[i-1]) / alt_close[i-1]
                   for i in range(1, len(alt_close))]

    btc_close   = btc_features['close'].values[-10:]
    btc_returns = [(btc_close[i] - btc_close[i-1]) / btc_close[i-1]
                   for i in range(1, len(btc_close))]

    if len(alt_returns) < 5 or len(btc_returns) < 5:
        return None, 0

    min_len = min(len(alt_returns), len(btc_returns))
    a = alt_returns[-min_len:]
    b = btc_returns[-min_len:]

    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)
    cov    = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(len(a)))
    std_a  = (sum((x - mean_a) ** 2 for x in a) ** 0.5) + 1e-9
    std_b  = (sum((x - mean_b) ** 2 for x in b) ** 0.5) + 1e-9
    corr   = cov / (std_a * std_b)

    btc_trend = btc_close[-1] - btc_close[-4]
    alt_trend = alt_close[-1] - alt_close[-4]
    btc_up    = btc_trend > 0
    btc_down  = btc_trend < 0
    alt_up    = alt_trend > 0
    alt_down  = alt_trend < 0

    threshold = config.BTC_CORR_THRESHOLD

    if abs(corr) >= threshold:
        if btc_up and alt_up:
            return 1, 0.72
        if btc_down and alt_down:
            return 0, 0.72

    if btc_up and alt_down and abs(corr) >= threshold * 0.8:
        return 0, 0.75

    if btc_down and alt_up and abs(corr) >= threshold * 0.8:
        return 1, 0.75

    return None, 0