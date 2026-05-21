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

# ══════════════════════════════════════════════════════════════════
# TAREA 1.1 — Reemplazar magic numbers con constantes nombradas
# TAREA 1.1 — Añadir límite de leverage (Sprint 4 adelantado, 5 min)
# ══════════════════════════════════════════════════════════════════

# ── LÍMITES DE SEGURIDAD (HARD LIMITS — NO CAMBIAR) ──────────────
MAX_LEVERAGE_ALLOWED = 125         # Máximo permitido 125x
DEFAULT_LEVERAGE     = 10         # Valor por defecto 10x
MIN_TRADES_FOR_AI    = 100         # Antes era 5 — sube a 20 ahora, llega a 100 en Sprint 3
MAX_BOOTSTRAP_BUFFER = 5          # Mínimo de trades para primer fit online


def load_dynamic_settings():
    """
    Carga el archivo storage/settings.json generado por la API/dashboard.

    Returns:
        dict: Configuración dinámica. Vacío si el archivo no existe o es inválido.
    """
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
    """
    Garantiza que un valor de riesgo esté expresado como porcentaje decimal (0–1).

    El bug original: settings.json tenía RISK_PER_TRADE=2.0 (USDT fijo)
    mientras MAX_RISK_CAP=0.04 (porcentaje). El RiskManager los comparaba
    directamente, haciendo que el cap nunca funcionara.

    Esta función detecta valores >= 1.0 y los convierte dividiéndolos entre 100,
    asumiendo que el usuario escribió "2" queriendo decir "2%".

    Args:
        value (float): Valor leído del JSON (puede ser 0.02 o 2.0).
        name (str):    Nombre de la variable (solo para el log).

    Returns:
        float: Valor como decimal entre 0.0 y 1.0.

    Examples:
        >>> normalize_risk_pct(2.0, 'RISK_PER_TRADE')
        0.02          # 2% del capital
        >>> normalize_risk_pct(0.02, 'RISK_PER_TRADE')
        0.02          # ya era correcto
    """
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
        >>> clamp_leverage(10)
        3
        >>> clamp_leverage(2)
        2
    """
    if requested > MAX_LEVERAGE_ALLOWED:
        logger.warning(
            f"Leverage {requested}x supera el límite {MAX_LEVERAGE_ALLOWED}x — "
            f"usando {MAX_LEVERAGE_ALLOWED}x"
        )
        return MAX_LEVERAGE_ALLOWED
    return requested


# ── CARGA DINÁMICA ────────────────────────────────────────────────
dyn = load_dynamic_settings()

# ── MERCADO ───────────────────────────────────────────────────────
PARES_ACTIVOS = dyn.get('PARES_ACTIVOS', ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'])
SYMBOL        = dyn.get('SYMBOL', 'BTCUSDT')
TIMEFRAME     = dyn.get('TIMEFRAME', '1m')

# LEVERAGE: siempre pasa por clamp_leverage — nunca usar dyn['LEVERAGE'] directo
LEVERAGE = clamp_leverage(int(dyn.get('LEVERAGE', DEFAULT_LEVERAGE)))

# ── CAPITAL ───────────────────────────────────────────────────────
PAPER_BALANCE  = float(dyn.get('PAPER_BALANCE', 1000.0))
# normalize_risk_pct convierte "2.0" → 0.02 automáticamente si alguien
# escribió el porcentaje como entero en settings.json
RISK_PER_TRADE = normalize_risk_pct(float(dyn.get('RISK_PER_TRADE', 0.02)), 'RISK_PER_TRADE')
MAX_BULLETS    = int(dyn.get('MAX_BULLETS', 3))
NO_SL_SIZE_PCT = float(dyn.get('NO_SL_SIZE_PCT', 0.10))
MIN_SIZE_USDT  = float(dyn.get('MIN_SIZE_USDT', 0.0))

# ── GESTIÓN DE RIESGO ─────────────────────────────────────────────
ATR_MULTIPLIER = float(dyn.get('ATR_MULTIPLIER', 2.0))
TP_MULTIPLIER  = float(dyn.get('TP_MULTIPLIER', 4.0))
MIN_CONFIDENCE = float(dyn.get('MIN_CONFIDENCE', 0.65))

# ── GESTIÓN DINÁMICA POR RACHA ────────────────────────────────────
MAX_CONSECUTIVE_LOSSES = int(dyn.get('MAX_CONSECUTIVE_LOSSES', 3))
RISK_REDUCTION_FACTOR  = float(dyn.get('RISK_REDUCTION_FACTOR', 0.5))
MAX_CONSECUTIVE_WINS   = int(dyn.get('MAX_CONSECUTIVE_WINS', 3))
RISK_INCREASE_FACTOR   = float(dyn.get('RISK_INCREASE_FACTOR', 1.25))
MAX_RISK_CAP           = normalize_risk_pct(float(dyn.get('MAX_RISK_CAP', 0.04)), 'MAX_RISK_CAP')

# ── COOLDOWN POST-LOSS ────────────────────────────────────────────
COOLDOWN_CANDLES = int(dyn.get('COOLDOWN_CANDLES', 3))

# ── SESIONES DE MERCADO (UTC) ─────────────────────────────────────
SESSION_WEIGHTS = dyn.get('SESSION_WEIGHTS', {
    'asia':    0.80,
    'europa':  1.00,
    'america': 1.10,
})

# ── TRAILING STOP ─────────────────────────────────────────────────
TRAILING_STOP_ACTIVATION = float(dyn.get('TRAILING_STOP_ACTIVATION', 0.5))
TRAILING_STOP_DISTANCE   = float(dyn.get('TRAILING_STOP_DISTANCE', 0.3))

# ── MÉTODOS AVANZADOS ─────────────────────────────────────────────
SMC_LOOKBACK          = int(dyn.get('SMC_LOOKBACK', 20))
SMC_OB_STRENGTH       = float(dyn.get('SMC_OB_STRENGTH', 0.3))
VWAP_BAND_MULT        = float(dyn.get('VWAP_BAND_MULT', 1.0))
LIQ_LOOKBACK          = int(dyn.get('LIQ_LOOKBACK', 30))
LIQ_CLUSTER_PCT       = float(dyn.get('LIQ_CLUSTER_PCT', 0.002))
WYCKOFF_LOOKBACK      = int(dyn.get('WYCKOFF_LOOKBACK', 50))
BTC_CORRELATION_LIMIT = int(dyn.get('BTC_CORRELATION_LIMIT', 100))
BTC_CORR_THRESHOLD    = float(dyn.get('BTC_CORR_THRESHOLD', 0.65))

# ── RECONEXIÓN AUTOMÁTICA ─────────────────────────────────────────
MAX_RECONNECT_ATTEMPTS = int(dyn.get('MAX_RECONNECT_ATTEMPTS', 10))
RECONNECT_WAIT_SECONDS = int(dyn.get('RECONNECT_WAIT_SECONDS', 30))

# ── RESUMEN DIARIO ────────────────────────────────────────────────
DAILY_SUMMARY_HOUR   = int(dyn.get('DAILY_SUMMARY_HOUR', 22))
DAILY_SUMMARY_MINUTE = int(dyn.get('DAILY_SUMMARY_MINUTE', 10))

# ── CICLO CIRCADIANO ──────────────────────────────────────────────
SLEEP_START_HOUR   = int(dyn.get('SLEEP_START_HOUR', 22))
SLEEP_START_MINUTE = int(dyn.get('SLEEP_START_MINUTE', 0))
SLEEP_END_HOUR     = int(dyn.get('SLEEP_END_HOUR', 8))
SLEEP_END_MINUTE   = int(dyn.get('SLEEP_END_MINUTE', 0))

validate_sleep_config(SLEEP_START_HOUR, SLEEP_START_MINUTE, SLEEP_END_HOUR, SLEEP_END_MINUTE)
logger.info(f"Sleep schedule configured: {SLEEP_START_HOUR:02d}:{SLEEP_START_MINUTE:02d} → {SLEEP_END_HOUR:02d}:{SLEEP_END_MINUTE:02d} UTC")