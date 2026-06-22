# brain/signal_engine.py
from strategies import (
    trend_follower, mean_reversion, breakout_logic,
    smc_structure, vwap_method, liquidity_zones,
    orderflow, wyckoff, btc_correlation,
)

class SignalEngine:
    def __init__(self, active_strategies):
        self.active = active_strategies

    def get_signals(self, df, btc_features=None):
        """Evalúa las capas de estrategias técnicas."""
        
        # Definición de mapeo para ejecución perezosa (lazy execution)
        strategy_map = {
            'trend':     lambda: trend_follower.analyze(df),
            'reversion': lambda: mean_reversion.analyze(df),
            'breakout':  lambda: breakout_logic.analyze(df),
            'smc':       lambda: smc_structure.analyze(df),
            'vwap':      lambda: vwap_method.analyze(df),
            'liquidity': lambda: liquidity_zones.analyze(df),
            'orderflow': lambda: orderflow.analyze(df),
            'wyckoff':   lambda: wyckoff.analyze(df),
            'btc_corr':  lambda: btc_correlation.analyze(df, btc_features)
        }

        # Solo ejecutamos si la estrategia está en la lista de activos
        basic_signals = {
            k: strategy_map[k]() for k in ['trend', 'reversion', 'breakout'] 
            if k in self.active
        }
        
        structure_signals = {
            k: strategy_map[k]() for k in ['smc', 'vwap', 'liquidity'] 
            if k in self.active
        }
        
        context_signals = {
            k: strategy_map[k]() for k in ['orderflow', 'wyckoff', 'btc_corr'] 
            if k in self.active
        }
        
        return basic_signals, structure_signals, context_signals