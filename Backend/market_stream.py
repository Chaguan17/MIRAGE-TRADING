import threading
import json
import time
import pandas as pd
import logging
import websocket

logger = logging.getLogger(__name__)


class MarketStream:
    """
    Gestiona una conexión WebSocket a Binance Futures (fstream.binance.com)
    para mantener un caché local en memoria de los datos OHLCV en tiempo real.
    """

    def __init__(self):
        self.symbols = []
        self.timeframes = []

        # cache[symbol][timeframe] = pd.DataFrame
        self.cache = {}
        self.latest_candle = {}

        # Alternative Data
        self.funding_rate = {}
        self.open_interest = {}

        self.lock = threading.Lock()
        self.ws = None
        self.ws_thread = None
        self.is_running = False
        self.stop_event = threading.Event()

    def initialize(self, symbols, timeframes):
        self.symbols = [str(s).strip().lower() for s in symbols]
        self.timeframes = list(timeframes)

        with self.lock:
            for sym in self.symbols:
                if sym not in self.cache:
                    self.cache[sym] = {tf: None for tf in self.timeframes}
                    self.latest_candle[sym] = {tf: None for tf in self.timeframes}
                    self.funding_rate[sym] = 0.0
                    self.open_interest[sym] = 0.0

    def start(self):
        if not self.symbols:
            logger.warning("No hay símbolos para suscribir al MarketStream.")
            return

        self.is_running = True
        self.stop_event.clear()
        self.ws_thread = threading.Thread(target=self._run_ws, daemon=True)
        self.ws_thread.start()

    def _run_ws(self):
        while self.is_running:
            streams = []
            for sym in self.symbols:
                for tf in self.timeframes:
                    streams.append(f"{sym}@kline_{tf}")
                streams.append(f"{sym}@markPrice@1s")

            url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"
            logger.info(f"⚡ Conectando a Binance Futures WebSocket Stream: {url}")

            self.ws = websocket.WebSocketApp(
                url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open,
            )

            ws_conn_thread = threading.Thread(target=self.ws.run_forever, kwargs={'ping_interval': 20, 'ping_timeout': 10}, daemon=True)
            ws_conn_thread.start()

            # Wait while connection is alive
            while self.is_running and ws_conn_thread.is_alive():
                self.stop_event.wait(timeout=2)

            if self.is_running:
                logger.info(
                    "🔄 Reconectando MarketStream de Binance Futuros en 3 segundos..."
                )
                self.stop_event.wait(timeout=3)

    def stop(self):
        self.is_running = False
        self.stop_event.set()
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2.0)

    def _on_open(self, ws):
        logger.info(
            "✅ MarketStream conectado exitosamente a Binance Futuros (fstream.binance.com)."
        )

    def _on_error(self, ws, error):
        logger.error(f"❌ Error en MarketStream: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"ℹ️ MarketStream cerrado: {close_status_code} - {close_msg}")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if "data" not in data:
                return

            stream_name = data.get("stream", "")
            payload = data["data"]

            # 1. Kline stream
            if "kline" in stream_name or "k" in payload:
                kline = payload.get("k", {})
                sym = payload.get("s", "").lower()
                tf = kline.get("i", "")

                if sym and tf:
                    candle_item = {
                        "timestamp": kline["t"],
                        "open": float(kline["o"]),
                        "high": float(kline["h"]),
                        "low": float(kline["l"]),
                        "close": float(kline["c"]),
                        "volume": float(kline["v"]),
                        "is_closed": kline["x"],
                        "last_update": time.time(),
                    }
                    with self.lock:
                        if sym not in self.latest_candle:
                            self.latest_candle[sym] = {}
                        self.latest_candle[sym][tf] = candle_item

            # 2. Mark Price (Funding Rate)
            elif "markPrice" in stream_name or "r" in payload:
                sym = payload.get("s", "").lower()
                if sym and "r" in payload:
                    with self.lock:
                        self.funding_rate[sym] = float(payload["r"])

        except Exception as e:
            logger.error(f"Error parseando mensaje WS: {e}")

    def set_historical_cache(self, symbol, tf, df):
        """Inicializa el caché con datos REST."""
        if df is None or df.empty:
            return
        sym = symbol.lower()
        with self.lock:
            if sym not in self.cache:
                self.cache[sym] = {}
            self.cache[sym][tf] = df.copy()

    def get_data(self, symbol, tf):
        """Devuelve el DataFrame combinado con la última vela del WebSocket."""
        sym = symbol.lower()
        with self.lock:
            base_df = self.cache.get(sym, {}).get(tf)
            latest = self.latest_candle.get(sym, {}).get(tf)

            if base_df is None or base_df.empty:
                return None

            if latest is None:
                return base_df.copy()

            last_ts_dt = base_df.iloc[-1]["timestamp"]
            latest_ts_dt = pd.to_datetime(latest["timestamp"], unit="ms")

            if latest_ts_dt == last_ts_dt:
                # Vela en curso: actualizar la última fila del caché REAL, no de una copia
                idx = base_df.index[-1]
                base_df.at[idx, "open"] = latest["open"]
                base_df.at[idx, "high"] = latest["high"]
                base_df.at[idx, "low"] = latest["low"]
                base_df.at[idx, "close"] = latest["close"]
                base_df.at[idx, "volume"] = latest["volume"]

            elif latest_ts_dt > last_ts_dt:
                # Vela nueva cerrada: extender el caché REAL, con límite para no crecer sin fin
                new_row = pd.DataFrame(
                    [
                        {
                            "timestamp": latest_ts_dt,
                            "open": latest["open"],
                            "high": latest["high"],
                            "low": latest["low"],
                            "close": latest["close"],
                            "volume": latest["volume"],
                        }
                    ]
                )
                base_df = pd.concat([base_df, new_row], ignore_index=True)
                # Evita crecimiento indefinido en memoria durante sesiones largas
                max_rows = 1500
                if len(base_df) > max_rows:
                    base_df = base_df.iloc[-max_rows:].reset_index(drop=True)
                self.cache[sym][tf] = base_df  # Persistir de vuelta en el caché real

            # A partir de aquí, trabajamos sobre una copia para no exponer el buffer interno mutable
            df = base_df.copy()
            idx = df.index[-1]
            df.at[idx, "funding_rate"] = self.funding_rate.get(sym, 0.0)

            return df

    def is_data_fresh(self, symbol, tf, max_age_seconds=180):
        """
        Verifica si los datos del símbolo y timeframe están recibiendo ticks activos vía WebSocket.
        Retorna False solo si no se han recibido ticks del WebSocket dentro del umbral max_age_seconds.
        """
        sym = symbol.lower()
        with self.lock:
            latest = self.latest_candle.get(sym, {}).get(tf)
            if latest and "last_update" in latest:
                age = time.time() - float(latest["last_update"])
                return age <= max_age_seconds

            # Fallback seguro: si el stream aún no ha recibido ticks pero tiene caché REST inicializado
            base_df = self.cache.get(sym, {}).get(tf)
            if base_df is not None and not base_df.empty:
                last_ts = base_df['timestamp'].iloc[-1]
                try:
                    if hasattr(last_ts, 'timestamp'):
                        ts_sec = last_ts.timestamp()
                    else:
                        ts_sec = float(last_ts) / 1000.0 if float(last_ts) > 1e11 else float(last_ts)
                    age = time.time() - ts_sec
                    return age < max_age_seconds
                except Exception:
                    return False

            return False


stream_manager = MarketStream()
