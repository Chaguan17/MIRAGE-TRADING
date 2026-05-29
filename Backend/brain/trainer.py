import sqlite3
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import precision_score, recall_score, f1_score
import logging

logger = logging.getLogger(__name__)

class Trainer:
    def __init__(self, ml_engine, feature_engine, config, feat_cols):
        self.ml = ml_engine
        self.fe = feature_engine
        self.cfg = config
        self.feat_cols = feat_cols

    def perform_nightly_retrain(self, symbol, db_path):
        """Reentrenamiento masivo con datos históricos usando validación Out-of-Sample."""
        try:
            conn = sqlite3.connect(db_path)
            query = f"SELECT * FROM trades WHERE pair = '{symbol}' AND result IN ('WIN', 'LOSS')"
            df = pd.read_sql(query, conn)
            conn.close()

            if len(df) < self.cfg.MIN_TRADES_FOR_AI:
                return False, f"Datos insuficientes: {len(df)} trades definitivos."

            for c in self.feat_cols:
                if c not in df.columns: 
                    df[c] = 0.0

            X = df[self.feat_cols]
            y_outcome = df['result'].apply(lambda x: 1 if x == 'WIN' else 0).to_numpy()
            
            # FIX: Time-Series Split (80% Train, 20% Validation) para evitar data leakage
            split_idx = int(len(X) * 0.8)
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y_outcome[:split_idx], y_outcome[split_idx:]
            
            # Ajustar escalador solo con datos de entrenamiento
            Xs_train = self.fe.fit_scaler(X_train)
            Xs_val = self.fe.scale(X_val)
            
            w_train = self._compute_weights(y_train)

            # Reentrenar Clasificador de Éxito
            self.ml.model_outcome = RandomForestClassifier(
                n_estimators=self.cfg.AI_BASE_ESTIMATORS,
                max_depth=6,
                min_samples_leaf=5,
                class_weight=w_train or 'balanced_subsample',
                random_state=self.cfg.RANDOM_STATE,
                n_jobs=1
            )
            self.ml.model_outcome.fit(Xs_train, y_train)

            # Reentrenar Clasificador de Stop Loss
            if 'sl_was_used' in df.columns and 'sl_was_hit' in df.columns:
                df_sl = df.dropna(subset=['sl_was_used', 'sl_was_hit'])
                if len(df_sl) >= self.cfg.MIN_TRADES_FOR_AI:
                    df_sl_train = df_sl.iloc[:int(len(df_sl) * 0.8)]
                    y_sl_train = ((df_sl_train['sl_was_used'] == 1) & (df_sl_train['sl_was_hit'] == 0)).astype(int).tolist()
                    Xs_sl_train = self.fe.scale(df_sl_train[self.feat_cols])
                    w_sl = self._compute_weights(y_sl_train)
                    
                    self.ml.model_sl = RandomForestClassifier(
                        n_estimators=self.cfg.AI_BASE_ESTIMATORS,
                        max_depth=6,
                        min_samples_leaf=5,
                        class_weight=w_sl or 'balanced_subsample',
                        random_state=self.cfg.RANDOM_STATE,
                        n_jobs=1
                    )
                    self.ml.model_sl.fit(Xs_sl_train, y_sl_train)

            self.ml.save_models()
            
            # Reportar métricas reales basadas en el conjunto de validación (Out-of-Sample)
            self._report_metrics(Xs_val, y_val)
            return True, len(df)
            
        except Exception as e:
            logger.error(f"Error en reentrenamiento nocturno: {e}")
            return False, str(e)

    def _compute_weights(self, y):
        classes = np.unique(y)
        if len(classes) < 2: 
            return None
        weights = compute_class_weight('balanced', classes=classes, y=y)
        return dict(zip(classes, weights))

    def _report_metrics(self, Xs_val, y_val):
        """Genera logs con métricas de validación reales."""
        if not hasattr(self.ml.model_outcome, 'classes_') or len(self.ml.model_outcome.classes_) < 2:
            logger.warning("Modelo no preparado para reportar métricas reales.")
            return
            
        y_pred = self.ml.model_outcome.predict(Xs_val)
        prec = precision_score(y_val, y_pred, zero_division=0)
        rec = recall_score(y_val, y_pred, zero_division=0)
        f1 = f1_score(y_val, y_pred, zero_division=0)

        logger.info(
            f"📈 [AI MODEL OOS METRICS] -> OOS Precision: {prec:.4f} | "
            f"OOS Recall: {rec:.4f} | OOS F1-Score: {f1:.4f}"
        )