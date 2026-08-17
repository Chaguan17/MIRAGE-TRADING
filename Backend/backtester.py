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
    Simulador de Ejecución Fiel de Mirage Trading.
    """

    def __init__(self, symbol, raw_df, btc_raw_df=None, test_dir="storage/backtests"):
        self.symbol = symbol
        self.test_dir = test_dir
        os.makedirs(self.test_dir, exist_ok=True)

        # Preparamos las features usando el DataEngine existente
        engine = DataEngine()
        logger.info(f"📊 Generando features para {symbol}...")
        self.df = engine.prepare_features(raw_df)
        self.btc_df = engine.prepare_features(btc_raw_df) if btc_raw_df is not None else None

        # Instanciamos componentes aislados de la producción
        self.brain = MirageBrain(symbol=symbol, storage_dir=self.test_dir)
        self.rm = RiskManager()

        self.balance = cfg.PAPER_BALANCE
        self.active_trade = None
        self.history = []

        # Tasas de comisión Binance Futuros (VIP 0)
        self.maker_fee = 0.0002  # 0.020% (Órdenes Límite)
        self.taker_fee = 0.0005  # 0.050% (Órdenes Mercado / Stop)
        self.slippage = 0.0005   # 0.050% Slippage promedio
        self.spread = 0.0002     # 0.020% Spread promedio (0.01% por lado)

    def run(self):
        print(f"🧪 Iniciando backtest para {self.symbol} ({len(self.df)} velas)...")

        # Iniciamos tras el warmup de indicadores (100 velas)
        for i in range(101, len(self.df)):
            row = self.df.iloc[i]

            # 1. Monitorear y evaluar salidas de trade activo en la vela actual (i)
            if self.active_trade:
                self._check_exit(row)

            # 2. Si no hay trade activo, evaluar nueva entrada basada en vela anterior (i-1) - ZERO LEAKAGE
            if not self.active_trade:
                lookback = self.df.iloc[:i]
                btc_look = self.btc_df.iloc[:i] if self.btc_df is not None else None

                if lookback.empty:
                    continue
                last_closed_row = lookback.iloc[-1]

                action, conf, method, use_sl = self.brain.get_consensus_prediction(
                    last_closed_row.to_dict(),
                    features_df=lookback,
                    btc_features=btc_look
                )

                # 3. Abrir posición al precio de APERTURA (Open) de la vela actual (i)
                if action is not None and conf > cfg.MIN_CONFIDENCE:
                    self._enter_trade(action, row, method, use_sl, entry_price=row['open'])

        # Cierre forzado de trade remanente al finalizar el marco temporal
        if self.active_trade:
            last_row = self.df.iloc[-1]
            self._close_trade(last_row, last_row['close'], 'TIMEFRAME_END', is_taker=True)

        self._summary()

    def _enter_trade(self, action, row, method, use_sl, entry_price=None):
        action_str = "LONG" if action == 1 else "SHORT"
        price = entry_price if entry_price else row['open']
        atr = row['ATR']

        sl, tp = self.rm.calculate_dynamic_stops(price, atr, action_str, row.get('ATR_pct'))
        size = self.rm.calculate_position_size(self.balance, price, sl if use_sl else None, symbol=self.symbol)

        if size > 0:
            use_limit = getattr(cfg, 'USE_LIMIT_ORDERS', True)
            entry_fee_rate = self.maker_fee if use_limit else self.taker_fee

            # Aplicar Spread y Slippage al precio real de llenado
            if action_str == "LONG":
                real_entry = price * (1 + (self.spread / 2) + self.slippage)
            else:
                real_entry = price * (1 - (self.spread / 2) - self.slippage)

            # Riesgo inicial en USDT para cálculo de R-Multiple
            initial_risk_usdt = abs(real_entry - sl) * size if use_sl and sl else (real_entry * size * 0.05)

            # Precio de liquidación estimado (90% del margen aislado a LEVERAGE)
            leverage = cfg.LEVERAGE
            if action_str == 'LONG':
                liq_price = real_entry * (1 - 0.9 / leverage)
            else:
                liq_price = real_entry * (1 + 0.9 / leverage)

            entry_ts_str = str(row['timestamp'])

            self.active_trade = {
                'entry_time': entry_ts_str,
                'action': action_str,
                'entry_price': real_entry,
                'raw_price': price,
                'size': size,
                'sl': sl,
                'initial_sl': sl,
                'tp': tp,
                'initial_tp': tp,
                'use_sl': use_sl,
                'method': method,
                'entry_fee_rate': entry_fee_rate,
                'initial_risk_usdt': max(initial_risk_usdt, 1e-4),
                'liq_price': liq_price,
                'mfe_price': real_entry,
                'mae_price': real_entry,
                'mfe_pct': 0.0,
                'mae_pct': 0.0,
                'is_breakeven': False,
                'is_trailing': False,
                'features': row.to_dict()
            }

    def _check_exit(self, row):
        t = self.active_trade
        action = t['action']
        high = float(row['high'])
        low = float(row['low'])
        entry = t['entry_price']

        # 1. Actualizar MAE y MFE intrabar
        if action == 'LONG':
            t['mfe_price'] = max(t['mfe_price'], high)
            t['mae_price'] = min(t['mae_price'], low)
            t['mfe_pct'] = max(t['mfe_pct'], (t['mfe_price'] - entry) / entry)
            t['mae_pct'] = max(t['mae_pct'], (entry - t['mae_price']) / entry)
        else:
            t['mfe_price'] = min(t['mfe_price'], low)
            t['mae_price'] = max(t['mae_price'], high)
            t['mfe_pct'] = max(t['mfe_pct'], (entry - t['mfe_price']) / entry)
            t['mae_pct'] = max(t['mae_pct'], (t['mae_price'] - entry) / entry)

        # 2. Evaluación de Liquidación (Mayor prioridad de seguridad)
        is_liquidated = False
        if action == 'LONG' and low <= t['liq_price']:
            is_liquidated = True
        elif action == 'SHORT' and high >= t['liq_price']:
            is_liquidated = True

        if is_liquidated:
            self._close_trade(row, t['liq_price'], 'LIQUIDATION', is_taker=True)
            return

        # 3. Evaluación de TP y SL usando High y Low
        hit_tp = False
        hit_sl = False

        if action == 'LONG':
            if high >= t['tp']:
                hit_tp = True
            if t['use_sl'] and t['sl'] is not None and low <= t['sl']:
                hit_sl = True
        else:
            if low <= t['tp']:
                hit_tp = True
            if t['use_sl'] and t['sl'] is not None and high >= t['sl']:
                hit_sl = True

        # 4. Política Conservadora de Impactos Simultáneos: Si la vela toca TP y SL simultáneamente -> Peor caso (SL)
        if hit_tp and hit_sl:
            reason = 'BREAKEVEN' if t['is_breakeven'] else ('TRAILING_STOP' if t['is_trailing'] else 'SL')
            self._close_trade(row, t['sl'], reason, is_taker=True)
            return
        elif hit_sl:
            reason = 'BREAKEVEN' if t['is_breakeven'] else ('TRAILING_STOP' if t['is_trailing'] else 'SL')
            self._close_trade(row, t['sl'], reason, is_taker=True)
            return
        elif hit_tp:
            # TP Límite se ejecuta con comisión Maker (0.020%)
            self._close_trade(row, t['tp'], 'TP', is_taker=False)
            return

        # 5. Simulación de Breakeven y Trailing Stop Intrabar (para velas posteriores)
        atr_val = row.get('ATR', entry * 0.01)

        # Breakeven check
        if not t['is_breakeven'] and not t['is_trailing']:
            be_sl = self.rm.calculate_breakeven_stop(t, high if action == 'LONG' else low)
            if be_sl is not None:
                t['sl'] = be_sl
                t['is_breakeven'] = True

        # Trailing Stop check
        trail_sl = self.rm.calculate_trailing_stop(t, high if action == 'LONG' else low, atr_val)
        if trail_sl is not None:
            t['sl'] = trail_sl
            t['is_trailing'] = True

    def _close_trade(self, row, raw_exit_price, exit_reason, is_taker=True):
        t = self.active_trade
        entry_price = t['entry_price']
        size = t['size']
        action = t['action']
        exit_ts_str = str(row['timestamp'])

        # Aplicar Fricción (Spread + Slippage) al precio real de salida
        if action == 'LONG':
            exit_price = raw_exit_price * (1 - (self.spread / 2) - self.slippage)
        else:
            exit_price = raw_exit_price * (1 + (self.spread / 2) + self.slippage)

        # Cálculo de PnL Bruto
        if action == 'LONG':
            gross_pnl = (exit_price - entry_price) * size
        else:
            gross_pnl = (entry_price - exit_price) * size

        # Comisiones (Entrada + Salida)
        exit_fee_rate = self.taker_fee if is_taker else self.maker_fee
        entry_notional = entry_price * size
        exit_notional = exit_price * size
        total_fees = (entry_notional * t['entry_fee_rate']) + (exit_notional * exit_fee_rate)

        # Slippage + Spread estimado en USDT
        estimated_friction = (entry_notional + exit_notional) * ((self.spread / 2) + self.slippage)

        if exit_reason == 'LIQUIDATION':
            # En liquidación se pierde el margen total asignado
            net_pnl = - (entry_notional / cfg.LEVERAGE)
        else:
            net_pnl = gross_pnl - total_fees

        # R-Multiple = PnL Neto / Riesgo Inicial USDT
        r_multiple = round(net_pnl / t['initial_risk_usdt'], 2)

        res = 'WIN' if net_pnl >= 0 else ('LIQUIDATED' if exit_reason == 'LIQUIDATION' else 'LOSS')

        # ── Nuevo Registro de Trade Estándar (15 campos) ───────────────────────
        trade_record = {
            'ENTRY': t['entry_time'],
            'EXIT': exit_ts_str,
            'SIDE': action,
            'ENTRY_PRICE': round(entry_price, 4),
            'EXIT_PRICE': round(exit_price, 4),
            'SL': round(t['initial_sl'], 4) if t['initial_sl'] else 0.0,
            'TP': round(t['initial_tp'], 4) if t['initial_tp'] else 0.0,
            'MFE': round(t['mfe_pct'] * 100, 2),
            'MAE': round(t['mae_pct'] * 100, 2),
            'FEES': round(total_fees, 4),
            'SLIPPAGE': round(estimated_friction, 4),
            'PNL': round(net_pnl, 4),
            'R_MULTIPLE': r_multiple,
            'EXIT_REASON': exit_reason,
            'METHOD': t['method'],
            # Alias legacy para compatibilidad
            'pnl': net_pnl,
            'res': res
        }

        self.balance += net_pnl
        self.history.append(trade_record)

        # Aprendizaje Walk-Forward dinámico
        self.brain.online_update(t['features'], res, t['use_sl'], res == 'LOSS')
        self.rm.register_result(res)

        self.active_trade = None

    def _summary(self):
        df_h = pd.DataFrame(self.history)
        if df_h.empty:
            print("⚠️ No se ejecutaron operaciones.")
            return

        total_pnl = df_h['PNL'].sum()
        total_trades = len(df_h)
        wins = df_h[df_h['PNL'] >= 0]['PNL']
        losses = df_h[df_h['PNL'] < 0]['PNL']
        wr = (len(wins) / total_trades) if total_trades > 0 else 0.0

        profit_factor = wins.sum() / abs(losses.sum()) if not losses.empty and losses.sum() != 0 else float('inf')

        # Equity y Max Drawdown
        df_h['equity'] = cfg.PAPER_BALANCE + df_h['PNL'].cumsum()
        peak = df_h['equity'].cummax()
        drawdown_abs = peak - df_h['equity']
        max_dd_pct = (drawdown_abs / peak).max()
        max_dd_abs = drawdown_abs.max()

        # R-Multiple y MAE/MFE promedios
        avg_r = df_h['R_MULTIPLE'].mean()
        avg_mfe = df_h['MFE'].mean()
        avg_mae = df_h['MAE'].mean()
        total_fees = df_h['FEES'].sum()

        # Sharpe / Sortino
        returns = df_h['PNL'] / (df_h['equity'].shift(1).fillna(cfg.PAPER_BALANCE))
        sharpe = (returns.mean() / returns.std() * np.sqrt(total_trades)) if returns.std() != 0 else 0.0
        neg_returns = returns[returns < 0]
        sortino = (returns.mean() / neg_returns.std() * np.sqrt(total_trades)) if not neg_returns.empty and neg_returns.std() != 0 else float('inf')

        # Desglose por motivo de salida
        exit_counts = df_h['EXIT_REASON'].value_counts().to_dict()
        exit_str = ", ".join([f"{k}: {v}" for k, v in exit_counts.items()])

        summary = (
            f"\n{'='*55}\n"
            f"📊 RESUMEN BACKTEST DE CONFIANZA: {self.symbol}\n"
            f"Trades totales:     {total_trades}\n"
            f"Win Rate:           {wr:.1%}\n"
            f"PnL Neto Total:     {total_pnl:.2f} USDT\n"
            f"Balance Final:      {self.balance:.2f} USDT\n"
            f"{'-' * 35}\n"
            f"Profit Factor:      {profit_factor:.2f}\n"
            f"Max Drawdown:       {max_dd_pct:.2%} ({max_dd_abs:.2f} USDT)\n"
            f"Promedio R-Multiple:{avg_r:+.2f}R\n"
            f"Promedio MFE:       +{avg_mfe:.2f}%\n"
            f"Promedio MAE:       -{avg_mae:.2f}%\n"
            f"Comisiones Totales: {total_fees:.2f} USDT\n"
            f"Sharpe Ratio:       {sharpe:.2f}\n"
            f"Sortino Ratio:      {sortino:.2f}\n"
            f"Motivos de Salida:  {exit_str}\n"
            f"{'='*55}"
        )
        print(summary)
        cfg.trade_logger.info(summary)