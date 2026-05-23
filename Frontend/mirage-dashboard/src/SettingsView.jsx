import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// ─── Tab metadata ─────────────────────────────────────────────────────────────
const TAB_INFO = {
  general:         { label: "Cuenta",              icon: "🏦" },
  market:          { label: "Mercado",             icon: "📊" },
  risk:            { label: "Riesgo",              icon: "🛡️" },
  risk_management: { label: "Riesgo",              icon: "🛡️" },
  execution:       { label: "Ejecución (SL/TP)",   icon: "⚡" },
  strategy:        { label: "Motor IA",            icon: "🧠" },
};
const TAB_ORDER = ["general", "market", "risk", "risk_management", "execution", "strategy"];

// ─── Styles ───────────────────────────────────────────────────────────────────
const S = {
  root: {
    backgroundColor: "#060913",  // FIX: antes faltaba, dependía del body
    minHeight: "100vh",
  },
  layout: {
    padding: "0 1.5rem 3rem",
    maxWidth: "1200px",
    margin: "0 auto",
    color: "#f8fafc",
    fontFamily: "Inter, system-ui, sans-serif",
    boxSizing: "border-box",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingTop: "1.5rem",
    paddingBottom: "1.5rem",
    borderBottom: "1px solid #1e293b",
    marginBottom: "2rem",
    flexWrap: "wrap",  // FIX: responsivo
    gap: "1rem",
  },
  headerLeft: { display: "flex", flexDirection: "column", gap: "4px" },
  backLink: {
    background: "none",
    border: "none",
    color: "#64748b",
    fontWeight: "600",
    fontSize: "0.85rem",
    cursor: "pointer",
    padding: 0,
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    transition: "color 0.2s",
  },
  title: {
    fontSize: "clamp(1.25rem, 4vw, 1.75rem)",  // FIX: responsivo
    fontWeight: "800",
    margin: 0,
    letterSpacing: "-0.5px",
  },
  headerActions: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    flexWrap: "wrap",
  },
  unsavedBadge: {
    fontSize: "0.72rem",
    fontWeight: "700",
    color: "#f59e0b",
    background: "rgba(245, 158, 11, 0.1)",
    border: "1px solid rgba(245, 158, 11, 0.2)",
    padding: "4px 10px",
    borderRadius: "20px",
    whiteSpace: "nowrap",
  },
  btnPrimary: {
    background: "linear-gradient(135deg, #aa3bff, #8b25e0)",
    color: "white",
    border: "none",
    padding: "11px 24px",
    borderRadius: "10px",
    fontWeight: "700",
    fontSize: "0.9rem",
    cursor: "pointer",
    transition: "all 0.2s",
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    whiteSpace: "nowrap",
    boxShadow: "0 4px 15px rgba(170, 59, 255, 0.25)",
  },
  btnDisabled: {
    opacity: 0.6,
    cursor: "not-allowed",
    pointerEvents: "none",
  },
  card: {
    background: "#0b1120",
    padding: "2rem",
    borderRadius: "20px",
    border: "1px solid #1e293b",
    boxShadow: "0 10px 25px -5px rgba(0,0,0,0.3)",
    minWidth: 0,  // FIX: evita que el grid se desborde
  },
  grid: {
    display: "grid",
    // FIX: min(100%, 300px) evita desbordamiento en móvil
    gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 300px), 1fr))",
    gap: "2rem",
    alignItems: "start",
  },
  formGroup: (full) => ({
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    gridColumn: full ? "1 / -1" : "auto",
  }),
  label: {
    fontWeight: "700",
    fontSize: "0.9rem",
    color: "#f8fafc",
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  desc: {
    fontSize: "0.78rem",
    color: "#64748b",
    margin: "2px 0 0",
    lineHeight: "1.5",
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
    transition: "border-color 0.2s",
    boxSizing: "border-box",
  },
  tagContainer: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    padding: "12px",
    background: "#060913",
    borderRadius: "12px",
    border: "1px solid #1e293b",
    minHeight: "52px",
  },
  tag: (active) => ({
    padding: "6px 13px",
    borderRadius: "20px",
    cursor: "pointer",
    fontSize: "0.78rem",
    fontWeight: "700",
    transition: "all 0.18s",
    background: active ? "#aa3bff" : "rgba(255,255,255,0.04)",
    color: active ? "white" : "#64748b",
    border: `1px solid ${active ? "#aa3bff" : "#1e293b"}`,
    userSelect: "none",
  }),
  addPairRow: {
    display: "flex",
    gap: "8px",
    marginTop: "4px",
  },
  addPairInput: {
    flex: 1,
    background: "#121b2e",
    border: "1px solid #334155",
    color: "white",
    padding: "9px 14px",
    borderRadius: "8px",
    fontSize: "0.85rem",
    outline: "none",
    fontFamily: "JetBrains Mono, monospace",
    boxSizing: "border-box",
    maxWidth: "280px",
  },
  addPairBtn: {
    background: "rgba(170,59,255,0.12)",
    border: "1px solid rgba(170,59,255,0.25)",
    color: "#aa3bff",
    padding: "9px 16px",
    borderRadius: "8px",
    fontWeight: "700",
    fontSize: "0.82rem",
    cursor: "pointer",
    whiteSpace: "nowrap",
    transition: "all 0.2s",
  },
  inputWrapper: {
    position: "relative",
    display: "flex",
    alignItems: "center",
  },
  unit: {
    position: "absolute",
    right: "14px",
    color: "#aa3bff",
    fontWeight: "700",
    pointerEvents: "none",
    fontSize: "0.82rem",
  },
  emptyState: {
    textAlign: "center",
    padding: "3rem 1rem",
    color: "#334155",
  },
  emptyIcon: { fontSize: "2rem", marginBottom: "8px" },
  emptyText: { fontSize: "0.9rem", color: "#475569", margin: 0 },

  // Toast
  toast: (type) => ({
    position: "fixed",
    bottom: "24px",
    right: "24px",
    background: type === "success" ? "#0f2a1e" : "#2a0f0f",
    border: `1px solid ${type === "success" ? "#00ffaa" : "#ff3b69"}`,
    color: type === "success" ? "#00ffaa" : "#ff3b69",
    padding: "14px 20px",
    borderRadius: "12px",
    fontWeight: "700",
    fontSize: "0.875rem",
    boxShadow: "0 8px 25px rgba(0,0,0,0.4)",
    zIndex: 9999,
    display: "flex",
    alignItems: "center",
    gap: "10px",
    animation: "slideUp 0.3s ease-out",
    maxWidth: "calc(100vw - 48px)",
  }),
};

// ─── GlobalAnimations (FIX: loading-container definido + CSS responsivo) ──────
const GlobalAnimations = () => (
  <style>{`
    :root { --bg-card: #0b1120; --text-muted: #64748b; }
    *, *::before, *::after { box-sizing: border-box; }
    body { margin: 0; padding: 0; background-color: #060913; overflow-x: hidden; -webkit-font-smoothing: antialiased; }
    @keyframes spin    { to { transform: rotate(360deg); } }
    @keyframes fadeIn  { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    .animate-spin    { animation: spin 1s linear infinite; }
    .animate-fade-in { animation: fadeIn 0.4s ease-out; }
    .spinner {
      width: 40px; height: 40px;
      border: 4px solid rgba(170, 59, 255, 0.1);
      border-top-color: #aa3bff; border-radius: 50%;
    }

    /* FIX: loading-container nunca estaba definido → loading invisible */
    .loading-container {
      height: 100vh; display: flex; flex-direction: column;
      justify-content: center; align-items: center;
      background-color: #060913;
    }

    /* ── Layout principal responsivo ── */
    /* FIX: content era "240px 1fr" fijo → se rompía en tablet/móvil */
    .settings-content {
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 2rem;
      align-items: start;
    }

    /* FIX: sidebar sticky necesita que el padre tenga overflow visible y el hijo height */
    .settings-sidebar {
      display: flex;
      flex-direction: column;
      gap: 6px;
      position: sticky;
      top: 24px;
    }

    /* En tablet: sidebar horizontal scrollable encima del contenido */
    @media (max-width: 860px) {
      .settings-content {
        grid-template-columns: 1fr !important;
      }
      .settings-sidebar {
        position: static !important;
        flex-direction: row !important;
        overflow-x: auto;
        padding-bottom: 4px;
        gap: 8px;
        scrollbar-width: none;
      }
      .settings-sidebar::-webkit-scrollbar { display: none; }
      .settings-tab-btn {
        flex-shrink: 0;
        white-space: nowrap;
      }
    }

    /* Hover en inputs */
    input:hover, select:hover { border-color: #475569 !important; }
    input:focus, select:focus { border-color: #aa3bff !important; box-shadow: 0 0 0 3px rgba(170,59,255,0.1); }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
  `}</style>
);

// ─── Toast Component ──────────────────────────────────────────────────────────
const Toast = ({ message, type, onClose }) => {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);

  return (
    <div style={S.toast(type)}>
      <span>{type === "success" ? "✓" : "✕"}</span>
      {message}
    </div>
  );
};

// ─── ConfigField ──────────────────────────────────────────────────────────────
// FIX CRÍTICO: los hooks useState/useMemo estaban después de returns condicionales
// → violación de Rules of Hooks → "Rendered fewer hooks than expected"
// Solución: todos los hooks van AL INICIO, antes de cualquier return.
const ConfigField = ({ param, paramKey, config, setConfig }) => {
  const rawValue    = config[paramKey];
  const isPercentage = param.unit === "%";
  const isArray     = param.type === "array" || Array.isArray(rawValue) || paramKey === "PARES_ACTIVOS";
  const isSelect    = param.type === "select";
  const isText      = param.type === "text" || param.type === "string";
  const isNumeric   = !isArray && !isSelect && !isText;

  // ── Hooks siempre al inicio (sin condición) ──
  const [addPairInput, setAddPairInput] = useState("");

  const displayValue = useMemo(() => {
    if (!isNumeric) return rawValue;
    if (isPercentage && typeof rawValue === "number" && rawValue <= 1.0) {
      return parseFloat((rawValue * 100).toFixed(2));
    }
    return rawValue;
  }, [rawValue, isPercentage, isNumeric]);

  const [localValue, setLocalValue] = useState(displayValue);

  useEffect(() => {
    if (isNumeric) setLocalValue(displayValue);
  }, [displayValue, isNumeric]);

  const handleNumericCommit = useCallback(() => {
    if (localValue === "" || localValue === null) return;
    let num = parseFloat(localValue);
    if (isNaN(num)) { setLocalValue(displayValue); return; }

    const minRaw = isPercentage ? param.min * 100 : param.min;
    const maxRaw = isPercentage ? param.max * 100 : param.max;
    if (param.min !== undefined && num < minRaw) num = minRaw;
    if (param.max !== undefined && num > maxRaw) num = maxRaw;

    const finalVal = isPercentage ? parseFloat((num / 100).toFixed(4)) : num;
    setLocalValue(isPercentage ? num : finalVal);
    setConfig((prev) => ({ ...prev, [paramKey]: finalVal }));
  }, [localValue, displayValue, isPercentage, param, paramKey, setConfig]);

  // ── Render según tipo ──

  // 1. ARRAY — lista de pares activos
  if (isArray) {
    const currentArray = Array.isArray(rawValue) ? rawValue : [];

    const togglePair = (pair) => {
      const next = currentArray.includes(pair)
        ? currentArray.filter((p) => p !== pair)
        : [...currentArray, pair];
      setConfig((prev) => ({ ...prev, [paramKey]: next }));
    };

    const handleAddPair = () => {
      const val = addPairInput.trim().toUpperCase();
      if (val && !currentArray.includes(val)) togglePair(val);
      setAddPairInput("");
    };

    return (
      <div style={S.formGroup(true)}>
        <div>
          <label style={S.label}>{param.label || "Pares Activos"}</label>
          <p style={S.desc}>{param.description || "Activos sobre los cuales el algoritmo ejecutará órdenes."}</p>
        </div>
        <div style={S.tagContainer}>
          {currentArray.length === 0 && (
            <span style={{ color: "#334155", fontSize: "0.8rem", padding: "4px" }}>
              Ningún par seleccionado
            </span>
          )}
          {currentArray.map((pair) => (
            <button key={pair} type="button" onClick={() => togglePair(pair)} style={S.tag(true)}
              title="Click para quitar">
              ✓ {pair}
            </button>
          ))}
        </div>
        {/* FIX UX: botón explícito "Añadir" en lugar de solo Enter */}
        <div style={S.addPairRow}>
          <input
            type="text"
            style={S.addPairInput}
            placeholder="Ej: SOLUSDT"
            value={addPairInput}
            onChange={(e) => setAddPairInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleAddPair(); } }}
          />
          <button type="button" onClick={handleAddPair} style={S.addPairBtn}>
            + Añadir
          </button>
        </div>
      </div>
    );
  }

  // 2. SELECT
  if (isSelect) {
    return (
      <div style={S.formGroup(false)}>
        <div>
          <label style={S.label}>{param.label}</label>
          <p style={S.desc}>{param.description}</p>
        </div>
        <select
          value={rawValue || ""}
          onChange={(e) => setConfig((prev) => ({ ...prev, [paramKey]: e.target.value }))}
          style={S.input}
        >
          {param.options?.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </div>
    );
  }

  // 3. TEXT / STRING
  if (isText) {
    return (
      <div style={S.formGroup(false)}>
        <div>
          <label style={S.label}>{param.label}</label>
          <p style={S.desc}>{param.description}</p>
        </div>
        <input
          type="text"
          style={S.input}
          value={rawValue || ""}
          onChange={(e) => setConfig((prev) => ({ ...prev, [paramKey]: e.target.value }))}
        />
      </div>
    );
  }

  // 4. NUMERIC
  return (
    <div style={S.formGroup(false)}>
      <div>
        <label style={S.label}>{param.label}</label>
        <p style={S.desc}>{param.description}</p>
      </div>
      <div style={S.inputWrapper}>
        <input
          type="number"
          step={isPercentage ? "0.01" : param.step || "1"}
          min={isPercentage && param.min !== undefined ? param.min * 100 : param.min}
          max={isPercentage && param.max !== undefined ? param.max * 100 : param.max}
          style={{ ...S.input, paddingRight: param.unit ? "3rem" : "16px" }}
          value={localValue ?? ""}
          onChange={(e) => setLocalValue(e.target.value)}
          onBlur={handleNumericCommit}
          onKeyDown={(e) => e.key === "Enter" && handleNumericCommit()}
        />
        {param.unit && <span style={S.unit}>{param.unit}</span>}
      </div>
      {param.min !== undefined && param.max !== undefined && (
        <span style={{ fontSize: "0.72rem", color: "#334155" }}>
          Rango: {isPercentage ? param.min * 100 : param.min} – {isPercentage ? param.max * 100 : param.max}{param.unit || ""}
        </span>
      )}
    </div>
  );
};

// ─── SettingsView ─────────────────────────────────────────────────────────────
export default function SettingsView() {
  const navigate = useNavigate();
  const [activeTab,           setActiveTab]           = useState(null);
  const [isSaving,            setIsSaving]            = useState(false);
  const [config,              setConfig]              = useState({});
  const [originalConfig,      setOriginalConfig]      = useState({});  // para detectar cambios
  const [parametersMetadata,  setParametersMetadata]  = useState({});
  const [loading,             setLoading]             = useState(true);
  const [toast,               setToast]               = useState(null); // { message, type }

  const hasUnsavedChanges = useMemo(
    () => JSON.stringify(config) !== JSON.stringify(originalConfig),
    [config, originalConfig]
  );

  useEffect(() => {
    (async () => {
      try {
        const [mRes, cRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/parameters`),
          fetch(`${API_BASE_URL}/api/config`),
        ]);
        const metadata   = await mRes.json();
        const configData = await cRes.json();

        setParametersMetadata(metadata);
        setConfig(configData || {});
        setOriginalConfig(configData || {});  // guardar copia base

        const firstTab = Object.values(metadata)[0]?.tab?.toLowerCase() || "general";
        setActiveTab(firstTab);
      } catch (_) {
        setToast({ message: "Error cargando configuración.", type: "error" });
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const saveSettings = async () => {
    setIsSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!res.ok) throw new Error("Server error");
      setOriginalConfig({ ...config });
      setToast({ message: "Configuración guardada correctamente.", type: "success" });
      // Pequeña pausa para que el usuario vea el toast antes de navegar
      setTimeout(() => navigate("/"), 1400);
    } catch (_) {
      setToast({ message: "Error al guardar la configuración.", type: "error" });
    } finally {
      setIsSaving(false);
    }
  };

  const tabs = useMemo(() => {
    const rawTabs = Object.values(parametersMetadata)
      .map((p) => p.tab?.toLowerCase())
      .filter(Boolean);
    return [...new Set(rawTabs)].sort(
      (a, b) => TAB_ORDER.indexOf(a) - TAB_ORDER.indexOf(b)
    );
  }, [parametersMetadata]);

  // Cuenta parámetros por tab para el badge
  const tabCounts = useMemo(() => {
    const counts = {};
    Object.values(parametersMetadata).forEach((p) => {
      const t = p.tab?.toLowerCase();
      if (t) counts[t] = (counts[t] || 0) + 1;
    });
    return counts;
  }, [parametersMetadata]);

  const activeParams = useMemo(
    () => Object.entries(parametersMetadata).filter(([, p]) => p.tab?.toLowerCase() === activeTab),
    [parametersMetadata, activeTab]
  );

  if (loading)
    return (
      <div className="loading-container">
        <GlobalAnimations />
        <div className="animate-spin spinner" />
      </div>
    );

  return (
    <div style={S.root}>
      <GlobalAnimations />
      <div style={S.layout} className="animate-fade-in">

        {/* ── Header ── */}
        <header style={S.header}>
          <div style={S.headerLeft}>
            <button onClick={() => navigate("/")} style={S.backLink}>
              ← Volver al Terminal
            </button>
            <h2 style={S.title}>Configuración Mirage</h2>
          </div>
          <div style={S.headerActions}>
            {/* Indicador de cambios sin guardar */}
            {hasUnsavedChanges && (
              <span style={S.unsavedBadge}>● Cambios sin guardar</span>
            )}
            <button
              onClick={saveSettings}
              disabled={isSaving || !hasUnsavedChanges}
              style={{
                ...S.btnPrimary,
                ...(isSaving || !hasUnsavedChanges ? S.btnDisabled : {}),
              }}
            >
              {isSaving ? (
                <>
                  <span style={{ display: "inline-block", width: "14px", height: "14px",
                    border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "white",
                    borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
                  Guardando...
                </>
              ) : (
                <>💾 Guardar Ajustes</>
              )}
            </button>
          </div>
        </header>

        {/* ── Content: Sidebar + Card ── */}
        {/* FIX: clase CSS maneja la responsividad; en móvil: tabs horizontales */}
        <div className="settings-content">

          {/* Sidebar / tab bar */}
          <nav className="settings-sidebar">
            {tabs.map((tab) => {
              const info    = TAB_INFO[tab];
              const isActive = activeTab === tab;
              const count   = tabCounts[tab] || 0;
              return (
                <button
                  key={tab}
                  className="settings-tab-btn"
                  onClick={() => setActiveTab(tab)}
                  style={{
                    padding: "12px 16px",
                    border: `1px solid ${isActive ? "#aa3bff" : "#1e293b"}`,
                    borderRadius: "12px",
                    cursor: "pointer",
                    textAlign: "left",
                    fontWeight: "600",
                    fontSize: "0.875rem",
                    transition: "all 0.2s",
                    background: isActive ? "#aa3bff" : "rgba(255,255,255,0.03)",
                    color: isActive ? "white" : "#64748b",
                    boxShadow: isActive ? "0 4px 15px rgba(170, 59, 255, 0.3)" : "none",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    justifyContent: "space-between",
                    whiteSpace: "nowrap",
                  }}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "15px" }}>{info?.icon || "⚙️"}</span>
                    {info?.label || tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </span>
                  {/* Contador de parámetros por tab */}
                  <span style={{
                    fontSize: "0.65rem",
                    fontWeight: "800",
                    background: isActive ? "rgba(255,255,255,0.2)" : "#1e293b",
                    color: isActive ? "white" : "#475569",
                    padding: "2px 7px",
                    borderRadius: "10px",
                    minWidth: "22px",
                    textAlign: "center",
                  }}>
                    {count}
                  </span>
                </button>
              );
            })}
          </nav>

          {/* Formulario */}
          <div style={S.card}>
            {activeParams.length === 0 ? (
              <div style={S.emptyState}>
                <div style={S.emptyIcon}>⚙️</div>
                <p style={S.emptyText}>No hay parámetros configurables en esta sección.</p>
              </div>
            ) : (
              <div style={S.grid}>
                {activeParams.map(([key, p]) => (
                  <ConfigField
                    key={key}
                    param={p}
                    paramKey={key}
                    config={config}
                    setConfig={setConfig}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Toast de notificación */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}