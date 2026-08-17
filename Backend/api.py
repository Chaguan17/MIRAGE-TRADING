from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import json
import os
import time
import sqlite3
import logging
import importlib
import asyncio
from contextlib import asynccontextmanager
import config as cfg
import notification_manager as nm

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida: reemplaza los eventos startup/shutdown."""
    # Tareas al iniciar
    broadcaster_task = asyncio.create_task(dashboard_broadcaster())
    yield
    # Tareas al cerrar
    broadcaster_task.cancel()
    try:
        await broadcaster_task
    except asyncio.CancelledError:
        pass

import math

def sanitize_nan(obj):
	if isinstance(obj, float):
		if math.isnan(obj) or math.isinf(obj):
			return 0.0
		return obj
	elif isinstance(obj, dict):
		return {k: sanitize_nan(v) for k, v in obj.items()}
	elif isinstance(obj, list):
		return [sanitize_nan(v) for v in obj]
	return obj

app = FastAPI(title="Mirage Trading API", lifespan=lifespan)

allowed_origins = [
	"http://localhost:5173",
	"http://localhost:5174",
	"http://localhost:3000",
	"http://127.0.0.1:5173",
	"http://127.0.0.1:5174",
	"http://127.0.0.1:3000",
]
if os.getenv("CORS_ORIGINS"):
	allowed_origins.extend(os.getenv("CORS_ORIGINS").split(","))

app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
	allow_origin_regex=r"http://.*",
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
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

async def dashboard_broadcaster():
	"""Ciclo centralizado que hace push de actualizaciones cada segundo."""
	while True:
		if manager.active_connections:
            # Ejecutamos la carga de datos (síncrona) en un hilo aparte para no bloquear
			payload = await asyncio.to_thread(_fetch_dashboard_data)
			await manager.broadcast(payload)
		await asyncio.sleep(1)

if not os.path.exists(cfg.SETTINGS_PATH):
	default_settings = {
	"TIMEFRAME": "1m",
	"PAPER_TRADING": True,
	"PAPER_BALANCE": 100.0,
	"RISK_PER_TRADE": 0.01,
	"MIN_CONFIDENCE": 0.65,
	"LEVERAGE": 5
}
	os.makedirs(cfg.STORAGE_DIR, exist_ok=True)
	with open(cfg.SETTINGS_PATH, "w", encoding="utf-8") as f:
		json.dump(default_settings, f)

@app.get("/")
def read_root():
	return {"status": "online", "bot": "Mirage Trading"}

_LAST_LIVE_STATE = {
	"pnl_total": 0, "pnl_diario": 0, "win_rate": 0, "total_operaciones": 0, "operaciones_activas": []
}
_LAST_HISTORY_STATE = {
	"chart_data": [], "ultimas_operaciones": []
}
_CACHED_REAL_CLIENT = None
_LAST_BINANCE_SYNC_TS = 0.0
_CACHED_REAL_POSITIONS = {}
_LAST_REAL_POSITIONS_TS = 0.0

def sanitize_config(config_dict):
	sanitized = config_dict.copy()
	if "API_KEY" in sanitized:
		val = sanitized["API_KEY"]
		sanitized["API_KEY"] = "********" + val[-5:] if (val and len(val) > 5) else ""
	if "API_SECRET" in sanitized:
		val = sanitized["API_SECRET"]
		sanitized["API_SECRET"] = "********" + val[-5:] if (val and len(val) > 5) else ""
	return sanitized

API_SECRET_TOKEN = os.getenv("API_SECRET_TOKEN", "").strip()

async def verify_auth(authorization: str = Header(None), token: str = Query(None)):
	if API_SECRET_TOKEN:
		provided = None
		if authorization and authorization.startswith("Bearer "):
			provided = authorization.split(" ")[1]
		elif token:
			provided = token
		if provided != API_SECRET_TOKEN:
			raise HTTPException(status_code=401, detail="Unauthorized")

def _fetch_dashboard_data():
	"""Lógica centralizada para obtener métricas, usada por REST y WebSockets."""
	global _LAST_LIVE_STATE, _LAST_HISTORY_STATE
	try:
		# 1. Cargar configuración actual directamente del archivo para asegurar interactividad
		current_config = {}
		if os.path.exists(cfg.SETTINGS_PATH):
			try:
				with open(cfg.SETTINGS_PATH, "r", encoding="utf-8") as f:
					current_config = json.load(f)
			except Exception as e:
				logger.error(f"Error reading settings.json: {e}")

		# 2. Cargar estado en vivo
		try:
			import sqlite3
			conn = sqlite3.connect(cfg.DB_PATH, timeout=15.0)
			c = conn.cursor()
			c.execute("SELECT state_json FROM system_state WHERE id = 1")
			row = c.fetchone()
			conn.close()
			if row and row[0]:
				data = json.loads(row[0])
				_LAST_LIVE_STATE = data
			else:
				data = _LAST_LIVE_STATE.copy()

			# Reconstrucción proactiva de operaciones activas leyendo los JSON en storage/
			active_trades = []
			if os.path.exists(cfg.STORAGE_DIR):
				for file_name in os.listdir(cfg.STORAGE_DIR):
					if file_name.startswith("active_trades_") and file_name.endswith(".json"):
						pair = file_name.replace("active_trades_", "").replace(".json", "")
						if pair == "TESTUSDT" or pair == "UNKNOWN":
							continue
						path = os.path.join(cfg.STORAGE_DIR, file_name)
						try:
							with open(path, "r", encoding="utf-8") as f:
								content = f.read().strip()
								trades_list = json.loads(content) if content else []
							if isinstance(trades_list, list):
								for t in trades_list:
									size_val = float(t.get("size", 0))
									entry_val = float(t.get("entry_price", 0))
									active_trades.append({
										"pair": pair,
										"type": t.get("action", "LONG"),
										"entry": entry_val,
										"size": size_val,
										"tp": float(t.get("tp", 0)),
										"sl": float(t.get("sl", 0)) if t.get("sl") is not None else 0,
										"bullets": int(t.get("bullets", 1)),
										"position_value": float(t.get("position_value", 0)) or (size_val * entry_val),
										"current_pnl": float(t.get("current_pnl", 0)),
										"current_price": float(t.get("current_price", entry_val)) or entry_val,
										"timestamp": t.get("timestamp", "")
									})
						except Exception as err:
							logger.error(f"Error parsing active trades file {file_name}: {err}")

			# Enriquecer directamente desde Binance si está en Modo Real para cero desincronización
			if not current_config.get("PAPER_TRADING", True) and cfg.API_KEY:
				try:
					global _CACHED_REAL_CLIENT, _LAST_BINANCE_SYNC_TS, _CACHED_REAL_POSITIONS, _LAST_REAL_POSITIONS_TS
					from binance_api import MirageBinance
					if _CACHED_REAL_CLIENT is None or _CACHED_REAL_CLIENT.paper_trading:
						_CACHED_REAL_CLIENT = MirageBinance(cfg.API_KEY, cfg.API_SECRET, paper_trading=False)
					real_client = _CACHED_REAL_CLIENT
					
					now_pos_ts = time.time()
					if now_pos_ts - _LAST_REAL_POSITIONS_TS > 5.0 or not _CACHED_REAL_POSITIONS:
						try:
							_CACHED_REAL_POSITIONS = real_client.get_open_positions() or {}
							_LAST_REAL_POSITIONS_TS = now_pos_ts
						except Exception as pos_err:
							logger.warning(f"Error consultando posiciones reales de Binance: {pos_err}")
					
					real_positions = _CACHED_REAL_POSITIONS
					
					active_pairs_in_list = {t["pair"] for t in active_trades}

					if real_positions and isinstance(real_positions, dict):
						for sym, real_pos in real_positions.items():
							clean_sym = sym.replace(":USDT", "").replace("/", "")
							sl_val = float(real_pos.get("sl", 0) or 0)
							tp_val = float(real_pos.get("tp", 0) or 0)
							is_long = real_pos.get("side", "LONG") == "LONG"
							entry_p = float(real_pos.get("entry_price", 0))
							if sl_val <= 0 and entry_p > 0:
								sl_val = entry_p * 0.98 if is_long else entry_p * 1.02

							if clean_sym not in active_pairs_in_list:
								# Si la posición está abierta en Binance pero no estaba en la lista local
								active_trades.append({
									"pair": clean_sym,
									"type": real_pos.get("side", "LONG"),
									"entry": entry_p,
									"size": float(real_pos.get("contracts", 0)),
									"tp": tp_val,
									"sl": sl_val,
									"bullets": 1,
									"position_value": round(float(real_pos.get("contracts", 0)) * entry_p, 2),
									"current_pnl": float(real_pos.get("pnl", 0)),
									"current_price": float(real_pos.get("current_price", 0)) or entry_p,
									"timestamp": ""
								})
							else:
								for t in active_trades:
									if t["pair"] == clean_sym:
										if real_pos.get("entry_price"):
											t["entry"] = float(real_pos["entry_price"])
										if real_pos.get("contracts"):
											t["size"] = float(real_pos["contracts"])
										if real_pos.get("pnl") is not None:
											t["current_pnl"] = float(real_pos["pnl"])
										if real_pos.get("current_price"):
											t["current_price"] = float(real_pos["current_price"])
										if sl_val > 0:
											t["sl"] = sl_val
										elif not t.get("sl") or float(t.get("sl", 0)) <= 0:
											t["sl"] = t["entry"] * 0.98 if t.get("type") == "LONG" else t["entry"] * 1.02
										if tp_val > 0:
											t["tp"] = tp_val
										else:
											if t.get("type") == "SHORT" and (not t.get("tp") or float(t.get("tp", 0)) >= t.get("entry", 0)):
												t["tp"] = round(t["entry"] * 0.95, 4)
											elif t.get("type") == "LONG" and (not t.get("tp") or float(t.get("tp", 0)) <= t.get("entry", 0)):
												t["tp"] = round(t["entry"] * 1.05, 4)
										t["position_value"] = round(t["size"] * t["entry"], 2)
					# Auto-sincronizar el historial de ejecuciones reales de Binance a la BD SQLite (cada 30s)
					now_sync_ts = time.time()
					if now_sync_ts - _LAST_BINANCE_SYNC_TS > 30.0:
						_LAST_BINANCE_SYNC_TS = now_sync_ts
						try:
							conn_sync = sqlite3.connect(cfg.DB_PATH, timeout=30.0)
							conn_sync.execute("PRAGMA journal_mode=WAL;")
							# Limpiar registros antiguos corruptos con pnl 0 de ejecuciones de entrada
							conn_sync.execute("DELETE FROM trades WHERE is_paper = 'REAL' AND pnl_usdt = 0.0")
							for sym in ['ETH/USDT:USDT', 'BTC/USDT:USDT', 'XRP/USDT:USDT']:
								clean_sym = sym.replace(':USDT', '').replace('/', '')
								trades_from_binance = real_client.client.fetch_my_trades(sym, limit=50)
								for t in trades_from_binance:
									info = t.get('info', {})
									rpnl = float(info.get('realizedPnl') or t.get('realizedPnl') or 0.0)
									# Solo procesar cierres reales de posición con PnL significativo (> 0.005 USDT)
									if abs(rpnl) < 0.005:
										continue

									fill_id = str(t.get('order') or t.get('id') or '')
									if not fill_id:
										continue

									closed_dt = str(t.get('datetime', '')).replace('T', ' ').replace('.000Z', '').replace('Z', '')[:19]
									t_ts = t.get('timestamp', 0)
									open_fills = [tr for tr in trades_from_binance if tr.get('timestamp', 0) < t_ts and abs(float(tr.get('info',{}).get('realizedPnl', 0))) <= 1e-6]
									opened_dt = open_fills[-1].get('datetime', '').replace('T', ' ').replace('.000Z', '').replace('Z', '')[:19] if open_fills else closed_dt

									fill_side = t.get('side', '').lower()
									action = 'SHORT' if fill_side == 'buy' else 'LONG'
									close_p = float(t.get('price', 0))
									amount = float(t.get('amount', 0))

									if amount <= 0:
										continue

									# Calcular precio de entrada implícito a partir del PnL realizado
									if action == 'SHORT':
										entry_p = close_p + (rpnl / amount)
									else:
										entry_p = close_p - (rpnl / amount)

									entry_p = round(max(0.0001, entry_p), 4)
									close_p = round(close_p, 4)
									rpnl_rounded = round(rpnl, 4)
									res_str = 'WIN' if rpnl >= 0 else 'LOSS'

									c = conn_sync.execute('SELECT COUNT(*) FROM trades WHERE order_id = ? OR (pair = ? AND timestamp = ? AND pnl_usdt = ?)', (fill_id, clean_sym, closed_dt, rpnl_rounded))
									if c.fetchone()[0] == 0:
										conn_sync.execute(
											'INSERT INTO trades (timestamp, pair, action, entry_price, close_price, size, result, pnl_usdt, order_id, is_paper, opened_at, closed_at) '
											'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
											(closed_dt, clean_sym, action, entry_p, close_p, amount, res_str, rpnl_rounded, fill_id, 'REAL', opened_dt, closed_dt)
										)
							conn_sync.commit()
							conn_sync.close()
						except Exception as sync_err:
							logger.warning(f"Error sincronizando historial real de Binance: {sync_err}")
				except Exception as binance_sync_err:
					logger.warning(f"No se pudo sincronizar directamente con Binance: {binance_sync_err}")
			
			data["operaciones_activas"] = active_trades
		except Exception as e:
			logger.error(f"Error reading SQLite system_state: {e}")
			data = _LAST_LIVE_STATE.copy()

		# 3. Inyectar configuración y balance para el Dashboard
		data["config"] = sanitize_config(current_config)
		
		if "balance_actual" not in data or data["balance_actual"] == 0:
			data["balance_actual"] = current_config.get("PAPER_BALANCE", 0)

		is_paper_mode = current_config.get("PAPER_TRADING", True)
		is_paper_tag = 'PAPER' if is_paper_mode else 'REAL'

		# 4. Asegurar pnl_diario (si no viene en system_state, calcularlo directo de DB filtrando por modo)
		if "pnl_diario" not in data or data["pnl_diario"] is None:
			try:
				from datetime import datetime
				today_prefix = datetime.now().strftime('%Y-%m-%d') + '%'
				conn_daily = sqlite3.connect(cfg.DB_PATH, timeout=5.0)
				r_daily = conn_daily.execute(
					"SELECT SUM(pnl_usdt) FROM trades WHERE pair != 'UNKNOWN' AND pair != 'TESTUSDT' "
					"AND (is_paper = ? OR (is_paper IS NULL AND ? = 'PAPER')) AND timestamp LIKE ?",
					(is_paper_tag, is_paper_tag, today_prefix)
				).fetchone()
				conn_daily.close()
				data["pnl_diario"] = round(float(r_daily[0]), 2) if (r_daily and r_daily[0] is not None) else 0.0
			except Exception as e:
				logger.error(f"Error calculating fallback pnl_diario: {e}")
				data["pnl_diario"] = 0.0

		# Sincronizar pares activos desde la configuración cargada
		pares_cfg = current_config.get("PARES_ACTIVOS", cfg.PARES_ACTIVOS)
		data["pares_activos"] = [str(p).strip().upper() for p in pares_cfg]
		data["notifications"] = nm.get_notifications()

		# Cambio de fuente: Leer desde SQLite en lugar de CSV con filtrado de modo estricto
		if os.path.exists(cfg.DB_PATH):
			try:
				conn = sqlite3.connect(cfg.DB_PATH, timeout=5.0)
				# Aislar trades de MODO REAL vs MODO PAPER SIM
				if is_paper_mode:
					query = "SELECT * FROM trades WHERE pair != 'UNKNOWN' AND pair != 'TESTUSDT' AND (is_paper = 'PAPER' OR is_paper IS NULL OR order_id IS NULL OR order_id IN ('0','OK','NONE','')) ORDER BY timestamp DESC"
				else:
					query = "SELECT * FROM trades WHERE pair != 'UNKNOWN' AND pair != 'TESTUSDT' AND (is_paper = 'REAL' OR (is_paper IS NULL AND order_id IS NOT NULL AND order_id NOT IN ('0','OK','NONE',''))) ORDER BY timestamp DESC"
				
				df = pd.read_sql(query, conn)
				conn.close()

				if not df.empty:
					df['pnl_acumulado'] = df['pnl_usdt'].cumsum()
					data["chart_data"] = df.tail(30)[['timestamp', 'pnl_acumulado']].rename(
						columns={'pnl_acumulado': 'pnl', 'timestamp': 'time'}
					).to_dict(orient="records")
					data["ultimas_operaciones"] = df.head(100).to_dict(orient="records")
					_LAST_HISTORY_STATE = {"chart_data": data["chart_data"], "ultimas_operaciones": data["ultimas_operaciones"]}
				else:
					data["chart_data"] = []
					data["ultimas_operaciones"] = []

				# Cargar registros de auditoría de desincronización (POSITION DESYNC)
				try:
					conn_desync = sqlite3.connect(cfg.DB_PATH, timeout=5.0)
					desync_df = pd.read_sql("SELECT * FROM desync_audit_logs ORDER BY id DESC LIMIT 20", conn_desync)
					conn_desync.close()
					data["desync_logs"] = desync_df.to_dict(orient="records") if not desync_df.empty else []
				except Exception:
					data["desync_logs"] = []
			except Exception as e:
				logger.error(f"Error reading history from DB: {e}")
				data["chart_data"] = _LAST_HISTORY_STATE["chart_data"]
				data["ultimas_operaciones"] = _LAST_HISTORY_STATE["ultimas_operaciones"]
		else:
			data["chart_data"] = []
			data["ultimas_operaciones"] = []

		return sanitize_nan(data)
	except Exception as e:
		logger.error(f"Error in _fetch_dashboard_data: {e}")
		return {"error": str(e)}

@app.get("/api/dashboard")
def get_dashboard_data(_ = Depends(verify_auth)):
	"""Mantiene compatibilidad con polling o carga inicial."""
	return _fetch_dashboard_data()

@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket, _ = Depends(verify_auth)):
	"""WebSocket con push periódico cada 3s para precios en tiempo real."""
	await manager.connect(websocket)
	try:
		# Envío inicial inmediato al conectar
		await websocket.send_json(sanitize_nan(_fetch_dashboard_data()))
		while True:
			try:
				# Espera mensajes del cliente con timeout de 3s
				# Si no llega nada en 3s, envía datos frescos
				await asyncio.wait_for(websocket.receive_text(), timeout=3.0)
			except asyncio.TimeoutError:
				# Timeout = hora de enviar datos frescos al frontend
				try:
					await websocket.send_json(sanitize_nan(_fetch_dashboard_data()))
				except Exception:
					break
	except WebSocketDisconnect:
		manager.disconnect(websocket)
	except Exception:
		manager.disconnect(websocket)

@app.get("/api/performance")
async def get_full_performance(_ = Depends(verify_auth)):
	"""Devuelve el historial completo de operaciones para análisis profundo."""
	try:
		if os.path.exists(cfg.DB_PATH):
			conn = sqlite3.connect(cfg.DB_PATH, timeout=15.0)
			is_paper_mode = bool(getattr(config, 'PAPER_TRADING', True))
			if os.path.exists(cfg.SETTINGS_PATH):
				try:
					with open(cfg.SETTINGS_PATH, "r", encoding="utf-8") as f:
						is_paper_mode = json.load(f).get("PAPER_TRADING", True)
				except Exception:
					pass

			if is_paper_mode:
				query = "SELECT * FROM trades WHERE pair != 'UNKNOWN' AND pair != 'TESTUSDT' AND (is_paper = 'PAPER' OR is_paper IS NULL OR order_id IS NULL OR order_id IN ('0','OK','NONE','')) ORDER BY timestamp ASC"
			else:
				query = "SELECT * FROM trades WHERE pair != 'UNKNOWN' AND pair != 'TESTUSDT' AND (is_paper = 'REAL' OR (is_paper IS NULL AND order_id IS NOT NULL AND order_id NOT IN ('0','OK','NONE',''))) ORDER BY timestamp ASC"
			
			df = pd.read_sql(query, conn)
			conn.close()
			data = df.to_dict(orient="records")
			logger.info(f"📊 Sirviendo historial desde DB ({'PAPER' if is_paper_mode else 'REAL'}): {len(data)} registros encontrados.")
			return sanitize_nan(data)
		return []
	except Exception as e:
		logger.error(f"Error reading full history: {e}")
		return []

@app.get("/api/backtest-vs-real")
async def get_backtest_vs_real_comparison(symbol: str = "ETHUSDT", _ = Depends(verify_auth)):
	"""Compara cuantitativamente la ejecución simulada (Backtest) vs dinero real."""
	try:
		from backtest_vs_real import BacktestVsRealComparator
		comparator = BacktestVsRealComparator()
		res = comparator.compare(symbol=symbol)
		return sanitize_nan(res)
	except Exception as e:
		logger.error(f"Error calculando comparación Backtest vs Real: {e}")
		return {"status": "error", "message": str(e)}

class CommandInput(BaseModel):
	action: str
	symbol: str | None = None

@app.post("/api/commands")
def send_command(cmd: CommandInput, _ = Depends(verify_auth)):
	command_path = os.path.join(cfg.STORAGE_DIR, "commands.json")
	try:
		payload = {"action": cmd.action, "timestamp": pd.Timestamp.utcnow().isoformat()}
		if cmd.symbol:
			payload["symbol"] = cmd.symbol.upper()
		with open(command_path, "w", encoding="utf-8") as f:
			json.dump(payload, f)
		return {"status": "ok", "command": cmd.action, "symbol": cmd.symbol}
	except Exception as e:
		return {"error": str(e)}

@app.post("/api/close_position/{symbol}")
def close_position_by_symbol(symbol: str, _ = Depends(verify_auth)):
	clean_symbol = symbol.strip().upper()
	command_path = os.path.join(cfg.STORAGE_DIR, "commands.json")
	try:
		with open(command_path, "w", encoding="utf-8") as f:
			json.dump({"action": "CLOSE_POSITION", "symbol": clean_symbol, "timestamp": pd.Timestamp.utcnow().isoformat()}, f)

		nm.add_notification(
			"SUCCESS",
			f"Cierre Solicitado ({clean_symbol})",
			f"Se envió la orden de cierre para {clean_symbol}. El orquestador la procesará en Binance.",
			clean_symbol
		)
		return {"status": "ok", "symbol": clean_symbol}
	except Exception as e:
		logger.error(f"Error closing position {symbol}: {e}")
		return {"error": str(e)}

@app.get("/api/chart/{symbol}")
def get_chart_data(symbol: str, tf: str = None, _ = Depends(verify_auth)):
	import ccxt
	try:
		clean_symbol = symbol.strip().upper()
		exchange = ccxt.binance({
			'enableRateLimit': True,
			'timeout': 10000,
			'options': {'defaultType': 'future'}
		})
		if not tf:
			with open(cfg.SETTINGS_PATH, "r", encoding="utf-8") as f:
				settings = json.load(f)
			tf = settings.get("TIMEFRAME", "15m")
		ohlcv = exchange.fetch_ohlcv(clean_symbol, tf, limit=200)
		data = []
		for row in ohlcv:
			data.append({
				"time": row[0] // 1000,
				"open": row[1],
				"high": row[2],
				"low": row[3],
				"close": row[4],
				"volume": row[5]
			})
		return data
	except Exception as e:
		logger.error(f"Error fetching chart data for {symbol}: {e}")
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
def get_config(_ = Depends(verify_auth)):
	try:
		with open(cfg.SETTINGS_PATH, "r", encoding="utf-8") as f:
			return sanitize_config(json.load(f))
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
	PAPER_TRADING: bool | None = None
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
	TIMEFRAME: str | None = None
	SLEEP_START_HOUR: int | None = None
	SLEEP_START_MINUTE: int | None = None
	SLEEP_END_HOUR: int | None = None
	SLEEP_END_MINUTE: int | None = None
	MAX_RISK_CAP: float | None = Field(None, ge=0)
	MAX_CONSECUTIVE_WINS: int | None = None
	MAX_CONSECUTIVE_LOSSES: int | None = None
	RISK_INCREASE_FACTOR: float | None = None
	RISK_REDUCTION_FACTOR: float | None = None
	ADAPTIVE_RISK_ENABLED: bool | None = None
	ADAPTIVE_RISK_FLOOR: float | None = Field(None, ge=0)
	ADAPTIVE_RISK_CEIL: float | None = Field(None, ge=0)
	ADAPTIVE_DRAWDOWN_FLOOR: float | None = Field(None, ge=0)
	ADAPTIVE_GROWTH_CEIL: float | None = Field(None, ge=0)
	DCA_ATR_MULT_1: float | None = Field(None, ge=0)
	DCA_ATR_MULT_2: float | None = Field(None, ge=0)
	MARTINGALE_MULTIPLIER: float | None = None
	MARTINGALE_MAX_STEPS: int | None = None
	MIN_SIZE_USDT: float | None = Field(None, ge=0)
	# Parámetros adicionales y de análisis
	TRAILING_ATR_MULTIPLIER: float | None = Field(None, ge=0)
	USE_LIMIT_ORDERS: bool | None = None
	VETO_CRASH_PCT: float | None = Field(None, ge=0, le=100)
	GLOBAL_RSI_OB_BASE: float | None = Field(None, ge=0)
	GLOBAL_RSI_OS_BASE: float | None = Field(None, ge=0)
	MAX_DRAWDOWN_HALT_PCT: float | None = Field(None, ge=0, le=100)
	NO_SL_SIZE_PCT: float | None = Field(None, ge=0, le=100)
	SMC_LOOKBACK: int | None = Field(None, ge=1)
	SMC_OB_STRENGTH: float | None = Field(None, ge=0, le=100)
	WYCKOFF_LOOKBACK: int | None = Field(None, ge=1)
	LIQ_LOOKBACK: int | None = Field(None, ge=1)
	LIQ_CLUSTER_PCT: float | None = Field(None, ge=0, le=100)
	BTC_CORR_THRESHOLD: float | None = Field(None, ge=0, le=1)
	VWAP_BAND_MULT: float | None = Field(None, ge=0)
	# Estrategias Habilitadas
	STRATEGY_TREND: bool | None = None
	STRATEGY_REVERSION: bool | None = None
	STRATEGY_BREAKOUT: bool | None = None
	STRATEGY_SMC: bool | None = None
	STRATEGY_VWAP: bool | None = None
	STRATEGY_LIQUIDITY: bool | None = None
	STRATEGY_ORDERFLOW: bool | None = None
	STRATEGY_WYCKOFF: bool | None = None
	STRATEGY_BTC_CORR: bool | None = None

@app.post("/api/config") # Modificado: Usa el modelo ConfigUpdate para validación
def update_config(new_settings: ConfigUpdate, _ = Depends(verify_auth)): 
	logger.info(f"Recibida actualización de config: {new_settings}")
	try:
		current = cfg.load_dynamic_settings()
	except Exception as e:
		logger.warning(f"Could not read existing config for merge: {e}")
		current = {}
	
	validated = new_settings.model_dump(exclude_none=True)
	
	percentage_fields = [
		"RISK_PER_TRADE",
		"MAX_RISK_CAP",
		"MIN_CONFIDENCE",
		"TRAILING_STOP_ACTIVATION",
		"TRAILING_STOP_DISTANCE",
		"BREAKEVEN_ACTIVATION",
		"ADAPTIVE_RISK_FLOOR",
		"ADAPTIVE_RISK_CEIL",
		"ADAPTIVE_DRAWDOWN_FLOOR",
		"MAX_DRAWDOWN_HALT_PCT",
		"VETO_CRASH_PCT",
		"NO_SL_SIZE_PCT",
		"SMC_OB_STRENGTH",
		"LIQ_CLUSTER_PCT",
	]
	
	for field in percentage_fields:
		if field in validated:
			value = validated[field]
			if value >= 1:
				validated[field] = value / 100.0
	
	if "PARES_ACTIVOS" in validated and isinstance(validated["PARES_ACTIVOS"], list):
		validated["PARES_ACTIVOS"] = [str(p).strip().upper() for p in validated["PARES_ACTIVOS"]]

	merged = {**current, **validated}
	with open(cfg.SETTINGS_PATH, "w", encoding="utf-8") as f:
		json.dump(merged, f, indent=4)

	return {"status": "success", "updated_keys": list(validated.keys())}


@app.delete("/api/notifications")
def clear_all_notifications(_ = Depends(verify_auth)):
	nm.clear_notifications()
	return {"status": "success", "message": "Bandeja de notificaciones limpiada"}