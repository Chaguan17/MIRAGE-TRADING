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
    para mantener un caché local en memoria de los datos OHLCV sin consumir
    peticiones de la API REST (Rate Limits).
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
        self.use_spot_fallback = False
        self.message_count = 0

    def initialize(self, symbols, timeframes):
        self.symbols = [s.lower() for s in symbols]
        self.timeframes = timeframes
        
        for sym in self.symbols:
            self.cache[sym] = {tf: None for tf in timeframes}
            self.latest_candle[sym] = {tf: None for tf in timeframes}
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
            self.message_count = 0
            
            streams = []
            for sym in self.symbols:
                for tf in self.timeframes:
                    streams.append(f"{sym}@kline_{tf}")
                if not self.use_spot_fallback:
                    streams.append(f"{sym}@markPrice")
                else:
                    streams.append(f"{sym}@miniTicker")
            
            base_url = "wss://stream.binance.com/stream" if self.use_spot_fallback else "wss://fstream.binance.com/stream"
            url = f"{base_url}?streams={'/'.join(streams)}"
            logger.info(f"Conectando a Binance Streams ({'Spot Fallback' if self.use_spot_fallback else 'Futures'}): {url}")
            
            self.ws = websocket.WebSocketApp(
                url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            ws_conn_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            ws_conn_thread.start()
            
            # Wait 6 seconds and check if messages arrived (if not on fallback yet)
            if not self.use_spot_fallback:
                self.stop_event.wait(timeout=6)
                if self.is_running and self.message_count == 0:
                    logger.warning("⚠️ No se recibieron mensajes en Futures WS en 6s. Activando Fallback a Spot WS...")
                    self.use_spot_fallback = True
                    try:
                        self.ws.close()
                    except Exception:
                        pass
                    ws_conn_thread.join(timeout=1.0)
                    continue # Reconnect using fallback
            
            # Wait until closed or stopped
            while self.is_running and ws_conn_thread.is_alive():
                self.stop_event.wait(timeout=2)
                
            if self.is_running:
                logger.info("Reconectando MarketStream en 5 segundos...")
                self.stop_event.wait(timeout=5)

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
        logger.info("MarketStream conectado a Binance.")

    def _on_error(self, ws, error):
        logger.error(f"Error en MarketStream: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"MarketStream cerrado: {close_status_code} - {close_msg}")

    def _on_message(self, ws, message):
        try:
            self.message_count += 1
            data = json.loads(message)
            if 'data' not in data:
                return
                
            stream_name = data.get('stream', '')
            payload = data['data']
            
            # 1. Kline stream
            if 'kline' in stream_name or 'k' in payload:
                kline = payload['k']
                sym = payload['s'].lower()
                tf = kline['i']
                
                with self.lock:
                    self.latest_candle[sym][tf] = {
                        'timestamp': kline['t'],
                        'open': float(kline['o']),
                        'high': float(kline['h']),
                        'low': float(kline['l']),
                        'close': float(kline['c']),
                        'volume': float(kline['v']),
                        'is_closed': kline['x']
                    }
            
            # 2. Mark Price (Funding Rate)
            elif 'markPrice' in stream_name or 'r' in payload:
                sym = payload['s'].lower()
                if 'r' in payload:
                    with self.lock:
                        self.funding_rate[sym] = float(payload['r'])
                        
            # 3. Open Interest (if supported)
            elif 'openInterest' in stream_name:
                sym = payload.get('s', '').lower()
                if sym:
                    pass # Not always reliable in standard stream, we'll keep the placeholder

        except Exception as e:
            logger.error(f"Error parseando mensaje WS: {e}")

    def set_historical_cache(self, symbol, tf, df):
        """Inicializa el caché con datos REST."""
        if df is None:
            return
        sym = symbol.lower()
        with self.lock:
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
            
            df = base_df.copy()
            
            last_ts_dt = df.iloc[-1]['timestamp']
            latest_ts_dt = pd.to_datetime(latest['timestamp'], unit='ms')
            
            if latest_ts_dt == last_ts_dt:
                idx = df.index[-1]
                df.at[idx, 'open'] = latest['open']
                df.at[idx, 'high'] = latest['high']
                df.at[idx, 'low'] = latest['low']
                df.at[idx, 'close'] = latest['close']
                df.at[idx, 'volume'] = latest['volume']
            elif latest_ts_dt > last_ts_dt:
                new_row = pd.DataFrame([{
                    'timestamp': latest_ts_dt,
                    'open': latest['open'],
                    'high': latest['high'],
                    'low': latest['low'],
                    'close': latest['close'],
                    'volume': latest['volume']
                }])
                df = pd.concat([df, new_row], ignore_index=True)
            
            # Inyectar Alternative Data en la última fila viva
            idx = df.index[-1]
            df.at[idx, 'funding_rate'] = self.funding_rate.get(sym, 0.0)
                
            return df

stream_manager = MarketStream()
