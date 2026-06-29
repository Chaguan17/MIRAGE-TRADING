# MIRAGE TRADING

> Bot de trading algorítmico autónomo para futuros de criptomonedas

**Mirage Trading** es un bot de trading algorítmico avanzado para futuros de criptomonedas (Binance Futures) que combina:
- **Machine Learning Ensemble** (Random Forest + XGBoost) como sistema de predicción.
- **9 estrategias técnicas** diferentes integradas.
- **Datos Alternativos** (Funding Rate, Fear & Greed Index).
- **Paper Trading** para simulación segura.
- **Dashboard en tiempo real** para monitoreo (TradingView charts).
- **Base de Datos SQLite** para persistencia e integridad.
- **WebSockets Nativos** (Latencia cero)
- Arquitectura modular Python + React.

**Estado:** Sprint 4 Completado (Evolución Institucional de la IA y Escalabilidad)

---

##  Visión General

**Mirage Trading** es un sistema completo de trading algorítmico que opera en **Binance Futures** de forma autónoma. Combina **9 estrategias técnicas** con un motor de **Machine Learning adaptativo** que aprende de cada operación, gestionando el riesgo de forma dinámica según el capital disponible en tiempo real.

El sistema no depende de intervención humana. Analiza el mercado, toma decisiones, gestiona posiciones abiertas y se reentrena automáticamente cada noche.

**Backend:**
- `fastapi` - API REST
- `ccxt` - Conexión con Binance
- `websocket-client` - Binance Streams
- `sklearn` & `xgboost` - Machine Learning Ensemble
- `optuna` - Algoritmos Genéticos de Auto-Optimización
- `pandas` / `numpy` - Manipulación de datos
- `sqlite3` - Base de datos

**Frontend:**
- `React 18+` + `React Router DOM`
- `Vite` - Build tool
- `lightweight-charts` - Gráficas de TradingView interactivas
- `WebSockets` - Datos en tiempo real

### Stack principal

## 🧠 Componentes Clave del Backend

### 1. **api.py** - Servidor FastAPI
**Responsabilidades:**
- Servir datos al Frontend vía SQLite y WebSockets.
- Endpoint bidireccional `/api/commands` (Ej. Botón del Pánico).

### 2. **market_stream.py** - Gestor de WebSockets (NUEVO SPRINT 2/4)
- Mantiene conexión viva con `fstream.binance.com`.
- Descarga velas, Funding Rate (`@markPrice`) y Open Interest en vivo.
- Reduce el consumo de la API REST en un 99%.

### 3. **brain.py & ml_engine.py** - Sistema de IA Híbrido (NUEVO SPRINT 4)
El corazón del bot ha evolucionado de un simple modelo a un **Ensamble Institucional**:
- **VotingClassifier:** Combina Random Forest y XGBoost. Ambos modelos deben dar señal de compra simultáneamente para entrar al mercado.
- **Optuna Optimizer:** Script dedicado (`optimizer.py`) que usa algoritmos genéticos los fines de semana para encontrar los hiperparámetros perfectos.

### 4. **data_engine.py** - Motor de Datos Aumentado
Aparte del análisis técnico clásico (RSI, EMA, ATR, MACD, Orderflow, Wyckoff), ahora inyecta **Datos Alternativos**:
- **Fear & Greed Index:** Sentimiento global desde `alternative.me`.
- **Funding Rate:** Tasa de financiación extraída de WebSockets.

### 5. **risk_manager.py** - Gestión de Riesgo
- **Position Sizing dinámico** basado en % de capital.
- **Stop Loss** dinámico (basado en ATR) y Breakeven automático.
- **Scale-In (DCA) Inteligente**: Solo promedia si la IA lo aprueba.
- **Martingala limitable**.

### 6. **executor.py & tracker.py** - Ejecutor y Registro (SQLite)
- Abre/cierra posiciones reales o paper.
- Registra todo transaccionalmente en `mirage_trading.db`.

---

## 💻 Frontend - Dashboard React

### Componentes principales:

**Dashboard Component**
- **TradingChart (NUEVO SPRINT 3):** Gráfica interactiva de TradingView (`lightweight-charts`) que dibuja tus puntos de entrada, SL y TP explícitamente en el gráfico. Escala dinámicamente según los decimales de la criptomoneda.
- **Panel Bidireccional:** Botón de "PANIC SELL" para forzar el cierre de toda la flota.

**SettingsView Component**
- Panel de cristal (Glassmorphism) para encender/apagar estrategias dinámicamente y ajustar modificadores (ej. Multiplicador de ATR) sin tocar código.

---

## 🚀 Estado del Desarrollo

### ✅ SPRINT 1, 2 & 3: COMPLETADO
- [x] Conexión blindada a Binance API (REST y WebSockets)
- [x] Paper Trading (simulación)
- [x] Inteligencia de Mercado (Veto Engine, Multi-TF 15m/1h/4h)
- [x] Risk Manager Avanzado (ATR Trailing Stop, DCA Inteligente)
- [x] Migración Completa a SQLite (`live_state` y `history`)
- [x] UI/UX Profesional (TradingView, Botón de Pánico, Ajustes Dinámicos)

### ✅ SPRINT 4: COMPLETADO
- [x] Ensamble IA (XGBoost + Random Forest en Voting Classifier)
- [x] Ingesta de Datos Alternativos (Funding Rate, Fear & Greed Index)
- [x] Script de Auto-Optimización (Optuna)

---

## 🎲 Flujo de Operación

```
[Binance Streams] + [Alternative Data] 
            ↓
       [Data Engine] 
            ↓
  [Brain (9 estrategias)] 
            ↓
 [Voting Classifier (RF + XGB)]
            ↓
      [Risk Manager]
            ↓
   [Executor] → [SQLite]
            ↓
  [TradingView Dashboard]
```

---

## 🎓 Conclusión

**Mirage Trading** ha superado su fase experimental y cuenta ahora con un esqueleto **de grado institucional**. Las reducciones drásticas en latencia (WebSockets), el salto en robustez predictiva (XGBoost + Optuna + F&G Index) y su persistencia segura (SQLite) lo convierten en un algoritmo formidable.

**Próximos pasos recomendados:**
- Dejar que el bot corra en Paper Trading (Live) por semanas para generar un dataset orgánico.
- Ejecutar `optimizer.py` los domingos para afilar las neuronas.
- (Opcional) Desarrollar módulo de Backtesting Formal.
