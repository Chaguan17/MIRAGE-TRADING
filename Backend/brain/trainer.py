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
        """Reentrenamiento masivo con datos históricos."""
        try:
            conn = sqlite3.connect(db_path)
            # Filtramos trades que tengan un resultado definitivo
            query = f"SELECT * FROM trades WHERE pair = '{symbol}' AND result IN ('WIN', 'LOSS')"
            df = pd.read_sql(query, conn)
            conn.close()

            if len(df) < self.cfg.MIN_TRADES_FOR_AI:
                return False, f"Datos insuficientes: {len(df)} trades definitivos."

            for c in self.feat_cols:
                if c not in df.columns: df[c] = 0.0

            X = df[self.feat_cols]
            y_outcome = df['result'].apply(lambda x: 1 if x == 'WIN' else 0).tolist()
            
            Xs = self.fe.fit_scaler(X)
            w = self._compute_weights(y_outcome)

            # Reentrenar Outcome
            self.ml.model_outcome = RandomForestClassifier(
                n_estimators=self.cfg.AI_BASE_ESTIMATORS,
                max_depth=6,
                min_samples_leaf=5,
                class_weight=w or 'balanced_subsample',
                random_state=self.cfg.RANDOM_STATE,
                n_jobs=-1
            )
            self.ml.model_outcome.fit(Xs, y_outcome)

            # Reentrenar SL
            if 'sl_was_used' in df.columns and 'sl_was_hit' in df.columns:
                df_sl = df.dropna(subset=['sl_was_used', 'sl_was_hit'])
                if len(df_sl) >= self.cfg.MIN_TRADES_FOR_AI:
                    y_sl = ((df_sl['sl_was_used'] == 1) & (df_sl['sl_was_hit'] == 0)).astype(int).tolist()
                    Xs_sl = self.fe.scale(df_sl[self.feat_cols])
                    w_sl = self._compute_weights(y_sl)
                    self.ml.model_sl = RandomForestClassifier(
                        n_estimators=self.cfg.AI_BASE_ESTIMATORS,
                        max_depth=6,
                        min_samples_leaf=5,
                        class_weight=w_sl or 'balanced_subsample',
                        random_state=self.cfg.RANDOM_STATE,
                        n_jobs=-1
                    )
                    self.ml.model_sl.fit(Xs_sl, y_sl)

            self.ml.save_models()
            self._report_metrics(Xs, y_outcome)
            return True, len(df)
        except Exception as e:
            return False, str(e)

    def _compute_weights(self, y):
        classes = np.unique(y)
        if len(classes) < 2: return None
        weights = compute_class_weight('balanced', classes=classes, y=np.array(y))
        return dict(zip(classes, weights))

    def _report_metrics(self, Xs, y_true):
        y_pred = self.ml.model_outcome.predict(Xs)
        prec = precision_score(y_true, y_pred, zero_division=0)
        rec = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        logger.info(f"📈 IA METRICS ({self.ml.symbol}): Prec: {prec:.2%}, Rec: {rec:.2%}, F1: {f1:.2%}")