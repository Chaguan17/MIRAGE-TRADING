"""
Tests básicos para Mirage Trading — Tarea Inmediata 1.2

Cómo ejecutar:
    cd Backend
    pytest tests/test_core.py -v

Requisitos:
    pip install pytest

Cobertura:
    - config.py  → leverage clamp, constantes
    - brain.py   → ai_weight, build_X
    - risk_manager.py → position sizing, stops, rachas
"""

import sys
import os

# Permite importar desde Backend/ sin instalar como paquete
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import config
from brain import MirageBrain
from Backend.risk_manager import RiskManager


# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════

class TestConfig:
    """Tests para config.py"""

    def test_leverage_default_es_seguro(self):
        """El leverage por defecto no debe superar MAX_LEVERAGE_ALLOWED."""
        assert config.LEVERAGE <= config.MAX_LEVERAGE_ALLOWED

    def test_clamp_leverage_limita_exceso(self):
        """clamp_leverage debe bajar cualquier valor > MAX a MAX."""
        resultado = config.clamp_leverage(10)
        assert resultado == config.MAX_LEVERAGE_ALLOWED

    def test_clamp_leverage_respeta_valor_valido(self):
        """clamp_leverage no debe tocar un valor dentro del límite."""
        resultado = config.clamp_leverage(2)
        assert resultado == 2

    def test_clamp_leverage_en_el_limite(self):
        """clamp_leverage debe aceptar exactamente MAX_LEVERAGE_ALLOWED."""
        resultado = config.clamp_leverage(config.MAX_LEVERAGE_ALLOWED)
        assert resultado == config.MAX_LEVERAGE_ALLOWED

    def test_min_trades_for_ai_mayor_que_5(self):
        """MIN_TRADES_FOR_AI debe ser mayor que el valor original (5) para reducir overfitting."""
        assert config.MIN_TRADES_FOR_AI > 5

    def test_risk_per_trade_razonable(self):
        """
        RISK_PER_TRADE debe ser positivo y estar en formato decimal (< 1.0).

        config.py aplica normalize_risk_pct() al cargarlo, por lo que
        aunque settings.json tenga 2.0 (entero), config.RISK_PER_TRADE
        siempre llega aquí como 0.02 (decimal).
        """
        assert config.RISK_PER_TRADE > 0
        assert config.RISK_PER_TRADE < 1.0, (
            f"RISK_PER_TRADE={config.RISK_PER_TRADE} debe ser decimal (ej: 0.02 = 2%), "
            f"no entero. normalize_risk_pct debería haberlo corregido."
        )

    def test_risk_y_cap_misma_unidad(self):
        """
        RISK_PER_TRADE y MAX_RISK_CAP deben estar ambos en formato decimal.

        normalize_risk_pct() en config.py garantiza esto al importar.
        Si este test falla, hay un bug en normalize_risk_pct.
        """
        assert config.RISK_PER_TRADE < 1.0, f"RISK_PER_TRADE={config.RISK_PER_TRADE} no es decimal"
        assert config.MAX_RISK_CAP    < 1.0, f"MAX_RISK_CAP={config.MAX_RISK_CAP} no es decimal"
        assert config.RISK_PER_TRADE <= config.MAX_RISK_CAP, (
            f"RISK_PER_TRADE ({config.RISK_PER_TRADE:.2%}) no puede superar "
            f"MAX_RISK_CAP ({config.MAX_RISK_CAP:.2%})"
        )

    def test_pares_activos_no_vacio(self):
        """Debe haber al menos un par configurado."""
        assert len(config.PARES_ACTIVOS) >= 1

    def test_paper_balance_positivo(self):
        """El balance simulado debe ser positivo."""
        assert config.PAPER_BALANCE > 0

    def test_validate_sleep_config_valida(self):
        """La configuración de sueño por defecto debe pasar la validación."""
        result = config.validate_sleep_config(22, 0, 22, 5)
        assert result is True

    def test_validate_sleep_config_hora_invalida(self):
        """Horas fuera de rango (0-23) deben retornar False."""
        result = config.validate_sleep_config(25, 0, 22, 5)
        assert result is False


# ══════════════════════════════════════════════════════════════
# BRAIN
# ══════════════════════════════════════════════════════════════

class TestMirageBrain:
    """Tests para brain.py"""

    @pytest.fixture
    def brain(self):
        """Instancia limpia de MirageBrain para cada test."""
        return MirageBrain(symbol="BTCUSDT")

    def test_ai_weight_es_cero_sin_trades(self, brain):
        """Sin trades, el peso de la IA debe ser 0 (puro técnico)."""
        brain.trades_seen = 0
        assert brain._ai_weight() == 0.0

    def test_ai_weight_es_cero_bajo_minimo(self, brain):
        """Con trades < MIN_TRADES_FOR_AI, el peso debe seguir en 0."""
        brain.trades_seen = brain.MIN_TRADES_FOR_AI - 1
        assert brain._ai_weight() == 0.0

    def test_ai_weight_sube_con_trades(self, brain):
        """Con suficientes trades, el peso debe ser mayor que 0."""
        brain.trades_seen = brain.MIN_TRADES_FOR_AI + 20
        assert brain._ai_weight() > 0.0

    def test_ai_weight_no_supera_maximo(self, brain):
        """El peso de la IA nunca debe superar MAX_AI_WEIGHT."""
        brain.trades_seen = 10_000
        assert brain._ai_weight() <= brain.MAX_AI_WEIGHT

    def test_build_X_tiene_columnas_correctas(self, brain):
        """_build_X debe devolver un DataFrame con todas las feature columns."""
        features_dict = {col: 0.5 for col in brain._feat_cols}
        X = brain._build_X(features_dict)
        assert list(X.columns) == brain._feat_cols

    def test_build_X_rellena_columnas_faltantes(self, brain):
        """_build_X debe rellenar con 0.0 las features que no estén en el dict."""
        X = brain._build_X({})  # dict vacío
        assert X.shape == (1, len(brain._feat_cols))
        assert (X.values == 0.0).all()

    def test_min_trades_for_ai_respeta_config(self, brain):
        """MIN_TRADES_FOR_AI en brain debe coincidir con el de config."""
        assert brain.MIN_TRADES_FOR_AI == config.MIN_TRADES_FOR_AI

    def test_predict_use_sl_devuelve_true_sin_modelo(self, brain):
        """
        Con trades_seen < MIN_TRADES_FOR_AI, _predict_use_sl debe devolver True
        independientemente de si hay un modelo guardado en disco.

        Forzamos trades_seen = 0 para simular un cerebro recién creado
        sin experiencia suficiente para confiar en el modelo SL.
        """
        brain.trades_seen = 0   # forzar estado "sin experiencia"
        X = brain._build_X({col: 0.5 for col in brain._feat_cols})
        result = brain._predict_use_sl(X)
        assert result is True


# ══════════════════════════════════════════════════════════════
# RISK MANAGER
# ══════════════════════════════════════════════════════════════

class TestRiskManager:
    """Tests para risk_manager.py"""

    @pytest.fixture
    def rm(self):
        """Instancia limpia de RiskManager para cada test."""
        return RiskManager()

    def test_riesgo_inicial_es_config(self, rm):
        """El riesgo inicial debe ser el de config.RISK_PER_TRADE."""
        assert rm.get_current_risk() == config.RISK_PER_TRADE

    def test_racha_inicial_cero(self, rm):
        """Sin trades, wins y losses deben ser 0."""
        wins, losses = rm.get_streak_info()
        assert wins == 0
        assert losses == 0

    def test_register_win_incrementa_wins(self, rm):
        """Registrar WIN debe incrementar consecutive_wins."""
        rm.register_result('WIN')
        wins, losses = rm.get_streak_info()
        assert wins == 1
        assert losses == 0

    def test_register_loss_incrementa_losses(self, rm):
        """Registrar LOSS debe incrementar consecutive_losses."""
        rm.register_result('LOSS')
        wins, losses = rm.get_streak_info()
        assert wins == 0
        assert losses == 1

    def test_win_resetea_racha_perdedora(self, rm):
        """Un WIN después de varios LOSS debe resetear consecutive_losses a 0."""
        rm.register_result('LOSS')
        rm.register_result('LOSS')
        rm.register_result('WIN')
        _, losses = rm.get_streak_info()
        assert losses == 0

    def test_calculate_position_size_sin_sl(self, rm):
        """Sin stop-loss, el size debe ser positivo y basado en NO_SL_SIZE_PCT."""
        size = rm.calculate_position_size(
            account_balance=1000,
            entry_price=100,
            stop_loss_price=None
        )
        assert size > 0

    def test_calculate_position_size_con_sl(self, rm):
        """Con stop-loss, el size debe ser positivo."""
        size = rm.calculate_position_size(
            account_balance=1000,
            entry_price=100,
            stop_loss_price=98  # 2% abajo
        )
        assert size > 0

    def test_calculate_position_size_sl_igual_entry(self, rm):
        """Si sl == entry (riesgo 0), no debe haber posición (división por cero)."""
        size = rm.calculate_position_size(
            account_balance=1000,
            entry_price=100,
            stop_loss_price=100
        )
        assert size == 0

    def test_calculate_dynamic_stops_long(self, rm):
        """En LONG, el SL debe estar por debajo del precio y el TP por encima."""
        sl, tp = rm.calculate_dynamic_stops(100, atr_value=2, action='LONG')
        assert sl < 100
        assert tp > 100

    def test_calculate_dynamic_stops_short(self, rm):
        """En SHORT, el SL debe estar por encima del precio y el TP por debajo."""
        sl, tp = rm.calculate_dynamic_stops(100, atr_value=2, action='SHORT')
        assert sl > 100
        assert tp < 100

    def test_riesgo_no_supera_cap_tras_rachas(self, rm):
        """El riesgo dinámico nunca debe superar MAX_RISK_CAP."""
        for _ in range(20):
            rm.register_result('WIN')
        assert rm.get_current_risk() <= config.MAX_RISK_CAP


# ══════════════════════════════════════════════════════════════
# BINANCE API (sin conexión real — solo estructura)
# ══════════════════════════════════════════════════════════════

class TestMirageBinanceStructure:
    """Tests de estructura para binance_api.py (sin conexión real)."""

    def test_paper_balance_inicial(self):
        """En paper mode, el balance debe coincidir con config.PAPER_BALANCE."""
        from binance_api import MirageBinance
        api = MirageBinance(api_key="test", api_secret="test", paper_trading=True)
        assert api.get_balance() == config.PAPER_BALANCE

    def test_max_retries_definido(self):
        """MAX_RETRIES debe estar definido y ser mayor que 0."""
        from binance_api import MirageBinance
        assert MirageBinance.MAX_RETRIES > 0

    def test_ohlcv_columns_completas(self):
        """OHLCV_COLUMNS debe tener exactamente las 6 columnas esperadas."""
        from binance_api import MirageBinance
        assert MirageBinance.OHLCV_COLUMNS == ['timestamp', 'open', 'high', 'low', 'close', 'volume']