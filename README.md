# 📊 ANÁLISIS DETALLADO: Mirage Trading

## 🎯 Resumen Ejecutivo

**Mirage Trading** es un bot de trading algorítmico avanzado para futuros de criptomonedas (Binance Futures) que combina:
- **Machine Learning** (Random Forest) como sistema de predicción
- **9 estrategias técnicas** diferentes integradas
- **Paper Trading** para simulación segura
- **Dashboard en tiempo real** para monitoreo
- Arquitectura modular Python + React

**Estado:** Sprint 2 en progreso (Gestión de riesgo y retroalimentación)

---

## 📁 Arquitectura del Proyecto

```
chaguan17-mirage-trading/
├── Backend/          → Motor de trading (Python + FastAPI)
├── Frontend/         → Dashboard (React + Vite)
└── Config files      → Dependencias y configuración
```

### Stack Tecnológico

**Backend:**
- `fastapi` - API REST
- `ccxt` - Conexión con Binance
- `sklearn` - Machine Learning (Random Forest)
- `pandas` - Manipulación de datos
- `numpy` - Cálculos numéricos

**Frontend:**
- `React 18+` + `React Router DOM 7.15`
- `Vite` - Build tool
- `WebSockets` - Datos en tiempo real

---

## 🧠 Componentes Clave del Backend

### 1. **api.py** - Servidor FastAPI
**Responsabilidades:**
- Endpoint `/api/dashboard` → Datos para el dashboard (PnL, operaciones, métricas)
- Endpoint `/api/config` → Lectura/escritura de configuración
- Middleware CORS configurado
- Gestión de storage (JSON + CSV)

**Flujo de datos:**
1. Lee `live_state.json` (estado del bot)
2. Lee `trade_history.csv` (historial de operaciones)
3. Calcula métricas acumulativas
4. Devuelve al frontend

**Configuración por defecto:**
```json
{
  "TIMEFRAME": "1m",
  "PAPER_BALANCE": 1000 USDT,
  "RISK_PER_TRADE": 2%,
  "MIN_CONFIDENCE": 65%,
  "LEVERAGE": 10x
}
```

### 2. **binance_api.py** - Wrapper de Binance
**Clase: `MirageBinance`**
- Abstracción de CCXT para Binance Futures
- Soporta **paper trading** (simulación con balance ficticio)
- Métodos clave:
  - `check_connection()` → Sincroniza reloj con Binance
  - `get_balance()` → Balance actual
  - `get_historical_data()` → Obtiene OHLCV (candles)

**Características de seguridad:**
- Manejo automático de RecvWindow (sincronización de reloj)
- Rate limiting habilitado
- Modo sandbox configurable

### 3. **brain.py** - Sistema de IA
**Clase: `MirageBrain`**

El corazón del bot. Contiene:

**Estrategias integradas:**
1. **Trend Follower** - Sigue tendencias alcistas/bajistas
2. **Mean Reversion** - Compra en mínimos, vende en máximos
3. **Breakout Logic** - Entrada en roturas de niveles clave
4. **SMC Structure** - Smart Money Concepts (Support/Resistance)
5. **VWAP Method** - Volume Weighted Average Price
6. **Liquidity Zones** - Zonas de liquidez para órdenes
7. **OrderFlow** - Análisis de flujo de órdenes
8. **Wyckoff Method** - Acumulación/distribución
9. **BTC Correlation** - Correlación con Bitcoin

**Modelo ML:**
- Random Forest Classifier
- Requisitos: Mínimo 5 trades para entrenar
- Features: RSI, EMA, ATR + salidas de estrategias

### 4. **data_engine.py** - Motor de Datos
Extrae features técnicos de los precios:
- RSI (Índice de Fuerza Relativa)
- EMA (Media Móvil Exponencial)
- ATR (Average True Range - volatilidad)

### 5. **risk_manager.py** - Gestión de Riesgo
- **Position Sizing dinámico** basado en % de capital
- **Stop Loss** automático
- **Take Profit** múltiple
- **Scale-In** (promediado) para mejorar breakeven

### 6. **executor.py** - Ejecutor de Órdenes
- Abre/cierra posiciones
- Gestiona órdenes limitadas y por mercado
- Registra operaciones

### 7. **tracker.py** - Feedback Loop
Registra en CSV:
- Timestamp, par, lado (LONG/SHORT)
- Entrada, salida, PnL
- Etiquetas para reentrenamiento de IA

### 8. **config.py** - Configuración
Carga variables de entorno (`.env`):
- API keys de Binance
- Parámetros del bot

---

## 💻 Frontend - Dashboard React

### Componentes principales:

**Dashboard Component**
- **Cards de KPIs:** PnL total, Win Rate, Operaciones activas
- **Gráfica de PnL acumulado** (últimas 30 operaciones)
- **Tabla de historial** de operaciones
- **Precios en vivo** de BTC, ETH, BNB (WebSocket)

**SettingsView Component**
- Panel para modificar configuración
- Dropdown para seleccionar estrategia
- Sliders para ajustar parámetros

**Tema personalizado:**
- Colores acorde al modo claro/oscuro
- Paleta: Púrpura (#aa3bff), blanco/gris
- Responsive (mobile + desktop)

---

## 🚀 Estado del Desarrollo

### ✅ SPRINT 1: COMPLETADO
- [x] Conexión blindada a Binance API
- [x] Paper Trading (simulación)
- [x] Data Engine (features)
- [x] Brain base (Random Forest)

### 🔄 SPRINT 2: EN PROCESO
- [x] Risk Manager (Position Sizing)
- [x] Scale-In logic
- [x] Hot-Reloading (cargar código sin reiniciar)
- [x] Trade Tracker + Dashboard
- ⏳ Próximas: Optimización, backtesting

---

## 🎲 Flujo de Operación

```
[Binance API] → [Data Engine] → [Brain (9 estrategias)] 
                                    ↓
                                [Voting System]
                                    ↓
                            [Risk Manager]
                                    ↓
                            [Executor] → [Tracker (CSV)]
                                    ↓
                                [Dashboard]
```

1. **Data Engine** obtiene datos del mercado (OHLCV)
2. **Brain** evalúa con 9 estrategias
3. Cada estrategia genera señal (BUY/SELL/HOLD)
4. **Voting system** calcula consenso (confidence)
5. **Risk Manager** valida riesgo
6. **Executor** envía orden a Binance
7. **Tracker** registra en CSV
8. **Dashboard** muestra en tiempo real

---

## ⚙️ Configuración Recomendada

**Para Paper Trading (TEST):**
```
PAPER_BALANCE: 1000 USDT
LEVERAGE: 5x
RISK_PER_TRADE: 1%
TIMEFRAME: 5m (volatilidad moderada)
```

**Para Trading Real (PRODUCCIÓN):**
```
LEVERAGE: 2-3x (máximo conservador)
RISK_PER_TRADE: 0.5-1%
TIMEFRAME: 15m-1h (menos ruido)
MIN_CONFIDENCE: 75% (más selectivo)
```

---

## ⚠️ Fortalezas del Proyecto

1. **Arquitectura modular** - Fácil de expandir
2. **9 estrategias diversificadas** - Reduce sesgo
3. **Machine Learning** - Adaptación dinámica
4. **Paper Trading** - Pruebas sin riesgo real
5. **Dashboard en vivo** - Monitoreo en tiempo real
6. **Gestión de riesgo avanzada** - Scale-in, stop-loss dinámico
7. **Logging completo** - Trazabilidad total

---

## 🚨 Áreas de Mejora / Riesgos

### Críticas:
1. **Sin backtesting formal** 
   - No hay validación histórica de estrategias
   - Riesgo: Estrategias que funcionan en "dirección actual" pueden fallar

2. **Modelo ML subentrenado**
   - Requiere solo 5 trades para entrenar (muy poco)
   - Risk: Overfitting severo

3. **Sin diversificación de pares**
   - Solo opera un par a la vez (?)
   - Riesgo concentrado

4. **Leverage configurable pero no limitado**
   - 10x en producción es muy alto
   - Risk: Liquidación rápida

### Técnicas:
5. **API Key en .env (buena práctica)**
   - Pero sin rotación de keys
   
6. **Sincronización de reloj manual**
   - CCXT puede manejarlo automáticamente

7. **CSV sin base de datos**
   - Performance puede degradarse con 10k+ operaciones

---

## 💡 Recomendaciones

### INMEDIATAS (Antes de producción):
1. **Implementar Backtesting**
   ```
   Test histórico 2020-2024
   Walkaorward analysis
   Máximo drawdown < 20%
   Sharpe ratio > 1.0
   ```

2. **Aumentar MIN_TRADES_FOR_AI a 100**
   - Mejor generalización del modelo

3. **Limitar LEVERAGE a 3x máximo**
   - Seguridad

4. **Implementar database (SQLite/PostgreSQL)**
   - Para track de 1000+ operaciones

### CORTO PLAZO (1-2 sprints):
5. **Stop-loss obligatorio** 
   - No permitir operaciones sin exit plan

6. **Logging de errores de API**
   - Reconexión automática

7. **Metrics mejoradas**
   - Sharpe Ratio, Calmar Ratio, Profit Factor

### MEDIANO PLAZO (Sprint 3-4):
8. **Multi-pair support**
   - Diversificación en 5+ pares

9. **Dynamic parameter optimization**
   - Ajuste automático de timeframe según volatilidad

10. **WebSocket para datos en vivo**
    - En lugar de polling cada 3s

---

## 📊 Métricas a Monitorear

**Dashboard debería mostrar:**
- ✅ PnL Total
- ✅ Win Rate
- ⚠️ Sharpe Ratio (FALTA)
- ⚠️ Máximo Drawdown (FALTA)
- ⚠️ Factor de Ganancia (Profit Factor) (FALTA)
- ⚠️ Promedio de ganancia vs pérdida (FALTA)

---

## 🔐 Seguridad

**Bien implementado:**
- Paper trading default ✅
- Rate limiting en CCXT ✅
- CORS configurado ✅
- API keys no en código ✅

**A mejorar:**
- Validación de entrada en API endpoints
- Timeout en conexión Binance
- Alertas de error crítico

---

## 🎓 Conclusión

**Mirage Trading** es un **proyecto sólido y bien estructurado** para un trading bot educativo/experimental. 

**Fortalezas:**
- Código limpio y modular
- Buenas prácticas (separation of concerns)
- Múltiples estrategias combinadas
- UI clara

**Punto crítico:** Necesita **backtesting riguroso** antes de operar en real. La falta de validación histórica es el principal riesgo.

**Recomendación final:**
```
⚠️ USAR SOLO EN PAPER TRADING hasta completar:
1. Backtesting 2023-2024
2. Min confidence ajustado a 75%+
3. Leverage limitado a 2x
4. 100+ trades en paper (validación)
5. Database para operaciones
```

**Potencial:** Con estas mejoras, podría ser una herramienta de trading viable.

---

**Análisis realizado:** Mayo 2026
**Proyecto:** Mirage Trading (chaguan17)
