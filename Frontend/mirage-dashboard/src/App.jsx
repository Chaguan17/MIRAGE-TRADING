import React, { useState, useEffect, useMemo } from "react";
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

// Variables de entorno
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_WS_URL =
  import.meta.env.VITE_API_WS_URL || "wss://stream.binance.com:9443/stream";

// Paleta Comercial "Dark Mode Institutional"
const theme = {
  bgApp: "#0B1120",
  bgCard: "#1E293B",
  bgInput: "#0F172A",
  border: "#334155",
  borderHover: "#475569",
  textMain: "#F8FAFC",
  textMuted: "#94A3B8",
  accent: "#3B82F6",
  accentHover: "#2563EB",
  success: "#10B981",
  danger: "#EF4444",
  warning: "#F59E0B",
  successBg: "rgba(16, 185, 129, 0.15)",
  dangerBg: "rgba(239, 68, 68, 0.15)",
};

// ==========================================
// VISTA 1: PANEL DE CONFIGURACIÓN (DINÁMICO)
// ==========================================
function SettingsView() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [config, setConfig] = useState({});
  const [parametersMetadata, setParametersMetadata] = useState({});
  const [loading, setLoading] = useState(true);

  // Cargar metadata y configuración
  useEffect(() => {
    const loadData = async () => {
      try {
        const metadataRes = await fetch(`${API_BASE_URL}/api/parameters`);
        const configRes = await fetch(`${API_BASE_URL}/api/config`);

        if (!metadataRes.ok || !configRes.ok) {
          throw new Error(`API error: metadata ${metadataRes.status}, config ${configRes.status}`);
        }

        const metadata = await metadataRes.json();
        const configData = await configRes.json();

        if (!metadata || Object.keys(metadata).length === 0) {
          throw new Error("No metadata received from API");
        }

        setParametersMetadata(metadata);
        setConfig(configData || {});
        const firstTab = [...new Set(Object.values(metadata).map(p => p.tab))].sort()[0];
        setActiveTab(firstTab);
        setLoading(false);
      } catch (err) {
        console.error("Error cargando configuración:", err);
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

    const updateVal = (newVal) => {
      let v = newVal;

      // Convertir a número si es tipo number
      if (param.type === 'number') {
        v = parseFloat(newVal);
        if (isNaN(v)) return;
        if (v < param.min) v = param.min;
        if (v > param.max) v = param.max;
        const factor = Math.pow(10, (param.step?.toString().split(".")[1]?.length || 0));
        v = Math.round(v * factor) / factor;
      }

      setConfig((prev) => ({ ...prev, [paramKey]: v }));
    };

    const increment = () => updateVal((val || 0) + parseFloat(param.step || 1));
    const decrement = () => updateVal((val || 0) - parseFloat(param.step || 1));

    const btnStyle = {
      width: "44px",
      height: "44px",
      backgroundColor: theme.bgCard,
      border: `1px solid ${theme.border}`,
      borderRadius: "8px",
      color: theme.textMain,
      fontSize: "20px",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      transition: "all 0.2s",
    };

    if (param.type === 'select') {
      return (
        <div
          style={{
            backgroundColor: theme.bgInput,
            padding: "20px",
            borderRadius: "12px",
            border: `1px solid ${theme.border}`,
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          <div>
            <label style={{
              color: theme.textMain,
              fontWeight: "600",
              fontSize: "14px",
              display: "block",
              marginBottom: "8px",
            }}>
              {param.label}
            </label>
            <span style={{
              color: theme.textMuted,
              fontSize: "12px",
              lineHeight: "1.4",
              display: "block",
            }}>
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
                  transition: "all 0.2s",
                  backgroundColor: config[paramKey] === opt ? theme.accent : "transparent",
                  color: config[paramKey] === opt ? "#fff" : theme.textMuted,
                  boxShadow: config[paramKey] === opt ? "0 2px 8px rgba(59, 130, 246, 0.4)" : "none",
                }}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      );
    }

    return (
      <div
        style={{
          backgroundColor: theme.bgInput,
          padding: "20px",
          borderRadius: "12px",
          border: `1px solid ${theme.border}`,
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        <div>
          <label style={{
            color: theme.textMain,
            fontWeight: "600",
            fontSize: "14px",
            display: "block",
            marginBottom: "4px",
          }}>
            {param.label}
          </label>
          <span style={{
            color: theme.textMuted,
            fontSize: "12px",
            lineHeight: "1.4",
            display: "block",
          }}>
            {param.description}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            onClick={decrement}
            style={btnStyle}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = theme.border)}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = theme.bgCard)}
          >
            -
          </button>
          <div style={{ flex: 1, position: "relative", display: "flex", alignItems: "center" }}>
            <input
              type="number"
              step={param.step}
              value={val ?? ''}
              onChange={(e) => updateVal(e.target.value)}
              style={{
                width: "100%",
                height: "44px",
                backgroundColor: theme.bgApp,
                color: theme.accent,
                border: `1px solid ${theme.border}`,
                borderRadius: "8px",
                fontWeight: "700",
                fontSize: "18px",
                textAlign: "center",
                outline: "none",
                paddingRight: param.unit ? "36px" : "10px",
              }}
              onFocus={(e) => (e.target.style.borderColor = theme.accent)}
              onBlur={(e) => {
                e.target.style.borderColor = theme.border;
                updateVal(e.target.value);
              }}
            />
            {param.unit && (
              <span style={{
                position: "absolute",
                right: "12px",
                color: theme.textMuted,
                fontSize: "13px",
                fontWeight: "600",
                pointerEvents: "none",
              }}>
                {param.unit}
              </span>
            )}
          </div>
          <button
            onClick={increment}
            style={btnStyle}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = theme.border)}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = theme.bgCard)}
          >
            +
          </button>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: theme.bgApp,
        color: theme.accent,
      }}>
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "15px",
        }}>
          <div style={{
            width: "40px",
            height: "40px",
            border: "4px solid rgba(59, 130, 246, 0.3)",
            borderTopColor: theme.accent,
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
          }} />
          <p style={{ color: theme.textMuted }}>Cargando ajustes...</p>
        </div>
      </div>
    );
  }

  const tabs = [...new Set(Object.values(parametersMetadata).map(p => p.tab))]
    .sort()
    .map(tabId => ({
      id: tabId,
      label: {
        general: "Cuenta y General",
        market: "Mercado",
        risk: "Gestión de Riesgo",
        execution: "Ejecución (SL/TP)",
        strategy: "Motor IA & Estrategia",
        scheduling: "Horarios"
      }[tabId] || tabId,
      icon: {
        general: "🏦",
        market: "📊",
        risk: "🛡️",
        execution: "⚡",
        strategy: "🧠",
        scheduling: "⏰"
      }[tabId] || "⚙️"
    }));

  return (
    <div style={{
      maxWidth: "1100px",
      margin: "40px auto",
      padding: "0 20px",
      animation: "fadeIn 0.4s ease-out",
    }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "30px",
      }}>
        <div>
          <button
            onClick={() => navigate("/")}
            style={{
              background: "none",
              border: "none",
              color: theme.textMuted,
              cursor: "pointer",
              fontSize: "14px",
              display: "flex",
              alignItems: "center",
              gap: "5px",
              marginBottom: "10px",
              transition: "color 0.2s",
            }}
            onMouseOver={(e) => (e.target.style.color = theme.textMain)}
            onMouseOut={(e) => (e.target.style.color = theme.textMuted)}
          >
            ← Volver al Terminal Principal
          </button>
          <h2 style={{ margin: 0, fontSize: "28px", color: theme.textMain }}>
            Ajustes del Algoritmo
          </h2>
        </div>
        <button
          onClick={saveSettings}
          disabled={isSaving}
          style={{
            padding: "12px 24px",
            borderRadius: "8px",
            backgroundColor: isSaving ? theme.border : theme.accent,
            color: "white",
            fontWeight: "bold",
            border: "none",
            cursor: isSaving ? "not-allowed" : "pointer",
            display: "flex",
            gap: "8px",
            alignItems: "center",
            transition: "all 0.2s",
          }}
        >
          {isSaving ? "Aplicando Cambios..." : "💾 Guardar y Aplicar"}
        </button>
      </div>

      <div style={{ display: "flex", gap: "24px", alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{
          flex: "1",
          minWidth: "220px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: "16px",
                borderRadius: "12px",
                border: "none",
                textAlign: "left",
                backgroundColor: activeTab === tab.id ? theme.bgCard : "transparent",
                color: activeTab === tab.id ? theme.textMain : theme.textMuted,
                fontWeight: activeTab === tab.id ? "700" : "500",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "12px",
                transition: "all 0.2s",
                borderLeft: activeTab === tab.id ? `4px solid ${theme.accent}` : "4px solid transparent",
              }}
            >
              <span style={{ fontSize: "20px" }}>{tab.icon}</span> {tab.label}
            </button>
          ))}
        </div>

        <div style={{
          flex: "3",
          minWidth: "300px",
          backgroundColor: theme.bgCard,
          padding: "32px",
          borderRadius: "16px",
          border: `1px solid ${theme.border}`,
        }}>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "24px",
          }}>
            {Object.entries(parametersMetadata)
              .filter(([_, param]) => param.tab === activeTab)
              .map(([key, param]) => (
                <EditableStepper key={key} param={param} paramKey={key} />
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// VISTA 2: DASHBOARD PRINCIPAL (COMERCIAL)
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
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "15px",
          }}
        >
          <div
            style={{
              width: "40px",
              height: "40px",
              border: "4px solid rgba(59, 130, 246, 0.3)",
              borderTopColor: theme.accent,
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
            }}
          />
          <h2 style={{ fontWeight: "500" }}>
            Sincronizando con Motor Algorítmico...
          </h2>
        </div>
      </div>
    );

  return (
    <div
      style={{
        maxWidth: "1400px",
        margin: "0 auto",
        animation: "fadeIn 0.5s ease-out",
      }}
    >
      {/* HEADER INSTITUCIONAL */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "32px",
          borderBottom: `1px solid ${theme.border}`,
          paddingBottom: "24px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              background: `linear-gradient(135deg, ${theme.accent}, #6366f1)`,
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
              <span style={{ fontWeight: "300", color: theme.textMuted }}>
                TERMINAL
              </span>
            </h1>
            <span
              style={{
                fontSize: "12px",
                color: theme.success,
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
                  backgroundColor: theme.success,
                  borderRadius: "50%",
                  boxShadow: "0 0 8px #10B981",
                }}
              ></div>
              Sistemas En Línea
            </span>
          </div>
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
            fontWeight: "600",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            transition: "all 0.2s",
          }}
          onMouseOver={(e) =>
            (e.currentTarget.style.borderColor = theme.textMuted)
          }
          onMouseOut={(e) => (e.currentTarget.style.borderColor = theme.border)}
        >
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
          </svg>
          Ajustes
        </button>
      </header>

      {/* KPIs ROW ORIGINAL */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "24px",
          marginBottom: "32px",
        }}
      >
        {[
          {
            label: "Net PnL Global (Live)",
            value: `${liveTotalPnL > 0 ? "+" : ""}${liveTotalPnL}`,
            unit: "USDT",
            color: liveTotalPnL >= 0 ? theme.success : theme.danger,
            sub: "Rendimiento Acumulado",
          },
          {
            label: "Win Rate Algorítmico",
            value: `${data.win_rate}`,
            unit: "%",
            color: theme.accent,
            sub: "Precisión de Modelos",
          },
          {
            label: "Volumen de Operaciones",
            value: data.total_operaciones,
            unit: "Trades",
            color: theme.textMain,
            sub: "Ejecuciones Totales",
          },
        ].map((kpi, idx) => (
          <div
            key={idx}
            style={{
              backgroundColor: theme.bgCard,
              border: `1px solid ${theme.border}`,
              padding: "24px",
              borderRadius: "16px",
              boxShadow:
                "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
              }}
            >
              <div>
                <h4
                  style={{
                    margin: "0 0 8px 0",
                    color: theme.textMuted,
                    fontSize: "13px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  {kpi.label}
                </h4>
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    gap: "6px",
                  }}
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
                      color: theme.textMuted,
                      fontWeight: "500",
                    }}
                  >
                    {kpi.unit}
                  </span>
                </div>
              </div>
            </div>
            <p
              style={{
                margin: "12px 0 0 0",
                fontSize: "13px",
                color: theme.borderHover,
              }}
            >
              {kpi.sub}
            </p>
          </div>
        ))}
      </div>

      {/* GRÁFICA EVOLUCIÓN */}
      <div
        style={{
          backgroundColor: theme.bgCard,
          border: `1px solid ${theme.border}`,
          padding: "24px",
          borderRadius: "16px",
          marginBottom: "32px",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "20px",
          }}
        >
          <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "600" }}>
            Curva de Equidad Algorítmica
          </h3>
          <span
            style={{
              fontSize: "12px",
              background: theme.bgApp,
              padding: "4px 8px",
              borderRadius: "4px",
              color: theme.textMuted,
              border: `1px solid ${theme.border}`,
            }}
          >
            Actualizado en tiempo real
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
                    stopColor={theme.accent}
                    stopOpacity={0.6}
                  />
                  <stop
                    offset="95%"
                    stopColor={theme.accent}
                    stopOpacity={0.05}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="4 4"
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
                  boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
                }}
                itemStyle={{ color: theme.textMain, fontWeight: "bold" }}
              />
              <Area
                type="monotone"
                dataKey="pnl"
                name="PnL Acumulado"
                stroke={theme.accent}
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorPnL)"
                activeDot={{ r: 6, strokeWidth: 0, fill: theme.textMain }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* TABLAS */}
      {(() => {
        const tableCardStyle = {
          backgroundColor: theme.bgCard,
          border: `1px solid ${theme.border}`,
          padding: "24px",
          borderRadius: "16px",
          marginBottom: "32px",
          overflowX: "auto",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        };
        const thStyle = {
          padding: "16px 12px",
          color: theme.textMuted,
          borderBottom: `1px solid ${theme.border}`,
          textTransform: "uppercase",
          fontSize: "12px",
          fontWeight: "600",
          letterSpacing: "0.5px",
          whiteSpace: "nowrap",
        };
        const tdStyle = {
          padding: "16px 12px",
          borderBottom: `1px solid ${theme.borderHover}`,
          fontSize: "14px",
          whiteSpace: "nowrap",
        };

        return (
          <>
            <div style={tableCardStyle}>
              <h3 style={{ margin: "0 0 20px 0", fontSize: "18px" }}>
                Operaciones Activas en Mercado
              </h3>
              <table
                style={{
                  width: "100%",
                  textAlign: "left",
                  borderCollapse: "collapse",
                }}
              >
                <thead>
                  <tr>
                    <th style={thStyle}>Activo</th>
                    <th style={thStyle}>Dirección</th>
                    <th style={thStyle}>Precio Entrada</th>
                    <th style={{ ...thStyle, color: theme.accent }}>
                      Marca Actual
                    </th>
                    <th style={{ ...thStyle, color: theme.success }}>
                      Take Profit
                    </th>
                    <th style={{ ...thStyle, color: theme.danger }}>
                      Stop Loss
                    </th>
                    <th style={{ ...thStyle, textAlign: "right" }}>
                      PnL Flotante
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.operaciones_activas?.length === 0 ? (
                    <tr>
                      <td
                        colSpan="7"
                        style={{
                          textAlign: "center",
                          padding: "40px",
                          color: theme.textMuted,
                        }}
                      >
                        No hay posiciones abiertas en este momento.
                      </td>
                    </tr>
                  ) : (
                    data.operaciones_activas?.map((op, idx) => {
                      const live = livePrices[op.pair] || op.current_price;
                      const livePnl = (
                        (live / op.entry - 1) *
                        (op.type === "LONG" ? 1 : -1) *
                        (op.position_value || 200)
                      ).toFixed(2);
                      return (
                        <tr
                          key={idx}
                          style={{ transition: "background 0.2s" }}
                          onMouseOver={(e) =>
                            (e.currentTarget.style.backgroundColor =
                              "rgba(255,255,255,0.02)")
                          }
                          onMouseOut={(e) =>
                            (e.currentTarget.style.backgroundColor =
                              "transparent")
                          }
                        >
                          <td style={{ ...tdStyle, fontWeight: "bold" }}>
                            {op.pair}
                          </td>
                          <td style={tdStyle}>
                            <span
                              style={{
                                padding: "4px 10px",
                                borderRadius: "6px",
                                fontSize: "12px",
                                fontWeight: "700",
                                backgroundColor:
                                  op.type === "LONG"
                                    ? theme.successBg
                                    : theme.dangerBg,
                                color:
                                  op.type === "LONG"
                                    ? theme.success
                                    : theme.danger,
                              }}
                            >
                              {op.type}
                            </span>
                          </td>
                          <td
                            style={{
                              ...tdStyle,
                              fontFamily: "Menlo, monospace",
                            }}
                          >
                            {op.entry}
                          </td>
                          <td
                            style={{
                              ...tdStyle,
                              fontFamily: "Menlo, monospace",
                              fontWeight: "bold",
                              color: theme.textMain,
                            }}
                          >
                            {live?.toLocaleString()}
                          </td>
                          <td
                            style={{
                              ...tdStyle,
                              fontFamily: "Menlo, monospace",
                              color: theme.success,
                            }}
                          >
                            {op.tp}
                          </td>
                          <td
                            style={{
                              ...tdStyle,
                              fontFamily: "Menlo, monospace",
                            }}
                          >
                            <span
                              style={{
                                color: op.is_trailing
                                  ? theme.warning
                                  : theme.danger,
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
                                  color: theme.warning,
                                  fontWeight: "bold",
                                }}
                              >
                                TRAILING
                              </span>
                            )}
                          </td>
                          <td
                            style={{
                              ...tdStyle,
                              textAlign: "right",
                              fontWeight: "700",
                              fontFamily: "Menlo, monospace",
                              color:
                                livePnl >= 0 ? theme.success : theme.danger,
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

            <div style={tableCardStyle}>
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
                    value={historyFilter}
                    onChange={(e) => setHistoryFilter(e.target.value)}
                    style={{
                      backgroundColor: theme.bgInput,
                      color: theme.textMain,
                      border: `1px solid ${theme.border}`,
                      padding: "8px 12px",
                      borderRadius: "6px",
                      outline: "none",
                      fontSize: "13px",
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
                      backgroundColor: theme.bgInput,
                      color: theme.textMain,
                      border: `1px solid ${theme.border}`,
                      padding: "8px 12px",
                      borderRadius: "6px",
                      outline: "none",
                      fontSize: "13px",
                    }}
                  >
                    <option value={20}>Últimos 20</option>
                    <option value={50}>Últimos 50</option>
                    <option value={100}>Últimos 100</option>
                  </select>
                </div>
              </div>
              <table
                style={{
                  width: "100%",
                  textAlign: "left",
                  borderCollapse: "collapse",
                }}
              >
                <thead>
                  <tr>
                    <th style={thStyle}>Fecha / Hora</th>
                    <th style={thStyle}>Activo</th>
                    <th style={thStyle}>Lado</th>
                    <th style={thStyle}>Precio Entrada</th>
                    <th style={thStyle}>Precio Salida</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>
                      Resultado PnL
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredHistory.map((op, i) => (
                    <tr
                      key={i}
                      style={{ transition: "background 0.2s" }}
                      onMouseOver={(e) =>
                        (e.currentTarget.style.backgroundColor =
                          "rgba(255,255,255,0.02)")
                      }
                      onMouseOut={(e) =>
                        (e.currentTarget.style.backgroundColor = "transparent")
                      }
                    >
                      <td
                        style={{
                          ...tdStyle,
                          color: theme.textMuted,
                          fontSize: "13px",
                        }}
                      >
                        {op.timestamp}
                      </td>
                      <td style={{ ...tdStyle, fontWeight: "bold" }}>
                        {op.pair}
                      </td>
                      <td
                        style={{
                          ...tdStyle,
                          fontWeight: "bold",
                          color:
                            op.action === "LONG" ? theme.success : theme.danger,
                        }}
                      >
                        {op.action}
                      </td>
                      <td
                        style={{ ...tdStyle, fontFamily: "Menlo, monospace" }}
                      >
                        {op.entry_price}
                      </td>
                      <td
                        style={{ ...tdStyle, fontFamily: "Menlo, monospace" }}
                      >
                        {op.close_price}
                      </td>
                      <td
                        style={{
                          ...tdStyle,
                          textAlign: "right",
                          fontWeight: "700",
                          fontFamily: "Menlo, monospace",
                          color:
                            op.pnl_usdt >= 0 ? theme.success : theme.danger,
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
          </>
        );
      })()}
    </div>
  );
}

// ==========================================
// APP ROOT CON RESET DE ESTILOS DE VITE
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
        .catch(() =>
          setError(
            "Conexión perdida con el motor Mirage. Verifique el servidor backend.",
          ),
        );
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
          padding: "20px",
        }}
      >
        <div
          style={{
            background: theme.dangerBg,
            padding: "30px",
            border: `1px solid ${theme.danger}`,
            borderRadius: "16px",
            maxWidth: "500px",
            textAlign: "center",
          }}
        >
          <h2 style={{ margin: "0 0 10px 0" }}>⚠️ Error Crítico de Conexión</h2>
          <p style={{ margin: 0, color: theme.textMain }}>{error}</p>
        </div>
      </div>
    );

  return (
    <>
      <style>{`
        /* Reset para eliminar el borde blanco y márgenes de la plantilla de Vite */
        html, body {
          margin: 0 !important;
          padding: 0 !important;
          background-color: ${theme.bgApp} !important;
        }
        #root {
          margin: 0 !important;
          padding: 0 !important;
          max-width: 100% !important;
          border: none !important;
          border-inline: none !important; 
          background-color: ${theme.bgApp} !important;
          min-height: 100vh;
        }
        
        /* Ocultar botones de inputs de número */
        input[type=number]::-webkit-inner-spin-button, 
        input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
        input[type=number] { -moz-appearance: textfield; }
        
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>

      <div
        style={{
          minHeight: "100vh",
          backgroundColor: theme.bgApp,
          color: theme.textMain,
          padding: "40px 20px",
          fontFamily: '"Inter", "Segoe UI", Roboto, sans-serif',
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
    </>
  );
}
