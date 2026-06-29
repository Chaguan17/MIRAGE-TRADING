import React from "react";
import { STYLES } from "./styles";

export default function HistoryTable({ 
  historyFilter, 
  setHistoryFilter, 
  availablePairs, 
  historyLimit, 
  setHistoryLimit, 
  filteredHistory 
}) {
  const formatPrice = (price) => {
    if (price === undefined || price === null) return "—";
    const num = parseFloat(price);
    if (isNaN(num)) return price;
    if (num === 0) return "0";
    if (num >= 1) return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return num.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 6 });
  };

  return (
    <div style={STYLES.card}>
      <div style={STYLES.chartHeader}>
        <h3 style={STYLES.chartTitle}>Historial de Ejecución</h3>
        <div style={STYLES.filterRow}>
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
              <th style={{ ...STYLES.th("right") }} className="col-hide-sm">
                Salida
              </th>
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
                  <td style={STYLES.td("left", "400", "#64748b")}>
                    {op.timestamp}
                  </td>
                  <td style={STYLES.td("left", "700")}>{op.pair}</td>
                  <td style={STYLES.td()}>
                    <span style={STYLES.badge(op.action)}>{op.action}</span>
                  </td>
                  <td style={STYLES.td("right", "400", "#f8fafc", true)}>
                    {formatPrice(op.entry_price)}
                  </td>
                  <td
                    style={STYLES.td("right", "400", "#f8fafc", true)}
                    className="col-hide-sm"
                  >
                    {formatPrice(op.close_price)}
                  </td>
                  <td
                    style={STYLES.td(
                      "right",
                      "700",
                      op.pnl_usdt >= 0 ? "#00ffaa" : "#ff3b69",
                      true,
                    )}
                  >
                    {op.pnl_usdt >= 0 ? "+" : ""}
                    {op.pnl_usdt} USDT
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
