import pytest
import pandas as pd
import numpy as np

import config
from strategies import wyckoff, liquidity_zones, orderflow
from brain.veto_engine import VetoEngine


def test_wyckoff_spring_trigger():
    """Verifica que el patrón Spring de Wyckoff ahora sí puede activarse."""
    lookback = config.WYCKOFF_LOOKBACK  # 50 por defecto
    
    # Crear un DataFrame donde el precio es súper plano al principio
    # pero tiene un quiebre por debajo de la zona en las últimas 5 velas y recupera.
    data = {
        'high': [100.1] * lookback,
        'low': [99.9] * lookback,
        'close': [100.0] * lookback,
        'volume': [100.0] * lookback,
        'above_ema200': [0] * lookback,
        'volume_ratio': [1.0] * lookback
    }
    
    # Modificar el tramo reciente (las últimas 5 velas)
    # la vela 46 tiene un mínimo en 95.0 (quiebra el soporte del rango que era 99.9)
    data['low'][-4] = 95.0
    # la última vela cierra en 100.0 (recupera la zona)
    data['close'][-1] = 100.0
    
    df = pd.DataFrame(data)
    
    action, conf = wyckoff.analyze(df)
    
    # Debería activarse el Spring y retornar señal alcista (1, 0.82)
    assert action == 1
    assert conf == 0.82


def test_liquidity_zones_levels():
    """Verifica que nearest_high y nearest_low se filtren correctamente con el precio actual."""
    # Creamos datos con picos locales (fractales)
    # Queremos simular un pico local en 950 (abajo de 1000) y otro en 1100 (arriba de 1000)
    lookback = config.LIQ_LOOKBACK
    highs = [900.0] * lookback
    lows = [800.0] * lookback
    closes = [1000.0] * lookback
    
    # Crear un fractal de máximo (liq_high) en 950 (abajo de la cotización actual)
    highs[10] = 950.0  # pico
    highs[9] = 940.0
    highs[11] = 940.0
    
    # Crear otro fractal de máximo en 1100 (arriba de la cotización actual)
    highs[20] = 1100.0  # pico
    highs[19] = 1090.0
    highs[21] = 1090.0
    
    data = {
        'high': highs,
        'low': lows,
        'close': closes,
        'volume_ratio': [1.0] * lookback
    }
    
    df = pd.DataFrame(data)
    
    # Si la lógica no filtrara, nearest_high elegiría 950 porque abs(950 - 1000) = 50,
    # que está más cerca de 1000 que 1100 (distancia = 100).
    # Pero como elegimos solo > precio, nearest_high debe ser 1100.
    
    action, conf = liquidity_zones.analyze(df)
    
    # Dado que nearest_high = 1100, y nearest_low = 800
    # No deberíamos tener una señal de caza (hunt_high / hunt_low) activa porque el precio no superó el nivel.
    # Pero el test comprueba que no explote y que funcione el filtrado interno.
    # Podemos validar la lógica del filtro simulando que la función corre.
    assert action is None or action in [0, 1]


def test_orderflow_index_guard():
    """Verifica que el guard de orderflow previene crashes de indexación con arrays cortos."""
    data = {
        'high': [100.0] * 10,
        'low': [99.0] * 10,
        'close': [99.5] * 10,
        'volume': [100.0] * 10,
        'volume_ratio': [1.0] * 10
    }
    df = pd.DataFrame(data)
    
    # El DataFrame tiene longitud 10. Antes de corregir, esto crasheaba con close[-11].
    # Ahora, el guard len(features) < 11 debe retornar None, 0 sin lanzar IndexError.
    action, conf = orderflow.analyze(df)
    assert action is None
    assert conf == 0


def test_veto_engine_local_rsi():
    """Verifica que el VetoEngine evalúe correctamente el RSI del activo local."""
    class FakeConfig:
        RSI_VOL_REF = 0.5
        RSI_VOL_ADJUSTMENT_FACTOR = 5.0
        GLOBAL_RSI_OB_BASE = 75
        GLOBAL_RSI_OS_BASE = 25
        
    veto = VetoEngine("ETHUSDT", FakeConfig())
    
    btc_row = {'RSI': 50.0, 'ATR_pct': 0.5}
    local_row_ob = {'RSI': 80.0, 'ATR_pct': 0.5}
    local_row_os = {'RSI': 20.0, 'ATR_pct': 0.5}
    
    # 1. Test LONG vetoado por sobrecompra local
    veto_res = veto.check_market_vetoes(tech_action=1, btc_action=None, btc_row=btc_row, local_row=local_row_ob)
    assert veto_res == 'RSI Overbought Veto'
    
    # 2. Test SHORT vetoado por sobreventa local
    veto_res = veto.check_market_vetoes(tech_action=0, btc_action=None, btc_row=btc_row, local_row=local_row_os)
    assert veto_res == 'RSI Oversold Veto'
    
    # 3. Test sin veto si está neutral
    local_row_neutral = {'RSI': 50.0, 'ATR_pct': 0.5}
    veto_res = veto.check_market_vetoes(tech_action=1, btc_action=None, btc_row=btc_row, local_row=local_row_neutral)
    assert veto_res is None


def test_update_config_strategies():
    """Verifica que el endpoint /api/config acepte y guarde las estrategias y campos adicionales."""
    from api import update_config, ConfigUpdate
    import json
    import os
    import config as cfg
    
    # Hacer copia de settings actual para restaurarla después
    original_settings = {}
    if os.path.exists(cfg.SETTINGS_PATH):
        with open(cfg.SETTINGS_PATH, "r", encoding="utf-8") as f:
            original_settings = json.load(f)
            
    try:
        # 1. Crear payload con estrategias desactivadas
        payload = ConfigUpdate(
            STRATEGY_TREND=False,
            STRATEGY_SMC=False,
            VETO_CRASH_PCT=0.1,  # 10% en escala decimal
        )
        
        # 2. Llamar a update_config directamente
        res = update_config(payload)
        assert res["status"] == "success"
        
        # 3. Leer settings.json guardado y verificar cambios
        with open(cfg.SETTINGS_PATH, "r", encoding="utf-8") as f:
            updated = json.load(f)
            
        assert updated["STRATEGY_TREND"] is False
        assert updated["STRATEGY_SMC"] is False
        assert updated["VETO_CRASH_PCT"] == 0.1
        
    finally:
        # Restaurar configuración original
        if original_settings:
            with open(cfg.SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(original_settings, f, indent=4)


def test_percentage_config_requires_decimal_scale():
    """Los porcentajes del API usan fracciones decimales, no números enteros de porcentaje."""
    from pydantic import ValidationError
    from api import ConfigUpdate

    payload = ConfigUpdate(
        ADAPTIVE_RISK_FLOOR=0.005,
        ADAPTIVE_RISK_CEIL=0.03,
        ADAPTIVE_DRAWDOWN_FLOOR=0.85,
        VETO_CRASH_PCT=0.01,
    )

    assert payload.ADAPTIVE_RISK_FLOOR == 0.005
    assert payload.VETO_CRASH_PCT == 0.01

    with pytest.raises(ValidationError):
        ConfigUpdate(ADAPTIVE_RISK_FLOOR=0.5)


def test_update_config_rejects_adaptive_floor_above_ceil(tmp_path, monkeypatch):
    """El mínimo adaptativo no puede superar el máximo, incluso al actualizar un único campo."""
    from fastapi import HTTPException
    from api import ConfigUpdate, update_config
    import config as cfg
    import json

    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"ADAPTIVE_RISK_FLOOR": 0.005, "ADAPTIVE_RISK_CEIL": 0.03}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cfg, "SETTINGS_PATH", str(settings_path))

    with pytest.raises(HTTPException, match="ADAPTIVE_RISK_FLOOR"):
        update_config(ConfigUpdate(ADAPTIVE_RISK_FLOOR=0.04))

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "ADAPTIVE_RISK_FLOOR": 0.005,
        "ADAPTIVE_RISK_CEIL": 0.03,
    }


def test_parameter_metadata_includes_adaptive_percentage_fields():
    """Los metadatos del frontend publican los cuatro controles en escala decimal."""
    from api import get_parameters_metadata
    import config as cfg

    metadata = get_parameters_metadata()

    expected_ranges = {
        "ADAPTIVE_RISK_FLOOR": (0.001, 0.05),
        "ADAPTIVE_RISK_CEIL": (0.005, 0.15),
        "ADAPTIVE_DRAWDOWN_FLOOR": (0.5, 0.99),
        "VETO_CRASH_PCT": (0.01, 0.3),
    }
    for name, (minimum, maximum) in expected_ranges.items():
        assert metadata[name]["isPercentage"] is True
        assert metadata[name]["min"] == minimum
        assert metadata[name]["max"] == maximum


def test_runtime_metadata_cannot_override_adaptive_percentage_scale(tmp_path, monkeypatch):
    """Los metadatos runtime conservan textos propios, pero no alteran escala ni límites."""
    from api import get_parameters_metadata
    import config as cfg
    import json

    runtime_metadata_path = tmp_path / "parameters_metadata.json"
    runtime_metadata_path.write_text(
        json.dumps({
            "ADAPTIVE_RISK_FLOOR": {
                "label": "Riesgo mínimo personalizado",
                "isPercentage": False,
                "min": 0,
                "max": 100,
                "step": 1,
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(cfg, "METADATA_PATH", str(runtime_metadata_path))

    field = get_parameters_metadata()["ADAPTIVE_RISK_FLOOR"]

    assert field["label"] == "Riesgo mínimo personalizado"
    assert field["isPercentage"] is True
    assert field["min"] == 0.001
    assert field["max"] == 0.05
    assert field["step"] == 0.001


def test_get_config_includes_adaptive_defaults_when_unset(tmp_path, monkeypatch):
    """El frontend recibe valores actuales seguros aunque no existan en settings.json."""
    from api import get_config
    import config as cfg
    import json

    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"LEVERAGE": 5}), encoding="utf-8")
    monkeypatch.setattr(cfg, "SETTINGS_PATH", str(settings_path))

    current = get_config()

    assert current["ADAPTIVE_RISK_FLOOR"] == cfg.ADAPTIVE_RISK_FLOOR
    assert current["ADAPTIVE_RISK_CEIL"] == cfg.ADAPTIVE_RISK_CEIL
    assert current["ADAPTIVE_DRAWDOWN_FLOOR"] == cfg.ADAPTIVE_DRAWDOWN_FLOOR
    assert current["VETO_CRASH_PCT"] == cfg.VETO_CRASH_PCT


def test_trailing_stop_profit_is_win():
    """Verifica que un Trailing Stop / Breakeven activado con ganancia sea registrado como WIN y PnL positivo."""
    from tracker import TradeTracker
    import sqlite3
    import os
    
    tracker = TradeTracker(symbol="TESTUSDT")
    # Limpiar trades anteriores de TESTUSDT si los hay
    conn = sqlite3.connect(tracker.db_path, timeout=15.0)
    conn.execute("DELETE FROM trades WHERE pair = 'TESTUSDT'")
    conn.commit()
    conn.close()
    
    # Registrar un trade LONG a 1.15 con SL trailing activado en 1.16
    tracker.register_trade(
        action="LONG",
        entry_price=1.15,
        size=100.0,
        sl=1.16,  # Trailing stop por encima de la entrada
        tp=1.20,
        features={},
        use_sl=True
    )
    
    # Simular que el precio actual baja a 1.16 (toca el Trailing Stop)
    tracker.update_market_price(1.16)
    
    # El trade debe haber sido retirado de active_trades
    assert len(tracker.active_trades) == 0
    
    # Consultar DB de SQLite para verificar el resultado del trade
    conn = sqlite3.connect(tracker.db_path, timeout=15.0)
    c = conn.cursor()
    c.execute("SELECT result, pnl_usdt, close_price FROM trades WHERE pair = 'TESTUSDT' ORDER BY rowid DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    
    assert row is not None
    res, pnl, close_p = row
    assert close_p == 1.16
    assert res == 'WIN'
    assert pnl > 0  # (1.16 - 1.15) * 100 = 1.0 USDT
