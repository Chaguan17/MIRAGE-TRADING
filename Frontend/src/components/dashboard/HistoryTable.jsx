import React, { useState } from "react";
import { STYLES } from "./styles";

function formatPrice(price) {
  if (price === undefined || price === null) return "—";
  const num = parseFloat(price);
  if (isNaN(num)) return price;
  if (num === 0) return "0";
  if (num < 0.01) return num.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 6 });
  if (num < 1) return num.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  if (num < 100) return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDuration(startStr, endStr) {
  if (!startStr || !endStr) return "—";
  try {
    const start = new Date(startStr.replace(" ", "T"));
    const end = new Date(endStr.replace(" ", "T"));
    if (isNaN(start.getTime()) || isNaN(end.getTime())) return "—";
    const diffMs = Math.max(0, end.getTime() - start.getTime());
    const totalMins = Math.floor(diffMs / (1000 * 60));
    if (totalMins < 60) return `${totalMins}m`;
    const hours = Math.floor(totalMins / 60);
    const mins = totalMins % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  } catch (_) {
    return "—";
  }
}

function getAssetBase(pair) {
  if (!pair) return "ETH";
  return pair.replace("USDT", "").replace("/", "").replace(":USDT", "");
}

function getCryptoIcon(pair) {
  const asset = getAssetBase(pair).toUpperCase();
  if (asset === "BTC") return "₿";
  if (asset === "ETH") return "Ξ";
  if (asset === "XRP") return "✕";
  if (asset === "SOL") return "◎";
  return "❖";
}

export default function HistoryTable({
  historyFilter,
  setHistoryFilter,
  availablePairs,
  historyLimit,
  setHistoryLimit,
  filteredHistory,
  leverage: configLeverage,
}) {
  const [expandedId, setExpandedId] = useState(null);

  const toggleExpand = (idx) => {
    setExpandedId(expandedId === idx ? null : idx);
  };

  return (
    <div style={{ ...STYLES.card, padding: "1.5rem" }}>
      {/* ── Filter Header ── */}
      <div style={STYLES.chartHeader}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <h3 style={{ ...STYLES.chartTitle, margin: 0 }}>Historial de Operaciones</h3>
          <span style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: "600" }}>
            ({filteredHistory.length} posiciones)
          </span>
        </div>

        <div style={STYLES.filterRow}>
          <select
            style={{ ...STYLES.select, width: "160px" }}
            value={historyFilter}
            onChange={(e) => setHistoryFilter(e.target.value)}
          >
            <option value="ALL" style={{ background: "#0b1120", color: "#f8fafc" }}>Todos los Pares</option>
            {(availablePairs || []).map((pair) => (
              <option key={pair} value={pair} style={{ background: "#0b1120", color: "#f8fafc" }}>
                {pair.replace("USDT", "/USDT")}
              </option>
            ))}
          </select>
          <select
            style={{ ...STYLES.select, width: "130px" }}
            value={historyLimit}
            onChange={(e) => setHistoryLimit(Number(e.target.value))}
          >
            <option value={20} style={{ background: "#0b1120", color: "#f8fafc" }}>Últimos 20</option>
            <option value={50} style={{ background: "#0b1120", color: "#f8fafc" }}>Últimos 50</option>
            <option value={100} style={{ background: "#0b1120", color: "#f8fafc" }}>Últimos 100</option>
          </select>
        </div>
      </div>

      {/* ── Position Cards List ── */}
      {filteredHistory.length === 0 ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#64748b", fontSize: "0.85rem" }}>
          No hay operaciones registradas en el historial.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "1rem" }}>
          {filteredHistory.map((op, idx) => {
            const isExpanded = expandedId === idx;
            const asset = getAssetBase(op.pair);
            const isShort = op.action === "SHORT";
            const netPnl = parseFloat(op.pnl_usdt || 0);
            const entryPrice = parseFloat(op.entry_price || 0);
            const closePrice = parseFloat(op.close_price || entryPrice);
            const sizeVal = parseFloat(op.size || 0);
            const tradeLeverage = op.leverage || configLeverage || 10;
            const isReal = op.is_paper === "REAL" || (op.order_id && String(op.order_id) !== "0" && String(op.order_id) !== "OK" && String(op.order_id) !== "NONE" && String(op.order_id) !== "PAPER");

            // ROI % calculation
            let roiPct = 0;
            if (entryPrice > 0) {
              const pnlPriceDiff = isShort ? (entryPrice - closePrice) : (closePrice - entryPrice);
              roiPct = (pnlPriceDiff / entryPrice) * tradeLeverage * 100;
            }

            const pnlColor = netPnl > 0 ? "#00ffaa" : netPnl < 0 ? "#ff3b69" : "#f8fafc";
            const roiColor = roiPct > 0 ? "#00ffaa" : roiPct < 0 ? "#ff3b69" : "#64748b";

            const openedAt = op.opened_at || op.timestamp || "—";
            const closedAt = op.closed_at || op.timestamp || "—";
            const durationStr = formatDuration(openedAt, closedAt);

            const notionalVal = sizeVal * entryPrice;
            const estFee = isReal ? (notionalVal + (sizeVal * closePrice)) * 0.00035 : 0;
            const grossPnl = netPnl + estFee;

            return (
              <div
                key={idx}
                onClick={() => toggleExpand(idx)}
                style={{
                  background: isExpanded
                    ? "linear-gradient(180deg, rgba(170, 59, 255, 0.08) 0%, rgba(11, 17, 32, 0.95) 100%)"
                    : "#0a0f1d",
                  border: isExpanded
                    ? "1px solid rgba(170, 59, 255, 0.35)"
                    : "1px solid rgba(30, 41, 59, 0.6)",
                  borderRadius: "14px",
                  padding: "1rem 1.25rem",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                  boxShadow: isExpanded ? "0 8px 24px rgba(0,0,0,0.5)" : "none",
                }}
              >
                {/* ── Card Header ── */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginBottom: "1rem" }}>
                  {/* Left: Badges */}
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                    <div style={{
                      width: "28px", height: "28px", borderRadius: "50%",
                      background: "rgba(170, 59, 255, 0.15)", border: "1px solid rgba(170, 59, 255, 0.3)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontWeight: "900", color: "#aa3bff", fontSize: "0.85rem"
                    }}>
                      {getCryptoIcon(op.pair)}
                    </div>

                    <span style={{ fontWeight: "800", color: "#f8fafc", fontSize: "1rem", letterSpacing: "0.5px" }}>
                      {op.pair ? op.pair.replace("USDT", "USDT") : "—"}
                    </span>

                    <span style={{ background: "rgba(30, 41, 59, 0.8)", color: "#94a3b8", padding: "2px 6px", borderRadius: "4px", fontSize: "0.68rem", fontWeight: "700" }}>
                      Perp
                    </span>

                    <span style={{ background: "rgba(30, 41, 59, 0.8)", color: "#94a3b8", padding: "2px 6px", borderRadius: "4px", fontSize: "0.68rem", fontWeight: "700" }}>
                      {tradeLeverage}x
                    </span>

                    <span style={{
                      background: isShort ? "rgba(255, 59, 105, 0.15)" : "rgba(0, 255, 170, 0.15)",
                      color: isShort ? "#ff3b69" : "#00ffaa",
                      border: `1px solid ${isShort ? "rgba(255, 59, 105, 0.3)" : "rgba(0, 255, 170, 0.3)"}`,
                      padding: "2px 8px", borderRadius: "4px", fontSize: "0.68rem", fontWeight: "800", textTransform: "uppercase"
                    }}>
                      Isolated {op.action}
                    </span>

                    <span style={{ background: "rgba(100, 116, 139, 0.15)", color: "#94a3b8", padding: "2px 6px", borderRadius: "4px", fontSize: "0.68rem", fontWeight: "700" }}>
                      Closed
                    </span>
                  </div>

                  {/* Right: Timestamps & Duration */}
                  <div style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: "600", fontFamily: "JetBrains Mono, monospace" }}>
                    <span>{openedAt} Opened</span>
                    <span style={{ margin: "0 6px", opacity: 0.4 }}>|</span>
                    <span>{closedAt} Closed</span>
                    {durationStr !== "—" && (
                      <span style={{ color: "#94a3b8", marginLeft: "6px" }}>(Lasting {durationStr})</span>
                    )}
                  </div>
                </div>

                {/* ── Metrics Grid (6 Columns) ── */}
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                  gap: "12px",
                  paddingTop: "4px"
                }}>
                  {/* Column 1: Realized PNL */}
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "#64748b", fontWeight: "600", textTransform: "uppercase", marginBottom: "4px" }}>
                      Realized PNL (USDT)
                    </div>
                    <div style={{ fontSize: "1rem", fontWeight: "800", color: pnlColor, fontFamily: "JetBrains Mono, monospace" }}>
                      {netPnl > 0 ? `+${netPnl.toFixed(2)}` : netPnl.toFixed(2)} USDT
                    </div>
                  </div>

                  {/* Column 2: ROI */}
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "#64748b", fontWeight: "600", textTransform: "uppercase", marginBottom: "4px" }}>
                      ROI
                    </div>
                    <div style={{ fontSize: "0.95rem", fontWeight: "800", color: roiColor, fontFamily: "JetBrains Mono, monospace" }}>
                      {roiPct > 0 ? `+${roiPct.toFixed(2)}%` : `${roiPct.toFixed(2)}%`}
                    </div>
                  </div>

                  {/* Column 3: Closed Vol */}
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "#64748b", fontWeight: "600", textTransform: "uppercase", marginBottom: "4px" }}>
                      Closed Vol. ({asset})
                    </div>
                    <div style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", fontFamily: "JetBrains Mono, monospace" }}>
                      {sizeVal.toFixed(3)}
                    </div>
                  </div>

                  {/* Column 4: Entry Price */}
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "#64748b", fontWeight: "600", textTransform: "uppercase", marginBottom: "4px" }}>
                      Entry Price
                    </div>
                    <div style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", fontFamily: "JetBrains Mono, monospace" }}>
                      {formatPrice(entryPrice)}
                    </div>
                  </div>

                  {/* Column 5: Avg. Close Price */}
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "#64748b", fontWeight: "600", textTransform: "uppercase", marginBottom: "4px" }}>
                      Avg. Close Price
                    </div>
                    <div style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", fontFamily: "JetBrains Mono, monospace" }}>
                      {formatPrice(closePrice)}
                    </div>
                  </div>

                  {/* Column 6: Max OI */}
                  <div>
                    <div style={{ fontSize: "0.68rem", color: "#64748b", fontWeight: "600", textTransform: "uppercase", marginBottom: "4px" }}>
                      Max OI ({asset})
                    </div>
                    <div style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", fontFamily: "JetBrains Mono, monospace" }}>
                      {sizeVal.toFixed(3)}
                    </div>
                  </div>
                </div>

                {/* ── Expanded Accordion: Trade History Journey ── */}
                {isExpanded && (
                  <div style={{
                    marginTop: "1.25rem",
                    paddingTop: "1.25rem",
                    borderTop: "1px solid rgba(170, 59, 255, 0.2)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                    fontFamily: "Inter, sans-serif"
                  }}>
                    <div style={{ fontSize: "0.78rem", fontWeight: "800", color: "#aa3bff", display: "flex", alignItems: "center", gap: "6px" }}>
                      <span>📜 RECORRIDO COMPLETO DE LA POSICIÓN</span>
                      <span style={{ fontSize: "0.7rem", color: "#94a3b8", fontWeight: "600" }}>
                        ({isReal ? `Binance Real #${op.order_id || "OK"}` : "Paper Trading Simulación"})
                      </span>
                    </div>

                    {/* Timeline Steps */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px" }}>
                      {/* Step 1: Entry */}
                      <div style={{ background: "rgba(11, 17, 32, 0.8)", border: "1px solid rgba(30, 41, 59, 0.6)", borderRadius: "10px", padding: "10px 14px" }}>
                        <div style={{ fontSize: "0.72rem", fontWeight: "800", color: "#00ffaa", marginBottom: "6px" }}>
                          🚀 1. APERTURA DE POSICIÓN
                        </div>
                        <div style={{ fontSize: "0.72rem", color: "#cbd5e1", display: "flex", flexDirection: "column", gap: "3px" }}>
                          <div>Fecha: <strong>{openedAt}</strong></div>
                          <div>Operación: <strong>{op.action} {sizeVal} {asset}</strong></div>
                          <div>Precio Entrada: <strong>${formatPrice(entryPrice)} USDT</strong></div>
                          <div>Notional Total: <strong>${notionalVal.toFixed(2)} USDT</strong></div>
                        </div>
                      </div>

                      {/* Step 2: Risk & Trail */}
                      <div style={{ background: "rgba(11, 17, 32, 0.8)", border: "1px solid rgba(30, 41, 59, 0.6)", borderRadius: "10px", padding: "10px 14px" }}>
                        <div style={{ fontSize: "0.72rem", fontWeight: "800", color: "#aa3bff", marginBottom: "6px" }}>
                          ⚡ 2. MONITOREO Y GESTIÓN DE RIESGO
                        </div>
                        <div style={{ fontSize: "0.72rem", color: "#cbd5e1", display: "flex", flexDirection: "column", gap: "3px" }}>
                          <div>Modo: <strong>Maker Limit (GTX 0.020%)</strong></div>
                          <div>Stop Loss / TP: <strong>Sincronizados en Binance</strong></div>
                          <div>Trailing Stop: <strong>Activo con dinámico ATR</strong></div>
                          <div>Estrategia: <strong>Consenso IA + SMC Structure</strong></div>
                        </div>
                      </div>

                      {/* Step 3: Exit & Settlement */}
                      <div style={{ background: "rgba(11, 17, 32, 0.8)", border: "1px solid rgba(30, 41, 59, 0.6)", borderRadius: "10px", padding: "10px 14px" }}>
                        <div style={{ fontSize: "0.72rem", fontWeight: "800", color: netPnl >= 0 ? "#00ffaa" : "#ff3b69", marginBottom: "6px" }}>
                          🏁 3. CIERRE Y LIQUIDACIÓN {netPnl >= 0 ? "🏆" : "💀"}
                        </div>
                        <div style={{ fontSize: "0.72rem", color: "#cbd5e1", display: "flex", flexDirection: "column", gap: "3px" }}>
                          <div>Fecha Cierre: <strong>{closedAt}</strong></div>
                          <div>Precio Salida: <strong>${formatPrice(closePrice)} USDT</strong></div>
                          <div>PnL Bruto: <strong>{grossPnl > 0 ? "+" : ""}{grossPnl.toFixed(4)} USDT</strong></div>
                          <div>Comisión Est.: <span style={{ color: "#ff3b69" }}>{isReal ? `-${estFee.toFixed(4)} USDT` : "$0.00"}</span></div>
                          <div>PnL Realizado Neto: <strong style={{ color: pnlColor }}>{netPnl > 0 ? "+" : ""}{netPnl.toFixed(4)} USDT</strong></div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
