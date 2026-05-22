import os
import sqlite3
import pandas as pd
import logging
from datetime import datetime
from threading import Lock
import config

logger = logging.getLogger(__name__)


class TradeTracker:
    # Columnas del CSV
    COLUMNAS = [
        'timestamp', 'pair', 'action', 'entry_price', 'close_price',
        'size', 'result', 'pnl_usdt',
        'RSI', 'ATR', 'ATR_pct', 'EMA_diff', 'EMA_diff_norm',
        'MACD', 'MACD_hist', 'BB_width', 'BB_position',
        'volume_ratio', 'trend_signal', 'above_ema200', 'momentum_signal',
        'VWAP_dist', 'delta_cum5', 'delta_div',
        'price_slope', 'range_pct', 'near_struct_high', 'near_struct_low',
        'sl_was_used', 'sl_was_hit',
    ]

    # Features para almacenar con cada trade
    FEATURE_COLS = [
        'RSI', 'ATR', 'ATR_pct', 'EMA_diff', 'EMA_diff_norm',
        'MACD', 'MACD_hist', 'BB_width', 'BB_position',
        'volume_ratio', 'trend_signal', 'above_ema200', 'momentum_signal',
        'VWAP_dist', 'delta_cum5', 'delta_div',
        'price_slope', 'range_pct', 'near_struct_high', 'near_struct_low',
    ]

    def __init__(self, symbol="BTCUSDT"):
        self.symbol        = symbol
        self.db_path       = config.DB_PATH
        self.active_trades = []
        self._trades_lock  = Lock()  # Thread-safe access to active_trades
        self._on_close_cb  = None

        self.total_trades = 0
        self.wins         = 0
        self.losses       = 0
        self.win_rate     = 0.0
        self.total_pnl    = 0.0

        self._ensure_storage()
        self._load_historical_stats()

    def set_on_close_callback(self, fn):
        self._on_close_cb = fn

    def _ensure_storage(self):
        """Crea la tabla de trades en SQLite si no existe."""
        os.makedirs('storage', exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        columns_sql = []
        for col in self.COLUMNAS:
            col_type = "REAL" if col in ['size', 'entry_price', 'close_price', 'pnl_usdt'] or col in self.FEATURE_COLS else "TEXT"
            columns_sql.append(f"{col} {col_type}")
        query = f"CREATE TABLE IF NOT EXISTS trades ({', '.join(columns_sql)})"
        cursor.execute(query)
        conn.commit()
        conn.close()

    def _load_historical_stats(self):
        try:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT COUNT(*), SUM(pnl_usdt), SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) FROM trades WHERE pair = ?"
            res = conn.execute(query, (self.symbol,)).fetchone()
            if res and res[0] > 0:
                self.total_trades = res[0]
                self.total_pnl    = res[1] or 0.0
                self.wins         = res[2] or 0
                self.win_rate     = (self.wins / self.total_trades) * 100
                logger.info(f"Loaded {self.total_trades} historical trades for {self.symbol}")
            conn.close()
        except Exception as e:
            logger.error(f"Error loading historical stats for {self.symbol}: {e}")

    def register_trade(self, action, entry_price, size, sl, tp, features, use_sl):
        trade = {
            'timestamp':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action':      action,
            'entry_price': entry_price,
            'size':        size,
            'sl':          sl if use_sl else None,
            'tp':          tp,
            'use_sl':      use_sl,
            '_features':   features,
            **{col: round(float(features.get(col, 0)), 6) for col in self.FEATURE_COLS},
        }
        with self._trades_lock:
            self.active_trades.append(trade)
        sl_str = f"SL={sl:.2f}" if use_sl else "SIN SL"
        print(f"📝 Orden {action} {self.symbol} @ {entry_price:.2f} | TP={tp:.2f} | {sl_str}")

    def update_market_price(self, current_price):
        with self._trades_lock:
            trades_copy = list(self.active_trades)

        for trade in trades_copy:
            close_price = result = sl_was_hit = None

            if trade['action'] == 'LONG':
                if current_price >= trade['tp']:
                    close_price, result, sl_was_hit = trade['tp'], 'WIN', False
                elif trade['use_sl'] and current_price <= trade['sl']:
                    close_price, result, sl_was_hit = trade['sl'], 'LOSS', True
            else:
                if current_price <= trade['tp']:
                    close_price, result, sl_was_hit = trade['tp'], 'WIN', False
                elif trade['use_sl'] and current_price >= trade['sl']:
                    close_price, result, sl_was_hit = trade['sl'], 'LOSS', True

            if result:
                pnl = (
                    (close_price - trade['entry_price']) * trade['size']
                    if trade['action'] == 'LONG'
                    else (trade['entry_price'] - close_price) * trade['size']
                )
                self._save_to_db(trade, close_price, result, pnl, sl_was_hit)
                self._update_live_stats(result, pnl)

                if self._on_close_cb:
                    margin_to_release = (trade['size'] * trade['entry_price']) / config.LEVERAGE
                    self._on_close_cb(
                        trade['_features'], result,
                        sl_was_used=trade['use_sl'],
                        sl_was_hit=sl_was_hit,
                        pnl=pnl,
                        margin_released=margin_to_release
                    )

                with self._trades_lock:
                    self.active_trades.remove(trade)
                emoji   = "🏆" if result == 'WIN' else "💀"
                sl_info = "(SL tocado)" if sl_was_hit else "(TP alcanzado)"
                print(f"{emoji} {self.symbol} Trade cerrado: {result} {sl_info} | PnL: {pnl:+.4f} USDT")

    def _save_to_db(self, trade, close_price, result, pnl, sl_was_hit):
        row = {
            'timestamp':   trade['timestamp'],
            'pair':        self.symbol,
            'action':      trade['action'],
            'entry_price': trade['entry_price'],
            'close_price': close_price,
            'size':        trade['size'],
            'result':      result,
            'pnl_usdt':    round(pnl, 4),
            'sl_was_used': int(trade['use_sl']),
            'sl_was_hit':  int(sl_was_hit) if sl_was_hit is not None else 0,
            **{col: trade.get(col, 0) for col in self.FEATURE_COLS},
        }
        
        conn = sqlite3.connect(self.db_path)
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        query = f"INSERT INTO trades ({cols}) VALUES ({placeholders})"
        
        try:
            conn.execute(query, list(row.values()))
            conn.commit()
        finally:
            conn.close()

    def _update_live_stats(self, result, pnl):
        self.total_trades += 1
        if result == 'WIN': self.wins   += 1
        else:               self.losses += 1
        self.total_pnl  += pnl
        self.win_rate    = (self.wins / self.total_trades) * 100

    def get_dashboard_stats(self):
        return self.total_trades, self.wins, self.losses, self.win_rate, self.total_pnl