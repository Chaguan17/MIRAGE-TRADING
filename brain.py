import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from methods import trend_follower, mean_reversion, breakout_logic


class MirageBrain:
    """
    Cerebro autodependiente de Mirage.

    Ciclo de vida:
    1. Sin historial → confía 100% en los expertos técnicos (arranca operando).
    2. Cada vez que se cierra un trade → online_update() refuerza el modelo
       inmediatamente con esa sola experiencia.
    3. En la ventana de sueño → nightly_retrain() reajusta el modelo completo
       con todo el historial acumulado.
    4. Cuantos más trades, más peso tiene la IA y menos los expertos técnicos,
       hasta un techo del 70% IA / 30% técnico.
    """

    MIN_TRADES_FOR_AI = 5      # A partir de aquí la IA empieza a opinar
    MAX_AI_WEIGHT     = 0.70   # Techo de peso de la IA (nunca descarta técnicos del todo)

    def __init__(self, model_name="mirage_v1.pkl"):
        self.model_path    = f"storage/{model_name}"
        self.feature_cols  = ['RSI', 'ATR', 'EMA_diff']
        self.model         = self._load_model()
        self.trades_seen   = self._count_historical_trades()

    # ──────────────────────────────────────────────────────────────────────────
    # CARGA / INICIALIZACIÓN
    # ──────────────────────────────────────────────────────────────────────────

    def _load_model(self):
        if os.path.exists(self.model_path):
            print("🧠 Cerebro: Cargando memoria de experiencias previas...")
            return joblib.load(self.model_path)
        print("🧠 Cerebro: Sin memoria previa — arrancando en Modo Experto Técnico.")
        return RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            class_weight='balanced',
            warm_start=True,   # permite añadir árboles sin reentrenar desde cero
        )

    def _count_historical_trades(self):
        """Cuántos trades ya hay en el CSV al arrancar."""
        path = 'storage/trade_history.csv'
        try:
            if os.path.exists(path):
                df = pd.read_csv(path)
                return len(df)
        except Exception:
            pass
        return 0

    # ──────────────────────────────────────────────────────────────────────────
    # PREDICCIÓN
    # ──────────────────────────────────────────────────────────────────────────

    def get_consensus_prediction(self, features_dict):
        df_f = pd.DataFrame([features_dict])
        if 'EMA_diff' not in features_dict:
            df_f['EMA_diff'] = features_dict.get('EMA_20', 0) - features_dict.get('EMA_50', 0)

        signals = {
            'trend':     trend_follower.analyze(df_f),
            'reversion': mean_reversion.analyze(df_f),
            'breakout':  breakout_logic.analyze(df_f),
        }

        best_action, tech_conf, method_name = self._resolve_experts(signals)
        if best_action is None:
            return None, 0, "None"

        # Pesos dinámicos: cuantos más trades, más IA y menos técnico puro
        ai_weight   = self._ai_weight()
        tech_weight = 1.0 - ai_weight

        ai_conf       = self._ai_confidence(df_f[self.feature_cols], best_action)
        final_conf    = (tech_conf * tech_weight) + (ai_conf * ai_weight)

        return best_action, final_conf, method_name

    def _resolve_experts(self, signals):
        best_action, max_conf, method_used = None, 0, "None"
        for name, (action, conf) in signals.items():
            if action is not None and conf > max_conf:
                best_action, max_conf, method_used = action, conf, name
        return best_action, max_conf, method_used

    def _ai_weight(self):
        """
        0.0  → sin trades (técnicos mandan)
        sube linealmente hasta MAX_AI_WEIGHT a partir de MIN_TRADES_FOR_AI.
        """
        if self.trades_seen < self.MIN_TRADES_FOR_AI:
            return 0.0
        ratio = min(1.0, (self.trades_seen - self.MIN_TRADES_FOR_AI) / 45)
        return ratio * self.MAX_AI_WEIGHT

    def _ai_confidence(self, X, action_code):
        """Probabilidad de que la IA avale la acción propuesta."""
        try:
            if not hasattr(self.model, "classes_"):
                return 0.5
            proba = self.model.predict_proba(X)[0]
            # proba[1] = prob de WIN; si la acción es SHORT devolvemos 1 - proba[1]
            return proba[1] if action_code == 1 else (1 - proba[1])
        except Exception:
            return 0.5

    # ──────────────────────────────────────────────────────────────────────────
    # APRENDIZAJE INMEDIATO (tras cada trade cerrado)
    # ──────────────────────────────────────────────────────────────────────────

    def online_update(self, features_dict, result_label):
        """
        Reforza el modelo con UN solo trade recién cerrado.
        Funciona tanto si el modelo está recién nacido como si ya tiene historial.
        result_label: 'WIN' o 'LOSS'
        """
        try:
            ema_diff = features_dict.get('EMA_diff',
                       features_dict.get('EMA_20', 0) - features_dict.get('EMA_50', 0))
            X = pd.DataFrame([{
                'RSI':     features_dict.get('RSI', 50),
                'ATR':     features_dict.get('ATR', 0),
                'EMA_diff': ema_diff,
            }])
            y = [1 if result_label == 'WIN' else 0]

            # warm_start=True: añade árboles en lugar de reemplazarlos
            trained = hasattr(self.model, "classes_")
            if not trained:
                # Primera vez: necesitamos al menos 2 clases distintas para fit
                # Si solo tenemos un resultado, guardamos y esperamos al siguiente
                if not hasattr(self, '_bootstrap_X'):
                    self._bootstrap_X = X
                    self._bootstrap_y = y
                    self.trades_seen += 1
                    return
                X = pd.concat([self._bootstrap_X, X])
                y = self._bootstrap_y + y
                del self._bootstrap_X, self._bootstrap_y

            self.model.fit(X, y)
            self.trades_seen += 1
            self._save_model()
            print(f"🔄 Cerebro actualizado al momento ({self.trades_seen} experiencias | peso IA: {self._ai_weight():.0%})")
        except Exception as e:
            print(f"⚠️ online_update error: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # REENTRENAMIENTO NOCTURNO COMPLETO
    # ──────────────────────────────────────────────────────────────────────────

    def nightly_retrain(self, history_path='storage/trade_history.csv'):
        """Reajusta el modelo completo con todo el historial (ventana de sueño)."""
        print(f"\n{'🌙' * 8} MODO SUEÑO: Procesando Experiencias {'🌙' * 8}")
        try:
            if not os.path.exists(history_path):
                print("CEREBRO: Sin historial todavía.")
                return

            df = pd.read_csv(history_path)
            if len(df) < self.MIN_TRADES_FOR_AI:
                print(f"CEREBRO: {len(df)}/{self.MIN_TRADES_FOR_AI} trades. "
                      f"Operando en Modo Experto Técnico hasta acumular más datos.")
                return

            X = df[self.feature_cols]
            y = df['result'].apply(lambda x: 1 if x == 'WIN' else 0)

            # Reentrenamiento completo (resetea warm_start)
            self.model.set_params(warm_start=False)
            self.model.fit(X, y)
            self.model.set_params(warm_start=True)

            self.trades_seen = len(df)
            self._save_model()
            print(f"✅ EVOLUCIÓN NOCTURNA: {len(df)} lecciones asimiladas | "
                  f"peso IA: {self._ai_weight():.0%}")

        except Exception as e:
            print(f"⚠️ Error en fase de sueño: {e}")

    def _save_model(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
