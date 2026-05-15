import { useState, useEffect, useMemo } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// Variables de entorno restauradas al 100%
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_WS_URL =
  import.meta.env.VITE_API_WS_URL || "wss://stream.binance.com:9443/stream";

const theme = {
  bgApp: "#0f172a",
  bgCard: "#1e293b",
  border: "#334155",
  textMain: "#f8fafc",
  textMuted: "#94a3b8",
  accent: "#3b82f6",
  success: "#10b981",
  danger: "#f43f5e",
  successBg: "rgba(16, 185, 129, 0.1)",
  dangerBg: "rgba(244, 63, 94, 0.1)",
};

// ==========================================
// VISTA 1: PANEL DE CONFIGURACIÓN (FULL EXPERT)
// ==========================================
function SettingsView() {
  const navigate = useNavigate();
  const [config, setConfig] = useState({
    PAPER_BALANCE: 1000.0,
    RISK_PER_TRADE: 0.02,
    TIMEFRAME: "1m",
    LEVERAGE: 10,
    MIN_CONFIDENCE: 0.65,
    ATR_MULTIPLIER: 2.0,
    TP_MULTIPLIER: 4.0,
    TRAILING_STOP_ACTIVATION: 0.5,
    TRAILING_STOP_DISTANCE: 0.3,
    MAX_CONSECUTIVE_LOSSES: 3,
    RISK_REDUCTION_FACTOR: 0.5,
    MAX_CONSECUTIVE_WINS: 3,
    RISK_INCREASE_FACTOR: 1.25,
    COOLDOWN_CANDLES: 3,
    SMC_LOOKBACK: 20,
    SMC_OB_STRENGTH: 0.3,
    WYCKOFF_LOOKBACK: 50,
  });

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/config`)
      .then((res) => res.json())
      .then((data) => setConfig((prev) => ({ ...prev, ...data })))
      .catch((err) => console.log("Error cargando config", err));
  }, []);

  const saveSettings = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      alert("Configuración guardada correctamente.");
      navigate("/");
    } catch (error) {
      alert("Error al guardar la configuración.");
    }
  };

  const ConfigInput = ({
    label,
    objKey,
    type = "number",
    step = "1",
    helpText,
  }) => (
    <div>
      <label
        style={{
          display: "block",
          color: theme.textMuted,
          marginBottom: "4px",
          fontWeight: "500",
          fontSize: "13px",
        }}
      >
        {label}
      </label>
      <input
        type={type}
        step={step}
        value={config[objKey]}
        onChange={(e) =>
          setConfig({
            ...config,
            [objKey]:
              type === "number" ? parseFloat(e.target.value) : e.target.value,
          })
        }
        style={{
          width: "100%",
          padding: "10px",
          borderRadius: "8px",
          backgroundColor: theme.bgApp,
          color: theme.textMain,
          border: `1px solid ${theme.border}`,
          fontSize: "14px",
        }}
      />
      {helpText && (
        <span
          style={{
            fontSize: "11px",
            color: theme.accent,
            display: "block",
            marginTop: "4px",
          }}
        >
          {helpText}
        </span>
      )}
    </div>
  );

  return (
    <div style={{ maxWidth: "1000px", margin: "40px auto", padding: "0 20px" }}>
      <button
        onClick={() => navigate("/")}
        style={{
          background: "none",
          border: "none",
          color: theme.accent,
          cursor: "pointer",
          marginBottom: "20px",
          fontSize: "16px",
          fontWeight: "bold",
        }}
      >
        ← Volver al Terminal
      </button>

      <div
        style={{
          backgroundColor: theme.bgCard,
          padding: "30px",
          borderRadius: "16px",
          border: `1px solid ${theme.border}`,
          boxShadow: "0 4px 20px rgba(0,0,0,0.2)",
        }}
      >
        <h2
          style={{
            marginTop: 0,
            marginBottom: "30px",
            color: theme.textMain,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          Configuración del Motor
          <button
            onClick={saveSettings}
            style={{
              padding: "10px 20px",
              borderRadius: "8px",
              backgroundColor: theme.success,
              color: "white",
              fontWeight: "bold",
              border: "none",
              cursor: "pointer",
            }}
          >
            Guardar Cambios
          </button>
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "20px",
          }}
        >
          <ConfigInput
            label="Balance Simulado (USDT)"
            objKey="PAPER_BALANCE"
            step="100"
          />
          <ConfigInput label="Apalancamiento (x)" objKey="LEVERAGE" />
          <ConfigInput
            label="Riesgo por Trade (%)"
            objKey="RISK_PER_TRADE"
            step="0.01"
          />
          <ConfigInput
            label="Confianza Mínima IA"
            objKey="MIN_CONFIDENCE"
            step="0.01"
          />
          <div>
            <label
              style={{
                display: "block",
                color: theme.textMuted,
                marginBottom: "4px",
                fontWeight: "500",
                fontSize: "13px",
              }}
            >
              Timeframe
            </label>
            <select
              value={config.TIMEFRAME}
              onChange={(e) =>
                setConfig({ ...config, TIMEFRAME: e.target.value })
              }
              style={{
                width: "100%",
                padding: "10px",
                borderRadius: "8px",
                backgroundColor: theme.bgApp,
                color: theme.textMain,
                border: `1px solid ${theme.border}`,
              }}
            >
              <option value="1m">1 Minuto</option>
              <option value="5m">5 Minutos</option>
              <option value="15m">15 Minutos</option>
              <option value="1h">1 Hora</option>
            </select>
          </div>
          <ConfigInput
            label="ATR Multiplier (SL)"
            objKey="ATR_MULTIPLIER"
            step="0.1"
          />
          <ConfigInput
            label="TP Multiplier"
            objKey="TP_MULTIPLIER"
            step="0.1"
          />
          <ConfigInput
            label="Trailing Activation (%)"
            objKey="TRAILING_STOP_ACTIVATION"
            step="0.1"
          />
          <ConfigInput
            label="Trailing Distance (%)"
            objKey="TRAILING_STOP_DISTANCE"
            step="0.1"
          />
          <ConfigInput label="Max. Losses" objKey="MAX_CONSECUTIVE_LOSSES" />
          <ConfigInput
            label="Risk Reduction Factor"
            objKey="RISK_REDUCTION_FACTOR"
            step="0.1"
          />
          <ConfigInput label="Max. Wins" objKey="MAX_CONSECUTIVE_WINS" />
          <ConfigInput
            label="Risk Increase Factor"
            objKey="RISK_INCREASE_FACTOR"
            step="0.1"
          />
          <ConfigInput label="Cooldown Candles" objKey="COOLDOWN_CANDLES" />
          <ConfigInput label="SMC Lookback" objKey="SMC_LOOKBACK" />
          <ConfigInput
            label="SMC OB Strength"
            objKey="SMC_OB_STRENGTH"
            step="0.1"
          />
          <ConfigInput label="Wyckoff Lookback" objKey="WYCKOFF_LOOKBACK" />
        </div>
      </div>
    </div>
  );
}

// ==========================================
// VISTA 2: DASHBOARD PRINCIPAL (TODO RESTAURADO)
// ==========================================
function Dashboard({
  data,
  livePrices,
  historyFilter,
  setHistoryFilter,
  historyLimit,
  setHistoryLimit,
}) {
  const navigate = useNavigate();

  // Cálculo de PnL Live para las tarjetas superiores
  const liveTotalPnL = useMemo(() => {
    if (!data) return 0;
    let closedPnl =
      data.pnl_total -
      (data.operaciones_activas?.reduce((acc, op) => acc + op.current_pnl, 0) ||
        0);
    let currentLive = 0;
    data.operaciones_activas?.forEach((op) => {
      const price = livePrices[op.pair];
      if (price) {
        const diff = price / op.entry - 1;
        const side = op.type === "LONG" ? 1 : -1;
        const posValue = op.position_value || 200;
        currentLive += posValue * diff * side;
      } else {
        currentLive += op.current_pnl;
      }
    });
    return (closedPnl + currentLive).toFixed(2);
  }, [data, livePrices]);

  const filteredHistory = useMemo(() => {
    if (!data || !data.ultimas_operaciones) return [];
    let processed = [...data.ultimas_operaciones].reverse();
    if (historyFilter !== "ALL")
      processed = processed.filter((op) => op.pair === historyFilter);
    return processed.slice(0, historyLimit);
  }, [data, historyFilter, historyLimit]);

  if (!data)
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: theme.bgApp,
          color: theme.accent,
        }}
      >
        <h2>Cargando Mirage Terminal...</h2>
      </div>
    );

  return (
    <div
      style={{ maxWidth: "1400px", margin: "0 auto", animation: "fadeIn 0.3s" }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "30px",
          borderBottom: `1px solid ${theme.border}`,
          paddingBottom: "20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "15px" }}>
          <div
            style={{
              background: `linear-gradient(135deg, ${theme.accent}, #8b5cf6)`,
              padding: "10px",
              borderRadius: "12px",
            }}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
            >
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 style={{ margin: 0, fontSize: "28px", fontWeight: "800" }}>
            MIRAGE{" "}
            <span style={{ fontWeight: "300", color: theme.textMuted }}>
              TERMINAL
            </span>
          </h1>
        </div>
        <button
          onClick={() => navigate("/settings")}
          style={{
            backgroundColor: theme.bgCard,
            color: theme.textMain,
            border: `1px solid ${theme.border}`,
            padding: "10px 20px",
            borderRadius: "8px",
            cursor: "pointer",
            fontWeight: "bold",
          }}
        >
          ⚙️ Ajustes
        </button>
      </header>

      {/* METRICAS */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "20px",
          marginBottom: "30px",
        }}
      >
        <div
          style={{
            backgroundColor: theme.bgCard,
            border: `1px solid ${theme.border}`,
            padding: "25px",
            borderRadius: "16px",
          }}
        >
          <h4
            style={{
              margin: "0 0 10px 0",
              color: theme.textMuted,
              fontSize: "12px",
              textTransform: "uppercase",
            }}
          >
            Net PnL Global (Live)
          </h4>
          <h2
            style={{
              margin: 0,
              fontSize: "36px",
              color: liveTotalPnL >= 0 ? theme.success : theme.danger,
            }}
          >
            {liveTotalPnL > 0 ? "+" : ""}
            {liveTotalPnL}{" "}
            <span style={{ fontSize: "14px", color: theme.textMuted }}>
              USDT
            </span>
          </h2>
        </div>
        <div
          style={{
            backgroundColor: theme.bgCard,
            border: `1px solid ${theme.border}`,
            padding: "25px",
            borderRadius: "16px",
          }}
        >
          <h4
            style={{
              margin: "0 0 10px 0",
              color: theme.textMuted,
              fontSize: "12px",
              textTransform: "uppercase",
            }}
          >
            Win Rate
          </h4>
          <h2 style={{ margin: 0, fontSize: "36px" }}>{data.win_rate}%</h2>
        </div>
        <div
          style={{
            backgroundColor: theme.bgCard,
            border: `1px solid ${theme.border}`,
            padding: "25px",
            borderRadius: "16px",
          }}
        >
          <h4
            style={{
              margin: "0 0 10px 0",
              color: theme.textMuted,
              fontSize: "12px",
              textTransform: "uppercase",
            }}
          >
            Total Trades
          </h4>
          <h2 style={{ margin: 0, fontSize: "36px" }}>
            {data.total_operaciones}
          </h2>
        </div>
      </div>

      {/* GRAFICA */}
      <div
        style={{
          backgroundColor: theme.bgCard,
          border: `1px solid ${theme.border}`,
          padding: "25px",
          borderRadius: "16px",
          marginBottom: "30px",
        }}
      >
        <h3 style={{ margin: "0 0 20px 0" }}>Evolución del Capital</h3>
        <div style={{ height: "350px", width: "100%" }}>
          <ResponsiveContainer>
            <AreaChart data={data.chart_data}>
              <defs>
                <linearGradient id="colorPnL" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor={theme.accent}
                    stopOpacity={0.8}
                  />
                  <stop offset="95%" stopColor={theme.accent} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke={theme.border}
              />
              <XAxis dataKey="time" hide />
              <YAxis
                tick={{ fill: theme.textMuted, fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: theme.bgApp,
                  border: `1px solid ${theme.border}`,
                }}
              />
              <Area
                type="monotone"
                dataKey="pnl"
                stroke={theme.accent}
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorPnL)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* TABLA ACTIVAS (COLUMNAS RESTAURADAS) */}
      <div
        style={{
          backgroundColor: theme.bgCard,
          border: `1px solid ${theme.border}`,
          padding: "25px",
          borderRadius: "16px",
          marginBottom: "30px",
        }}
      >
        <h3 style={{ margin: "0 0 20px 0" }}>Operaciones Activas</h3>
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              textAlign: "left",
              borderCollapse: "collapse",
            }}
          >
            <thead>
              <tr
                style={{
                  color: theme.textMuted,
                  borderBottom: `2px solid ${theme.border}`,
                }}
              >
                <th style={{ padding: "12px 10px" }}>Par</th>
                <th>Lado</th>
                <th>Entrada</th>
                <th style={{ color: theme.accent }}>Precio Actual</th>
                <th style={{ color: theme.success }}>Take Profit</th>
                <th style={{ color: theme.danger }}>Stop Loss</th>
                <th style={{ textAlign: "right" }}>PnL Flotante</th>
              </tr>
            </thead>
            <tbody>
              {data.operaciones_activas?.map((op, idx) => {
                const live = livePrices[op.pair] || op.current_price;
                const livePnl = (
                  (live / op.entry - 1) *
                  (op.type === "LONG" ? 1 : -1) *
                  (op.position_value || 200)
                ).toFixed(2);
                return (
                  <tr
                    key={idx}
                    style={{ borderBottom: `1px solid ${theme.border}` }}
                  >
                    <td style={{ padding: "16px 10px", fontWeight: "bold" }}>
                      {op.pair}
                    </td>
                    <td>
                      <span
                        style={{
                          padding: "4px 10px",
                          borderRadius: "6px",
                          fontSize: "12px",
                          fontWeight: "bold",
                          backgroundColor:
                            op.type === "LONG"
                              ? theme.successBg
                              : theme.dangerBg,
                          color:
                            op.type === "LONG" ? theme.success : theme.danger,
                        }}
                      >
                        {op.type}
                      </span>
                    </td>
                    <td style={{ fontFamily: "monospace" }}>{op.entry}</td>
                    <td
                      style={{
                        fontFamily: "monospace",
                        fontWeight: "bold",
                        color: theme.textMain,
                      }}
                    >
                      {live.toLocaleString()}
                    </td>
                    <td
                      style={{ fontFamily: "monospace", color: theme.success }}
                    >
                      {op.tp}
                    </td>
                    <td style={{ fontFamily: "monospace" }}>
                      <span
                        style={{
                          color: op.is_trailing ? "#f59e0b" : theme.danger,
                        }}
                      >
                        {op.sl === 0 ? "SIN SL" : op.sl}
                      </span>
                      {op.is_trailing && (
                        <span
                          style={{
                            marginLeft: "8px",
                            fontSize: "10px",
                            color: "#f59e0b",
                          }}
                        >
                          TRAILING 🔺
                        </span>
                      )}
                    </td>
                    <td
                      style={{
                        textAlign: "right",
                        fontWeight: "bold",
                        color: livePnl >= 0 ? theme.success : theme.danger,
                      }}
                    >
                      {livePnl > 0 ? "+" : ""}
                      {livePnl}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* HISTORIAL */}
      <div
        style={{
          backgroundColor: theme.bgCard,
          border: `1px solid ${theme.border}`,
          padding: "25px",
          borderRadius: "16px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: "20px",
          }}
        >
          <h3 style={{ margin: 0 }}>Historial de Transacciones</h3>
          <div style={{ display: "flex", gap: "10px" }}>
            <select
              value={historyFilter}
              onChange={(e) => setHistoryFilter(e.target.value)}
              style={{
                backgroundColor: theme.bgApp,
                color: theme.textMain,
                border: `1px solid ${theme.border}`,
                padding: "8px",
                borderRadius: "6px",
              }}
            >
              <option value="ALL">Todos los Pares</option>
              <option value="BTCUSDT">BTC/USDT</option>
              <option value="ETHUSDT">ETH/USDT</option>
              <option value="BNBUSDT">BNB/USDT</option>
            </select>
            <select
              value={historyLimit}
              onChange={(e) => setHistoryLimit(Number(e.target.value))}
              style={{
                backgroundColor: theme.bgApp,
                color: theme.textMain,
                border: `1px solid ${theme.border}`,
                padding: "8px",
                borderRadius: "6px",
              }}
            >
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
        <table
          style={{
            width: "100%",
            textAlign: "left",
            borderCollapse: "collapse",
            fontSize: "14px",
          }}
        >
          <thead>
            <tr
              style={{
                color: theme.textMuted,
                borderBottom: `2px solid ${theme.border}`,
              }}
            >
              <th style={{ padding: "12px 10px" }}>Fecha</th>
              <th>Par</th>
              <th>Lado</th>
              <th>Entrada</th>
              <th>Salida</th>
              <th style={{ textAlign: "right" }}>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {filteredHistory.map((op, i) => (
              <tr key={i} style={{ borderBottom: `1px solid ${theme.border}` }}>
                <td style={{ padding: "14px 10px", color: theme.textMuted }}>
                  {op.timestamp}
                </td>
                <td style={{ fontWeight: "bold" }}>{op.pair}</td>
                <td
                  style={{
                    color: op.action === "LONG" ? theme.success : theme.danger,
                    fontWeight: "bold",
                  }}
                >
                  {op.action}
                </td>
                <td style={{ fontFamily: "monospace" }}>{op.entry_price}</td>
                <td style={{ fontFamily: "monospace" }}>{op.close_price}</td>
                <td
                  style={{
                    textAlign: "right",
                    fontWeight: "bold",
                    color: op.pnl_usdt >= 0 ? theme.success : theme.danger,
                  }}
                >
                  {op.pnl_usdt >= 0 ? "+" : ""}
                  {op.pnl_usdt}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ==========================================
// APP: GESTIÓN DE RUTAS Y DATOS
// ==========================================
export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [livePrices, setLivePrices] = useState({});
  const [historyFilter, setHistoryFilter] = useState("ALL");
  const [historyLimit, setHistoryLimit] = useState(20);

  useEffect(() => {
    const fetchD = () => {
      fetch(`${API_BASE_URL}/api/dashboard`)
        .then((res) => res.json())
        .then((d) => {
          if (d.error) setError(d.error);
          else {
            setData(d);
            setError(null);
          }
        })
        .catch(() => setError("Desconectado del motor de Mirage."));
    };
    fetchD();
    const timer = setInterval(fetchD, 3000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const ws = new WebSocket(
      `${API_WS_URL}?streams=btcusdt@ticker/ethusdt@ticker/bnbusdt@ticker`,
    );
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.data?.s)
        setLivePrices((p) => ({ ...p, [msg.data.s]: parseFloat(msg.data.c) }));
    };
    return () => ws.close();
  }, []);

  if (error)
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: theme.bgApp,
          color: theme.danger,
        }}
      >
        <div
          style={{
            background: theme.dangerBg,
            padding: "20px",
            border: `1px solid ${theme.danger}`,
            borderRadius: "12px",
          }}
        >
          <h2>⚠️ Error de Conexión</h2>
          <p>{error}</p>
        </div>
      </div>
    );

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: theme.bgApp,
        color: theme.textMain,
        padding: "30px 20px",
        fontFamily: '"Inter", sans-serif',
      }}
    >
      <Routes>
        <Route
          path="/"
          element={
            <Dashboard
              data={data}
              livePrices={livePrices}
              historyFilter={historyFilter}
              setHistoryFilter={setHistoryFilter}
              historyLimit={historyLimit}
              setHistoryLimit={setHistoryLimit}
            />
          }
        />
        <Route path="/settings" element={<SettingsView />} />
      </Routes>
    </div>
  );
}
