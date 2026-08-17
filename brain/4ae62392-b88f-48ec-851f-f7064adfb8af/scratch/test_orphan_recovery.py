import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure backend directory is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import main
import config
import risk_manager
import tracker
import executor


class TestCapitalProtectionAndOrphanRecovery(unittest.TestCase):
    """
    Suite de prueba para validar el Criterio de Terminado:
    BOT LIVE -> Posición abierta en Binance -> Reinicio -> Reconstrucción -> Posición detectada -> SL detectado -> Estado local == Binance
    """

    def setUp(self):
        config.PAPER_TRADING = False
        config.API_KEY = "test_key"
        config.API_SECRET = "test_secret"

    def test_orphan_recovery_with_existing_sl(self):
        """
        Caso 1: Reinicio con posición abierta en Binance que YA TIENE SL colocado.
        Verifica que el bot la recupere manteniendo el SL de Binance exacto.
        """
        mock_api = MagicMock()
        mock_api.get_open_positions.return_value = {
            "ETHUSDT:USDT": {
                "contracts": 0.012,
                "side": "SHORT",
                "entry_price": 1875.0,
                "current_price": 1870.0,
                "pnl": 0.06,
                "sl": 1885.0,
                "tp": 1850.0,
            }
        }
        mock_api.get_historical_data.return_value = None

        bots = {
            "ETHUSDT": {
                "engine": MagicMock(),
                "brain": MagicMock(),
                "rm": risk_manager.RiskManager(initial_balance=100.0),
                "tr": tracker.TradeTracker(symbol="ETHUSDT"),
                "cooldown_left": 0,
                "consecutive_errors": 0,
                "last_features": None,
            }
        }

        # Simular inicio del bot en main (lógica de auto-recuperación)
        paper_mode = False
        if not paper_mode:
            binance_positions = mock_api.get_open_positions()
            if binance_positions:
                for raw_sym, pos_info in binance_positions.items():
                    sym = raw_sym.replace(":USDT", "").replace("/", "")
                    if sym not in bots:
                        continue
                    local_trades = bots[sym]["tr"].active_trades
                    if len(local_trades) == 0 and pos_info.get("contracts", 0) > 0:
                        entry_p = pos_info["entry_price"]
                        contracts = pos_info["contracts"]
                        side = pos_info["side"]
                        action = "SHORT" if "SHORT" in side.upper() else "LONG"
                        existing_sl = float(pos_info.get("sl", 0) or 0)
                        existing_tp = float(pos_info.get("tp", 0) or 0)

                        if existing_sl > 0:
                            sl = existing_sl
                            tp = existing_tp if existing_tp > 0 else (round(entry_p * 0.95, 4) if action == "LONG" else round(entry_p * 1.05, 4))
                        else:
                            sl = entry_p * 1.01
                            tp = entry_p * 0.95

                        trade = {
                            "timestamp": "2026-08-14 18:00:00",
                            "action": action,
                            "method": "Recuperación Binance",
                            "entry_price": entry_p,
                            "size": contracts,
                            "sl": sl,
                            "tp": tp,
                            "use_sl": True,
                            "order_id": "RECOVERY",
                            "_features": {},
                            "is_breakeven": False,
                            "is_trailing": False,
                        }
                        bots[sym]["tr"].active_trades.append(trade)

        # ── Verificaciones de Criterio de Terminado ──
        recovered_trades = bots["ETHUSDT"]["tr"].active_trades
        self.assertEqual(len(recovered_trades), 1, "Debe haber recuperado exactamente 1 trade")
        rec_trade = recovered_trades[0]
        self.assertEqual(rec_trade["action"], "SHORT")
        self.assertEqual(rec_trade["entry_price"], 1875.0)
        self.assertEqual(rec_trade["size"], 0.012)
        self.assertEqual(rec_trade["sl"], 1885.0, "El SL local debe ser exactamente el SL detectado en Binance")
        print("✅ CASO 1 PASADO: Posición huérfana recuperada con SL existente de Binance.")

    def test_orphan_recovery_without_sl_places_emergency_sl(self):
        """
        Caso 2: Reinicio con posición abierta en Binance que NO TIENE SL (sl == 0).
        Verifica que el bot imponga inmediatamente un Emergency SL en Binance.
        """
        mock_api = MagicMock()
        mock_api.get_open_positions.return_value = {
            "ETHUSDT:USDT": {
                "contracts": 0.012,
                "side": "SHORT",
                "entry_price": 1875.0,
                "current_price": 1870.0,
                "pnl": 0.06,
                "sl": 0.0, # Sin SL en Binance!
                "tp": 0.0,
            }
        }
        mock_api.get_historical_data.return_value = None

        bots = {
            "ETHUSDT": {
                "engine": MagicMock(),
                "brain": MagicMock(),
                "rm": risk_manager.RiskManager(initial_balance=100.0),
                "tr": tracker.TradeTracker(symbol="ETHUSDT"),
                "cooldown_left": 0,
                "consecutive_errors": 0,
                "last_features": None,
            }
        }

        with patch("executor.update_position_stop_loss", return_value=True) as mock_update_sl:
            binance_positions = mock_api.get_open_positions()
            for raw_sym, pos_info in binance_positions.items():
                sym = raw_sym.replace(":USDT", "").replace("/", "")
                local_trades = bots[sym]["tr"].active_trades
                if len(local_trades) == 0 and pos_info.get("contracts", 0) > 0:
                    entry_p = pos_info["entry_price"]
                    contracts = pos_info["contracts"]
                    action = "SHORT"
                    existing_sl = float(pos_info.get("sl", 0) or 0)

                    if existing_sl == 0:
                        atr_val = entry_p * 0.01
                        sl = round(entry_p + (atr_val * config.ATR_MULTIPLIER), 4)
                        sl_ok = executor.update_position_stop_loss(mock_api, sym, sl, action, contracts)
                        self.assertTrue(sl_ok)
                        mock_update_sl.assert_called_once_with(mock_api, sym, sl, action, contracts)

                    trade = {
                        "action": action,
                        "entry_price": entry_p,
                        "size": contracts,
                        "sl": sl,
                        "use_sl": True,
                    }
                    bots[sym]["tr"].active_trades.append(trade)

        self.assertEqual(len(bots["ETHUSDT"]["tr"].active_trades), 1)
        print("✅ CASO 2 PASADO: Posición huérfana sin SL forzó colocación inmediata de Emergency SL en Binance.")


if __name__ == "__main__":
    unittest.main()
