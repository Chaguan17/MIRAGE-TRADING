import time
import os
import shutil
import json
import importlib
import logging
import config
import brain
from binance_api import MirageBinance
import data_engine
import risk_manager
import tracker
from datetime import datetime, time as dtime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

FILES_TO_WATCH = ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py', 'brain.py', 'storage/settings.json']

def check_for_updates(last_mod_times):
    updated = False
    for f in FILES_TO_WATCH:
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

def make_callback(symbol, bots, api):
    """
    Genera el callback de cierre de trade para un símbolo.
    Se extrae a función de nivel de módulo para evitar problemas de scope
    en el hot-reload (el original estaba definido dentro del bucle for).
    """
    def on_trade_closed(features_dict, result_label, sl_was_used, sl_was_hit, pnl, margin_released):
        # Sinergia: Actualizamos el balance real/simulado de la API
        api.release_margin(margin_released)
        api.update_paper_equity(pnl)
        
        bots[symbol]['rm'].register_result(result_label)
        bots[symbol]['brain'].online_update(features_dict, result_label, sl_was_used, sl_was_hit)
    return on_trade_closed

def main():
    print("🤖 MIRAGE TRADING — Arquitectura de Flota MULTI-PAIR")

    api = MirageBinance(config.API_KEY, config.API_SECRET, paper_trading=True)
    if not connect_with_retry(api):
        return

    account_balance = api.get_balance()
    os.makedirs("storage", exist_ok=True)

    pares_activos = config.PARES_ACTIVOS

    # Sinergia: Motor de contexto para BTC (necesario para vetos de IA incluso si no se opera)
    btc_context_engine = None
    if 'BTCUSDT' not in pares_activos:
        btc_context_engine = data_engine.DataEngine()

    bots = {}
    for sym in pares_activos:
        print(f"⚙️ Construyendo motor para {sym}...")
        bots[sym] = {
            'engine': data_engine.DataEngine(),
            'brain': brain.MirageBrain(symbol=sym),
            'rm': risk_manager.RiskManager(),
            'tr': tracker.TradeTracker(symbol=sym),
            'cooldown_left': 0,
            'consecutive_errors': 0
        }

        cb = make_callback(sym, bots, api)
        bots[sym]['tr'].set_on_close_callback(cb)

        raw_data = api.get_historical_data(sym, config.TIMEFRAME, limit=1000)
        if raw_data is not None:
            bots[sym]['last_features'] = bots[sym]['engine'].prepare_features(raw_data)
            bots[sym]['brain'].nightly_retrain()
        else:
            bots[sym]['last_features'] = None
            logger.warning(f"No se pudo obtener datos iniciales para {sym}")

    sleep_start = dtime(config.SLEEP_START_HOUR, config.SLEEP_START_MINUTE)
    sleep_end = dtime(config.SLEEP_END_HOUR, config.SLEEP_END_MINUTE)

    last_mod_times = {f: os.path.getmtime(f) for f in FILES_TO_WATCH if os.path.exists(f)}
    already_slept = False
    last_backup_dt = None

    while True:
        # ── CICLO CIRCADIANO GLOBAL ──────────────────────────────────────────
        if is_sleep_time():
            if not already_slept:
                print(f"\n🌙 MODO SUEÑO ({datetime.now().strftime('%H:%M')})")
                for sym in pares_activos:
                    bots[sym]['brain'].nightly_retrain()
                already_slept = True
                logger.info(f"⏳ Modo Sueño: Flota en mantenimiento hasta las {sleep_end.strftime('%H:%M')}")
            time.sleep(30)
            continue

        if already_slept:
            print(f"\n☀️ DESPERTANDO FLOTA")
            already_slept = False

        # --- SISTEMA DE SEGURIDAD: BACKUP AUTOMÁTICO ---
        now_dt = datetime.now()
        if last_backup_dt is None or (now_dt - last_backup_dt).days >= 1:
            if os.path.exists(config.DB_PATH):
                backup_name = f"mirage_safe_{now_dt.strftime('%Y%m%d_%H%M')}.db"
                backup_path = os.path.join(config.BACKUP_DIR, backup_name)
                shutil.copy(config.DB_PATH, backup_path)
                logger.info(f"🛡️ Seguridad: Backup de base de datos creado en {backup_name}")
            last_backup_dt = now_dt

        has_updates, last_mod_times = check_for_updates(last_mod_times)
        if has_updates:
            print("\n💡 Actualización detectada — recargando módulos base...")
            importlib.reload(risk_manager)
            importlib.reload(config)
            importlib.reload(tracker)
            importlib.reload(data_engine)
            importlib.reload(brain)
            logger.info("⚙️ Configuración actualizada desde el Dashboard")
            # Actualizar pares por si cambiaron en config
            pares_activos = config.PARES_ACTIVOS

            for sym in pares_activos:
                if sym not in bots:
                    # Nuevo par añadido en caliente
                    bots[sym] = {
                        'engine': data_engine.DataEngine(),
                        'brain': brain.MirageBrain(symbol=sym),
                        'rm': risk_manager.RiskManager(),
                        'tr': tracker.TradeTracker(symbol=sym),
                        'cooldown_left': 0,
                        'consecutive_errors': 0,
                        'last_features': None,
                    }
                else:
                    memoria = bots[sym]['tr'].active_trades
                    bots[sym]['rm'] = risk_manager.RiskManager()
                    bots[sym]['tr'] = tracker.TradeTracker(symbol=sym)
                    bots[sym]['tr'].active_trades = memoria
                    bots[sym]['engine'] = data_engine.DataEngine()
                    bots[sym]['brain'] = brain.MirageBrain(symbol=sym) # Re-instanciar IA

                cb = make_callback(sym, bots, api)
                bots[sym]['tr'].set_on_close_callback(cb)

            print("✅ Toda la flota actualizada.\n")

        account_balance = api.get_balance()
        available_margin = api.get_available_margin()

        global_btc_features = None
        web_operaciones_activas = []
        web_pnl_global = 0
        web_trades_global = 0
        web_wins_global = 0

        # --- PASO CRÍTICO: Obtener contexto global de BTC antes que el resto ---
        if btc_context_engine:
            btc_raw = api.get_historical_data('BTCUSDT', config.TIMEFRAME, limit=200)
            if btc_raw is not None:
                global_btc_features = btc_context_engine.prepare_features(btc_raw)
        elif 'BTCUSDT' in bots:
            # Si BTC está en la flota, se procesará dentro del loop y llenará global_btc_features
            pass

        print("\n" + "═" * 64)
        for sym in pares_activos:
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

                if sym == 'BTCUSDT':
                    global_btc_features = features

                with b['tr']._trades_lock:
                    trades_to_process = list(b['tr'].active_trades)

                for t in trades_to_process:
                    if 'is_trailing' not in t:
                        t['is_trailing'] = False
                    if 'is_breakeven' not in t:
                        t['is_breakeven'] = False

                    # --- Gestión de Breakeven Automático ---
                    new_be = b['rm'].calculate_breakeven_stop(t, current_price)
                    if new_be is not None:
                        logger.info(f"🛡️ {sym} Breakeven: SL movido a entrada ({new_be})")
                        t['sl'] = new_be
                        t['is_breakeven'] = True
                        t['use_sl'] = True
                        t['is_trailing'] = False # El trailing toma el control después

                    new_sl = b['rm'].calculate_trailing_stop(t, current_price, atr_current)
                    if new_sl is not None and new_sl != t['sl']:
                        logger.info(f"{sym} trailing stop updated: {t['sl']} → {new_sl}")
                        print(f"🔺 {sym} Trailing stop: {t['sl']} → {new_sl}")
                        t['sl'] = new_sl
                        t['use_sl'] = True
                        t['is_trailing'] = True

                trades_before = len(b['tr'].active_trades)
                b['tr'].update_market_price(current_price)
                if len(b['tr'].active_trades) < trades_before:
                    _, consecutive_losses = b['rm'].get_streak_info()
                    if consecutive_losses > 0:
                        b['cooldown_left'] = config.COOLDOWN_CANDLES

                total, wins, losses, wr, pnl = b['tr'].get_dashboard_stats()
                web_pnl_global += pnl
                web_trades_global += total
                web_wins_global += wins

                c_wins, c_losses = b['rm'].get_streak_info()

                print(f"📊 {sym: <8} | {current_price:>10,.2f} USDT | WR: {wr:>4.1f}% | PnL: {pnl:>7.4f}")
                if b['cooldown_left'] > 0:
                    print(f"   ⏸️  Cooldown: {b['cooldown_left']} vela(s)")

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
                        "is_trailing": t.get('is_trailing', False),
                        "is_breakeven": t.get('is_breakeven', False),
                        "size": t.get('size', 0),
                        "position_value": t.get('size', 0) * t.get('entry_price', 0)
                    })

                # --- Lógica de Scale-In (DCA) ---
                if 0 < len(active_trades_snapshot) < config.MAX_BULLETS:
                    t_ref = active_trades_snapshot[0]
                    dca_levels = b['rm'].calculate_averaging_levels(t_ref['entry_price'], atr_current, t_ref['action'])
                    
                    # Determinamos el índice del siguiente nivel de promediado a buscar.
                    # Si hay 1 trade activo (la entrada inicial), buscamos el nivel 0 de la lista DCA.
                    next_idx = len(active_trades_snapshot) - 1
                    if next_idx < len(dca_levels):
                        target_price = dca_levels[next_idx]
                        is_hit = (t_ref['action'] == 'LONG' and current_price <= target_price) or \
                                 (t_ref['action'] == 'SHORT' and current_price >= target_price)
                        
                        if is_hit:
                            print(f"   🎯 {sym} SCALE-IN: Precio {current_price} alcanzó nivel {target_price}")
                            size = b['rm'].calculate_position_size(available_margin, current_price, t_ref['sl'] if t_ref['sl'] != 0 else None)
                            if size > 0:
                                margin_needed = (size * current_price) / config.LEVERAGE
                                api.occupy_margin(margin_needed)
                                b['tr'].register_trade(t_ref['action'], current_price, size, t_ref['sl'], t_ref['tp'], last_row, t_ref.get('use_sl', True))

                action_code, confidence, method_name, use_sl = b['brain'].get_consensus_prediction(
                    last_row, features_df=features, btc_features=global_btc_features if sym != 'BTCUSDT' else None
                )

                can_trade = (
                    action_code is not None
                    and confidence > config.MIN_CONFIDENCE
                    and len(b['tr'].active_trades) == 0
                    and b['cooldown_left'] == 0
                )

                if can_trade:
                    action_str = "LONG" if action_code == 1 else "SHORT"
                    sl, tp = b['rm'].calculate_dynamic_stops(
                        current_price, atr_current, action_str, 
                        atr_pct=last_row.get('ATR_pct')
                    )
                    size = b['rm'].calculate_position_size(available_margin, current_price, sl if use_sl else None)
                    if size > 0:
                        margin_needed = (size * current_price) / config.LEVERAGE
                        api.occupy_margin(margin_needed)
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

        # Sinergia: Reducimos el tiempo de espera para que los cambios se vean casi al instante
        time.sleep(5)

if __name__ == "__main__":
    main()