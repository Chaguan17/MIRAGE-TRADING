import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ReTooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// ─── Helpers ──────────────────────────────────────────────────────────────────
const sharpeLabel = (ratio) => {
  const r = parseFloat(ratio);
  if (r >= 2) return { text: "Excelente", color: "#00ffaa" };
  if (r >= 1) return { text: "Bueno", color: "#aa3bff" };
  if (r >= 0) return { text: "Bajo", color: "#f59e0b" };
  return { text: "Negativo", color: "#ff3b69" };
};

// ─── Styles ───────────────────────────────────────────────────────────────────
const STYLES = {
  layout: {
    padding: "0 1.5rem 2.5rem",
    maxWidth: "1200px",
    margin: "0 auto",
    color: "#f8fafc",
    minHeight: "100vh",
    backgroundColor: "#060913",
    fontFamily: "Inter, system-ui, sans-serif",
    boxSizing: "border-box",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "1.5rem 0 1.5rem",
    borderBottom: "1px solid #1e293b",
    marginBottom: "2rem",
    flexWrap: "wrap", // FIX: header se adapta en móvil
    gap: "12px",
  },
  brandSection: { display: "flex", alignItems: "center", gap: "16px" },
  backLink: {
    background: "none",
    border: "1px solid #1e293b",
    color: "#94a3b8",
    fontWeight: "600",
    fontSize: "0.875rem",
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    textDecoration: "none",
    padding: "8px 14px",
    borderRadius: "8px",
    transition: "all 0.2s",
    whiteSpace: "nowrap",
  },
  brandTitle: {
    fontSize: "clamp(1.1rem, 4vw, 1.5rem)", // FIX: responsivo
    fontWeight: "900",
    letterSpacing: "-0.5px",
    margin: 0,
  },
  brandSubtitle: { color: "#aa3bff", fontWeight: "300" },
  chartBadge: {
    fontSize: "0.7rem",
    background: "rgba(170, 59, 255, 0.12)",
    color: "#aa3bff",
    padding: "4px 12px",
    borderRadius: "20px",
    fontWeight: "700",
    border: "1px solid rgba(170, 59, 255, 0.15)",
    whiteSpace: "nowrap",
  },
  kpiGrid: {
    display: "grid",
    // FIX: min(100%, 240px) evita desbordamiento en pantallas muy pequeñas
    gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))",
    gap: "20px",
    marginBottom: "2rem",
  },
  card: {
    background: "#0b1120",
    border: "1px solid #1e293b",
    borderRadius: "16px",
    padding: "1.5rem",
    boxShadow: "0 4px 20px rgba(0, 0, 0, 0.25)",
  },
  // FIX: perfCard estaba referenciado pero NUNCA definido → spread de undefined
  perfCard: {
    padding: "1.25rem 1.5rem",
  },
  kpiLabel: {
    fontSize: "0.72rem",
    color: "#64748b",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    margin: 0,
  },
  kpiValueBox: {
    display: "flex",
    alignItems: "baseline",
    gap: "8px",
    marginTop: "10px",
    flexWrap: "wrap",
  },
  kpiValue: (color) => ({
    fontFamily: "JetBrains Mono, monospace",
    fontSize: "clamp(1.4rem, 4vw, 2rem)", // FIX: responsivo
    fontWeight: "700",
    margin: 0,
    letterSpacing: "-0.5px",
    color: color || "#f8fafc",
  }),
  kpiUnit: { fontSize: "0.85rem", color: "#64748b", fontWeight: "600" },
  kpiSublabel: {
    fontSize: "0.7rem",
    marginTop: "6px",
    fontWeight: "700",
    letterSpacing: "0.3px",
  },
  perfValue: (color, size) => ({
    fontFamily: "JetBrains Mono, monospace",
    fontWeight: "800",
    marginTop: "8px",
    color: color || "#f8fafc",
    fontSize: size || "1.4rem",
  }),
  chartHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "1.5rem",
    flexWrap: "wrap", // FIX: no se desborda en pantallas estrechas
    gap: "12px",
  },
  chartTitle: { fontSize: "0.95rem", fontWeight: "700", margin: 0 },
  tagSelector: { display: "flex", gap: "8px", flexWrap: "wrap" },
  tagBtn: (active) => ({
    padding: "7px 14px",
    borderRadius: "8px",
    fontSize: "0.8rem",
    fontWeight: "700",
    cursor: "pointer",
    border: "1px solid #1e293b",
    background: active ? "#aa3bff" : "#121b2e",
    color: active ? "white" : "#64748b",
    transition: "all 0.2s",
    whiteSpace: "nowrap",
  }),
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
  // Win Rate progress bar
  progressTrack: {
    height: "6px",
    background: "#1e293b",
    borderRadius: "3px",
    marginTop: "12px",
    overflow: "hidden",
  },
  progressFill: (pct) => ({
    height: "100%",
    width: `${Math.min(pct, 100)}%`,
    background:
      pct >= 60
        ? "linear-gradient(90deg, #00c97d, #00ffaa)"
        : pct >= 45
          ? "linear-gradient(90deg, #f59e0b, #fbbf24)"
          : "linear-gradient(90deg, #ff3b69, #ff6b8a)",
    borderRadius: "3px",
    transition: "width 0.6s ease",
  }),
};

// ─── Animations + responsive CSS ─────────────────────────────────────────────
const GlobalAnimations = () => (
  <style>{`
    :root {
      --bg-card: #0b1120;
      --text-muted: #64748b;
      --text-main: #f8fafc;
    }
    *, *::before, *::after { box-sizing: border-box; }
    body {
      margin: 0; padding: 0;
      background-color: #060913;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
    }
    @keyframes spin    { to { transform: rotate(360deg); } }
    @keyframes fadeIn  { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .animate-spin  { animation: spin 1s linear infinite; }
    .animate-fade-in { animation: fadeIn 0.4s ease-out; }
    .spinner {
      width: 40px; height: 40px;
      border: 4px solid rgba(170, 59, 255, 0.1);
      border-top-color: #aa3bff;
      border-radius: 50%;
    }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }

    /* FIX: mainContent era grid de 2 cols con 320px fijo → roto en tablet/móvil */
    .perf-main-grid {
      display: grid;
      grid-template-columns: 300px 1fr;
      gap: 24px;
      margin-top: 24px;
    }
    /* FIX: sidebar pasaba a 1 columna larga en móvil; ahora usa 2 columnas */
    .perf-sidebar {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    @media (max-width: 900px) {
      .perf-main-grid {
        grid-template-columns: 1fr !important;
      }
      .perf-sidebar {
        display: grid !important;
        grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
        gap: 16px;
      }
    }
    @media (max-width: 480px) {
      .perf-sidebar {
        grid-template-columns: 1fr !important;
      }
    }
  `}</style>
);

// ─── Custom Tooltip para los gráficos ────────────────────────────────────────
const CustomBarTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const val = payload[0].value;
  return (
    <div
      style={{
        background: "#0b1120",
        border: "1px solid #1e293b",
        borderRadius: "10px",
        padding: "10px 14px",
        fontSize: "0.8rem",
      }}
    >
      <div style={{ color: "#64748b", marginBottom: "4px" }}>{label}</div>
      <div
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontWeight: "700",
          color: val >= 0 ? "#00ffaa" : "#ff3b69",
        }}
      >
        {val >= 0 ? "+" : ""}
        {val.toFixed(2)} USDT
      </div>
    </div>
  );
};

// ─── Main Component ───────────────────────────────────────────────────────────
export default function PerformanceView() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [chartMode, setViewMode] = useState("daily");

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/performance`)
      .then((res) => {
        if (!res.ok)
          throw new Error(`Error ${res.status}: Falló el servicio analítico.`);
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data)) {
          const cleanData = data
            .filter((t) => t.pair && t.pair !== "UNKNOWN")
            .map((t) => ({ ...t, pnl_usdt: parseFloat(t.pnl_usdt) || 0 }));
          setHistory(cleanData);
        } else {
          throw new Error("Formato de respuesta inválido.");
        }
        setLoading(false);
      })
      .catch((err) => {
        setFetchError(err.message);
        setLoading(false);
      });
  }, []);

  const stats = useMemo(() => {
    if (!Array.isArray(history) || history.length === 0) return null;

    const totalTrades = history.length;
    const wins = history.filter((t) => t.pnl_usdt > 0);
    const losses = history.filter((t) => t.pnl_usdt <= 0);

    const totalProfit = wins.reduce((acc, t) => acc + t.pnl_usdt, 0);
    const totalLoss = Math.abs(losses.reduce((acc, t) => acc + t.pnl_usdt, 0));
    const netPnL = totalProfit - totalLoss;

    // Max drawdown
    let peak = 0,
      currentPnL = 0,
      maxDD = 0;
    history.forEach((t) => {
      currentPnL += t.pnl_usdt;
      if (currentPnL > peak) peak = currentPnL;
      const dd = peak - currentPnL;
      if (dd > maxDD) maxDD = dd;
    });

    // Per-pair PnL
    const pairMap = {};
    history.forEach((t) => {
      pairMap[t.pair] = (pairMap[t.pair] || 0) + t.pnl_usdt;
    });
    const pairData = Object.entries(pairMap)
      .map(([name, pnl]) => ({ name, pnl: parseFloat(pnl.toFixed(2)) }))
      .sort((a, b) => b.pnl - a.pnl);

    // Daily PnL
    const dayMap = {};
    history.forEach((t) => {
      try {
        const d = new Date(t.timestamp);
        if (!isNaN(d.getTime())) {
          const key = d.toISOString().split("T")[0];
          dayMap[key] = (dayMap[key] || 0) + t.pnl_usdt;
        }
      } catch (_) {}
    });
    const dailyData = Object.entries(dayMap)
      .map(([date, pnl]) => ({ date, pnl: parseFloat(pnl.toFixed(2)) }))
      .sort((a, b) => a.date.localeCompare(b.date));

    // Monthly PnL
    const monthMap = {};
    history.forEach((t) => {
      try {
        const d = new Date(t.timestamp);
        if (!isNaN(d.getTime())) {
          const key = d.toISOString().substring(0, 7);
          monthMap[key] = (monthMap[key] || 0) + t.pnl_usdt;
        }
      } catch (_) {}
    });
    const monthlyData = Object.entries(monthMap)
      .map(([month, pnl]) => ({ month, pnl: parseFloat(pnl.toFixed(2)) }))
      .sort((a, b) => a.month.localeCompare(b.month));

    // Sharpe
    const pnls = history.map((t) => t.pnl_usdt);
    const avgPnL = netPnL / totalTrades;
    const variance =
      pnls.map((x) => Math.pow(x - avgPnL, 2)).reduce((a, b) => a + b, 0) /
      totalTrades;
    const stdDev = Math.sqrt(variance);
    const sharpeRatio = stdDev === 0 ? "0.00" : (avgPnL / stdDev).toFixed(2);

    // Best / Worst trade (NUEVA MÉTRICA)
    const bestTrade = Math.max(...pnls).toFixed(2);
    const worstTrade = Math.min(...pnls).toFixed(2);

    // Consecutive wins (NUEVA MÉTRICA)
    let maxConsecWins = 0,
      streak = 0;
    history.forEach((t) => {
      if (t.pnl_usdt > 0) {
        streak++;
        maxConsecWins = Math.max(maxConsecWins, streak);
      } else streak = 0;
    });

    return {
      totalTrades,
      winRate: ((wins.length / totalTrades) * 100).toFixed(1),
      winCount: wins.length,
      lossCount: losses.length,
      profitFactor:
        totalLoss === 0
          ? totalProfit.toFixed(2)
          : (totalProfit / totalLoss).toFixed(2),
      avgWin: wins.length ? (totalProfit / wins.length).toFixed(2) : "0.00",
      avgLoss: losses.length ? (totalLoss / losses.length).toFixed(2) : "0.00",
      netPnL: netPnL.toFixed(2),
      maxDD: maxDD.toFixed(2),
      sharpeRatio,
      bestTrade,
      worstTrade,
      maxConsecWins,
      pairData,
      dailyData,
      monthlyData,
    };
  }, [history]);

  // ── Loading ──
  if (loading)
    return (
      <div style={STYLES.loading}>
        <GlobalAnimations />
        <div className="animate-spin spinner" />
      </div>
    );

  // ── Error / sin datos ──
  if (fetchError || !stats)
    return (
      <div
        style={{ ...STYLES.layout, textAlign: "center", paddingTop: "80px" }}
      >
        <GlobalAnimations />
        <button onClick={() => navigate("/")} style={STYLES.backLink}>
          ← Volver al Terminal
        </button>
        <div
          style={{
            ...STYLES.card,
            maxWidth: "500px",
            margin: "24px auto",
            background: "rgba(255, 59, 105, 0.08)",
            borderColor: "#ff3b69",
          }}
        >
          <h3 style={{ color: "#ff3b69", margin: "0 0 8px" }}>
            Métricas No Disponibles
          </h3>
          <p style={{ color: "#64748b", fontSize: "0.9rem", margin: 0 }}>
            {fetchError ||
              "Se requiere un historial mínimo de transacciones cerradas."}
          </p>
        </div>
      </div>
    );

  const sharpe = sharpeLabel(stats.sharpeRatio);

  return (
    <div style={STYLES.layout} className="animate-fade-in">
      <GlobalAnimations />

      {/* ── Header ── */}
      <header style={STYLES.header}>
        <div style={STYLES.brandSection}>
          <button onClick={() => navigate("/")} style={STYLES.backLink}>
            ← Volver
          </button>
          <h1 style={STYLES.brandTitle}>
            MIRAGE <span style={STYLES.brandSubtitle}>METRICS</span>
          </h1>
        </div>
        <span style={STYLES.chartBadge}>Análisis Histórico Pro</span>
      </header>

      {/* ── KPI Top Row ── */}
      <div style={STYLES.kpiGrid}>
        {/* Net PnL */}
        <div style={STYLES.card}>
          <h4 style={STYLES.kpiLabel}>Net PnL Histórico</h4>
          <div style={STYLES.kpiValueBox}>
            <h2
              style={STYLES.kpiValue(
                parseFloat(stats.netPnL) >= 0 ? "#00ffaa" : "#ff3b69",
              )}
            >
              {parseFloat(stats.netPnL) >= 0 ? "+" : ""}
              {stats.netPnL}
            </h2>
            <span style={STYLES.kpiUnit}>USDT</span>
          </div>
        </div>

        {/* Profit Factor */}
        <div style={STYLES.card}>
          <h4 style={STYLES.kpiLabel}>Profit Factor</h4>
          <div style={STYLES.kpiValueBox}>
            <h2 style={STYLES.kpiValue("#aa3bff")}>{stats.profitFactor}</h2>
            <span style={STYLES.kpiUnit}>RATIO</span>
          </div>
          <p
            style={{
              ...STYLES.kpiSublabel,
              color:
                parseFloat(stats.profitFactor) >= 1.5 ? "#00ffaa" : "#f59e0b",
            }}
          >
            {parseFloat(stats.profitFactor) >= 2
              ? "Sólido"
              : parseFloat(stats.profitFactor) >= 1.5
                ? "Rentable"
                : parseFloat(stats.profitFactor) >= 1
                  ? "Marginal"
                  : "Deficitario"}
          </p>
        </div>

        {/* Max Drawdown */}
        <div style={STYLES.card}>
          <h4 style={STYLES.kpiLabel}>Max Drawdown</h4>
          <div style={STYLES.kpiValueBox}>
            <h2 style={STYLES.kpiValue("#ff3b69")}>-{stats.maxDD}</h2>
            <span style={STYLES.kpiUnit}>USDT</span>
          </div>
        </div>

        {/* Sharpe Ratio — MEJORADO: ahora con etiqueta cualitativa */}
        <div style={STYLES.card}>
          <h4 style={STYLES.kpiLabel}>Sharpe Ratio</h4>
          <div style={STYLES.kpiValueBox}>
            <h2 style={STYLES.kpiValue("#f59e0b")}>{stats.sharpeRatio}</h2>
            <span style={STYLES.kpiUnit}>SCORE</span>
          </div>
          <p style={{ ...STYLES.kpiSublabel, color: sharpe.color }}>
            {sharpe.text}
          </p>
        </div>

        {/* Best / Worst trade — NUEVA */}
        <div style={STYLES.card}>
          <h4 style={STYLES.kpiLabel}>Mejor / Peor Trade</h4>
          <div
            style={{
              marginTop: "10px",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
            }}
          >
            <span
              style={{
                fontFamily: "JetBrains Mono, monospace",
                fontWeight: "700",
                color: "#00ffaa",
                fontSize: "1.1rem",
              }}
            >
              +{stats.bestTrade}{" "}
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "#64748b",
                  fontFamily: "inherit",
                }}
              >
                USDT
              </span>
            </span>
            <span
              style={{
                fontFamily: "JetBrains Mono, monospace",
                fontWeight: "700",
                color: "#ff3b69",
                fontSize: "1.1rem",
              }}
            >
              {stats.worstTrade}{" "}
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "#64748b",
                  fontFamily: "inherit",
                }}
              >
                USDT
              </span>
            </span>
          </div>
        </div>
      </div>

      {/* ── Main Content: Sidebar + Chart ── */}
      {/* FIX: era gridTemplateColumns: "320px 1fr" (fijo) → ahora usa clase CSS responsiva */}
      <div className="perf-main-grid">
        {/* Sidebar de estadísticas */}
        {/* FIX: perfCard nunca estaba definido; marginTop manual reemplazado por gap del grid */}
        <div className="perf-sidebar">
          {/* Win Rate — MEJORADO: con barra de progreso */}
          <div style={{ ...STYLES.card, ...STYLES.perfCard }}>
            <h4 style={STYLES.kpiLabel}>Win Rate</h4>
            <div style={STYLES.perfValue("#00ffaa", "1.5rem")}>
              {stats.winRate}%
            </div>
            <div style={STYLES.progressTrack}>
              <div style={STYLES.progressFill(parseFloat(stats.winRate))} />
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: "6px",
              }}
            >
              <span
                style={{
                  fontSize: "0.7rem",
                  color: "#00ffaa",
                  fontWeight: "700",
                }}
              >
                {stats.winCount}W
              </span>
              <span
                style={{
                  fontSize: "0.7rem",
                  color: "#ff3b69",
                  fontWeight: "700",
                }}
              >
                {stats.lossCount}L
              </span>
            </div>
          </div>

          {/* Avg Win / Loss */}
          <div style={{ ...STYLES.card, ...STYLES.perfCard }}>
            <h4 style={STYLES.kpiLabel}>Avg Win / Avg Loss</h4>
            <div style={{ marginTop: "8px" }}>
              <span
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  color: "#00ffaa",
                  fontWeight: "700",
                  fontSize: "1.1rem",
                }}
              >
                +{stats.avgWin}
              </span>
              <span style={{ color: "#334155", margin: "0 8px" }}>/</span>
              <span
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  color: "#ff3b69",
                  fontWeight: "700",
                  fontSize: "1.1rem",
                }}
              >
                -{stats.avgLoss}
              </span>
              <span
                style={{
                  fontSize: "0.72rem",
                  color: "#64748b",
                  marginLeft: "4px",
                }}
              >
                USDT
              </span>
            </div>
          </div>

          {/* Total Trades */}
          <div style={{ ...STYLES.card, ...STYLES.perfCard }}>
            <h4 style={STYLES.kpiLabel}>Total Trades</h4>
            <div style={STYLES.perfValue(null, "1.5rem")}>
              {stats.totalTrades}
            </div>
          </div>

          {/* Racha máx — NUEVA */}
          <div style={{ ...STYLES.card, ...STYLES.perfCard }}>
            <h4 style={STYLES.kpiLabel}>Racha Ganadora Máx.</h4>
            <div
              style={{
                ...STYLES.perfValue("#f59e0b", "1.5rem"),
                display: "flex",
                alignItems: "baseline",
                gap: "6px",
              }}
            >
              {stats.maxConsecWins}
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "#64748b",
                  fontFamily: "inherit",
                }}
              >
                consecutivas
              </span>
            </div>
          </div>
        </div>

        {/* Gráfico temporal */}
        <div style={STYLES.card}>
          <div style={STYLES.chartHeader}>
            <h3 style={STYLES.chartTitle}>
              Rendimiento por Distribución Temporal
            </h3>
            <div style={STYLES.tagSelector}>
              <button
                style={STYLES.tagBtn(chartMode === "daily")}
                onClick={() => setViewMode("daily")}
              >
                Día
              </button>
              <button
                style={STYLES.tagBtn(chartMode === "monthly")}
                onClick={() => setViewMode("monthly")}
              >
                Mes
              </button>
            </div>
          </div>
          <div style={{ height: "280px", width: "100%" }}>
            <ResponsiveContainer>
              <BarChart
                data={
                  chartMode === "daily" ? stats.dailyData : stats.monthlyData
                }
                margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#1e293b"
                />
                <XAxis
                  dataKey={chartMode === "daily" ? "date" : "month"}
                  tick={{ fill: "#64748b", fontSize: 10, fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                  // Mostrar solo algunos ticks en daily para no saturar
                  interval={chartMode === "daily" ? "preserveStartEnd" : 0}
                />
                <YAxis
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(val) => `$${val}`}
                />
                {/* Línea de referencia en 0 para separar ganancias/pérdidas visualmente */}
                <ReferenceLine y={0} stroke="#334155" strokeWidth={1} />
                <ReTooltip
                  content={<CustomBarTooltip />}
                  cursor={{ fill: "rgba(255,255,255,0.03)" }}
                />
                <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                  {(chartMode === "daily"
                    ? stats.dailyData
                    : stats.monthlyData
                  ).map((entry, i) => (
                    <Cell
                      key={`cell-${i}`}
                      fill={entry.pnl >= 0 ? "#00ffaa" : "#ff3b69"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── PnL por activo ── */}
      <div style={{ ...STYLES.card, marginTop: "24px" }}>
        <div style={STYLES.chartHeader}>
          <h3 style={STYLES.chartTitle}>Net PnL por Activo</h3>
          <span
            style={{
              fontSize: "0.7rem",
              background: "rgba(0,255,170,0.08)",
              color: "#00ffaa",
              padding: "4px 10px",
              borderRadius: "20px",
              fontWeight: "700",
              border: "1px solid rgba(0,255,170,0.15)",
            }}
          >
            {stats.pairData.length} pares
          </span>
        </div>
        <div style={{ height: "260px", width: "100%" }}>
          <ResponsiveContainer>
            <BarChart
              data={stats.pairData}
              margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke="#1e293b"
              />
              <XAxis
                dataKey="name"
                tick={{ fill: "#f8fafc", fontSize: 11, fontWeight: 700 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(val) => `$${val}`}
              />
              <ReferenceLine y={0} stroke="#334155" strokeWidth={1} />
              <ReTooltip
                content={<CustomBarTooltip />}
                cursor={{ fill: "rgba(255,255,255,0.03)" }}
              />
              <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                {stats.pairData.map((entry, i) => (
                  <Cell
                    key={`cell-${i}`}
                    fill={entry.pnl >= 0 ? "#00ffaa" : "#ff3b69"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
