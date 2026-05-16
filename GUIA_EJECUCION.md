# 🎯 GUÍA DE EJECUCIÓN - Mirage Trading Sprints

## 📋 Checklist Rápido

Usa este documento como guía día a día para completar cada sprint.

---

## ⚡ SEMANA 1: TAREAS INMEDIATAS

### Lunes & Martes: Code Review

```bash
# 1. Ejecutar linter en backend
cd Backend
pylint *.py methods/*.py --disable=C0111,W0212

# 2. Buscar magic numbers y hardcoding
grep -n "^[[:space:]]*[0-9]\+" *.py | head -20

# 3. Documentar funciones principales
# Agregar docstrings: """Qué hace, Args, Returns, Ejemplo"""

# Ejemplo:
def predict(self, data):
    """
    Predice si comprar, vender u holdear basado en 9 estrategias.
    
    Args:
        data (dict): {rsi, ema_9, ema_21, atr, ...}
    
    Returns:
        int: 1 (BUY), -1 (SELL), 0 (HOLD)
    
    Ejemplo:
        >>> brain.predict({'rsi': 25, 'ema_9': 100, ...})
        1  # BUY signal
    """
    ...
```

**Checklist:**
- [ ] Pylint score > 8.0
- [ ] Todos los métodos > 10 líneas tengan docstring
- [ ] Sin imports no utilizados
- [ ] Sin variables no utilizadas

**Estimación:** 4-6 horas

---

### Miércoles: Testing Setup

```bash
# 1. Crear estructura de tests
mkdir -p Backend/tests
touch Backend/tests/__init__.py
touch Backend/tests/test_core.py
touch Backend/tests/conftest.py

# 2. Instalar pytest
pip install pytest pytest-cov

# 3. Escribir test básico
# Backend/tests/test_core.py

import pytest
from Backend.config import load_config

def test_load_config():
    config = load_config()
    assert config['TIMEFRAME'] == '1m'
    assert config['LEVERAGE'] <= 3

def test_position_sizing():
    from Backend.risk_manager import RiskManager
    rm = RiskManager(balance=1000)
    size = rm.calculate_position_size(entry=100, stop_loss=98)
    assert size > 0

# 4. Ejecutar tests
pytest Backend/tests/ -v --cov=Backend
```

**Checklist:**
- [ ] Pytest instala sin error
- [ ] 5+ tests creados
- [ ] Coverage > 60%
- [ ] CI/CD configurado (GitHub Actions)

**Estimación:** 6-8 horas

---

### Jueves & Viernes: Documentación + Tracking

```bash
# 1. Crear Backend/STRATEGIES.md
cat > Backend/STRATEGIES.md << 'EOF'
# Estrategias de Trading Mirage

## 1. Trend Follower
**Lógica:** Sigue tendencias con EMA cruzadas
- EMA 9 > EMA 21 → COMPRAR
- EMA 9 < EMA 21 → VENDER
**Parámetros:** lookback=21, threshold=0.65

## 2. Mean Reversion
**Lógica:** RSI < 30 → Sobrevendido → COMPRAR
**Parámetros:** rsi_period=14, oversold=30, overbought=70

... (8 estrategias más)
EOF

# 2. Crear ISSUES.md con bugs conocidos
cat > ISSUES.md << 'EOF'
## 🔴 CRITICAL

### [1] CSV Performance (Sprint 4)
- Problema: Lectura CSV lenta con 10k+ trades
- Solución: Migrar a SQLite
- Sprint: 4

### [2] ML Overfitting (Sprint 3)
- Problema: MIN_TRADES_FOR_AI = 5 es muy bajo
- Solución: Aumentar a 100
- Sprint: 3

... (13 issues más)
EOF

# 3. Crear GitHub Issues (si usas GitHub)
gh issue create --title "Code Review & Refactoring" --body "Sprint Inmediato Task 1.1"
gh issue create --title "Setup Testing Framework" --body "Sprint Inmediato Task 1.2"
...
```

**Checklist:**
- [ ] STRATEGIES.md completado (9 estrategias documentadas)
- [ ] ISSUES.md con 15+ problemas identificados
- [ ] GitHub Issues creados (opcional pero recomendado)

**Estimación:** 6-8 horas

---

**FIN SEMANA 1:** 30-42 horas ✅

---

## 🔴 SEMANA 3-4: SPRINT 3 - BACKTESTING

### Semana 3: Implementación

```bash
# 1. Crear backtester.py (ver ejemplos de código)
cp CODIGO_EJEMPLOS_SPRINTS.md Backend/backtester.py

# 2. Descargar datos históricos
python -c "
import ccxt
import pandas as pd

exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', since=exchange.parse8601('2020-01-01'), limit=1500)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'o', 'h', 'l', 'c', 'v'])
df.to_csv('data/btcusdt_2020_2024.csv', index=False)
print(f'Downloaded {len(df)} candles')
"

# 3. Ejecutar backtest
python Backend/backtester.py --symbol BTCUSDT --start 2020-01-01 --end 2024-12-31

# Output esperado:
# 🚀 Iniciando backtest...
# 📊 Total PnL: +1,250 USDT
# Win Rate: 58%
# Sharpe Ratio: 1.45
```

**Checklist:**
- [ ] Backtester.py ejecuta sin errores
- [ ] Genera 5+ métricas
- [ ] Sharpe Ratio > 0.5 (básico)

**Estimación:** 20 horas

---

### Semana 4: Análisis & Validación

```bash
# 1. Walk-forward analysis
python Backend/walk_forward.py --window 1y

# Output:
# 2020-2021 (Train) → 2022 (Test): Sharpe 1.2
# 2021-2022 (Train) → 2023 (Test): Sharpe 0.9
# 2022-2023 (Train) → 2024 (Test): Sharpe 1.1

# 2. Cambiar MIN_TRADES_FOR_AI
sed -i 's/MIN_TRADES_FOR_AI = 5/MIN_TRADES_FOR_AI = 100/' Backend/brain.py

# 3. Generar reporte HTML
python Backend/generate_report.py --output backtest_report.html

# 4. Ejecutar suite completa de tests
pytest Backend/tests/ --cov=Backend --cov-report=html
open htmlcov/index.html  # Ver cobertura visual
```

**Checklist:**
- [ ] Walk-forward completado (4 períodos)
- [ ] MIN_TRADES_FOR_AI = 100
- [ ] Sharpe ≥ 1.0 en ≥ 3 estrategias
- [ ] Reporte HTML generado
- [ ] Coverage > 75%

**Estimación:** 30-40 horas

---

**FIN SPRINT 3:** 71-98 horas ✅

---

## 🟠 SEMANA 5-6: SPRINT 4 - PRODUCCIÓN

### Tareas en Paralelo

```bash
# TASK 1: Leverage Limits
# Backend/config.py
MAX_LEVERAGE = 3.0
DEFAULT_LEVERAGE = 2.0

# Backend/binance_api.py
def set_leverage(self, pair, leverage):
    leverage = min(leverage, self.MAX_LEVERAGE)
    self.client.set_leverage(leverage, pair)

# Test:
pytest Backend/tests/test_leverage.py -v

---

# TASK 2: Database Migration
# Backend/database.py
python Backend/database.py

# Verificar:
sqlite3 storage/trades.db ".tables"
# Output: trades

# Migrar CSV → DB
python Backend/migrate_csv_to_db.py

---

# TASK 3: Logging Setup
# Backend/logger_config.py
from logger_config import setup_logging
logger = setup_logging()

# Test:
pytest Backend/tests/test_logging.py

---

# TASK 4: Dashboard Actualizado
# Frontend/App.jsx
# Agregar 4 cards nuevos: sharpe_ratio, max_drawdown, profit_factor, avg_win

npm run dev  # Probar frontend

---

# TASK 5: Reconexión Automática
# Backend/binance_api.py
# Implementar exponential backoff (ver ejemplos)

# Test:
pytest Backend/tests/test_reconnection.py
```

**Daily Standup (Para equipo):**

```
Lunes:
- ¿Hiciste?   Leverage limits completado
- ¿Bloqueos?  Ninguno
- ¿Próximo?   Database migration

Martes:
- ¿Hiciste?   SQLite create + migrate CSV
- ¿Bloqueos?  CSV muy grande, 10GB RAM
- ¿Próximo?   Logging setup

...
```

**Checklist Final Sprint 4:**
- [ ] Leverage ≤ 3x (validado)
- [ ] Stop-loss obligatorio (0% trades sin SL)
- [ ] SQLite activo (migrate completado)
- [ ] Reconexión automática (5 reintentos)
- [ ] Logs en archivo (rotación 50MB)
- [ ] Dashboard +4 métricas (funcional)

**Estimación:** 43-57 horas

---

**FIN SPRINT 4:** 10-12 semanas ✅

---

## 🟢 SEMANA 7-8: SPRINT 5 - MULTI-PAR

### Configuración

```bash
# 1. Definir pares a operar
# Backend/config.py
TRADING_PAIRS = [
    "BTCUSDT",    # Volatilidad alta
    "ETHUSDT",    # Correlacionado con BTC
    "BNBUSDT",    # Menos correlacionado
    "SOLUSDT",    # Alta volatilidad
    "MATICUSDT"   # Altcoin
]

# 2. Refactor para multi-par
# Backend/main.py
for pair in TRADING_PAIRS:
    signal = brain.predict(pair)
    if signal != 0:
        executor.execute(pair, signal)

# 3. Multi-par manager (ver ejemplos)
cp CODIGO_EJEMPLOS_SPRINTS.md Backend/multi_pair_manager.py

# 4. Test multi-par
pytest Backend/tests/test_multi_pair.py -v

# 5. WebSocket streaming
pip install websockets
python Backend/websocket_handler.py

# 6. Dashboard actualizado
npm run dev

# 7. Alertas email (SetupGrid)
pip install sendgrid
export SENDGRID_API_KEY="..."
pytest Backend/tests/test_alerts.py
```

**Checklist:**
- [ ] 5 pares operando simultáneamente
- [ ] Límites de riesgo por par validados
- [ ] WebSocket conectado
- [ ] Dashboard muestra todos los pares
- [ ] Emails funcionando

**Estimación:** 72-94 horas

---

**FIN SPRINT 5:** 13-14 semanas ✅

---

## 🔵 SEMANA 9-10: SPRINT 6 (Opcional)

```bash
# Tareas opcionales para mejorar el bot

# 1. Dynamic timeframe
python Backend/dynamic_timeframe.py

# 2. Ensemble models
python Backend/ensemble_models.py

# 3. API pública
npm run dev

# 4. Performance analytics
python Backend/analytics.py
```

---

## 🚀 DEPLOYMENT A PRODUCCIÓN

### Pre-Deployment Checklist

```bash
# 1. Todos los tests pasan
pytest Backend/tests/ --cov=Backend
# Requerido: Coverage > 85%, todos los tests en verde

# 2. Backtest exitoso
python Backend/backtester.py --symbol BTCUSDT
# Requerido: Sharpe ≥ 1.0, Max DD < -40%

# 3. Code review completado
# GitHub review approval de mínimo 2 personas

# 4. Variables de entorno configuradas
cp Backend/.env.example Backend/.env
# Rellenar: API_KEY, API_SECRET, EMAIL, etc.

# 5. Base de datos creada
sqlite3 storage/trades.db ".tables"

# 6. Logs creados
mkdir -p storage/logs
touch storage/logs/mirage.log

# 7. Deploy a VPS (ejemplo con systemd)
ssh user@vps.example.com << 'EOF'
cd /opt/mirage-trading
git pull origin main
pip install -r requirements.txt
systemctl restart mirage-trading
journalctl -u mirage-trading -f
EOF
```

### Monitoreo en Producción

```bash
# 1. Logs en vivo
tail -f storage/logs/mirage.log | grep ERROR

# 2. Performance del bot
sqlite3 storage/trades.db "SELECT AVG(pnl_usdt), COUNT(*) FROM trades WHERE date(timestamp) = date('now')"

# 3. Alertas (email/SMS)
# Si PnL daily < -5% → Pausar bot automáticamente

# 4. Dashboard en vivo
open http://localhost:5173  # Ver estado real-time
```

---

## 📊 Métricas de Éxito por Sprint

| Sprint | Métrica | Target |
|--------|---------|--------|
| 3 | Sharpe Ratio | ≥ 1.0 |
| 3 | Max Drawdown | < -40% |
| 3 | Profit Factor | ≥ 1.5 |
| 4 | Uptime | ≥ 99% |
| 4 | Test Coverage | ≥ 85% |
| 5 | Multi-pair Ops | 5 pares |
| 5 | Total Risk | ≤ 5% balance |
| 6 | Sharpe Ratio | ≥ 1.5 |

---

## 🆘 Troubleshooting

### "CSV es demasiado lento"
```bash
# Solución: Migrar a SQLite (Sprint 4, Task 3)
python Backend/migrate_csv_to_db.py
```

### "ML model no convergió"
```bash
# Solución: Aumentar MIN_TRADES_FOR_AI a 100
# Esperar más operaciones en paper trading
```

### "Binance API timeout"
```bash
# Solución: Implementar reconexión automática (Sprint 4, Task 4)
# Aumentar timeout: client.timeout = 60000
```

### "WebSocket se desconecta"
```bash
# Solución: Auto-reconnect con exponential backoff
# Ver Backend/websocket_handler.py
```

---

## 📝 Documentación Links

- **Análisis del Proyecto:** `analisis_mirage_trading.md`
- **Plan de Sprints:** `SPRINTS_MIRAGE_TRADING.md`
- **Ejemplos de Código:** `CODIGO_EJEMPLOS_SPRINTS.md`
- **Esta Guía:** `GUIA_EJECUCION.md`

---

**Última actualización:** Mayo 2026
**Estado:** Listo para ejecutar
**Tiempo total:** 10-15 semanas (2.5-3.5 meses)

¡Éxito con tu bot de trading! 🚀
