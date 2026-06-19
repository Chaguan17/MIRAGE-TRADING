import os
import pandas as pd
import logging
import config as cfg
import numpy as np
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
        self.fee_rate = 0.0004 # Agregado: Tasa de comisión por operación
        self.slippage = 0.0005 # Agregado: Simulación de slippage
        self.spread = 0.0002   # Agregado: Spread promedio (0.02%)

    def run(self):
        print(f"🧪 Iniciando backtest para {self.symbol} ({len(self.df)} velas)...")
        
        # Iniciamos tras el warmup de indicadores (RSI/EMA necesitan datos previos)
        for i in range(101, len(self.df)):
            row = self.df.iloc[i]
            
            # 1. Monitorear trades activos
            if self.active_trade:
                self._check_exit(row)
                continue 

            # 2. Eliminar Leakage: Predicción con vela i-1
            lookback = self.df.iloc[:i]
            btc_look = self.btc_df.iloc[:i] if self.btc_df is not None else None
            
            if lookback.empty: continue
            last_closed_row = lookback.iloc[-1]
            
            action, conf, method, use_sl = self.brain.get_consensus_prediction(
                last_closed_row.to_dict(), 
                features_df=lookback, 
                btc_features=btc_look
            )

            # 3. Abrir posición al precio de APERTURA de la vela actual (i)
            if action is not None and conf > cfg.MIN_CONFIDENCE:
                self._enter_trade(action, row, method, use_sl, entry_price=row['open'])

        self._summary()

    def _enter_trade(self, action, row, method, use_sl, entry_price=None):
        action_str = "LONG" if action == 1 else "SHORT"
        price = entry_price if entry_price else row['close']
        atr = row['ATR']
        
        sl, tp = self.rm.calculate_dynamic_stops(price, atr, action_str, row.get('ATR_pct'))
        size = self.rm.calculate_position_size(self.balance, price, sl if use_sl else None)

        if size > 0:
            # Aplicamos Spread y Slippage a la entrada
            if action_str == "LONG":
                real_entry = price * (1 + (self.spread / 2) + self.slippage)
            else:
                real_entry = price * (1 - (self.spread / 2) - self.slippage)

            self.active_trade = {
                'action': action_str,
                'entry_price': real_entry,
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
        exit_p = cp

        # Simulación de Liquidación (90% del margen)
        leverage = cfg.LEVERAGE
        liq_price = t['entry_price'] * (1 - 0.9 / leverage) if t['action'] == 'LONG' else t['entry_price'] * (1 + 0.9 / leverage)

        if t['action'] == 'LONG':
            if row['low'] <= liq_price: exit_p, res = liq_price, 'LIQUIDATED'
            elif cp >= t['tp']: exit_p, res = t['tp'], 'WIN'
            elif t['use_sl'] and cp <= t['sl']: exit_p, res = t['sl'], 'LOSS'
        else:
            if row['high'] >= liq_price: exit_p, res = liq_price, 'LIQUIDATED'
            elif cp <= t['tp']: exit_p, res = t['tp'], 'WIN'
            elif t['use_sl'] and cp >= t['sl']: exit_p, res = t['sl'], 'LOSS'

        if res:
            entry = t['entry_price']
            exit_real = exit_p

            # Salida con fricción (Slippage + Spread)
            if t['action'] == 'LONG':
                exit_real *= (1 - (self.spread / 2) - self.slippage)
            else:
                exit_real *= (1 + (self.spread / 2) + self.slippage)

            # PnL Bruto (Diferencia de precio * cantidad)
            if t['action'] == 'LONG':
                gross_pnl = (exit_real - entry) * t['size']
            else:
                gross_pnl = (entry - exit_real) * t['size']

            # Comisiones (Valor nocional entrada + Valor nocional salida) * tasa
            fees = (entry * t['size'] + exit_real * t['size']) * self.fee_rate

            pnl = gross_pnl - fees
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

        # Métricas Profesionales (Sharpe, DD, PF)
        total_pnl = df_h['pnl'].sum()
        wr = (df_h['res'] == 'WIN').mean()
        wins = df_h[df_h['res'] == 'WIN']['pnl']
        losses = df_h[df_h['res'].isin(['LOSS', 'LIQUIDATED'])]['pnl']
        
        profit_factor = wins.sum() / abs(losses.sum()) if not losses.empty and losses.sum() != 0 else float('inf')
        
        # Equity y Max Drawdown
        df_h['equity'] = cfg.PAPER_BALANCE + df_h['pnl'].cumsum()
        peak = df_h['equity'].cummax()
        drawdown_abs = peak - df_h['equity']
        max_dd_pct = (drawdown_abs / peak).max()
        max_dd_abs = drawdown_abs.max()

        # Sharpe Ratio simplificado por trade
        returns = df_h['pnl'] / (df_h['equity'].shift(1).fillna(cfg.PAPER_BALANCE))
        sharpe = (returns.mean() / returns.std() * np.sqrt(len(df_h))) if returns.std() != 0 else 0

        summary = (
            f"\n{'='*40}\n"
            f"📊 RESUMEN BACKTEST: {self.symbol}\n"
            f"Win Rate:       {wr:.1%}\n"
            f"PnL Neto:       {total_pnl:.2f} USDT\n"
            f"Profit Factor:  {profit_factor:.2f}\n"
            f"Max Drawdown:   {max_dd_pct:.2%} ({max_dd_abs:.2f} USDT)\n"
            f"Sharpe Ratio:   {sharpe:.2f}\n"
            f"{'='*40}"
        )
        cfg.trade_logger.info(summary)
        
        profit_factor = wins.sum() / abs(losses.sum()) if not losses.empty and losses.sum() != 0 else float('inf')
        
        # Equity y Drawdown
        df_h['equity'] = cfg.PAPER_BALANCE + df_h['pnl'].cumsum()
        peak = df_h['equity'].cummax()
        drawdown_abs = peak - df_h['equity']
        max_dd_pct = (drawdown_abs / peak).max()
        max_dd_abs = drawdown_abs.max()

        # Sharpe / Sortino (Aprox. por trade)
        returns = df_h['pnl'] / (df_h['equity'].shift(1).fillna(cfg.PAPER_BALANCE))
        sharpe = (returns.mean() / returns.std() * np.sqrt(len(df_h))) if returns.std() != 0 else 0
        neg_returns = returns[returns < 0]
        sortino = (returns.mean() / neg_returns.std() * np.sqrt(len(df_h))) if not neg_returns.empty and neg_returns.std() != 0 else float('inf')

        # Expectancy
        expectancy = (wr * (wins.mean() if not wins.empty else 0)) + ((1 - wr) * (losses.mean() if not losses.empty else 0))

        # Recovery Factor
        recovery_factor = total_pnl / max_dd_abs if max_dd_abs != 0 else float('inf')

        summary = (
            f"\n{'='*40}\n"
            f"📊 RESUMEN BACKTEST: {self.symbol}\n"
            f"Trades totales: {len(df_h)}\n"
            f"Win Rate:       {wr:.1%}\n"
            f"PnL Neto:       {total_pnl:.2f} USDT\n"
            f"Balance Final:  {self.balance:.2f} USDT\n"
            f"{'-' * 20}\n"
            f"Profit Factor:  {profit_factor:.2f}\n"
            f"Max Drawdown:   {max_dd_pct:.2%} ({max_dd_abs:.2f} USDT)\n"
            f"Expectancy:     {expectancy:.2f} USDT/trade\n"
            f"Sharpe Ratio:   {sharpe:.2f}\n"
            f"Sortino Ratio:  {sortino:.2f}\n"
            f"Recovery Factor:{recovery_factor:.2f}\n"
            f"{'='*40}"
        )
        cfg.trade_logger.info(summary)
        if 'LIQUIDATED' in df_h['res'].values:
            cfg.trade_logger.warning(f"💀 LIQUIDACIONES: {len(df_h[df_h['res'] == 'LIQUIDATED'])}")