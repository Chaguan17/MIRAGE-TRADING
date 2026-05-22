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
import "./index.css"; // Importamos los estilos globales

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_WS_URL =
  import.meta.env.VITE_API_WS_URL || "wss://stream.binance.com:9443/stream";

const chartColors = {
  accent: "#3B82F6",
  textMain: "#F8FAFC",
  textMuted: "#94A3B8",
};

function SettingsView() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [config, setConfig] = useState({});
  const [parametersMetadata, setParametersMetadata] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const metadataRes = await fetch(`${API_BASE_URL}/api/parameters`);
        const configRes = await fetch(`${API_BASE_URL}/api/config`);
        if (!metadataRes.ok || !configRes.ok) throw new Error("API Error");

        const metadata = await metadataRes.json();
        const configData = await configRes.json();

        setParametersMetadata(metadata);
        setConfig(configData || {});
        const firstTab = [
          ...new Set(Object.values(metadata).map((p) => p.tab)),
        ].sort()[0];
        setActiveTab(firstTab);
        setLoading(false);
      } catch (err) {
        console.error(err);
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const saveSettings = async () => {
    setIsSaving(true);
    try {
      await fetch(`${API_BASE_URL}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      setTimeout(() => {
        setIsSaving(false);
        navigate("/");
      }, 600);
    } catch (error) {
      alert("Error al guardar la configuración.");
      setIsSaving(false);
    }
  };

  const EditableStepper = ({ param, paramKey }) => {
    const val = config[paramKey];

    // ==========================================
    // 1. NUEVO DISEÑO: BOTONES TOGGLE PARA PARES
    // ==========================================
    if (
      paramKey === "PARES_ACTIVOS" ||
      param.type === "array" ||
      Array.isArray(val)
    ) {
      const currentArray = Array.isArray(val)
        ? val
        : typeof val === "string"
          ? val
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : [];

      // Lista de pares comunes para mostrar como botones.
      // Puedes añadir más aquí si quieres que salgan por defecto.
      const commonPairs = [
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
        "SOLUSDT",
        "XRPUSDT",
        "ADAUSDT",
        "DOGEUSDT",
        "AVAXUSDT",
        "LINKUSDT",
        "MATICUSDT",
        "DOTUSDT",
        "LTCUSDT",
      ];

      // Unimos la lista común con cualquier par raro que el usuario haya guardado previamente
      const allDisplayPairs = Array.from(
        new Set([...commonPairs, ...currentArray]),
      );

      const togglePair = (pair) => {
        if (currentArray.includes(pair)) {
          // Si está, lo quitamos
          setConfig({
            ...config,
            [paramKey]: currentArray.filter((p) => p !== pair),
          });
        } else {
          // Si no está, lo añadimos
          setConfig({ ...config, [paramKey]: [...currentArray, pair] });
        }
      };

      const handleAddCustom = (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          const newItem = e.currentTarget.value.trim().toUpperCase();
          if (newItem && !currentArray.includes(newItem)) {
            setConfig({ ...config, [paramKey]: [...currentArray, newItem] });
          }
          e.currentTarget.value = "";
        }
      };

      return (
        <div className="input-container">
          <div>
            <label
              style={{
                color: "var(--text-main)",
                fontWeight: "600",
                fontSize: "14px",
                display: "block",
              }}
            >
              {param.label || "Pares Activos"}
            </label>
            <span
              style={{
                color: "var(--text-muted)",
                fontSize: "12px",
                display: "block",
                marginTop: "4px",
              }}
            >
              {param.description ||
                "Haz clic en los pares para activarlos o desactivarlos."}
            </span>
          </div>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "10px",
              marginTop: "12px",
              marginBottom: "12px",
            }}
          >
            {allDisplayPairs.map((pair) => {
              const isActive = currentArray.includes(pair);
              return (
                <button
                  key={pair}
                  onClick={() => togglePair(pair)}
                  style={{
                    padding: "8px 16px",
                    borderRadius: "8px",
                    fontWeight: "700",
                    fontSize: "13px",
                    cursor: "pointer",
                    transition: "all 0.2s",
                    border: isActive
                      ? "1px solid var(--success)"
                      : "1px solid var(--border)",
                    backgroundColor: isActive
                      ? "var(--success-bg)"
                      : "var(--bg-card)",
                    color: isActive ? "var(--success)" : "var(--text-muted)",
                    boxShadow: isActive
                      ? "0 2px 8px rgba(16, 185, 129, 0.2)"
                      : "none",
                  }}
                >
                  {isActive ? "✓ " : "+ "}
                  {pair}
                </button>
              );
            })}
          </div>

          {currentArray.length === 0 && (
            <span
              style={{
                color: "var(--danger)",
                fontSize: "13px",
                fontWeight: "600",
                marginBottom: "12px",
                display: "block",
              }}
            >
              ⚠️ No hay pares configurados. El bot no operará.
            </span>
          )}

          <div style={{ marginTop: "4px" }}>
            <input
              type="text"
              className="text-input"
              placeholder="¿Falta un par? Escríbelo aquí y presiona ENTER"
              onKeyDown={handleAddCustom}
              style={{ fontSize: "13px", width: "100%", height: "40px" }}
            />
          </div>
        </div>
      );
    }

    // ==========================================
    // 2. TEXTOS NORMALES (Ej. SYMBOL)
    // ==========================================
    if (param.type === "text") {
      return (
        <div className="input-container">
          <div>
            <label
              style={{
                color: "var(--text-main)",
                fontWeight: "600",
                fontSize: "14px",
                display: "block",
              }}
            >
              {param.label}
            </label>
            <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>
              {param.description}
            </span>
          </div>
          <input
            type="text"
            className="text-input"
            value={val || ""}
            onChange={(e) =>
              setConfig({ ...config, [paramKey]: e.target.value })
            }
          />
        </div>
      );
    }

    // ==========================================
    // 3. SELECTORES (Opciones Múltiples)
    // ==========================================
    if (param.type === "select") {
      return (
        <div className="input-container">
          <div>
            <label
              style={{
                color: "var(--text-main)",
                fontWeight: "600",
                fontSize: "14px",
                display: "block",
              }}
            >
              {param.label}
            </label>
            <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>
              {param.description}
            </span>
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {param.options.map((opt) => (
              <button
                key={opt}
                onClick={() => setConfig({ ...config, [paramKey]: opt })}
                style={{
                  padding: "10px 16px",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontWeight: "600",
                  backgroundColor:
                    config[paramKey] === opt ? "var(--accent)" : "transparent",
                  color:
                    config[paramKey] === opt ? "#fff" : "var(--text-muted)",
                  boxShadow:
                    config[paramKey] === opt
                      ? "0 2px 8px rgba(59, 130, 246, 0.4)"
                      : "none",
                }}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      );
    }

    // ==========================================
    // 4. NÚMEROS Y STEPPERS (El resto)
    // ==========================================
    const updateVal = (newVal) => {
      let v = parseFloat(newVal);
      if (isNaN(v)) return;
      if (v < param.min) v = param.min;
      if (v > param.max) v = param.max;
      const factor = Math.pow(
        10,
        param.step?.toString().split(".")[1]?.length || 0,
      );
      v = Math.round(v * factor) / factor;
      setConfig((prev) => ({ ...prev, [paramKey]: v }));
    };

    return (
      <div className="input-container">
        <div>
          <label
            style={{
              color: "var(--text-main)",
              fontWeight: "600",
              fontSize: "14px",
              display: "block",
            }}
          >
            {param.label}
          </label>
          <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>
            {param.description}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            onClick={() => updateVal((val || 0) - parseFloat(param.step || 1))}
            className="btn-icon"
          >
            -
          </button>
          <div
            style={{
              flex: 1,
              position: "relative",
              display: "flex",
              alignItems: "center",
            }}
          >
            <input
              type="number"
              className="text-input"
              style={{
                textAlign: "center",
                fontSize: "18px",
                paddingRight: param.unit ? "36px" : "16px",
              }}
              step={param.step}
              value={val ?? ""}
              onChange={(e) => updateVal(e.target.value)}
              onBlur={(e) => updateVal(e.target.value)}
            />
            {param.unit && (
              <span
                style={{
                  position: "absolute",
                  right: "12px",
                  color: "var(--text-muted)",
                  fontSize: "13px",
                  fontWeight: "600",
                }}
              >
                {param.unit}
              </span>
            )}
          </div>
          <button
            onClick={() => updateVal((val || 0) + parseFloat(param.step || 1))}
            className="btn-icon"
          >
            +
          </button>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          className="animate-spin"
          style={{
            width: "40px",
            height: "40px",
            border: "4px solid rgba(59,130,246,0.3)",
            borderTopColor: "var(--accent)",
            borderRadius: "50%",
          }}
        />
      </div>
    );
  }

  const tabs = [...new Set(Object.values(parametersMetadata).map((p) => p.tab))]
    .sort()
    .map((tabId) => ({
      id: tabId,
      label:
        {
          general: "Cuenta y General",
          market: "Mercado",
          risk: "Gestión de Riesgo",
          execution: "Ejecución (SL/TP)",
          strategy: "Motor IA & Estrategia",
          scheduling: "Horarios",
        }[tabId] || tabId,
      icon:
        {
          general: "🏦",
          market: "📊",
          risk: "🛡️",
          execution: "⚡",
          strategy: "🧠",
          scheduling: "⏰",
        }[tabId] || "⚙️",
    }));

  return (
    <div className="settings-layout animate-fade-in">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "30px",
        }}
      >
        <div>
          <button
            onClick={() => navigate("/")}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "5px",
              marginBottom: "10px",
            }}
          >
            ← Volver al Terminal Principal
          </button>
          <h2 style={{ margin: 0, fontSize: "28px" }}>Ajustes del Algoritmo</h2>
        </div>
        <button
          onClick={saveSettings}
          disabled={isSaving}
          className="btn-primary"
        >
          {isSaving ? "Aplicando Cambios..." : "💾 Guardar y Aplicar"}
        </button>
      </div>

      <div
        style={{
          display: "flex",
          gap: "24px",
          alignItems: "flex-start",
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            flex: "1",
            minWidth: "220px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: "16px",
                borderRadius: "12px",
                border: "none",
                textAlign: "left",
                cursor: "pointer",
                backgroundColor:
                  activeTab === tab.id ? "var(--bg-card)" : "transparent",
                color:
                  activeTab === tab.id
                    ? "var(--text-main)"
                    : "var(--text-muted)",
                fontWeight: activeTab === tab.id ? "700" : "500",
                display: "flex",
                alignItems: "center",
                gap: "12px",
                borderLeft:
                  activeTab === tab.id
                    ? "4px solid var(--accent)"
                    : "4px solid transparent",
              }}
            >
              <span style={{ fontSize: "20px" }}>{tab.icon}</span> {tab.label}
            </button>
          ))}
        </div>

        <div
          className="card"
          style={{
            flex: "3",
            minWidth: "300px",
            padding: "32px",
            marginBottom: 0,
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "24px",
            }}
          >
            {Object.entries(parametersMetadata)
              .filter(([_, p]) => p.tab === activeTab)
              .map(([key, p]) => (
                <EditableStepper key={key} param={p} paramKey={key} />
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}

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
          (op.position_value || 200) *
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
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          className="animate-spin"
          style={{
            width: "40px",
            height: "40px",
            border: "4px solid rgba(59,130,246,0.3)",
            borderTopColor: "var(--accent)",
            borderRadius: "50%",
          }}
        />
      </div>
    );

  return (
    <div className="dashboard-layout animate-fade-in">
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "32px",
          borderBottom: "1px solid var(--border)",
          paddingBottom: "24px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              background: "linear-gradient(135deg, var(--accent), #6366f1)",
              padding: "12px",
              borderRadius: "12px",
              boxShadow: "0 4px 15px rgba(59, 130, 246, 0.3)",
            }}
          >
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
            <h1
              style={{
                margin: 0,
                fontSize: "28px",
                fontWeight: "800",
                letterSpacing: "-0.5px",
              }}
            >
              MIRAGE{" "}
              <span style={{ fontWeight: "300", color: "var(--text-muted)" }}>
                TERMINAL
              </span>
            </h1>
            <span
              style={{
                fontSize: "12px",
                color: "var(--success)",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                marginTop: "4px",
              }}
            >
              <div
                style={{
                  width: "8px",
                  height: "8px",
                  backgroundColor: "var(--success)",
                  borderRadius: "50%",
                  boxShadow: "0 0 8px var(--success)",
                }}
              ></div>{" "}
              Sistemas En Línea
            </span>
          </div>
        </div>
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
            <h4
              style={{
                margin: "0 0 8px 0",
                color: "var(--text-muted)",
                fontSize: "13px",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              {kpi.label}
            </h4>
            <div
              style={{ display: "flex", alignItems: "baseline", gap: "6px" }}
            >
              <h2
                style={{
                  margin: 0,
                  fontSize: "40px",
                  fontWeight: "700",
                  color: kpi.color,
                  letterSpacing: "-1px",
                }}
              >
                {kpi.value}
              </h2>
              <span
                style={{
                  fontSize: "16px",
                  color: "var(--text-muted)",
                  fontWeight: "500",
                }}
              >
                {kpi.unit}
              </span>
            </div>
          </div>
        ))}
      </div>

      {pairStats.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: "12px",
            marginBottom: "32px",
            flexWrap: "wrap",
          }}
        >
          {pairStats.map((s) => (
            <div
              key={s.pair}
              className="card"
              style={{
                padding: "10px 16px",
                marginBottom: 0,
                display: "flex",
                gap: "12px",
                alignItems: "center",
              }}
            >
              <span style={{ fontWeight: "700", fontSize: "14px" }}>
                {s.pair}
              </span>
              <div
                style={{
                  width: "1px",
                  height: "24px",
                  backgroundColor: "var(--border)",
                }}
              ></div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    color: s.wr >= 50 ? "var(--success)" : "var(--danger)",
                    fontWeight: "800",
                    fontSize: "14px",
                  }}
                >
                  {s.wr}%
                </span>
                <span
                  style={{
                    color: "var(--text-muted)",
                    fontSize: "10px",
                    textTransform: "uppercase",
                  }}
                >
                  {s.total} Trades
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "20px",
          }}
        >
          <h3 style={{ margin: 0, fontSize: "18px" }}>
            Curva de Equidad Algorítmica
          </h3>
          <span
            style={{
              fontSize: "12px",
              background: "var(--bg-app)",
              padding: "4px 8px",
              borderRadius: "4px",
              color: "var(--text-muted)",
              border: "1px solid var(--border)",
            }}
          >
            En tiempo real
          </span>
        </div>
        <div style={{ height: "350px", width: "100%" }}>
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
                tick={{ fill: chartColors.textMuted, fontSize: 12 }}
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
                itemStyle={{ color: chartColors.textMain, fontWeight: "bold" }}
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
        <h3 style={{ margin: "0 0 20px 0", fontSize: "18px" }}>
          Operaciones Activas en Mercado
        </h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Activo</th>
              <th>Dirección</th>
              <th>Precio Entrada</th>
              <th style={{ color: "var(--accent)" }}>Marca Actual</th>
              <th style={{ color: "var(--success)" }}>Take Profit</th>
              <th style={{ color: "var(--danger)" }}>Stop Loss</th>
              <th style={{ textAlign: "right" }}>ROI %</th>
              <th style={{ textAlign: "right" }}>PnL Flotante</th>
            </tr>
          </thead>
          <tbody>
            {data.operaciones_activas?.length === 0 ? (
              <tr>
                <td
                  colSpan="8"
                  style={{
                    textAlign: "center",
                    padding: "40px",
                    color: "var(--text-muted)",
                  }}
                >
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
                    (op.position_value || 200)
                  ).toFixed(2),
                );
                const roiPct = (
                  (live / op.entry - 1) *
                  (op.type === "LONG" ? 1 : -1) *
                  100
                ).toFixed(2);
                return (
                  <tr key={idx}>
                    <td style={{ fontWeight: "bold" }}>{op.pair}</td>
                    <td>
                      <span
                        style={{
                          padding: "4px 10px",
                          borderRadius: "6px",
                          fontSize: "12px",
                          fontWeight: "700",
                          backgroundColor:
                            op.type === "LONG"
                              ? "var(--success-bg)"
                              : "var(--danger-bg)",
                          color:
                            op.type === "LONG"
                              ? "var(--success)"
                              : "var(--danger)",
                        }}
                      >
                        {op.type}
                      </span>
                    </td>
                    <td style={{ fontFamily: "Menlo, monospace" }}>
                      {op.entry}
                    </td>
                    <td
                      style={{
                        fontFamily: "Menlo, monospace",
                        fontWeight: "bold",
                      }}
                    >
                      {live?.toLocaleString()}
                    </td>
                    <td
                      style={{
                        fontFamily: "Menlo, monospace",
                        color: "var(--success)",
                      }}
                    >
                      {op.tp}
                    </td>
                    <td style={{ fontFamily: "Menlo, monospace" }}>
                      <span
                        style={{
                          color: op.is_trailing
                            ? "var(--warning)"
                            : "var(--danger)",
                        }}
                      >
                        {op.sl === 0 ? "SIN SL" : op.sl}
                      </span>
                      {op.is_trailing && (
                        <span
                          style={{
                            marginLeft: "8px",
                            fontSize: "10px",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            backgroundColor: "rgba(245, 158, 11, 0.1)",
                            color: "var(--warning)",
                            fontWeight: "bold",
                          }}
                        >
                          TRAILING
                        </span>
                      )}
                    </td>
                    <td
                      style={{
                        textAlign: "right",
                        fontWeight: "700",
                        fontFamily: "Menlo, monospace",
                        color: roiPct >= 0 ? "var(--success)" : "var(--danger)",
                      }}
                    >
                      {roiPct > 0 ? "+" : ""}
                      {roiPct}%
                    </td>
                    <td
                      style={{
                        textAlign: "right",
                        fontWeight: "700",
                        fontFamily: "Menlo, monospace",
                        color:
                          livePnl >= 0 ? "var(--success)" : "var(--danger)",
                      }}
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
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "16px",
            marginBottom: "20px",
          }}
        >
          <h3 style={{ margin: 0, fontSize: "18px" }}>
            Historial de Ejecución
          </h3>
          <div style={{ display: "flex", gap: "12px" }}>
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
                <td style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                  {op.timestamp}
                </td>
                <td style={{ fontWeight: "bold" }}>{op.pair}</td>
                <td
                  style={{
                    fontWeight: "bold",
                    color:
                      op.action === "LONG" ? "var(--success)" : "var(--danger)",
                  }}
                >
                  {op.action}
                </td>
                <td style={{ fontFamily: "Menlo, monospace" }}>
                  {op.entry_price}
                </td>
                <td style={{ fontFamily: "Menlo, monospace" }}>
                  {op.close_price}
                </td>
                <td
                  style={{
                    textAlign: "right",
                    fontWeight: "700",
                    fontFamily: "Menlo, monospace",
                    color:
                      op.pnl_usdt >= 0 ? "var(--success)" : "var(--danger)",
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

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [livePrices, setLivePrices] = useState({});
  const [historyFilter, setHistoryFilter] = useState("ALL");
  const [historyLimit, setHistoryLimit] = useState(20);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectDelayRef = useRef(1000);

  const connectWebSocket = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket(
      `${API_WS_URL}?streams=btcusdt@ticker/ethusdt@ticker/bnbusdt@ticker`,
    );
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
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, delay);
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
    connectWebSocket();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  if (error)
    return (
      <div
        className="app-container"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          className="card"
          style={{
            background: "var(--danger-bg)",
            borderColor: "var(--danger)",
            textAlign: "center",
          }}
        >
          <h2 style={{ color: "var(--danger)" }}>
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
        <Route path="/settings" element={<SettingsView />} />
      </Routes>
    </div>
  );
}
