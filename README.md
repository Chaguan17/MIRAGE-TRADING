# MIRAGE TRADING

> Bot de trading algorítmico autónomo para futuros de criptomonedas

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST%20%2B%20WebSocket-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![ML](https://img.shields.io/badge/ML-Random%20Forest-orange?style=flat-square)](https://scikit-learn.org)
[![Binance](https://img.shields.io/badge/Exchange-Binance%20Futures-F0B90B?style=flat-square)](https://binance.com)
[![Status](https://img.shields.io/badge/Estado-Paper%20Trading%20Activo-brightgreen?style=flat-square)]()

---

## MACRO — Visión General

**Mirage Trading** es un sistema completo de trading algorítmico que opera en **Binance Futures** de forma autónoma. Combina **9 estrategias técnicas** con un motor de **Machine Learning adaptativo** que aprende de cada operación, gestionando el riesgo de forma dinámica según el capital disponible en tiempo real.

El sistema no depende de intervención humana. Analiza el mercado, toma decisiones, gestiona posiciones abiertas y se reentrena automáticamente cada noche.

### Resultados reales en Paper Trading

| Métrica | Valor |
|---------|-------|
| Win Rate | **60.7%** |
| Profit Factor | **1.52** |
| Operaciones ejecutadas | **1,016+** |
| Racha ganadora máxima | **30 consecutivas** |
| Pares operados simultáneamente | **BTC · ETH · BNB** |

### Stack principal

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11 · FastAPI · SQLite · ccxt |
| Machine Learning | scikit-learn (Random Forest) · joblib |
| Análisis técnico | pandas · pandas-ta · numpy |
| Frontend | React 18 · Recharts · WebSocket nativo |
| Seguridad | python-dotenv · SHA-256 checksum · atomic writes |

---

## MESO — Arquitectura

### Flujo de decisión

```
Binance OHLCV
      │
      ▼
Data Engine ── 20+ features (RSI, EMA, ATR, BB, VWAP, Delta, SMC)
      │
      ▼
BRAIN — 3 Capas de Señales
  BÁSICA (x1.0)      ESTRUCTURA (x1.2)    CONTEXTO (x0.8)
  Trend Follower     SMC Structure         OrderFlow
  Mean Reversion     VWAP Method           Wyckoff
  Breakout Logic     Liquidity Zones       BTC Correlation
      │
      ▼
Consensus Engine (votación ponderada + detección de conflictos)
      │
      ▼
Sistema de Vetos
  · BTC Trend Veto
  · RSI Dinámico (ajustado por volatilidad)
  · AI Probability Veto (bloquea si prob. < 40%)
      │
      ▼
ML Engine — Random Forest
  ai_weight crece gradualmente con el historial acumulado
      │
      ▼
Risk Manager Adaptativo
  riesgo ajustado automáticamente al capital disponible
      │
      ▼
Executor DRY_RUN / REAL + Tracker SQLite + Dashboard Live
```

### Estructura de archivos

```
MIRAGE-TRADING/
├── Backend/
│   ├── main.py              ← Orquestador del loop principal
│   ├── config.py            ← Fuente única de verdad
│   ├── api.py               ← FastAPI REST + WebSocket broadcaster
│   ├── binance_api.py       ← Wrapper ccxt (paper + real)
│   ├── data_engine.py       ← Feature engineering (20+ indicadores)
│   ├── risk_manager.py      ← Gestión de riesgo adaptativa
│   ├── tracker.py           ← Persistencia SQLite con integridad
│   ├── executor.py          ← Ejecución órdenes (DRY_RUN / REAL)
│   ├── brain/
│   │   ├── __init__.py         ← MirageBrain (orquestador)
│   │   ├── ml_engine.py        ← Random Forest + integridad SHA-256
│   │   ├── signal_engine.py    ← Evaluación lazy de 9 estrategias
│   │   ├── consensus_engine.py ← Votación ponderada por capas
│   │   ├── veto_engine.py      ← Filtros de mercado e IA
│   │   ├── trainer.py          ← Reentrenamiento nocturno walk-forward
│   │   └── feature_engine.py   ← Escalado StandardScaler
│   └── methods/             ← 9 estrategias técnicas independientes
│       ├── trend_follower.py · mean_reversion.py · breakout_logic.py
│       ├── smc_structure.py · vwap_method.py · liquidity_zones.py
│       └── orderflow.py · wyckoff.py · btc_correlation.py
└── Frontend/mirage-dashboard/src/
    ├── App.jsx              ← Router + estado + WebSocket Binance
    ├── PerformanceView.jsx  ← Sharpe, Profit Factor, Drawdown, WR
    └── SettingsView.jsx     ← Config dinámica desde metadatos JSON
```

---

## MICRO — Implementación Técnica

### 1. Consenso Multi-Capa con Detección de Conflictos

```python
# Si dos señales opuestas compiten demasiado, la capa devuelve None
# en lugar de emitir una señal débil e imprecisa
if v_min > 0 and (v_min / v_max) > LAYER_CONFLICT_THRESHOLD:
    return None, 0, 'Layer Conflict'

# Votación final ponderada entre las 3 capas
for action, conf, weight in layers:
    if action is not None:
        final_votes[action] += conf * weight
```

### 2. ML con Curva de Aprendizaje Gradual

El modelo no interfiere hasta tener experiencia suficiente. Su peso crece proporcionalmente al historial:

```python
def calculate_ai_weight(self, trades_seen):
    if trades_seen < MIN_TRADES_FOR_AI:
        return 0.0  # Sin historial → solo señales técnicas
    ratio = min(1.0, (trades_seen - MIN_TRADES_FOR_AI) / LEARNING_STEPS)
    return ratio * AI_MAX_WEIGHT  # Máximo 40% de influencia

# Confianza final: combinación ponderada técnico + IA
confidence = (tech_conf * (1 - ai_weight)) + (ai_conf * ai_weight)
```

### 3. Riesgo Adaptativo al Capital

```python
ratio = balance_actual / balance_inicial

if ratio < 0.85:    # Capital caído → riesgo mínimo de seguridad
    risk = max(FLOOR, base_risk * ratio)

elif ratio > 1.20:  # Capital crecido → escala conservadoramente
    risk = min(CEIL, base_risk * (1 + (ratio - 1) * 0.3))
```

Sistema de stops automático:
- **Breakeven**: SL se mueve al entry cuando lleva 45% del camino al TP
- **Trailing Stop**: sigue el precio al 0.8% de distancia tras activarse
- **DCA Scale-In**: hasta 3 entradas en niveles ATR predefinidos

### 4. Persistencia Atómica de Modelos ML

```python
def _safe_save(self, model, path):
    joblib.dump(model, path + ".tmp")         # 1. Escribir temporal
    checksum = self._generate_checksum(path + ".tmp")
    with open(path + ".sha256", "w") as f:
        f.write(checksum)                      # 2. Guardar checksum
    os.replace(path + ".tmp", path)           # 3. Reemplazo atómico
    # Si el archivo se corrompe → restaura desde backup automáticamente
```

### 5. WebSocket con Backoff Exponencial (Frontend)

```javascript
ws.onclose = () => {
    const delay = Math.min(reconnectDelay, 30000);
    reconnectDelay = delay * 2;               // Backoff exponencial
    setTimeout(() => connectWebSocket(pairs), delay);
};
```

### 6. Hot-Reload sin Interrumpir Trades Activos

```python
if has_updates:
    importlib.reload(config)
    importlib.reload(risk_manager)
    # Los trades abiertos continúan — solo se actualiza la configuración
```

### 7. Executor Dual Mode

```python
DRY_RUN = True  # Cambiar a False para dinero real

def execute_trade(client, symbol, action, size, sl=None, tp=None):
    if DRY_RUN:
        logger.info(f"[DRY RUN] {action} {size} {symbol} | SL={sl} | TP={tp}")
        return {"dry_run": True}

    order = client.create_order(symbol, side, 'MARKET', quantity=size)
    client.create_order(symbol, sl_side, 'STOP_MARKET', stopPrice=sl, closePosition=True)
    client.create_order(symbol, tp_side, 'TAKE_PROFIT_MARKET', stopPrice=tp, closePosition=True)
    return order
```

---

## Quick Start

```bash
# Backend
cd Backend
pip install -r requirements.txt
cp .env.example .env          # BINANCE_API_KEY + BINANCE_API_SECRET
python main.py                # Bot arranca en paper trading por defecto

# API (terminal separada)
uvicorn api:app --reload --port 8000

# Frontend (terminal separada)
cd Frontend/mirage-dashboard
npm install && npm run dev    # http://localhost:5173

# Tests
cd Backend && pytest tests/ -v
```

---

## Configuración

```jsonc
// Paper Trading (configuración actual)
{
  "TIMEFRAME": "5m",
  "LEVERAGE": 5,
  "RISK_PER_TRADE": 0.01,        // 1% por operación
  "MIN_CONFIDENCE": 0.70,         // 70% confianza mínima
  "BREAKEVEN_ACTIVATION": 0.45,
  "TRAILING_STOP_DISTANCE": 0.008
}

// Real — conservador (próximo paso)
{
  "TIMEFRAME": "15m",
  "LEVERAGE": 3,
  "RISK_PER_TRADE": 0.005,        // 0.5% por operación
  "MIN_CONFIDENCE": 0.75
}
```

---

## Estado del Proyecto

| Componente | Estado |
|-----------|--------|
| 9 estrategias técnicas | ✅ Completo |
| ML adaptativo + reentrenamiento nocturno | ✅ Completo |
| Risk Manager adaptativo al capital | ✅ Completo |
| Dashboard en tiempo real (REST + WebSocket) | ✅ Completo |
| Paper Trading estable con métricas reales | ✅ Activo |
| Ejecución real (DRY RUN activado) | ✅ Listo para activar |
| Hosting 24/7 | ⏳ Próximo paso |

---

*Jesus Gomez Chaguan · Junio 2026*
