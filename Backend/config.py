"""
config.py — Mirage Trading
Fuente única de verdad para todas las constantes del bot.
Carga settings.json y rellena los valores faltantes con defaults seguros.
"""
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Rutas ────────────────────────────────────────────────────────────────────
STORAGE_DIR      = "storage"
SETTINGS_PATH    = os.path.join(STORAGE_DIR, "settings.json")
METADATA_PATH    = os.path.join(STORAGE_DIR, "parameters_metadata.json")
LIVE_STATE_PATH  = os.path.join(STORAGE_DIR, "live_state.json")
DB_PATH          = os.path.join(STORAGE_DIR, "mirage_trading.db")
BACKUP_DIR       = os.path.join(STORAGE_DIR, "backups")

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR,  exist_ok=True)

# ── Trade logger (para backtester) ───────────────────────────────────────────
trade_logger = logging.getLogger("trade_logger")
if not trade_logger.handlers:
    _fh = logging.FileHandler(os.path.join(STORAGE_DIR, "trades.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    trade_logger.addHandler(_fh)
    trade_logger.setLevel(logging.INFO)


def load_dynamic_settings() -> dict:
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
    except Exception as e:
        logger.error(f"Error cargando settings.json: {e}")
    return {}


dyn = load_dynamic_settings()

# ── Credenciales ─────────────────────────────────────────────────────────────
API_KEY    = dyn.get("API_KEY",    os.getenv("BINANCE_API_KEY", ""))
API_SECRET = dyn.get("API_SECRET", os.getenv("BINANCE_API_SECRET", ""))

MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_WAIT_SECONDS = 10

# ════════════════════════════════════════════════════════════════════════════
# NORMALIZACIÓN Y VALIDACIÓN
# ════════════════════════════════════════════════════════════════════════════

def normalize_percentage(value: float, name: str) -> float:
    """Convierte valores > 1 al formato decimal (ej: 2 → 0.02)."""
    if value > 1:
        converted = value / 100.0
        logger.warning(f"{name}={value} convertido a decimal={converted:.6f}")
        return converted
    return value

# Alias usado en tests
normalize_risk_pct = normalize_percentage

PERCENTAGE_FIELDS = {
    "RISK_PER_TRADE":          (0.001, 0.10),   # ampliado para adaptativos
    "MAX_RISK_CAP":            (0.001, 0.15),
    "MIN_CONFIDENCE":          (0.50,  0.95),
    "TRAILING_STOP_ACTIVATION":(0.001, 0.99),
    "TRAILING_STOP_DISTANCE":  (0.001, 0.50),
    "BREAKEVEN_ACTIVATION":    (0.001, 0.90),
}

def validate_percentage(name: str, value: float) -> float:
    if name not in PERCENTAGE_FIELDS:
        return value
    lo, hi = PERCENTAGE_FIELDS[name]
    if value < lo:
        logger.warning(f"{name} demasiado bajo ({value}) → ajustado a {lo}")
        return lo
    if value > hi:
        logger.warning(f"{name} demasiado alto ({value}) → ajustado a {hi}")
        return hi
    return value

# ── Leverage con clamp ───────────────────────────────────────────────────────
MAX_LEVERAGE_ALLOWED = 20

def clamp_leverage(value: int) -> int:
    return min(int(value), MAX_LEVERAGE_ALLOWED)

def validate_sleep_config(start_h: int, start_m: int, end_h: int, end_m: int) -> bool:
    return all(0 <= h <= 23 and 0 <= m <= 59
               for h, m in [(start_h, start_m), (end_h, end_m)])

# ════════════════════════════════════════════════════════════════════════════
# PARÁMETROS OPERATIVOS (cargados desde settings.json)
# ════════════════════════════════════════════════════════════════════════════

PAPER_BALANCE = float(dyn.get("PAPER_BALANCE", 1000))
LEVERAGE      = clamp_leverage(dyn.get("LEVERAGE", 5))
TIMEFRAME     = dyn.get("TIMEFRAME", "15m")
PARES_ACTIVOS = dyn.get("PARES_ACTIVOS", ["BTCUSDT"])
SYMBOL        = PARES_ACTIVOS[0] if PARES_ACTIVOS else "BTCUSDT"  # alias legacy

MAX_BULLETS        = int(dyn.get("MAX_BULLETS", 3))
MARTINGALE_ENABLED = bool(dyn.get("MARTINGALE_ENABLED", False))
MARTINGALE_MULTIPLIER  = float(dyn.get("MARTINGALE_MULTIPLIER", 1.5))
MARTINGALE_MAX_STEPS   = int(dyn.get("MARTINGALE_MAX_STEPS", 2))
COOLDOWN_CANDLES   = int(dyn.get("COOLDOWN_CANDLES", 3))

# Ciclo circadiano
SLEEP_START_HOUR   = int(dyn.get("SLEEP_START_HOUR", 23))
SLEEP_START_MINUTE = int(dyn.get("SLEEP_START_MINUTE", 0))
SLEEP_END_HOUR     = int(dyn.get("SLEEP_END_HOUR", 6))
SLEEP_END_MINUTE   = int(dyn.get("SLEEP_END_MINUTE", 0))

# Risk
RISK_PER_TRADE = validate_percentage(
    "RISK_PER_TRADE",
    normalize_percentage(float(dyn.get("RISK_PER_TRADE", 0.01)), "RISK_PER_TRADE")
)
MAX_RISK_CAP = validate_percentage(
    "MAX_RISK_CAP",
    normalize_percentage(float(dyn.get("MAX_RISK_CAP", 0.05)), "MAX_RISK_CAP")
)
MIN_CONFIDENCE = validate_percentage(
    "MIN_CONFIDENCE",
    normalize_percentage(float(dyn.get("MIN_CONFIDENCE", 0.60)), "MIN_CONFIDENCE")
)

MAX_CONSECUTIVE_WINS   = int(dyn.get("MAX_CONSECUTIVE_WINS", 3))
MAX_CONSECUTIVE_LOSSES = int(dyn.get("MAX_CONSECUTIVE_LOSSES", 2))
RISK_INCREASE_FACTOR   = float(dyn.get("RISK_INCREASE_FACTOR", 1.25))
RISK_REDUCTION_FACTOR  = float(dyn.get("RISK_REDUCTION_FACTOR", 0.5))

NO_SL_SIZE_PCT = float(dyn.get("NO_SL_SIZE_PCT", 0.10))   # % del balance sin SL
MIN_SIZE_USDT  = float(dyn.get("MIN_SIZE_USDT", 5.0))

# Stops dinámicos
ATR_MULTIPLIER        = float(dyn.get("ATR_MULTIPLIER", 1.5))
TP_MULTIPLIER         = float(dyn.get("TP_MULTIPLIER", 3.0))

TRAILING_ATR_MULTIPLIER = float(dyn.get("TRAILING_ATR_MULTIPLIER", 0.5))

TRAILING_STOP_ACTIVATION = validate_percentage(
    "TRAILING_STOP_ACTIVATION",
    normalize_percentage(float(dyn.get("TRAILING_STOP_ACTIVATION", 0.005)), "TRAILING_STOP_ACTIVATION")
)
BREAKEVEN_ACTIVATION = validate_percentage(
    "BREAKEVEN_ACTIVATION",
    normalize_percentage(float(dyn.get("BREAKEVEN_ACTIVATION", 0.5)), "BREAKEVEN_ACTIVATION")
)

# Filtros Macro (Veto Engine)
VETO_CRASH_PCT = float(dyn.get("VETO_CRASH_PCT", 0.08))  # 8% caída en 1H


# Ajuste dinámico TP/SL por volatilidad
TP_VOL_REF              = float(dyn.get("TP_VOL_REF", 0.5))
TP_VOL_ADJUSTMENT_FACTOR= float(dyn.get("TP_VOL_ADJUSTMENT_FACTOR", 0.3))
TP_MIN_MULTIPLIER       = float(dyn.get("TP_MIN_MULTIPLIER", 1.5))
SL_VOL_REF              = float(dyn.get("SL_VOL_REF", 0.5))
SL_VOL_ADJUSTMENT_FACTOR= float(dyn.get("SL_VOL_ADJUSTMENT_FACTOR", 0.2))
SL_MIN_MULTIPLIER       = float(dyn.get("SL_MIN_MULTIPLIER", 0.8))

# ════════════════════════════════════════════════════════════════════════════
# PARÁMETROS DE ESTRATEGIAS TÉCNICAS
# ════════════════════════════════════════════════════════════════════════════

SMC_LOOKBACK   = int(dyn.get("SMC_LOOKBACK", 20))
SMC_OB_STRENGTH= float(dyn.get("SMC_OB_STRENGTH", 0.005))  # 0.5% mínimo movimiento
WYCKOFF_LOOKBACK = int(dyn.get("WYCKOFF_LOOKBACK", 50))

LIQ_LOOKBACK    = int(dyn.get("LIQ_LOOKBACK", 50))
LIQ_CLUSTER_PCT = float(dyn.get("LIQ_CLUSTER_PCT", 0.002))  # 0.2% tolerancia

BTC_CORR_THRESHOLD = float(dyn.get("BTC_CORR_THRESHOLD", 0.6))

VWAP_BAND_MULT  = float(dyn.get("VWAP_BAND_MULT", 1.5))

# Veto RSI dinámico
RSI_VOL_REF              = float(dyn.get("RSI_VOL_REF", 0.5))
RSI_VOL_ADJUSTMENT_FACTOR= float(dyn.get("RSI_VOL_ADJUSTMENT_FACTOR", 5.0))
GLOBAL_RSI_OB_BASE       = float(dyn.get("GLOBAL_RSI_OB_BASE", 75))
GLOBAL_RSI_OS_BASE       = float(dyn.get("GLOBAL_RSI_OS_BASE", 25))

# ════════════════════════════════════════════════════════════════════════════
# PARÁMETROS DE IA / ML
# ════════════════════════════════════════════════════════════════════════════

MIN_TRADES_FOR_AI      = int(dyn.get("MIN_TRADES_FOR_AI", 30))
AI_BASE_ESTIMATORS     = int(dyn.get("AI_BASE_ESTIMATORS", 100))
AI_MAX_WEIGHT          = float(dyn.get("AI_MAX_WEIGHT", 0.40))
AI_LEARNING_CURVE_STEPS= int(dyn.get("AI_LEARNING_CURVE_STEPS", 45))
RANDOM_STATE           = int(dyn.get("RANDOM_STATE", 42))
MAX_BOOTSTRAP_BUFFER   = int(dyn.get("MAX_BOOTSTRAP_BUFFER", 500))

# ════════════════════════════════════════════════════════════════════════════
# ESTRATEGIAS ACTIVAS Y PESOS DE CAPAS
# ════════════════════════════════════════════════════════════════════════════

_all_strats = {
    "STRATEGY_TREND": "trend",
    "STRATEGY_REVERSION": "reversion",
    "STRATEGY_BREAKOUT": "breakout",
    "STRATEGY_SMC": "smc",
    "STRATEGY_VWAP": "vwap",
    "STRATEGY_LIQUIDITY": "liquidity",
    "STRATEGY_ORDERFLOW": "orderflow",
    "STRATEGY_WYCKOFF": "wyckoff",
    "STRATEGY_BTC_CORR": "btc_corr"
}

ACTIVE_STRATEGIES = []
for key, name in _all_strats.items():
    if dyn.get(key, True):
        ACTIVE_STRATEGIES.append(name)

LAYER_WEIGHTS = dyn.get("LAYER_WEIGHTS", {
    "basic":     1.0,
    "structure": 1.2,
    "context":   0.8,
})

# Pesos por sesión de mercado (hora UTC)
SESSION_WEIGHTS = dyn.get("SESSION_WEIGHTS", {
    "asia":    0.85,
    "europa":  1.00,
    "america": 1.10,
})

# ════════════════════════════════════════════════════════════════════════════
# RISK MANAGER ADAPTATIVO — Núcleo del objetivo personal
# ════════════════════════════════════════════════════════════════════════════
# El bot calcula el riesgo real en función del capital disponible.
# Si el balance cae mucho, se reduce el riesgo automáticamente.
# Si el balance crece, se permite escalar conservadoramente.

ADAPTIVE_RISK_ENABLED   = bool(dyn.get("ADAPTIVE_RISK_ENABLED", True))
ADAPTIVE_RISK_FLOOR     = float(dyn.get("ADAPTIVE_RISK_FLOOR", 0.005))   # 0.5% mínimo
ADAPTIVE_RISK_CEIL      = float(dyn.get("ADAPTIVE_RISK_CEIL", 0.03))     # 3% máximo
ADAPTIVE_DRAWDOWN_FLOOR = float(dyn.get("ADAPTIVE_DRAWDOWN_FLOOR", 0.85))# reducir si balance < 85% inicial
ADAPTIVE_GROWTH_CEIL    = float(dyn.get("ADAPTIVE_GROWTH_CEIL", 1.20))   # aumentar si balance > 120% inicial
