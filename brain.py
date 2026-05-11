import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from methods import trend_follower, mean_reversion, breakout_logic


class MirageBrain:

    MIN_TRADES_FOR_AI = 5
    MAX_AI_WEIGHT     = 0.70
    BASE_ESTIMATORS   = 100   # árboles base
    ESTIMATORS_STEP   = 10    # árboles que se añaden en cada online_update

    def __init__(self):
        self.outcome_path = 'storage/model_outcome.pkl'
        self.sl_path      = 'storage/model_sl.pkl'
        self.scaler_path  = 'storage/scaler.pkl'

        self.model_outcome = self._load_or_create(self.outcome_path)
        self.model_sl      = self._load_or_create(self.sl_path)
        self.scaler        = self._load_scaler()

        self.trades_seen       = self._count_historical_trades()
        self._bootstrap_buffer = []

        from data_engine import DataEngine
        self._feat_cols = DataEngine().get_feature_columns()

    # ──────────────────────────────────────────────────────────────────────────
    # INIT
    # ──────────────────────────────────────────────────────────────────────────

    def _load_or_create(self, path):
        if os.path.exists(path):
            print(f"🧠 Cargando modelo desde disco: {path}")
            return joblib.load(path)
        print(f"🧠 Modelo nuevo — Modo Experto Técnico.")
        # Sin class_weight='balanced' + warm_start juntos
        # Los pesos los calculamos manualmente antes de cada fit
        return RandomForestClassifier(
            n_estimators=self.BASE_ESTIMATORS,
            random_state=42,
            warm_start=True,   # warm_start SÍ, pero sin balanced
        )

    def _load_scaler(self):
        if os.path.exists(self.scaler_path):
            return joblib.load(self.scaler_path)
        return StandardScaler()

    def _count_historical_trades(self):
        path = 'storage/trade_history.csv'
        try:
            if os.path.exists(path):
                return len(pd.read_csv(path))
        except Exception:
            pass
        return 0

    # ──────────────────────────────────────────────────────────────────────────
    # PESOS DE CLASE (reemplaza class_weight='balanced')
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_weights(self, y):
        """
        Calcula manualmente los pesos por clase para compensar desbalance
        (más LOSS que WIN o viceversa) sin usar 'balanced' + warm_start.
        """
        classes = np.unique(y)
        if len(classes) < 2:
            return None
        weights = compute_class_weight('balanced', classes=classes, y=np.array(y))
        return dict(zip(classes, weights))

    # ──────────────────────────────────────────────────────────────────────────
    # FEATURES
    # ──────────────────────────────────────────────────────────────────────────

    def _build_X(self, features_dict):
        row = {col: features_dict.get(col, 0.0) for col in self._feat_cols}
        return pd.DataFrame([row])

    def _scale(self, X):
        try:
            if hasattr(self.scaler, 'mean_'):
                return self.scaler.transform(X)
        except Exception:
            pass
        return X.values

    def _fit_scaler_and_scale(self, X):
        Xs = self.scaler.fit_transform(X)
        joblib.dump(self.scaler, self.scaler_path)
        return Xs

    # ──────────────────────────────────────────────────────────────────────────
    # PREDICCIÓN
    # ──────────────────────────────────────────────────────────────────────────

    def get_consensus_prediction(self, features_dict):
        X = self._build_X(features_dict)

        signals = {
            'trend':     trend_follower.analyze(pd.DataFrame([features_dict])),
            'reversion': mean_reversion.analyze(pd.DataFrame([features_dict])),
            'breakout':  breakout_logic.analyze(pd.DataFrame([features_dict])),
        }

        best_action, tech_conf, method_name = self._resolve_experts(signals)
        if best_action is None:
            return None, 0, 'None', True

        ai_weight   = self._ai_weight()
        tech_weight = 1.0 - ai_weight
        ai_conf     = self._predict_outcome(X, best_action)
        confidence  = (tech_conf * tech_weight) + (ai_conf * ai_weight)
        use_sl      = self._predict_use_sl(X)

        return best_action, confidence, method_name, use_sl

    def _resolve_experts(self, signals):
        best_action, max_conf, method = None, 0, 'None'
        for name, (action, conf) in signals.items():
            if action is not None and conf > max_conf:
                best_action, max_conf, method = action, conf, name
        return best_action, max_conf, method

    def _ai_weight(self):
        if self.trades_seen < self.MIN_TRADES_FOR_AI:
            return 0.0
        ratio = min(1.0, (self.trades_seen - self.MIN_TRADES_FOR_AI) / 45)
        return ratio * self.MAX_AI_WEIGHT

    def _predict_outcome(self, X, action_code):
        try:
            if not hasattr(self.model_outcome, 'classes_'):
                return 0.5
            Xs    = self._scale(X)
            proba = self.model_outcome.predict_proba(Xs)[0]
            return proba[1] if action_code == 1 else (1 - proba[1])
        except Exception:
            return 0.5

    def _predict_use_sl(self, X):
        try:
            if not hasattr(self.model_sl, 'classes_') or self.trades_seen < self.MIN_TRADES_FOR_AI:
                return True
            Xs = self._scale(X)
            return self.model_sl.predict_proba(Xs)[0][1] >= 0.5
        except Exception:
            return True

    # ──────────────────────────────────────────────────────────────────────────
    # APRENDIZAJE INMEDIATO
    # ──────────────────────────────────────────────────────────────────────────

    def online_update(self, features_dict, result_label, sl_was_used, sl_was_hit):
        try:
            X         = self._build_X(features_dict)
            y_outcome = [1 if result_label == 'WIN' else 0]
            y_sl      = [1 if (sl_was_used and sl_was_hit) else 0]

            self._bootstrap_buffer.append((X, y_outcome, y_sl))

            if len(self._bootstrap_buffer) < 2:
                self.trades_seen += 1
                return

            ys_outcome = [b[1][0] for b in self._bootstrap_buffer]
            ys_sl      = [b[2][0] for b in self._bootstrap_buffer]
            X_all      = pd.concat([b[0] for b in self._bootstrap_buffer])
            Xs         = self._fit_scaler_and_scale(X_all)

            # Outcome model — aumentar n_estimators para que warm_start añada árboles
            if len(set(ys_outcome)) >= 2:
                w = self._compute_weights(ys_outcome)
                current_n = self.model_outcome.n_estimators
                self.model_outcome.set_params(
                    n_estimators=current_n + self.ESTIMATORS_STEP,
                    class_weight=w,
                )
                self.model_outcome.fit(Xs, ys_outcome)

            # SL model
            if len(set(ys_sl)) >= 2:
                w_sl = self._compute_weights(ys_sl)
                current_n = self.model_sl.n_estimators
                self.model_sl.set_params(
                    n_estimators=current_n + self.ESTIMATORS_STEP,
                    class_weight=w_sl,
                )
                self.model_sl.fit(self._scale(X_all), ys_sl)

            self.trades_seen += 1
            self._save_all()
            print(f"🔄 Cerebro actualizado ({self.trades_seen} exp. | peso IA: {self._ai_weight():.0%})")

        except Exception as e:
            print(f"⚠️ online_update error: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # REENTRENAMIENTO NOCTURNO
    # ──────────────────────────────────────────────────────────────────────────

    def nightly_retrain(self, history_path='storage/trade_history.csv'):
        print(f"\n{'🌙'*8} MODO SUEÑO: Reentrenando con historial completo {'🌙'*8}")
        try:
            if not os.path.exists(history_path):
                print("CEREBRO: Sin historial todavía.")
                return

            df = pd.read_csv(history_path)
            if len(df) < self.MIN_TRADES_FOR_AI:
                print(f"CEREBRO: {len(df)}/{self.MIN_TRADES_FOR_AI} trades mínimos.")
                return

            for c in self._feat_cols:
                if c not in df.columns:
                    df[c] = 0.0

            X         = df[self._feat_cols]
            y_outcome = df['result'].apply(lambda x: 1 if x == 'WIN' else 0).tolist()

            Xs = self._fit_scaler_and_scale(X)
            w  = self._compute_weights(y_outcome)

            # Reentrenamiento completo: resetear n_estimators a base
            self.model_outcome = RandomForestClassifier(
                n_estimators=self.BASE_ESTIMATORS,
                random_state=42,
                warm_start=True,
                class_weight=w,
            )
            self.model_outcome.fit(Xs, y_outcome)

            # Modelo SL
            if 'sl_was_used' in df.columns and 'sl_was_hit' in df.columns:
                df_sl = df.dropna(subset=['sl_was_used', 'sl_was_hit'])
                if len(df_sl) >= self.MIN_TRADES_FOR_AI:
                    Xs_sl = self.scaler.transform(df_sl[self._feat_cols])
                    y_sl  = ((df_sl['sl_was_used'] == 1) & (df_sl['sl_was_hit'] == 1)).astype(int).tolist()
                    w_sl  = self._compute_weights(y_sl)
                    self.model_sl = RandomForestClassifier(
                        n_estimators=self.BASE_ESTIMATORS,
                        random_state=42,
                        warm_start=True,
                        class_weight=w_sl,
                    )
                    self.model_sl.fit(Xs_sl, y_sl)
                    print(f"🛡️  Modelo SL reentrenado con {len(df_sl)} trades.")

            self.trades_seen       = len(df)
            self._bootstrap_buffer = []
            self._save_all()
            self._print_feature_importance()
            print(f"✅ EVOLUCIÓN NOCTURNA: {len(df)} lecciones | peso IA: {self._ai_weight():.0%}")

        except Exception as e:
            print(f"⚠️ Error en fase de sueño: {e}")

    def _print_feature_importance(self):
        try:
            if not hasattr(self.model_outcome, 'feature_importances_'):
                return
            pairs = sorted(
                zip(self._feat_cols, self.model_outcome.feature_importances_),
                key=lambda x: x[1], reverse=True
            )
            print("\n📊 TOP FEATURES (lo que más influye en WIN/LOSS):")
            for feat, imp in pairs[:5]:
                bar = '█' * int(imp * 40)
                print(f"   {feat:<20} {bar} {imp:.3f}")
        except Exception:
            pass

    def _save_all(self):
        os.makedirs('storage', exist_ok=True)
        joblib.dump(self.model_outcome, self.outcome_path)
        joblib.dump(self.model_sl,      self.sl_path)