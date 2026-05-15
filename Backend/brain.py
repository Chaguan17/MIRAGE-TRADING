import os
import joblib
import pandas as pd
import numpy as np
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import precision_score, recall_score, f1_score
from methods import (
    trend_follower, mean_reversion, breakout_logic,
    smc_structure, vwap_method, liquidity_zones,
    orderflow, wyckoff, btc_correlation,
)

logger = logging.getLogger(__name__)


class MirageBrain:

    MIN_TRADES_FOR_AI = 5
    MAX_AI_WEIGHT     = 0.70
    BASE_ESTIMATORS   = 100
    ESTIMATORS_STEP   = 10

    LAYER_WEIGHTS = {
        'basic':     0.25,
        'structure': 0.45,
        'context':   0.30,
    }

    def __init__(self, symbol="BTCUSDT"):
        self.symbol = symbol
        # Ahora cada moneda tiene sus propios archivos de memoria
        self.outcome_path = f'storage/model_outcome_{self.symbol}.pkl'
        self.sl_path      = f'storage/model_sl_{self.symbol}.pkl'
        self.scaler_path  = f'storage/scaler_{self.symbol}.pkl'

        self.model_outcome     = self._load_or_create(self.outcome_path)
        self.model_sl          = self._load_or_create(self.sl_path)
        self.scaler            = self._load_scaler()
        self.trades_seen       = self._count_historical_trades()
        self._bootstrap_buffer = []

        from data_engine import DataEngine
        self._feat_cols = DataEngine().get_feature_columns()

    def _load_or_create(self, path):
        if os.path.exists(path):
            print(f"🧠 Cargando modelo: {path}")
            return joblib.load(path)
        print(f"🧠 Modelo nuevo para {self.symbol} — Modo Experto Técnico.")
        return RandomForestClassifier(
            n_estimators=self.BASE_ESTIMATORS,
            random_state=42,
            warm_start=True,
        )

    def _load_scaler(self):
        if os.path.exists(self.scaler_path):
            return joblib.load(self.scaler_path)
        return StandardScaler()

    def _count_historical_trades(self):
        try:
            if os.path.exists('storage/trade_history.csv'):
                df = pd.read_csv('storage/trade_history.csv')
                if 'pair' in df.columns:
                    return len(df[df['pair'] == self.symbol])
                return len(df)
        except FileNotFoundError:
            logger.info(f"trade_history.csv not found for {self.symbol}")
        except pd.errors.EmptyDataError:
            logger.warning(f"trade_history.csv is empty for {self.symbol}")
        except Exception as e:
            logger.error(f"Error counting historical trades for {self.symbol}: {e}")
        return 0

    def _get_session_weight(self):
        import config
        from datetime import datetime, timezone
        hour_utc = datetime.now(timezone.utc).hour
        if 0 <= hour_utc < 8:
            session = 'asia'
        elif 8 <= hour_utc < 16:
            session = 'europa'
        else:
            session = 'america'
        return config.SESSION_WEIGHTS.get(session, 1.0), session

    def get_session_info(self):
        weight, session = self._get_session_weight()
        return session, weight

    def _build_X(self, features_dict):
        row = {col: features_dict.get(col, 0.0) for col in self._feat_cols}
        return pd.DataFrame([row])

    def _scale(self, X):
        try:
            if hasattr(self.scaler, 'mean_'):
                return self.scaler.transform(X)
        except ValueError as e:
            logger.warning(f"Scaler transform failed for {self.symbol}: {e}, returning unscaled data")
        except Exception as e:
            logger.error(f"Unexpected error in _scale for {self.symbol}: {e}")
        return X.values

    def _fit_scaler_and_scale(self, X):
        Xs = self.scaler.fit_transform(X)
        joblib.dump(self.scaler, self.scaler_path)
        return Xs

    def _compute_weights(self, y):
        classes = np.unique(y)
        if len(classes) < 2:
            return None
        weights = compute_class_weight('balanced', classes=classes, y=np.array(y))
        return dict(zip(classes, weights))

    def get_consensus_prediction(self, features_dict, features_df=None, btc_features=None):
        import config
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

        ai_weight   = self._ai_weight()
        tech_weight = 1.0 - ai_weight
        ai_conf     = self._predict_outcome(X, tech_action)
        confidence  = (tech_conf * tech_weight) + (ai_conf * ai_weight)

        session_weight, _ = self._get_session_weight()
        confidence *= session_weight

        use_sl = self._predict_use_sl(X)
        return tech_action, confidence, method_name, use_sl

    def _weighted_consensus(self, basic, structure, context):
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

        winner     = max(final_votes, key=final_votes.get)
        total      = final_votes[1] + final_votes[0] + 1e-9
        final_conf = final_votes[winner] / total
        method_name = s_name if s_action == winner else (b_name if b_action == winner else c_name)
        return winner, final_conf, method_name

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
        except IndexError as e:
            logger.warning(f"Prediction index error for {self.symbol}: {e}")
            return 0.5
        except Exception as e:
            logger.error(f"Error in _predict_outcome for {self.symbol}: {e}")
            return 0.5

    def _predict_use_sl(self, X):
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

            if len(set(ys_outcome)) >= 2:
                w = self._compute_weights(ys_outcome)
                self.model_outcome.set_params(
                    n_estimators=self.model_outcome.n_estimators + self.ESTIMATORS_STEP,
                    class_weight=w,
                )
                self.model_outcome.fit(Xs, ys_outcome)

            if len(set(ys_sl)) >= 2:
                w_sl = self._compute_weights(ys_sl)
                self.model_sl.set_params(
                    n_estimators=self.model_sl.n_estimators + self.ESTIMATORS_STEP,
                    class_weight=w_sl,
                )
                self.model_sl.fit(self._scale(X_all), ys_sl)

            self.trades_seen += 1
            self._save_all()
            print(f"🔄 Cerebro {self.symbol} actualizado ({self.trades_seen} exp. | peso IA: {self._ai_weight():.0%})")

        except Exception as e:
            print(f"⚠️ online_update error en {self.symbol}: {e}")

    def nightly_retrain(self, history_path='storage/trade_history.csv'):
        print(f"\n{'🌙'*4} {self.symbol} SUEÑO: Reentrenando {'🌙'*4}")
        try:
            if not os.path.exists(history_path):
                print(f"CEREBRO {self.symbol}: Sin historial todavía.")
                return

            df = pd.read_csv(history_path)
            
            # AISLAMIENTO: Filtramos para que solo aprenda de su propia moneda
            if 'pair' in df.columns:
                df = df[df['pair'] == self.symbol]

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
                random_state=42,
                warm_start=True,
                class_weight=w,
            )
            self.model_outcome.fit(Xs, y_outcome)

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
                    print(f"🛡️  Modelo SL {self.symbol} reentrenado con {len(df_sl)} trades.")

            self.trades_seen       = len(df)
            self._bootstrap_buffer = []
            self._save_all()
            self._print_metrics(Xs, y_outcome)
            self._print_feature_importance()
            print(f"✅ EVOLUCIÓN {self.symbol}: {len(df)} lecciones | peso IA: {self._ai_weight():.0%}")

        except Exception as e:
            print(f"⚠️ Error en fase de sueño ({self.symbol}): {e}")

    def _print_metrics(self, Xs, y_true):
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
        os.makedirs('storage', exist_ok=True)
        joblib.dump(self.model_outcome, self.outcome_path)
        joblib.dump(self.model_sl,      self.sl_path)