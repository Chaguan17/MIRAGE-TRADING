import React from "react";

const GlobalAnimations = () => (
  <style>{`
    :root {
      --bg-card: #0b1120;
      --text-muted: #64748b;
      --text-main: #f8fafc;
    }
    *, *::before, *::after { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      padding: 0;
      background-color: #060913;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .animate-spin { animation: spin 1s linear infinite; }
    .animate-fade-in { animation: fadeIn 0.4s ease-out; }
    .spinner {
      width: 40px; height: 40px;
      border: 4px solid rgba(170, 59, 255, 0.1);
      border-top-color: #aa3bff;
      border-radius: 50%;
    }
    /* Scrollbar estilizado */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #334155; }

    /* Responsive: en pantallas <= 640px, ocultar columnas menos críticas de las tablas */
    @media (max-width: 640px) {
      .col-hide-sm { display: none !important; }
    }
  `}</style>
);

// ─── Dashboard ─────────────────────────────────────────────────────────────────
export default GlobalAnimations;
