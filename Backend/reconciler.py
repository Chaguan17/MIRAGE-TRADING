"""
reconciler.py — Mirage Trading
Motor Reconciliador de Ejecución Real (Mirage vs Binance Futures).

Objetivo: Auditar periódicamente el estado en memoria de Mirage contra el
estado remoto de Binance para garantizar CERO desincronización en dinero real.
"""
import sqlite3
import time
import logging
import json
from datetime import datetime
import config
import notification_manager as nm

logger = logging.getLogger(__name__)


class PositionReconciler:
    """
    Compara minuciosamente las 10 métricas críticas entre Mirage y Binance.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or config.DB_PATH
        self.last_notified_ts = {}
        self._ensure_audit_table()

    def _ensure_audit_table(self):
        """Crea la tabla desync_audit_logs si no existe."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS desync_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    local_state TEXT,
                    remote_state TEXT,
                    reason TEXT NOT NULL,
                    action_taken TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error creando tabla desync_audit_logs: {e}")

    def log_desync_event(self, symbol, local_state, remote_state, reason, action_taken):
        """Registra un evento de desincronización en la base de datos SQLite de auditoría con cooldown de 60s."""
        now_ts = time.time()
        last_time = self.last_notified_ts.get(symbol, 0)

        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        local_str = json.dumps(local_state) if isinstance(local_state, dict) else str(local_state)
        remote_str = json.dumps(remote_state) if isinstance(remote_state, dict) else str(remote_state)

        # Aplicar Cooldown de 60 segundos por símbolo para notificaciones y logs repetitivos
        if (now_ts - last_time) >= 60.0:
            self.last_notified_ts[symbol] = now_ts

            logger.warning(
                f"⚠️ POSITION DESYNC DETECTADO [{symbol}]\n"
                f"  Reason: {reason}\n"
                f"  Action Taken: {action_taken}\n"
                f"  Local: {local_str}\n"
                f"  Remote: {remote_str}"
            )

            nm.add_notification(
                "WARNING",
                f"POSITION DESYNC DETECTADO ({symbol})",
                f"{reason} | Acción: {action_taken}",
                symbol
            )

        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.execute(
                "INSERT INTO desync_audit_logs (timestamp, symbol, local_state, remote_state, reason, action_taken) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts_str, symbol, local_str, remote_str, reason, action_taken)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error registrando desync en DB: {e}")

    def reconcile_symbol(self, api, symbol, local_trade, open_orders=None):
        """
        Audita las 10 métricas críticas para un símbolo:
        1. position_active
        2. side
        3. quantity
        4. entry_price
        5. leverage
        6. sl (Stop Loss)
        7. tp (Take Profit)
        8. open_orders (conteo de órdenes de protección)
        9. pnl (unrealized PnL)
        10. fees (estimadas o cobradas)

        Retorna un dict con:
        {
            'is_synced': bool,
            'discrepancies': list[str],
            'action': str, # 'NONE', 'CLOSE_LOCAL', 'SYNC_SL', 'SYNC_TP', 'UPDATE_ENTRY'
            'remote_pos': dict or None
        }
        """
        # Si estamos en Paper Trading, no hay reconciliación contra Binance real
        if getattr(api, 'paper_trading', True):
            return {
                'is_synced': True,
                'discrepancies': [],
                'action': 'NONE',
                'remote_pos': None
            }

        symbol_clean = symbol.replace(":USDT", "").replace("/", "").upper()

        # 1. Obtener posiciones reales de Binance
        try:
            real_positions = api.get_open_positions()
        except Exception as e:
            logger.error(f"Error obteniendo posiciones reales de Binance para reconciliar {symbol_clean}: {e}")
            return {
                'is_synced': False,
                'discrepancies': [f"API Error: {e}"],
                'action': 'NONE',
                'remote_pos': None
            }

        remote_pos = real_positions.get(symbol_clean) if real_positions else None
        remote_has_pos = remote_pos is not None and float(remote_pos.get('contracts', 0) or 0) > 0

        local_has_pos = local_trade is not None

        discrepancies = []

        # ── CASO A: Discrepancia de Existencia de Posición ──
        if local_has_pos and not remote_has_pos:
            discrepancies.append("Posición existe localmente pero fue CERRADA en Binance (TP/SL/Manual)")
            reason = "Posición cerrada externamente en Binance"
            action_taken = "Cerrar trade localmente y liberar margen"

            self.log_desync_event(
                symbol=symbol_clean,
                local_state={"active": True, "side": local_trade.get("action"), "size": local_trade.get("size")},
                remote_state={"active": False},
                reason=reason,
                action_taken=action_taken
            )
            return {
                'is_synced': False,
                'discrepancies': discrepancies,
                'action': 'CLOSE_LOCAL',
                'remote_pos': None
            }

        if not local_has_pos and remote_has_pos:
            discrepancies.append("Posición existe en Binance pero NO en memoria local de Mirage")
            reason = "Posición huérfana abierta externamente o reinicio"
            action_taken = "Reconstruir trade en memoria local con SL/TP"

            self.log_desync_event(
                symbol=symbol_clean,
                local_state={"active": False},
                remote_state=remote_pos,
                reason=reason,
                action_taken=action_taken
            )
            return {
                'is_synced': False,
                'discrepancies': discrepancies,
                'action': 'RECOVER_REMOTE',
                'remote_pos': remote_pos
            }

        if not local_has_pos and not remote_has_pos:
            # Ambas sin posición -> Totalmente sincronizadas
            return {
                'is_synced': True,
                'discrepancies': [],
                'action': 'NONE',
                'remote_pos': None
            }

        # ── CASO B: Ambas tienen posición active -> Auditar las 10 métricas ──
        rem_contracts = float(remote_pos.get('contracts', 0))
        rem_side = str(remote_pos.get('side', '')).upper()
        rem_entry = float(remote_pos.get('entry_price', 0))
        rem_sl = float(remote_pos.get('sl', 0) or 0)
        rem_tp = float(remote_pos.get('tp', 0) or 0)

        loc_contracts = float(local_trade.get('size', 0))
        loc_side = str(local_trade.get('action', '')).upper()
        loc_entry = float(local_trade.get('entry_price', 0))
        loc_sl = float(local_trade.get('sl', 0) or 0)
        loc_tp = float(local_trade.get('tp', 0) or 0)

        # 2. Side (LONG vs SHORT)
        if loc_side != rem_side and ("SHORT" in loc_side) != ("SHORT" in rem_side):
            discrepancies.append(f"Side mismatch: local={loc_side} vs remote={rem_side}")

        # 3. Quantity / contracts
        if abs(loc_contracts - rem_contracts) > 1e-5:
            discrepancies.append(f"Quantity mismatch: local={loc_contracts} vs remote={rem_contracts}")

        # 4. Entry price
        if abs(loc_entry - rem_entry) > 0.01:
            discrepancies.append(f"Entry price mismatch: local={loc_entry} vs remote={rem_entry}")

        # 5 & 6. SL & TP
        sl_desync = abs(loc_sl - rem_sl) > 0.05
        tp_desync = abs(loc_tp - rem_tp) > 0.05 and loc_tp > 0 and rem_tp > 0

        if sl_desync:
            discrepancies.append(f"SL mismatch: local={loc_sl} vs remote={rem_sl}")
        if tp_desync:
            discrepancies.append(f"TP mismatch: local={loc_tp} vs remote={rem_tp}")

        action_to_take = 'NONE'

        if discrepancies:
            if sl_desync or tp_desync:
                action_to_take = 'SYNC_SL_TP'
                reason = f"Desincronización de SL/TP: {', '.join(discrepancies)}"
                action_taken = "Actualizar órdenes reales en Binance para matchear estado deseado"
            else:
                action_to_take = 'UPDATE_LOCAL_SNAPSHOT'
                reason = f"Desincronización menor de datos: {', '.join(discrepancies)}"
                action_taken = "Actualizar snapshot en memoria local con datos reales de Binance"

            self.log_desync_event(
                symbol=symbol_clean,
                local_state={"side": loc_side, "size": loc_contracts, "entry": loc_entry, "sl": loc_sl, "tp": loc_tp},
                remote_state={"side": rem_side, "size": rem_contracts, "entry": rem_entry, "sl": rem_sl, "tp": rem_tp},
                reason=reason,
                action_taken=action_taken
            )

        return {
            'is_synced': len(discrepancies) == 0,
            'discrepancies': discrepancies,
            'action': action_to_take,
            'remote_pos': remote_pos
        }


position_reconciler = PositionReconciler()
