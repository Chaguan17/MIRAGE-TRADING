import pytest
import pandas as pd
import sqlite3
import os

from backtest_vs_real import BacktestVsRealComparator


def test_backtest_vs_real_comparator_instantiation(tmp_path):
    db_file = str(tmp_path / "test_mirage.db")
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE trades (
            timestamp TEXT, pair TEXT, action TEXT, entry_price REAL,
            close_price REAL, size REAL, result TEXT, pnl_usdt REAL,
            is_paper TEXT, FEES REAL, SLIPPAGE REAL, MFE REAL, MAE REAL
        )
    """)
    conn.execute("""
        INSERT INTO trades VALUES (
            '2026-08-01 00:00:00', 'ETHUSDT', 'LONG', 1800.0, 1820.0, 0.1,
            'WIN', 2.0, 'REAL', 0.1, 0.05, 1.2, 0.3
        )
    """)
    conn.commit()
    conn.close()

    comparator = BacktestVsRealComparator(db_path=db_file)
    df_real = comparator.get_real_trades("ETHUSDT")

    assert len(df_real) == 1
    assert df_real.iloc[0]['pair'] == 'ETHUSDT'
    assert float(df_real.iloc[0]['pnl_usdt']) == 2.0


def test_backtest_vs_real_metrics_and_matrix_construction(tmp_path):
    db_file = str(tmp_path / "test_mirage.db")
    comparator = BacktestVsRealComparator(db_path=db_file)

    bt_metrics = {
        'trades': 10,
        'win_rate': 60.0,
        'profit_factor': 2.1,
        'avg_win': 5.0,
        'avg_loss': -2.5,
        'expectancy': 2.0,
        'max_drawdown': 4.5,
        'total_fees': 1.2,
        'total_slippage': 0.8,
        'avg_mfe': 1.8,
        'avg_mae': 0.9,
        'total_pnl': 20.0
    }

    real_metrics = {
        'trades': 10,
        'win_rate': 50.0,
        'profit_factor': 1.8,
        'avg_win': 4.8,
        'avg_loss': -2.6,
        'expectancy': 1.5,
        'max_drawdown': 5.0,
        'total_fees': 1.4,
        'total_slippage': 1.0,
        'avg_mfe': 1.6,
        'avg_mae': 1.1,
        'total_pnl': 15.0
    }

    matrix = comparator._build_comparison_matrix(bt_metrics, real_metrics)
    assert len(matrix) == 11, "Debe generar las 11 métricas comparativas"

    score = comparator._calculate_fidelity_score(bt_metrics, real_metrics)
    assert 0.0 <= score <= 100.0, "La puntuación de fidelidad predictiva debe estar entre 0 y 100"
