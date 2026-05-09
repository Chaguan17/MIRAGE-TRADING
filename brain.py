import os
import joblib
import datetime
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from methods import trend_follower, mean_reversion

class MirageBrain:
    def __init__(self, model_name="mirage_v1.pkl"):
        self.model_path = f"storage/{model_name}"
        # Definimos las columnas sensoriales exactas (La "visión" del bot)
        self.feature_columns = ['RSI', 'ATR', 'EMA_diff']
        self.model = self._load_model()

    def _load_model(self):
        """Carga la memoria persistente o inicializa un cerebro aprendiz."""
        if os.path.exists(self.model_path):
            print("🧠 Cerebro: Cargando memoria de experiencias previas...")
            return joblib.load(self.model_path)
        
        print("🧠 Cerebro: Inicializando nuevo modelo (Modo Aprendiz).")
        # Usamos class_weight='balanced' porque habrá más derrotas que victorias al inicio
        return RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')

    def get_consensus_prediction(self, features_dict):
        """
        ORQUESTADOR: Consulta expertos y filtra con IA.
        Retorna: (Acción, Confianza, Método)
        """
        # 1. Transformar diccionario de entrada en DataFrame para la IA
        df_features = pd.DataFrame([features_dict])
        # Aseguramos que EMA_diff esté presente (EMA_20 - EMA_50)
        df_features['EMA_diff'] = features_dict.get('EMA_20', 0) - features_dict.get('EMA_50', 0)
        
        # 2. Consultar a los expertos (Lógica Técnica)
        signals = {
            'trend': trend_follower.analyze(df_features),
            'reversion': mean_reversion.analyze(df_features)
        }
        
        best_action, method_conf, method_name = self._resolve_experts(signals)
        
        if best_action is None:
            return None, 0, "None"

        # 3. FILTRO DE IA: ¿Qué probabilidad de éxito tiene este escenario?
        ai_confidence = self._verify_with_ai(df_features[self.feature_columns])
        
        # Confianza Final: 40% Técnica + 60% IA
        final_confidence = (method_conf * 0.4) + (ai_confidence * 0.6)
        
        return best_action, final_confidence, method_name

    def _resolve_experts(self, signals):
        """Decide qué método técnico tiene más peso hoy."""
        best_action = None
        max_conf = 0
        method_used = "None"

        for name, (action, conf) in signals.items():
            if action is not None and conf > max_conf:
                best_action, max_conf, method_used = action, conf, name
        return best_action, max_conf, method_used

    def _verify_with_ai(self, X):
        """Calcula la probabilidad de éxito según el histórico."""
        try:
            # Si el modelo no ha sido entrenado (recién nacido), devuelve 0.5 (neutral)
            if not hasattr(self.model, "classes_"):
                return 0.5
            # predict_proba devuelve [prob_clase_0, prob_clase_1]
            return self.model.predict_proba(X)[0][1] 
        except:
            return 0.5

    def nightly_retrain(self, history_path='storage/trade_history.csv'):
        """Evolución del modelo basada en el diario de trading."""
        print(f"\n{'🌙' * 10} MODO SUEÑO: Procesando Experiencias {'🌙' * 10}")
        
        try:
            if not os.path.exists(history_path): return
            df = pd.read_csv(history_path)
            
            if len(df) < 10: # Subimos el listón a 10 para mayor estabilidad
                print(f"CEREBRO: {len(df)}/10 trades. Datos insuficientes para evolucionar.")
                return

            # Preparación de datos (X = Sentidos, y = Resultado)
            X = df[self.feature_columns]
            y = df['result'].apply(lambda x: 1 if x == 'WIN' else 0)

            self.model.fit(X, y)
            
            # Guardado con versión
            joblib.dump(self.model, self.model_path)
            print(f"✅ EVOLUCIÓN: El cerebro ha asimilado {len(df)} lecciones.")
            
        except Exception as e:
            print(f"⚠️ Error en fase de sueño: {e}")