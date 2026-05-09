import os

# Las llaves se leerán del sistema operativo, no del archivo
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

SYMBOL = 'BTCUSDT'
TIMEFRAME = '1m'

# Modo Sueño
SLEEP_HOUR = 0
SLEEP_MINUTE = 5