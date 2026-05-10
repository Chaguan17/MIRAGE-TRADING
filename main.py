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


# ──────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────────────────────────

def check_for_updates(last_mod_times):
    files_to_watch = ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py', 'brain.py']
    updated = False
    for file in files_to_watch:
        try:
            if os.path.exists(file):
                t = os.path.getmtime(file)
                if t > last_mod_times.get(file, 0):
                    updated = True
                    last_mod_times[file] = t
        except Exception:
            pass
    return updated, last_mod_times


def is_sleep_time():
    now   = datetime.now().time()
    start = dtime(config.SLEEP_START_HOUR, config.SLEEP_START_MINUTE)
    end   = dtime(config.SLEEP_END_HOUR,   config.SLEEP_END_MINUTE)
    if start <= end:
        return start <= now < end
    return now >= start or now < end   # ventana que cruza medianoche


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("🤖 BIENVENIDO A MIRAGE TRADING — Sistema Autodependiente")

    api    = MirageBinance(config.API_KEY, config.API_SECRET, paper_trading=True)
    engine = DataEngine()
    brain  = MirageBrain()
    rm     = risk_manager.RiskManager()
    tr     = tracker.TradeTracker()

    # ── Conectar cerebro ↔ tracker (feedback inmediato tras cada trade) ──────
    tr.set_on_close_callback(brain.online_update)

    if not api.check_connection():
        return

    account_balance = api.get_balance()

    # ── Estudio histórico inicial ────────────────────────────────────────────
    print("📚 Descargando datos históricos...")
    raw_data = api.get_historical_data(config.SYMBOL, config.TIMEFRAME, limit=1000)
    if raw_data is None:
        print("❌ Error descargando datos. Abortando.")
        return
    engine.prepare_features(raw_data)
    brain.nightly_retrain()   # intento inicial (puede que no haya suficientes datos aún)

    sleep_start = dtime(config.SLEEP_START_HOUR, config.SLEEP_START_MINUTE)
    sleep_end   = dtime(config.SLEEP_END_HOUR,   config.SLEEP_END_MINUTE)
    ai_w        = brain._ai_weight()
    print(
        f"\n🚀 {config.SYMBOL} bajo vigilancia."
        f" | Sueño: {sleep_start.strftime('%H:%M')}→{sleep_end.strftime('%H:%M')}"
        f" | Peso IA inicial: {ai_w:.0%}\n"
    )

    files_to_watch = ['risk_manager.py', 'data_engine.py', 'config.py', 'tracker.py', 'brain.py']
    last_mod_times = {f: os.path.getmtime(f) for f in files_to_watch if os.path.exists(f)}
    already_slept  = False

    while True:

        # ── 🌙 CICLO CIRCADIANO ──────────────────────────────────────────────
        if is_sleep_time():
            if not already_slept:
                print(f"\n🌙 MODO SUEÑO ({datetime.now().strftime('%H:%M')}) — Reentrenando cerebro...")
                brain.nightly_retrain()
                already_slept = True
                print(f"⏳ Durmiendo hasta las {sleep_end.strftime('%H:%M')}...")
            time.sleep(30)
            continue

        if already_slept:
            print(f"\n☀️  DESPERTANDO — Cerebro actualizado. Peso IA: {brain._ai_weight():.0%}")
            already_slept = False

        # ── BUCLE OPERATIVO ──────────────────────────────────────────────────
        try:
            # A. Hot-Reload
            has_updates, last_mod_times = check_for_updates(last_mod_times)
            if has_updates:
                print("\n💡 Actualización detectada — Re-sincronizando...")
                memoria_temporal = tr.active_trades
                importlib.reload(risk_manager)
                importlib.reload(config)
                importlib.reload(tracker)
                importlib.reload(data_engine)
                rm     = risk_manager.RiskManager()
                tr     = tracker.TradeTracker()
                tr.active_trades = memoria_temporal
                tr.set_on_close_callback(brain.online_update)   # reconectar callback
                engine = data_engine.DataEngine()
                print("✅ Sistemas actualizados.\n")

            # B. Datos de mercado
            live_data = api.get_historical_data(config.SYMBOL, config.TIMEFRAME, limit=100)
            if live_data is None:
                continue

            current_price       = live_data.iloc[-1]['close']
            features            = engine.prepare_features(live_data)
            last_features_row   = features.iloc[-1].to_dict()
            atr_current         = last_features_row['ATR']

            if not api.paper_trading:
                account_balance = api.get_balance()

            # C. Vigilancia de trades activos (cierre + feedback al cerebro)
            tr.update_market_price(current_price)

            # D. Dashboard
            total, wins, losses, wr, pnl = tr.get_dashboard_stats()
            now_str = datetime.now().strftime('%H:%M:%S')
            ai_pct  = brain._ai_weight()
            print("\n" + "═" * 58)
            print(f"📊 MIRAGE  [{now_str}]  BTC: {current_price:>10,.1f} USDT")
            print(f"🏆 {wins}W / {losses}L  WR: {wr:.1f}%  PnL: {pnl:+.4f} USDT  |  Ops: {total}")
            print(f"🧠 Peso IA: {ai_pct:.0%}  ({brain.trades_seen} experiencias)  |  Balance: {account_balance:.2f} USDT")
            print("═" * 58)

            # E. Predicción
            action_code, confidence, method_name = brain.get_consensus_prediction(last_features_row)

            # F. Ejecución
            if action_code is not None and confidence > 0.55 and len(tr.active_trades) == 0:
                action_str = "LONG" if action_code == 1 else "SHORT"
                print(f"\n🧠 SEÑAL: {action_str}  |  Método: {method_name.upper()}  |  Confianza: {confidence:.2%}")

                sl, tp = rm.calculate_dynamic_stops(current_price, atr_current, action_str)
                size   = rm.calculate_position_size(account_balance, current_price, sl)

                print(f"🛡️  SL: {sl:.2f}  |  TP: {tp:.2f}  |  Size: {size} BTC")
                tr.register_trade(action_str, current_price, size, sl, tp, last_features_row)

            else:
                if len(tr.active_trades) > 0:
                    t = tr.active_trades[0]
                    floating_pnl = (
                        (current_price - t['entry_price']) * t['size']
                        if t['action'] == 'LONG'
                        else (t['entry_price'] - current_price) * t['size']
                    )
                    pnl_emoji = "📈" if floating_pnl >= 0 else "📉"
                    print(
                        f"\n⏳ Vigilando {t['action']} @ entrada {t['entry_price']:.2f}\n"
                        f"   Precio actual : {current_price:.2f}\n"
                        f"   TP (objetivo) : {t['tp']:.2f}  (faltan {abs(current_price - t['tp']):.2f} USD)\n"
                        f"   SL (stop)     : {t['sl']:.2f}  (faltan {abs(current_price - t['sl']):.2f} USD)\n"
                        f"   {pnl_emoji} PnL flotante  : {floating_pnl:+.4f} USDT"
                    )
                else:
                    side = "LONG" if action_code == 1 else ("SHORT" if action_code == 0 else "—")
                    print(f"⏳ Sin señal suficiente  |  Mejor: {method_name} {side}  conf: {confidence:.2%}")

            time.sleep(60)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
