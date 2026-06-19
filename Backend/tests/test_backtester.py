import pytest
import pandas as pd
import os
import sys

# Asegurar que Python encuentre los módulos del Backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from backtester import SimpleBacktester

def test_backtester_initialization():
    """Verifica que el backtester se instancia correctamente con datos mínimos."""
    # Creamos un DataFrame de juguete (250 velas para pasar el warmup de EMA_200)
    data = {
        'timestamp': pd.date_range(start='2023-01-01', periods=250, freq='1min'),
        'open': [20000.0 + (i % 10) * 10 for i in range(250)],
        'high': [20100.0 + (i % 10) * 10 for i in range(250)],
        'low': [19900.0 + (i % 10) * 10 for i in range(250)],
        'close': [20000.0 + (i % 10) * 10 + 5.0 for i in range(250)],
        'volume': [100.0] * 250
    }
    df = pd.DataFrame(data)
    
    # Usamos una carpeta temporal para no ensuciar la producción
    tester = SimpleBacktester("BTCUSDT", df, test_dir="storage/test_runs")
    
    assert tester.symbol == "BTCUSDT"
    assert len(tester.df) >= 50
    assert tester.balance == config.PAPER_BALANCE

def test_backtester_run_no_errors():
    """Verifica que el bucle de backtesting puede correr sin crashear."""
    data = {
        'timestamp': pd.date_range(start='2023-01-01', periods=260, freq='1min'),
        'open': [20000.0 + (i % 10) * 10 for i in range(260)],
        'high': [20100.0 + (i % 10) * 10 for i in range(260)],
        'low': [19900.0 + (i % 10) * 10 for i in range(260)],
        'close': [20000.0 + (i % 10) * 10 + 5.0 for i in range(260)],
        'volume': [100.0] * 260
    }
    tester = SimpleBacktester("BTCUSDT", pd.DataFrame(data), test_dir="storage/test_runs")
    # Si esto no lanza una excepción, el motor es estable
    tester.run()