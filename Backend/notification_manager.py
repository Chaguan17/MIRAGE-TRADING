"""
notification_manager.py — Mirage Trading
Sistema de almacenamiento persistente de notificaciones entre procesos (main.py y api.py).
Guarda los eventos en storage/notifications.json.
"""
import os
import json
import time
from datetime import datetime
from threading import Lock
import logging
import config as cfg

logger = logging.getLogger(__name__)
NOTIFICATIONS_FILE = os.path.join(cfg.STORAGE_DIR, "notifications.json")
_LOCK = Lock()
_COOLDOWN = {}


def add_notification(level: str, title: str, message: str, symbol: str = None):
    """
    Agrega una notificación del sistema y la persiste en storage/notifications.json.
    level: 'SUCCESS' | 'WARNING' | 'ERROR' | 'INFO'
    """
    key = (title, symbol)
    now = time.time()
    if key in _COOLDOWN and now - _COOLDOWN[key] < 60:
        return None
    _COOLDOWN[key] = now
    item = {
        "id": int(time.time() * 1000),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "level": level.upper(),
        "title": title,
        "message": str(message),
        "symbol": symbol or "",
    }
    with _LOCK:
        items = get_notifications()
        items.insert(0, item)
        items = items[:50]  # Conservar las últimas 50 notificaciones

        try:
            os.makedirs(cfg.STORAGE_DIR, exist_ok=True)
            with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error escribiendo en notifications.json: {e}")

    logger.info(f"🔔 NOTIFICACIÓN [{level}]: {title} — {message}")
    return item


def get_notifications():
    """Lee las notificaciones persistidas en storage/notifications.json."""
    if not os.path.exists(NOTIFICATIONS_FILE):
        return []
    try:
        with open(NOTIFICATIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Error leyendo notifications.json: {e}")
        return []


def clear_notifications():
    """Limpia el historial de notificaciones."""
    with _LOCK:
        try:
            if os.path.exists(NOTIFICATIONS_FILE):
                os.remove(NOTIFICATIONS_FILE)
        except Exception as e:
            logger.error(f"Error borrando notifications.json: {e}")
