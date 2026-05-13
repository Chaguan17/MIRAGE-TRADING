import os
from dotenv import load_dotenv

load_dotenv()

API_KEY    = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

if not API_KEY or not API_SECRET:
    print("⚠️ ADVERTENCIA: No se detectaron las llaves API. Revisa tu archivo .env")

# ── MERCADO ───────────────────────────────────────────────────────────────────
SYMBOL    = 'BTCUSDT'
TIMEFRAME = '1m'
LEVERAGE  = 10

# ── CAPITAL ───────────────────────────────────────────────────────────────────
PAPER_BALANCE  = 1000.0
RISK_PER_TRADE = 0.02
MAX_BULLETS    = 3
NO_SL_SIZE_PCT = 0.10
MIN_SIZE_USDT  = 0.0

# ── GESTIÓN DE RIESGO ─────────────────────────────────────────────────────────
ATR_MULTIPLIER = 2.0
TP_MULTIPLIER  = 4.0
MIN_CONFIDENCE = 0.65

# ── GESTIÓN DINÁMICA POR RACHA ────────────────────────────────────────────────
MAX_CONSECUTIVE_LOSSES = 3
RISK_REDUCTION_FACTOR  = 0.5
MAX_CONSECUTIVE_WINS   = 3
RISK_INCREASE_FACTOR   = 1.25
MAX_RISK_CAP           = 0.04

# ── COOLDOWN POST-LOSS ────────────────────────────────────────────────────────
COOLDOWN_CANDLES = 3

# ── SESIONES DE MERCADO (UTC) ─────────────────────────────────────────────────
SESSION_WEIGHTS = {
    'asia':    0.80,
    'europa':  1.00,
    'america': 1.10,
}

# ── TRAILING STOP ─────────────────────────────────────────────────────────────
TRAILING_STOP_ACTIVATION = 0.5
TRAILING_STOP_DISTANCE   = 0.3

# ── MÉTODOS AVANZADOS ─────────────────────────────────────────────────────────
SMC_LOOKBACK          = 20
SMC_OB_STRENGTH       = 0.3
VWAP_BAND_MULT        = 1.0
LIQ_LOOKBACK          = 30
LIQ_CLUSTER_PCT       = 0.002
WYCKOFF_LOOKBACK      = 50
BTC_CORRELATION_LIMIT = 100
BTC_CORR_THRESHOLD    = 0.65

# ── RECONEXIÓN AUTOMÁTICA ─────────────────────────────────────────────────────
MAX_RECONNECT_ATTEMPTS = 10
RECONNECT_WAIT_SECONDS = 30

# ── RESUMEN DIARIO ────────────────────────────────────────────────────────────
DAILY_SUMMARY_HOUR   = 23
DAILY_SUMMARY_MINUTE = 55

# ── CICLO CIRCADIANO ──────────────────────────────────────────────────────────
SLEEP_START_HOUR   = 0
SLEEP_START_MINUTE = 0
SLEEP_END_HOUR     = 0
SLEEP_END_MINUTE   = 5