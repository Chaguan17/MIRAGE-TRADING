import React from "react";
import { STYLES } from "./styles";

export default function NotificationDrawer({ notifications = [], isOpen, onClose, onClearNotifications }) {
  if (!isOpen) return null;

  const handleClear = async () => {
    try {
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      await fetch(`${API_BASE_URL}/api/notifications`, { method: "DELETE" });
      if (onClearNotifications) onClearNotifications();
    } catch (e) {
      console.error("Error clearing notifications:", e);
    }
  };

  const getLevelStyle = (level) => {
    switch (level) {
      case "ERROR":
        return {
          bg: "rgba(239, 68, 68, 0.08)",
          border: "rgba(239, 68, 68, 0.3)",
          color: "#f87171",
          icon: "🚨",
          badgeBg: "rgba(239, 68, 68, 0.2)",
        };
      case "WARNING":
        return {
          bg: "rgba(245, 158, 11, 0.08)",
          border: "rgba(245, 158, 11, 0.3)",
          color: "#fbbf24",
          icon: "⚠️",
          badgeBg: "rgba(245, 158, 11, 0.2)",
        };
      case "SUCCESS":
        return {
          bg: "rgba(16, 185, 129, 0.08)",
          border: "rgba(16, 185, 129, 0.3)",
          color: "#34d399",
          icon: "✅",
          badgeBg: "rgba(16, 185, 129, 0.2)",
        };
      default:
        return {
          bg: "rgba(59, 130, 246, 0.08)",
          border: "rgba(59, 130, 246, 0.3)",
          color: "#60a5fa",
          icon: "ℹ️",
          badgeBg: "rgba(59, 130, 246, 0.2)",
        };
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0, 0, 0, 0.6)",
          backdropFilter: "blur(4px)",
          zIndex: 998,
        }}
      />

      {/* Drawer */}
      <aside
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          width: "420px",
          maxWidth: "90vw",
          background: "#0b1120",
          borderLeft: "1px solid #1e293b",
          zIndex: 999,
          display: "flex",
          flexDirection: "column",
          boxShadow: "-8px 0 32px rgba(0,0,0,0.6)",
          animation: "slideInRight 0.25s ease-out",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px",
            borderBottom: "1px solid #1e293b",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: "rgba(15, 23, 42, 0.8)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "1.3rem" }}>🔔</span>
            <div>
              <h2 style={{ margin: 0, fontSize: "1.1rem", color: "#f8fafc", fontWeight: "700" }}>
                Bandeja de Eventos
              </h2>
              <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                Registro de errores y ejecuciones en Binance
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              cursor: "pointer",
              fontSize: "1.2rem",
              padding: "4px 8px",
            }}
          >
            ✕
          </button>
        </div>

        {/* List of notifications */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          {notifications.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "40px 20px",
                color: "#64748b",
                fontSize: "0.9rem",
              }}
            >
              <div style={{ fontSize: "2rem", marginBottom: "8px" }}>🧹</div>
              No hay alertas ni errores registrados por el momento.
            </div>
          ) : (
            notifications.map((item) => {
              const st = getLevelStyle(item.level);
              return (
                <div
                  key={item.id}
                  style={{
                    background: st.bg,
                    border: `1px solid ${st.border}`,
                    borderRadius: "10px",
                    padding: "14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                    transition: "transform 0.15s ease",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span>{st.icon}</span>
                      <span
                        style={{
                          fontSize: "0.85rem",
                          fontWeight: "700",
                          color: st.color,
                        }}
                      >
                        {item.title}
                      </span>
                    </div>
                    <span
                      style={{
                        fontFamily: "JetBrains Mono, monospace",
                        fontSize: "0.7rem",
                        color: "#94a3b8",
                      }}
                    >
                      {item.timestamp}
                    </span>
                  </div>

                  <p
                    style={{
                      margin: 0,
                      fontSize: "0.82rem",
                      color: "#cbd5e1",
                      lineHeight: "1.4",
                      wordBreak: "break-word",
                    }}
                  >
                    {item.message}
                  </p>

                  {item.symbol && (
                    <div style={{ marginTop: "4px" }}>
                      <span
                        style={{
                          fontSize: "0.7rem",
                          fontWeight: "600",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          background: st.badgeBg,
                          color: st.color,
                          fontFamily: "JetBrains Mono, monospace",
                        }}
                      >
                        {item.symbol}
                      </span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "14px 20px",
            borderTop: "1px solid #1e293b",
            background: "rgba(15, 23, 42, 0.9)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <button
            onClick={handleClear}
            disabled={notifications.length === 0}
            style={{
              ...STYLES.btnSecondary,
              padding: "6px 14px",
              fontSize: "0.8rem",
              borderColor: "rgba(239, 68, 68, 0.3)",
              color: notifications.length > 0 ? "#f87171" : "#64748b",
              opacity: notifications.length > 0 ? 1 : 0.5,
              cursor: notifications.length > 0 ? "pointer" : "not-allowed",
            }}
          >
            🗑️ Limpiar Alertas
          </button>
          <button
            onClick={onClose}
            style={{
              ...STYLES.btnSecondary,
              padding: "6px 16px",
              fontSize: "0.8rem",
            }}
          >
            Cerrar
          </button>
        </div>
      </aside>
    </>
  );
}
