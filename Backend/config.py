import os
import json
import logging

logger = logging.getLogger(__name__)

STORAGE_DIR = "storage"
SETTINGS_PATH = os.path.join(STORAGE_DIR, "settings.json")
METADATA_PATH = os.path.join(STORAGE_DIR, "parameters_metadata.json")
LIVE_STATE_PATH = os.path.join(STORAGE_DIR, "live_state.json")
DB_PATH = os.path.join(STORAGE_DIR, "mirage_trading.db")
BACKUP_DIR = os.path.join(STORAGE_DIR, "backups")

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)


def load_dynamic_settings():
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
    except Exception as e:
        logger.error(f"Error crítico al cargar settings.json: {e}")
    return {}


dyn = load_dynamic_settings()

# Credenciales (Prioridad: settings.json -> Environment)
API_KEY = dyn.get("API_KEY", os.getenv("BINANCE_API_KEY", ""))
API_SECRET = dyn.get("API_SECRET", os.getenv("BINANCE_API_SECRET", ""))
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_WAIT_SECONDS = 10


# ============================================================
# NORMALIZACIÓN PROFESIONAL
# ============================================================

def normalize_percentage(value: float, name: str) -> float:
    """
    Convierte porcentajes humanos a decimal.

    2    -> 0.02
    60   -> 0.60
    0.02 -> 0.02
    """

    if value > 1:
        converted = value / 100.0

        logger.warning(
            f"{name}={value} convertido automáticamente "
            f"a decimal={converted}"
        )

        return converted

    return value


# Definimos rangos permitidos para evitar que el bot use valores absurdos por error
PERCENTAGE_FIELDS = {
    "RISK_PER_TRADE": (0.001, 0.03),
    "MIN_CONFIDENCE": (0.50, 0.95),
    "TRAILING_STOP_ACTIVATION": (0.001, 0.99),
    "TRAILING_STOP_DISTANCE": (0.001, 0.50),
    "BREAKEVEN_ACTIVATION": (0.001, 0.90),
}


def validate_percentage(name: str, value: float):
    if name not in PERCENTAGE_FIELDS:
        return value

    min_val, max_val = PERCENTAGE_FIELDS[name]

    if value < min_val:
        logger.warning(
            f"{name} demasiado bajo ({value}) "
            f"→ ajustado a {min_val}"
        )
        return min_val

    if value > max_val:
        logger.warning(
            f"{name} demasiado alto ({value}) "
            f"→ ajustado a {max_val}"
        )
        return max_val

    return value


# ============================================================
# CONFIG
# ============================================================

PAPER_BALANCE = float(
    dyn.get("PAPER_BALANCE", 1000)
)

LEVERAGE = int(
    dyn.get("LEVERAGE", 5)
)

TIMEFRAME = dyn.get(
    "TIMEFRAME",
    "1m"
)

PARES_ACTIVOS = dyn.get(
    "PARES_ACTIVOS",
    ["BTCUSDT"]
)

MAX_BULLETS = int(dyn.get("MAX_BULLETS", 3))
MARTINGALE_ENABLED = bool(dyn.get("MARTINGALE_ENABLED", False))
COOLDOWN_CANDLES = int(dyn.get("COOLDOWN_CANDLES", 5))

# Ciclo Circadiano
SLEEP_START_HOUR = int(dyn.get("SLEEP_START_HOUR", 23))
SLEEP_START_MINUTE = int(dyn.get("SLEEP_START_MINUTE", 0))
SLEEP_END_HOUR = int(dyn.get("SLEEP_END_HOUR", 6))
SLEEP_END_MINUTE = int(dyn.get("SLEEP_END_MINUTE", 0))

BREAKEVEN_ACTIVATION = float(dyn.get("BREAKEVEN_ACTIVATION", 0.5))

RISK_PER_TRADE = validate_percentage(
    "RISK_PER_TRADE",
    normalize_percentage(
        float(dyn.get("RISK_PER_TRADE", 0.01)),
        "RISK_PER_TRADE"
    )
)

MIN_CONFIDENCE = validate_percentage(
    "MIN_CONFIDENCE",
    normalize_percentage(
        float(dyn.get("MIN_CONFIDENCE", 0.60)),
        "MIN_CONFIDENCE"
    )
)

ATR_MULTIPLIER = float(
    dyn.get("ATR_MULTIPLIER", 1.5)
)

TP_MULTIPLIER = float(
    dyn.get("TP_MULTIPLIER", 3.0)
)

TRAILING_STOP_ACTIVATION = float(
    dyn.get("TRAILING_STOP_ACTIVATION", 0.005)
)

TRAILING_STOP_DISTANCE = float(
    dyn.get("TRAILING_STOP_DISTANCE", 0.0025)
)