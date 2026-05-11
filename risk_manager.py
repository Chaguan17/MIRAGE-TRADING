import config


class RiskManager:
    def __init__(self):
        self.risk_per_trade = config.RISK_PER_TRADE
        self.max_bullets    = config.MAX_BULLETS

    def calculate_position_size(self, account_balance, entry_price, stop_loss_price):
        """
        Con SL  → tamaño basado en riesgo monetario fijo (RISK_PER_TRADE % del balance).
        Sin SL  → posición conservadora fija (NO_SL_SIZE_PCT % del balance nocional).
        """
        if stop_loss_price is None:
            notional = account_balance * config.NO_SL_SIZE_PCT
            return round(notional / entry_price, 6)

        risk_amount   = account_balance * self.risk_per_trade
        risk_per_coin = abs(entry_price - stop_loss_price)
        if risk_per_coin == 0:
            return 0
        total_size  = risk_amount / risk_per_coin
        bullet_size = total_size / self.max_bullets
        return round(bullet_size, 6)

    def calculate_dynamic_stops(self, current_price, atr_value, action):
        """
        SL y TP basados en ATR con multiplicadores desde config.
        El llamador decide si usa el SL según brain.use_sl.
        """
        if action == 'LONG':
            sl = current_price - (atr_value * config.ATR_MULTIPLIER)
            tp = current_price + (atr_value * config.TP_MULTIPLIER)
        else:
            sl = current_price + (atr_value * config.ATR_MULTIPLIER)
            tp = current_price - (atr_value * config.TP_MULTIPLIER)
        return round(sl, 2), round(tp, 2)

    def calculate_averaging_levels(self, entry_price, atr_value, action):
        if action == 'LONG':
            dca = [entry_price - atr_value * 0.5, entry_price - atr_value * 1.0]
        else:
            dca = [entry_price + atr_value * 0.5, entry_price + atr_value * 1.0]
        return [round(l, 2) for l in dca]