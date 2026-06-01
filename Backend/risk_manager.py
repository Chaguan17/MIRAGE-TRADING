"""
risk_manager.py — Mirage Trading
Gestión de riesgo ADAPTATIVA al capital disponible.

Objetivo: el bot ajusta el riesgo solo, sin intervención humana,
en función de su balance real vs balance inicial.
"""
import logging
import config

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, initial_balance: float | None = None):
        self._base_risk          = config.RISK_PER_TRADE
        self._current_risk       = config.RISK_PER_TRADE
        self._consecutive_wins   = 0
        self._consecutive_losses = 0
        self._martingale_step    = 0
        # Referencia de capital inicial para el sistema adaptativo
        self._initial_balance    = initial_balance or config.PAPER_BALANCE

    # ─── Sistema adaptativo ──────────────────────────────────────────────────

    def adapt_risk_to_capital(self, current_balance: float) -> float:
        """
        Ajusta el riesgo base en función del balance actual vs el inicial.

        - Si el balance cae por debajo del ADAPTIVE_DRAWDOWN_FLOOR → reduce riesgo
        - Si el balance supera ADAPTIVE_GROWTH_CEIL → permite escalar
        - En zona intermedia → usa el riesgo dinámico por rachas
        """
        if not config.ADAPTIVE_RISK_ENABLED:
            return self._current_risk

        ratio = current_balance / (self._initial_balance + 1e-9)

        if ratio < config.ADAPTIVE_DRAWDOWN_FLOOR:
            # Capital menguado → riesgo mínimo de seguridad
            safe_risk = max(
                config.ADAPTIVE_RISK_FLOOR,
                self._base_risk * ratio  # proporcional a cuánto ha caído
            )
            if safe_risk < self._current_risk:
                logger.warning(
                    f"⚠️ Balance caído al {ratio:.1%} del inicial → "
                    f"riesgo adaptado: {safe_risk:.2%}"
                )
                self._current_risk = safe_risk

        elif ratio > config.ADAPTIVE_GROWTH_CEIL:
            # Capital crecido → permitir aumentar el riesgo conservadoramente
            growth_risk = min(
                config.ADAPTIVE_RISK_CEIL,
                self._base_risk * (1 + (ratio - 1) * 0.3)  # 30% del crecimiento
            )
            if growth_risk > self._current_risk:
                logger.info(
                    f"📈 Balance creció al {ratio:.1%} del inicial → "
                    f"riesgo adaptado: {growth_risk:.2%}"
                )
                self._current_risk = growth_risk

        # Clamp final de seguridad
        self._current_risk = max(
            config.ADAPTIVE_RISK_FLOOR,
            min(self._current_risk, config.ADAPTIVE_RISK_CEIL)
        )
        return self._current_risk

    # ─── Registro de resultados ──────────────────────────────────────────────

    def register_result(self, result: str):
        if result == 'WIN':
            self._martingale_step    = 0
            self._consecutive_losses = 0
            self._consecutive_wins  += 1
            if self._consecutive_wins >= config.MAX_CONSECUTIVE_WINS:
                new_risk = min(
                    self._current_risk * config.RISK_INCREASE_FACTOR,
                    config.MAX_RISK_CAP,
                )
                if new_risk != self._current_risk:
                    self._current_risk = new_risk
                    logger.info(f"📈 Racha ganadora → riesgo: {self._current_risk:.2%}")
        else:
            self._consecutive_wins   = 0
            self._consecutive_losses += 1

            if config.MARTINGALE_ENABLED and self._martingale_step < config.MARTINGALE_MAX_STEPS:
                self._martingale_step += 1
                new_risk = min(
                    self._current_risk * config.MARTINGALE_MULTIPLIER,
                    config.MAX_RISK_CAP
                )
                self._current_risk = new_risk
                logger.warning(
                    f"⚠️ MARTINGALA paso {self._martingale_step} → "
                    f"riesgo: {self._current_risk:.2%}"
                )
            elif (not config.MARTINGALE_ENABLED and
                  self._consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES):
                new_risk = max(
                    self._current_risk * config.RISK_REDUCTION_FACTOR,
                    config.RISK_PER_TRADE * 0.25,
                )
                if new_risk != self._current_risk:
                    self._current_risk = new_risk
                    logger.info(f"📉 Racha perdedora → riesgo: {self._current_risk:.2%}")

        # Clamp de seguridad tras cualquier cambio
        self._current_risk = max(
            config.ADAPTIVE_RISK_FLOOR,
            min(self._current_risk, config.MAX_RISK_CAP)
        )

    # ─── Sizing de posición ──────────────────────────────────────────────────

    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss_price: float | None,
        current_balance: float | None = None,
    ) -> float:
        """
        Calcula el tamaño de posición.
        Si se pasa current_balance, el riesgo se adapta al capital real.
        """
        if current_balance is not None:
            self.adapt_risk_to_capital(current_balance)

        if entry_price <= 0:
            return 0

        total_buying_power = account_balance * config.LEVERAGE
        risk_amount = account_balance * self._current_risk

        if stop_loss_price is None:
            notional = min(
                total_buying_power * 0.10,
                account_balance * config.NO_SL_SIZE_PCT
            )
            size = round(notional / entry_price, 6)
        else:
            risk_per_coin = abs(entry_price - stop_loss_price)
            if risk_per_coin == 0:
                return 0
            size = round((risk_amount / risk_per_coin) / config.MAX_BULLETS, 6)

        # Cap de apalancamiento real
        max_notional_per_bullet = total_buying_power / config.MAX_BULLETS
        current_notional = size * entry_price
        if current_notional > max_notional_per_bullet:
            logger.warning(
                f"📏 Size ajustado: {current_notional:.2f} → "
                f"{max_notional_per_bullet:.2f} USDT (cap leverage)"
            )
            size = round(max_notional_per_bullet / entry_price, 6)

        if config.MIN_SIZE_USDT > 0 and size * entry_price < config.MIN_SIZE_USDT:
            logger.debug(f"Size {size * entry_price:.2f} USDT < mínimo {config.MIN_SIZE_USDT} → cancelado")
            return 0

        return size

    # ─── Stops dinámicos ─────────────────────────────────────────────────────

    def calculate_dynamic_stops(
        self,
        current_price: float,
        atr_value: float,
        action: str,
        atr_pct: float | None = None,
    ) -> tuple[float, float]:
        tp_mult = config.TP_MULTIPLIER
        sl_mult = config.ATR_MULTIPLIER

        if atr_pct is not None:
            vol_diff_tp = atr_pct - config.TP_VOL_REF
            tp_mult = max(config.TP_MIN_MULTIPLIER,
                          config.TP_MULTIPLIER - vol_diff_tp * config.TP_VOL_ADJUSTMENT_FACTOR)

            vol_diff_sl = atr_pct - config.SL_VOL_REF
            sl_mult = max(config.SL_MIN_MULTIPLIER,
                          config.ATR_MULTIPLIER - vol_diff_sl * config.SL_VOL_ADJUSTMENT_FACTOR)

        if action == 'LONG':
            sl = current_price - (atr_value * sl_mult)
            tp = current_price + (atr_value * tp_mult)
        else:
            sl = current_price + (atr_value * sl_mult)
            tp = current_price - (atr_value * tp_mult)

        return round(sl, 4), round(tp, 4)

    # ─── Trailing & Breakeven ────────────────────────────────────────────────
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

        trail_dist = current_price * config.TRAILING_STOP_DISTANCE

        if action == 'LONG':
            new_sl = round(current_price - trail_dist, 4)
            if trade['sl'] is None or new_sl > trade['sl']:
                return new_sl
            else:
                new_sl = round(current_price + trail_dist, 4)
                if trade['sl'] is None or new_sl < trade['sl']:
                    return new_sl
        return None


    def calculate_breakeven_stop(
        self,
        trade: dict,
        current_price: float,
    ) -> float | None:
        if trade.get('is_breakeven', False) or trade.get('is_trailing', False):
            return None

        entry      = trade['entry_price']
        tp         = trade['tp']
        action     = trade['action']
        dist_total = abs(tp - entry)

        if dist_total == 0:
            return None

        dist_moved = (current_price - entry) if action == 'LONG' else (entry - current_price)
        if dist_moved >= dist_total * config.BREAKEVEN_ACTIVATION:
            return entry

        return None

    def calculate_averaging_levels(
        self,
        entry_price: float,
        atr_value: float,
        action: str,
    ) -> list[float]:
        if action == 'LONG':
            dca = [entry_price - atr_value * 0.5, entry_price - atr_value * 1.0]
        else:
            dca = [entry_price + atr_value * 0.5, entry_price + atr_value * 1.0]
        return [round(l, 4) for l in dca]

    # ─── Getters ─────────────────────────────────────────────────────────────

    def get_current_risk(self) -> float:
        return self._current_risk

    def get_streak_info(self) -> tuple[int, int]:
        return self._consecutive_wins, self._consecutive_losses

    def get_status_dict(self) -> dict:
        """Devuelve un snapshot del estado del risk manager para el dashboard."""
        return {
            "current_risk_pct":  round(self._current_risk * 100, 2),
            "base_risk_pct":     round(self._base_risk * 100, 2),
            "consecutive_wins":  self._consecutive_wins,
            "consecutive_losses":self._consecutive_losses,
            "martingale_step":   self._martingale_step,
        }
