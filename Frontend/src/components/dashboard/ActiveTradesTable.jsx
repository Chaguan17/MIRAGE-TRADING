import React from "react";
import { STYLES } from "./styles";

export default function ActiveTradesTable({ operaciones_activas, livePrices }) {
  const formatPrice = (price) => {
    if (price === undefined || price === null) return "—";
    const num = parseFloat(price);
    if (isNaN(num)) return price;
    if (num === 0) return "0";
    if (num >= 1) return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return num.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 6 });
  };

  return (
    <div style={{ ...STYLES.card, marginBottom: "1.5rem" }}>
      <h3 style={STYLES.tableSectionTitle}>Operaciones Activas en Mercado</h3>
      <div style={STYLES.tableResponsive}>
        <table style={STYLES.table}>
          <thead>
            <tr>
              <th style={STYLES.th()}>Activo</th>
              <th style={STYLES.th("center")}>Dirección</th>
              <th
                style={{
                  ...STYLES.th("right"),
                  ...{ className: "col-hide-sm" },
                }}
              >
                Monto
              </th>
              <th style={STYLES.th("right")}>Precio Entrada</th>
              <th style={STYLES.th("right", "#aa3bff")}>Marca Actual</th>
              <th
                style={{ ...STYLES.th("right", "#00ffaa") }}
                className="col-hide-sm"
              >
                Take Profit
              </th>
              <th
                style={{ ...STYLES.th("right", "#ff3b69") }}
                className="col-hide-sm"
              >
                Stop Loss
              </th>
              <th style={STYLES.th("right")}>ROI</th>
              <th style={STYLES.th("right")}>PnL Flotante</th>
            </tr>
          </thead>
          <tbody>
            {!operaciones_activas?.length ? (
              <tr>
                <td colSpan="9" style={STYLES.td("center", "400", "#64748b")}>
                  No hay posiciones abiertas en este momento.
                </td>
              </tr>
            ) : (
              operaciones_activas.map((op, idx) => {
                const live = livePrices[op.pair] || op.current_price;
                const livePnl = parseFloat(
                  (
                    (live / op.entry - 1) *
                    (op.type === "LONG" ? 1 : -1) *
                    (op.position_value || 0)
                  ).toFixed(2),
                );
                const roiPct = parseFloat(
                  (
                    (live / op.entry - 1) *
                    (op.type === "LONG" ? 1 : -1) *
                    100
                  ).toFixed(2),
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
                      <span style={STYLES.badge(op.type)}>{op.type}</span>
                    </td>
                    <td
                      style={STYLES.td("right", "400", "#f8fafc", true)}
                      className="col-hide-sm"
                    >
                      {op.position_value
                        ? `$${op.position_value.toFixed(2)}`
                        : "—"}
                    </td>
                    <td style={STYLES.td("right", "400", "#f8fafc", true)}>
                      {formatPrice(op.entry)}
                    </td>
                    <td style={STYLES.td("right", "700", "#aa3bff", true)}>
                      {formatPrice(live)}
                    </td>
                    <td
                      style={STYLES.td("right", "400", "#00ffaa", true)}
                      className="col-hide-sm"
                    >
                      {formatPrice(op.tp)}
                    </td>
                    <td
                      style={STYLES.td("right", "400", "#f8fafc", true)}
                      className="col-hide-sm"
                    >
                      <span
                        style={{
                          color: op.is_trailing ? "#f59e0b" : "#ff3b69",
                        }}
                      >
                        {op.sl === 0 ? "SIN SL" : formatPrice(op.sl)}
                      </span>
                      {op.is_breakeven && (
                        <span style={STYLES.specialBadge("#00ffaa")}>BE</span>
                      )}
                      {op.is_trailing && (
                        <span style={STYLES.specialBadge("#f59e0b")}>TR</span>
                      )}
                    </td>
                    <td
                      style={STYLES.td(
                        "right",
                        "700",
                        roiPct >= 0 ? "#00ffaa" : "#ff3b69",
                        true,
                      )}
                    >
                      {roiPct > 0 ? "+" : ""}
                      {roiPct}%
                    </td>
                    <td
                      style={STYLES.td(
                        "right",
                        "700",
                        livePnl >= 0 ? "#00ffaa" : "#ff3b69",
                        true,
                      )}
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
    </div>
  );
}
