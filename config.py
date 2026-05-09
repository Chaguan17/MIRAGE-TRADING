import os
from dotenv import load_dotenv

# Intentar cargar el archivo .env (para local)
load_dotenv()

# Ahora busca en el .env o en el sistema (para el servidor)
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Si sigue sin encontrar nada, avisamos para evitar el error de Binance
if not API_KEY or not API_SECRET:
    print("⚠️ ADVERTENCIA: No se detectaron las llaves API. Revisa tu archivo .env")

SYMBOL = 'BTCUSDT'
TIMEFRAME = '1m'

SLEEP_HOUR = 0
SLEEP_MINUTE = 5