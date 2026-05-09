import time
import os
import importlib
import config
from binance_api import MirageBinance
from data_engine import DataEngine
from brain import MirageBrain
import risk_manager
import tracker
from datetime import datetime

def check_for_updates(last_mod_times):
    """Vigila si hay cambios en los módulos para asimilarlos en caliente."""
    updated = False
    files_to_watch = ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py'] 
    
    for file in files_to_watch:
        try:
            if os.path.exists(file):
                current_mod_time = os.path.getmtime(file)
                if current_mod_time > last_mod_times.get(file, 0):
                    updated = True
                    last_mod_times[file] = current_mod_time
        except Exception:
            pass
            
    return updated, last_mod_times

def main():
    print("🤖 BIENVENIDO A MIRAGE TRADING - Fase 3: Evolución Sensorial")
    
    # 1. Inicialización de componentes
    api = MirageBinance(config.API_KEY, config.API_SECRET, paper_trading=True)
    engine = DataEngine()
    brain = MirageBrain()
    rm = risk_manager.RiskManager()
    tr = tracker.TradeTracker()

    if not api.check_connection(): return

    print("📚 Iniciando fase de estudio histórico...")
    raw_data = api.get_historical_data(config.SYMBOL, config.TIMEFRAME, limit=1000)
    if raw_data is not None:
        processed_data = engine.prepare_features(raw_data)
        labeled_data = engine.create_labels(processed_data)
        brain.train(labeled_data)
    else:
        print("❌ Error descargando datos históricos.")
        return
        
    print("📈 Cerebro: Entrenamiento completado. Memoria actualizada.")
    print(f"🚀 {config.SYMBOL} está bajo vigilancia. Buscando oportunidades...\n")

    last_mod_times = {file: os.path.getmtime(file) for file in ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py'] if os.path.exists(file)}

    while True:
        # --- 🌙 CICLO CIRCADIANO (MODO SUEÑO) ---
        now = datetime.now()
        if now.hour == config.SLEEP_HOUR and now.minute == config.SLEEP_MINUTE:
            brain.nightly_retrain()
            print("⏳ Esperando al siguiente minuto para despertar...")
            time.sleep(61)
            continue 

        try:
            # A. SEXTO SENTIDO (Hot-Reload) con preservación de memoria
            has_updates, last_mod_times = check_for_updates(last_mod_times)
            if has_updates:
                print("\n💡 ¡OOOO! Me he encontrado con una nueva instrucción.")
                print("🔄 Asimilando nuevo conocimiento...")
                
                memoria_temporal = tr.active_trades 
                
                importlib.reload(risk_manager)
                importlib.reload(config)
                importlib.reload(tracker)
                
                rm = risk_manager.RiskManager()
                tr = tracker.TradeTracker()
                tr.active_trades = memoria_temporal 
                
                print("✅ Actualización inyectada (Memoria Sensorial Preservada).\n")

            # B. OBSERVACIÓN Y TRANSFORMACIÓN (ETL)
            live_data = api.get_historical_data(config.SYMBOL, config.TIMEFRAME, limit=100)
            current_price = live_data.iloc[-1]['close']
            features = engine.prepare_features(live_data)
            atr_current = features.iloc[-1]['ATR'] 
            
            # C. VIGILANCIA DE MERCADO
            tr.update_market_price(current_price)

            # D. DASHBOARD DE RENDIMIENTO
            total, wins, losses, wr, pnl = tr.get_dashboard_stats()
            print("\n" + "="*55)
            print(f"📊 MIRAGE DASHBOARD | Precio Actual: {current_price}")
            print(f"📈 Trades Activos: {len(tr.active_trades)} | Historial CSV: {total} Operaciones")
            print(f"🏆 Win Rate: {wr:.1f}% ({wins}W / {losses}L) | 💰 PnL Total: {pnl:.4f} USDT")
            print("="*55)

            # E. PREDICCIÓN
            prediction, confidence = brain.predict(features)
            
            # F. LÓGICA DE EJECUCIÓN
            if confidence > 0.65 and len(tr.active_trades) == 0:
                action = "LONG" if prediction == 1 else "SHORT"
                print(f"\n🧠 Decisión: {action} | Confianza: {confidence:.2%}")
                
                # Gestión de Riesgo
                sl, tp = rm.calculate_dynamic_stops(current_price, atr_current, action)
                bullets = rm.calculate_averaging_levels(current_price, atr_current, action)
                size = rm.calculate_position_size(17.45, current_price, sl)
                
                print(f"🛡️ Gestión de Riesgo Aplicada:")
                print(f"   - Entrada: {current_price} | Tamaño: {size} BTC")
                print(f"   - SL: {sl:.2f} | TP: {tp:.2f}")
                
                # 💾 REGISTRO CON MEMORIA SENSORIAL (Aquí pasamos los indicadores)
                # Convertimos la última fila de features a diccionario para el tracker
                current_market_features = features.iloc[-1].to_dict()
                tr.register_trade(action, current_price, size, sl, tp, current_market_features)
                print(f"📝 Orden Simulada Registrada con Memoria Sensorial.")
            
            else:
                if len(tr.active_trades) > 0:
                    trade_actual = tr.active_trades[0] 
                    print(f"⏳ Vigilando {config.SYMBOL} [{trade_actual['action']}] | Entrada: {trade_actual['entry_price']} | SL: {trade_actual['sl']:.2f} | TP: {trade_actual['tp']:.2f}")
                else:
                    print(f"⏳ Mercado incierto (Confianza: {confidence:.2%}). Esperando...")

            time.sleep(60)

        except KeyboardInterrupt:
            print("\n🛑 Apagando Mirage Trading...")
            break
        except Exception as e:
            print(f"⚠️ Error en el ciclo: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()