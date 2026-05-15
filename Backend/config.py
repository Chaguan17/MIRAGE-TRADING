import os
from dotenv import load_dotenv
import json
import logging

logger = logging.getLogger(__name__)

load_dotenv()

API_KEY    = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

if not API_KEY or not API_SECRET:
    logger.warning("Missing Binance API credentials in .env")

SETTINGS_PATH = "storage/settings.json"

def load_dynamic_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {SETTINGS_PATH}: {e}")
        except Exception as e:
            logger.error(f"Error loading settings from {SETTINGS_PATH}: {e}")
    return {}

def validate_sleep_config(start_hour, start_minute, end_hour, end_minute):
    """Validate that sleep configuration makes sense."""
    if not (0 <= start_hour <= 23 and 0 <= start_minute <= 59):
        logger.error(f"Invalid sleep start time: {start_hour}:{start_minute}")
        return False
    if not (0 <= end_hour <= 23 and 0 <= end_minute <= 59):
        logger.error(f"Invalid sleep end time: {end_hour}:{end_minute}")
        return False
    # Warn if sleep window is very small
    from datetime import time as dtime
    start = dtime(start_hour, start_minute)
    end = dtime(end_hour, end_minute)
    if start == end:
        logger.warning("Sleep start time equals end time - bot will not sleep properly")
    return True

dyn = load_dynamic_settings()

# ── MERCADO ───────────────────────────────────────────────────────────────────
PARES_ACTIVOS = dyn.get('PARES_ACTIVOS', ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']) # Soporte Multi-Pair
SYMBOL    = dyn.get('SYMBOL', 'BTCUSDT' )
TIMEFRAME = dyn.get('TIMEFRAME', '1m')
LEVERAGE  = int(dyn.get('LEVERAGE', 10))

# ── CAPITAL ───────────────────────────────────────────────────────────────────
PAPER_BALANCE  = float(dyn.get('PAPER_BALANCE', 1000.0))
RISK_PER_TRADE = float(dyn.get('RISK_PER_TRADE', 0.02))
MAX_BULLETS    = int(dyn.get('MAX_BULLETS', 3))
NO_SL_SIZE_PCT = float(dyn.get('NO_SL_SIZE_PCT', 0.10))
MIN_SIZE_USDT  = float(dyn.get('MIN_SIZE_USDT', 0.0))

# ── GESTIÓN DE RIESGO ─────────────────────────────────────────────────────────
ATR_MULTIPLIER = float(dyn.get('ATR_MULTIPLIER', 2.0))
TP_MULTIPLIER  = float(dyn.get('TP_MULTIPLIER', 4.0))
MIN_CONFIDENCE = float(dyn.get('MIN_CONFIDENCE', 0.65))

# ── GESTIÓN DINÁMICA POR RACHA ────────────────────────────────────────────────
MAX_CONSECUTIVE_LOSSES = int(dyn.get('MAX_CONSECUTIVE_LOSSES', 3))
RISK_REDUCTION_FACTOR  = float(dyn.get('RISK_REDUCTION_FACTOR', 0.5))
MAX_CONSECUTIVE_WINS   = int(dyn.get('MAX_CONSECUTIVE_WINS', 3))
RISK_INCREASE_FACTOR   = float(dyn.get('RISK_INCREASE_FACTOR', 1.25))
MAX_RISK_CAP           = float(dyn.get('MAX_RISK_CAP', 0.04))

# ── COOLDOWN POST-LOSS ────────────────────────────────────────────────────────
COOLDOWN_CANDLES = int(dyn.get('COOLDOWN_CANDLES', 3))

# ── SESIONES DE MERCADO (UTC) ─────────────────────────────────────────────────
SESSION_WEIGHTS = dyn.get('SESSION_WEIGHTS', {
    'asia':    0.80,
    'europa':  1.00,
    'america': 1.10,
})

# ── TRAILING STOP ─────────────────────────────────────────────────────────────
TRAILING_STOP_ACTIVATION = float(dyn.get('TRAILING_STOP_ACTIVATION', 0.5))
TRAILING_STOP_DISTANCE   = float(dyn.get('TRAILING_STOP_DISTANCE', 0.3))

# ── MÉTODOS AVANZADOS ─────────────────────────────────────────────────────────
SMC_LOOKBACK          = int(dyn.get('SMC_LOOKBACK', 20))
SMC_OB_STRENGTH       = float(dyn.get('SMC_OB_STRENGTH', 0.3))
VWAP_BAND_MULT        = float(dyn.get('VWAP_BAND_MULT', 1.0))
LIQ_LOOKBACK          = int(dyn.get('LIQ_LOOKBACK', 30))
LIQ_CLUSTER_PCT       = float(dyn.get('LIQ_CLUSTER_PCT', 0.002))
WYCKOFF_LOOKBACK      = int(dyn.get('WYCKOFF_LOOKBACK', 50))
BTC_CORRELATION_LIMIT = int(dyn.get('BTC_CORRELATION_LIMIT', 100))
BTC_CORR_THRESHOLD    = float(dyn.get('BTC_CORR_THRESHOLD', 0.65))

# ── RECONEXIÓN AUTOMÁTICA ─────────────────────────────────────────────────────
MAX_RECONNECT_ATTEMPTS = int(dyn.get('MAX_RECONNECT_ATTEMPTS', 10))
RECONNECT_WAIT_SECONDS = int(dyn.get('RECONNECT_WAIT_SECONDS', 30))

# ── RESUMEN DIARIO ────────────────────────────────────────────────────────────
DAILY_SUMMARY_HOUR   = int(dyn.get('DAILY_SUMMARY_HOUR', 22))
DAILY_SUMMARY_MINUTE = int(dyn.get('DAILY_SUMMARY_MINUTE', 10))

# ── CICLO CIRCADIANO ──────────────────────────────────────────────────────────
SLEEP_START_HOUR   = int(dyn.get('SLEEP_START_HOUR', 22))
SLEEP_START_MINUTE = int(dyn.get('SLEEP_START_MINUTE', 0))
SLEEP_END_HOUR     = int(dyn.get('SLEEP_END_HOUR', 22))
SLEEP_END_MINUTE   = int(dyn.get('SLEEP_END_MINUTE', 5))

validate_sleep_config(SLEEP_START_HOUR, SLEEP_START_MINUTE, SLEEP_END_HOUR, SLEEP_END_MINUTE)