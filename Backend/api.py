from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import os

app = FastAPI(title="Mirage Trading API")

# Esto permite que nuestra web (frontend) se comunique con esta API sin errores de seguridad
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción cambiaremos esto por la URL de tu web
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_PATH = "storage/settings.json"

if not os.path.exists(CONFIG_PATH):
    default_settings = {
        "TIMEFRAME": "1m",
        "PAPER_BALANCE": 1000.0,
        "RISK_PER_TRADE": 0.02,
        "MIN_CONFIDENCE": 0.65,
        "LEVERAGE": 10
    }
    os.makedirs("storage", exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(default_settings, f)

# Ruta del archivo CSV de tu tracker
TRACKER_FILE = "storage/trade_history.csv"

@app.get("/")
def read_root():
    return {"status": "online", "bot": "Mirage Trading"}

@app.get("/api/dashboard")
def get_dashboard_data():
    try:
        # 1. LEER LA VERDAD ABSOLUTA DESDE EL BOT
        try:
            with open("storage/live_state.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            # Si el bot acaba de arrancar y aún no ha creado el archivo
            data = {
                "pnl_total": 0, "win_rate": 0, "total_operaciones": 0, "operaciones_activas": []
            }

        # 2. LEER EL CSV SOLO PARA EL HISTORIAL Y LA GRÁFICA
        try:
            df = pd.read_csv("storage/trade_history.csv")
            df['pnl_acumulado'] = df['pnl_usdt'].cumsum()
            
            # Gráfica: últimas 30 operaciones
            data["chart_data"] = df.tail(30)[['timestamp', 'pnl_acumulado']].rename(columns={'pnl_acumulado': 'pnl', 'timestamp': 'time'}).to_dict(orient="records")
            # Historial inferior: últimas 5
            data["ultimas_operaciones"] = df.tail(100).to_dict(orient="records")
        except:
            data["chart_data"] = []
            data["ultimas_operaciones"] = []

        return data
    except Exception as e:
        return {"error": str(e)}
    

@app.get("/api/config")
def get_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

@app.post("/api/config")
def update_config(new_settings: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(new_settings, f, indent=4)
    return {"status": "success"}