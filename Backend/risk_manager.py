import config


class RiskManager:
    def __init__(self):
        self._current_risk       = config.RISK_PER_TRADE
        self._consecutive_wins   = 0
        self._consecutive_losses = 0

    def register_result(self, result):
        if result == 'WIN':
            self._consecutive_losses = 0
            self._consecutive_wins  += 1
            if self._consecutive_wins >= config.MAX_CONSECUTIVE_WINS:
                new_risk = min(
                    self._current_risk * config.RISK_INCREASE_FACTOR,
                    config.MAX_RISK_CAP,
                )
                if new_risk != self._current_risk:
                    self._current_risk = new_risk
                    print(f"📈 Racha ganadora — riesgo subido a {self._current_risk:.1%}")
        else:
            self._consecutive_wins   = 0
            self._consecutive_losses += 1
            if self._consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
                new_risk = max(
                    self._current_risk * config.RISK_REDUCTION_FACTOR,
                    config.RISK_PER_TRADE * 0.25,
                )
                if new_risk != self._current_risk:
                    self._current_risk = new_risk
                    print(f"📉 Racha perdedora — riesgo reducido a {self._current_risk:.1%}")

    def get_current_risk(self):
        return self._current_risk

    def get_streak_info(self):
        return self._consecutive_wins, self._consecutive_losses

    def calculate_position_size(self, account_balance, entry_price, stop_loss_price):
        if stop_loss_price is None:
            notional = account_balance * config.NO_SL_SIZE_PCT
            size     = round(notional / entry_price, 6)
        else:
            risk_amount   = account_balance * self._current_risk
            risk_per_coin = abs(entry_price - stop_loss_price)
            if risk_per_coin == 0:
                return 0
            size = round((risk_amount / risk_per_coin) / config.MAX_BULLETS, 6)

        if config.MIN_SIZE_USDT > 0 and size * entry_price < config.MIN_SIZE_USDT:
            print(f"⚠️ Size {size * entry_price:.2f} USDT < mínimo — cancelado")
            return 0

        return size

    def calculate_dynamic_stops(self, current_price, atr_value, action):
        if action == 'LONG':
            sl = current_price - (atr_value * config.ATR_MULTIPLIER)
            tp = current_price + (atr_value * config.TP_MULTIPLIER)
        else:
            sl = current_price + (atr_value * config.ATR_MULTIPLIER)
            tp = current_price - (atr_value * config.TP_MULTIPLIER)
        return round(sl, 2), round(tp, 2)

    def calculate_trailing_stop(self, trade, current_price, atr_value):
        entry      = trade['entry_price']
        tp         = trade['tp']
        action     = trade['action']
        dist_total = abs(tp - entry)

        if dist_total == 0:
            return None

        dist_moved = (current_price - entry) if action == 'LONG' else (entry - current_price)

        if dist_moved < dist_total * config.TRAILING_STOP_ACTIVATION:
            return None

        trail_dist = atr_value * config.TRAILING_STOP_DISTANCE
        if action == 'LONG':
            new_sl = round(current_price - trail_dist, 2)
            if trade['sl'] is None or new_sl > trade['sl']:
                return new_sl
        else:
            new_sl = round(current_price + trail_dist, 2)
            if trade['sl'] is None or new_sl < trade['sl']:
                return new_sl

        return None

    def calculate_averaging_levels(self, entry_price, atr_value, action):
        if action == 'LONG':
            dca = [entry_price - atr_value * 0.5, entry_price - atr_value * 1.0]
        else:
            dca = [entry_price + atr_value * 0.5, entry_price + atr_value * 1.0]
        return [round(l, 2) for l in dca]