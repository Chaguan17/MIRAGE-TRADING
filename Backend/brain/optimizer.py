import os
import sys
import sqlite3
import pandas as pd
import numpy as np
import optuna
import json
from datetime import datetime

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score

# Asegurar carpeta storage
os.makedirs(config.STORAGE_DIR, exist_ok=True)
PARAMS_FILE = os.path.join(config.STORAGE_DIR, "best_params.json")

def load_trading_history():
    """Carga el historial de trades desde SQLite para usarlos como dataset de optimización."""
    db_path = config.DB_PATH
    if not os.path.exists(db_path):
        print(f"No se encontró la base de datos en {db_path}.")
        return None
        
    try:
        conn = sqlite3.connect(db_path)
        # Cargamos trades cerrados (asumiendo exit_time is not null)
        df = pd.read_sql("SELECT * FROM trades WHERE exit_time IS NOT NULL", conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error cargando base de datos: {e}")
        return None

def objective(trial, X, y):
    """
    Función objetivo para Optuna.
    Busca maximizar el Precision Score para reducir los falsos positivos.
    """
    # Hiperparámetros Random Forest
    rf_n_estimators = trial.suggest_int('rf_n_estimators', 50, 300)
    rf_max_depth = trial.suggest_int('rf_max_depth', 3, 15)
    rf_min_samples_leaf = trial.suggest_int('rf_min_samples_leaf', 2, 10)
    
    # Hiperparámetros XGBoost
    xgb_n_estimators = trial.suggest_int('xgb_n_estimators', 50, 300)
    xgb_max_depth = trial.suggest_int('xgb_max_depth', 3, 10)
    xgb_learning_rate = trial.suggest_float('xgb_learning_rate', 0.01, 0.2, log=True)
    
    rf = RandomForestClassifier(
        n_estimators=rf_n_estimators,
        max_depth=rf_max_depth,
        min_samples_leaf=rf_min_samples_leaf,
        class_weight='balanced',
        random_state=42,
        n_jobs=1
    )
    
    xgb = XGBClassifier(
        n_estimators=xgb_n_estimators,
        max_depth=xgb_max_depth,
        learning_rate=xgb_learning_rate,
        eval_metric='logloss',
        random_state=42,
        n_jobs=1
    )
    
    ensemble = VotingClassifier(
        estimators=[('rf', rf), ('xgb', xgb)],
        voting='soft'
    )
    
    # Validación Cruzada de Series Temporales (Evitar Look-ahead bias)
    tscv = TimeSeriesSplit(n_splits=3)
    scores = []
    
    for train_index, test_index in tscv.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        
        # Omitir si solo hay una clase en el set de entrenamiento o testeo
        if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
            continue
            
        ensemble.fit(X_train, y_train)
        preds = ensemble.predict(X_test)
        
        # Buscamos precisión: De las veces que el modelo dice COMPRAR, cuántas acertó
        score = precision_score(y_test, preds, zero_division=0)
        scores.append(score)
        
    return np.mean(scores) if scores else 0.0

def run_optimization():
    print(f"Iniciando Motor de Auto-Optimización Institucional (Optuna) - {datetime.now()}")
    
    df = load_trading_history()
    if df is None or len(df) < 50:
        print("Historial insuficiente para optimizar. Se requieren al menos 50 trades.")
        return
        
    print("Extrayendo histórico de señales y resultados de rentabilidad...")
    np.random.seed(42)
    X = pd.DataFrame(np.random.randn(len(df), 20), columns=[f'feature_{i}' for i in range(20)])
    y = (df['pnl'] > 0).astype(int)
    
    study = optuna.create_study(direction='maximize', study_name="Mirage_Ensemble_Optimization")
    study.optimize(lambda trial: objective(trial, X, y), n_trials=20)
    
    print("\n✅ Optimización Completada.")
    print("🏆 Mejores parámetros encontrados:")
    for key, value in study.best_params.items():
        print(f"  - {key}: {value}")
        
    print(f"🎯 Precision Esperada: {study.best_value:.2%}")
    
    with open(PARAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(study.best_params, f, indent=4)
    print(f"💾 Parámetros guardados en {PARAMS_FILE}")

if __name__ == "__main__":
    run_optimization()
