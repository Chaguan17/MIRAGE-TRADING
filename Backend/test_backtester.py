import pytest
import pandas as pd
import os
import sys

# Asegurar que Python encuentre los módulos del Backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtester import SimpleBacktester

def test_backtester_initialization():
    """Verifica que el backtester se instancia correctamente con datos mínimos."""
    # Creamos un DataFrame de juguete (110 velas para pasar el warmup)
    data = {
        'timestamp': pd.date_range(start='2023-01-01', periods=110, freq='1min'),
        'open': [20000] * 110,
        'high': [20100] * 110,
        'low': [19900] * 110,
        'close': [20000] * 110,
        'volume': [100] * 110
    }
    df = pd.DataFrame(data)
    
    # Usamos una carpeta temporal para no ensuciar la producción
    tester = SimpleBacktester("BTCUSDT", df, test_dir="storage/test_runs")
    
    assert tester.symbol == "BTCUSDT"
    assert len(tester.df) >= 110
    assert tester.balance == 1000 # El balance por defecto en config.py

def test_backtester_run_no_errors():
    """Verifica que el bucle de backtesting puede correr sin crashear."""
    data = {
        'timestamp': pd.date_range(start='2023-01-01', periods=120, freq='1min'),
        'open': [20000] * 120, 'high': [20100] * 120, 'low': [19900] * 120, 'close': [20000] * 120, 'volume': [100] * 120
    }
    tester = SimpleBacktester("BTCUSDT", pd.DataFrame(data), test_dir="storage/test_runs")
    # Si esto no lanza una excepción, el motor es estable
    tester.run()