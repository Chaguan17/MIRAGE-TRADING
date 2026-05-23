import os
import pandas as pd
import logging
import config as cfg
from brain import MirageBrain
from risk_manager import RiskManager
from data_engine import DataEngine

logger = logging.getLogger(__name__)

class SimpleBacktester:
    """
    Simula el mercado iterando sobre un DataFrame histórico, permitiendo que
    el cerebro de Mirage aprenda y ejecute operaciones como si estuviera en vivo.
    """
    def __init__(self, symbol, raw_df, btc_raw_df=None, test_dir="storage/backtests"):
        self.symbol = symbol
        self.test_dir = test_dir
        os.makedirs(self.test_dir, exist_ok=True)

        # Preparamos las features usando el DataEngine existente
        engine = DataEngine()
        print(f"📊 Generando features para {symbol}...")
        self.df = engine.prepare_features(raw_df)
        self.btc_df = engine.prepare_features(btc_raw_df) if btc_raw_df is not None else None
        
        # Instanciamos componentes aislados de la producción
        self.brain = MirageBrain(symbol=symbol, storage_dir=self.test_dir)
        self.rm = RiskManager()
        
        self.balance = cfg.PAPER_BALANCE
        self.active_trade = None
        self.history = []

    def run(self):
        print(f"🧪 Iniciando backtest para {self.symbol} ({len(self.df)} velas)...")
        
        # Iniciamos tras el warmup de indicadores (RSI/EMA necesitan datos previos)
        for i in range(100, len(self.df)):
            row = self.df.iloc[i]
            current_price = row['close']
            
            # 1. Monitorear trades activos
            if self.active_trade:
                self._check_exit(row)
                continue 

            # 2. Obtener señal (Slice del DF hasta 'i' para evitar look-ahead bias)
            lookback = self.df.iloc[:i+1]
            btc_look = self.btc_df.iloc[:i+1] if self.btc_df is not None else None
            
            action, conf, method, use_sl = self.brain.get_consensus_prediction(
                row.to_dict(), 
                features_df=lookback, 
                btc_features=btc_look
            )

            # 3. Abrir posición si hay consenso
            if action is not None and conf > cfg.MIN_CONFIDENCE:
                self._enter_trade(action, row, method, use_sl)

        self._summary()

    def _enter_trade(self, action, row, method, use_sl):
        action_str = "LONG" if action == 1 else "SHORT"
        price = row['close']
        atr = row['ATR']
        
        sl, tp = self.rm.calculate_dynamic_stops(price, atr, action_str, row.get('ATR_pct'))
        size = self.rm.calculate_position_size(self.balance, price, sl if use_sl else None)

        if size > 0:
            self.active_trade = {
                'action': action_str,
                'entry_price': price,
                'size': size,
                'sl': sl, 
                'tp': tp,
                'use_sl': use_sl,
                'method': method,
                'features': row.to_dict()
            }

    def _check_exit(self, row):
        t = self.active_trade
        cp = row['close']
        res = None
        exit_p = None

        if t['action'] == 'LONG':
            if cp >= t['tp']: exit_p, res = t['tp'], 'WIN'
            elif t['use_sl'] and cp <= t['sl']: exit_p, res = t['sl'], 'LOSS'
        else:
            if cp <= t['tp']: exit_p, res = t['tp'], 'WIN'
            elif t['use_sl'] and cp >= t['sl']: exit_p, res = t['sl'], 'LOSS'

        if res:
            pnl = (exit_p - t['entry_price']) * t['size'] if t['action'] == 'LONG' else (t['entry_price'] - exit_p) * t['size']
            self.balance += pnl
            self.history.append({'pnl': pnl, 'res': res, 'method': t['method']})
            
            # El cerebro aprende dinámicamente durante el backtest (Walk-forward learning)
            self.brain.online_update(t['features'], res, t['use_sl'], res == 'LOSS')
            self.rm.register_result(res)
            self.active_trade = None

    def _summary(self):
        df_h = pd.DataFrame(self.history)
        if df_h.empty:
            print("⚠️ No se ejecutaron operaciones.")
            return
        
        wr = (df_h['res'] == 'WIN').mean()
        print(f"\n{'='*40}")
        print(f"📊 RESUMEN BACKTEST: {self.symbol}")
        print(f"Trades totales: {len(df_h)}")
        print(f"Win Rate:       {wr:.1%}")
        print(f"PnL Neto:       {df_h['pnl'].sum():.2f} USDT")
        print(f"Balance Final:  {self.balance:.2f} USDT")
        print(f"{'='*40}")