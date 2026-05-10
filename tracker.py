import os
import pandas as pd
from datetime import datetime


class TradeTracker:
    COLUMNAS = [
        'timestamp', 'action', 'entry_price', 'close_price',
        'size', 'result', 'pnl_usdt', 'RSI', 'ATR', 'EMA_diff'
    ]

    def __init__(self, filepath='storage/trade_history.csv'):
        self.filepath     = filepath
        self.active_trades = []
        self._on_close_cb  = None  # callback → brain.online_update

        self.total_trades = 0
        self.wins         = 0
        self.losses       = 0
        self.win_rate     = 0.0
        self.total_pnl    = 0.0

        self._ensure_storage()
        self._load_historical_stats()

    def set_on_close_callback(self, fn):
        """
        Registra la función que se llamará cada vez que un trade se cierra.
        fn(features_dict, result_label)  → brain.online_update
        """
        self._on_close_cb = fn

    # ──────────────────────────────────────────────────────────────────────────

    def _ensure_storage(self):
        if not os.path.exists('storage'):
            os.makedirs('storage')
        if not os.path.exists(self.filepath):
            pd.DataFrame(columns=self.COLUMNAS).to_csv(self.filepath, index=False)
        else:
            df_check = pd.read_csv(self.filepath, nrows=0)
            if list(df_check.columns) != self.COLUMNAS:
                print("⚠️ Re-estructurando encabezado del CSV...")
                df_fix = pd.read_csv(self.filepath, names=self.COLUMNAS, skiprows=1)
                df_fix.to_csv(self.filepath, index=False)

    def _load_historical_stats(self):
        try:
            df = pd.read_csv(self.filepath)
            if not df.empty:
                self.total_trades = len(df)
                self.wins         = len(df[df['result'] == 'WIN'])
                self.losses       = len(df[df['result'] == 'LOSS'])
                self.total_pnl    = df['pnl_usdt'].sum()
                self.win_rate     = (self.wins / self.total_trades) * 100
                print(f"🧠 MEMORIA: Recuperadas {self.total_trades} experiencias pasadas.")
        except Exception as e:
            print(f"⚠️ Error al recuperar memoria: {e}")

    # ──────────────────────────────────────────────────────────────────────────

    def register_trade(self, action, entry_price, size, sl, tp, features):
        trade = {
            'timestamp':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action':      action,
            'entry_price': entry_price,
            'size':        size,
            'sl':          sl,
            'tp':          tp,
            # Guardamos features para poder pasarlas al cerebro al cerrar
            'RSI':      round(features.get('RSI', 0), 2),
            'ATR':      round(features.get('ATR', 0), 2),
            'EMA_diff': round(features.get('EMA_20', 0) - features.get('EMA_50', 0), 2),
            '_features': features,   # referencia completa (no se guarda en CSV)
        }
        self.active_trades.append(trade)
        print(f"📝 Orden {action} @ {entry_price:.2f} registrada.")

    def update_market_price(self, current_price):
        for trade in self.active_trades[:]:
            close_price = result = None

            if trade['action'] == "LONG":
                if current_price >= trade['tp']:  close_price, result = trade['tp'],  'WIN'
                elif current_price <= trade['sl']: close_price, result = trade['sl'], 'LOSS'
            else:  # SHORT
                if current_price <= trade['tp']:  close_price, result = trade['tp'],  'WIN'
                elif current_price >= trade['sl']: close_price, result = trade['sl'], 'LOSS'

            if result:
                pnl = ((close_price - trade['entry_price']) * trade['size']
                       if trade['action'] == "LONG"
                       else (trade['entry_price'] - close_price) * trade['size'])

                self._save_to_csv(trade, close_price, result, pnl)
                self._update_live_stats(result, pnl)

                # ── FEEDBACK INMEDIATO AL CEREBRO ──────────────────────────
                if self._on_close_cb:
                    self._on_close_cb(trade['_features'], result)

                self.active_trades.remove(trade)
                emoji = "🏆" if result == 'WIN' else "💀"
                print(f"{emoji} Trade cerrado: {result} | PnL: {pnl:+.4f} USDT")

    def _save_to_csv(self, trade, close_price, result, pnl):
        new_row = pd.DataFrame([{
            'timestamp':   trade['timestamp'],
            'action':      trade['action'],
            'entry_price': trade['entry_price'],
            'close_price': close_price,
            'size':        trade['size'],
            'result':      result,
            'pnl_usdt':    round(pnl, 4),
            'RSI':         trade['RSI'],
            'ATR':         trade['ATR'],
            'EMA_diff':    trade['EMA_diff'],
        }])
        new_row.to_csv(self.filepath, mode='a', header=False, index=False)

    def _update_live_stats(self, result, pnl):
        self.total_trades += 1
        if result == 'WIN': self.wins   += 1
        else:               self.losses += 1
        self.total_pnl  += pnl
        self.win_rate    = (self.wins / self.total_trades) * 100

    def get_dashboard_stats(self):
        return self.total_trades, self.wins, self.losses, self.win_rate, self.total_pnl
