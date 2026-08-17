import sqlite3
import pandas as pd
import numpy as np
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
import logging
from brain.ml_engine import MLEngine

logger = logging.getLogger(__name__)


class Trainer:
    """
    Gestiona el reentrenamiento de IA con validación Out-of-Sample (OOS)
    y despliegue seguro por Staging (TRAIN -> VALIDATE -> COMPARE -> PROMOTE).
    """

    def __init__(self, ml_engine, feature_engine, config, feat_cols):
        self.ml = ml_engine
        self.fe = feature_engine
        self.cfg = config
        self.feat_cols = feat_cols

    def perform_nightly_retrain(self, symbol, db_path):
        """
        Reentrenamiento masivo con datos históricos usando el flujo seguro:
        TRAIN -> VALIDATE -> COMPARE -> PROMOTE
        """
        try:
            conn = sqlite3.connect(db_path, timeout=15.0)
            query = "SELECT * FROM trades WHERE pair = ? AND result IN ('WIN', 'LOSS')"
            df = pd.read_sql(query, conn, params=(symbol,))
            conn.close()

            if len(df) < self.cfg.MIN_TRADES_FOR_AI:
                return False, f"Datos insuficientes: {len(df)} trades definitivos (Mínimo {self.cfg.MIN_TRADES_FOR_AI})."

            for c in self.feat_cols:
                if c not in df.columns:
                    df[c] = 0.0

            X = df[self.feat_cols]
            y_outcome = df['result'].apply(lambda x: 1 if x == 'WIN' else 0).to_numpy()

            # Time-Series Split (80% Train, 20% Validation) para evitar data leakage
            split_idx = int(len(X) * 0.8)
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y_outcome[:split_idx], y_outcome[split_idx:]

            if len(np.unique(y_train)) < 2 or len(np.unique(y_val)) < 2:
                return False, "Insuficiente diversidad de clases en datos de entrenamiento/validación."

            # Ajustar escalador solo con datos de entrenamiento
            Xs_train = self.fe.fit_scaler(X_train)
            Xs_val = self.fe.scale(X_val)

            w_train = self._compute_weights(y_train)

            # ── STEP 1: TRAIN CANDIDATE (v_next) ──────────────────────────────────
            # Crear Ensamble Unificado (RandomForest + XGBoost)
            params = {}
            if w_train:
                params['rf'] = {'class_weight': w_train}

            candidate_outcome = MLEngine.create_ensemble(self.cfg, params=params)
            candidate_outcome.fit(Xs_train, y_train)

            # Entrenar modelo candidato para Stop Loss si hay datos suficientes
            candidate_sl = None
            if 'sl_was_used' in df.columns and 'sl_was_hit' in df.columns:
                df_sl = df.dropna(subset=['sl_was_used', 'sl_was_hit'])
                if len(df_sl) >= self.cfg.MIN_TRADES_FOR_AI:
                    df_sl_train = df_sl.iloc[:int(len(df_sl) * 0.8)]
                    y_sl_train = ((df_sl_train['sl_was_used'] == 1) & (df_sl_train['sl_was_hit'] == 0)).astype(int).to_numpy()
                    if len(np.unique(y_sl_train)) >= 2:
                        Xs_sl_train = self.fe.scale(df_sl_train[self.feat_cols])
                        w_sl = self._compute_weights(y_sl_train)
                        candidate_sl = MLEngine.create_ensemble(self.cfg, params={'rf': {'class_weight': w_sl}} if w_sl else None)
                        candidate_sl.fit(Xs_sl_train, y_sl_train)

            # ── STEP 2: VALIDATE & COMPARE (v_next vs v_current) ─────────────────
            cand_metrics = self._evaluate_model(candidate_outcome, Xs_val, y_val)

            current_metrics = {'f1': 0.0, 'precision': 0.0, 'accuracy': 0.0}
            if hasattr(self.ml.model_outcome, 'classes_') and len(self.ml.model_outcome.classes_) >= 2:
                current_metrics = self._evaluate_model(self.ml.model_outcome, Xs_val, y_val)

            logger.info(
                f"📊 [AI STAGING COMPARISON] -> "
                f"Candidate (v_next): F1={cand_metrics['f1']:.4f}, Prec={cand_metrics['precision']:.4f} | "
                f"Live (v_current): F1={current_metrics['f1']:.4f}, Prec={current_metrics['precision']:.4f}"
            )

            # ── STEP 3: PROMOTE OR DISCARD ───────────────────────────────────────
            # Criterio de Promoción: v_next debe superar o igualar a v_current y tener Prec >= 0.50
            should_promote = (
                cand_metrics['f1'] >= current_metrics['f1'] - 0.02 and
                cand_metrics['precision'] >= 0.50
            )

            if should_promote or not hasattr(self.ml.model_outcome, 'classes_'):
                self.ml.promote_candidate(candidate_outcome, candidate_sl)
                logger.info(f"🚀 [AI STAGING PROMOTED] Modelo candidato {symbol} promovido a producción.")
                return True, f"Modelo promovido exitosamente (OOS F1: {cand_metrics['f1']:.4f})"
            else:
                logger.warning(f"🛡️ [AI STAGING REJECTED] Modelo candidato {symbol} rechazado. Se conserva modelo vivo (v_current).")
                return False, f"Candidato no superó al modelo en vivo (Cand F1: {cand_metrics['f1']:.4f} vs Live F1: {current_metrics['f1']:.4f})"

        except Exception as e:
            logger.error(f"Error en reentrenamiento nocturno por staging: {e}")
            return False, str(e)

    def _compute_weights(self, y):
        classes = np.unique(y)
        if len(classes) < 2:
            return None
        weights = compute_class_weight('balanced', classes=classes, y=y)
        return dict(zip(classes, weights))

    def _evaluate_model(self, model, Xs_val, y_val):
        """Evalúa las métricas Out-of-Sample de un modelo."""
        try:
            y_pred = model.predict(Xs_val)
            prec = precision_score(y_val, y_pred, zero_division=0)
            rec = recall_score(y_val, y_pred, zero_division=0)
            f1 = f1_score(y_val, y_pred, zero_division=0)
            acc = accuracy_score(y_val, y_pred)
            return {'precision': prec, 'recall': rec, 'f1': f1, 'accuracy': acc}
        except Exception:
            return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0, 'accuracy': 0.0}