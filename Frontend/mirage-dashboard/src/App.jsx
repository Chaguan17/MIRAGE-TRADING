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

// Paleta de colores Global Premium Dark Mode
const theme = {
  bgApp: "#0f172a", // Slate 900
  bgCard: "#1e293b", // Slate 800
  border: "#334155", // Slate 700
  textMain: "#f8fafc", // Slate 50
  textMuted: "#94a3b8", // Slate 400
  accent: "#3b82f6", // Blue 500
  success: "#10b981", // Emerald 500
  danger: "#f43f5e", // Rose 500
  successBg: "rgba(16, 185, 129, 0.1)",
  dangerBg: "rgba(244, 63, 94, 0.1)",
};

// ==========================================
// VISTA 1: PANEL DE CONFIGURACIÓN (FULL EXPERT)
// ==========================================
function SettingsView() {
  const navigate = useNavigate();

  // Estado inicial con TODAS las variables de config.py
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
    fetch("http://127.0.0.1:8000/api/config")
      .then((res) => res.json())
      .then((data) => setConfig((prev) => ({ ...prev, ...data })))
      .catch((err) => console.log("Error cargando config", err));
  }, []);

  const saveSettings = async () => {
    try {
      await fetch("http://127.0.0.1:8000/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      alert(
        "Configuración guardada. Mirage aplicará los cambios automáticamente.",
      );
      navigate("/");
    } catch (error) {
      alert("Error al guardar la configuración.");
    }
  };

  // Componente interno para no repetir tanto código en los inputs
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
    <div
      style={{
        maxWidth: "1000px",
        margin: "40px auto",
        padding: "0 20px",
        animation: "fadeIn 0.3s",
      }}
    >
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
              fontSize: "14px",
            }}
          >
            Guardar Cambios
          </button>
        </h2>

        {/* === SECCIÓN 1: OPERATIVA BÁSICA === */}
        <h3
          style={{
            color: theme.textMain,
            borderBottom: `1px solid ${theme.border}`,
            paddingBottom: "10px",
            marginTop: "30px",
          }}
        >
          📊 Operativa y Capital
        </h3>
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
            helpText="Ej: 0.02 = 2%"
          />
          <ConfigInput
            label="Confianza Mínima IA"
            objKey="MIN_CONFIDENCE"
            step="0.01"
            helpText="Umbral para entrar al mercado"
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
                fontSize: "14px",
              }}
            >
              <option value="1m">1 Minuto</option>
              <option value="5m">5 Minutos</option>
              <option value="15m">15 Minutos</option>
              <option value="1h">1 Hora</option>
            </select>
          </div>
        </div>

        {/* === SECCIÓN 2: STOPS Y TAKE PROFITS === */}
        <h3
          style={{
            color: theme.textMain,
            borderBottom: `1px solid ${theme.border}`,
            paddingBottom: "10px",
            marginTop: "40px",
          }}
        >
          🛡️ Gestión de Riesgo y Trailing
        </h3>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "20px",
          }}
        >
          <ConfigInput
            label="Multiplicador Stop Loss (ATR)"
            objKey="ATR_MULTIPLIER"
            step="0.1"
          />
          <ConfigInput
            label="Multiplicador Take Profit (ATR)"
            objKey="TP_MULTIPLIER"
            step="0.1"
          />
          <ConfigInput
            label="Activación Trailing Stop (%)"
            objKey="TRAILING_STOP_ACTIVATION"
            step="0.1"
            helpText="Beneficio flotante para activarlo"
          />
          <ConfigInput
            label="Distancia Trailing Stop (%)"
            objKey="TRAILING_STOP_DISTANCE"
            step="0.1"
          />
        </div>

        {/* === SECCIÓN 3: GESTIÓN DE RACHAS === */}
        <h3
          style={{
            color: theme.textMain,
            borderBottom: `1px solid ${theme.border}`,
            paddingBottom: "10px",
            marginTop: "40px",
          }}
        >
          📉 Gestión de Rachas y Cooldown
        </h3>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "20px",
          }}
        >
          <ConfigInput
            label="Max. Pérdidas Consecutivas"
            objKey="MAX_CONSECUTIVE_LOSSES"
          />
          <ConfigInput
            label="Reducción de Riesgo (Factor)"
            objKey="RISK_REDUCTION_FACTOR"
            step="0.1"
            helpText="Si pierdes, el riesgo se multiplica por esto"
          />
          <ConfigInput
            label="Max. Ganancias Consecutivas"
            objKey="MAX_CONSECUTIVE_WINS"
          />
          <ConfigInput
            label="Aumento de Riesgo (Factor)"
            objKey="RISK_INCREASE_FACTOR"
            step="0.1"
            helpText="Si ganas, el riesgo se multiplica por esto"
          />
          <ConfigInput
            label="Velas de Cooldown post-loss"
            objKey="COOLDOWN_CANDLES"
            helpText="Pausa obligatoria tras racha negativa"
          />
        </div>

        {/* === SECCIÓN 4: ALGORITMOS === */}
        <h3
          style={{
            color: theme.textMain,
            borderBottom: `1px solid ${theme.border}`,
            paddingBottom: "10px",
            marginTop: "40px",
          }}
        >
          🧠 Algoritmos Avanzados (SMC & Wyckoff)
        </h3>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "20px",
          }}
        >
          <ConfigInput
            label="Lookback SMC (Velas)"
            objKey="SMC_LOOKBACK"
            step="5"
          />
          <ConfigInput
            label="Fuerza de Order Blocks (SMC)"
            objKey="SMC_OB_STRENGTH"
            step="0.1"
          />
          <ConfigInput
            label="Lookback Wyckoff (Velas)"
            objKey="WYCKOFF_LOOKBACK"
            step="10"
          />
        </div>
      </div>
    </div>
  );
}

// ==========================================
// VISTA 2: DASHBOARD PRINCIPAL
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

  const filteredHistory = useMemo(() => {
    if (!data || !data.ultimas_operaciones) return [];
    let processed = [...data.ultimas_operaciones].reverse();
    if (historyFilter !== "ALL") {
      processed = processed.filter((op) => op.pair === historyFilter);
    }
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
          fontFamily: "system-ui",
        }}
      >
        <h2>Iniciando Terminal Mirage...</h2>
      </div>
    );

  return (
    <div
      style={{ maxWidth: "1400px", margin: "0 auto", animation: "fadeIn 0.3s" }}
    >
      {/* HEADER */}
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
              boxShadow: "0 4px 15px rgba(59, 130, 246, 0.4)",
            }}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1
            style={{
              margin: 0,
              fontSize: "28px",
              fontWeight: "800",
              letterSpacing: "-0.5px",
            }}
          >
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

      {/* METRICS CARDS */}
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
            boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
          }}
        >
          <h4
            style={{
              margin: "0 0 10px 0",
              color: theme.textMuted,
              fontSize: "14px",
              textTransform: "uppercase",
              letterSpacing: "1px",
            }}
          >
            Net PnL Global
          </h4>
          <h2
            style={{
              margin: 0,
              fontSize: "36px",
              fontWeight: "800",
              color: data.pnl_total >= 0 ? theme.success : theme.danger,
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            {data.pnl_total > 0 ? "+" : ""}
            {data.pnl_total}
            <span
              style={{
                fontSize: "14px",
                padding: "4px 8px",
                borderRadius: "20px",
                backgroundColor:
                  data.pnl_total >= 0 ? theme.successBg : theme.dangerBg,
                color: data.pnl_total >= 0 ? theme.success : theme.danger,
              }}
            >
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
            boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
          }}
        >
          <h4
            style={{
              margin: "0 0 10px 0",
              color: theme.textMuted,
              fontSize: "14px",
              textTransform: "uppercase",
              letterSpacing: "1px",
            }}
          >
            Win Rate Global
          </h4>
          <h2
            style={{
              margin: 0,
              fontSize: "36px",
              fontWeight: "800",
              color: theme.textMain,
            }}
          >
            {data.win_rate}%
          </h2>
          <div
            style={{
              marginTop: "10px",
              height: "4px",
              background: theme.border,
              borderRadius: "2px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${data.win_rate}%`,
                background: `linear-gradient(90deg, ${theme.accent}, ${theme.success})`,
              }}
            ></div>
          </div>
        </div>

        <div
          style={{
            backgroundColor: theme.bgCard,
            border: `1px solid ${theme.border}`,
            padding: "25px",
            borderRadius: "16px",
            boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
          }}
        >
          <h4
            style={{
              margin: "0 0 10px 0",
              color: theme.textMuted,
              fontSize: "14px",
              textTransform: "uppercase",
              letterSpacing: "1px",
            }}
          >
            Total Trades
          </h4>
          <h2
            style={{
              margin: 0,
              fontSize: "36px",
              fontWeight: "800",
              color: theme.textMain,
            }}
          >
            {data.total_operaciones}
          </h2>
        </div>
      </div>

      {/* CHART SECTION */}
      <div
        style={{
          backgroundColor: theme.bgCard,
          border: `1px solid ${theme.border}`,
          padding: "25px",
          borderRadius: "16px",
          marginBottom: "30px",
          boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
        }}
      >
        <h3 style={{ margin: "0 0 20px 0", color: theme.textMain }}>
          Evolución del Capital
        </h3>
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
                tickFormatter={(val) => `$${val}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: theme.bgApp,
                  border: `1px solid ${theme.border}`,
                  borderRadius: "8px",
                  color: theme.textMain,
                }}
                itemStyle={{ color: theme.accent, fontWeight: "bold" }}
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

      {/* TABLES SECTION */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "30px" }}>
        {/* Active Trades */}
        <div
          style={{
            backgroundColor: theme.bgCard,
            border: `1px solid ${theme.border}`,
            padding: "25px",
            borderRadius: "16px",
            boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
          }}
        >
          <h3
            style={{
              margin: "0 0 20px 0",
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            <span
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                backgroundColor:
                  data.operaciones_activas?.length > 0
                    ? theme.accent
                    : theme.textMuted,
                display: "inline-block",
                boxShadow:
                  data.operaciones_activas?.length > 0
                    ? `0 0 10px ${theme.accent}`
                    : "none",
              }}
            ></span>
            Operaciones Activas
          </h3>

          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                textAlign: "left",
                borderCollapse: "collapse",
                fontSize: "15px",
              }}
            >
              <thead>
                <tr
                  style={{
                    color: theme.textMuted,
                    borderBottom: `2px solid ${theme.border}`,
                  }}
                >
                  <th style={{ padding: "12px 10px", fontWeight: "500" }}>
                    Par
                  </th>
                  <th style={{ padding: "12px 10px", fontWeight: "500" }}>
                    Lado
                  </th>
                  <th style={{ padding: "12px 10px", fontWeight: "500" }}>
                    Entrada
                  </th>
                  <th
                    style={{
                      padding: "12px 10px",
                      fontWeight: "500",
                      color: theme.accent,
                    }}
                  >
                    Precio Actual
                  </th>
                  <th style={{ padding: "12px 10px", fontWeight: "500" }}>
                    Take Profit
                  </th>
                  <th style={{ padding: "12px 10px", fontWeight: "500" }}>
                    Stop Loss
                  </th>
                  <th
                    style={{
                      padding: "12px 10px",
                      fontWeight: "500",
                      textAlign: "right",
                    }}
                  >
                    PnL Flotante
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.operaciones_activas &&
                data.operaciones_activas.length > 0 ? (
                  data.operaciones_activas.map((op, idx) => (
                    <tr
                      key={idx}
                      style={{ borderBottom: `1px solid ${theme.border}` }}
                    >
                      <td style={{ padding: "16px 10px", fontWeight: "bold" }}>
                        {op.pair}
                      </td>
                      <td style={{ padding: "16px 10px" }}>
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
                      <td
                        style={{
                          padding: "16px 10px",
                          fontFamily: "monospace",
                        }}
                      >
                        {op.entry}
                      </td>
                      <td
                        style={{
                          padding: "16px 10px",
                          fontFamily: "monospace",
                          fontWeight: "bold",
                          color: theme.textMain,
                        }}
                      >
                        {livePrices[op.pair]
                          ? livePrices[op.pair].toLocaleString("en-US", {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })
                          : op.current_price}
                      </td>
                      <td
                        style={{
                          padding: "16px 10px",
                          fontFamily: "monospace",
                          color: theme.success,
                        }}
                      >
                        {op.tp}
                      </td>
                      <td
                        style={{
                          padding: "16px 10px",
                          fontFamily: "monospace",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                        }}
                      >
                        <span
                          style={{
                            color: op.is_trailing ? "#f59e0b" : theme.danger,
                            fontWeight: op.is_trailing ? "bold" : "normal",
                          }}
                        >
                          {op.sl === 0 ? "SIN SL" : op.sl}
                        </span>
                        {op.is_trailing && (
                          <span
                            style={{
                              padding: "2px 6px",
                              fontSize: "10px",
                              backgroundColor: "rgba(245, 158, 11, 0.1)",
                              color: "#f59e0b",
                              borderRadius: "4px",
                              border: "1px solid #f59e0b",
                            }}
                          >
                            TRAILING 🔺
                          </span>
                        )}
                      </td>
                      <td
                        style={{
                          padding: "16px 10px",
                          fontFamily: "monospace",
                          textAlign: "right",
                          fontWeight: "bold",
                          fontSize: "16px",
                          color:
                            op.current_pnl > 0 ? theme.success : theme.danger,
                        }}
                      >
                        {op.current_pnl > 0 ? "+" : ""}
                        {op.current_pnl}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td
                      colSpan="7"
                      style={{
                        padding: "30px 10px",
                        textAlign: "center",
                        color: theme.textMuted,
                      }}
                    >
                      Buscando oportunidades en el mercado...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Trade History */}
        <div
          style={{
            backgroundColor: theme.bgCard,
            border: `1px solid ${theme.border}`,
            padding: "25px",
            borderRadius: "16px",
            boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "20px",
              flexWrap: "wrap",
              gap: "15px",
            }}
          >
            <h3 style={{ margin: 0, color: theme.textMain }}>
              Historial de Transacciones
            </h3>
            <div style={{ display: "flex", gap: "10px" }}>
              <select
                value={historyFilter}
                onChange={(e) => setHistoryFilter(e.target.value)}
                style={{
                  backgroundColor: theme.bgApp,
                  color: theme.textMain,
                  border: `1px solid ${theme.border}`,
                  padding: "8px 15px",
                  borderRadius: "6px",
                  fontSize: "14px",
                  outline: "none",
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
                  padding: "8px 15px",
                  borderRadius: "6px",
                  fontSize: "14px",
                  outline: "none",
                }}
              >
                <option value={20}>Últimas 20</option>
                <option value={50}>Últimas 50</option>
                <option value={100}>Últimas 100</option>
              </select>
            </div>
          </div>

          <div style={{ overflowX: "auto" }}>
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
                  <th style={{ padding: "12px 10px", fontWeight: "500" }}>
                    Fecha y Hora
                  </th>
                  <th style={{ padding: "12px 10px", fontWeight: "500" }}>
                    Par
                  </th>
                  <th style={{ padding: "12px 10px", fontWeight: "500" }}>
                    Lado
                  </th>
                  <th style={{ padding: "12px 10px", fontWeight: "500" }}>
                    Entrada
                  </th>
                  <th style={{ padding: "12px 10px", fontWeight: "500" }}>
                    Salida
                  </th>
                  <th
                    style={{
                      padding: "12px 10px",
                      fontWeight: "500",
                      textAlign: "right",
                    }}
                  >
                    Resultado
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.length > 0 ? (
                  filteredHistory.map((op, idx) => (
                    <tr
                      key={idx}
                      style={{ borderBottom: `1px solid ${theme.border}` }}
                    >
                      <td
                        style={{ padding: "14px 10px", color: theme.textMuted }}
                      >
                        {op.timestamp}
                      </td>
                      <td style={{ padding: "14px 10px", fontWeight: "bold" }}>
                        {op.pair || "BTCUSDT"}
                      </td>
                      <td style={{ padding: "14px 10px" }}>
                        <span
                          style={{
                            color:
                              op.action === "LONG"
                                ? theme.success
                                : theme.danger,
                            fontWeight: "bold",
                          }}
                        >
                          {op.action}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: "14px 10px",
                          fontFamily: "monospace",
                        }}
                      >
                        {op.entry_price}
                      </td>
                      <td
                        style={{
                          padding: "14px 10px",
                          fontFamily: "monospace",
                        }}
                      >
                        {op.close_price}
                      </td>
                      <td
                        style={{
                          padding: "14px 10px",
                          fontFamily: "monospace",
                          textAlign: "right",
                          fontWeight: "bold",
                          color:
                            op.pnl_usdt >= 0 ? theme.success : theme.danger,
                        }}
                      >
                        {op.pnl_usdt >= 0 ? "+" : ""}
                        {op.pnl_usdt}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td
                      colSpan="6"
                      style={{
                        padding: "30px 10px",
                        textAlign: "center",
                        color: theme.textMuted,
                      }}
                    >
                      No hay operaciones registradas.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// COMPONENTE RAÍZ (GESTIÓN DE ESTADO Y RUTAS)
// ==========================================
export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [livePrices, setLivePrices] = useState({});
  const [historyFilter, setHistoryFilter] = useState("ALL");
  const [historyLimit, setHistoryLimit] = useState(20);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const response = await fetch("http://127.0.0.1:8000/api/dashboard");
        const result = await response.json();
        if (result.error) setError(result.error);
        else {
          setData(result);
          setError(null);
        }
      } catch (err) {
        setError("Desconectado del motor de Mirage.");
      }
    };
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const wsUrl =
      "wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/ethusdt@ticker/bnbusdt@ticker";
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.data && msg.data.s && msg.data.c) {
        setLivePrices((prev) => ({
          ...prev,
          [msg.data.s]: parseFloat(msg.data.c),
        }));
      }
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
          fontFamily: "system-ui",
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
        fontFamily: '"Inter", system-ui, sans-serif',
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
