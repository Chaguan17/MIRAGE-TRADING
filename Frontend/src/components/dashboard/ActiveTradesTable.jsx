import React, { useState } from "react";
import { STYLES } from "./styles";

export default function ActiveTradesTable({ operaciones_activas, livePrices, leverage }) {
  // Estado local para alternar la visualización del monto de la posición:
  // 'VALUE' = Valor total en $, 'MARGIN' = Margen ocupado, 'SIZE' = Cantidad de monedas
  const [posDisplayMode, setPosDisplayMode] = useState("VALUE");
  const [closingPair, setClosingPair] = useState(null);

  const formatPrice = (price) => {
    if (price === undefined || price === null) return "—";
    const num = parseFloat(price);
    if (isNaN(num)) return price;
    if (num === 0) return "0";
    if (num < 1) return num.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 6 });
    if (num < 10) return num.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
    if (num < 100) return num.toLocaleString("en-US", { minimumFractionDigits: 3, maximumFractionDigits: 4 });
    return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const getPositionText = (op, lev) => {
    if (!op) return "—";
    const posVal = op.position_value || (op.size && op.entry ? op.size * op.entry : 0);
    const levVal = lev || leverage || 10;

    if (posDisplayMode === "MARGIN") {
      const margin = posVal / levVal;
      return `$${margin.toFixed(2)}`;
    }
    if (posDisplayMode === "SIZE") {
      const coinSymbol = op.pair ? op.pair.replace("USDT", "") : "";
      return `${op.size ? op.size.toLocaleString("en-US", { maximumFractionDigits: 4 }) : "—"} ${coinSymbol}`;
    }
    // Default VALUE
    return `$${posVal.toFixed(2)}`;
  };

  const calculateProgressPct = (livePrice, entryPrice, tpPrice, slPrice, isLong) => {
    if (!livePrice || !entryPrice) return 50;
    if (!tpPrice || tpPrice === 0) return 50;

    const sl = slPrice > 0 ? slPrice : (isLong ? entryPrice * 0.98 : entryPrice * 1.02);
    const tp = tpPrice;

    if (isLong) {
      if (livePrice >= tp) return 100;
      if (livePrice <= sl) return 0;
      const totalRange = tp - sl;
      if (totalRange <= 0) return 50;
      const currentPos = livePrice - sl;
      return Math.min(100, Math.max(0, (currentPos / totalRange) * 100));
    } else {
      // SHORT
      if (livePrice <= tp) return 100;
      if (livePrice >= sl) return 0;
      const totalRange = sl - tp;
      if (totalRange <= 0) return 50;
      const currentPos = sl - livePrice;
      return Math.min(100, Math.max(0, (currentPos / totalRange) * 100));
    }
  };

  const handleClosePosition = async (pair) => {
    try {
      setClosingPair(pair);
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      await fetch(`${API_BASE_URL}/api/close_position/${pair}`, { method: "POST" });
    } catch (e) {
      console.error("Error closing position:", e);
    } finally {
      setTimeout(() => setClosingPair(null), 1000);
    }
  };

  return (
    <div style={{ ...STYLES.card, marginBottom: "1.5rem" }}>
      {/* ── Encabezado con Título y Switcher de Posición ── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <h3 style={{ ...STYLES.tableSectionTitle, marginBottom: 0 }}>
          Operaciones Activas en Mercado
        </h3>

        {/* Switcher interactivo: Valor / Margen / Cantidad */}
        <div
          style={{
            display: "inline-flex",
            background: "#060913",
            border: "1px solid #1e293b",
            borderRadius: "8px",
            padding: "2px",
            fontSize: "0.72rem",
            fontWeight: "700",
          }}
        >
          <button
            onClick={() => setPosDisplayMode("VALUE")}
            style={{
              background: posDisplayMode === "VALUE" ? "#aa3bff" : "transparent",
              color: posDisplayMode === "VALUE" ? "#ffffff" : "#64748b",
              border: "none",
              borderRadius: "6px",
              padding: "4px 10px",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
            title="Mostrar Valor Total de la Posición ($)"
          >
            $ Valor
          </button>
          <button
            onClick={() => setPosDisplayMode("MARGIN")}
            style={{
              background: posDisplayMode === "MARGIN" ? "#aa3bff" : "transparent",
              color: posDisplayMode === "MARGIN" ? "#ffffff" : "#64748b",
              border: "none",
              borderRadius: "6px",
              padding: "4px 10px",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
            title="Mostrar Margen USDT ocupado"
          >
            🛡️ Margen
          </button>
          <button
            onClick={() => setPosDisplayMode("SIZE")}
            style={{
              background: posDisplayMode === "SIZE" ? "#aa3bff" : "transparent",
              color: posDisplayMode === "SIZE" ? "#ffffff" : "#64748b",
              border: "none",
              borderRadius: "6px",
              padding: "4px 10px",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
            title="Mostrar Cantidad de Monedas"
          >
            📦 Cantidad
          </button>
        </div>
      </div>

      <div style={STYLES.tableResponsive}>
        <table style={STYLES.table}>
          <thead>
            <tr>
              <th style={STYLES.th()}>Activo</th>
              <th style={STYLES.th("center")}>Dirección</th>
              <th style={{ ...STYLES.th("right"), className: "col-hide-sm" }}>
                {posDisplayMode === "VALUE"
                  ? "Valor Posición"
                  : posDisplayMode === "MARGIN"
                  ? "Margen Usado"
                  : "Cantidad"}
              </th>
              <th style={STYLES.th("right")}>Precio Entrada</th>
              <th style={STYLES.th("right", "#aa3bff")}>Marca Actual</th>
              <th style={STYLES.th("center")} className="col-hide-sm">
                Progreso SL ➔ TP
              </th>
              <th style={STYLES.th("right")}>ROI / PnL Flotante</th>
              <th style={STYLES.th("center")}>Acción</th>
            </tr>
          </thead>
          <tbody>
            {!operaciones_activas?.length ? (
              <tr>
                <td colSpan="8" style={STYLES.td("center", "400", "#64748b")}>
                  No hay posiciones abiertas en este momento.
                </td>
              </tr>
            ) : (
              operaciones_activas.map((op, idx) => {
                const live = livePrices[op.pair] || op.current_price;
                const isLong = op.type === "LONG";
                const safeEntry = op.entry && op.entry > 0 ? op.entry : 1;
                const livePnl = (op.current_pnl !== undefined && op.current_pnl !== null)
                  ? parseFloat(op.current_pnl)
                  : parseFloat(
                      (
                        (live / safeEntry - 1) *
                        (isLong ? 1 : -1) *
                        (op.position_value || (op.size * op.entry) || 0)
                      ).toFixed(2)
                    ) || 0;
                const roiPct = parseFloat(
                  (
                    (live / safeEntry - 1) *
                    (isLong ? 1 : -1) *
                    100 *
                    (op.leverage || leverage || 10)
                  ).toFixed(2)
                ) || 0;

                const progressPct = calculateProgressPct(
                  live,
                  op.entry,
                  op.tp,
                  op.sl,
                  isLong
                );

                return (
                  <tr key={idx}>
                    <td style={STYLES.td("left", "700")}>
                      {op.pair}
                      {op.bullets > 1 && (
                        <span
                          style={{
                            fontSize: "0.65rem",
                            background: "rgba(170, 59, 255, 0.15)",
                            color: "#aa3bff",
                            padding: "3px 6px",
                            borderRadius: "8px",
                            marginLeft: "8px",
                            fontWeight: "800",
                            textTransform: "uppercase",
                          }}
                        >
                          DCA x{op.bullets}
                        </span>
                      )}
                    </td>
                    <td style={STYLES.td("center")}>
                      {/* Badge limpio de dirección sin porcentajes */}
                      <span style={STYLES.badge(op.type)}>{op.type}</span>
                    </td>
                    <td
                      style={STYLES.td("right", "400", "#f8fafc", true)}
                      className="col-hide-sm"
                    >
                      {getPositionText(op, leverage)}
                    </td>
                    <td style={STYLES.td("right", "400", "#f8fafc", true)}>
                      {formatPrice(op.entry)}
                    </td>
                    <td style={STYLES.td("right", "700", "#aa3bff", true)}>
                      {formatPrice(live)}
                    </td>
                    <td
                      style={{
                        ...STYLES.td("center"),
                        minWidth: "150px",
                      }}
                      className="col-hide-sm"
                    >
                      {/* Barra de progreso SL ➔ Precio Actual ➔ TP */}
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "4px",
                          alignItems: "center",
                        }}
                      >
                        <div
                          style={{
                            width: "100%",
                            height: "6px",
                            background: "#1e293b",
                            borderRadius: "3px",
                            overflow: "hidden",
                            position: "relative",
                          }}
                        >
                          <div
                            style={{
                              width: `${progressPct}%`,
                              height: "100%",
                              background:
                                livePnl >= 0
                                  ? "linear-gradient(90deg, #3b82f6, #00ffaa)"
                                  : "linear-gradient(90deg, #ff3b69, #f59e0b)",
                              borderRadius: "3px",
                              transition: "width 0.3s ease",
                            }}
                          />
                        </div>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            width: "100%",
                            fontSize: "0.65rem",
                            color: "#64748b",
                            fontFamily: "JetBrains Mono, monospace",
                          }}
                        >
                          <span style={{ color: op.is_trailing ? "#f59e0b" : "#ff3b69" }}>
                            SL: {op.sl === 0 ? "—" : formatPrice(op.sl)}
                            {op.is_breakeven && (
                              <span style={STYLES.specialBadge("#00ffaa")}>BE</span>
                            )}
                            {op.is_trailing && (
                              <span style={STYLES.specialBadge("#f59e0b")}>TR</span>
                            )}
                          </span>
                          <span style={{ color: "#00ffaa" }}>
                            TP: {op.tp === 0 ? "—" : formatPrice(op.tp)}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td style={STYLES.td("right")}>
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "flex-end",
                          gap: "2px",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: "JetBrains Mono, monospace",
                            fontWeight: "700",
                            fontSize: "0.85rem",
                            color: livePnl >= 0 ? "#00ffaa" : "#ff3b69",
                          }}
                        >
                          {livePnl >= 0 ? "+" : ""}
                          {livePnl} USDT
                        </span>
                        <span
                          style={{
                            fontFamily: "JetBrains Mono, monospace",
                            fontSize: "0.72rem",
                            fontWeight: "600",
                            color: roiPct >= 0 ? "rgba(0, 255, 170, 0.8)" : "rgba(255, 59, 105, 0.8)",
                          }}
                        >
                          ({roiPct >= 0 ? "+" : ""}
                          {roiPct}%)
                        </span>
                      </div>
                    </td>
                    <td style={STYLES.td("center")}>
                      <button
                        onClick={() => handleClosePosition(op.pair)}
                        disabled={closingPair === op.pair}
                        style={{
                          background: "rgba(239, 68, 68, 0.15)",
                          border: "1px solid rgba(239, 68, 68, 0.4)",
                          color: "#f87171",
                          borderRadius: "6px",
                          padding: "4px 10px",
                          fontSize: "0.72rem",
                          fontWeight: "700",
                          cursor: closingPair === op.pair ? "wait" : "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title={`Cerrar / Limpiar posición en ${op.pair}`}
                      >
                        {closingPair === op.pair ? "..." : "✕ Cerrar"}
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
