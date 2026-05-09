import os
import joblib
from sklearn.ensemble import RandomForestClassifier
import datetime
import pandas as pd


class MirageBrain:
    def __init__(self, model_name="mirage_v1.pkl"):
        self.model_path = f"storage/{model_name}"
        self.model = self._load_model()

    def _load_model(self):
        # Si ya existe un aprendizaje previo, lo cargamos
        if os.path.exists(self.model_path):
            print("🧠 Cerebro: Cargando memoria de experiencias previas...")
            return joblib.load(self.model_path)
        
        # Si es un bot "recién nacido", creamos un modelo base
        print("🧠 Cerebro: Inicializando nuevo modelo (Modo Aprendiz).")
        return RandomForestClassifier(n_estimators=100, random_state=42)

    def train(self, df):
        """
        Entrena al bot usando los indicadores como entrada (X) 
        y el resultado futuro como salida (y).
        """
        # Seleccionamos las columnas que usaremos para predecir
        features = ['RSI', 'trend_signal', 'ATR'] 
        X = df[features]
        y = df['target']
        
        self.model.fit(X, y)
        
        # Guardamos lo aprendido en la carpeta storage
        if not os.path.exists('storage'):
            os.makedirs('storage')
        joblib.dump(self.model, self.model_path)
        print("📈 Cerebro: Entrenamiento completado. Memoria actualizada.")

    def predict(self, current_data):
        """
        Recibe los datos actuales y predice si hay probabilidad de éxito.
        """
        features = ['RSI', 'trend_signal', 'ATR']
        X = current_data[features].tail(1) # Solo la última fila
        
        prediction = self.model.predict(X)[0]
        # Obtenemos la probabilidad (ej: 0.75 significa 75% de confianza)
        probability = self.model.predict_proba(X).max()
        
        return prediction, probability
    
    def nightly_retrain(self, history_path='storage/trade_history.csv'):
        """
        MODO SUEÑO PROFUNDO: El cerebro analiza las nuevas columnas sensoriales
        y evoluciona su modelo para no repetir errores contextuales.
        """
        
        print("\n" + "🌙"*20)
        print("CEREBRO: Iniciando asimilación de experiencias...")
        
        try:
            if not os.path.exists(history_path):
                print("CEREBRO: No hay diario de operaciones. Sigo con el conocimiento actual.")
                return
                
            df = pd.read_csv(history_path)
            
            # Solo evolucionamos si tenemos suficientes experiencias nuevas (ej. 5 trades)
            if len(df) < 5:
                print(f"CEREBRO: Solo tengo {len(df)} experiencias. Necesito al menos 5 para no sacar conclusiones precipitadas.")
                return

            print(f"📚 Analizando {len(df)} trades con Memoria Sensorial...")

            # 1. EL "QUÉ PASÓ" (Features sensoriales)
            X_real = df[['RSI', 'ATR', 'EMA_diff']]
            
            # 2. EL "QUÉ DEBIÓ PASAR" (Etiquetas)
            # 1 si fue WIN, 0 si fue LOSS
            y_real = df['result'].apply(lambda x: 1 if x == 'WIN' else 0)

            # 3. RE-ENTRENAMIENTO (Refuerzo)
            # El modelo aprende a asociar esos indicadores con el éxito o el fracaso
            self.model.fit(X_real, y_real)
            
            # 4. EVOLUCIÓN DE ARCHIVO
            version = datetime.now().strftime("%Y%m%d")
            new_path = f"storage/mirage_brain_v{version}.pkl"
            joblib.dump(self.model, new_path)
            
            print(f"✅ EVOLUCIÓN COMPLETADA: He asimilado mis errores.")
            print(f"🧠 Nuevo modelo guardado: {new_path}")
            print("🌙"*20 + "\n")

        except Exception as e:
            print(f"⚠️ Error en la fase de sueño: {e}")