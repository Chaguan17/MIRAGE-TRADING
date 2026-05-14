import time
import os
import importlib
import config
from binance_api import MirageBinance
from data_engine import DataEngine
from brain import MirageBrain
import risk_manager
import tracker
import data_engine
from datetime import datetime, time as dtime


def check_for_updates(last_mod_times):
    files   = ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py', 'brain.py']
    updated = False
    for f in files:
        try:
            if os.path.exists(f):
                t = os.path.getmtime(f)
                if t > last_mod_times.get(f, 0):
                    updated = True
                    last_mod_times[f] = t
        except Exception:
            pass
    return updated, last_mod_times


def is_sleep_time():
    now   = datetime.now().time()
    start = dtime(config.SLEEP_START_HOUR, config.SLEEP_START_MINUTE)
    end   = dtime(config.SLEEP_END_HOUR,   config.SLEEP_END_MINUTE)
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
    print("🤖 MIRAGE TRADING — Sprint 6")

    api    = MirageBinance(config.API_KEY, config.API_SECRET, paper_trading=True)
    engine = DataEngine()
    brain  = MirageBrain()
    rm     = risk_manager.RiskManager()
    tr     = tracker.TradeTracker()

    def on_trade_closed(features_dict, result_label, sl_was_used, sl_was_hit):
        rm.register_result(result_label)
        brain.online_update(features_dict, result_label, sl_was_used, sl_was_hit)

    tr.set_on_close_callback(on_trade_closed)

    if not connect_with_retry(api):
        return

    account_balance = api.get_balance()

    print("📚 Descargando datos históricos...")
    raw_data = api.get_historical_data(config.SYMBOL, config.TIMEFRAME, limit=1000)
    if raw_data is None:
        print("❌ Error descargando datos.")
        return
    engine.prepare_features(raw_data)
    brain.nightly_retrain()

    sleep_start = dtime(config.SLEEP_START_HOUR, config.SLEEP_START_MINUTE)
    sleep_end   = dtime(config.SLEEP_END_HOUR,   config.SLEEP_END_MINUTE)
    print(
        f"\n🚀 {config.SYMBOL} | Sueño: {sleep_start.strftime('%H:%M')}→{sleep_end.strftime('%H:%M')}"
        f" | Peso IA: {brain._ai_weight():.0%} | 9 métodos activos\n"
    )

    files_to_watch     = ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py', 'brain.py']
    last_mod_times     = {f: os.path.getmtime(f) for f in files_to_watch if os.path.exists(f)}
    already_slept      = False
    cooldown_left      = 0
    consecutive_errors = 0
    btc_features       = None

    while True:

        # ── CICLO CIRCADIANO ─────────────────────────────────────────────────
        if is_sleep_time():
            if not already_slept:
                print(f"\n🌙 MODO SUEÑO ({datetime.now().strftime('%H:%M')})")
                brain.nightly_retrain()
                already_slept = True
                print(f"⏳ Durmiendo hasta las {sleep_end.strftime('%H:%M')}...")
            time.sleep(30)
            continue

        if already_slept:
            print(f"\n☀️  DESPERTANDO | Peso IA: {brain._ai_weight():.0%}")
            already_slept = False

        try:
            # A. Hot-Reload
            has_updates, last_mod_times = check_for_updates(last_mod_times)
            if has_updates:
                print("\n💡 Actualización detectada — recargando módulos...")
                memoria = tr.active_trades
                importlib.reload(risk_manager)
                importlib.reload(config)
                importlib.reload(tracker)
                importlib.reload(data_engine)
                rm     = risk_manager.RiskManager()
                tr     = tracker.TradeTracker()
                tr.active_trades = memoria
                tr.set_on_close_callback(on_trade_closed)
                engine = data_engine.DataEngine()
                print("✅ Módulos actualizados.\n")

            # B. Datos del activo principal
            live_data = api.get_historical_data(config.SYMBOL, config.TIMEFRAME, limit=200)
            if live_data is None:
                print("⚠️ Sin datos — reconectando...")
                if not connect_with_retry(api):
                    break
                continue

            consecutive_errors = 0
            current_price = live_data.iloc[-1]['close']
            features      = engine.prepare_features(live_data)
            last_row      = features.iloc[-1].to_dict()
            atr_current   = last_row['ATR']

            # C. Datos BTC para correlación
            if config.SYMBOL != 'BTCUSDT':
                try:
                    btc_raw = api.get_historical_data(
                        'BTCUSDT', config.TIMEFRAME,
                        limit=config.BTC_CORRELATION_LIMIT
                    )
                    if btc_raw is not None:
                        btc_features = engine.prepare_features(btc_raw)
                except Exception:
                    btc_features = None
            else:
                btc_features = features

            if not api.paper_trading:
                account_balance = api.get_balance()

            # D. Trailing stop
            for t in tr.active_trades:
                new_sl = rm.calculate_trailing_stop(t, current_price, atr_current)
                if new_sl is not None:
                    print(f"🔺 Trailing stop: {t['sl']} → {new_sl}")
                    t['sl']     = new_sl
                    t['use_sl'] = True

            # E. Vigilancia — cierre y cooldown
            trades_before = len(tr.active_trades)
            tr.update_market_price(current_price)
            trades_after  = len(tr.active_trades)

            if trades_after < trades_before:
                _, consecutive_losses = rm.get_streak_info()
                if consecutive_losses > 0:
                    cooldown_left = config.COOLDOWN_CANDLES
                    print(f"⏸️  Cooldown activado: {cooldown_left} velas.")

            # F. Dashboard
            total, wins, losses, wr, pnl = tr.get_dashboard_stats()
            session_name, session_w      = brain.get_session_info()
            c_wins, c_losses             = rm.get_streak_info()
            now_str = datetime.now().strftime('%H:%M:%S')

            print("\n" + "═" * 64)
            print(f"📊 MIRAGE  [{now_str}]  {config.SYMBOL}: {current_price:>10,.2f} USDT")
            print(f"🏆 {wins}W / {losses}L  WR: {wr:.1f}%  PnL: {pnl:+.4f}  Ops: {total}")
            print(f"🧠 Exp: {brain.trades_seen}  IA: {brain._ai_weight():.0%}  Balance: {account_balance:.2f} USDT")
            print(f"🌍 {session_name.upper()} (x{session_w})  Racha: +{c_wins}W/-{c_losses}L  Riesgo: {rm.get_current_risk():.1%}")
            if cooldown_left > 0:
                print(f"⏸️  Cooldown: {cooldown_left} vela(s)")
            print("═" * 64)
            active_trade_info = None
            if tr.active_trades:
                t = tr.active_trades[0]
                fpnl = (
                    (current_price - t['entry_price']) * t['size']
                    if t['action'] == 'LONG'
                    else (t['entry_price'] - current_price) * t['size']
                )
                active_trade_info = {
                    'action':       t['action'],
                    'entry_price':  t['entry_price'],
                    'tp':           t['tp'],
                    'sl':           t['sl'],
                    'use_sl':       t['use_sl'],
                    'current_price': current_price,
                    'floating_pnl': round(fpnl, 4),
                }

            tg.write_status({
                'wins':          wins,
                'losses':        losses,
                'pnl':           round(pnl, 4),
                'balance':       account_balance,
                'trades_seen':   brain.trades_seen,
                'ai_weight':     brain._ai_weight(),
                'symbol':        config.SYMBOL,
                'current_price': current_price,
                'session':       session_name,
            }, active_trade_info)

            # G. Predicción con 9 métodos
            action_code, confidence, method_name, use_sl = brain.get_consensus_prediction(
                last_row,
                features_df=features,
                btc_features=btc_features,
            )

            # H. Ejecución
            can_trade = (
                action_code is not None
                and confidence > config.MIN_CONFIDENCE
                and len(tr.active_trades) == 0
                and cooldown_left == 0
            )

            if can_trade:
                action_str = "LONG" if action_code == 1 else "SHORT"
                sl, tp     = rm.calculate_dynamic_stops(current_price, atr_current, action_str)
                size       = rm.calculate_position_size(
                    account_balance, current_price,
                    sl if use_sl else None,
                )
                if size > 0:
                    sl_display = f"SL={sl:.2f}" if use_sl else "SIN SL"
                    print(f"\n🧠 SEÑAL: {action_str}  |  {method_name.upper()}  |  conf: {confidence:.2%}")
                    print(f"🛡️  TP={tp:.2f}  |  {sl_display}  |  size={size}")
                    tr.register_trade(action_str, current_price, size, sl, tp, last_row, use_sl)

            else:
                if cooldown_left > 0:
                    cooldown_left -= 1

                if len(tr.active_trades) > 0:
                    t    = tr.active_trades[0]
                    fpnl = (
                        (current_price - t['entry_price']) * t['size']
                        if t['action'] == 'LONG'
                        else (t['entry_price'] - current_price) * t['size']
                    )
                    ep      = "📈" if fpnl >= 0 else "📉"
                    sl_line = (
                        f"SL={t['sl']:.2f}  (faltan {abs(current_price - t['sl']):.2f})"
                        if t['use_sl'] else "SIN SL"
                    )
                    print(
                        f"\n⏳ Vigilando {t['action']} @ {t['entry_price']:.2f}\n"
                        f"   Precio actual : {current_price:.2f}\n"
                        f"   TP (objetivo) : {t['tp']:.2f}  (faltan {abs(current_price - t['tp']):.2f})\n"
                        f"   Stop Loss     : {sl_line}\n"
                        f"   {ep} PnL flotante : {fpnl:+.4f} USDT"
                    )
                else:
                    side = "LONG" if action_code == 1 else ("SHORT" if action_code == 0 else "—")
                    print(f"⏳ Sin señal  |  {method_name} {side}  conf: {confidence:.2%}")

            time.sleep(60)

        except Exception as e:
            consecutive_errors += 1
            print(f"⚠️ Error: {e}")
            if consecutive_errors >= 5:
                print("❌ Demasiados errores consecutivos — reiniciando ciclo...")
                consecutive_errors = 0
            time.sleep(10)


if __name__ == "__main__":
    main()