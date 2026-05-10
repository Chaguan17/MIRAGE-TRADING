import ccxt
import pandas as pd


class MirageBinance:
    def __init__(self, api_key, api_secret, paper_trading=True):
        self.paper_trading = paper_trading
        self._paper_balance = 1000.0  # Balance simulado inicial en USDT

        key_preview = str(api_key)[:5] if api_key else "NINGUNA"
        print(f"🔑 Llave detectada: {key_preview}...")

        self.client = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
            }
        })

        self.client.set_sandbox_mode(False)

        if self.paper_trading:
            print("🛡️ MODO PAPER TRADING: Conectado a la red real. Órdenes simuladas.")

    def check_connection(self):
        try:
            self.client.load_time_difference()
            print(f"⏱️ Reloj sincronizado (Desfase: {self.client.options['timeDifference']} ms)")

            if self.paper_trading:
                print(f"✅ Conexión OK. Balance paper: {self._paper_balance} USDT")
            else:
                balance = self.client.fetch_balance()
                total_usdt = balance.get('USDT', {}).get('total', 0)
                print(f"✅ Conexión Privada Exitosa. Balance: {total_usdt} USDT")
            return True
        except Exception as e:
            print(f"❌ Error de API: {e}")
            return False

    def get_balance(self):
        """Devuelve el balance USDT disponible (real o simulado)."""
        if self.paper_trading:
            return self._paper_balance
        try:
            balance = self.client.fetch_balance()
            return float(balance.get('USDT', {}).get('free', 0))
        except Exception as e:
            print(f"⚠️ Error obteniendo balance: {e}")
            return 0.0

    def get_historical_data(self, symbol, timeframe='15m', limit=500):
        try:
            bars = self.client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"❌ Error al obtener datos: {e}")
            return None
