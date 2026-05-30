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

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_WS_URL =
  import.meta.env.VITE_API_WS_URL || "wss://stream.binance.com:9443/stream";

const chartColors = {
  accent: "#aa3bff",
  textMain: "#F8FAFC",
  textMuted: "#64748b",
};

// ─── CSS-in-JS styles ──────────────────────────────────────────────────────────
const STYLES = {
  layout: {
    width: "100%",
    maxWidth: "1800px",
    minHeight: "100vh",           // FIX: era maxHeight, cortaba el contenido
    margin: "0 auto",
    padding: "0 1.5rem 2rem",    // FIX: no tenía padding; el contenido iba de borde a borde
    color: "#f8fafc",
    backgroundColor: "#060913",
    fontFamily: "Inter, system-ui, sans-serif",
    boxSizing: "border-box",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "1.5rem 0",
    borderBottom: "1px solid #1e293b",
    marginBottom: "2rem",
    flexWrap: "wrap",             // FIX: en móvil, los botones se van a la siguiente línea
    gap: "1rem",
  },
  brandSection: { display: "flex", alignItems: "center", gap: "1rem" },
  logoBox: {
    background: "linear-gradient(135deg, #aa3bff, #6366f1)",
    padding: "10px",
    borderRadius: "12px",
    display: "flex",
    alignItems: "center",
    flexShrink: 0,
    boxShadow: "0 4px 15px rgba(170, 59, 255, 0.12)",
  },
  brandTitle: {
    fontSize: "clamp(1.1rem, 4vw, 1.5rem)",  // FIX: responsivo
    fontWeight: "900",
    letterSpacing: "-1px",
    margin: 0,
  },
  brandSubtitle: { color: "#aa3bff", fontWeight: "300" },
  statusIndicator: {
    fontSize: "0.75rem",
    color: "#64748b",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginTop: "4px",
    fontWeight: "500",
  },
  statusDot: {
    width: "8px",
    height: "8px",
    background: "#00ffaa",
    borderRadius: "50%",
    boxShadow: "0 0 10px #00ffaa",
    flexShrink: 0,
  },
  headerButtons: {
    display: "flex",
    gap: "12px",
    flexWrap: "wrap",             // FIX: en pantallas muy estrechas los botones se apilan
  },
  btnSecondary: {
    background: "#0b1120",
    border: "1px solid #1e293b",
    color: "#f8fafc",
    padding: "10px 20px",
    borderRadius: "8px",
    fontSize: "0.875rem",
    fontWeight: "600",
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    transition: "all 0.2s",
    whiteSpace: "nowrap",
  },
  kpiGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", // FIX: min() evita desbordamiento en móvil
    gap: "1.5rem",
    marginBottom: "2rem",
  },
  card: {
    background: "#0b1120",
    border: "1px solid #1e293b",
    borderRadius: "16px",
    padding: "1.5rem",
    transition: "transform 0.2s",
  },
  kpiLabel: {
    fontSize: "0.7rem",
    color: "#64748b",
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: "1px",
    margin: 0,
  },
  kpiValueBox: {
    display: "flex",
    alignItems: "baseline",
    gap: "8px",
    marginTop: "8px",
    flexWrap: "wrap",
  },
  kpiValue: (color) => ({
    fontFamily: "JetBrains Mono, monospace",
    fontSize: "clamp(1.5rem, 5vw, 2.25rem)",  // FIX: responsivo
    fontWeight: "700",
    margin: 0,
    color: color || "#f8fafc",
  }),
  kpiUnit: { fontSize: "0.8rem", color: "#64748b", fontWeight: "600" },
  pairStatsRow: {
    display: "flex",
    gap: "12px",
    overflowX: "auto",
    paddingBottom: "12px",
    marginBottom: "2rem",
    scrollbarWidth: "thin",
    scrollbarColor: "#1e293b transparent",
  },
  pairStatCard: {
    minWidth: "170px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 16px",
    background: "#0b1120",
    border: "1px solid #1e293b",
    borderRadius: "12px",
    flexShrink: 0,
    gap: "12px",
  },
  pairStatName: {
    fontWeight: "700",
    fontFamily: "JetBrains Mono, monospace",
    fontSize: "0.85rem",
    color: "#f8fafc",
  },
  pairStatDivider: { width: "1px", height: "20px", backgroundColor: "#1e293b", flexShrink: 0 },
  pairStatDetails: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
  },
  pairStatWr: (isHigh) => ({
    fontFamily: "JetBrains Mono, monospace",
    fontWeight: "700",
    fontSize: "0.875rem",
    display: "flex",
    alignItems: "center",
    gap: "6px",
    color: isHigh ? "#00ffaa" : "#ff3b69",
  }),
  dot: (active) => ({
    width: "6px",
    height: "6px",
    borderRadius: "50%",
    background: active ? "#00ffaa" : "#64748b",
    boxShadow: active ? "0 0 6px #00ffaa" : "none",
    flexShrink: 0,
  }),
  pairStatCount: {
    fontSize: "0.65rem",
    color: "#64748b",
    textTransform: "uppercase",
    fontWeight: "600",
    marginTop: "2px",
  },
  chartHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "1.5rem",
    flexWrap: "wrap",
    gap: "8px",
  },
  chartTitle: { fontSize: "1rem", fontWeight: "800", margin: 0 },
  chartBadge: {
    fontSize: "0.65rem",
    background: "rgba(170, 59, 255, 0.12)",
    color: "#aa3bff",
    padding: "4px 10px",
    borderRadius: "20px",
    fontWeight: "800",
    textTransform: "uppercase",
    whiteSpace: "nowrap",
  },
  tableSectionTitle: {
    fontSize: "1rem",
    fontWeight: "800",
    marginBottom: "20px",
    marginTop: 0,
  },
  tableResponsive: {
    overflowX: "auto",         // FIX: scroll horizontal en móvil
    width: "100%",
    WebkitOverflowScrolling: "touch",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    textAlign: "left",
    minWidth: "600px",          // FIX: tableLayout: "fixed" sin anchos definidos causaba columnas aplastadas
  },
  th: (align = "left", color) => ({
    padding: "12px",
    fontSize: "0.75rem",
    color: color || "#64748b",
    textTransform: "uppercase",
    fontWeight: "700",
    borderBottom: "1px solid #1e293b",
    textAlign: align,
    whiteSpace: "nowrap",
  }),
  td: (align = "left", weight = "400", color = "#f8fafc", mono = false) => ({
    padding: "16px 12px",
    fontSize: "0.85rem",
    borderBottom: "1px solid rgba(255,255,255,0.02)",
    textAlign: align,
    fontWeight: weight,
    color: color,
    fontFamily: mono ? "JetBrains Mono, monospace" : "inherit",
    whiteSpace: "nowrap",
  }),
  badge: (type) => ({
    padding: "4px 8px",
    borderRadius: "4px",
    fontSize: "0.7rem",
    fontWeight: "800",
    display: "inline-block",
    background:
      type === "LONG" ? "rgba(0, 255, 170, 0.1)" : "rgba(255, 59, 105, 0.1)",
    color: type === "LONG" ? "#00ffaa" : "#ff3b69",
  }),
  specialBadge: (color) => ({
    fontSize: "10px",
    background: color,
    color: "#000",
    padding: "2px 4px",
    borderRadius: "3px",
    marginLeft: "5px",
    fontWeight: "900",
  }),
  filterRow: {
    display: "flex",
    gap: "12px",
    flexWrap: "wrap",
  },
  select: {
    background: "#121b2e",
    color: "#f8fafc",
    border: "1px solid #1e293b",
    borderRadius: "8px",
    padding: "0 10px",
    fontSize: "0.85rem",
    outline: "none",
    height: "36px",
    cursor: "pointer",
  },
  loading: {
    height: "100vh",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#060913",
    color: "#f8fafc",
    padding: "1rem",
  },
};

// FIX: CSS variables definidas (var(--bg-card) y var(--text-muted) se usaban en Tooltip pero nunca se declaraban)
const GlobalAnimations = () => (
  <style>{`
    :root {
      --bg-card: #0b1120;
      --text-muted: #64748b;
      --text-main: #f8fafc;
    }
    *, *::before, *::after { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      padding: 0;
      background-color: #060913;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .animate-spin { animation: spin 1s linear infinite; }
    .animate-fade-in { animation: fadeIn 0.4s ease-out; }
    .spinner {
      width: 40px; height: 40px;
      border: 4px solid rgba(170, 59, 255, 0.1);
      border-top-color: #aa3bff;
      border-radius: 50%;
    }
    /* Scrollbar estilizado */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #334155; }

    /* Responsive: en pantallas <= 640px, ocultar columnas menos críticas de las tablas */
    @media (max-width: 640px) {
      .col-hide-sm { display: none !important; }
    }
  `}</style>
);

// ─── Dashboard ─────────────────────────────────────────────────────────────────
function Dashboard({
  data,
  livePrices,
  historyFilter,
  setHistoryFilter,
  historyLimit,
  setHistoryLimit,
}) {
  const navigate = useNavigate();

  // Calcula el PnL total en vivo (cerrado + flotante con precios actualizados)
  const liveTotalPnL = useMemo(() => {
    if (!data) return 0;
    const closedPnl =
      data.pnl_total -
      (data.operaciones_activas?.reduce((acc, op) => acc + (op.current_pnl || 0), 0) || 0);

    const currentLive = data.operaciones_activas?.reduce((acc, op) => {
      const price = livePrices[op.pair];
      if (price) {
        return (
          acc +
          (op.position_value || 0) *
            (price / op.entry - 1) *
            (op.type === "LONG" ? 1 : -1)
        );
      }
      return acc + (op.current_pnl || 0);
    }, 0) || 0;

    return parseFloat((closedPnl + currentLive).toFixed(2));
  }, [data, livePrices]);

  // FIX: lista de pares dinámica extraída del historial real (no hardcodeada)
  const availablePairs = useMemo(() => {
    if (!data?.ultimas_operaciones) return [];
    const pairs = new Set(
      data.ultimas_operaciones
        .map((op) => op.pair)
        .filter((p) => p && p !== "UNKNOWN")
    );
    return Array.from(pairs).sort();
  }, [data]);

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
      if (!op.pair || op.pair === "UNKNOWN") return;
      if (!stats[op.pair]) stats[op.pair] = { wins: 0, total: 0 };
      stats[op.pair].total += 1;
      if (op.pnl_usdt > 0) stats[op.pair].wins += 1;
    });
    return Object.entries(stats)
      .map(([pair, s]) => ({
        pair,
        wr: s.total > 0 ? ((s.wins / s.total) * 100).toFixed(1) : "0.0",
        total: s.total,
      }))
      .sort((a, b) => b.total - a.total);
  }, [data]);

  if (!data)
    return (
      <div style={STYLES.loading}>
        <GlobalAnimations />
        <div className="animate-spin spinner" />
      </div>
    );

  return (
    <div style={STYLES.layout} className="animate-fade-in">
      <GlobalAnimations />

      {/* ── Header ── */}
      <header style={STYLES.header}>
        <div style={STYLES.brandSection}>
          <div style={STYLES.logoBox}>
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div>
            <h1 style={STYLES.brandTitle}>
              MIRAGE <span style={STYLES.brandSubtitle}>TERMINAL</span>
            </h1>
            <span style={STYLES.statusIndicator}>
              <div style={STYLES.statusDot} /> Sistemas En Línea
            </span>
          </div>
        </div>

        <div style={STYLES.headerButtons}>
          <button onClick={() => navigate("/performance")} style={STYLES.btnSecondary}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            Métricas
          </button>
          <button onClick={() => navigate("/settings")} style={STYLES.btnSecondary}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            Ajustes
          </button>
        </div>
      </header>

      {/* ── KPI Cards ── */}
      <div style={STYLES.kpiGrid}>
        {[
          {
            label: "Net PnL Global (Live)",
            value: `${liveTotalPnL >= 0 ? "+" : ""}${liveTotalPnL.toFixed(2)}`,
            unit: "USDT",
            color: liveTotalPnL >= 0 ? "#00ffaa" : "#ff3b69",
          },
          {
            label: "Balance de Cuenta",
            value: (data.balance_actual || 0).toLocaleString(undefined, { minimumFractionDigits: 2 }),
            unit: "USDT",
            color: "#00ffaa",
          },
          {
            label: "Riesgo & Palanca",
            value: `${((data.config?.RISK_PER_TRADE || 0) * 100).toFixed(1)}% / ${data.config?.LEVERAGE || 0}x`,
            unit: "Config",
            color: "#aa3bff",
          },
          {
            label: "Win Rate Algorítmico",
            value: `${data.win_rate}`,
            unit: "%",
            color: "#aa3bff",
          },
          {
            label: "Volumen de Operaciones",
            value: data.total_operaciones,
            unit: "Trades",
            color: "#f8fafc",
          },
        ].map((kpi, idx) => (
          <div key={idx} style={STYLES.card}>
            <h4 style={STYLES.kpiLabel}>{kpi.label}</h4>
            <div style={STYLES.kpiValueBox}>
              <h2 style={STYLES.kpiValue(kpi.color)}>{kpi.value}</h2>
              <span style={STYLES.kpiUnit}>{kpi.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* ── Pair Stats Row ── */}
      {pairStats.length > 0 && (
        <div style={STYLES.pairStatsRow}>
          {pairStats.map((s) => (
            <div key={s.pair} style={STYLES.pairStatCard}>
              <span style={STYLES.pairStatName}>{s.pair}</span>
              <div style={STYLES.pairStatDivider} />
              <div style={STYLES.pairStatDetails}>
                <span style={STYLES.pairStatWr(parseFloat(s.wr) >= 50)}>
                  <div style={STYLES.dot(data.pares_activos?.includes(s.pair))} />
                  {s.wr}%
                </span>
                <span style={STYLES.pairStatCount}>{s.total} Trades</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Equity Chart ── */}
      <div style={{ ...STYLES.card, marginBottom: "1.5rem" }}>
        <div style={STYLES.chartHeader}>
          <h3 style={STYLES.chartTitle}>Curva de Equidad Algorítmica</h3>
          <span style={STYLES.chartBadge}>En tiempo real</span>
        </div>
        <div style={{ height: "280px", width: "100%" }}>
          <ResponsiveContainer>
            <AreaChart
              data={data.chart_data}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorPnL" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColors.accent} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={chartColors.accent} stopOpacity={0.01} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="#1e293b" />
              <XAxis dataKey="time" hide />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 11, fontWeight: 600 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(val) => `$${val}`}
              />
              {/* FIX: var(--bg-card) y var(--text-muted) ahora están definidas en :root */}
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--bg-card)",
                  border: "1px solid #1e293b",
                  borderRadius: "12px",
                  boxShadow: "0 10px 25px rgba(0,0,0,0.4)",
                }}
                itemStyle={{ color: "#fff", fontWeight: "bold" }}
                labelStyle={{ color: "var(--text-muted)", fontSize: "11px" }}
              />
              <Area
                type="monotone"
                dataKey="pnl"
                stroke={chartColors.accent}
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#colorPnL)"
                activeDot={{ r: 5, strokeWidth: 0, fill: "white" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Active Operations Table ── */}
      <div style={{ ...STYLES.card, marginBottom: "1.5rem" }}>
        <h3 style={STYLES.tableSectionTitle}>Operaciones Activas en Mercado</h3>
        <div style={STYLES.tableResponsive}>
          <table style={STYLES.table}>
            <thead>
              <tr>
                <th style={STYLES.th()}>Activo</th>
                <th style={STYLES.th("center")}>Dirección</th>
                <th style={{ ...STYLES.th("right"), ...{ className: "col-hide-sm" } }}>Monto</th>
                <th style={STYLES.th("right")}>Precio Entrada</th>
                <th style={STYLES.th("right", "#aa3bff")}>Marca Actual</th>
                <th style={{ ...STYLES.th("right", "#00ffaa") }} className="col-hide-sm">Take Profit</th>
                <th style={{ ...STYLES.th("right", "#ff3b69") }} className="col-hide-sm">Stop Loss</th>
                <th style={STYLES.th("right")}>ROI</th>
                <th style={STYLES.th("right")}>PnL Flotante</th>
              </tr>
            </thead>
            <tbody>
              {!data.operaciones_activas?.length ? (
                <tr>
                  <td colSpan="9" style={STYLES.td("center", "400", "#64748b")}>
                    No hay posiciones abiertas en este momento.
                  </td>
                </tr>
              ) : (
                data.operaciones_activas.map((op, idx) => {
                  const live = livePrices[op.pair] || op.current_price;
                  const livePnl = parseFloat(
                    (
                      (live / op.entry - 1) *
                      (op.type === "LONG" ? 1 : -1) *
                      (op.position_value || 0)
                    ).toFixed(2)
                  );
                  // FIX: roiPct era string comparado con número; ahora se parsea correctamente
                  const roiPct = parseFloat(
                    (
                      (live / op.entry - 1) *
                      (op.type === "LONG" ? 1 : -1) *
                      100
                    ).toFixed(2)
                  );

                  return (
                    <tr key={idx}>
                      <td style={STYLES.td("left", "700")}>{op.pair}</td>
                      <td style={STYLES.td("center")}>
                        <span style={STYLES.badge(op.type)}>{op.type}</span>
                      </td>
                      <td style={STYLES.td("right", "400", "#f8fafc", true)} className="col-hide-sm">
                        {op.position_value ? `$${op.position_value.toFixed(2)}` : "—"}
                      </td>
                      <td style={STYLES.td("right", "400", "#f8fafc", true)}>
                        {op.entry.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td style={STYLES.td("right", "700", "#aa3bff", true)}>
                        {live
                          ? live.toLocaleString(undefined, { minimumFractionDigits: 2 })
                          : "—"}
                      </td>
                      <td style={STYLES.td("right", "400", "#00ffaa", true)} className="col-hide-sm">
                        {op.tp}
                      </td>
                      <td style={STYLES.td("right", "400", "#f8fafc", true)} className="col-hide-sm">
                        <span style={{ color: op.is_trailing ? "#f59e0b" : "#ff3b69" }}>
                          {op.sl === 0 ? "SIN SL" : op.sl}
                        </span>
                        {op.is_breakeven && (
                          <span style={STYLES.specialBadge("#00ffaa")}>BE</span>
                        )}
                        {op.is_trailing && (
                          <span style={STYLES.specialBadge("#f59e0b")}>TR</span>
                        )}
                      </td>
                      <td style={STYLES.td("right", "700", roiPct >= 0 ? "#00ffaa" : "#ff3b69", true)}>
                        {/* FIX: antes roiPct era string → comparación siempre true */}
                        {roiPct > 0 ? "+" : ""}{roiPct}%
                      </td>
                      <td style={STYLES.td("right", "700", livePnl >= 0 ? "#00ffaa" : "#ff3b69", true)}>
                        {livePnl > 0 ? "+" : ""}{livePnl} USDT
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── History Table ── */}
      <div style={STYLES.card}>
        <div style={STYLES.chartHeader}>
          <h3 style={STYLES.chartTitle}>Historial de Ejecución</h3>
          <div style={STYLES.filterRow}>
            {/* FIX: pares dinámicos extraídos del historial real, no hardcodeados */}
            <select
              style={{ ...STYLES.select, width: "160px" }}
              value={historyFilter}
              onChange={(e) => setHistoryFilter(e.target.value)}
            >
              <option value="ALL">Todos los Pares</option>
              {availablePairs.map((pair) => (
                <option key={pair} value={pair}>
                  {pair.replace("USDT", "/USDT")}
                </option>
              ))}
            </select>
            <select
              style={{ ...STYLES.select, width: "130px" }}
              value={historyLimit}
              onChange={(e) => setHistoryLimit(Number(e.target.value))}
            >
              <option value={20}>Últimos 20</option>
              <option value={50}>Últimos 50</option>
              <option value={100}>Últimos 100</option>
            </select>
          </div>
        </div>
        <div style={STYLES.tableResponsive}>
          <table style={STYLES.table}>
            <thead>
              <tr>
                <th style={STYLES.th()}>Fecha / Hora</th>
                <th style={STYLES.th()}>Activo</th>
                <th style={STYLES.th()}>Lado</th>
                <th style={STYLES.th("right")}>Entrada</th>
                <th style={{ ...STYLES.th("right") }} className="col-hide-sm">Salida</th>
                <th style={STYLES.th("right")}>Resultado PnL</th>
              </tr>
            </thead>
            <tbody>
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan="6" style={STYLES.td("center", "400", "#64748b")}>
                    No hay operaciones en el historial.
                  </td>
                </tr>
              ) : (
                filteredHistory.map((op, i) => (
                  <tr key={i}>
                    <td style={STYLES.td("left", "400", "#64748b")}>{op.timestamp}</td>
                    <td style={STYLES.td("left", "700")}>{op.pair}</td>
                    <td style={STYLES.td()}>
                      <span style={STYLES.badge(op.action)}>{op.action}</span>
                    </td>
                    <td style={STYLES.td("right", "400", "#f8fafc", true)}>{op.entry_price}</td>
                    <td style={STYLES.td("right", "400", "#f8fafc", true)} className="col-hide-sm">
                      {op.close_price}
                    </td>
                    <td
                      style={STYLES.td(
                        "right",
                        "700",
                        op.pnl_usdt >= 0 ? "#00ffaa" : "#ff3b69",
                        true
                      )}
                    >
                      {op.pnl_usdt >= 0 ? "+" : ""}{op.pnl_usdt} USDT
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── App root ──────────────────────────────────────────────────────────────────
export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [livePrices, setLivePrices] = useState({});
  const [historyFilter, setHistoryFilter] = useState("ALL");
  const [historyLimit, setHistoryLimit] = useState(20);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectDelayRef = useRef(1000);
  const unmountedRef = useRef(false);  // FIX: evita reconexión después del unmount

  const connectWebSocket = (pairs = []) => {
    if (unmountedRef.current) return;  // FIX: no reconectar si el componente fue desmontado
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const streams =
      pairs.length > 0
        ? pairs.map((p) => `${p.toLowerCase()}@ticker`).join("/")
        : "btcusdt@ticker/ethusdt@ticker/bnbusdt@ticker";

    const ws = new WebSocket(`${API_WS_URL}?streams=${streams}`);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.data?.s)
          setLivePrices((p) => ({ ...p, [msg.data.s]: parseFloat(msg.data.c) }));
      } catch (_) {}
    };

    ws.onopen = () => {
      reconnectDelayRef.current = 1000;
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;  // FIX: no reconectar tras cleanup
      const delay = Math.min(reconnectDelayRef.current, 30000);
      reconnectDelayRef.current = delay * 2;
      reconnectTimeoutRef.current = setTimeout(() => connectWebSocket(pairs), delay);
    };

    wsRef.current = ws;
  };

  // Polling al backend cada 3s
  useEffect(() => {
    const fetchD = () => {
      fetch(`${API_BASE_URL}/api/dashboard`)
        .then((res) => res.json())
        .then((d) => {
          if (d.error) setError(d.error);
          else { setData(d); setError(null); }
        })
        .catch(() =>
          setError("Conexión perdida con el motor Mirage. Verifique el servidor backend.")
        );
    };
    fetchD();
    const timer = setInterval(fetchD, 3000);
    return () => clearInterval(timer);
  }, []);

  // Reconectar WebSocket cuando cambien los pares activos
  useEffect(() => {
    if (data?.pares_activos) {
      if (wsRef.current) wsRef.current.close();
      connectWebSocket(data.pares_activos);
    } else {
      connectWebSocket();
    }
    return () => {
      unmountedRef.current = true;
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [data?.pares_activos]);

  if (error)
    return (
      <div style={STYLES.loading}>
        <GlobalAnimations />
        <div
          style={{
            ...STYLES.card,
            background: "rgba(255, 59, 105, 0.08)",
            borderColor: "#ff3b69",
            textAlign: "center",
            padding: "40px",
            maxWidth: "460px",
            width: "100%",
          }}
        >
          <h2 style={{ marginBottom: "12px", fontSize: "1.4rem", color: "#ff3b69" }}>
            ⚠️ Error Crítico de Sistema
          </h2>
          <p style={{ color: "#f8fafc", fontSize: "0.95rem", margin: 0 }}>{error}</p>
        </div>
      </div>
    );

  return (
    <div style={{ backgroundColor: "#060913", minHeight: "100vh" }}>
      <GlobalAnimations />
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