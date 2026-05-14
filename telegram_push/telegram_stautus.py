import requests
import json
import os
import config
from datetime import datetime


class TelegramNotifier:
    """
    Notificaciones de MIRAGE usando el mismo bot de Telegram del proyecto de noticias.
    Escribe también un archivo JSON de estado que el bot de noticias puede leer
    para responder a /mirage y /mirage_trade.
    """

    def __init__(self):
        self.token   = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)
        self.status_path = 'storage/mirage_status.json'

        if not self.enabled:
            print("📵 Telegram: desactivado (sin TOKEN o CHAT_ID en config)")
        else:
            print("📱 Telegram: activado — usando bot de noticias")

    # ──────────────────────────────────────────────────────────────────────────
    # ENVÍO DE MENSAJES
    # ──────────────────────────────────────────────────────────────────────────

    def _send(self, text):
        if not self.enabled:
            return
        try:
            url  = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                'chat_id':    self.chat_id,
                'text':       text,
                'parse_mode': 'HTML',
            }
            requests.post(url, data=data, timeout=5)
        except Exception as e:
            print(f"⚠️ Telegram error: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # ESCRITURA DE ESTADO (para /mirage y /mirage_trade)
    # ──────────────────────────────────────────────────────────────────────────

    def write_status(self, stats: dict, active_trade: dict | None = None):
        """
        Escribe el estado actual de MIRAGE en un JSON.
        El bot de noticias lo lee cuando alguien escribe /mirage o /mirage_trade.
        """
        try:
            os.makedirs('storage', exist_ok=True)
            payload = {
                **stats,
                'active_trade': active_trade,
                'updated_at':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            with open(self.status_path, 'w') as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error escribiendo status: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # NOTIFICACIONES
    # ──────────────────────────────────────────────────────────────────────────

    def send_startup(self, symbol, balance, ai_weight):
        self._send(
            f"🤖 <b>MIRAGE TRADING arrancado</b>\n"
            f"📊 Par: <b>{symbol}</b>\n"
            f"💰 Balance: <b>{balance:.2f} USDT</b>\n"
            f"🧠 Peso IA: <b>{ai_weight:.0%}</b>\n"
            f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )

    def send_trade_open(self, action, entry_price, tp, sl, size, method, confidence, use_sl):
        sl_str = f"SL: <b>{sl:.2f}</b>" if use_sl else "SL: <b>SIN SL</b>"
        emoji  = "🟢" if action == 'LONG' else "🔴"
        self._send(
            f"{emoji} <b>TRADE ABIERTO — {action}</b>\n"
            f"💵 Entrada: <b>{entry_price:.2f}</b>\n"
            f"🎯 TP: <b>{tp:.2f}</b>  |  {sl_str}\n"
            f"📦 Size: <b>{size}</b>\n"
            f"🧠 {method.upper()}  conf: <b>{confidence:.2%}</b>\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )

    def send_trade_close(self, action, entry_price, close_price, pnl, result, sl_was_hit):
        emoji  = "🏆" if result == 'WIN' else "💀"
        how    = "SL tocado" if sl_was_hit else "TP alcanzado"
        self._send(
            f"{emoji} <b>TRADE CERRADO — {result}</b>\n"
            f"📌 {action} | {entry_price:.2f} → <b>{close_price:.2f}</b>\n"
            f"💰 PnL: <b>{pnl:+.4f} USDT</b>\n"
            f"📋 {how}\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )

    def send_trailing_update(self, old_sl, new_sl):
        self._send(f"🔺 <b>Trailing Stop</b>: {old_sl:.2f} → <b>{new_sl:.2f}</b>")

    def send_sleep(self, wake_time):
        self._send(f"🌙 <b>MODO SUEÑO</b> — Vuelvo a las <b>{wake_time}</b>")

    def send_wakeup(self, ai_weight):
        self._send(f"☀️ <b>DESPERTANDO</b> | Peso IA: <b>{ai_weight:.0%}</b>")

    def send_daily_summary(self, wins, losses, wr, pnl, balance):
        emoji = "📈" if pnl >= 0 else "📉"
        self._send(
            f"{emoji} <b>RESUMEN DEL DÍA</b>\n"
            f"🏆 {wins}W / {losses}L  |  WR: <b>{wr:.1f}%</b>\n"
            f"💰 PnL: <b>{pnl:+.4f} USDT</b>\n"
            f"💼 Balance: <b>{balance:.2f} USDT</b>"
        )

    def send_error(self, error_msg):
        self._send(
            f"⚠️ <b>ERROR EN MIRAGE</b>\n"
            f"<code>{str(error_msg)[:200]}</code>\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )

    def send_reconnecting(self, attempt):
        self._send(f"🔄 <b>Reconectando...</b> intento {attempt}")