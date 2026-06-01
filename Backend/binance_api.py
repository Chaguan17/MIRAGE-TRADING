import time
import ccxt
import pandas as pd
import logging
import config

logger = logging.getLogger(__name__)


class MirageBinance:
    """
    Wrapper de ccxt.binance para Mirage Trading.

    Gestiona la conexión a Binance Futures con:
    - Paper trading (simulación sin dinero real)
    - Retry automático con backoff exponencial en get_historical_data
    - Leverage siempre limitado por config.clamp_leverage

    Attributes:
        paper_trading (bool): True → no envía órdenes reales.
        client (ccxt.binance): Instancia de ccxt configurada para Futures.
    """

    # ══════════════════════════════════════════════════════════════
    # TAREA 1.1 — Constantes con nombre (antes eran magic numbers)
    # ══════════════════════════════════════════════════════════════
    MAX_RETRIES     = 5    # Reintentos máximos en get_historical_data
    BASE_WAIT_SEC   = 1    # Espera base (se duplica con cada reintento)
    OHLCV_COLUMNS   = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    def __init__(self, api_key, api_secret, paper_trading=True):
        """
        Args:
            api_key (str):      Binance API key (puede ser None en paper mode).
            api_secret (str):   Binance API secret.
            paper_trading (bool): True = simulación, False = real.
        """
        self.paper_trading  = paper_trading
        self._paper_balance = config.PAPER_BALANCE
        self._used_margin   = 0.0 # Margen ocupado por trades abiertos

        key_preview = str(api_key)[:5] if api_key else "NINGUNA"
        print(f"🔑 Llave detectada: {key_preview}...")

        self.client = ccxt.binance({
            'apiKey':          api_key,
            'secret':          api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType':             'future',
                'adjustForTimeDifference': True,
            }
        })
        self.client.set_sandbox_mode(False)

        if self.paper_trading:
            print(f"🛡️ MODO PAPER TRADING | Balance simulado: {self._paper_balance} USDT")

    # ── GESTIÓN DE MARGEN SIMULADO ────────────────────────────────

    def get_available_margin(self):
        """Devuelve el capital 'Cash' disponible para abrir nuevas posiciones."""
        if not self.paper_trading:
            balance = self.client.fetch_balance()
            return float(balance.get('USDT', {}).get('free', 0))
        # En paper: Balance Total - Margen Ocupado
        return max(0, self._paper_balance - self._used_margin)

    def occupy_margin(self, amount):
        if self.paper_trading:
            self._used_margin += amount

    def release_margin(self, amount):
        if self.paper_trading:
            self._used_margin = max(0, self._used_margin - amount)

    def update_paper_equity(self, pnl):
        if self.paper_trading:
            self._paper_balance += pnl

    # ── CONEXIÓN ──────────────────────────────────────────────────

    def check_connection(self):
        """
        Verifica la conexión y sincroniza el reloj con Binance.

        En paper mode solo comprueba la sincronización de tiempo.
        En modo real también obtiene el balance de USDT.

        Returns:
            bool: True si la conexión fue exitosa.
        """
        try:
            self.client.load_time_difference()
            diff_ms = self.client.options['timeDifference']
            print(f"⏱️ Reloj sincronizado (Desfase: {diff_ms} ms)")
            if self.paper_trading:
                print(f"✅ Conexión OK. Balance paper: {self._paper_balance} USDT")
            else:
                balance    = self.client.fetch_balance()
                total_usdt = balance.get('USDT', {}).get('total', 0)
                print(f"✅ Conexión Privada OK. Balance: {total_usdt} USDT")
            return True
        except Exception as e:
            logger.error(f"Error de conexión: {e}")
            print(f"❌ Error de API: {e}")
            return False

    # ── BALANCE ───────────────────────────────────────────────────

    def get_balance(self):
        """
        Devuelve el balance disponible en USDT.

        Returns:
            float: Balance en USDT. En paper mode devuelve el balance simulado.
                   Devuelve 0.0 si hay error en modo real.
        """
        if self.paper_trading:
            return self._paper_balance
        try:
            balance = self.client.fetch_balance()
            return float(balance.get('USDT', {}).get('free', 0))
        except Exception as e:
            logger.warning(f"Error obteniendo balance: {e}")
            print(f"⚠️ Error obteniendo balance: {e}")
            return 0.0
    def get_real_balance(self) -> float:
        """Consulta el balance real de Binance siempre, independiente del modo paper."""
        try:
            balance = self.client.fetch_balance()
            return float(balance.get('USDT', {}).get('total', 0))
        except Exception as e:
            logger.warning(f"No se pudo obtener balance real: {e}")
            return 0.0

    # ── DATOS HISTÓRICOS ──────────────────────────────────────────

    def get_historical_data(self, symbol, timeframe='1m', limit=500):
        """
        Descarga velas OHLCV con reintentos automáticos (backoff exponencial).

        En caso de error transitorio (timeout, rate limit) reintenta hasta
        MAX_RETRIES veces, esperando BASE_WAIT_SEC * 2^intento entre cada una.

        Args:
            symbol (str):    Par de trading (p.ej. 'BTCUSDT').
            timeframe (str): Temporalidad ('1m', '5m', '1h', etc.).
            limit (int):     Número de velas a descargar.

        Returns:
            pd.DataFrame | None: DataFrame con columnas OHLCV y timestamp
                                 como datetime. None si todos los reintentos fallan.

        Example:
            >>> api.get_historical_data('BTCUSDT', '5m', 200)
            # DataFrame con 200 filas
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                bars = self.client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
                df   = pd.DataFrame(bars, columns=self.OHLCV_COLUMNS)
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df

            except ccxt.NetworkError as e:
                wait = self.BASE_WAIT_SEC * (2 ** attempt)
                logger.warning(
                    f"NetworkError en {symbol} (intento {attempt+1}/{self.MAX_RETRIES}): "
                    f"{e} — reintentando en {wait}s"
                )
                print(f"⚠️ Red caída en {symbol}, reintentando en {wait}s...")
                time.sleep(wait)

            except ccxt.RateLimitExceeded as e:
                wait = self.BASE_WAIT_SEC * (2 ** attempt)
                logger.warning(f"RateLimit en {symbol}: {e} — esperando {wait}s")
                time.sleep(wait)

            except Exception as e:
                logger.error(f"Error inesperado en get_historical_data({symbol}): {e}")
                print(f"❌ Error al obtener datos de {symbol}: {e}")
                return None

        logger.error(f"get_historical_data({symbol}) falló tras {self.MAX_RETRIES} intentos")
        print(f"❌ No se pudo obtener datos de {symbol} tras {self.MAX_RETRIES} intentos")
        return None