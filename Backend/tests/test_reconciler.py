import os
import sys
import unittest
import sqlite3
import tempfile
from unittest.mock import MagicMock

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reconciler import PositionReconciler


class TestPositionReconciler(unittest.TestCase):
    def setUp(self):
        self.tmp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.tmp_db.close()
        self.reconciler = PositionReconciler(db_path=self.tmp_db.name)

    def tearDown(self):
        if os.path.exists(self.tmp_db.name):
            os.remove(self.tmp_db.name)

    def test_paper_mode_returns_synced(self):
        mock_api = MagicMock()
        mock_api.paper_trading = True
        res = self.reconciler.reconcile_symbol(mock_api, "ETHUSDT", {"action": "SHORT", "size": 0.012})
        self.assertTrue(res['is_synced'])
        self.assertEqual(res['action'], 'NONE')

    def test_perfect_sync_returns_true(self):
        mock_api = MagicMock()
        mock_api.paper_trading = False
        mock_api.get_open_positions.return_value = {
            "ETHUSDT": {
                "contracts": 0.012,
                "side": "SHORT",
                "entry_price": 1875.0,
                "sl": 1885.0,
                "tp": 1850.0
            }
        }
        local_trade = {
            "action": "SHORT",
            "size": 0.012,
            "entry_price": 1875.0,
            "sl": 1885.0,
            "tp": 1850.0
        }
        res = self.reconciler.reconcile_symbol(mock_api, "ETHUSDT", local_trade)
        self.assertTrue(res['is_synced'])
        self.assertEqual(res['action'], 'NONE')

    def test_position_closed_externally_returns_close_local(self):
        mock_api = MagicMock()
        mock_api.paper_trading = False
        mock_api.get_open_positions.return_value = {} # No position in Binance!

        local_trade = {
            "action": "SHORT",
            "size": 0.012,
            "entry_price": 1875.0,
            "sl": 1885.0
        }
        res = self.reconciler.reconcile_symbol(mock_api, "ETHUSDT", local_trade)
        self.assertFalse(res['is_synced'])
        self.assertEqual(res['action'], 'CLOSE_LOCAL')
        self.assertIn("CERRADA en Binance", res['discrepancies'][0])

        # Verificar que el evento se registró en SQLite desync_audit_logs
        conn = sqlite3.connect(self.tmp_db.name)
        logs = conn.execute("SELECT symbol, reason, action_taken FROM desync_audit_logs").fetchall()
        conn.close()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0][0], "ETHUSDT")

    def test_sl_desync_returns_sync_sl_tp(self):
        mock_api = MagicMock()
        mock_api.paper_trading = False
        mock_api.get_open_positions.return_value = {
            "ETHUSDT": {
                "contracts": 0.012,
                "side": "SHORT",
                "entry_price": 1875.0,
                "sl": 1890.0, # Binance tiene 1890
                "tp": 1850.0
            }
        }
        local_trade = {
            "action": "SHORT",
            "size": 0.012,
            "entry_price": 1875.0,
            "sl": 1885.0, # Local tiene 1885
            "tp": 1850.0
        }
        res = self.reconciler.reconcile_symbol(mock_api, "ETHUSDT", local_trade)
        self.assertFalse(res['is_synced'])
        self.assertEqual(res['action'], 'SYNC_SL_TP')


if __name__ == "__main__":
    unittest.main()
