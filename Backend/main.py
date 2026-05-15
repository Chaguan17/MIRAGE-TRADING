import time
import os
import json
import importlib
import logging
import config
from binance_api import MirageBinance
from data_engine import DataEngine
from brain import MirageBrain
import risk_manager
import tracker
import data_engine
from datetime import datetime, time as dtime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================
# ⚙️ CONFIGURACIÓN MULTI-PAIR
# ==========================================
PARES_ACTIVOS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']


def check_for_updates(last_mod_times):
    files = ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py', 'brain.py']
    updated = False
    for f in files:
        try:
            if os.path.exists(f):
                t = os.path.getmtime(f)
                if t > last_mod_times.get(f, 0):
                    updated = True
                    last_mod_times[f] = t
        except OSError as e:
            logger.warning(f"Could not check modification time for {f}: {e}")
    return updated, last_mod_times

def is_sleep_time():
    now = datetime.now().time()
    start = dtime(config.SLEEP_START_HOUR, config.SLEEP_START_MINUTE)
    end = dtime(config.SLEEP_END_HOUR, config.SLEEP_END_MINUTE)
    if start <= end:
        return start <= now < end
    return now >= start or now < end

def connect_with_retry(api):
    attempt = 0
    while attempt < config.MAX_RECONNECT_ATTEMPTS:
        if api.check_connection():
            return True
        attempt += 1
        print(f"🔄 Reconectando... intento {attempt}/{config.MAX_RECONNECT_ATTEMPTS}")
        time.sleep(config.RECONNECT_WAIT_SECONDS)
    print("❌ No se pudo reconectar. Bot detenido.")
    return False

def main():
    print("🤖 MIRAGE TRADING — Arquitectura de Flota MULTI-PAIR")

    api = MirageBinance(config.API_KEY, config.API_SECRET, paper_trading=True)
    if not connect_with_retry(api):
        return

    account_balance = api.get_balance()
    os.makedirs("storage", exist_ok=True)

    # 1. INICIALIZAR EL EJÉRCITO DE BOTS (Un cerebro por moneda)
    bots = {}
    for sym in PARES_ACTIVOS:
        print(f"⚙️ Construyendo motor para {sym}...")
        bots[sym] = {
            'engine': DataEngine(),
            'brain': MirageBrain(symbol=sym), # Pasa el símbolo
            'rm': risk_manager.RiskManager(),
            'tr': tracker.TradeTracker(symbol=sym), # Pasa el símbolo
            'cooldown_left': 0,
            'consecutive_errors': 0
        }

        # Conectar el callback del tracker a SU propio cerebro
        def make_callback(symbol):
            def on_trade_closed(features_dict, result_label, sl_was_used, sl_was_hit):
                bots[symbol]['rm'].register_result(result_label)
                bots[symbol]['brain'].online_update(features_dict, result_label, sl_was_used, sl_was_hit)
            return on_trade_closed
            
        bots[sym]['tr'].set_on_close_callback(make_callback(sym))

        # Descargar historial inicial para esta moneda
        raw_data = api.get_historical_data(sym, config.TIMEFRAME, limit=1000)
        if raw_data is not None:
            bots[sym]['engine'].prepare_features(raw_data)
            bots[sym]['brain'].nightly_retrain()

    sleep_start = dtime(config.SLEEP_START_HOUR, config.SLEEP_START_MINUTE)
    sleep_end = dtime(config.SLEEP_END_HOUR, config.SLEEP_END_MINUTE)
    
    files_to_watch = ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py', 'brain.py']
    last_mod_times = {f: os.path.getmtime(f) for f in files_to_watch if os.path.exists(f)}
    already_slept = False

    while True:
        # ── CICLO CIRCADIANO GLOBAL ──────────────────────────────────────────
        if is_sleep_time():
            if not already_slept:
                print(f"\n🌙 MODO SUEÑO ({datetime.now().strftime('%H:%M')})")
                for sym in PARES_ACTIVOS:
                    bots[sym]['brain'].nightly_retrain()
                already_slept = True
                print(f"⏳ Durmiendo hasta las {sleep_end.strftime('%H:%M')}...")
            time.sleep(30)
            continue

        if already_slept:
            print(f"\n☀️ DESPERTANDO FLOTA")
            already_slept = False

        # A. Hot-Reload (Global)
        has_updates, last_mod_times = check_for_updates(last_mod_times)
        if has_updates:
            print("\n💡 Actualización detectada — recargando módulos base...")
            importlib.reload(risk_manager)
            importlib.reload(config)
            importlib.reload(tracker)
            importlib.reload(data_engine)
            
            for sym in PARES_ACTIVOS:
                memoria = bots[sym]['tr'].active_trades
                bots[sym]['rm'] = risk_manager.RiskManager()
                bots[sym]['tr'] = tracker.TradeTracker(symbol=sym) # Recarga con símbolo
                bots[sym]['tr'].active_trades = memoria
                bots[sym]['tr'].set_on_close_callback(make_callback(sym))
                bots[sym]['engine'] = data_engine.DataEngine()
            print("✅ Toda la flota actualizada.\n")

        if not api.paper_trading:
            account_balance = api.get_balance()

        # Variables para el Dashboard Web
        global_btc_features = None
        web_operaciones_activas = []
        web_pnl_global = 0
        web_trades_global = 0
        web_wins_global = 0

        # ── CICLO DE ANÁLISIS POR MONEDA ─────────────────────────────────────
        print("\n" + "═" * 64)
        for sym in PARES_ACTIVOS:
            b = bots[sym]
            try:
                live_data = api.get_historical_data(sym, config.TIMEFRAME, limit=200)
                if live_data is None:
                    continue

                b['consecutive_errors'] = 0
                current_price = live_data.iloc[-1]['close']
                features = b['engine'].prepare_features(live_data)
                last_row = features.iloc[-1].to_dict()
                atr_current = last_row['ATR']

                # Guardar BTC para correlación de las demás
                if sym == 'BTCUSDT':
                    global_btc_features = features

                # Trailing stop
                with b['tr']._trades_lock:
                    trades_to_process = list(b['tr'].active_trades)

                for t in trades_to_process:
                    if 'is_trailing' not in t:
                        t['is_trailing'] = False
                    new_sl = b['rm'].calculate_trailing_stop(t, current_price, atr_current)
                    if new_sl is not None and new_sl != t['sl']:
                        logger.info(f"{sym} trailing stop updated: {t['sl']} → {new_sl}")
                        print(f"🔺 {sym} Trailing stop: {t['sl']} → {new_sl}")
                        t['sl'] = new_sl
                        t['use_sl'] = True
                        t['is_trailing'] = True

                # Vigilancia
                trades_before = len(b['tr'].active_trades)
                b['tr'].update_market_price(current_price)
                if len(b['tr'].active_trades) < trades_before:
                    _, consecutive_losses = b['rm'].get_streak_info()
                    if consecutive_losses > 0:
                        b['cooldown_left'] = config.COOLDOWN_CANDLES

                # Estadísticas Locales
                total, wins, losses, wr, pnl = b['tr'].get_dashboard_stats()
                web_pnl_global += pnl
                web_trades_global += total
                web_wins_global += wins

                c_wins, c_losses = b['rm'].get_streak_info()
                
                # Imprimir estado en consola por moneda
                print(f"📊 {sym: <8} | {current_price:>10,.2f} USDT | WR: {wr:>4.1f}% | PnL: {pnl:>7.4f}")
                if b['cooldown_left'] > 0:
                    print(f"   ⏸️  Cooldown: {b['cooldown_left']} vela(s)")

                # Preparar datos flotantes para la web
                with b['tr']._trades_lock:
                    active_trades_snapshot = list(b['tr'].active_trades)

                for t in active_trades_snapshot:
                    fpnl = (current_price - t['entry_price']) * t['size'] if t['action'] == 'LONG' else (t['entry_price'] - current_price) * t['size']
                    web_operaciones_activas.append({
                        "pair": sym,
                        "current_price": round(current_price, 2),
                        "type": t['action'],
                        "entry": round(t['entry_price'], 2),
                        "tp": round(t['tp'], 2) if t['tp'] else 0,
                        "sl": round(t['sl'], 2) if t['sl'] else 0,
                        "current_pnl": round(fpnl, 2),
                        "is_trailing": t.get('is_trailing', False)
                    })

                # Predicción
                action_code, confidence, method_name, use_sl = b['brain'].get_consensus_prediction(
                    last_row, features_df=features, btc_features=global_btc_features if sym != 'BTCUSDT' else None
                )

                # Ejecución
                can_trade = (
                    action_code is not None
                    and confidence > config.MIN_CONFIDENCE
                    and len(b['tr'].active_trades) == 0
                    and b['cooldown_left'] == 0
                )

                if can_trade:
                    action_str = "LONG" if action_code == 1 else "SHORT"
                    sl, tp = b['rm'].calculate_dynamic_stops(current_price, atr_current, action_str)
                    size = b['rm'].calculate_position_size(account_balance, current_price, sl if use_sl else None)
                    if size > 0:
                        print(f"   🧠 SEÑAL: {action_str} | {method_name.upper()} | conf: {confidence:.2%} | size: {size}")
                        b['tr'].register_trade(action_str, current_price, size, sl, tp, last_row, use_sl)
                else:
                    if b['cooldown_left'] > 0:
                        b['cooldown_left'] -= 1

            except Exception as e:
                b['consecutive_errors'] += 1
                logger.error(f"Error processing {sym}: {e}", exc_info=True)
                print(f"⚠️ Error en {sym}: {e}")
        
        print("═" * 64)

        # ── ACTUALIZAR EL DASHBOARD WEB ──────────────────────────────────────
        try:
            win_rate_global = (web_wins_global / web_trades_global * 100) if web_trades_global > 0 else 0
            estado_en_vivo = {
                "pnl_total": round(float(web_pnl_global), 2),
                "win_rate": round(float(win_rate_global), 1),
                "total_operaciones": int(web_trades_global),
                "operaciones_activas": web_operaciones_activas
            }
            with open("storage/live_state.json", "w", encoding="utf-8") as f:
                json.dump(estado_en_vivo, f)
        except IOError as e:
            logger.error(f"Failed to write live_state.json: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating dashboard: {e}")

        time.sleep(60)

if __name__ == "__main__":
    main()