import time
import os
import shutil
import json
import importlib
import logging
import config
import brain
import executor
from binance_api import MirageBinance
from backend.tracker import TradeTracker
from backend.brain.ml_engine import ml_engine_instance
from market_stream import stream_manager
import data_engine as data_engine
import risk_manager as risk_manager
import tracker as tracker
from datetime import datetime, time as dtime

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

FILES_TO_WATCH = [
    "risk_manager.py",
    "data_engine.py",
    "config.py",
    "tracker.py",
    "brain/__init__.py",
    "storage/settings.json",
]


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
            logger.warning(f"No se pudo verificar {f}: {e}")
    return updated, last_mod_times


def is_sleep_time():
    now = datetime.now().time()
    start = dtime(config.SLEEP_START_HOUR, config.SLEEP_START_MINUTE)
    end = dtime(config.SLEEP_END_HOUR, config.SLEEP_END_MINUTE)
    if start <= end:
        return start <= now < end
    return now >= start or now < end


def connect_with_retry(api):
    for attempt in range(1, config.MAX_RECONNECT_ATTEMPTS + 1):
        if api.check_connection():
            return True
        print(f"🔄 Reconectando... intento {attempt}/{config.MAX_RECONNECT_ATTEMPTS}")
        time.sleep(config.RECONNECT_WAIT_SECONDS)
    print("❌ No se pudo reconectar. Bot detenido.")
    return False


def make_callback(symbol, bots, api):
    def on_trade_closed(
        features_dict, result_label, sl_was_used, sl_was_hit, pnl, margin_released
    ):
        api.release_margin(margin_released)
        api.update_paper_equity(pnl)
        bots[symbol]["rm"].register_result(result_label)
        bots[symbol]["brain"].online_update(
            features_dict, result_label, sl_was_used, sl_was_hit
        )

    return on_trade_closed


def _build_bot(sym, api, initial_balance):
    """Construye un dict-bot para un par dado."""
    raw_data = api.get_historical_data(sym, config.TIMEFRAME, limit=1000)
    engine = data_engine.DataEngine()
    b = {
        "engine": engine,
        "brain": brain.MirageBrain(symbol=sym),
        "rm": risk_manager.RiskManager(initial_balance=initial_balance),
        "tr": tracker.TradeTracker(symbol=sym),
        "cooldown_left": 0,
        "consecutive_errors": 0,
        "last_features": None,
    }
    if raw_data is not None:
        b["last_features"] = engine.prepare_features(raw_data)
        b["brain"].nightly_retrain()
    else:
        logger.warning(f"No se pudieron obtener datos iniciales para {sym}")
    return b


def main():
    print("🤖 MIRAGE TRADING — Flota Multi-Par con Riesgo Adaptativo")

    api = MirageBinance(config.API_KEY, config.API_SECRET, paper_trading=True)
    if not connect_with_retry(api):
        return

    initial_balance = config.PAPER_BALANCE
    os.makedirs("storage", exist_ok=True)
    pares_activos = config.PARES_ACTIVOS

    # Motor BTC de contexto (solo si BTC NO está en la flota activa)
    btc_context_engine = None
    if "BTCUSDT" not in pares_activos:
        btc_context_engine = data_engine.DataEngine()

    bots = {}
    for sym in pares_activos:
        print(f"⚙️  Construyendo motor para {sym}...")
        api.setup_symbol(sym, config.LEVERAGE)
        bots[sym] = _build_bot(sym, api, initial_balance)
        cb = make_callback(sym, bots, api)
        bots[sym]["tr"].set_on_close_callback(cb)

    sleep_end = dtime(config.SLEEP_END_HOUR, config.SLEEP_END_MINUTE)
    last_mod_times = {
        f: os.path.getmtime(f) for f in FILES_TO_WATCH if os.path.exists(f)
    }
    already_slept = False
    last_backup_dt = None
    last_known_balance = config.PAPER_BALANCE

    timeframes_to_track = list(set([config.TIMEFRAME, "1h", "4h", "1m"]))
    symbols_to_track = list(pares_activos)
    if "BTCUSDT" not in symbols_to_track:
        symbols_to_track.append("BTCUSDT")
        
    stream_manager.initialize(symbols_to_track, timeframes_to_track)
    
    print("Descargando históricos iniciales para el caché RAM...")
    for sym in stream_manager.symbols:
        for tf in timeframes_to_track:
            df = api.get_historical_data(sym.upper(), tf, limit=200)
            stream_manager.set_historical_cache(sym, tf, df)
    
    stream_manager.start()

    while True:
        # ── Ciclo circadiano ──────────────────────────────────────────────────
        if is_sleep_time():
            if not already_slept:
                print(f"\n🌙 MODO SUEÑO ({datetime.now().strftime('%H:%M')})")
                for sym in pares_activos:
                    bots[sym]["brain"].nightly_retrain()
                already_slept = True
                logger.info(
                    f"⏳ Flota en mantenimiento hasta las {sleep_end.strftime('%H:%M')}"
                )
            time.sleep(30)
            continue

        if already_slept:
            print(f"\n☀️  DESPERTANDO FLOTA")
            already_slept = False

        # ── Backup automático diario ──────────────────────────────────────────
        now_dt = datetime.now()
        if last_backup_dt is None or (now_dt - last_backup_dt).days >= 1:
            if os.path.exists(config.DB_PATH):
                bk_name = f"mirage_safe_{now_dt.strftime('%Y%m%d_%H%M')}.db"
                shutil.copy(config.DB_PATH, os.path.join(config.BACKUP_DIR, bk_name))
                logger.info(f"🛡️  Backup creado: {bk_name}")
            last_backup_dt = now_dt

        # ── Hot-reload ────────────────────────────────────────────────────────
        has_updates, last_mod_times = check_for_updates(last_mod_times)
        if has_updates:
            print("\n💡 Actualización detectada — recargando módulos...")
            importlib.reload(risk_manager)
            importlib.reload(config)
            importlib.reload(tracker)
            importlib.reload(data_engine)
            importlib.reload(brain)
            pares_activos = config.PARES_ACTIVOS

            current_balance = api.get_balance()
            for sym in pares_activos:
                if sym not in bots:
                    api.setup_symbol(sym, config.LEVERAGE)
                    bots[sym] = _build_bot(sym, api, current_balance)
                else:
                    memoria = bots[sym]["tr"].active_trades
                    bots[sym]["rm"] = risk_manager.RiskManager(
                        initial_balance=current_balance
                    )
                    bots[sym]["tr"] = tracker.TradeTracker(symbol=sym)
                    bots[sym]["tr"].active_trades = memoria
                    bots[sym]["engine"] = data_engine.DataEngine()
                    bots[sym]["brain"] = brain.MirageBrain(symbol=sym)
                cb = make_callback(sym, bots, api)
                bots[sym]["tr"].set_on_close_callback(cb)
            print("✅ Flota actualizada.\n")

        account_balance = api.get_balance()
        if account_balance > 0:
            last_known_balance = account_balance
        else:
            account_balance = last_known_balance
            
        available_margin = api.get_available_margin()

        # ── COMANDOS BIDIRECCIONALES (PANIC BUTTON) ───────────────────────────
        command_file = os.path.join(config.STORAGE_DIR, "commands.json")
        if os.path.exists(command_file):
            try:
                with open(command_file, "r", encoding="utf-8") as f:
                    cmd_data = json.load(f)
                if cmd_data.get("action") == "PANIC_SELL":
                    print("\n🚨🚨 PANIC BUTTON ACTIVADO 🚨🚨 Cerrando todas las operaciones...")
                    for sym in pares_activos:
                        b = bots[sym]
                        if len(b["tr"].active_trades) > 0:
                            # Conseguir el precio actual
                            live_1m = stream_manager.get_data(sym, "1m")
                            if live_1m is not None and not live_1m.empty:
                                close_p = live_1m.iloc[-1]['close']
                            else:
                                close_p = b["tr"].active_trades[0]['entry_price']
                            b["tr"].force_close(close_p, api)
                os.remove(command_file)
            except Exception as e:
                logger.error(f"Error procesando command_file: {e}")

        # ── SOLUCIÓN PUNTO 3: Obtención anticipada del contexto global de BTC ──
        global_btc_features = None
        if "BTCUSDT" in pares_activos or btc_context_engine:
            btc_raw = stream_manager.get_data("BTCUSDT", config.TIMEFRAME)
            btc_1h = stream_manager.get_data("BTCUSDT", "1h")
            btc_4h = stream_manager.get_data("BTCUSDT", "4h")
            
            engine = bots["BTCUSDT"]["engine"] if "BTCUSDT" in pares_activos else btc_context_engine
            if btc_raw is not None:
                global_btc_features = engine.prepare_features(btc_raw, btc_1h, btc_4h)

        print("\n" + "═" * 64)
        for sym in pares_activos:
            b = bots[sym]
            try:
                # Optimización: si procesamos BTCUSDT y ya lo descargamos arriba para el contexto, lo reutilizamos
                if sym == "BTCUSDT" and global_btc_features is not None:
                    features = global_btc_features
                else:
                    live_data = stream_manager.get_data(sym, config.TIMEFRAME)
                    live_1h = stream_manager.get_data(sym, "1h")
                    live_4h = stream_manager.get_data(sym, "4h")
                    
                    if live_data is None:
                        continue
                    features = b["engine"].prepare_features(live_data, live_1h, live_4h)

                b["consecutive_errors"] = 0
                current_price = features.iloc[-1]["close"]
                b["last_price"] = current_price
                last_row = features.iloc[-1].to_dict()
                atr_current = last_row.get("ATR", 0)

                # ── Gestión de trades activos ─────────────────────────────────
                with b["tr"]._trades_lock:
                    trades_to_process = list(b["tr"].active_trades)

                for t in trades_to_process:
                    t.setdefault("is_trailing", False)
                    t.setdefault("is_breakeven", False)

                    new_be = b["rm"].calculate_breakeven_stop(t, current_price)
                    if new_be is not None:
                        logger.info(f"🛡️  {sym} Breakeven activado → SL={new_be}")
                        t["sl"] = new_be
                        t["is_breakeven"] = True
                        t["use_sl"] = True
                        t["is_trailing"] = False

                    new_sl = b["rm"].calculate_trailing_stop(
                        t, current_price, atr_current
                    )
                    if new_sl is not None and new_sl != t["sl"]:
                        logger.info(f"{sym} trailing: {t['sl']} → {new_sl}")
                        t["sl"] = new_sl
                        t["use_sl"] = True
                        t["is_trailing"] = True

                trades_before = len(b["tr"].active_trades)
                b["tr"].update_market_price(current_price)
                if len(b["tr"].active_trades) < trades_before:
                    _, consecutive_losses = b["rm"].get_streak_info()
                    if consecutive_losses > 0:
                        b["cooldown_left"] = config.COOLDOWN_CANDLES

                total, wins, losses, wr, pnl = b["tr"].get_dashboard_stats()

                print(
                    f"📊 {sym:<8} | {current_price:>10,.2f} USDT | WR: {wr:>4.1f}% | PnL: {pnl:>7.4f} | Risk: {b['rm'].get_current_risk():.2%}"
                )
                if b["cooldown_left"] > 0:
                    print(f"   ⏸️  Cooldown: {b['cooldown_left']} vela(s)")

                with b["tr"]._trades_lock:
                    active_trades_snapshot = list(b["tr"].active_trades)

                # ── Señal de entrada (Consenso IA) ────────────────────────────
                action_code, confidence, method_name, use_sl = b[
                    "brain"
                ].get_consensus_prediction(
                    last_row,
                    features_df=features,
                    btc_features=global_btc_features if sym != "BTCUSDT" else None,
                )

                # ── Scale-In Inteligente (DCA) ─────────────────────────────────
                if 0 < len(active_trades_snapshot) < config.MAX_BULLETS:
                    t_ref = active_trades_snapshot[0]
                    dca_levels = b["rm"].calculate_averaging_levels(
                        t_ref["entry_price"], atr_current, t_ref["action"]
                    )
                    next_idx = len(active_trades_snapshot) - 1
                    if next_idx < len(dca_levels):
                        target_price = dca_levels[next_idx]
                        is_hit = (
                            t_ref["action"] == "LONG" and current_price <= target_price
                        ) or (
                            t_ref["action"] == "SHORT" and current_price >= target_price
                        )
                        
                        ai_agrees = (t_ref["action"] == "LONG" and action_code == 1) or \
                                    (t_ref["action"] == "SHORT" and action_code == 0)

                        if is_hit:
                            if ai_agrees:
                                print(f"   🎯 {sym} SCALE-IN @ {current_price} | Confirmado por IA")
                                # MEJORA DE RIESGO: Argumentos explícitos por clave para el dimensionamiento adaptativo exacto
                                size = b["rm"].calculate_position_size(
                                    account_balance=account_balance,
                                    entry_price=current_price,
                                    stop_loss_price=(
                                        t_ref["sl"] if t_ref.get("use_sl") else None
                                    ),
                                    current_balance=account_balance,
                                )
                                if size > 0:
                                    margin_needed = (size * current_price) / config.LEVERAGE
                                    if margin_needed <= available_margin:
                                        api.occupy_margin(margin_needed)
                                        b["tr"].register_trade(
                                            t_ref["action"],
                                            current_price,
                                            size,
                                            t_ref["sl"],
                                            t_ref["tp"],
                                            last_row,
                                            t_ref.get("use_sl", True),
                                        )
                            else:
                                print(f"   ⏳ {sym} Nivel DCA alcanzado, esperando confirmación técnica...")

                # Señal ya calculada arriba para uso conjunto con el DCA

                can_trade = (
                    action_code is not None
                    and confidence > config.MIN_CONFIDENCE
                    and len(b["tr"].active_trades) == 0
                    and b["cooldown_left"] == 0
                )

                if can_trade:
                    action_str = "LONG" if action_code == 1 else "SHORT"
                    sl, tp = b["rm"].calculate_dynamic_stops(
                        current_price,
                        atr_current,
                        action_str,
                        atr_pct=last_row.get("ATR_pct"),
                    )
                    size = b["rm"].calculate_position_size(
                        account_balance=account_balance,
                        entry_price=current_price,
                        stop_loss_price=sl if use_sl else None,
                        current_balance=account_balance,
                    )

                    if size > 0:
                        margin_needed = (size * current_price) / config.LEVERAGE
                        if margin_needed <= available_margin:
                            api.occupy_margin(margin_needed)
                            print(
                                f"   🧠 SEÑAL: {action_str} | {method_name.upper()} | conf: {confidence:.2%} | size: {size}"
                            )

                            # ── Ejecución real en Binance ─────────────────────────────
                            order = executor.execute_trade(
                                client=api,
                                symbol=sym,
                                action=action_str,
                                size=size,
                                sl=sl if use_sl else None,
                                tp=tp,
                            )
                            if order:
                                b["tr"].register_trade(
                                    action_str,
                                    current_price,
                                    size,
                                    sl,
                                    tp,
                                    last_row,
                                    use_sl,
                                )
                            else:
                                api.release_margin(margin_needed)
                        else:
                            logger.warning(
                                f"⚠️ Margen insuficiente para {sym}. Requerido: {margin_needed:.2f}"
                            )
                else:
                    if b["cooldown_left"] > 0:
                        b["cooldown_left"] -= 1

            except Exception as e:
                b["consecutive_errors"] += 1
                logger.error(f"Error en {sym}: {e}", exc_info=True)
                print(f"⚠️  Error en {sym}: {e}")

        print("═" * 64)

        # ── Actualizar dashboard ──────────────────────────────────────────────
        try:
            web_pnl_global = 0
            web_trades_global = 0
            web_wins_global = 0
            
            for sym in pares_activos:
                total, wins, losses, wr, pnl = bots[sym]["tr"].get_dashboard_stats()
                web_pnl_global += pnl
                web_trades_global += total
                web_wins_global += wins
                
            wr_global = (
                (web_wins_global / web_trades_global * 100)
                if web_trades_global > 0
                else 0
            )
            rm_status = {
                sym: bots[sym]["rm"].get_status_dict() for sym in pares_activos
            }

            # ── AÑADIR: balance real de Binance ──────────────────────────────
            real_balance = api.get_real_balance()
            
            tracker_stats = {
                sym: {
                    "total": bots[sym]["tr"].total_trades,
                    "wins": bots[sym]["tr"].wins,
                    "losses": bots[sym]["tr"].losses,
                    "win_rate": round(bots[sym]["tr"].win_rate, 1),
                    "pnl": round(bots[sym]["tr"].total_pnl, 2),
                } for sym in pares_activos
            }

            # ── Reconstrucción segura de operaciones activas ─────────────────
            web_operaciones_activas_safe = []
            for sym in pares_activos:
                b = bots[sym]
                with b["tr"]._trades_lock:
                    active_trades_snapshot = list(b["tr"].active_trades)
                
                curr_price = b.get("last_price", 0)
                
                if not active_trades_snapshot:
                    continue

                total_size = sum(t.get("size", 0) for t in active_trades_snapshot)
                if total_size > 0:
                    avg_entry = sum(t.get("size", 0) * t.get("entry_price", 0) for t in active_trades_snapshot) / total_size
                else:
                    avg_entry = active_trades_snapshot[0].get("entry_price", 0)

                total_pnl = 0
                for t in active_trades_snapshot:
                    if curr_price > 0:
                        fpnl = (curr_price - t["entry_price"]) * t.get("size", 0) if t["action"] == "LONG" else (t["entry_price"] - curr_price) * t.get("size", 0)
                        total_pnl += fpnl

                last_t = active_trades_snapshot[-1]
                
                web_operaciones_activas_safe.append({
                    "pair": sym,
                    "current_price": round(curr_price, 6),
                    "type": last_t["action"],
                    "entry": round(avg_entry, 6),
                    "tp": round(last_t.get("tp"), 6) if last_t.get("tp") else 0,
                    "sl": round(last_t.get("sl"), 6) if last_t.get("sl") else 0,
                    "current_pnl": round(total_pnl, 2),
                    "is_trailing": any(t.get("is_trailing", False) for t in active_trades_snapshot),
                    "is_breakeven": any(t.get("is_breakeven", False) for t in active_trades_snapshot),
                    "size": total_size,
                    "position_value": total_size * avg_entry,
                    "bullets": len(active_trades_snapshot)
                })

            estado = {
                "pnl_total": round(float(web_pnl_global), 2),
                "win_rate": round(float(wr_global), 1),
                "total_operaciones": int(web_trades_global),
                "operaciones_activas": web_operaciones_activas_safe,
                "balance_actual": round(account_balance, 2),
                "balance_inicial": round(initial_balance, 2),
                "balance_real": round(real_balance, 2),
                "risk_managers": rm_status,
                "tracker_stats": tracker_stats,
            }
            import sqlite3
            import json
            conn = sqlite3.connect(config.DB_PATH)
            c = conn.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS system_state (id INTEGER PRIMARY KEY, state_json TEXT)')
            c.execute('INSERT OR REPLACE INTO system_state (id, state_json) VALUES (1, ?)', (json.dumps(estado),))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error actualizando dashboard: {e}")

        time.sleep(5)


if __name__ == "__main__":
    main()
