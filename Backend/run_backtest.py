import os
import time
import pandas as pd
import config as cfg
from binance_api import MirageBinance
from backtester import SimpleBacktester

def fetch_large_history(api, symbol, timeframe, limit):
    """
    Descarga una cantidad arbitraria de velas paginando mediante ccxt.
    """
    print(f"Descargando {limit} velas de {symbol} en {timeframe}...")
    
    # Calcular ms por vela
    # 15m = 15 * 60 * 1000 = 900,000 ms
    tf_ms = api.client.parse_timeframe(timeframe) * 1000
    
    # Binance permite hasta 1500 velas por llamada. Usaremos 1000 por seguridad.
    batch_size = 1000
    
    # Calcular desde qué timestamp empezar
    now_ms = api.client.milliseconds()
    start_time = now_ms - (limit * tf_ms)
    
    all_bars = []
    current_time = start_time
    
    while len(all_bars) < limit:
        remaining = limit - len(all_bars)
        fetch_limit = min(batch_size, remaining)
        
        try:
            print(f"  -> Obteniendo {fetch_limit} velas desde {pd.to_datetime(current_time, unit='ms')}")
            bars = api.client.fetch_ohlcv(symbol, timeframe=timeframe, since=current_time, limit=fetch_limit)
            
            if not bars:
                break
                
            all_bars.extend(bars)
            
            # Avanzar el tiempo a la última vela recibida + 1 ms
            current_time = bars[-1][0] + 1
            
            time.sleep(0.5) # Respetar rate limits
            
        except Exception as e:
            print(f"Error durante paginación: {e}")
            break
            
    df = pd.DataFrame(all_bars, columns=api.OHLCV_COLUMNS)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Eliminar posibles duplicados
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    return df.tail(limit)

def main():
    print("Iniciando simulación de Backtesting (Deep Run)...")
    
    # 1. Configuración de la prueba
    symbol = "SOLUSDT"
    timeframe = "15m"
    limit = 30000  # ~312 días en 15m

    # 2. Conectar a Binance (sin keys para datos públicos)
    api = MirageBinance(None, None, paper_trading=True)
    
    # 3. Obtener datos históricos con paginación
    df = fetch_large_history(api, symbol, timeframe, limit)
    
    if df is None or df.empty:
        print("Error: No se pudieron obtener datos históricos.")
        return
        
    print(f"Datos descargados con éxito: {len(df)} velas.")
    print(f"Rango: {df['timestamp'].iloc[0]} a {df['timestamp'].iloc[-1]}")
    
    # 4. Iniciar Backtester
    # NOTA: En un test tan grande, la IA irá entrenándose a medida que ve nuevos datos.
    bt = SimpleBacktester(symbol=symbol, raw_df=df)
    bt.run()

if __name__ == "__main__":
    main()
