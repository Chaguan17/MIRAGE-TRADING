import React from "react";
import { STYLES } from "./styles";

export default function KPIGrid({ data, liveTotalPnL }) {
  const kpis = [
    {
      label: "Net PnL Global (Live)",
      value: `${liveTotalPnL >= 0 ? "+" : ""}${liveTotalPnL.toFixed(2)}`,
      unit: "USDT",
      color: liveTotalPnL >= 0 ? "#00ffaa" : "#ff3b69",
    },
    {
      label: "Balance Cuenta",
      value: data.balance_actual
        ? `${data.balance_actual.toFixed(2)}`
        : "—",
      unit: "USDT",
      color:
        data.balance_actual >= data.balance_inicial
          ? "#00ffaa"
          : "#ff3b69",
    },
    {
      label: "Balance Binance Real",
      value:
        data.balance_real !== undefined && data.balance_real > 0
          ? data.balance_real.toFixed(2)
          : "0.00",
      unit: data.balance_real > 0 ? "USDT" : "",
      color: "#f59e0b",
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
  ];

  return (
    <div style={STYLES.kpiGrid}>
      {kpis.map((kpi, idx) => (
        <div key={idx} style={STYLES.card}>
          <h4 style={STYLES.kpiLabel}>{kpi.label}</h4>
          <div style={STYLES.kpiValueBox}>
            <h2 style={STYLES.kpiValue(kpi.color)}>{kpi.value}</h2>
            <span style={STYLES.kpiUnit}>{kpi.unit}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
