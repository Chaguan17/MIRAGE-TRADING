import pytest
import sqlite3
import pandas as pd
import numpy as np
import os
from sklearn.ensemble import VotingClassifier

import config as cfg
from brain.ml_engine import MLEngine
from brain.trainer import Trainer
from brain.feature_engine import FeatureEngine


def test_ml_engine_create_ensemble_structure():
    """Verifica que create_ensemble retorna un VotingClassifier con RF y XGBoost."""
    ensemble = MLEngine.create_ensemble(cfg)
    assert isinstance(ensemble, VotingClassifier)
    assert len(ensemble.estimators) == 2
    estimator_names = [name for name, _ in ensemble.estimators]
    assert 'rf' in estimator_names
    assert 'xgb' in estimator_names


def test_trainer_staging_pipeline_promotion(tmp_path):
    """
    Verifica que el flujo TRAIN -> VALIDATE -> COMPARE -> PROMOTE
    promueve exitosamente el candidato cuando OOS pasa los umbrales.
    """
    db_file = str(tmp_path / "test_trainer.db")
    model_file = str(tmp_path / "outcome_model.pkl")
    sl_file = str(tmp_path / "sl_model.pkl")

    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE trades (
            pair TEXT, result TEXT, sl_was_used INTEGER, sl_was_hit INTEGER,
            RSI REAL, ATR REAL, ATR_pct REAL, EMA_diff REAL, EMA_diff_norm REAL,
            MACD REAL, MACD_hist REAL, BB_width REAL, BB_position REAL,
            volume_ratio REAL, trend_signal REAL, above_ema200 REAL, momentum_signal REAL,
            VWAP_dist REAL, delta_cum5 REAL, delta_div REAL,
            price_slope REAL, range_pct REAL, near_struct_high REAL, near_struct_low REAL
        )
    """)

    # Insertar 30 trades sintéticos alternando WIN y LOSS con patrones claros
    feat_cols = [
        'RSI', 'ATR', 'ATR_pct', 'EMA_diff', 'EMA_diff_norm',
        'MACD', 'MACD_hist', 'BB_width', 'BB_position',
        'volume_ratio', 'trend_signal', 'above_ema200', 'momentum_signal',
        'VWAP_dist', 'delta_cum5', 'delta_div',
        'price_slope', 'range_pct', 'near_struct_high', 'near_struct_low'
    ]

    for i in range(40):
        res = 'WIN' if i % 2 == 0 else 'LOSS'
        vals = [
            'ETHUSDT', res, 1, 0 if res == 'WIN' else 1
        ] + [float(i * 1.5 if res == 'WIN' else -i * 1.5)] * len(feat_cols)

        placeholders = ', '.join(['?'] * len(vals))
        conn.execute(f"INSERT INTO trades VALUES ({placeholders})", vals)

    conn.commit()
    conn.close()

    scaler_file = str(tmp_path / "scaler.pkl")
    ml = MLEngine('ETHUSDT', model_file, sl_file, cfg)
    fe = FeatureEngine(scaler_file, feat_cols)
    trainer = Trainer(ml, fe, cfg, feat_cols)

    success, msg = trainer.perform_nightly_retrain('ETHUSDT', db_file)
    assert success is True
    assert "promovido" in msg.lower() or "promoted" in msg.lower() or "oos" in msg.lower()
