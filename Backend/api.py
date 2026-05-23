from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import os
import sqlite3
import logging
import importlib
import config as cfg

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

if not os.path.exists(cfg.SETTINGS_PATH):
    default_settings = {
        "TIMEFRAME": "1m",
        "PAPER_BALANCE": 1000.0,
        "RISK_PER_TRADE": 0.02,
        "MIN_CONFIDENCE": 0.65,
        "LEVERAGE": 10
    }
    os.makedirs(cfg.STORAGE_DIR, exist_ok=True)
    with open(cfg.SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(default_settings, f)

@app.get("/")
def read_root():
    return {"status": "online", "bot": "Mirage Trading"}

@app.get("/api/dashboard")
def get_dashboard_data():
    try:
        # Sinergia: Recargamos el módulo config para que el Dashboard 
        # siempre muestre los valores reales actuales (ej. pares activos)
        importlib.reload(cfg)
        
        try:
            with open(cfg.LIVE_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.info("live_state.json not found, returning default data")
            data = {
                "pnl_total": 0, "win_rate": 0, "total_operaciones": 0, "operaciones_activas": []
            }

        # Sinergia: Enviamos los pares activos actuales para que el frontend ajuste sus WebSockets
        # Normalización: Eliminamos espacios y forzamos mayúsculas para evitar fallos de coincidencia visual
        data["pares_activos"] = [str(p).strip().upper() for p in getattr(cfg, "PARES_ACTIVOS", [])]

        # Cambio de fuente: Leer desde SQLite en lugar de CSV
        if os.path.exists(cfg.DB_PATH):
            try:
                conn = sqlite3.connect(cfg.DB_PATH)
                # Filtramos UNKNOWN y limitamos para no saturar el JSON si el historial crece mucho
                query = "SELECT * FROM trades WHERE pair != 'UNKNOWN' ORDER BY timestamp ASC"
                df = pd.read_sql(query, conn)
                conn.close()

                if not df.empty:
                    df['pnl_acumulado'] = df['pnl_usdt'].cumsum()
                    data["chart_data"] = df.tail(30)[['timestamp', 'pnl_acumulado']].rename(
                        columns={'pnl_acumulado': 'pnl', 'timestamp': 'time'}
                    ).to_dict(orient="records")
                    data["ultimas_operaciones"] = df.tail(100).to_dict(orient="records")
                else:
                    data["chart_data"] = []
                    data["ultimas_operaciones"] = []
            except Exception as e:
                logger.error(f"Error reading history from DB: {e}")
                data["chart_data"] = []
                data["ultimas_operaciones"] = []
        else:
            data["chart_data"] = []
            data["ultimas_operaciones"] = []

        return data
    except Exception as e:
        logger.error(f"Error in get_dashboard_data: {e}")
        return {"error": str(e)}

@app.get("/api/performance")
async def get_full_performance():
    """Devuelve el historial completo de operaciones para análisis profundo."""
    try:
        if os.path.exists(cfg.DB_PATH):
            conn = sqlite3.connect(cfg.DB_PATH)
            df = pd.read_sql("SELECT * FROM trades ORDER BY timestamp ASC", conn)
            conn.close()
            data = df.to_dict(orient="records")
            logger.info(f"📊 Sirviendo historial desde DB: {len(data)} registros encontrados.")
            return data
        return []
    except Exception as e:
        logger.error(f"Error reading full history: {e}")
        return []


@app.get("/api/parameters")
def get_parameters_metadata():
    try:
        with open(cfg.METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("parameters_metadata.json not found")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in parameters_metadata.json: {e}")
        return {}

@app.get("/api/config")
def get_config():
    try:
        with open(cfg.SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found at {cfg.SETTINGS_PATH}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return {}

@app.post("/api/config")
def update_config(new_settings: dict):
    try:
        current = {}
        if os.path.exists(cfg.SETTINGS_PATH):
            with open(cfg.SETTINGS_PATH, "r", encoding="utf-8") as f:
                current = json.load(f)
    except Exception as e:
        logger.warning(f"Could not read existing config for merge: {e}")
        current = {}

    merged = {**current, **new_settings}

    with open(cfg.SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=4)

    return {"status": "success", "updated_keys": list(new_settings.keys())}