from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import os
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Mirage Trading API")

allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
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
            logger.info("live_state.json not found, returning default data")
            data = {
                "pnl_total": 0, "win_rate": 0, "total_operaciones": 0, "operaciones_activas": []
            }

        # 2. LEER EL CSV SOLO PARA EL HISTORIAL Y LA GRÁFICA
        try:
            df = pd.read_csv("storage/trade_history.csv")
            df['pnl_acumulado'] = df['pnl_usdt'].cumsum()

            data["chart_data"] = df.tail(30)[['timestamp', 'pnl_acumulado']].rename(columns={'pnl_acumulado': 'pnl', 'timestamp': 'time'}).to_dict(orient="records")
            data["ultimas_operaciones"] = df.tail(100).to_dict(orient="records")
        except FileNotFoundError:
            logger.warning("trade_history.csv not found")
            data["chart_data"] = []
            data["ultimas_operaciones"] = []
        except Exception as e:
            logger.error(f"Error reading trade history: {e}")
            data["chart_data"] = []
            data["ultimas_operaciones"] = []

        return data
    except Exception as e:
        logger.error(f"Error in get_dashboard_data: {e}")
        return {"error": str(e)}
    

@app.get("/api/config")
def get_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found at {CONFIG_PATH}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return {}

@app.post("/api/config")
def update_config(new_settings: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(new_settings, f, indent=4)
    return {"status": "success"}