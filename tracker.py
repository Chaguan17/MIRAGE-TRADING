import os
import pandas as pd
from datetime import datetime

class TradeTracker:
    def __init__(self, filepath='storage/trade_history.csv'):
        self.filepath = filepath
        self.active_trades = []
        
        # Atributos de caché para el Dashboard (Evita leer el CSV cada segundo)
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.win_rate = 0.0
        self.total_pnl = 0.0
        
        self._ensure_storage()
        self._load_historical_stats() # Recuperar la memoria al iniciar

    def _ensure_storage(self):
        """Garantiza que la carpeta y el archivo existan."""
        if not os.path.exists('storage'):
            os.makedirs('storage')
        if not os.path.exists(self.filepath):
            df = pd.DataFrame(columns=[
                'timestamp', 'action', 'entry_price', 'close_price', 
                'size', 'result', 'pnl_usdt', 'RSI', 'ATR', 'EMA_diff'
            ])
            df.to_csv(self.filepath, index=False)

    def _load_historical_stats(self):
        """
        MEMORIA HISTÓRICA: Lee el CSV al arrancar para que el Dashboard 
        muestre las 9 (o más) operaciones previas correctamente.
        """
        try:
            df = pd.read_csv(self.filepath)
            if not df.empty:
                self.total_trades = len(df)
                self.wins = len(df[df['result'] == 'WIN'])
                self.losses = len(df[df['result'] == 'LOSS'])
                self.total_pnl = df['pnl_usdt'].sum()
                self.win_rate = (self.wins / self.total_trades) * 100
                print(f"🧠 MEMORIA: Recuperadas {self.total_trades} experiencias pasadas.")
        except Exception as e:
            print(f"⚠️ Error al recuperar memoria: {e}")

    def register_trade(self, action, entry_price, size, sl, tp, features):
        """Registra un trade en la memoria RAM activa."""
        trade = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': action,
            'entry_price': entry_price,
            'size': size,
            'sl': sl,
            'tp': tp,
            'RSI': round(features['RSI'], 2),
            'ATR': round(features['ATR'], 2),
            'EMA_diff': round(features['EMA_20'] - features['EMA_50'], 2)
        }
        self.active_trades.append(trade)
        print(f"📝 Orden {action} en {entry_price} registrada en memoria activa.")

    def update_market_price(self, current_price):
        """Vigila la salida de trades y sincroniza con el CSV inmediatamente."""
        for trade in self.active_trades[:]: # Iterar sobre copia
            close_price = None
            result = None
            
            # Lógica de salida
            if trade['action'] == "LONG":
                if current_price >= trade['tp']: close_price, result = trade['tp'], 'WIN'
                elif current_price <= trade['sl']: close_price, result = trade['sl'], 'LOSS'
            elif trade['action'] == "SHORT":
                if current_price <= trade['tp']: close_price, result = trade['tp'], 'WIN'
                elif current_price >= trade['sl']: close_price, result = trade['sl'], 'LOSS'

            if result:
                pnl = (close_price - trade['entry_price']) * trade['size'] if trade['action'] == "LONG" else (trade['entry_price'] - close_price) * trade['size']
                
                # PERSISTENCIA INMEDIATA: Antes de borrar de RAM, guardar en DISCO
                self._save_to_csv(trade, close_price, result, pnl)
                
                # Actualizar estadísticas en tiempo real
                self._update_live_stats(result, pnl)
                
                self.active_trades.remove(trade)
                print(f"✅ Trade cerrado: {result} | PnL: {pnl:.4f}")

    def _save_to_csv(self, trade, close_price, result, pnl):
        """Escribe la experiencia en el CSV para el Machine Learning."""
        new_row = pd.DataFrame([{
            'timestamp': trade['timestamp'],
            'action': trade['action'],
            'entry_price': trade['entry_price'],
            'close_price': close_price,
            'size': trade['size'],
            'result': result,
            'pnl_usdt': round(pnl, 4),
            'RSI': trade['RSI'],
            'ATR': trade['ATR'],
            'EMA_diff': trade['EMA_diff']
        }])
        new_row.to_csv(self.filepath, mode='a', header=False, index=False)

    def _update_live_stats(self, result, pnl):
        """Actualiza los contadores internos sin necesidad de re-leer el CSV."""
        self.total_trades += 1
        if result == 'WIN': self.wins += 1
        else: self.losses += 1
        self.total_pnl += pnl
        self.win_rate = (self.wins / self.total_trades) * 100

    def get_dashboard_stats(self):
        """Devuelve las estadísticas procesadas para el Dashboard."""
        return self.total_trades, self.wins, self.losses, self.win_rate, self.total_pnl