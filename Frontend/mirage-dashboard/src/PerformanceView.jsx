import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip, ResponsiveContainer, Cell } from "recharts";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function PerformanceView() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [chartMode, setViewMode] = useState("daily"); // "daily" | "monthly"

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/performance`)
      .then(res => {
        if (!res.ok) throw new Error(`Error ${res.status}: No se encontró el endpoint de métricas.`);
        return res.json();
      })
      .then(data => {
        console.log("📊 Datos recibidos del historial:", data);
        if (Array.isArray(data)) {
          // Sinergia: Filtramos UNKNOWN y sanitizamos números
          const cleanData = data
            .filter(t => t.pair && t.pair !== "UNKNOWN")
            .map(t => ({
              ...t,
              pnl_usdt: parseFloat(t.pnl_usdt) || 0
            }));
          setHistory(cleanData);
        } else {
          throw new Error("El servidor no devolvió un formato de historial válido.");
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("❌ Error en fetch:", err);
        setFetchError(err.message);
        setLoading(false);
      });
  }, []);

  const stats = useMemo(() => {
    if (!Array.isArray(history) || history.length === 0) return null;

    const totalTrades = history.length;
    const wins = history.filter(t => (parseFloat(t.pnl_usdt) || 0) > 0);
    const losses = history.filter(t => (parseFloat(t.pnl_usdt) || 0) <= 0);
    
    const totalProfit = wins.reduce((acc, t) => acc + (parseFloat(t.pnl_usdt) || 0), 0);
    const totalLoss = Math.abs(losses.reduce((acc, t) => acc + (parseFloat(t.pnl_usdt) || 0), 0));
    const netPnL = totalProfit - totalLoss;

    // Cálculo de Drawdown Máximo
    let peak = 0;
    let currentPnL = 0;
    let maxDD = 0;
    history.forEach(t => {
      currentPnL += t.pnl_usdt;
      if (currentPnL > peak) peak = currentPnL;
      const dd = peak - currentPnL;
      if (dd > maxDD) maxDD = dd;
    });

    // Agrupación por par
    const pairMap = {};
    history.forEach(t => {
      if (!pairMap[t.pair]) pairMap[t.pair] = 0;
      pairMap[t.pair] += t.pnl_usdt;
    });
    const pairData = Object.entries(pairMap).map(([name, pnl]) => ({ name, pnl }));

    // Agrupación por día para identificar tendencias temporales
    const dayMap = {};
    history.forEach(t => {
      try {
        const d = new Date(t.timestamp);
        if (!isNaN(d.getTime())) {
          const dateKey = d.toISOString().split('T')[0];
          dayMap[dateKey] = (dayMap[dateKey] || 0) + (parseFloat(t.pnl_usdt) || 0);
        }
      } catch (e) {
        console.warn("⚠️ Timestamp inválido encontrado:", t.timestamp);
      }
    });
    const dailyData = Object.entries(dayMap).map(([date, pnl]) => ({ date, pnl })).sort((a, b) => a.date.localeCompare(b.date));

    // Agrupación por mes
    const monthMap = {};
    history.forEach(t => {
      try {
        const d = new Date(t.timestamp);
        if (!isNaN(d.getTime())) {
          const monthKey = d.toISOString().substring(0, 7); // YYYY-MM
          monthMap[monthKey] = (monthMap[monthKey] || 0) + (parseFloat(t.pnl_usdt) || 0);
        }
      } catch (e) {}
    });
    const monthlyData = Object.entries(monthMap).map(([month, pnl]) => ({ month, pnl })).sort((a, b) => a.month.localeCompare(b.month));

    // Cálculo de Sharpe Ratio (Eficiencia del beneficio vs volatilidad del PnL)
    const pnls = history.map(t => parseFloat(t.pnl_usdt) || 0);
    const avgPnL = netPnL / totalTrades;
    const variance = pnls.map(x => Math.pow(x - avgPnL, 2)).reduce((a, b) => a + b, 0) / totalTrades;
    const stdDev = Math.sqrt(variance);
    const sharpeRatio = stdDev === 0 ? 0 : (avgPnL / stdDev).toFixed(2);

    return {
      totalTrades,
      winRate: (wins.length / totalTrades * 100).toFixed(1),
      profitFactor: totalLoss === 0 ? totalProfit.toFixed(2) : (totalProfit / totalLoss).toFixed(2),
      avgWin: wins.length ? (totalProfit / wins.length).toFixed(2) : 0,
      avgLoss: losses.length ? (totalLoss / losses.length).toFixed(2) : 0,
      netPnL: netPnL.toFixed(2),
      maxDD: maxDD.toFixed(2),
      sharpeRatio,
      pairData,
      dailyData,
      monthlyData
    };
  }, [history]);

  if (loading) return <div className="loading-container"><div className="spinner" /></div>;

  if (fetchError || !stats) {
    return (
      <div className="app-container" style={{ textAlign: "center", paddingTop: "100px" }}>
        <button onClick={() => navigate("/")} className="back-link">← Volver al Terminal</button>
        <h2 className="text-danger" style={{ marginTop: "20px" }}>⚠️ Error de Datos</h2>
        <p style={{ color: "var(--text-muted)" }}>{fetchError || "No hay historial suficiente para generar métricas."}</p>
      </div>
    );
  }

  return (
    <div className="dashboard-layout animate-fade-in">
      <header className="header-container">
        <div className="brand-section">
          <button onClick={() => navigate("/")} className="back-link" style={{ marginRight: "15px", fontSize: "20px" }}>
            ←
          </button>
          <h1 className="brand-title">
            MIRAGE <span className="brand-subtitle">METRICS</span>
          </h1>
        </div>
        <span className="chart-badge">Análisis Histórico Pro</span>
      </header>

      <div className="kpi-grid">
        <div className="card" style={{ marginBottom: 0 }}>
          <h4 className="kpi-card-label">NET PNL HISTÓRICO</h4>
          <div className="kpi-card-value-box">
            <h2 className={`kpi-card-value ${stats.netPnL >= 0 ? "text-success" : "text-danger"}`}>
              {stats.netPnL >= 0 ? "+" : ""}{stats.netPnL}
            </h2>
            <span className="kpi-card-unit">USDT</span>
          </div>
        </div>
        <div className="card" style={{ marginBottom: 0 }}>
          <h4 className="kpi-card-label">PROFIT FACTOR</h4>
          <div className="kpi-card-value-box">
            <h2 className="kpi-card-value" style={{ color: "var(--accent)" }}>{stats.profitFactor}</h2>
            <span className="kpi-card-unit">RATIO</span>
          </div>
        </div>
        <div className="card" style={{ marginBottom: 0 }}>
          <h4 className="kpi-card-label">MAX DRAWDOWN</h4>
          <div className="kpi-card-value-box">
            <h2 className="kpi-card-value" style={{ color: "var(--danger)" }}>-{stats.maxDD}</h2>
            <span className="kpi-card-unit">USDT</span>
          </div>
        </div>
        <div className="card" style={{ marginBottom: 0 }}>
          <h4 className="kpi-card-label">SHARPE RATIO</h4>
          <div className="kpi-card-value-box">
            <h2 className="kpi-card-value" style={{ color: "var(--warning)" }}>{stats.sharpeRatio}</h2>
            <span className="kpi-card-unit">SCORE</span>
          </div>
        </div>
      </div>

      <div className="performance-grid" style={{ marginTop: "20px" }}>
        <div className="card performance-card">
            <h4 className="kpi-card-label">WIN RATE</h4>
            <div className="performance-value">{stats.winRate}%</div>
        </div>
        <div className="card performance-card">
            <h4 className="kpi-card-label">AVG WIN / LOSS</h4>
            <div className="performance-value text-success">+{stats.avgWin} <span style={{fontSize: "12px", color: "var(--text-muted)"}}>/</span> <span className="text-danger">-{stats.avgLoss}</span></div>
        </div>
        <div className="card performance-card">
            <h4 className="kpi-card-label">TOTAL TRADES</h4>
            <div className="performance-value">{stats.totalTrades}</div>
        </div>
      </div>

      <div className="card">
        <div className="chart-header" style={{ marginBottom: "20px" }}>
          <h3 className="chart-title">Curva de Rendimiento Temporal</h3>
          <div className="tags-selector" style={{ marginTop: 0 }}>
            <button 
              className={`tag-btn ${chartMode === "daily" ? "active" : ""}`}
              onClick={() => setViewMode("daily")}
            >
              Día
            </button>
            <button 
              className={`tag-btn ${chartMode === "monthly" ? "active" : ""}`}
              onClick={() => setViewMode("monthly")}
            >
              Mes
            </button>
          </div>
        </div>
        <div style={{ height: "250px", width: "100%" }}>
          <ResponsiveContainer>
            <BarChart data={chartMode === "daily" ? stats.dailyData : stats.monthlyData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis 
                dataKey={chartMode === "daily" ? "date" : "month"} 
                tick={{ fill: "#F8FAFC", fontSize: 11, fontWeight: 500 }} 
                axisLine={false} 
                tickLine={false}
              />
              <YAxis 
                tick={{ fill: "#F8FAFC", fontSize: 11, fontWeight: 500 }} 
                axisLine={false} 
                tickLine={false}
                tickFormatter={(val) => `$${val}`}
              />
              <ReTooltip 
                contentStyle={{ backgroundColor: "var(--bg-app)", border: "1px solid var(--border)", borderRadius: "8px" }}
                itemStyle={{ fontWeight: "bold", color: "#fff", fontSize: "14px" }}
                labelStyle={{ color: "var(--text-muted)" }}
                cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
              />
              <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                {(chartMode === "daily" ? stats.dailyData : stats.monthlyData).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? "var(--success)" : "var(--danger)"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <h3 className="chart-title" style={{ marginBottom: "20px" }}>Rentabilidad por Activo</h3>
        <div style={{ height: "250px", width: "100%" }}>
          <ResponsiveContainer>
            <BarChart data={stats.pairData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis 
                dataKey="name" 
                tick={{ fill: "#F8FAFC", fontSize: 12, fontWeight: 700 }} 
                axisLine={false} 
                tickLine={false}
              />
              <YAxis 
                tick={{ fill: "#F8FAFC", fontSize: 11, fontWeight: 500 }} 
                axisLine={false} 
                tickLine={false}
              />
              <ReTooltip 
                contentStyle={{ backgroundColor: "var(--bg-app)", border: "1px solid var(--border)", borderRadius: "8px" }}
                itemStyle={{ fontWeight: "bold", color: "#fff", fontSize: "14px" }}
                labelStyle={{ color: "var(--text-muted)" }}
                cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
              />
              <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                {stats.pairData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? "var(--success)" : "var(--danger)"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}