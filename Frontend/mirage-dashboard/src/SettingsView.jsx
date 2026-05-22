import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const ConfigField = ({ param, paramKey, config, setConfig }) => {
  const value = config[paramKey];
  const isPercentage = param.unit === "%";

  // Sinergia: Si es porcentaje, convertimos 0.02 -> 2 para el usuario
  const displayValue = useMemo(() => {
    if (isPercentage && typeof value === "number" && value <= 1.0) {
      // Solo multiplicamos si parece ser un decimal (evita re-multiplicar si ya es entero)
      return parseFloat((value * 100).toFixed(2));
    }
    return value;
  }, [value, isPercentage]);

  const [localValue, setLocalValue] = useState(displayValue);

  // Sincronizar solo cuando el valor externo cambie drásticamente (ej: carga inicial)
  useEffect(() => {
    setLocalValue(displayValue);
  }, [displayValue]);

  const handleCommit = () => {
    if (localValue === "" || localValue === null) return;
    
    let numericVal = parseFloat(localValue);
    if (isNaN(numericVal)) {
      setLocalValue(displayValue);
      return;
    }

    // Si es porcentaje, guardamos como decimal para el backend (2 -> 0.02)
    const finalVal = isPercentage ? numericVal / 100 : numericVal;
    
    setConfig((prev) => ({ ...prev, [paramKey]: finalVal }));
  };

  if (param.type === "array" || Array.isArray(value)) {
    const currentArray = Array.isArray(value) ? value : [];
    const commonPairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"];
    const allDisplayPairs = Array.from(new Set([...commonPairs, ...currentArray]));

    const togglePair = (pair) => {
      const next = currentArray.includes(pair) 
        ? currentArray.filter((p) => p !== pair) 
        : [...currentArray, pair];
      setConfig((prev) => ({ ...prev, [paramKey]: next }));
    };

    return (
      <div className="form-group full-width">
        <div className="field-info">
          <label>{param.label || "Pares Activos"}</label>
          <p>{param.description}</p>
        </div>
        <div className="field-control">
          <div className="tags-selector">
            {allDisplayPairs.map((pair) => (
              <button
                key={pair}
                onClick={() => togglePair(pair)}
                className={`tag-btn ${currentArray.includes(pair) ? "active" : ""}`}
              >
                {pair}
              </button>
            ))}
          </div>
          <input
            type="text"
            className="minimal-input mt-2"
            placeholder="Añadir par manual + Enter"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const val = e.currentTarget.value.trim().toUpperCase();
                if (val && !currentArray.includes(val)) togglePair(val);
                e.currentTarget.value = "";
              }
            }}
          />
        </div>
      </div>
    );
  }

  if (param.type === "select") {
    return (
      <div className="form-group">
        <div className="field-info">
          <label>{param.label}</label>
          <p>{param.description}</p>
        </div>
        <div className="field-control">
          <select
            value={value}
            onChange={(e) => setConfig((prev) => ({ ...prev, [paramKey]: e.target.value }))}
            className="form-select"
          >
            {param.options.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
      </div>
    );
  }

  return (
    <div className="form-group">
      <div className="field-info">
        <label>{param.label}</label>
        <p>{param.description}</p>
      </div>
      <div className="field-control">
        <div className="input-wrapper">
          <input
            type="text"
            className="form-input"
            value={localValue ?? ""}
            onChange={(e) => setLocalValue(e.target.value)}
            onBlur={handleCommit}
          />
          {param.unit && <span className="input-unit">{param.unit}</span>}
        </div>
      </div>
    </div>
  );
};

export default function SettingsView() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [config, setConfig] = useState({});
  const [parametersMetadata, setParametersMetadata] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [mRes, cRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/parameters`),
          fetch(`${API_BASE_URL}/api/config`),
        ]);
        const metadata = await mRes.json();
        const configData = await cRes.json();
        setParametersMetadata(metadata);
        setConfig(configData || {});
        setActiveTab(Object.values(metadata)[0]?.tab || "general");
        setLoading(false);
      } catch (err) {
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
      navigate("/");
    } catch (error) {
      alert("Error al guardar.");
    } finally { setIsSaving(false); }
  };

  if (loading) return <div className="loading-container"><div className="spinner" /></div>;

  const tabInfo = {
    general: { label: "Cuenta", icon: "🏦" },
    market: { label: "Mercado", icon: "📊" },
    risk: { label: "Riesgo", icon: "🛡️" },
    execution: { label: "Ejecución", icon: "⚡" },
    strategy: { label: "Motor IA", icon: "🧠" },
  };

  const tabs = [...new Set(Object.values(parametersMetadata).map((p) => p.tab))].sort((a, b) => {
    const order = ["general", "market", "risk", "execution", "strategy"];
    return order.indexOf(a) - order.indexOf(b);
  });

  return (
    <div className="settings-layout animate-fade-in">
      <div className="settings-header">
        <div><button onClick={() => navigate("/")} className="back-link">← Volver</button><h2 className="settings-title">Configuración Mirage</h2></div>
        <button onClick={saveSettings} disabled={isSaving} className="btn-primary">{isSaving ? "Guardando..." : "💾 Guardar Ajustes"}</button>
      </div>
      <div className="settings-content">
        <div className="tabs-sidebar">
          {tabs.map((tab) => (
            <button key={tab} onClick={() => setActiveTab(tab)} className={`tab-button ${activeTab === tab ? "active" : ""}`}>
              <span style={{marginRight: '10px'}}>{tabInfo[tab]?.icon || "⚙️"}</span>
              {tabInfo[tab]?.label || tab.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="card settings-card-body">
          <div className="settings-grid">{Object.entries(parametersMetadata).filter(([_, p]) => p.tab === activeTab).map(([key, p]) => (<ConfigField key={key} param={p} paramKey={key} config={config} setConfig={setConfig} />))}</div>
        </div>
      </div>
    </div>
  );
}