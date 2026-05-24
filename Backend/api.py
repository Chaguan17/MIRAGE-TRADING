from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import json
import os
import sqlite3
import logging
import importlib
import asyncio
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

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Envía datos a todos los clientes conectados de forma asíncrona."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Inicia el broadcaster en segundo plano al arrancar la API."""
    asyncio.create_task(dashboard_broadcaster())

async def dashboard_broadcaster():
    """Ciclo centralizado que hace push de actualizaciones cada 2 segundos."""
    while True:
        if manager.active_connections:
            payload = _fetch_dashboard_data()
            await manager.broadcast(payload)
        await asyncio.sleep(2)

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

def _fetch_dashboard_data():
    """Lógica centralizada para obtener métricas, usada por REST y WebSockets."""
    try:
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
        logger.error(f"Error in _fetch_dashboard_data: {e}")
        return {"error": str(e)}

@app.get("/api/dashboard")
def get_dashboard_data():
    """Mantiene compatibilidad con polling o carga inicial."""
    return _fetch_dashboard_data()

@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """Suspensión de WebSocket para actualizaciones en tiempo real."""
    await manager.connect(websocket)
    try:
        # Envío inicial inmediato al conectar
        await websocket.send_json(_fetch_dashboard_data())
        while True:
            await websocket.receive_text() # Mantiene la conexión viva y escucha desconexiones
    except WebSocketDisconnect:
        manager.disconnect(websocket)

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

class ConfigUpdate(BaseModel): # Modificado: Rangos más amplios para evitar errores 422 antes de normalizar
    LEVERAGE: int | None = Field(None, ge=1, le=125)
    RISK_PER_TRADE: float | None = Field(None, ge=0, le=100)
    MIN_CONFIDENCE: float | None = Field(None, ge=0, le=100)
    PAPER_BALANCE: float | None = Field(None, ge=1)
    # Gestión de Salidas (Stops) - Permitimos valores desde 0 para flexibilidad total
    ATR_MULTIPLIER: float | None = Field(None, ge=0)
    TP_MULTIPLIER: float | None = Field(None, ge=0)
    TRAILING_STOP_ACTIVATION: float | None = Field(None, ge=0)
    TRAILING_STOP_DISTANCE: float | None = Field(None, ge=0)
    BREAKEVEN_ACTIVATION: float | None = Field(None, ge=0)
    # Estrategia de Capital
    MARTINGALE_ENABLED: bool | None = None
    MAX_BULLETS: int | None = None
    COOLDOWN_CANDLES: int | None = None
    # Configuración de Flota y Horarios
    PARES_ACTIVOS: list[str] | None = None
    SLEEP_START_HOUR: int | None = None
    SLEEP_START_MINUTE: int | None = None
    SLEEP_END_HOUR: int | None = None
    SLEEP_END_MINUTE: int | None = None

@app.post("/api/config") # Modificado: Usa el modelo ConfigUpdate para validación
def update_config(new_settings: ConfigUpdate): 
    logger.info(f"Recibida actualización de config: {new_settings}")
    try:
        current = cfg.load_dynamic_settings()
    except Exception as e:
        logger.warning(f"Could not read existing config for merge: {e}")
        current = {}
    
    validated = new_settings.model_dump(exclude_none=True)
    
    percentage_fields = [
        "RISK_PER_TRADE",
        "MIN_CONFIDENCE",
        "TRAILING_STOP_ACTIVATION",
        "TRAILING_STOP_DISTANCE",
        "BREAKEVEN_ACTIVATION"
    ]
    
    for field in percentage_fields:
        if field in validated:
            value = validated[field]
            if value > 1:
                validated[field] = value / 100.0
    
    merged = {**current, **validated}
    with open(cfg.SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=4)
    
    return {"status": "success", "updated_keys": list(validated.keys())}