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

# --- RUTAS DE ARCHIVOS ---
STORAGE_DIR          = "storage"
SETTINGS_PATH        = os.path.join(STORAGE_DIR, "settings.json")
TRADE_HISTORY_PATH   = os.path.join(STORAGE_DIR, "trade_history.csv")
DB_PATH              = os.path.join(STORAGE_DIR, "mirage_trading.db")
BACKUP_DIR           = os.path.join(STORAGE_DIR, "backups")
LIVE_STATE_PATH      = os.path.join(STORAGE_DIR, "live_state.json")
METADATA_PATH        = os.path.join(STORAGE_DIR, "parameters_metadata.json")

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

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

dyn = load_dynamic_settings()

# --- CONSTANTES DE SEGURIDAD Y IA ---
MAX_LEVERAGE_ALLOWED = int(dyn.get("MAX_LEVERAGE_ALLOWED", 125))
DEFAULT_LEVERAGE     = int(dyn.get("DEFAULT_LEVERAGE", 10))
MIN_TRADES_FOR_AI    = int(dyn.get("MIN_TRADES_FOR_AI", 100))
MAX_BOOTSTRAP_BUFFER = int(dyn.get("MAX_BOOTSTRAP_BUFFER", 5))

# --- HIPERPARÁMETROS IA ---
AI_MAX_WEIGHT           = float(dyn.get("AI_MAX_WEIGHT", 0.70))
AI_BASE_ESTIMATORS      = int(dyn.get("AI_BASE_ESTIMATORS", 100))
AI_ESTIMATORS_STEP      = int(dyn.get("AI_ESTIMATORS_STEP", 10))
AI_LEARNING_CURVE_STEPS = int(dyn.get("AI_LEARNING_CURVE_STEPS", 45))
RANDOM_STATE            = int(dyn.get("RANDOM_STATE", 42))

LAYER_WEIGHTS = dyn.get("LAYER_WEIGHTS", {"basic": 0.25, "structure": 0.45, "context": 0.30})


def validate_sleep_config(start_hour, start_minute, end_hour, end_minute):
    """
    Valida que los parámetros del ciclo circadiano sean coherentes.

    Args:
        start_hour (int):   Hora de inicio del sueño (0-23).
        start_minute (int): Minuto de inicio (0-59).
        end_hour (int):     Hora de fin del sueño (0-23).
        end_minute (int):   Minuto de fin (0-59).

    Returns:
        bool: True si la config es válida, False si hay errores.
    """
    if not (0 <= start_hour <= 23 and 0 <= start_minute <= 59):
        logger.error(f"Invalid sleep start time: {start_hour}:{start_minute}")
        return False
    if not (0 <= end_hour <= 23 and 0 <= end_minute <= 59):
        logger.error(f"Invalid sleep end time: {end_hour}:{end_minute}")
        return False
    from datetime import time as dtime
    if dtime(start_hour, start_minute) == dtime(end_hour, end_minute):
        logger.warning("Sleep start time equals end time — bot will not sleep properly")
    return True


def normalize_risk_pct(value: float, name: str) -> float:
    if value >= 1.0:
        converted = value / 100.0
        logger.warning(
            f"{name}={value} parece ser un porcentaje entero (ej: 2 = 2%). "
            f"Convirtiendo automáticamente a {converted} (decimal). "
            f"Corrige storage/settings.json para evitar este aviso."
        )
        return converted
    return value


def clamp_leverage(requested: int) -> int:
    """
    Limita el leverage al máximo permitido por seguridad.

    Args:
        requested (int): Leverage solicitado (p.ej. desde settings.json).

    Returns:
        int: Leverage real a usar (nunca supera MAX_LEVERAGE_ALLOWED).

    Example:
        >>> clamp_leverage(200)
        125
        >>> clamp_leverage(10)
        10
        >>> clamp_leverage(2)
        2

    BUG MENOR CORREGIDO #9:
    El docstring original decía:
        >>> clamp_leverage(10)
        3   ← INCORRECTO (10 < 125, no se recorta)
    El valor correcto es 10, porque 10 no supera MAX_LEVERAGE_ALLOWED=125.
    """
    if requested > MAX_LEVERAGE_ALLOWED:
        logger.warning(
            f"Leverage {requested}x supera el límite {MAX_LEVERAGE_ALLOWED}x — "
            f"usando {MAX_LEVERAGE_ALLOWED}x"
        )
        return MAX_LEVERAGE_ALLOWED
    return requested


# --- VALIDACIÓN DEFENSIVA PARA PARES_ACTIVOS ---
_raw_pares = dyn.get('PARES_ACTIVOS', ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'])

if isinstance(_raw_pares, list):
    PARES_ACTIVOS = _raw_pares
elif isinstance(_raw_pares, str):
    PARES_ACTIVOS = [p.strip() for p in _raw_pares.split(',') if p.strip()]
    logger.warning(f"PARES_ACTIVOS se recibió como texto. Auto-convertido a lista: {PARES_ACTIVOS}")
else:
    logger.error(f"PARES_ACTIVOS en settings.json es inválido (tipo {type(_raw_pares).__name__}). Forzando pares por defecto.")
    PARES_ACTIVOS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']

# --- PRESETS PARA LA UI ---
PRESET_PAIRS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'LINKUSDT']
PRESET_TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']
# -----------------------------------------------

SYMBOL        = dyn.get('SYMBOL', 'BTCUSDT')
TIMEFRAME     = dyn.get('TIMEFRAME', '1m')

LEVERAGE = clamp_leverage(int(dyn.get('LEVERAGE', DEFAULT_LEVERAGE)))


PAPER_BALANCE  = float(dyn.get('PAPER_BALANCE', 1000.0))


RISK_PER_TRADE = normalize_risk_pct(float(dyn.get('RISK_PER_TRADE', 0.02)), 'RISK_PER_TRADE')
MAX_BULLETS    = int(dyn.get('MAX_BULLETS', 3))
NO_SL_SIZE_PCT = float(dyn.get('NO_SL_SIZE_PCT', 0.10))
MIN_SIZE_USDT  = float(dyn.get('MIN_SIZE_USDT', 0.0))


ATR_MULTIPLIER = float(dyn.get('ATR_MULTIPLIER', 2.0))
TP_MULTIPLIER  = float(dyn.get('TP_MULTIPLIER', 4.0))
MIN_CONFIDENCE = float(dyn.get('MIN_CONFIDENCE', 0.55))


MAX_CONSECUTIVE_LOSSES = int(dyn.get('MAX_CONSECUTIVE_LOSSES', 3))
RISK_REDUCTION_FACTOR  = float(dyn.get('RISK_REDUCTION_FACTOR', 0.5))
MAX_CONSECUTIVE_WINS   = int(dyn.get('MAX_CONSECUTIVE_WINS', 3))
RISK_INCREASE_FACTOR   = float(dyn.get('RISK_INCREASE_FACTOR', 1.25))
MAX_RISK_CAP           = normalize_risk_pct(float(dyn.get('MAX_RISK_CAP', 0.04)), 'MAX_RISK_CAP')


COOLDOWN_CANDLES = int(dyn.get('COOLDOWN_CANDLES', 3))


SESSION_WEIGHTS = dyn.get('SESSION_WEIGHTS', {
    'asia':    0.80,
    'europa':  1.00,
    'america': 1.10,
})


TRAILING_STOP_ACTIVATION = float(dyn.get('TRAILING_STOP_ACTIVATION', 0.5))
TRAILING_STOP_DISTANCE   = float(dyn.get('TRAILING_STOP_DISTANCE', 0.3))
BREAKEVEN_ACTIVATION     = float(dyn.get('BREAKEVEN_ACTIVATION', 0.5))


SMC_LOOKBACK          = int(dyn.get('SMC_LOOKBACK', 20))
SMC_OB_STRENGTH       = float(dyn.get('SMC_OB_STRENGTH', 0.3))
VWAP_BAND_MULT        = float(dyn.get('VWAP_BAND_MULT', 1.0))
LIQ_LOOKBACK          = int(dyn.get('LIQ_LOOKBACK', 30))
LIQ_CLUSTER_PCT       = float(dyn.get('LIQ_CLUSTER_PCT', 0.002))
WYCKOFF_LOOKBACK      = int(dyn.get('WYCKOFF_LOOKBACK', 50))
BTC_CORRELATION_LIMIT = int(dyn.get('BTC_CORRELATION_LIMIT', 100))
BTC_CORR_THRESHOLD    = float(dyn.get('BTC_CORR_THRESHOLD', 0.65))


MAX_RECONNECT_ATTEMPTS = int(dyn.get('MAX_RECONNECT_ATTEMPTS', 10))
RECONNECT_WAIT_SECONDS = int(dyn.get('RECONNECT_WAIT_SECONDS', 30))


DAILY_SUMMARY_HOUR   = int(dyn.get('DAILY_SUMMARY_HOUR', 22))
DAILY_SUMMARY_MINUTE = int(dyn.get('DAILY_SUMMARY_MINUTE', 10))


SLEEP_START_HOUR   = int(dyn.get('SLEEP_START_HOUR', 22))
SLEEP_START_MINUTE = int(dyn.get('SLEEP_START_MINUTE', 0))
SLEEP_END_HOUR     = int(dyn.get('SLEEP_END_HOUR', 8))
SLEEP_END_MINUTE   = int(dyn.get('SLEEP_END_MINUTE', 0))


# --- VETOS DINÁMICOS ---
GLOBAL_RSI_OB_BASE        = float(dyn.get("GLOBAL_RSI_OB_BASE", 75.0))
GLOBAL_RSI_OS_BASE        = float(dyn.get("GLOBAL_RSI_OS_BASE", 25.0))
RSI_VOL_ADJUSTMENT_FACTOR = float(dyn.get("RSI_VOL_ADJUSTMENT_FACTOR", 20.0))
RSI_VOL_REF               = float(dyn.get("RSI_VOL_REF", 0.15))

# --- AJUSTE DINÁMICO DE TAKE PROFIT ---
TP_VOL_ADJUSTMENT_FACTOR  = float(dyn.get("TP_VOL_ADJUSTMENT_FACTOR", 5.0))
TP_VOL_REF                = float(dyn.get("TP_VOL_REF", 0.15))
TP_MIN_MULTIPLIER         = float(dyn.get("TP_MIN_MULTIPLIER", 2.0))

# --- ESTRATEGIA MARTINGALA ---
MARTINGALE_ENABLED    = str(dyn.get("MARTINGALE_ENABLED", "False")).lower() == "true"
MARTINGALE_MULTIPLIER = float(dyn.get("MARTINGALE_MULTIPLIER", 2.0))
MARTINGALE_MAX_STEPS  = int(dyn.get("MARTINGALE_MAX_STEPS", 3))

# --- AJUSTE DINÁMICO DE STOP LOSS ---
SL_VOL_ADJUSTMENT_FACTOR  = float(dyn.get("SL_VOL_ADJUSTMENT_FACTOR", 2.0))
SL_VOL_REF                = float(dyn.get("SL_VOL_REF", 0.15))
SL_MIN_MULTIPLIER         = float(dyn.get("SL_MIN_MULTIPLIER", 1.2))

validate_sleep_config(SLEEP_START_HOUR, SLEEP_START_MINUTE, SLEEP_END_HOUR, SLEEP_END_MINUTE)
logger.info(f"Sleep schedule configured: {SLEEP_START_HOUR:02d}:{SLEEP_START_MINUTE:02d} → {SLEEP_END_HOUR:02d}:{SLEEP_END_MINUTE:02d} UTC")