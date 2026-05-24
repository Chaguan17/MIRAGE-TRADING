import logging
import pandas as pd

logger = logging.getLogger(__name__)

class VetoEngine:
    def __init__(self, symbol, config):
        self.symbol = symbol
        self.cfg = config

    def check_market_vetoes(self, tech_action, btc_action, btc_row):
        """Vetos basados en contexto de mercado (BTC, RSI)."""
        # Veto de BTC
        if self.symbol != "BTCUSDT" and btc_action is not None:
            if tech_action != btc_action:
                return 'BTC Trend Veto'

        # Veto de RSI Dinámico
        if btc_row is not None and 'RSI' in btc_row and 'ATR_pct' in btc_row:
            rsi = btc_row['RSI']
            vol = btc_row['ATR_pct']
            if not pd.isna(rsi) and not pd.isna(vol):
                vol_diff = vol - self.cfg.RSI_VOL_REF
                adjustment = vol_diff * self.cfg.RSI_VOL_ADJUSTMENT_FACTOR
                dyn_ob = max(65, min(85, self.cfg.GLOBAL_RSI_OB_BASE - adjustment))
                dyn_os = max(15, min(35, self.cfg.GLOBAL_RSI_OS_BASE + adjustment))

                if tech_action == 1 and rsi >= dyn_ob:
                    return 'RSI Overbought Veto'
                elif tech_action == 0 and rsi <= dyn_os:
                    return 'RSI Oversold Veto'
        
        return None

    def check_ai_veto(self, ai_weight, ai_conf):
        """Veto si la IA detecta baja probabilidad a pesar del consenso técnico."""
        if ai_weight > 0.1 and ai_conf < 0.40:
            logger.info(f"🧠 IA VETO en {self.symbol}: Probabilidad de éxito baja ({ai_conf:.1%})")
            return True
        return False