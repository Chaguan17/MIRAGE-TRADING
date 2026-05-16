# 💻 EJEMPLOS DE CÓDIGO POR SPRINT

## Índice
- [Sprint 3: Backtesting](#sprint-3-backtesting)
- [Sprint 4: Producción](#sprint-4-producción)
- [Sprint 5: Multi-Par](#sprint-5-multi-par)

---

## SPRINT 3: BACKTESTING

### backtester.py

```python
"""
Backtesting engine para validar estrategias.
Simula operaciones contra datos históricos.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path

class Backtester:
    def __init__(self, 
                 symbol="BTCUSDT",
                 start_date="2020-01-01",
                 end_date="2024-12-31",
                 initial_balance=1000.0,
                 leverage=2.0):
        """
        Args:
            symbol: Trading pair (BTCUSDT, ETHUSDT, etc.)
            start_date: Inicio de backtest (YYYY-MM-DD)
            end_date: Fin de backtest
            initial_balance: Capital inicial en USDT
            leverage: Multiplicador de tamaño de posición
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_balance = initial_balance
        self.leverage = leverage
        
        # Estado
        self.balance = initial_balance
        self.equity_curve = [initial_balance]  # Para gráficas
        self.trades = []
        self.position = None  # Posición actual (dict)
        self.data = None  # DataFrame OHLCV
        
    def fetch_data(self):
        """
        Descargar datos históricos de Binance.
        En producción, usar CCXT o API REST.
        
        Aquí usamos CSV simulado para ejemplo.
        """
        # TODO: Reemplazar con CCXT en producción
        # import ccxt
        # exchange = ccxt.binance()
        # self.data = exchange.fetch_ohlcv(self.symbol, '1d', since=..., limit=...)
        
        # Para ejemplo, generar datos sintéticos
        print(f"📥 Descargando {self.symbol} desde {self.start_date} a {self.end_date}...")
        
        # STUB: En real, fetch real OHLCV
        date_range = pd.date_range(self.start_date, self.end_date, freq='1D')
        np.random.seed(42)
        
        prices = np.cumsum(np.random.randn(len(date_range)) * 0.02) + 100
        
        self.data = pd.DataFrame({
            'timestamp': date_range,
            'open': prices + np.random.randn(len(prices)) * 0.5,
            'high': prices + abs(np.random.randn(len(prices)) * 0.5),
            'low': prices - abs(np.random.randn(len(prices)) * 0.5),
            'close': prices,
            'volume': np.random.randint(100, 1000, len(prices))
        })
        
        return self.data
    
    def calculate_features(self):
        """Calcular RSI, EMA, ATR para cada candle."""
        df = self.data.copy()
        
        # RSI (14 periodos)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMA (9 y 21 periodos)
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        
        # ATR (14 periodos, volatilidad)
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift()),
                abs(df['low'] - df['close'].shift())
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        self.data = df
        return df
    
    def generate_signals(self):
        """
        Generar señales BUY/SELL basado en estrategias.
        Aquí implementamos "Trend Follower" como ejemplo.
        """
        df = self.data.copy()
        df['signal'] = 0  # 0=HOLD, 1=BUY, -1=SELL
        
        # Trend Follower: EMA 9 > EMA 21 = BUY, si no SELL
        for i in range(21, len(df)):
            if df['ema_9'].iloc[i] > df['ema_21'].iloc[i]:
                df.loc[i, 'signal'] = 1  # BUY
            else:
                df.loc[i, 'signal'] = -1  # SELL
        
        self.data = df
        return df
    
    def run(self):
        """Ejecutar simulación de trades."""
        print(f"\n🚀 Iniciando backtest...")
        print(f"   Balance inicial: ${self.balance:.2f}")
        print(f"   Leverage: {self.leverage}x")
        
        self.fetch_data()
        self.calculate_features()
        self.generate_signals()
        
        # Iterar sobre cada candle
        for idx, row in self.data.iterrows():
            signal = row['signal']
            close_price = row['close']
            
            # Si hay posición abierta y signal dice cerrar
            if self.position and signal != self.position['side']:
                self._close_position(idx, close_price)
            
            # Si no hay posición y hay señal de entrada
            if not self.position and signal != 0:
                self._open_position(idx, close_price, signal)
            
            # Actualizar equity curve
            equity = self.balance
            if self.position:
                # PnL no realizado
                pnl = (close_price - self.position['entry']) * self.position['size']
                equity += pnl
            
            self.equity_curve.append(equity)
        
        # Cerrar posición abierta al final
        if self.position:
            last_price = self.data['close'].iloc[-1]
            self._close_position(len(self.data) - 1, last_price)
        
        return self.calculate_metrics()
    
    def _open_position(self, idx, price, side):
        """Abrir nueva posición."""
        # Tamaño = 10% del balance por posición (con leverage)
        size = (self.balance * 0.1 * self.leverage) / price
        
        self.position = {
            'idx': idx,
            'entry_time': self.data['timestamp'].iloc[idx],
            'entry': price,
            'side': side,  # 1=LONG, -1=SHORT
            'size': size,
            'stop_loss': price * (0.98 if side == 1 else 1.02),  # 2% SL
        }
        
        action = "LONG" if side == 1 else "SHORT"
        print(f"📈 ENTRADA {action} en ${price:.2f} (trade #{len(self.trades)+1})")
    
    def _close_position(self, idx, price):
        """Cerrar posición abierta."""
        pnl = (price - self.position['entry']) * self.position['size']
        if self.position['side'] == -1:  # SHORT
            pnl = -pnl
        
        self.balance += pnl
        
        trade = {
            'entry_time': self.position['entry_time'],
            'entry': self.position['entry'],
            'exit_time': self.data['timestamp'].iloc[idx],
            'exit': price,
            'side': 'LONG' if self.position['side'] == 1 else 'SHORT',
            'pnl': pnl,
            'size': self.position['size']
        }
        self.trades.append(trade)
        
        action = "CIERRE" if pnl > 0 else "PÉRDIDA"
        print(f"📊 {action}: ${pnl:.2f} | Balance: ${self.balance:.2f}")
        
        self.position = None
    
    def calculate_metrics(self):
        """Calcular métricas de backtest."""
        trades = self.trades
        
        if not trades:
            print("❌ No hay trades en el backtest")
            return {}
        
        # Retornos
        returns = [t['pnl'] for t in trades]
        pnl_total = sum(returns)
        
        # Win Rate
        wins = len([r for r in returns if r > 0])
        loss = len([r for r in returns if r <= 0])
        win_rate = wins / len(returns) * 100 if returns else 0
        
        # Profit Factor
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Retorno en porcentaje
        return_pct = (pnl_total / self.initial_balance) * 100
        
        # Sharpe Ratio
        daily_returns = np.diff(self.equity_curve) / np.array(self.equity_curve)[:-1]
        sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
        
        # Máximo Drawdown
        cumulative = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        metrics = {
            'symbol': self.symbol,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_pnl': pnl_total,
            'return_pct': return_pct,
            'num_trades': len(trades),
            'win_rate': win_rate,
            'wins': wins,
            'losses': loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'avg_win': sum(r for r in returns if r > 0) / wins if wins > 0 else 0,
            'avg_loss': sum(r for r in returns if r < 0) / loss if loss > 0 else 0,
        }
        
        return metrics
    
    def print_summary(self, metrics):
        """Imprimir resumen de resultados."""
        print("\n" + "="*60)
        print("📊 RESUMEN DE BACKTEST")
        print("="*60)
        print(f"Símbolo:          {metrics['symbol']}")
        print(f"Período:          {metrics['start_date']} a {metrics['end_date']}")
        print(f"Balance inicial:  ${metrics['initial_balance']:.2f}")
        print(f"Balance final:    ${metrics['final_balance']:.2f}")
        print(f"PnL Total:        ${metrics['total_pnl']:.2f} ({metrics['return_pct']:.2f}%)")
        print(f"\nOperaciones:      {metrics['num_trades']}")
        print(f"Ganancias:        {metrics['wins']}")
        print(f"Pérdidas:         {metrics['losses']}")
        print(f"Win Rate:         {metrics['win_rate']:.1f}%")
        print(f"\nProfit Factor:    {metrics['profit_factor']:.2f}x")
        print(f"Sharpe Ratio:     {metrics['sharpe_ratio']:.2f}")
        print(f"Max Drawdown:     {metrics['max_drawdown']:.2%}")
        print(f"Avg Win:          ${metrics['avg_win']:.2f}")
        print(f"Avg Loss:         ${metrics['avg_loss']:.2f}")
        print("="*60)
    
    def save_results(self, filename="backtest_results.json"):
        """Guardar resultados en JSON."""
        metrics = self.calculate_metrics()
        
        results = {
            'metrics': metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Resultados guardados en {filename}")
        return results


# EJEMPLO DE USO
if __name__ == "__main__":
    backtest = Backtester(
        symbol="BTCUSDT",
        start_date="2022-01-01",
        end_date="2024-12-31",
        initial_balance=1000.0,
        leverage=2.0
    )
    
    metrics = backtest.run()
    backtest.print_summary(metrics)
    backtest.save_results()
```

---

## SPRINT 4: PRODUCCIÓN

### database.py

```python
"""
Sistema de persistencia con SQLite.
Reemplaza CSV con BD relacional.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple

class TradeDatabase:
    def __init__(self, db_path="storage/trades.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Retornar filas como dicts
        self.create_tables()
    
    def create_tables(self):
        """Crear tablas si no existen."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pair TEXT NOT NULL,
                action TEXT NOT NULL,  -- 'LONG' o 'SHORT'
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                pnl_usdt REAL NOT NULL,
                size REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crear índices para queries rápidas
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_pair ON trades(pair)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_action ON trades(action)")
        
        self.conn.commit()
        print("✅ Tablas de BD creadas")
    
    def add_trade(self, timestamp: str, pair: str, action: str, 
                 entry_price: float, exit_price: float, pnl_usdt: float, 
                 size: float) -> int:
        """
        Agregar una operación a la BD.
        
        Returns:
            ID del trade insertado
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO trades 
            (timestamp, pair, action, entry_price, exit_price, pnl_usdt, size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, pair, action, entry_price, exit_price, pnl_usdt, size))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_last_trades(self, limit: int = 100, pair: str = None) -> List[Dict]:
        """Obtener últimos N trades."""
        if pair:
            query = "SELECT * FROM trades WHERE pair = ? ORDER BY timestamp DESC LIMIT ?"
            result = self.conn.execute(query, (pair, limit)).fetchall()
        else:
            query = "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?"
            result = self.conn.execute(query, (limit,)).fetchall()
        
        return [dict(row) for row in result]
    
    def get_trades_for_pair(self, pair: str) -> List[Dict]:
        """Obtener todos los trades de un par específico."""
        query = "SELECT * FROM trades WHERE pair = ? ORDER BY timestamp ASC"
        result = self.conn.execute(query, (pair,)).fetchall()
        return [dict(row) for row in result]
    
    def calculate_stats(self, pair: str = None) -> Dict:
        """Calcular estadísticas de trades."""
        if pair:
            trades = self.get_trades_for_pair(pair)
        else:
            query = "SELECT * FROM trades"
            rows = self.conn.execute(query).fetchall()
            trades = [dict(row) for row in rows]
        
        if not trades:
            return {'total_trades': 0}
        
        pnls = [t['pnl_usdt'] for t in trades]
        
        return {
            'total_trades': len(trades),
            'total_pnl': sum(pnls),
            'wins': len([p for p in pnls if p > 0]),
            'losses': len([p for p in pnls if p <= 0]),
            'win_rate': len([p for p in pnls if p > 0]) / len(pnls) * 100,
            'avg_win': sum([p for p in pnls if p > 0]) / len([p for p in pnls if p > 0]),
            'avg_loss': sum([p for p in pnls if p < 0]) / len([p for p in pnls if p < 0]) if any(p < 0 for p in pnls) else 0,
        }
    
    def close(self):
        """Cerrar conexión a BD."""
        self.conn.close()


# EJEMPLO
if __name__ == "__main__":
    db = TradeDatabase()
    
    # Agregar trade
    db.add_trade(
        timestamp="2024-01-15 10:30:00",
        pair="BTCUSDT",
        action="LONG",
        entry_price=42100.0,
        exit_price=42350.0,
        pnl_usdt=250.0,
        size=0.005
    )
    
    # Obtener últimos trades
    trades = db.get_last_trades(10)
    print(f"Últimos 10 trades: {trades}")
    
    # Calcular stats
    stats = db.calculate_stats()
    print(f"Estadísticas: {stats}")
    
    db.close()
```

### risk_limits.py (Leverage & Stop Loss)

```python
"""
Sistema de límites de riesgo para producción.
"""

class RiskLimiter:
    # Límites hard
    MAX_LEVERAGE = 3.0
    DEFAULT_LEVERAGE = 2.0
    MAX_RISK_PER_TRADE = 0.02  # 2%
    MAX_TOTAL_RISK = 0.05  # 5%
    MIN_STOP_LOSS_DISTANCE = 0.01  # 1%
    
    def __init__(self, balance: float):
        self.balance = balance
        self.positions = []
    
    def validate_leverage(self, requested_leverage: float) -> float:
        """
        Validar y limitar leverage.
        
        Returns:
            Leverage permitido (capped si es necesario)
        """
        if requested_leverage > self.MAX_LEVERAGE:
            print(f"⚠️ Leverage {requested_leverage} excede máximo {self.MAX_LEVERAGE}")
            return self.MAX_LEVERAGE
        return requested_leverage
    
    def validate_stop_loss(self, entry: float, stop_loss: float, side: str) -> bool:
        """
        Validar que el stop-loss esté lo suficientemente lejos.
        
        Args:
            entry: Precio de entrada
            stop_loss: Precio de stop-loss
            side: 'LONG' o 'SHORT'
        
        Returns:
            True si es válido, False si no
        """
        if side == 'LONG':
            distance = (entry - stop_loss) / entry
            if distance < self.MIN_STOP_LOSS_DISTANCE:
                print(f"❌ Stop-loss muy cercano: {distance:.2%} < {self.MIN_STOP_LOSS_DISTANCE:.2%}")
                return False
        else:  # SHORT
            distance = (stop_loss - entry) / entry
            if distance < self.MIN_STOP_LOSS_DISTANCE:
                print(f"❌ Stop-loss muy cercano: {distance:.2%} < {self.MIN_STOP_LOSS_DISTANCE:.2%}")
                return False
        
        return True
    
    def validate_position_size(self, position_size: float) -> bool:
        """
        Validar que la posición no exceda límites de riesgo.
        """
        total_exposure = sum(p['size'] for p in self.positions)
        
        if total_exposure + position_size > self.balance * self.MAX_TOTAL_RISK:
            print(f"❌ Exposición total excede límite: {total_exposure + position_size} > {self.balance * self.MAX_TOTAL_RISK}")
            return False
        
        return True
    
    def validate_trade(self, pair: str, side: str, entry: float, 
                      stop_loss: float, position_size: float) -> Dict[str, bool]:
        """
        Validar todo un trade.
        
        Returns:
            Dict con validaciones
        """
        return {
            'stop_loss_valid': self.validate_stop_loss(entry, stop_loss, side),
            'position_size_valid': self.validate_position_size(position_size),
            'is_valid': (
                self.validate_stop_loss(entry, stop_loss, side) and
                self.validate_position_size(position_size)
            )
        }


# EJEMPLO
if __name__ == "__main__":
    limiter = RiskLimiter(balance=1000.0)
    
    # Test 1: Leverage excesivo
    safe_leverage = limiter.validate_leverage(5.0)
    print(f"Leverage solicitado: 5.0 → Permitido: {safe_leverage}")
    # Output: 3.0
    
    # Test 2: Stop-loss inválido (muy cercano)
    is_valid = limiter.validate_stop_loss(entry=42100.0, stop_loss=42050.0, side='LONG')
    print(f"SL válido: {is_valid}")
    # Output: False (distancia < 1%)
    
    # Test 3: Stop-loss válido (2% de distancia)
    is_valid = limiter.validate_stop_loss(entry=42100.0, stop_loss=41258.0, side='LONG')
    print(f"SL válido: {is_valid}")
    # Output: True (distancia > 1%)
```

---

## SPRINT 5: MULTI-PAR

### multi_pair_manager.py

```python
"""
Gestor de múltiples pares simultáneamente.
"""

from typing import List, Dict
from dataclasses import dataclass

@dataclass
class Position:
    pair: str
    side: str  # 'LONG' o 'SHORT'
    entry_price: float
    stop_loss: float
    take_profit: float
    size: float
    opened_at: str

class MultiPairManager:
    def __init__(self, pairs: List[str], risk_limiter):
        self.pairs = pairs  # ['BTCUSDT', 'ETHUSDT', ...]
        self.positions = {}  # {pair: Position}
        self.risk_limiter = risk_limiter
    
    def update_pair(self, pair: str, signal: int, price: float):
        """
        Procesar señal para un par.
        
        Args:
            pair: Trading pair
            signal: 1 (BUY), -1 (SELL), 0 (HOLD)
            price: Precio actual
        """
        if pair not in self.pairs:
            return
        
        # Si hay posición abierta en este par
        if pair in self.positions:
            position = self.positions[pair]
            
            # Checkear stop-loss
            if position.side == 'LONG' and price <= position.stop_loss:
                self.close_position(pair, price, "STOP_LOSS")
            
            # Checkear take-profit
            if position.side == 'LONG' and price >= position.take_profit:
                self.close_position(pair, price, "TAKE_PROFIT")
        
        # Si no hay posición y hay señal
        if signal != 0 and pair not in self.positions:
            self.open_position(pair, signal, price)
    
    def open_position(self, pair: str, side: int, price: float):
        """Abrir nueva posición."""
        # Calcular tamaño (1% del capital por posición)
        size = (self.risk_limiter.balance * 0.01) / price
        
        # Calcular SL y TP
        if side == 1:  # LONG
            stop_loss = price * 0.98  # 2% abajo
            take_profit = price * 1.03  # 3% arriba
        else:  # SHORT
            stop_loss = price * 1.02  # 2% arriba
            take_profit = price * 0.97  # 3% abajo
        
        # Validar
        validation = self.risk_limiter.validate_trade(
            pair, 'LONG' if side == 1 else 'SHORT',
            price, stop_loss, size
        )
        
        if not validation['is_valid']:
            print(f"❌ {pair}: Trade rechazado por risk manager")
            return False
        
        # Abrir posición
        self.positions[pair] = Position(
            pair=pair,
            side='LONG' if side == 1 else 'SHORT',
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            size=size,
            opened_at=datetime.now().isoformat()
        )
        
        action = "LONG" if side == 1 else "SHORT"
        print(f"📈 {pair}: Entrada {action} a ${price:.2f}")
        return True
    
    def close_position(self, pair: str, price: float, reason: str):
        """Cerrar posición."""
        if pair not in self.positions:
            return
        
        position = self.positions[pair]
        pnl = (price - position.entry_price) * position.size
        
        if position.side == 'SHORT':
            pnl = -pnl
        
        print(f"📊 {pair}: Cerrado ({reason}) | PnL: ${pnl:.2f}")
        
        del self.positions[pair]
    
    def get_portfolio_status(self) -> Dict:
        """Retornar estado de todas las posiciones."""
        return {
            'num_open_positions': len(self.positions),
            'pairs_active': list(self.positions.keys()),
            'positions': {k: {
                'side': v.side,
                'entry': v.entry_price,
                'sl': v.stop_loss,
                'tp': v.take_profit
            } for k, v in self.positions.items()}
        }
```

---

## Ejecución de Ejemplos

Para probar estos códigos:

```bash
# Sprint 3: Backtesting
cd Backend
python backtester.py
# Output: Resumen de backtest con métricas

# Sprint 4: Base de datos
python database.py
# Output: Crear BD, agregar trades, calcular stats

# Sprint 5: Multi-par
python multi_pair_manager.py
# Output: Gestión de múltiples posiciones
```

---

**Notas:**
- Estos son ejemplos simplificados
- En producción, agregar manejo de excepciones exhaustivo
- Agregar logging en todos los métodos críticos
- Unit tests para cada clase

