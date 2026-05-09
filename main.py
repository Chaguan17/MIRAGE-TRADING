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
    # Añadimos los métodos a la vigilancia para que el bot aprenda si cambias una regla técnica
    files_to_watch = ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py', 'brain.py'] 
    
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
        # El cerebro ahora es capaz de entrenarse con las columnas sensoriales completas
        brain.nightly_retrain() 
    else:
        print("❌ Error descargando datos históricos.")
        return
        
    print(f"🚀 {config.SYMBOL} bajo vigilancia. Buscando oportunidades con Comité de Expertos...\n")

    last_mod_times = {file: os.path.getmtime(file) for file in ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py', 'brain.py'] if os.path.exists(file)}

    while True:
        # --- 🌙 CICLO CIRCADIANO (MODO SUEÑO) ---
        now = datetime.now()
        if now.hour == config.SLEEP_HOUR and now.minute == config.SLEEP_MINUTE:
            brain.nightly_retrain()
            print("⏳ Esperando al siguiente minuto para despertar con un cerebro evolucionado...")
            time.sleep(61)
            continue 

        try:
            # A. SEXTO SENTIDO (Hot-Reload)
            has_updates, last_mod_times = check_for_updates(last_mod_times)
            if has_updates:
                print("\n💡 ¡Actualización detectada! Re-sincronizando sistemas...")
                memoria_temporal = tr.active_trades 
                
                importlib.reload(risk_manager)
                importlib.reload(config)
                importlib.reload(tracker)
                importlib.reload(data_engine) # Recargar sentidos por si cambiaste indicadores
                
                rm = risk_manager.RiskManager()
                tr = tracker.TradeTracker()
                tr.active_trades = memoria_temporal 
                print("✅ Sistemas actualizados y memoria de trades preservada.\n")

            # B. OBSERVACIÓN Y TRANSFORMACIÓN (Sentidos)
            live_data = api.get_historical_data(config.SYMBOL, config.TIMEFRAME, limit=100)
            if live_data is None: continue
            
            current_price = live_data.iloc[-1]['close']
            features = engine.prepare_features(live_data)
            last_features_row = features.iloc[-1].to_dict() # Foto actual del mercado
            atr_current = last_features_row['ATR'] 
            
            # C. VIGILANCIA DE MERCADO (Actualiza SL/TP)
            tr.update_market_price(current_price)

            # D. DASHBOARD DE RENDIMIENTO
            total, wins, losses, wr, pnl = tr.get_dashboard_stats()
            print("\n" + "="*55)
            print(f"📊 MIRAGE DASHBOARD | Precio Actual: {current_price}")
            print(f"📈 Activos: {len(tr.active_trades)} | Historial: {total} Op. | PnL: {pnl:.4f} USDT")
            print(f"🏆 Win Rate: {wr:.1f}% ({wins}W / {losses}L)")
            print("="*55)

            # E. PREDICCIÓN POR CONSENSO (Sincronizado con brain.py v1.1)
            # Ahora pedimos Acción, Confianza y cuál de los expertos (Trend/Reversion/Breakout) habló
            action_code, confidence, method_name = brain.get_consensus_prediction(last_features_row)
            
            # F. LÓGICA DE EJECUCIÓN (Autodependencia)
            if action_code is not None and confidence > 0.65 and len(tr.active_trades) == 0:
                action_str = "LONG" if action_code == 1 else "SHORT"
                
                print(f"\n🧠 DECISIÓN: {action_str} | Método: {method_name.upper()}")
                print(f"🎯 Confianza del Comité: {confidence:.2%}")
                
                # Gestión de Riesgo Dinámica
                sl, tp = rm.calculate_dynamic_stops(current_price, atr_current, action_str)
                size = rm.calculate_position_size(17.45, current_price, sl)
                
                print(f"🛡️ Riesgo: SL {sl:.2f} | TP {tp:.2f} | Size: {size} BTC")
                
                # REGISTRO CON MEMORIA SENSORIAL COMPLETA
                tr.register_trade(action_str, current_price, size, sl, tp, last_features_row)
                print(f"📝 Registrado en CSV para futuro estudio nocturno.")
            
            else:
                if len(tr.active_trades) > 0:
                    t = tr.active_trades[0]
                    dist_tp = abs(current_price - t['tp'])
                    print(f"⏳ Vigilando {t['action']} | Entrada: {t['entry_price']} | Dist. TP: {dist_tp:.2f}")
                else:
                    print(f"⏳ Analizando... [IA: {confidence:.2%} | Sugiere: {method_name}]")

            time.sleep(60)

        except Exception as e:
            print(f"⚠️ Error en el ciclo: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()