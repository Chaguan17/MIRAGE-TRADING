import os
from dotenv import load_dotenv

load_dotenv()

API_KEY    = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

if not API_KEY or not API_SECRET:
    print("⚠️ ADVERTENCIA: No se detectaron las llaves API. Revisa tu archivo .env")

# ── MERCADO ──────────────────────────────────────────────────────────────────
SYMBOL     = 'BTCUSDT'
TIMEFRAME  = '1m'
LEVERAGE   = 10          # apalancamiento (solo referencia por ahora, en paper no aplica)

# ── CAPITAL ───────────────────────────────────────────────────────────────────
PAPER_BALANCE    = 10.0   # balance simulado inicial en USDT
RISK_PER_TRADE   = 0.02     # porcentaje del balance arriesgado por operación (2%)
MAX_BULLETS      = 4        # divisiones de entrada (DCA)
NO_SL_SIZE_PCT   = 0.005    # tamaño de posición sin SL (0.5% del balance nocional)

# ── GESTIÓN DE RIESGO ─────────────────────────────────────────────────────────
ATR_MULTIPLIER   = 2.0      # distancia del SL en múltiplos de ATR
TP_MULTIPLIER    = 2.0      # distancia del TP en múltiplos de ATR (ATR * mult * 2 antes)
MIN_CONFIDENCE   = 0.55     # confianza mínima para abrir una operación

# ── CICLO CIRCADIANO ──────────────────────────────────────────────────────────
SLEEP_START_HOUR   = 22      # hora de inicio del modo sueño
SLEEP_START_MINUTE = 0
SLEEP_END_HOUR     = 22      # hora de fin del modo sueño
SLEEP_END_MINUTE   = 5