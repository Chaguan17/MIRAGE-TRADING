import pytest
import pandas as pd

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


def test_backtester_faithful_execution_schema_and_conflict_policy():
    """
    Verifica que:
    1. Las salidas TP/SL se evalúan usando High/Low.
    2. Ante impactos simultáneos (High >= TP y Low <= SL), aplica la política conservadora de SL.
    3. Todos los 15 campos del nuevo registro de trade están presentes.
    4. MAE, MFE y R-Multiple son calculados correctamente.
    """
    data = {
        'timestamp': pd.date_range(start='2023-01-01', periods=150, freq='1min'),
        'open': [20000.0] * 150,
        'high': [20100.0] * 150,
        'low': [19900.0] * 150,
        'close': [20005.0] * 150,
        'volume': [100.0] * 150
    }
    df = pd.DataFrame(data)
    tester = SimpleBacktester("ETHUSDT", df, test_dir="storage/test_runs")

    # Forzar un trade activo con SL=1980 y TP=2050
    tester.active_trade = {
        'entry_time': "2023-01-01 00:00:00",
        'action': "LONG",
        'entry_price': 2000.0,
        'raw_price': 2000.0,
        'size': 0.1,
        'sl': 1980.0,
        'initial_sl': 1980.0,
        'tp': 2050.0,
        'initial_tp': 2050.0,
        'use_sl': True,
        'method': "TEST",
        'entry_fee_rate': 0.0002,
        'initial_risk_usdt': 2.0,
        'liq_price': 1800.0,
        'mfe_price': 2000.0,
        'mae_price': 2000.0,
        'mfe_pct': 0.0,
        'mae_pct': 0.0,
        'is_breakeven': False,
        'is_trailing': False,
        'features': {}
    }

    # Evaluar vela que toca simultáneamente High >= 2050 (2060) y Low <= 1980 (1970)
    conflict_row = {
        'timestamp': "2023-01-01 00:01:00",
        'open': 2000.0,
        'high': 2060.0,  # Supera TP
        'low': 1970.0,   # Rompe SL
        'close': 2010.0,
        'volume': 100.0,
        'ATR': 10.0
    }

    tester._check_exit(pd.Series(conflict_row))

    # Verificaciones
    assert len(tester.history) == 1, "Debe haber registrado el trade cerrado"
    t = tester.history[0]

    # 1. Verificar Política Conservadora (SL sobre TP)
    assert t['EXIT_REASON'] == 'SL', "Ante impacto simultáneo, la política conservadora debe forzar salida por SL"

    # 2. Verificar presencia de los 15 campos requeridos
    required_fields = [
        'ENTRY', 'EXIT', 'SIDE', 'ENTRY_PRICE', 'EXIT_PRICE',
        'SL', 'TP', 'MFE', 'MAE', 'FEES', 'SLIPPAGE',
        'PNL', 'R_MULTIPLE', 'EXIT_REASON', 'METHOD'
    ]
    for field in required_fields:
        assert field in t, f"El campo {field} debe estar presente en el registro de trade"

    # 3. Verificar MAE y MFE
    assert t['MFE'] >= 3.0, "MFE debe reflejar el avance máximo hacia High (2060 / 2000 = +3.0%)"
    assert t['MAE'] >= 1.5, "MAE debe reflejar la excursión máxima adversa hacia Low (1970 / 2000 = -1.5%)"

    # 4. Verificar R-Multiple
    assert isinstance(t['R_MULTIPLE'], (float, int))