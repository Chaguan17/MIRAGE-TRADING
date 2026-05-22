import React, { useState, useEffect, useMemo, useRef } from "react";
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
import PerformanceView from "./PerformanceView";
import SettingsView from "./SettingsView";
import "./index.css"; // Importamos los estilos globales
import "./App.css"; // Estilos específicos del componente App

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_WS_URL =
  import.meta.env.VITE_API_WS_URL || "wss://stream.binance.com:9443/stream";

const chartColors = {
  accent: "#3B82F6",
  textMain: "#F8FAFC",
  textMuted: "#94A3B8",
};

function Dashboard({
  data,
  livePrices,
  historyFilter,
  setHistoryFilter,
  historyLimit,
  setHistoryLimit,
}) {
  const navigate = useNavigate();

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
        currentLive +=
          (op.position_value || 0) *
          (price / op.entry - 1) *
          (op.type === "LONG" ? 1 : -1);
      } else {
        currentLive += op.current_pnl;
      }
    });
    return parseFloat((closedPnl + currentLive).toFixed(2));
  }, [data, livePrices]);

  const filteredHistory = useMemo(() => {
    if (!data?.ultimas_operaciones) return [];
    let processed = [...data.ultimas_operaciones].reverse();
    if (historyFilter !== "ALL")
      processed = processed.filter((op) => op.pair === historyFilter);
    return processed.slice(0, historyLimit);
  }, [data, historyFilter, historyLimit]);

  const pairStats = useMemo(() => {
    if (!data?.ultimas_operaciones) return [];
    const stats = {};
    data.ultimas_operaciones.forEach((op) => {
      // Sinergia: Ignoramos pares desconocidos o errores de registro
      if (!op.pair || op.pair === "UNKNOWN") return;
      
      if (!stats[op.pair]) stats[op.pair] = { wins: 0, total: 0 };
      stats[op.pair].total += 1;
      if (op.pnl_usdt > 0) stats[op.pair].wins += 1;
    });
    return Object.entries(stats)
      .map(([pair, s]) => ({
        pair,
        wr: s.total > 0 ? ((s.wins / s.total) * 100).toFixed(1) : 0,
        total: s.total,
      }))
      .sort((a, b) => b.total - a.total);
  }, [data]);

  if (!data)
    return (
      <div className="loading-container">
        <div className="animate-spin spinner" />
      </div>
    );

  return (
    <div className="dashboard-layout animate-fade-in">
      <header className="header-container">
        <div className="brand-section">
          <div className="brand-logo-box">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
          </div>
          <div>
            <h1 className="brand-title">
              MIRAGE <span className="brand-subtitle">TERMINAL</span>
            </h1>
            <span className="status-indicator">
              <div className="status-dot"></div>{" "}
              Sistemas En Línea
            </span>
          </div>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button onClick={() => navigate("/performance")} className="btn-secondary">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>{" "}
            Métricas
          </button>
          <button onClick={() => navigate("/settings")} className="btn-secondary">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>{" "}
            Ajustes
          </button>
        </div>
      </header>

      <div className="kpi-grid">
        {[
          {
            label: "Net PnL Global (Live)",
            value: `${liveTotalPnL >= 0 ? "+" : ""}${liveTotalPnL.toFixed(2)}`,
            unit: "USDT",
            color: liveTotalPnL >= 0 ? "var(--success)" : "var(--danger)",
          },
          {
            label: "Win Rate Algorítmico",
            value: `${data.win_rate}`,
            unit: "%",
            color: "var(--accent)",
          },
          {
            label: "Volumen de Operaciones",
            value: data.total_operaciones,
            unit: "Trades",
            color: "var(--text-main)",
          },
        ].map((kpi, idx) => (
          <div key={idx} className="card" style={{ marginBottom: 0 }}>
            <h4 className="kpi-card-label">{kpi.label}</h4>
            <div className="kpi-card-value-box">
              <h2 className="kpi-card-value" style={{ color: kpi.color }}>
                {kpi.value}
              </h2>
              <span className="kpi-card-unit">{kpi.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {pairStats.length > 0 && (
        <div className="pair-stats-row">
          {pairStats.map((s) => (
            <div key={s.pair} className="card pair-stat-card">
              <span className="pair-stat-name">{s.pair}</span>
              <div className="pair-stat-divider"></div>
              <div className="pair-stat-details">
                <span
                  className={`pair-stat-wr ${
                    s.wr >= 50 ? "text-success" : "text-danger"
                  }`}
                >
                  <span className={`dot-indicator ${
                    data.pares_activos?.includes(s.pair) 
                      ? 'dot-operating' 
                      : 'dot-stopped'
                  }`}></span>
                  {s.wr}%
                </span>
                <span className="pair-stat-count">
                  {s.total} Trades
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <div className="chart-header">
          <h3 className="chart-title">Curva de Equidad Algorítmica</h3>
          <span className="chart-badge">En tiempo real</span>
        </div>
        <div style={{ height: "250px", width: "100%" }}>
          <ResponsiveContainer>
            <AreaChart
              data={data.chart_data}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorPnL" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor={chartColors.accent}
                    stopOpacity={0.6}
                  />
                  <stop
                    offset="95%"
                    stopColor={chartColors.accent}
                    stopOpacity={0.05}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="4 4"
                vertical={false}
                stroke="var(--border)"
              />
              <XAxis dataKey="time" hide />
              <YAxis
                tick={{ fill: "var(--text-muted)", fontSize: 11, fontWeight: 500 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(val) => `$${val}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--bg-app)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                }}
                itemStyle={{ color: "#fff", fontWeight: "bold" }}
                labelStyle={{ color: "var(--text-muted)" }}
              />
              <Area
                type="monotone"
                dataKey="pnl"
                stroke={chartColors.accent}
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorPnL)"
                activeDot={{ r: 6, strokeWidth: 0, fill: chartColors.textMain }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card" style={{ overflowX: "auto" }}>
        <h3 className="table-section-title">Operaciones Activas en Mercado</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ textAlign: "center" }}>Activo</th>
              <th style={{ textAlign: "center" }}>Dirección</th>
              <th style={{ textAlign: "center" }}>Monto (USDT)</th>
              <th style={{ textAlign: "center" }}>Precio Entrada</th>
              <th style={{ textAlign: "center", color: "var(--accent)" }}>Marca Actual</th>
              <th style={{ textAlign: "center", color: "var(--success)" }}>Take Profit</th>
              <th style={{ textAlign: "center", color: "var(--danger)" }}>Stop Loss</th>
              <th style={{ textAlign: "center" }}>ROI %</th>
              <th style={{ textAlign: "center" }}>PnL Flotante</th>
            </tr>
          </thead>
          <tbody>
            {data.operaciones_activas?.length === 0 ? (
              <tr>
                <td colSpan="9" className="table-empty-row">
                  No hay posiciones abiertas en este momento.
                </td>
              </tr>
            ) : (
              data.operaciones_activas?.map((op, idx) => {
                const live = livePrices[op.pair] || op.current_price;
                const livePnl = parseFloat(
                  (
                    (live / op.entry - 1) *
                    (op.type === "LONG" ? 1 : -1) *
                    (op.position_value || 0)
                  ).toFixed(2),
                );
                const roiPct = (
                  (live / op.entry - 1) *
                  (op.type === "LONG" ? 1 : -1) *
                  100
                ).toFixed(2);
                return (
                  <tr key={idx}>
                    <td style={{ fontWeight: "bold", textAlign: "center" }}>{op.pair}</td>
                    <td style={{ textAlign: "center" }}>
                      <span
                        className={`badge-direction ${
                          op.type === "LONG" ? "badge-long" : "badge-short"
                        }`}
                      >
                        {op.type}
                      </span>
                    </td>
                    <td className="mono-text text-center">
                      {op.position_value ? `${op.position_value.toFixed(2)}` : "0.00"}
                    </td>
                    <td className="mono-text text-center">{op.entry}</td>
                    <td className="mono-text-bold text-center">
                      {live?.toLocaleString()}
                    </td>
                    <td className="mono-text text-success text-center">
                      {op.tp}
                    </td>
                    <td className="mono-text text-center">
                      <span
                        className={
                          op.is_trailing ? "text-warning" : "text-danger"
                        }
                      >
                        {op.sl === 0 ? "SIN SL" : op.sl}
                      </span>
                      {op.is_breakeven && <span className="badge-safe">BE SAFE</span>}
                      {op.is_trailing && <span className="badge-trailing">TRAILING</span>}
                    </td>
                    <td
                      className={`roi-cell text-center ${
                        roiPct >= 0 ? "text-success" : "text-danger"
                      }`}
                    >
                      {roiPct > 0 ? "+" : ""}
                      {roiPct}%
                    </td>
                    <td
                      className={`pnl-cell text-center ${
                        livePnl >= 0 ? "text-success" : "text-danger"
                      }`}
                    >
                      {livePnl > 0 ? "+" : ""}
                      {livePnl} USDT
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ overflowX: "auto" }}>
        <div className="history-header-row">
          <h3 className="chart-title">
            Historial de Ejecución
          </h3>
          <div className="history-controls">
            <select
              className="select-input"
              value={historyFilter}
              onChange={(e) => setHistoryFilter(e.target.value)}
            >
              <option value="ALL">Todos los Pares</option>
              <option value="BTCUSDT">BTC/USDT</option>
              <option value="ETHUSDT">ETH/USDT</option>
              <option value="BNBUSDT">BNB/USDT</option>
            </select>
            <select
              className="select-input"
              value={historyLimit}
              onChange={(e) => setHistoryLimit(Number(e.target.value))}
            >
              <option value={20}>Últimos 20</option>
              <option value={50}>Últimos 50</option>
              <option value={100}>Últimos 100</option>
            </select>
          </div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Fecha / Hora</th>
              <th>Activo</th>
              <th>Lado</th>
              <th>Precio Entrada</th>
              <th>Precio Salida</th>
              <th style={{ textAlign: "right" }}>Resultado PnL</th>
            </tr>
          </thead>
          <tbody>
            {filteredHistory.map((op, i) => (
              <tr key={i}>
                <td className="history-timestamp">
                  {op.timestamp}
                </td>
                <td style={{ fontWeight: "bold" }}>{op.pair}</td>
                <td
                  className={`mono-text-bold ${
                    op.action === "LONG" ? "text-success" : "text-danger"
                  }`}
                >
                  {op.action}
                </td>
                <td className="mono-text">{op.entry_price}</td>
                <td className="mono-text">{op.close_price}</td>
                <td
                  className={`pnl-cell ${
                    op.pnl_usdt >= 0 ? "text-success" : "text-danger"
                  }`}
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

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [livePrices, setLivePrices] = useState({});
  const [historyFilter, setHistoryFilter] = useState("ALL");
  const [historyLimit, setHistoryLimit] = useState(20);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectDelayRef = useRef(1000);

  const connectWebSocket = (pairs = []) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;
    
    // Sinergia: Creamos los streams dinámicamente basados en la config del backend
    const streams = pairs.length > 0 
      ? pairs.map(p => `${p.toLowerCase()}@ticker`).join('/')
      : "btcusdt@ticker/ethusdt@ticker/bnbusdt@ticker";

    const ws = new WebSocket(`${API_WS_URL}?streams=${streams}`);
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.data?.s)
          setLivePrices((p) => ({
            ...p,
            [msg.data.s]: parseFloat(msg.data.c),
          }));
      } catch (_) {}
    };
    ws.onopen = () => {
      reconnectDelayRef.current = 1000;
    };
    ws.onerror = (e) => console.warn("WebSocket error:", e);
    ws.onclose = () => {
      const delay = Math.min(reconnectDelayRef.current, 30000);
      reconnectDelayRef.current = delay * 2;
      reconnectTimeoutRef.current = setTimeout(() => connectWebSocket(pairs), delay);
    };
    wsRef.current = ws;
  };

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
        .catch(() => setError("Conexión perdida con el motor Mirage."));
    };
    fetchD();
    const timer = setInterval(fetchD, 3000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    // Si el backend nos informa de nuevos pares, reiniciamos el socket para escucharlos
    if (data?.pares_activos) {
      if (wsRef.current) wsRef.current.close();
      connectWebSocket(data.pares_activos);
    } else {
      connectWebSocket();
    }

    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [data?.pares_activos]); // Se dispara cuando cambia la lista de pares en el backend

  if (error)
    return (
      <div className="app-container app-error-wrapper">
        <div className="card error-alert-card">
          <h2 className="text-danger">
            ⚠️ Error Crítico de Conexión
          </h2>
          <p>{error}</p>
        </div>
      </div>
    );

  return (
    <div className="app-container">
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
        <Route path="/performance" element={<PerformanceView />} />
        <Route path="/settings" element={<SettingsView />} />
      </Routes>
    </div>
  );
}
