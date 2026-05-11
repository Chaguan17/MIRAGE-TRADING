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


def main():
    print("🤖 MIRAGE TRADING — Sistema Autodependiente v2")

    api    = MirageBinance(config.API_KEY, config.API_SECRET, paper_trading=True)
    engine = DataEngine()
    brain  = MirageBrain()
    rm     = risk_manager.RiskManager()
    tr     = tracker.TradeTracker()

    tr.set_on_close_callback(brain.online_update)

    if not api.check_connection():
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
        f"\n🚀 {config.SYMBOL} en vigilancia"
        f" | Sueño: {sleep_start.strftime('%H:%M')}→{sleep_end.strftime('%H:%M')}"
        f" | Peso IA: {brain._ai_weight():.0%}\n"
    )

    files_to_watch = ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py', 'brain.py']
    last_mod_times = {f: os.path.getmtime(f) for f in files_to_watch if os.path.exists(f)}
    already_slept  = False

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

        # ── BUCLE OPERATIVO ──────────────────────────────────────────────────
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
                rm = risk_manager.RiskManager()
                tr = tracker.TradeTracker()
                tr.active_trades = memoria
                tr.set_on_close_callback(brain.online_update)
                engine = data_engine.DataEngine()
                print("✅ Módulos actualizados.\n")

            # B. Mercado
            live_data = api.get_historical_data(config.SYMBOL, config.TIMEFRAME, limit=200)
            if live_data is None:
                continue

            current_price = live_data.iloc[-1]['close']
            features      = engine.prepare_features(live_data)
            last_row      = features.iloc[-1].to_dict()
            atr_current   = last_row['ATR']

            if not api.paper_trading:
                account_balance = api.get_balance()

            # C. Vigilancia → cierra trades y retroalimenta al cerebro
            tr.update_market_price(current_price)

            # D. Dashboard
            total, wins, losses, wr, pnl = tr.get_dashboard_stats()
            now_str = datetime.now().strftime('%H:%M:%S')
            print("\n" + "═" * 60)
            print(f"📊 MIRAGE  [{now_str}]  BTC: {current_price:>10,.1f} USDT")
            print(f"🏆 {wins}W / {losses}L  WR: {wr:.1f}%  PnL: {pnl:+.4f}  Ops: {total}")
            print(f"🧠 Exp: {brain.trades_seen}  Peso IA: {brain._ai_weight():.0%}  Balance: {account_balance:.2f} USDT")
            print("═" * 60)

            # E. Predicción — incluye decisión de SL
            action_code, confidence, method_name, use_sl = brain.get_consensus_prediction(last_row)

            # F. Ejecución
            if action_code is not None and confidence > config.MIN_CONFIDENCE and len(tr.active_trades) == 0:
                action_str = "LONG" if action_code == 1 else "SHORT"
                sl, tp     = rm.calculate_dynamic_stops(current_price, atr_current, action_str)
                size       = rm.calculate_position_size(
                    account_balance, current_price,
                    sl if use_sl else None,
                )

                sl_display = f"SL={sl:.2f}" if use_sl else "SIN SL (cierre por señal contraria)"
                print(f"\n🧠 SEÑAL: {action_str}  |  {method_name.upper()}  |  conf: {confidence:.2%}")
                print(f"🛡️  TP={tp:.2f}  |  {sl_display}  |  size={size} BTC")

                tr.register_trade(action_str, current_price, size, sl, tp, last_row, use_sl)

            else:
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
                        f"   TP (objetivo) : {t['tp']:.2f}  (faltan {abs(current_price - t['tp']):.2f} USD)\n"
                        f"   Stop Loss     : {sl_line}\n"
                        f"   {ep} PnL flotante : {fpnl:+.4f} USDT"
                    )
                else:
                    side = "LONG" if action_code == 1 else ("SHORT" if action_code == 0 else "—")
                    print(f"⏳ Sin señal  |  {method_name} {side}  conf: {confidence:.2%}")

            time.sleep(60)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()