import React from "react";
import { STYLES } from "./styles";

export default function DashboardHeader({ navigate, config, onOpenNotifications, unreadCount = 0 }) {
  const isPaper = config ? config.PAPER_TRADING !== false : true;

  const handleToggleTradingMode = async () => {
    const targetMode = isPaper ? "REAL (Binance Futures)" : "PAPER (Simulación)";
    const confirmMsg = isPaper
      ? "🚨 ¿DESEAS ACTIVAR EL MODO REAL EN BINANCE FUTURES?\n\nEl bot ejecutará operaciones reales con balance real en tu cuenta de Binance Futures según tus señales."
      : "🛡️ ¿Deseas volver a Modo Paper Trading (Simulación sin dinero real)?";

    if (window.confirm(confirmMsg)) {
      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
        const res = await fetch(`${API_BASE_URL}/api/config`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ PAPER_TRADING: !isPaper }),
        });
        if (res.ok) {
          alert(`✅ Modo de trading actualizado a: ${targetMode}`);
        } else {
          alert("❌ Error cambiando el modo de trading");
        }
      } catch (e) {
        alert("❌ Error al conectar con el servidor API");
      }
    }
  };

  return (
    <header style={STYLES.header}>
      <div style={STYLES.brandSection}>
        <div style={STYLES.logoBox}>
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
        </div>
        <div>
          <h1 style={STYLES.brandTitle}>
            MIRAGE <span style={STYLES.brandSubtitle}>TERMINAL</span>
          </h1>
          <span style={STYLES.statusIndicator}>
            <div style={STYLES.statusDot} /> Sistemas En Línea
          </span>
        </div>
      </div>

      <div style={STYLES.headerButtons}>
        {/* Botón de Notificaciones / Alertas */}
        <button
          onClick={onOpenNotifications}
          title="Ver bandeja de eventos y errores"
          style={{
            ...STYLES.btnSecondary,
            position: "relative",
            borderColor: unreadCount > 0 ? "rgba(239, 68, 68, 0.6)" : "rgba(255,255,255,0.1)",
            background: unreadCount > 0 ? "rgba(239, 68, 68, 0.12)" : "rgba(255, 255, 255, 0.03)",
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke={unreadCount > 0 ? "#ef4444" : "currentColor"}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span style={{ color: unreadCount > 0 ? "#f87171" : "inherit" }}>Alertas</span>

          {unreadCount > 0 && (
            <span
              style={{
                position: "absolute",
                top: "-5px",
                right: "-5px",
                background: "#ef4444",
                color: "#ffffff",
                fontSize: "0.68rem",
                fontWeight: "800",
                minWidth: "18px",
                height: "18px",
                borderRadius: "9px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "0 4px",
                boxShadow: "0 0 8px rgba(239, 68, 68, 0.8)",
              }}
            >
              {unreadCount}
            </span>
          )}
        </button>

        {/* Switcher MODO PAPER / REAL */}
        <button
          onClick={handleToggleTradingMode}
          title={isPaper ? "Clic para activar MODO REAL en Binance" : "Clic para volver a MODO PAPER (Simulado)"}
          style={{
            ...STYLES.btnSecondary,
            background: isPaper ? "rgba(59, 130, 246, 0.12)" : "rgba(245, 158, 11, 0.15)",
            borderColor: isPaper ? "rgba(59, 130, 246, 0.4)" : "rgba(245, 158, 11, 0.6)",
            color: isPaper ? "#60a5fa" : "#fbbf24",
            boxShadow: isPaper ? "none" : "0 0 12px rgba(245, 158, 11, 0.25)",
          }}
        >
          {isPaper ? (
            <>
              <span style={{ fontSize: "0.9rem" }}>🛡️</span>
              <span>MODO PAPER</span>
            </>
          ) : (
            <>
              <span style={{ fontSize: "0.9rem" }}>🔥</span>
              <span style={{ fontWeight: "800" }}>MODO REAL (LIVE)</span>
            </>
          )}
        </button>

        <button
          onClick={() => navigate("/performance")}
          style={STYLES.btnSecondary}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="18" y1="20" x2="18" y2="10" />
            <line x1="12" y1="20" x2="12" y2="4" />
            <line x1="6" y1="20" x2="6" y2="14" />
          </svg>
          Métricas
        </button>

        <button
          onClick={async () => {
            if(window.confirm("🚨 ¿ESTÁS SEGURO? Esto cerrará todas las posiciones a mercado. 🚨")) {
              try {
                const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
                const res = await fetch(`${API_BASE_URL}/api/commands`, {
                  method: 'POST',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({ action: "PANIC_SELL" })
                });
                if(res.ok) alert("Comando de Pánico Enviado");
              } catch(e) {
                alert("Error al enviar pánico");
              }
            }
          }}
          style={{
            ...STYLES.btnSecondary,
            borderColor: "rgba(239, 68, 68, 0.5)",
            color: "#ef4444",
            background: "rgba(239, 68, 68, 0.1)"
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          PANIC CLOSE
        </button>

        <button
          onClick={() => navigate("/settings")}
          style={STYLES.btnSecondary}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          Ajustes
        </button>
      </div>
    </header>
  );
}
