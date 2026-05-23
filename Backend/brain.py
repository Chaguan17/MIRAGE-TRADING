import os
import joblib
import pandas as pd
import sqlite3
import numpy as np
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import config as cfg
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import precision_score, recall_score, f1_score
from methods import (
    trend_follower, mean_reversion, breakout_logic,
    smc_structure, vwap_method, liquidity_zones,
    orderflow, wyckoff, btc_correlation,
)

logger = logging.getLogger(__name__)


class MirageBrain:

    def __init__(self, symbol="BTCUSDT", storage_dir=None):
        self.symbol = symbol

        self.cfg = cfg
        self.storage_dir = storage_dir or self.cfg.STORAGE_DIR
        self.MIN_TRADES_FOR_AI = self.cfg.MIN_TRADES_FOR_AI
        self.MAX_AI_WEIGHT     = self.cfg.AI_MAX_WEIGHT
        self.BASE_ESTIMATORS   = self.cfg.AI_BASE_ESTIMATORS
        self.ESTIMATORS_STEP   = self.cfg.AI_ESTIMATORS_STEP
        self.LAYER_WEIGHTS     = self.cfg.LAYER_WEIGHTS
        self.RSI_OB_BASE       = self.cfg.GLOBAL_RSI_OB_BASE
        self.RSI_OS_BASE       = self.cfg.GLOBAL_RSI_OS_BASE
        self.RSI_VOL_ADJ       = self.cfg.RSI_VOL_ADJUSTMENT_FACTOR
        self.RSI_VOL_REF       = self.cfg.RSI_VOL_REF

        self.outcome_path = os.path.join(self.storage_dir, f'model_outcome_{self.symbol}.pkl')
        self.sl_path      = os.path.join(self.storage_dir, f'model_sl_{self.symbol}.pkl')
        self.scaler_path  = os.path.join(self.storage_dir, f'scaler_{self.symbol}.pkl')

        self.model_outcome     = self._load_or_create(self.outcome_path)
        self.model_sl          = self._load_or_create(self.sl_path)
        self.scaler            = self._load_scaler()
        self.trades_seen       = self._count_historical_trades()

        self._bootstrap_buffer = []
        self._max_buffer       = cfg.MAX_BOOTSTRAP_BUFFER

        from data_engine import DataEngine
        self._feat_cols = DataEngine().get_feature_columns()

    def _load_or_create(self, path):
        if os.path.exists(path):
            print(f"🧠 Cargando modelo: {path}")
            return joblib.load(path)
        print(f"🧠 Modelo nuevo para {self.symbol} — Modo Experto Técnico.")
        return RandomForestClassifier(
            n_estimators=self.BASE_ESTIMATORS,
            random_state=self.cfg.RANDOM_STATE,
            warm_start=True,
        )

    def _load_scaler(self):
        """Carga el scaler guardado o crea uno nuevo (StandardScaler)."""
        if os.path.exists(self.scaler_path):
            return joblib.load(self.scaler_path)
        return StandardScaler()

    def _count_historical_trades(self):
        """
        Cuenta los trades históricos del CSV para este símbolo.

        Returns:
            int: Número de trades del par. 0 si el CSV no existe o está vacío.
        """
        try:
            if os.path.exists(self.cfg.DB_PATH):
                conn = sqlite3.connect(self.cfg.DB_PATH)
                query = "SELECT COUNT(*) FROM trades WHERE pair = ?"
                res = conn.execute(query, (self.symbol,)).fetchone()
                conn.close()
                return res[0] if res else 0
        except Exception as e:
            logger.error(f"Error counting historical trades for {self.symbol}: {e}")
        return 0

    def _get_session_weight(self):
        """
        Devuelve el multiplicador de confianza según la sesión UTC actual.

        Returns:
            tuple[float, str]: (peso, nombre_sesión)
                - asia    (00-08 UTC): 0.80
                - europa  (08-16 UTC): 1.00
                - america (16-24 UTC): 1.10
        """
        from datetime import datetime, timezone
        hour_utc = datetime.now(timezone.utc).hour
        if 0 <= hour_utc < 8:
            session = 'asia'
        elif 8 <= hour_utc < 16:
            session = 'europa'
        else:
            session = 'america'
        return self.cfg.SESSION_WEIGHTS.get(session, 1.0), session

    def get_session_info(self):
        """
        Expone la sesión actual para el dashboard/logs.

        Returns:
            tuple[str, float]: (nombre_sesión, peso)
        """
        weight, session = self._get_session_weight()
        return session, weight

    def _build_X(self, features_dict):
        """
        Construye el DataFrame de features listo para el modelo.

        Args:
            features_dict (dict): Features del último candle (output de DataEngine).

        Returns:
            pd.DataFrame: 1 fila con las columnas de self._feat_cols.
                          Columnas faltantes se rellenan con 0.0.
        """
        row = {col: features_dict.get(col, 0.0) for col in self._feat_cols}
        return pd.DataFrame([row])

    def _scale(self, X):
        """
        Transforma X con el scaler ajustado.

        Returns X sin escalar si el scaler no fue entrenado todavía,
        para evitar errores en los primeros trades.

        Args:
            X (pd.DataFrame): Features sin escalar.

        Returns:
            np.ndarray: Features escaladas (o sin escalar si el scaler no está listo).
        """
        try:
            if hasattr(self.scaler, 'mean_'):
                return self.scaler.transform(X)
        except ValueError as e:
            logger.warning(f"Scaler transform failed for {self.symbol}: {e}, returning unscaled data")
        except Exception as e:
            logger.error(f"Unexpected error in _scale for {self.symbol}: {e}")
        return X.values

    def _fit_scaler_and_scale(self, X):
        """
        Entrena el scaler con X y lo persiste en disco.

        Args:
            X (pd.DataFrame): Features para fit + transform.

        Returns:
            np.ndarray: Features escaladas.
        """
        Xs = self.scaler.fit_transform(X)
        joblib.dump(self.scaler, self.scaler_path)
        return Xs

    def _compute_weights(self, y):
        """
        Calcula class_weight='balanced' para clases desbalanceadas.

        Args:
            y (list[int]): Etiquetas (0=LOSS, 1=WIN).

        Returns:
            dict | None: {clase: peso} o None si solo hay una clase.
        """
        classes = np.unique(y)
        if len(classes) < 2:
            return None
        weights = compute_class_weight('balanced', classes=classes, y=np.array(y))
        return dict(zip(classes, weights))

    def get_consensus_prediction(self, features_dict, features_df=None, btc_features=None):
        """
        Genera la señal de trading combinando 9 estrategias + IA.

        Args:
            features_dict (dict):         Features del último candle.
            features_df (pd.DataFrame):   DataFrame completo (opcional).
            btc_features (pd.DataFrame):  Features de BTC para correlación.

        Returns:
            tuple[int|None, float, str, bool]:
                - action_code (1=LONG, 0=SHORT, None=sin señal)
                - confidence  (0.0 – 1.0)
                - method_name (estrategia dominante)
                - use_sl      (True si el modelo SL recomienda usarlo)
        """
        X  = self._build_X(features_dict)
        df = features_df if features_df is not None else pd.DataFrame([features_dict])

        basic_signals = {
            'trend':     trend_follower.analyze(df),
            'reversion': mean_reversion.analyze(df),
            'breakout':  breakout_logic.analyze(df),
        }
        structure_signals = {
            'smc':       smc_structure.analyze(df),
            'vwap':      vwap_method.analyze(df),
            'liquidity': liquidity_zones.analyze(df),
        }
        context_signals = {
            'orderflow': orderflow.analyze(df),
            'wyckoff':   wyckoff.analyze(df),
            'btc_corr':  btc_correlation.analyze(df, btc_features),
        }

        tech_action, tech_conf, method_name = self._weighted_consensus(
            basic_signals, structure_signals, context_signals
        )

        if tech_action is None:
            return None, 0, 'None', True

        # --- Veto de BTC (Tendencia de mercado global) ---
        if self.symbol != "BTCUSDT" and btc_features is not None:
            btc_action, _ = context_signals.get('btc_corr', (None, 0))
            if tech_action != btc_action:
                logger.info(f"🚫 BTC VETO en {self.symbol}: Desalineado con la tendencia global.")
                return None, 0, 'BTC Trend Veto', True

        # --- Veto de RSI Global Dinámico (Ajustado por Volatilidad) ---
        if btc_features is not None and 'RSI' in btc_features.columns and 'ATR_pct' in btc_features.columns:
            btc_rsi = btc_features.iloc[-1]['RSI']
            btc_vol = btc_features.iloc[-1]['ATR_pct']
            if not pd.isna(btc_rsi) and not pd.isna(btc_vol):
                vol_diff = btc_vol - self.RSI_VOL_REF
                adjustment = vol_diff * self.RSI_VOL_ADJ
                dyn_ob = max(65, min(85, self.RSI_OB_BASE - adjustment))
                dyn_os = max(15, min(35, self.RSI_OS_BASE + adjustment))

                if tech_action == 1 and btc_rsi >= dyn_ob:
                    return None, 0, 'RSI Overbought Veto', True
                elif tech_action == 0 and btc_rsi <= dyn_os:
                    return None, 0, 'RSI Oversold Veto', True

        ai_weight   = self._ai_weight()
        tech_weight = 1.0 - ai_weight
        ai_conf     = self._predict_outcome(X, tech_action)
        confidence  = (tech_conf * tech_weight) + (ai_conf * ai_weight)

        # --- MEJORA: Veto de IA (Contradicción detectada por el modelo) ---
        # Si la IA tiene experiencia (peso > 0.1) y estima una probabilidad de éxito
        # baja (< 40%), cancelamos la señal técnica por seguridad.
        if ai_weight > 0.1 and ai_conf < 0.40 and hasattr(self.model_outcome, 'classes_'):
            logger.info(f"🧠 IA VETO en {self.symbol}: Probabilidad de éxito baja ({ai_conf:.1%})")
            return None, 0, 'AI Veto', True
        # -----------------------------------------------------------------

        session_weight, _ = self._get_session_weight()
        confidence *= session_weight

        use_sl = self._predict_use_sl(X)
        return tech_action, confidence, method_name, use_sl

    def _weighted_consensus(self, basic, structure, context):
        """
        Voting ponderado entre las 3 capas de estrategias.
        """
        def layer_vote(signals):
            votes = {1: 0.0, 0: 0.0}
            best_conf, best_method = 0, 'None'
            for name, (action, conf) in signals.items():
                if action is not None:
                    votes[action] += conf
                    if conf > best_conf:
                        best_conf, best_method = conf, name
            if votes[1] == 0 and votes[0] == 0:
                return None, 0, 'None'

            # --- MEJORA: Detección de conflicto interno en la capa ---
            # Si las señales opuestas en una capa son muy similares, hay indecisión.
            v_max = max(votes[1], votes[0])
            v_min = min(votes[1], votes[0])
            if v_min > 0 and (v_min / v_max) > 0.7:
                return None, 0, 'Layer Conflict'

            winner = max(votes, key=votes.get)
            total  = votes[1] + votes[0] + 1e-9
            return winner, votes[winner] / total, best_method

        b_action, b_conf, b_name = layer_vote(basic)
        s_action, s_conf, s_name = layer_vote(structure)
        c_action, c_conf, c_name = layer_vote(context)

        lw = self.LAYER_WEIGHTS
        final_votes = {1: 0.0, 0: 0.0}
        for action, conf, weight in [
            (b_action, b_conf, lw['basic']),
            (s_action, s_conf, lw['structure']),
            (c_action, c_conf, lw['context']),
        ]:
            if action is not None:
                final_votes[action] += conf * weight

        if final_votes[1] == 0 and final_votes[0] == 0:
            return None, 0, 'None'

        # --- MEJORA: Detección de conflicto global entre capas ---
        v_max = max(final_votes[1], final_votes[0])
        v_min = min(final_votes[1], final_votes[0])
        if v_min > 0 and (v_min / v_max) > 0.8:
            return None, 0, 'Global Consensus Conflict'

        winner      = max(final_votes, key=final_votes.get)
        total       = final_votes[1] + final_votes[0] + 1e-9
        final_conf  = final_votes[winner] / total
        method_name = s_name if s_action == winner else (b_name if b_action == winner else c_name)
        return winner, final_conf, method_name

    def _ai_weight(self):
        """
        Calcula el peso actual del modelo ML (0.0 → MAX_AI_WEIGHT).

        Returns:
            float: 0.0 si hay menos trades que MIN_TRADES_FOR_AI,
                   hasta MAX_AI_WEIGHT cuando hay trades suficientes.
        """
        if self.trades_seen < self.MIN_TRADES_FOR_AI:
            return 0.0
        steps = getattr(self.cfg, 'AI_LEARNING_CURVE_STEPS', 45)
        ratio = min(1.0, (self.trades_seen - self.MIN_TRADES_FOR_AI) / steps)
        return ratio * self.MAX_AI_WEIGHT

    def _predict_outcome(self, X, action_code):
        """
        Probabilidad de WIN según el modelo de resultado.
        """
        try:
            if not hasattr(self.model_outcome, 'classes_'):
                return 0.5
            Xs    = self._scale(X)
            proba = self.model_outcome.predict_proba(Xs)[0]
            return proba[1] if action_code == 1 else (1 - proba[1])
        except IndexError as e:
            logger.warning(f"Prediction index error for {self.symbol}: {e}")
            return 0.5
        except Exception as e:
            logger.error(f"Error in _predict_outcome for {self.symbol}: {e}")
            return 0.5

    def _predict_use_sl(self, X):
        """
        Decide si usar stop-loss según el modelo SL.

        Returns:
            bool: True si se recomienda stop-loss activo.
        """
        try:
            if not hasattr(self.model_sl, 'classes_') or self.trades_seen < self.MIN_TRADES_FOR_AI:
                return True
            Xs = self._scale(X)
            return self.model_sl.predict_proba(Xs)[0][1] >= 0.5
        except IndexError as e:
            logger.warning(f"SL prediction index error for {self.symbol}: {e}")
            return True
        except Exception as e:
            logger.error(f"Error in _predict_use_sl for {self.symbol}: {e}")
            return True

    def online_update(self, features_dict, result_label, sl_was_used, sl_was_hit):
        """
        Actualiza los modelos con el resultado del trade recién cerrado.

        Args:
            features_dict (dict): Features que había en el momento de la entrada.
            result_label (str):   'WIN' o 'LOSS'.
            sl_was_used (bool):   Si el stop-loss estaba activo.
            sl_was_hit (bool):    Si el stop-loss fue tocado.
        """
        try:
            X         = self._build_X(features_dict)
            y_outcome = [1 if result_label == 'WIN' else 0]
            y_sl      = [1 if (sl_was_used and sl_was_hit) else 0]

            self._bootstrap_buffer.append((X, y_outcome, y_sl))

            # Recortar buffer al máximo permitido (evita acumulación infinita)
            if len(self._bootstrap_buffer) > self._max_buffer:
                self._bootstrap_buffer = self._bootstrap_buffer[-self._max_buffer:]

            if len(self._bootstrap_buffer) < 2:
                self.trades_seen += 1
                return

            ys_outcome = [b[1][0] for b in self._bootstrap_buffer]
            ys_sl      = [b[2][0] for b in self._bootstrap_buffer]
            X_all      = pd.concat([b[0] for b in self._bootstrap_buffer])
            Xs         = self._fit_scaler_and_scale(X_all)

            trained = False

            if len(set(ys_outcome)) >= 2:
                w = self._compute_weights(ys_outcome)
                self.model_outcome.set_params(
                    n_estimators=self.model_outcome.n_estimators + self.ESTIMATORS_STEP,
                    class_weight=w,
                )
                self.model_outcome.fit(Xs, ys_outcome)
                trained = True

            if len(set(ys_sl)) >= 2:
                w_sl = self._compute_weights(ys_sl)
                self.model_sl.set_params(
                    n_estimators=self.model_sl.n_estimators + self.ESTIMATORS_STEP,
                    class_weight=w_sl,
                )
                self.model_sl.fit(self._scale(X_all), ys_sl)
                trained = True

            self.trades_seen += 1

            # Vaciar el buffer tras el fit para no re-entrenar con datos viejos
            if trained:
                self._bootstrap_buffer = []

            self._save_all()
            print(
                f"🔄 Cerebro {self.symbol} actualizado "
                f"({self.trades_seen} exp. | peso IA: {self._ai_weight():.0%})"
            )

        except Exception as e:
            print(f"⚠️ online_update error en {self.symbol}: {e}")

    def nightly_retrain(self):
        """
        Reentrenamiento completo con todos los trades históricos del CSV.
        """
        print(f"\n{'🌙'*4} {self.symbol} SUEÑO: Reentrenando {'🌙'*4}")
        try:
            if not os.path.exists(self.cfg.DB_PATH):
                print(f"CEREBRO {self.symbol}: Sin historial todavía.")
                return

            conn = sqlite3.connect(self.cfg.DB_PATH)
            query = f"SELECT * FROM trades WHERE pair = '{self.symbol}'"
            df = pd.read_sql(query, conn)
            conn.close()

            if len(df) < self.MIN_TRADES_FOR_AI:
                print(f"CEREBRO {self.symbol}: {len(df)}/{self.MIN_TRADES_FOR_AI} trades mínimos.")
                return

            for c in self._feat_cols:
                if c not in df.columns:
                    df[c] = 0.0

            X         = df[self._feat_cols]
            y_outcome = df['result'].apply(lambda x: 1 if x == 'WIN' else 0).tolist()
            Xs        = self._fit_scaler_and_scale(X)
            w         = self._compute_weights(y_outcome)

            self.model_outcome = RandomForestClassifier(
                n_estimators=self.BASE_ESTIMATORS,
                random_state=self.cfg.RANDOM_STATE,
                warm_start=True,
                class_weight=w,
            )
            self.model_outcome.fit(Xs, y_outcome)

            if 'sl_was_used' in df.columns and 'sl_was_hit' in df.columns:
                df_sl = df.dropna(subset=['sl_was_used', 'sl_was_hit'])
                if len(df_sl) >= self.MIN_TRADES_FOR_AI:
                    Xs_sl = self.scaler.transform(df_sl[self._feat_cols])
                    y_sl  = (
                        (df_sl['sl_was_used'] == 1) & (df_sl['sl_was_hit'] == 1)
                    ).astype(int).tolist()
                    w_sl  = self._compute_weights(y_sl)
                    self.model_sl = RandomForestClassifier(
                        n_estimators=self.BASE_ESTIMATORS,
                        random_state=self.cfg.RANDOM_STATE,
                        warm_start=True,
                        class_weight=w_sl,
                    )
                    self.model_sl.fit(Xs_sl, y_sl)
                    print(f"🛡️  Modelo SL {self.symbol} reentrenado con {len(df_sl)} trades.")

            self.trades_seen       = len(df)
            self._bootstrap_buffer = []
            self._save_all()
            self._print_metrics(Xs, y_outcome)
            self._print_feature_importance()
            print(
                f"✅ EVOLUCIÓN {self.symbol}: {len(df)} lecciones | "
                f"peso IA: {self._ai_weight():.0%}"
            )

        except Exception as e:
            print(f"⚠️ Error en fase de sueño ({self.symbol}): {e}")

    def _print_metrics(self, Xs, y_true):
        """Imprime precisión, recall y F1 del modelo de outcome."""
        try:
            y_pred = self.model_outcome.predict(Xs)
            prec   = precision_score(y_true, y_pred, zero_division=0)
            rec    = recall_score(y_true, y_pred, zero_division=0)
            f1     = f1_score(y_true, y_pred, zero_division=0)
            print(f"\n📈 CALIDAD DEL MODELO {self.symbol}:")
            print(f"   Precision : {prec:.2%}")
            print(f"   Recall    : {rec:.2%}")
            print(f"   F1-Score  : {f1:.2%}  ← si sube sesión a sesión, el bot aprende")
        except ValueError as e:
            logger.warning(f"Metrics calculation error for {self.symbol}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error printing metrics for {self.symbol}: {e}")

    def _print_feature_importance(self):
        """Imprime el top 7 de features por importancia del modelo de outcome."""
        try:
            if not hasattr(self.model_outcome, 'feature_importances_'):
                return
            pairs = sorted(
                zip(self._feat_cols, self.model_outcome.feature_importances_),
                key=lambda x: x[1], reverse=True,
            )
            print(f"\n📊 TOP FEATURES {self.symbol}:")
            for feat, imp in pairs[:7]:
                bar = '█' * int(imp * 40)
                print(f"   {feat:<22} {bar} {imp:.3f}")
        except AttributeError as e:
            logger.warning(f"Feature importance not available for {self.symbol}: {e}")
        except Exception as e:
            logger.error(f"Error printing feature importance for {self.symbol}: {e}")

    def _save_all(self):
        """Persiste ambos modelos en disco (storage/)."""
        os.makedirs(self.cfg.STORAGE_DIR, exist_ok=True)
        joblib.dump(self.model_outcome, self.outcome_path)
        joblib.dump(self.model_sl,      self.sl_path)