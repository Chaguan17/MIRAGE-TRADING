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
        # Referencia de capital inicial y pico histórico (High-Water Mark)
        self._initial_balance    = initial_balance or config.PAPER_BALANCE
        self._high_water_mark    = self._initial_balance

    # ─── Sistema adaptativo ──────────────────────────────────────────────────

    def adapt_risk_to_capital(self, current_balance: float) -> float:
        """
        Ajusta el riesgo base en función del balance actual vs el pico histórico (High-Water Mark).

        - Actualiza constantemente el pico de equidad (_high_water_mark).
        - Si el balance cae por debajo del ADAPTIVE_DRAWDOWN_FLOOR relativo al pico → reduce riesgo para proteger ganancias acumuladas.
        - Si el balance alcanza un nuevo récord → escala el riesgo conservadoramente.
        """
        if not config.ADAPTIVE_RISK_ENABLED or current_balance <= 0:
            return self._current_risk

        # Actualizar el pico histórico de balance (High-Water Mark)
        if current_balance > self._high_water_mark:
            self._high_water_mark = current_balance

        # Calcular el ratio respecto al pico histórico de la cuenta
        ratio = current_balance / (self._high_water_mark + 1e-9)

        if ratio < config.ADAPTIVE_DRAWDOWN_FLOOR:
            # Capital menguado respecto al pico → riesgo mínimo de seguridad
            safe_risk = max(
                config.ADAPTIVE_RISK_FLOOR,
                self._base_risk * ratio
            )
            if safe_risk < self._current_risk:
                logger.warning(
                    f"⚠️ Drawdown detectado ({ratio:.1%} del pico histórico ${self._high_water_mark:.2f}) → "
                    f"riesgo adaptado: {safe_risk:.2%}"
                )
                self._current_risk = safe_risk

        elif ratio >= 1.0:
            growth_ratio = current_balance / (self._initial_balance + 1e-9)
            if growth_ratio > config.ADAPTIVE_GROWTH_CEIL:
                growth_risk = min(
                    config.ADAPTIVE_RISK_CEIL,
                    self._base_risk * (1 + (growth_ratio - 1) * 0.3)
                )
                if growth_risk > self._current_risk:
                    logger.info(
                        f"📈 Nuevo pico de balance (${current_balance:.2f}) → "
                        f"riesgo adaptado: {growth_risk:.2%}"
                    )
                    self._current_risk = growth_risk

        # Clamp final de seguridad
        self._current_risk = max(
            config.ADAPTIVE_RISK_FLOOR,
            min(self._current_risk, config.ADAPTIVE_RISK_CEIL)
        )
        return self._current_risk

    def is_kill_switch_triggered(self, current_balance: float) -> bool:
        """
        Verifica si el Drawdown total del capital ha superado el límite de parada de emergencia.
        (Ej: caída > 15% respecto al pico histórico o balance inicial).
        """
        if current_balance <= 0:
            return True

        max_dd_limit = getattr(config, 'MAX_DRAWDOWN_HALT_PCT', 0.15)
        # Comparar contra pico histórico y balance inicial
        ref_equity = max(self._high_water_mark, self._initial_balance)
        if ref_equity <= 0:
            return False

        drawdown_pct = (ref_equity - current_balance) / ref_equity
        if drawdown_pct >= max_dd_limit:
            logger.critical(
                f"🚨 KILL SWITCH ACTIVADO: Drawdown del {drawdown_pct:.2%} superó el máximo permitido ({max_dd_limit:.2%}) "
                f"| Equity actual: ${current_balance:.2f} | Pico: ${ref_equity:.2f}"
            )
            return True
        return False

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
        symbol: str = "ETHUSDT",
    ) -> float:
        """
        Calcula el tamaño de posición adaptado a las precisiones y nocional mínimo del símbolo.
        """
        if current_balance is not None:
            self.adapt_risk_to_capital(current_balance)

        if entry_price <= 0:
            return 0

        total_buying_power = account_balance * config.LEVERAGE
        risk_amount = account_balance * self._current_risk

        effective_bullets = 1 if account_balance < 15.0 else config.MAX_BULLETS
        max_notional_per_bullet = total_buying_power / effective_bullets

        if stop_loss_price is None:
            notional = min(
                total_buying_power * 0.50,
                account_balance * config.NO_SL_SIZE_PCT
            )
            size = round(notional / entry_price, 6)
        else:
            risk_per_coin = abs(entry_price - stop_loss_price)
            if risk_per_coin == 0:
                return 0
            size = round((risk_amount / risk_per_coin) / effective_bullets, 6)

        # Determinar precisiones y nocional mínimo según el símbolo en Binance Futuros
        import math
        sym_upper = str(symbol or "ETHUSDT").upper()
        
        default_min_notional = max(float(getattr(config, 'MIN_SIZE_USDT', 5.0) or 5.0), 22.5)
        symbol_rules = {
            "BTC":  {"min": 52.5, "step": 0.001, "prec": 3},
            "ETH":  {"min": 22.5, "step": 0.001, "prec": 3},
            "XRP":  {"min": 22.5, "step": 1.0,   "prec": 0},
            "DOGE": {"min": 5.0,  "step": 1.0,   "prec": 0},
            "SOL":  {"min": 5.0,  "step": 0.1,   "prec": 1},
            "ADA":  {"min": 5.0,  "step": 1.0,   "prec": 0},
            "HBAR": {"min": 5.0,  "step": 1.0,   "prec": 0},
        }

        min_required_notional = default_min_notional
        step = 0.01
        prec = 2
        
        for k, rules in symbol_rules.items():
            if k in sym_upper:
                min_required_notional = rules.get("min", default_min_notional)
                step = rules["step"]
                prec = rules["prec"]
                break

        current_notional = size * entry_price
        if current_notional > max_notional_per_bullet:
            logger.warning(
                f"📏 Size ajustado: {current_notional:.2f} → "
                f"{max_notional_per_bullet:.2f} USDT (cap leverage)"
            )
            raw_cap_size = max_notional_per_bullet / entry_price
            size = round(math.floor(raw_cap_size / step) * step, prec)

        current_notional = size * entry_price
        if current_notional < min_required_notional:
            if total_buying_power >= min_required_notional:
                raw_min_size = min_required_notional / entry_price
                size = round(math.ceil(raw_min_size / step) * step, prec)
                new_notional = size * entry_price
                logger.info(
                    f"📐 Ajustando notional de ${current_notional:.2f} USDT al mínimo de Binance "
                    f"(${new_notional:.2f} USDT | Size: {size})"
                )
            else:
                logger.warning(
                    f"⚠️ Poder de compra ${total_buying_power:.2f} USDT < mínimo de Binance (${min_required_notional:.2f} USDT)"
                )
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

        # Trailing Dinámico Basado en Volatilidad
        if atr_value and atr_value > 0:
            trail_dist = atr_value * getattr(config, 'TRAILING_ATR_MULTIPLIER', 0.5)
        else:
            trail_dist = current_price * 0.0025 # Fallback estático
            

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
        mult1 = config.DCA_ATR_MULT_1
        mult2 = config.DCA_ATR_MULT_2

        # Piso de seguridad: Garantiza que la distancia mínima sea al menos 0.8% para DCA 1 y 1.5% para DCA 2
        # Esto evita re-compras prematuras en oscilaciones de $0.50 o ruido menor.
        min_dist1 = entry_price * 0.008
        min_dist2 = entry_price * 0.015

        dist1 = max(atr_value * mult1, min_dist1)
        dist2 = max(atr_value * mult2, min_dist2)

        if action == 'LONG':
            dca = [entry_price - dist1, entry_price - dist2]
        else:
            dca = [entry_price + dist1, entry_price + dist2]
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
