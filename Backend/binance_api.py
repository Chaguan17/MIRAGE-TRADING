import time
import ccxt
import pandas as pd
import logging
import config

import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

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
        logger.info(f"Llave detectada: {key_preview}...")

        self.client = ccxt.binance({
            'apiKey':          api_key,
            'secret':          api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType':             'future',
                'adjustForTimeDifference': True,
                'recvWindow':              60000,
                'warnOnFetchOpenOrdersWithoutSymbol': False,
            }
        })
        self.client.set_sandbox_mode(False)

        if not self.paper_trading:
            try:
                self.client.load_time_difference()
            except Exception as e:
                logger.warning(f"Sincronización inicial de tiempo con Binance: {e}")
        else:
            logger.info(f"MODO PAPER TRADING | Balance simulado: {self._paper_balance} USDT")

    # ── GESTIÓN DE MARGEN SIMULADO ────────────────────────────────

    def get_available_margin(self):
        """Devuelve el capital 'Cash' disponible para abrir nuevas posiciones."""
        if not self.paper_trading:
            try:
                balance = self.client.fetch_balance()
                return float(balance.get('USDT', {}).get('free', 0))
            except Exception as e:
                err_str = str(e)
                if "-1021" in err_str or "Timestamp" in err_str:
                    logger.warning("⏱️ Desfase de reloj detectado con Binance (-1021). Re-sincronizando tiempo...")
                    try:
                        self.client.load_time_difference()
                        balance = self.client.fetch_balance()
                        return float(balance.get('USDT', {}).get('free', 0))
                    except Exception as retry_err:
                        logger.error(f"Error tras re-sincronización de tiempo: {retry_err}")
                else:
                    logger.error(f"Error obteniendo balance disponible de Binance: {e}")
                return 0.0
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

    def setup_symbol(self, symbol: str, leverage: int):
        """
        Configura el símbolo para usar Margen Aislado y el apalancamiento deseado.
        """
        if self.paper_trading:
            print(f"🛡️ [PAPER] {symbol} configurado (simulado) a ISOLATED margin, {leverage}x leverage")
            return True
            
        try:
            # CCXT maneja la conversión si se requiere
            margin_ok = True
            try:
                self.client.set_margin_mode('isolated', symbol)
                logger.info(f"✅ {symbol}: Margen cambiado a ISOLATED")
            except Exception as e:
                err_str = str(e)
                if "No need to change" in err_str or "MARGIN_TYPE_UNCHANGED" in err_str:
                    logger.info(f"ℹ️ {symbol}: Modo de margen ya es ISOLATED")
                elif "-4067" in err_str or "open orders" in err_str.lower():
                    logger.warning(f"⚠️ {symbol}: No se pudo cambiar el margen porque existen órdenes abiertas (SL/TP activo). Asumiendo margen correcto.")
                else:
                    logger.error(f"❌ {symbol}: Error al cambiar margin_type a ISOLATED: {e}")
                    print(f"⚠️ {symbol}: Error al cambiar modo de margen a ISOLATED: {e}")
                    margin_ok = False
                    
            try:
                self.client.set_leverage(leverage, symbol)
                logger.info(f"✅ {symbol}: Apalancamiento ajustado a {leverage}x")
            except Exception as e:
                logger.error(f"❌ {symbol}: Error al ajustar leverage: {e}")
                return False
                
            return margin_ok
        except Exception as e:
            logger.error(f"❌ Error en setup_symbol para {symbol}: {e}")
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
            return float(balance.get('USDT', {}).get('total', 0))
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

    def get_open_positions(self, symbols=None):
        """
        Devuelve un diccionario { 'ETHUSDT': {'contracts': 0.011, 'side': 'SHORT', 'sl': 1881.81, 'tp': 0.0, ...} }
        con las posiciones reales abiertas en Binance Futuros y sus TP/SL activos.
        """
        if self.paper_trading:
            return {}
        try:
            self.client.options['warnOnFetchOpenOrdersWithoutSymbol'] = False
            try:
                raw_positions = self.client.fetch_positions(symbols)
            except Exception as pos_err:
                if "-1021" in str(pos_err) or "timestamp" in str(pos_err).lower():
                    try:
                        self.client.load_time_difference()
                    except Exception:
                        pass
                    raw_positions = self.client.fetch_positions(symbols)
                else:
                    raise pos_err

            open_orders_by_symbol = {}
            try:
                all_orders = self.client.fetch_open_orders()
            except Exception as order_err:
                if "-1021" in str(order_err) or "timestamp" in str(order_err).lower():
                    try:
                        self.client.load_time_difference()
                        all_orders = self.client.fetch_open_orders()
                    except Exception as retry_err:
                        all_orders = []
                        logger.warning(f"No se pudieron consultar órdenes abiertas globales tras re-sincronizar reloj: {retry_err}")
                else:
                    all_orders = []
                    logger.warning(f"No se pudieron consultar órdenes abiertas globales: {order_err}")

            # Consultar órdenes condicionales de Binance Futuros (Algo Orders: STOP, TAKE_PROFIT)
            algo_orders_list = []
            try:
                if hasattr(self.client, 'fapiPrivateGetOpenAlgoOrders'):
                    algo_orders_raw = self.client.fapiPrivateGetOpenAlgoOrders()
                    if isinstance(algo_orders_raw, list):
                        algo_orders_list = algo_orders_raw
            except Exception as algo_err:
                logger.debug(f"fapiPrivateGetOpenAlgoOrders error: {algo_err}")

            for o in all_orders:
                raw_sym = o.get('symbol', '').replace('/', '').replace(':USDT', '')
                if raw_sym not in open_orders_by_symbol:
                    open_orders_by_symbol[raw_sym] = []
                open_orders_by_symbol[raw_sym].append(o)

            for ao in algo_orders_list:
                raw_sym = ao.get('symbol', '').replace('/', '').replace(':USDT', '')
                if raw_sym not in open_orders_by_symbol:
                    open_orders_by_symbol[raw_sym] = []
                open_orders_by_symbol[raw_sym].append({
                    'id': ao.get('algoId'),
                    'symbol': raw_sym,
                    'type': ao.get('orderType'),
                    'side': ao.get('side'),
                    'stopPrice': float(ao.get('triggerPrice') or ao.get('price') or 0.0),
                    'triggerPrice': float(ao.get('triggerPrice') or 0.0),
                    'price': float(ao.get('price') or 0.0),
                    'info': ao
                })

            res = {}
            for p in raw_positions:
                contracts = float(p.get('contracts', 0) or 0)
                clean_sym = p.get('symbol', '').replace('/', '').replace(':USDT', '')
                if contracts > 0:
                    sl = 0.0
                    tp = 0.0
                    orders = open_orders_by_symbol.get(clean_sym, [])
                    entry_p = float(p.get('entryPrice', 0) or 0)
                    is_long = str(p.get('side', '')).upper() == 'LONG'
                    for o in orders:
                        info = o.get('info', {})
                        orig_type = str(info.get('origType', '') or info.get('type', '') or o.get('type', '') or '').upper()
                        trigger_p = float(
                            o.get('stopPrice') or
                            o.get('triggerPrice') or
                            info.get('stopPrice') or
                            info.get('triggerPrice') or
                            o.get('price') or
                            0.0
                        )
                        if trigger_p <= 0:
                            continue

                        # Clasificación precisa de orden condicional Stop Loss vs Take Profit
                        if 'STOP' in orig_type and 'TAKE' not in orig_type:
                            sl = trigger_p
                        elif 'TAKE' in orig_type:
                            tp = trigger_p
                        else:
                            # Fallback si origType no trae STOP explícito: comparar precio gatillo vs precio de entrada
                            if entry_p > 0:
                                if is_long:
                                    if trigger_p < entry_p:
                                        sl = trigger_p
                                    else:
                                        tp = trigger_p
                                else:
                                    if trigger_p > entry_p:
                                        sl = trigger_p
                                    else:
                                        tp = trigger_p

                    res[clean_sym] = {
                        'contracts': contracts,
                        'side': str(p.get('side', '')).upper(),
                        'entry_price': float(p.get('entryPrice', 0) or 0),
                        'current_price': float(p.get('markPrice', 0) or p.get('entryPrice', 0) or 0),
                        'pnl': float(p.get('unrealizedPnl', 0) or 0),
                        'sl': sl,
                        'tp': tp,
                    }
            return res
        except Exception as e:
            logger.error(f"Error fetching open positions from Binance: {e}")
            return None