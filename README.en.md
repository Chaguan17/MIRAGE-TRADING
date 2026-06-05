# MIRAGE TRADING

> Autonomous algorithmic trading bot for cryptocurrency futures

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST%20%2B%20WebSocket-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![ML](https://img.shields.io/badge/ML-Random%20Forest-orange?style=flat-square)](https://scikit-learn.org)
[![Binance](https://img.shields.io/badge/Exchange-Binance%20Futures-F0B90B?style=flat-square)](https://binance.com)
[![Status](https://img.shields.io/badge/Status-Paper%20Trading%20Active-brightgreen?style=flat-square)]()

---

##  Overview

**Mirage Trading** is a fully autonomous algorithmic trading system operating on **Binance Futures**. It combines **9 technical strategies** with an **adaptive Machine Learning engine** that learns from every trade and dynamically manages risk based on real-time available capital.

The system operates without human intervention. It analyzes the market, makes decisions, manages open positions, and automatically retrains every night.

### Real Paper Trading Results

| Metric | Value |
|--------|-------|
| Win Rate | **60.7%** |
| Profit Factor | **1.52** |
| Trades executed | **1,016+** |
| Max winning streak | **30 consecutive** |
| Pairs traded simultaneously | **BTC · ETH · BNB** |

### Main Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 · FastAPI · SQLite · ccxt |
| Machine Learning | scikit-learn (Random Forest) · joblib |
| Technical Analysis | pandas · pandas-ta · numpy |
| Frontend | React 18 · Recharts · Native WebSocket |
| Security | python-dotenv · SHA-256 checksum · atomic writes |

---

##  Architecture

### Decision Flow

```
Binance OHLCV
      │
      ▼
Data Engine ── 20+ features (RSI, EMA, ATR, BB, VWAP, Delta, SMC)
      │
      ▼
BRAIN — 3 Signal Layers
  BASIC (x1.0)       STRUCTURE (x1.2)     CONTEXT (x0.8)
  Trend Follower     SMC Structure         OrderFlow
  Mean Reversion     VWAP Method           Wyckoff
  Breakout Logic     Liquidity Zones       BTC Correlation
      │
      ▼
Consensus Engine (weighted voting + conflict detection)
      │
      ▼
Veto System
  · BTC Trend Veto
  · Dynamic RSI Veto (volatility-adjusted thresholds)
  · AI Probability Veto (blocks if success prob. < 40%)
      │
      ▼
ML Engine — Random Forest
  ai_weight grows gradually as trade history accumulates
      │
      ▼
Adaptive Risk Manager
  risk auto-adjusted to current available capital
      │
      ▼
Executor DRY_RUN / REAL + SQLite Tracker + Live Dashboard
```

### File Structure

```
MIRAGE-TRADING/
├── Backend/
│   ├── main.py              ← Main loop orchestrator
│   ├── config.py            ← Single source of truth
│   ├── api.py               ← FastAPI REST + WebSocket broadcaster
│   ├── binance_api.py       ← ccxt wrapper (paper + real)
│   ├── data_engine.py       ← Feature engineering (20+ indicators)
│   ├── risk_manager.py      ← Adaptive risk management
│   ├── tracker.py           ← SQLite persistence with integrity
│   ├── executor.py          ← Order execution (DRY_RUN / REAL)
│   ├── brain/
│   │   ├── __init__.py         ← MirageBrain (orchestrator)
│   │   ├── ml_engine.py        ← Random Forest + SHA-256 integrity
│   │   ├── signal_engine.py    ← Lazy evaluation of 9 strategies
│   │   ├── consensus_engine.py ← Weighted layer voting
│   │   ├── veto_engine.py      ← Market and AI filters
│   │   ├── trainer.py          ← Nightly walk-forward retraining
│   │   └── feature_engine.py   ← StandardScaler feature scaling
│   └── methods/             ← 9 independent technical strategies
│       ├── trend_follower.py · mean_reversion.py · breakout_logic.py
│       ├── smc_structure.py · vwap_method.py · liquidity_zones.py
│       └── orderflow.py · wyckoff.py · btc_correlation.py
└── Frontend/mirage-dashboard/src/
    ├── App.jsx              ← Router + state + Binance WebSocket
    ├── PerformanceView.jsx  ← Sharpe, Profit Factor, Drawdown, WR
    └── SettingsView.jsx     ← Dynamic config from JSON metadata
```

---

##  Technical Implementation

### 1. Multi-Layer Consensus with Conflict Detection

```python
# If two opposing signals compete too closely, the layer returns None
# instead of emitting a weak, unreliable signal
if v_min > 0 and (v_min / v_max) > LAYER_CONFLICT_THRESHOLD:
    return None, 0, 'Layer Conflict'

# Final weighted vote across the 3 layers
for action, conf, weight in layers:
    if action is not None:
        final_votes[action] += conf * weight
```

### 2. ML with Gradual Learning Curve

The model does not interfere until it has enough experience. Its weight grows proportionally to the accumulated history:

```python
def calculate_ai_weight(self, trades_seen):
    if trades_seen < MIN_TRADES_FOR_AI:
        return 0.0  # No history → pure technical signals only
    ratio = min(1.0, (trades_seen - MIN_TRADES_FOR_AI) / LEARNING_STEPS)
    return ratio * AI_MAX_WEIGHT  # Maximum 40% influence

# Final confidence: weighted blend of technical + AI
confidence = (tech_conf * (1 - ai_weight)) + (ai_conf * ai_weight)
```

### 3. Capital-Adaptive Risk Management

```python
ratio = current_balance / initial_balance

if ratio < 0.85:    # Capital dropped → minimum safety risk
    risk = max(FLOOR, base_risk * ratio)

elif ratio > 1.20:  # Capital grown → scale conservatively
    risk = min(CEIL, base_risk * (1 + (ratio - 1) * 0.3))
```

Automatic multi-level stop system:
- **Breakeven**: SL moves to entry price when 45% of the way to TP
- **Trailing Stop**: follows price at 0.8% distance once activated
- **DCA Scale-In**: up to 3 entries at predefined ATR levels

### 4. Atomic ML Model Persistence

```python
def _safe_save(self, model, path):
    joblib.dump(model, path + ".tmp")         # 1. Write to temp file
    checksum = self._generate_checksum(path + ".tmp")
    with open(path + ".sha256", "w") as f:
        f.write(checksum)                      # 2. Store SHA-256 checksum
    os.replace(path + ".tmp", path)           # 3. Atomic replacement
    # On corruption detected → auto-restores from backup
```

### 5. WebSocket with Exponential Backoff (Frontend)

```javascript
ws.onclose = () => {
    const delay = Math.min(reconnectDelay, 30000);
    reconnectDelay = delay * 2;               // Exponential backoff
    setTimeout(() => connectWebSocket(pairs), delay);
};
```

### 6. Hot-Reload Without Interrupting Active Trades

```python
if has_updates:
    importlib.reload(config)
    importlib.reload(risk_manager)
    # Open trades continue uninterrupted — only config is updated
```

### 7. Dual-Mode Executor

```python
DRY_RUN = True  # Set to False to activate real money

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
cp .env.example .env          # Add BINANCE_API_KEY + BINANCE_API_SECRET
python main.py                # Bot starts in paper trading mode by default

# API (separate terminal)
uvicorn api:app --reload --port 8000

# Frontend (separate terminal)
cd Frontend/mirage-dashboard
npm install && npm run dev    # http://localhost:5173

# Tests
cd Backend && pytest tests/ -v
```

---

## Configuration

```jsonc
// Paper Trading (current)
{
  "TIMEFRAME": "5m",
  "LEVERAGE": 5,
  "RISK_PER_TRADE": 0.01,        // 1% per trade
  "MIN_CONFIDENCE": 0.70,         // 70% minimum confidence threshold
  "BREAKEVEN_ACTIVATION": 0.45,
  "TRAILING_STOP_DISTANCE": 0.008
}

// Real trading — conservative (next step)
{
  "TIMEFRAME": "15m",
  "LEVERAGE": 3,
  "RISK_PER_TRADE": 0.005,        // 0.5% per trade
  "MIN_CONFIDENCE": 0.75
}
```

---

## Project Status

| Component | Status |
|-----------|--------|
| 9 technical strategies | ✅ Complete |
| Adaptive ML + nightly retraining | ✅ Complete |
| Capital-adaptive Risk Manager | ✅ Complete |
| Real-time dashboard (REST + WebSocket) | ✅ Complete |
| Stable Paper Trading with real metrics | ✅ Active |
| Real execution (DRY RUN enabled) | ✅ Ready to activate |
| 24/7 hosting | ⏳ Next step |

---

*Jesus Gomez Chaguan · June 2026*
