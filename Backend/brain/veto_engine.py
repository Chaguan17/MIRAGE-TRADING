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

    def check_macro_crash(self, btc_features_df):
        """Revisa si BTC ha tenido una caída brusca en la última hora."""
        if btc_features_df is None or len(btc_features_df) < 2:
            return None
            
        # Determinar cuántas velas hay en 1 hora según TIMEFRAME
        tf = getattr(self.cfg, 'TIMEFRAME', '5m')
        if tf.endswith('m'):
            mins = int(tf.replace('m', ''))
            candles_1h = max(2, int(60 / mins))
        elif tf.endswith('h'):
            candles_1h = max(2, int(1 / int(tf.replace('h', ''))))
        else:
            candles_1h = 4
            
        if len(btc_features_df) < candles_1h:
            return None
            
        recent_closes = btc_features_df['close'].iloc[-candles_1h:].values
        start_price = recent_closes[0]
        end_price = recent_closes[-1]
        
        drop_pct = (start_price - end_price) / start_price
        
        if drop_pct >= self.cfg.VETO_CRASH_PCT:
            logger.warning(f"🚨 MACRO VETO: BTC ha caído un {drop_pct:.2%} en la última hora. Pausando LONGs en {self.symbol}.")
            return 'BTC Crash Veto'
            
        return None

    def check_ai_veto(self, ai_weight, ai_conf):
        """Veto si la IA detecta baja probabilidad a pesar del consenso técnico."""
        if ai_weight > 0.1 and ai_conf < 0.40:
            logger.info(f"🧠 IA VETO en {self.symbol}: Probabilidad de éxito baja ({ai_conf:.1%})")
            return True
        return False