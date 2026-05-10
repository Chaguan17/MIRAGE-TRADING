import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

if not API_KEY or not API_SECRET:
    print("⚠️ ADVERTENCIA: No se detectaron las llaves API. Revisa tu archivo .env")

SYMBOL = 'BTCUSDT'
TIMEFRAME = '1m'

# ─── Ciclo Circadiano ───────────────────────────────────────────────────────
# Hora en que el bot entra en MODO SUEÑO para reentrenar el modelo.
# Se define como una ventana: desde SLEEP_START_HOUR:SLEEP_START_MINUTE
# hasta SLEEP_END_HOUR:SLEEP_END_MINUTE (hora local del servidor).
# Durante ese bloque NO opera; al salir, despierta con el cerebro actualizado.
SLEEP_START_HOUR   = 0    # 00:00 — medianoche
SLEEP_START_MINUTE = 0
SLEEP_END_HOUR     = 0    # 00:05 — vuelve a operar pasados 5 minutos
SLEEP_END_MINUTE   = 5
