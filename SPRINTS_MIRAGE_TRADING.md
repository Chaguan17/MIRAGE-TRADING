# 🚀 PLAN DE SPRINTS: Mirage Trading
## De Experimental a Producción

---

## 📊 Visión General

| Sprint | Nombre | Duración | Estado | Prioridad |
|--------|--------|----------|--------|-----------|
| Inmediato | Tareas críticas ahora | 1 semana | 🔴 BLOQUEANTE | **P0** |
| Sprint 3 | Backtesting & Validación | 2-3 semanas | 🔴 CRÍTICO | **P0** |
| Sprint 4 | Producción & Límites de Riesgo | 2-3 semanas | 🟠 IMPORTANTE | **P1** |
| Sprint 5 | Escalabilidad & Multi-Par | 2-3 semanas | 🟢 NICE-TO-HAVE | **P2** |
| Sprint 6 | Optimización (Opcional) | 2-3 semanas | 🔵 FUTURO | **P3** |

**Timeline total:** 10-15 semanas (~2.5-3.5 meses)

---

## ⚡ TAREAS INMEDIATAS (Esta semana)

### Por qué primero?
Estas tareas **desbloquean** los sprints posteriores. Sin ellas, no hay base sólida para backtesting.

### Tarea 1.1: Code Review & Refactoring

**Descripción:**
Limpieza general del código para que sea mantenible y testeable.

**Subtareas:**
- [ ] Ejecutar `pylint` en `Backend/` → fixing warnings
- [ ] Reemplazar magic numbers con constantes (ej: `MIN_TRADES_FOR_AI = 5` con variable `config.MIN_TRADES_FOR_AI`)
- [ ] Estandarizar nombres de variables (snake_case en todo Python)
- [ ] Agregar docstrings a todas las funciones principales
- [ ] Remover código muerto y comentarios obsoletos

**Archivos críticos:**
- `brain.py` (1000+ líneas, refactor agresivo)
- `binance_api.py` (verificar manejo de excepciones)
- `risk_manager.py` (verificar lógica de posicionamiento)

**Aceptación:**
- Pylint score > 8.0
- Todos los métodos tienen docstrings
- Zero warnings en imports

**Estimación:** 8-12 horas

---

### Tarea 1.2: Setup Testing

**Descripción:**
Crear suite básica de tests con pytest.

**Subtareas:**
- [ ] Crear carpeta `Backend/tests/`
- [ ] Escribir tests para `config.py` (cargar/validar config)
- [ ] Escribir tests para `risk_manager.py` (posicionamiento dinámico)
- [ ] Escribir tests para `brain.py` (voting system, confidence threshold)
- [ ] Setup CI/CD con GitHub Actions (run tests on push)

**Test coverage mínimo:** 60%

**Archivo:** `Backend/tests/test_core.py` (500 líneas)

**Aceptación:**
- pytest corre sin errores
- Coverage > 60%
- CI pasa en cada commit

**Estimación:** 10-14 horas

---

### Tarea 1.3: Documentación de Estrategias

**Descripción:**
Documentar cada una de las 9 estrategias técnicas con fórmulas y parámetros.

**Subtareas:**
- [ ] Crear `Backend/STRATEGIES.md` (1500+ palabras)
- [ ] Para cada estrategia: 
  - Qué es (1 párrafo)
  - Fórmula técnica (si aplica)
  - Parámetros clave (threshold, lookback, etc.)
  - Condición de entrada
  - Condición de salida
  - Ejemplo: "Si RSI < 30 → BUY"

**Formato:**
```markdown
## Trend Follower

**Descripción:** Sigue tendencias alcistas identificando EMA cruzadas.

**Fórmula:** 
- EMA corto: 9 periodos
- EMA largo: 21 periodos
- Señal: EMA9 > EMA21 = BULL

**Parámetros:**
- lookback_periods: 21
- confidence_threshold: 0.65

**Entrada:** EMA9 cruza sobre EMA21 (bullish)
**Salida:** EMA9 cae bajo EMA21 (bearish)

**Ejemplo:**
```
precio: [10, 11, 12, 13, 14, ...]
EMA9:  [10.2, 10.6, 11.2, 12.1, ...]
EMA21: [10.1, 10.3, 10.5, 10.8, ...]
       Entrada aquí ↑ (EMA9 > EMA21)
```

**Aceptación:**
- Todas las 9 estrategias documentadas
- Fórmulas técnicas correctas
- Parámetros por defecto listados
- Ejemplos visuales para 3 estrategias

**Estimación:** 8-10 horas

---

### Tarea 1.4: Issue Tracker

**Descripción:**
Crear lista de bugs conocidos y TODOs en GitHub Issues.

**Subtareas:**
- [ ] Crear `ISSUES.md` con bugs conocidos:
  - CSV performance degradation con 1000+ trades
  - Paper trading balance no sincroniza si hay error
  - ML model overfit (5 trades mínimo es muy bajo)
  - Sin validación de entrada en endpoints API
  - Timeout en conexión Binance (30s default)
  
- [ ] Etiquetar por severidad: `[critical]`, `[high]`, `[medium]`
- [ ] Asignar prioridad vs sprint

**Formato:**
```
## 🔴 [CRITICAL] CSV Performance Issue

**Problema:** 
Después de 5000+ trades, lectura de CSV toma > 1s.

**Causa raíz:**
Pandas carga el CSV completo en memoria sin chunking.

**Solución propuesta:**
Migrar a SQLite con índices.

**Sprint:** 4 (Producción)
```

**Aceptación:**
- Mínimo 15 issues creados
- Todos etiquetados
- Priorizados por sprint

**Estimación:** 4-6 horas

---

**Total Inmediato:** 30-42 horas (1 semana intenso, 2 semanas normales)

---

## 🔴 SPRINT 3: Backtesting & Validación (2-3 semanas)

### Por qué es crítico?

Antes de operar en real (o incluso en paper), **debes validar tu bot contra datos históricos reales**. Sin esto:
- No sabes si las estrategias funcionan
- El ML puede estar overfitted al mercado actual
- Podrías perder dinero real muy rápido

### Tarea 3.1: Framework de Backtesting

**Descripción:**
Crear sistema que simule operaciones contra datos históricos.

**Archivo:** `Backend/backtester.py` (~400 líneas)

**Lógica:**
```python
class Backtester:
    def __init__(self, start_date, end_date, initial_balance):
        self.data = fetch_ohlcv(start_date, end_date)  # Histórico 2016-2024
        self.balance = initial_balance
        self.trades = []
        
    def run(self, strategy_name):
        """Simula compra/venta según estrategia"""
        for day in self.data:
            signal = self.brain.predict(day)
            if signal == "BUY":
                self.execute_buy(day.close)
            elif signal == "SELL":
                self.execute_sell(day.close)
        
        return self.calculate_metrics()
    
    def calculate_metrics(self):
        """Retorna: PnL, Win Rate, Sharpe, Drawdown, etc."""
        return {
            'total_pnl': float,
            'win_rate': float,
            'sharpe_ratio': float,
            'max_drawdown': float,
            'profit_factor': float,
            'num_trades': int
        }
```

**Subtareas:**
- [ ] Descargar datos históricos (CCXT, inicio 2016)
- [ ] Implementar `execute_buy()`, `execute_sell()` (sin API real)
- [ ] Calcular métricas (ver Tarea 3.2)
- [ ] Guardar resultados en JSON/CSV
- [ ] Crear gráficas (equity curve, drawdown, histogram PnL)

**Aceptación:**
- Backtester corre para 1 estrategia sin errores
- Genera reporte JSON con 6+ métricas
- Equity curve plottea correctamente

**Estimación:** 20-28 horas

---

### Tarea 3.2: Métricas Avanzadas

**Descripción:**
Implementar cálculo de métricas profesionales.

**Métricas a agregar:**

#### 1. Sharpe Ratio
```
Sharpe = (Retorno Promedio - Tasa Libre de Riesgo) / Desviación Estándar
Interprete: > 1.0 = Bueno, > 2.0 = Excelente
```

```python
def calculate_sharpe(returns, risk_free_rate=0.02):
    excess_return = np.mean(returns) - risk_free_rate
    return excess_return / np.std(returns)
```

#### 2. Máximo Drawdown
```
MaxDD = (Peak - Trough) / Peak
La mayor caída desde un máximo histórico.
Interprete: < -20% es aceptable, < -50% es malo
```

```python
def calculate_max_drawdown(equity_curve):
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - running_max) / running_max
    return np.min(drawdown)
```

#### 3. Calmar Ratio
```
Calmar = Retorno Anualizado / |Máximo Drawdown|
Interprete: > 1.0 = Bueno
```

#### 4. Profit Factor
```
Profit Factor = Ganancia Total / Pérdida Total
Interprete: > 1.5 = Bueno, > 2.0 = Muy bueno
```

#### 5. Recovery Factor
```
Recovery = Retorno Total / Máximo Drawdown
```

**Archivo:** `Backend/metrics.py` (~200 líneas)

**Aceptación:**
- Todas 5 métricas calculan sin error
- Validadas contra benchmark (ej: comparar con Backtrader)
- Documentadas con ejemplos

**Estimación:** 12-16 horas

---

### Tarea 3.3: Walk-Forward Analysis

**Descripción:**
Validar el modelo entrenando en datos pasados y testeando en futuros (rolling window).

**Lógica:**
```
Año 2016-2022:  TRAIN (modelo aprende)
Año 2023:       TEST  (predice sin haber visto estos datos)

Año 2017-2023:  TRAIN (actualizado)
Año 2024:       TEST  (valida 2024)
```

**Archivo:** `Backend/walk_forward.py` (~300 líneas)

**Subtareas:**
- [ ] Dividir datos en 4 ventanas (2016-2022, 2023, 2024, etc.)
- [ ] Para cada ventana: entrenar ML en TRAIN, testear en TEST
- [ ] Graficar resultados por período
- [ ] Detectar degradación de performance

**Interpretación:**
```
Si Sharpe en 2023 = 1.2 pero Sharpe en 2024 = 0.3
→ El modelo se degradó (posible cambio de mercado)
→ Necesita reentrenamiento
```

**Aceptación:**
- 4 períodos procesados correctamente
- Tablas comparativas generadas
- Gráficas por período

**Estimación:** 14-20 horas

---

### Tarea 3.4: Aumento de MIN_TRADES_FOR_AI

**Descripción:**
Cambiar de 5 trades mínimo a 100 (reduce overfitting).

**Cambios:**
- `brain.py` línea 284: `MIN_TRADES_FOR_AI = 5` → `MIN_TRADES_FOR_AI = 100`

**Impacto:**
- El modelo no entrena hasta tener 100 trades históricos
- En paper trading: tarda más en aprender pero es más robusto
- Evita predicciones basadas en ruido

**Aceptación:**
- Tests pasan con nuevo valor
- Documentación actualizada

**Estimación:** 1-2 horas

---

### Tarea 3.5: Reporte Visual

**Descripción:**
Generar dashboard HTML con resultados de backtesting.

**Archivo:** `Backend/backtest_report.html` (generado dinámicamente)

**Contenido:**
```html
<h1>Backtesting Report: 2016-2024</h1>

<h2>Resumen de Métricas</h2>
<table>
  <tr><td>Total PnL</td><td>+12,450 USDT</td></tr>
  <tr><td>Win Rate</td><td>58%</td></tr>
  <tr><td>Sharpe Ratio</td><td>1.45</td></tr>
  <tr><td>Máximo Drawdown</td><td>-18.5%</td></tr>
  <tr><td>Profit Factor</td><td>2.1x</td></tr>
</table>

<h2>Equity Curve</h2>
<img src="equity_curve.png"/>

<h2>Drawdown %</h2>
<img src="drawdown.png"/>

<h2>Distribution de PnL</h2>
<img src="pnl_histogram.png"/>

<h2>Trades Individuales</h2>
<table>
  <tr><th>Fecha</th><th>Pair</th><th>Entrada</th><th>Salida</th><th>PnL</th></tr>
  ...
</table>
```

**Tecnología:** Matplotlib para gráficas, Jinja2 para templating HTML

**Aceptación:**
- HTML se genera sin errores
- Todas las gráficas renderizan
- Tabla de trades es completa

**Estimación:** 10-14 horas

---

**Total Sprint 3:** 71-98 horas (~2.5 semanas a tiempo completo)

**Criterio de salida:** 
✓ Backtesting completado para todas 9 estrategias
✓ Sharpe Ratio ≥ 1.0 en al menos 3 estrategias
✓ Max Drawdown < -40%
✓ Reporte visual generado

---

## 🟠 SPRINT 4: Producción & Límites de Riesgo (2-3 semanas)

### Por qué es importante?

El bot debe ser **robusto y seguro** antes de operar. Sprint 4 agrega barandas de seguridad.

### Tarea 4.1: Limitar Leverage

**Problema actual:**
```
LEVERAGE: 10  # Muy alto, riesgo de liquidación rápida
```

**Solución:**
```python
# config.py
MAX_LEVERAGE = 3  # Límite hard
DEFAULT_LEVERAGE = 2  # Recomendado

# binance_api.py
def set_leverage(self, pair, leverage):
    if leverage > MAX_LEVERAGE:
        logger.warning(f"Leverage {leverage} > MAX {MAX_LEVERAGE}, capping...")
        leverage = MAX_LEVERAGE
    self.client.set_leverage(leverage, pair)
```

**Subtareas:**
- [ ] Actualizar `config.py` con `MAX_LEVERAGE`, `DEFAULT_LEVERAGE`
- [ ] Validar en `binance_api.py`
- [ ] Tests para intentar establecer leverage > MAX
- [ ] Logs cuando se limita

**Aceptación:**
- No se permite leverage > 3x
- DEFAULT = 2x en nueva instalación
- Warnings en logs

**Estimación:** 3-5 horas

---

### Tarea 4.2: Stop-Loss Obligatorio

**Problema actual:**
Las operaciones pueden no tener stop-loss definido.

**Solución:**
```python
# risk_manager.py
def validate_position(self, entry_price, stop_loss, take_profit):
    if stop_loss is None:
        raise ValueError("Stop-loss obligatorio")
    if abs(entry_price - stop_loss) / entry_price < 0.01:
        raise ValueError("Stop-loss debe ser ≥ 1% del entry")
    return True
```

**Subtareas:**
- [ ] Añadir validación en `executor.py`
- [ ] Tests para rechazar órdenes sin SL
- [ ] Dashboard muestra SL para cada operación
- [ ] Logs cuando se rechaza orden

**Aceptación:**
- 100% de trades tienen stop-loss
- Distancia mínima validada (1% del entry)
- Rechaza órdenes inválidas

**Estimación:** 6-8 horas

---

### Tarea 4.3: Migración CSV → SQLite

**Problema actual:**
```python
df = pd.read_csv("storage/trade_history.csv")  # Lento con 10k+ filas
```

**Solución:**
```python
# Backend/database.py (NUEVO)
import sqlite3

class TradeDB:
    def __init__(self, db_path="storage/trades.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                pair TEXT,
                action TEXT,
                entry_price REAL,
                exit_price REAL,
                pnl_usdt REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)")
        self.conn.commit()
    
    def add_trade(self, timestamp, pair, action, entry, exit, pnl):
        self.conn.execute(
            "INSERT INTO trades (timestamp, pair, action, entry_price, exit_price, pnl_usdt) VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, pair, action, entry, exit, pnl)
        )
        self.conn.commit()
    
    def get_last_trades(self, limit=100):
        return self.conn.execute(
            "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
```

**Subtareas:**
- [ ] Crear `Backend/database.py` (~200 líneas)
- [ ] Reemplazar pd.read_csv() con queries SQLite
- [ ] Migración: convertir CSV existente a DB
- [ ] Tests para insert/select
- [ ] Backup automático del DB

**Performance:**
```
CSV (5000 trades):  ~500ms lectura
SQLite (5000):      ~50ms lectura  ✓ 10x más rápido
```

**Aceptación:**
- SQLite creado con índices
- Queries funcionan sin error
- Migración completa (CSV → DB)
- Performance > 10x más rápido

**Estimación:** 14-18 horas

---

### Tarea 4.4: Reconexión Automática

**Problema actual:**
Si Binance API cae, el bot se detiene.

**Solución:**
```python
# binance_api.py
def get_historical_data(self, symbol, timeframe='1m', limit=500, max_retries=5):
    for attempt in range(max_retries):
        try:
            bars = self.client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        except Exception as e:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
            logger.warning(f"API error, reintentando en {wait_time}s: {e}")
            time.sleep(wait_time)
    
    logger.error("Fallo permanente después de 5 reintentos")
    return None
```

**Subtareas:**
- [ ] Implementar exponential backoff (1s, 2s, 4s, 8s, 16s)
- [ ] Tests para simular fallos de API
- [ ] Logs detallados de cada reintento
- [ ] Máximo 5 reintentos

**Aceptación:**
- Reintentos funcionan (testeado con mock)
- Logs muestran retries
- Falla gracefully después de 5 intentos

**Estimación:** 8-10 horas

---

### Tarea 4.5: Logging Exhaustivo

**Problema actual:**
Errores de API no se registran bien.

**Solución:**
```python
# Backend/logger_config.py (NUEVO)
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    logger = logging.getLogger('mirage')
    handler = RotatingFileHandler(
        'storage/logs/mirage.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
```

**Subtareas:**
- [ ] Crear sistema de logging centralizado
- [ ] Logs guardados en `storage/logs/mirage.log`
- [ ] Rotación automática (máx 50MB)
- [ ] Niveles: DEBUG, INFO, WARNING, ERROR
- [ ] Agregar logs en puntos críticos (API calls, trades, errors)

**Aceptación:**
- Log file se crea en la primera ejecución
- Errores capturados y logeados
- Rotación funciona (5 backups máximo)

**Estimación:** 6-8 horas

---

### Tarea 4.6: Dashboard Mejorado

**Descripción:**
Agregar nuevas métricas a la UI.

**Cambios en `Frontend/App.jsx`:**
```jsx
// Antes
<div>PnL Total: {data.pnl_total}</div>

// Después
<div>
  <div>PnL Total: {data.pnl_total}</div>
  <div>Sharpe Ratio: {data.sharpe_ratio.toFixed(2)}</div>
  <div>Max Drawdown: {data.max_drawdown.toFixed(2)}%</div>
  <div>Profit Factor: {data.profit_factor.toFixed(2)}x</div>
</div>
```

**Backend cambios:**
```python
# api.py
def get_dashboard_data():
    data = {
        'pnl_total': ...,
        'win_rate': ...,
        'sharpe_ratio': calculate_sharpe(returns),  ← NUEVO
        'max_drawdown': calculate_max_drawdown(equity),  ← NUEVO
        'profit_factor': calculate_profit_factor(trades),  ← NUEVO
    }
```

**Subtareas:**
- [ ] Calcular métricas en backend
- [ ] Pasar a frontend
- [ ] Renderizar en 4 nuevos cards
- [ ] Estilos acorde al tema

**Aceptación:**
- 4 nuevas métricas aparecen en dashboard
- Actualizan cada 3 segundos
- Sin errores de rendering

**Estimación:** 6-8 horas

---

**Total Sprint 4:** 43-57 horas (~2 semanas)

**Criterio de salida:**
✓ Leverage limitado a 2-3x
✓ Stop-loss obligatorio y validado
✓ SQLite activo, CSV migrado
✓ Reconexión automática testeada
✓ Logs se escriben correctamente
✓ Dashboard muestra 7 métricas

---

## 🟢 SPRINT 5: Escalabilidad & Multi-Par (2-3 semanas)

### Por qué?

Un bot que opera un solo par es aburrido. Escalemos a 5+ pares con diversificación.

### Tarea 5.1: Soporte Multi-Par

**Problema actual:**
Bot opera solo en 1 par (hardcoded).

**Solución:**
```python
# config.py
TRADING_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "MATICUSDT"]
```

```python
# main.py (REFACTOR)
for pair in TRADING_PAIRS:
    signal = brain.predict(pair)
    if signal:
        execute_trade(pair, signal)
```

**Subtareas:**
- [ ] Refactor `brain.py` para aceptar `pair` como parámetro
- [ ] Refactor `data_engine.py` para múltiples pares
- [ ] Refactor `executor.py` para manejar 5+ pares simultáneamente
- [ ] Almacenar datos históricos por par
- [ ] Tests para múltiples pares

**Aceptación:**
- Bot opera en 5 pares simultáneamente
- Sin errores de sincronización
- Datos históricos separados por par

**Estimación:** 18-24 horas

---

### Tarea 5.2: Diversificación & Risk Limits

**Descripción:**
Asegurar que no haya concentración excesiva en un solo par.

**Lógica:**
```python
# risk_manager.py
MAX_RISK_PER_PAIR = 0.02  # 2% del capital por par
TOTAL_RISK = 0.05  # 5% del capital máximo en posiciones

def validate_new_position(self, pair, size):
    current_exposure = sum(pos.size for pos in self.positions if pos.pair != pair)
    new_exposure = current_exposure + size
    
    if new_exposure > TOTAL_RISK * self.balance:
        raise RiskError(f"Exposición total {new_exposure} > {TOTAL_RISK*self.balance}")
```

**Subtareas:**
- [ ] Definir límites por par
- [ ] Validar en `risk_manager.py`
- [ ] Tests para límites
- [ ] Logs cuando se rechaza por riesgo

**Aceptación:**
- Máx 2% por par
- Máx 5% total
- Se rechaza si excede

**Estimación:** 10-12 horas

---

### Tarea 5.3: WebSocket para Data en Vivo

**Problema actual:**
```python
# main.py
while True:
    data = binance.get_ohlcv()
    brain.predict(data)
    time.sleep(3)  # Polling cada 3 segundos
```

**Solución:**
```python
# Backend/websocket_handler.py (NUEVO)
import asyncio
import websockets
import json

async def stream_prices():
    stream_url = "wss://stream.binance.com:9443/stream?streams=btcusdt@kline_1m/ethusdt@kline_1m/..."
    async with websockets.connect(stream_url) as ws:
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            await process_candle(data)
```

**Ventaja:**
```
Polling (3s delay):     Precio puede llegar 3 segundos tarde
WebSocket (push):       Actualización en < 100ms
```

**Subtareas:**
- [ ] Implementar WebSocket async handler
- [ ] Reemplazar polling en main.py
- [ ] Reconnect automático si se cae
- [ ] Tests para stream

**Aceptación:**
- WebSocket se conecta sin error
- Recibe datos en < 200ms
- Reconecta automáticamente

**Estimación:** 14-18 horas

---

### Tarea 5.4: Dashboard Multi-Par

**Descripción:**
Actualizar UI para mostrar estado de todos los pares.

**Mockup:**
```
┌─────────────────────────────────────────────────┐
│ MIRAGE TRADING - Dashboard                      │
├─────────────────────────────────────────────────┤
│ Total PnL: +1,250 USDT | Win Rate: 62%         │
├─────────────────────────────────────────────────┤
│ PARES ACTIVOS:                                  │
│                                                 │
│ BTCUSDT    [LONG]  Entry: 42,100  Current: 42,350  +250 USDT
│ ETHUSDT    [HOLD]  No posición activa
│ BNBUSDT    [SHORT] Entry: 610     Current: 605     +50 USDT
│ SOLUSDT    [HOLD]  No posición activa
│ MATICUSDT  [LONG]  Entry: 0.85    Current: 0.88    +30 USDT
│
├─────────────────────────────────────────────────┤
│ HISTORIAL (últimas 30 operaciones)              │
│ ...                                             │
└─────────────────────────────────────────────────┘
```

**Subtareas:**
- [ ] Crear componente `PairStatus` en React
- [ ] Renderizar 5 filas (un par cada una)
- [ ] Mostrar entrada, precio actual, PnL
- [ ] Colores: GREEN para LONG, RED para SHORT, GRAY para HOLD
- [ ] Actualizar cada segundo

**Aceptación:**
- Todos los pares se muestran
- Colores correctos
- Se actualiza en vivo

**Estimación:** 10-14 horas

---

### Tarea 5.5: Alertas por Email/SMS

**Descripción:**
Notificar usuario cuando se cierra una posición importante.

**Implementación:**
```python
# Backend/alerts.py (NUEVO)
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_alert(pair, action, pnl):
    message = Mail(
        from_email="bot@mirage.trading",
        to_emails="user@email.com",
        subject=f"🤖 Operación cerrada: {pair} {action}",
        html_content=f"<h1>{pair} {action}</h1><p>PnL: ${pnl}</p>"
    )
    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    sg.send(message)
```

**Subtareas:**
- [ ] Integrar SendGrid
- [ ] Enviar email al cerrar posición
- [ ] Template HTML profesional
- [ ] Tests (mock email)
- [ ] Config: `ALERT_EMAIL`, `ALERT_MIN_PNL` (solo alertar si |PnL| > umbral)

**Aceptación:**
- Email se envía correctamente
- Template renderiza bien
- Solo alerta si |PnL| > 50 USDT (configurable)

**Estimación:** 8-10 horas

---

### Tarea 5.6: Documentación Completa

**Descripción:**
Escribir guías de setup, deploy, API.

**Archivos:**
- [ ] `README.md` (500 palabras): qué es, cómo instalar, ejemplo básico
- [ ] `DEPLOY.md` (800 palabras): cómo lanzar en producción (VPS, systemd, etc.)
- [ ] `API.md` (400 palabras): endpoints disponibles
- [ ] `CONFIG.md` (600 palabras): todas las variables de configuración

**README outline:**
```
# Mirage Trading Bot

## Qué es?
Bot de criptotarifas con IA...

## Quickstart
1. Clone repo
2. `pip install -r requirements.txt`
3. Copia `.env.example` → `.env`
4. `python Backend/main.py`

## Características
- 9 estrategias técnicas
- Machine Learning (Random Forest)
- Paper trading
- Dashboard en tiempo real

## Requisitos
- Python 3.9+
- Binance API keys
- Node.js 16+ (para frontend)

## Resultados Históricos
Backtesting 2016-2024: Sharpe 1.45, Max DD -18%, Profit Factor 2.1x

## Riesgos
- Leverage 2x (configurable hasta 3x)
- Stop-loss obligatorio
- No es garantizado ganar dinero
```

**Aceptación:**
- 4 archivos de doc creados
- Ejemplos funcionales
- Sin errores de formato

**Estimación:** 12-16 horas

---

**Total Sprint 5:** 72-94 horas (~2.5 semanas)

**Criterio de salida:**
✓ Multi-par operativo (5 pares)
✓ Diversificación límites validados
✓ WebSocket live data
✓ Dashboard multi-par
✓ Alertas email funcionales
✓ Documentación completa

---

## 🔵 SPRINT 6: Optimización & Aprendizaje (Opcional, 2-3 semanas)

### Tarea 6.1: Dynamic Parameter Tuning

Ajustar automáticamente timeframe según volatilidad.

**Lógica:**
```python
def select_timeframe(self, atr):
    """ATR alto = mercado volátil = usar timeframe mayor"""
    if atr > 2.0:
        return "5m"  # Mercado volátil
    elif atr > 1.0:
        return "1m"
    else:
        return "30s"  # Mercado calmo, análisis más granular
```

**Estimación:** 10-14 horas

---

### Tarea 6.2: Ensemble Models

Combinar múltiples modelos ML para predicciones más robustas.

```python
models = [
    RandomForestClassifier(...),
    GradientBoostingClassifier(...),
    LogisticRegression(...)
]

predictions = [m.predict(X) for m in models]
final_signal = majority_vote(predictions)
```

**Estimación:** 16-20 horas

---

### Tarea 6.3: API REST Pública

Permitir queries externas (precios, historial).

```
GET /api/price/BTCUSDT
GET /api/trades?limit=100
GET /api/metrics
```

**Estimación:** 12-16 horas

---

### Tarea 6.4: Performance por Estrategia

Medir qué estrategia genera más PnL.

```
Strategy Performance:
├─ Trend Follower:    +450 USDT (8 trades)
├─ Mean Reversion:    +380 USDT (12 trades)
├─ Breakout:          +290 USDT (5 trades)
└─ Otros:             +140 USDT
```

**Estimación:** 12-14 horas

---

**Total Sprint 6:** 50-64 horas (~2 semanas)

---

## ✅ Checklist de Completitud

### Sprint 3:
- [ ] Backtester implementado
- [ ] Sharpe Ratio calculado
- [ ] Walk-forward analysis completado
- [ ] MIN_TRADES_FOR_AI = 100
- [ ] Reporte HTML generado

### Sprint 4:
- [ ] Leverage ≤ 3x
- [ ] Stop-loss obligatorio
- [ ] SQLite activo
- [ ] Reconexión automática
- [ ] Logs en archivo
- [ ] Dashboard +4 métricas

### Sprint 5:
- [ ] Multi-par (5 pairs)
- [ ] Limits de riesgo por par
- [ ] WebSocket streaming
- [ ] Dashboard actualizado
- [ ] Alertas email
- [ ] Docs completas

### Sprint 6 (opcional):
- [ ] Dynamic timeframe
- [ ] Ensemble models
- [ ] API pública
- [ ] Performance por estrategia

---

## 📊 Estimaciones Totales

| Sprint | Horas | Semanas | Prioridad |
|--------|-------|---------|-----------|
| Inmediato | 30-42 | 1 | 🔴 P0 |
| Sprint 3 | 71-98 | 2.5 | 🔴 P0 |
| Sprint 4 | 43-57 | 2 | 🟠 P1 |
| Sprint 5 | 72-94 | 2.5 | 🟢 P2 |
| Sprint 6 | 50-64 | 2 | 🔵 P3 |
| **TOTAL** | **266-355** | **10-15** | |

---

## 🎯 Hitos Críticos

```
Semana 1:  ✓ Tareas Inmediatas (Code review, tests)
Semana 3:  ✓ Sprint 3 completado (Backtesting OK)
Semana 5:  ✓ Sprint 4 completado (Producción segura)
Semana 7:  ✓ Sprint 5 completado (Multi-par)
Semana 10: ✓ Bot listo para producción real
Semana 12: ✓ Sprint 6 opcional (mejoras)
```

---

## 💡 Notas Finales

1. **Los sprints pueden ser parcialmente paralelos**
   - S3 y S4 pueden overlap (ejemplo: S3 testing + S4 leverage limits)
   - Pero S3 (backtesting) debe completarse ANTES de dinero real

2. **Cada sprint requiere code review**
   - Antes de merge a main, peer review
   - Mínimo 1 persona que verifique lógica

3. **Después de cada sprint, ejecutar suite de tests**
   - `pytest Backend/tests/` debe pasar
   - Backtesting debe confirmarse

4. **No saltarse Sprint 3 (backtesting)**
   - Sin validación histórica, alto riesgo de pérdida
   - Absolutamente crítico

5. **Sprint 5 agrega valor pero no es bloqueante**
   - Bot puede funcionar con 1 par
   - Multi-par es "nice-to-have"

---

**Plan creado:** Mayo 2026
**Proyecto:** Mirage Trading
**Estado:** Listo para ejecutar
