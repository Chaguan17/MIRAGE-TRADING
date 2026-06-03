import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";

const PAIR_PRESETS = [
  "BTCUSDT",
  "ETHUSDT",
  "BNBUSDT",
];

const TIMEFRAME_PRESETS = ["1m", "5m", "15m", "1h", "4h", "1d"];

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// ─── TAB INFO ─────────────────────────────────────────────────────
const TAB_INFO = {
  general: { label: "Cuenta", icon: "🏦" },
  market: { label: "Mercado", icon: "📊" },
  risk: { label: "Riesgo", icon: "🛡️" },
  execution: { label: "Ejecución", icon: "⚡" },
  strategy: { label: "Motor IA", icon: "🧠" },
  analysis: { label: "Análisis", icon: "🔍" },
  scheduling: { label: "Ciclo Sueño", icon: "⏰" },
  vetos: { label: "Vetos", icon: "🚫" },
  connection: { label: "Conexión", icon: "🌐" },
};

const TAB_ORDER = [
  "general",
  "market",
  "risk",
  "execution",
  "strategy",
  "analysis",
  "scheduling",
  "vetos",
  "connection",
];

// ─── STYLES ───────────────────────────────────────────────────────
const S = {
  root: {
    backgroundColor: "#060913",
    minHeight: "100vh",
  },

  layout: {
    padding: "0 1.5rem 3rem",
    maxWidth: "1200px",
    margin: "0 auto",
    color: "#f8fafc",
    fontFamily: "Inter, system-ui, sans-serif",
  },

  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingTop: "1.5rem",
    paddingBottom: "1.5rem",
    borderBottom: "1px solid #1e293b",
    marginBottom: "2rem",
    flexWrap: "wrap",
    gap: "1rem",
  },

  title: {
    fontSize: "1.7rem",
    fontWeight: "800",
    margin: 0,
  },

  btnPrimary: {
    background: "none",
    border: "1px solid #1e293b",
    color: "#7526b6",
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

  card: {
    background: "#0b1120",
    padding: "2rem",
    borderRadius: "20px",
    border: "1px solid #1e293b",
  },

  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 300px), 1fr))",
    gap: "2rem",
  },

  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },

  label: {
    fontWeight: "700",
    fontSize: "0.9rem",
  },

  desc: {
    fontSize: "0.78rem",
    color: "#64748b",
    lineHeight: "1.5",
  },

  inputWrapper: {
    position: "relative",
  },

  input: {
    background: "#121b2e",
    border: "1px solid #334155",
    color: "white",
    padding: "11px 16px",
    borderRadius: "10px",
    fontSize: "0.9rem",
    width: "100%",
    outline: "none",
    fontFamily: "JetBrains Mono, monospace",
    boxSizing: "border-box",
  },

  unit: {
    position: "absolute",
    right: "14px",
    top: "50%",
    transform: "translateY(-50%)",
    color: "#aa3bff",
    fontWeight: "700",
    pointerEvents: "none",
  },

  presetContainer: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
  },

  presetBtn: (active) => ({
    padding: "6px 12px",
    borderRadius: "8px",
    fontSize: "0.75rem",
    fontWeight: "700",
    cursor: "pointer",
    border: "1px solid",
    borderColor: active ? "#aa3bff" : "#334155",
    background: active ? "rgba(170, 59, 255, 0.15)" : "#121b2e",
    color: active ? "#aa3bff" : "#94a3b8",
  }),

  switch: (active) => ({
    width: "44px",
    height: "22px",
    borderRadius: "11px",
    background: active ? "#aa3bff" : "#1e293b",
    position: "relative",
    cursor: "pointer",
    transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
    border: "1px solid",
    borderColor: active ? "#aa3bff" : "#334155",
    padding: 0,
  }),

  switchCircle: (active) => ({
    width: "16px",
    height: "16px",
    borderRadius: "50%",
    background: "white",
    position: "absolute",
    top: "2px",
    left: active ? "24px" : "2px",
    transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
    boxShadow: "0 2px 4px rgba(0,0,0,0.3)",
  }),

  slider: {
    width: "100%",
    accentColor: "#aa3bff",
    marginTop: "12px",
    cursor: "pointer",
  },
};

// ─── GLOBAL CSS ──────────────────────────────────────────────────
const GlobalAnimations = () => (
  <style>{`
    body {
      margin: 0;
      background: #060913;
      overflow-x: hidden;
    }

    input:focus,
    select:focus {
      border-color: #aa3bff !important;
      box-shadow: 0 0 0 3px rgba(170,59,255,0.1);
    }

    .settings-content {
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 2rem;
    }

    .settings-sidebar {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    @media (max-width: 860px) {
      .settings-content {
        grid-template-columns: 1fr;
      }

      .settings-sidebar {
        flex-direction: row;
        overflow-x: auto;
      }
    }
  `}</style>
);

// ─── CONFIG FIELD ────────────────────────────────────────────────
const ConfigField = ({ param, paramKey, config, setConfig }) => {
  const rawValue = config[paramKey];

  // ✅ FIX PROFESIONAL
  const isPercentage = param.isPercentage === true;

  const isArray = param.type === "array" || Array.isArray(rawValue);

  const isSelect = param.type === "select";

  const isBoolean = param.type === "boolean" || typeof rawValue === "boolean";

  const isText = param.type === "text" || param.type === "string";

  const isNumeric = !isArray && !isSelect && !isText && !isBoolean;

  // ✅ FIX DISPLAY VALUE
  const displayValue = useMemo(() => {
    if (!isNumeric) return rawValue;

    if (isPercentage) {
      const numeric =
        typeof rawValue === "number" ? rawValue : parseFloat(rawValue);

      if (isNaN(numeric)) return 0;

      return Number((numeric * 100).toFixed(2));
    }

    return rawValue;
  }, [rawValue, isPercentage, isNumeric]);

  const [localValue, setLocalValue] = useState(displayValue);

  useEffect(() => {
    setLocalValue(displayValue);
  }, [displayValue]);

  const computedStep = useMemo(() => {
    // ✅ FIX %
    if (isPercentage) {
      return "0.1";
    }

    const metaStep = Number(param.step);

    if (param.step !== undefined && param.step !== null && metaStep >= 1) {
      return String(metaStep);
    }

    if (Number.isInteger(Number(rawValue))) {
      return "1";
    }

    return param.step ? String(param.step) : "1";
  }, [isPercentage, param.step, rawValue]);

  const toDisplayScale = useCallback(
    (val) => {
      if (val === undefined || val === null) return undefined;

      if (!isPercentage) return val;

      return Number(val) * 100;
    },
    [isPercentage],
  );

  // ✅ FIX TOTAL %
  const handleNumericCommit = useCallback(() => {
    if (localValue === "" || localValue === null) return;

    const sanitized = String(localValue).replace(",", ".");
    let num = parseFloat(sanitized);

    if (isNaN(num)) {
      setLocalValue(displayValue);
      return;
    }

    const minRaw = toDisplayScale(param.min);

    const maxRaw = toDisplayScale(param.max);

    if (minRaw !== undefined && num < minRaw) {
      num = minRaw;
    }

    if (maxRaw !== undefined && num > maxRaw) {
      num = maxRaw;
    }

    let finalVal;

    if (isPercentage) {
      // ✅ 60 -> 0.60
      finalVal = Number((num / 100).toFixed(6));
    } else if (Number(computedStep) >= 1) {
      finalVal = Math.round(num);
    } else {
      finalVal = Number(num.toFixed(8));
    }

    setLocalValue(isPercentage ? num : finalVal);

    setConfig((prev) => ({
      ...prev,
      [paramKey]: finalVal,
    }));
  }, [
    localValue,
    displayValue,
    isPercentage,
    param,
    paramKey,
    computedStep,
    setConfig,
    toDisplayScale,
  ]);

  // ─── ARRAY ──────────────────────────────────────────
  if (isArray) {
    const currentArray = Array.isArray(rawValue) ? rawValue : [];

    const togglePair = (pair) => {
      const next = currentArray.includes(pair)
        ? currentArray.filter((p) => p !== pair)
        : [...currentArray, pair];

      setConfig((prev) => ({
        ...prev,
        [paramKey]: next,
      }));
    };

    return (
      <div style={S.formGroup}>
        <label style={S.label}>{param.label}</label>

        <div style={S.presetContainer}>
          {PAIR_PRESETS.map((pair) => (
            <button
              key={pair}
              type="button"
              onClick={() => togglePair(pair)}
              style={S.presetBtn(currentArray.includes(pair))}
            >
              {pair}
            </button>
          ))}
        </div>
      </div>
    );
  }

  // ─── BOOLEAN (SWITCH) ──────────────────────────────
  if (isBoolean) {
    return (
      <div
        style={{
          ...S.formGroup,
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
          background: "rgba(255,255,255,0.02)",
          padding: "12px",
          borderRadius: "10px",
        }}
      >
        <div style={{ flex: 1, marginRight: "12px" }}>
          <label style={S.label}>{param.label}</label>
          <p style={S.desc}>{param.description}</p>
        </div>
        <button
          type="button"
          style={S.switch(!!rawValue)}
          onClick={() =>
            setConfig((prev) => ({ ...prev, [paramKey]: !rawValue }))
          }
        >
          <div style={S.switchCircle(!!rawValue)} />
        </button>
      </div>
    );
  }

  // ─── SELECT ─────────────────────────────────────────
  if (isSelect) {
    return (
      <div style={S.formGroup}>
        <label style={S.label}>{param.label}</label>

        <select
          value={rawValue || ""}
          onChange={(e) =>
            setConfig((prev) => ({
              ...prev,
              [paramKey]: e.target.value,
            }))
          }
          style={S.input}
        >
          {param.options?.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>
    );
  }

  // ─── TEXT ───────────────────────────────────────────
  if (isText) {
    return (
      <div style={S.formGroup}>
        <label style={S.label}>{param.label}</label>

        <input
          type="text"
          value={rawValue || ""}
          style={S.input}
          onChange={(e) =>
            setConfig((prev) => ({
              ...prev,
              [paramKey]: e.target.value,
            }))
          }
        />
      </div>
    );
  }

  // ─── NUMERIC ────────────────────────────────────────
  return (
    <div style={S.formGroup}>
      <div>
        <label style={S.label}>{param.label}</label>

        <p style={S.desc}>{param.description}</p>
      </div>

      <div style={S.inputWrapper}>
        <input
          type="number"
          step={computedStep}
          min={toDisplayScale(param.min)}
          max={toDisplayScale(param.max)}
          style={{
            ...S.input,
            paddingRight: param.unit ? "3rem" : "16px",
          }}
          value={localValue ?? ""}
          onChange={(e) => setLocalValue(e.target.value)}
          onBlur={handleNumericCommit}
          onKeyDown={(e) => e.key === "Enter" && handleNumericCommit()}
        />

        {param.unit && <span style={S.unit}>{param.unit}</span>}
      </div>

      {isPercentage && (
        <input
          type="range"
          min={toDisplayScale(param.min) || 0}
          max={toDisplayScale(param.max) || 100}
          step={computedStep}
          value={localValue ?? 0}
          onChange={(e) => {
            const val = e.target.value;
            setLocalValue(val);
            // Actualización reactiva para feedback visual inmediato
            const num = parseFloat(val);
            if (!isNaN(num)) {
              setConfig((prev) => ({
                ...prev,
                [paramKey]: Number((num / 100).toFixed(6)),
              }));
            }
          }}
          style={S.slider}
        />
      )}

      {param.min !== undefined && param.max !== undefined && (
        <span
          style={{
            fontSize: "0.72rem",
            color: "#334155",
          }}
        >
          Rango: {toDisplayScale(param.min)}
          {" - "}
          {toDisplayScale(param.max)}
          {param.unit || ""}
        </span>
      )}
    </div>
  );
};

// ─── MAIN VIEW ───────────────────────────────────────────────────
export default function SettingsView() {
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState(null);

  const [config, setConfig] = useState({});

  const [metadata, setMetadata] = useState({});

  useEffect(() => {
    (async () => {
      const [mRes, cRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/parameters`),
        fetch(`${API_BASE_URL}/api/config`),
      ]);

      const m = await mRes.json();
      const c = await cRes.json();

      setMetadata(m);
      setConfig(c);

      const firstTab = Object.values(m)[0]?.tab || "general";

      setActiveTab(firstTab);
    })();
  }, []);

  const tabs = useMemo(() => {
    const rawTabs = Object.values(metadata)
      .map((p) => p.tab)
      .filter(Boolean);

    return [...new Set(rawTabs)].sort(
      (a, b) => TAB_ORDER.indexOf(a) - TAB_ORDER.indexOf(b),
    );
  }, [metadata]);

  const activeParams = useMemo(() => {
    return Object.entries(metadata).filter(([, p]) => p.tab === activeTab);
  }, [metadata, activeTab]);

  const saveSettings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/config`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          JSON.stringify(errorData.detail || "Error desconocido"),
        );
      }

      alert("✅ Configuración guardada con éxito");
      navigate("/");
    } catch (err) {
      console.error("Error al guardar:", err);
      alert("❌ No se pudo guardar: " + err.message);
    }
  };

  return (
    <div style={S.root}>
      <GlobalAnimations />

      <div style={S.layout}>
        {/* HEADER */}
        <header style={S.header}>
          <button onClick={() => navigate("/")} style={{ ...S.btnPrimary }}>
            ← Volver al Terminal
          </button>
          <h2 style={S.title}>Configuración Mirage</h2>

          <button onClick={saveSettings} style={S.btnPrimary}>
            💾 Guardar
          </button>
        </header>

        {/* CONTENT */}
        <div className="settings-content">
          {/* SIDEBAR */}
          <nav className="settings-sidebar">
            {tabs.map((tab) => {
              const info = TAB_INFO[tab];

              const isActive = activeTab === tab;

              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  style={{
                    padding: "12px 16px",

                    border: `1px solid ${isActive ? "#aa3bff" : "#1e293b"}`,

                    borderRadius: "12px",

                    cursor: "pointer",

                    background: isActive ? "#aa3bff" : "rgba(255,255,255,0.03)",

                    color: isActive ? "white" : "#64748b",

                    fontWeight: "700",

                    textAlign: "left",
                  }}
                >
                  {info?.icon} {info?.label}
                </button>
              );
            })}
          </nav>

          {/* CARD */}
          <div style={S.card}>
            <div style={S.grid}>
              {activeParams.map(([key, param]) => (
                <ConfigField
                  key={key}
                  param={param}
                  paramKey={key}
                  config={config}
                  setConfig={setConfig}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
