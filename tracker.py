# tracker.py
import os
import pandas as pd
from datetime import datetime

class TradeTracker:
    def __init__(self, filepath='storage/trade_history.csv'):
        self.filepath = filepath
        self.active_trades = []
        
        if not os.path.exists('storage'):
            os.makedirs('storage')
        if not os.path.exists(self.filepath):
            # 1. Añadimos las columnas de los "Sentidos" (Features) al CSV
            df = pd.DataFrame(columns=[
                'timestamp', 'action', 'entry_price', 'close_price', 
                'size', 'result', 'pnl_usdt', 'RSI', 'ATR', 'EMA_diff'
            ])
            df.to_csv(self.filepath, index=False)

    def register_trade(self, action, entry_price, size, sl, tp, features):
        """Ahora recibe 'features' para tener Memoria Sensorial"""
        trade = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': action,
            'entry_price': entry_price,
            'size': size,
            'sl': sl,
            'tp': tp,
            # 2. Guardamos la foto del mercado en este instante
            'RSI': round(features['RSI'], 2),
            'ATR': round(features['ATR'], 2),
            'EMA_diff': round(features['EMA_20'] - features['EMA_50'], 2)
        }
        self.active_trades.append(trade)

    def update_market_price(self, current_price):
        """Vigila si el precio actual toca algún SL o TP de los trades abiertos"""
        closed_trades = []
        
        for trade in self.active_trades:
            close_price = None
            result = None
            
            if trade['action'] == "LONG":
                if current_price >= trade['tp']:
                    close_price, result = trade['tp'], 'WIN'
                elif current_price <= trade['sl']:
                    close_price, result = trade['sl'], 'LOSS'
                    
            elif trade['action'] == "SHORT":
                if current_price <= trade['tp']:
                    close_price, result = trade['tp'], 'WIN'
                elif current_price >= trade['sl']:
                    close_price, result = trade['sl'], 'LOSS'

            # Si el trade se cerró, calculamos la ganancia/pérdida (PnL)
            if result:
                if trade['action'] == "LONG":
                    pnl = (close_price - trade['entry_price']) * trade['size']
                else: # SHORT
                    pnl = (trade['entry_price'] - close_price) * trade['size']
                
                self._save_to_csv(trade, close_price, result, pnl)
                closed_trades.append(trade)

        # Limpiamos los trades que ya se cerraron de la memoria activa
        for ct in closed_trades:
            self.active_trades.remove(ct)

    def _save_to_csv(self, trade, close_price, result, pnl):
        """Guardamos la fila completa con los indicadores"""
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
    def get_dashboard_stats(self):
        """Lee el CSV y calcula el resumen de rendimiento"""
        try:
            df = pd.read_csv(self.filepath)
            if df.empty:
                return 0, 0, 0, 0.0, 0.0
            
            total_trades = len(df)
            wins = len(df[df['result'] == 'WIN'])
            losses = len(df[df['result'] == 'LOSS'])
            total_pnl = df['pnl_usdt'].sum()
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            
            return total_trades, wins, losses, win_rate, total_pnl
        except:
            return 0, 0, 0, 0.0, 0.0