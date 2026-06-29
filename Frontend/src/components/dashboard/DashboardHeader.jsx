import React from "react";
import { STYLES } from "./styles";

export default function DashboardHeader({ navigate }) {
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
