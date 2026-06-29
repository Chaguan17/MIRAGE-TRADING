# MIRAGE TRADING

> Autonomous algorithmic trading bot for cryptocurrency futures

**Mirage Trading** is an advanced algorithmic trading bot for cryptocurrency futures (Binance Futures) that combines:
- **Machine Learning Ensemble** (Random Forest + XGBoost) as a prediction system.
- **9 integrated technical strategies**.
- **Alternative Data** (Funding Rate, Fear & Greed Index).
- **Paper Trading** for safe simulation.
- **Real-time Dashboard** for monitoring (TradingView charts).
- **SQLite Database** for persistence and data integrity.
- **Native WebSockets** (Zero latency).
- Modular Python + React architecture.

**Status:** Sprint 4 Completed (Institutional AI Evolution and Scalability)

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

**Backend:**
- `fastapi` - REST API
- `ccxt` - Binance REST Connection
- `websocket-client` - Binance Streams
- `sklearn` & `xgboost` - Machine Learning Ensemble
- `optuna` - Auto-Optimization Genetic Algorithms
- `sqlite3` - Robust Data Storage
- `pandas` / `numpy` - Data processing

**Frontend:**
- `React 18+`
- `lightweight-charts` - TradingView financial charts
- `WebSockets` - Real-time market data

---

## 🧠 Core Components

### 1. **Mirage Brain & ML Engine (AI System)**
The heart of the bot. It evaluates market conditions through three layers:
- **Consensus Voting**: Aggregates signals from 9 strategies (Trend, SMC, Wyckoff, OrderFlow, etc.).
- **Ensemble Classifier (NEW)**: A `VotingClassifier` combines `RandomForest` and `XGBoost`. Both models must independently agree to buy, drastically reducing false positives.
- **Veto System**: Blocks trades if global BTC trend is crashing or if the predicted success probability is too low.

### 2. **Advanced Risk Manager**
- **Smart Sizing**: Position size calculated based on balance and real buying power.
- **Martingale**: Configurable risk multiplier after losses to recover capital quickly.
- **Protections**: 
  - **Breakeven**: Moves SL to entry price at 50% TP progress.
  - **Trailing Stop**: Pursues profit using ATR-based dynamic distance.
  - **Intelligent Scale-In (DCA)**: Up to 3 "bullets" to improve entry price during pullbacks, only triggered if the AI spots a divergence.

### 3. **Market Stream & Data Engine**
- **Zero Latency**: Subscribed to Binance WebSocket Streams (`@kline_1m`, `@markPrice`), dropping REST API usage by 99%.
- **Alternative Data**: Feeds the neural network not just with OHLCV, but with the **Funding Rate** and the global **Fear & Greed Index** to gauge institutional sentiment.

### 4. **SQLite Tracker & Optuna Optimizer**
- Replaced legacy JSON/CSV storage with a robust transactional SQLite database (`mirage_trading.db`).
- **Auto-Tune Engine**: A standalone `optimizer.py` script uses Optuna and historical SQLite data to genetically find the most profitable hyper-parameters for the ML models.

### 1. Multi-Layer Consensus with Conflict Detection

```python
# If two opposing signals compete too closely, the layer returns None
# instead of emitting a weak, unreliable signal
if v_min > 0 and (v_min / v_max) > LAYER_CONFLICT_THRESHOLD:
    return None, 0, 'Layer Conflict'

- **TradingView Integration**: The old equity curve has been replaced by `TradingChart.jsx`, drawing real-time candlesticks, Entry levels, Take Profits, and Stop Losses explicitly on the chart.
- **Bi-Directional Control**: Includes a "PANIC SELL" button to force-close the entire active fleet directly from the UI.
- **Glassmorphism Settings**: Beautifully redesigned Settings UI allowing strategy toggling and parameter tweaking without touching any code.

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
[WebSocket Streams] + [Alternative Data] 
            ↓
       [Data Engine] 
            ↓
[9 Strategies + Ensemble ML Engine]
            ↓
     [Risk & Margin Check]
            ↓
    [Execution & SQLite Tracking]
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

- **Paper Trading by default**: Safe environment for AI learning.
- **Margin Awareness**: The bot tracks used vs. available margin to prevent over-leveraging.
- **Sleep Cycles**: Automatic nightly maintenance.
- **Hot-Reload**: Parameters can be updated from the UI without stopping the engine.

---

## Configuration

**Mirage Trading** has moved from an experimental setup to an institutional-grade algorithmic trading bot. The addition of XGBoost, Optuna, Alternative Data, SQLite, and WebSockets makes it extremely resilient and intelligent.

> **Recommendation**: Let the bot run in Paper Trading mode to build a massive dataset, and run `optimizer.py` every weekend to naturally evolve its neural pathways.
