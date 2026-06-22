import React from "react";
import { Routes, Route } from "react-router-dom";
import DashboardView from "./pages/DashboardView";
import PerformanceView from "./pages/PerformanceView";
import SettingsView from "./pages/SettingsView";
import { useDashboardData } from "./hooks/useDashboardData";
import GlobalAnimations from "./components/GlobalAnimations";

export default function App() {
  const dashboard = useDashboardData();

  if (dashboard.error) {
    return (
      <div style={{ height: "100vh", display: "flex", justifyContent: "center", alignItems: "center", backgroundColor: "#060913", color: "#f8fafc", padding: "1rem" }}>
        <GlobalAnimations />
        <div style={{ background: "rgba(255, 59, 105, 0.08)", borderColor: "#ff3b69", border: "1px solid", borderRadius: "16px", textAlign: "center", padding: "40px", maxWidth: "460px", width: "100%" }}>
          <h2 style={{ marginBottom: "12px", fontSize: "1.4rem", color: "#ff3b69" }}>⚠️ Error Crítico de Sistema</h2>
          <p style={{ color: "#f8fafc", fontSize: "0.95rem", margin: 0 }}>{dashboard.error}</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ backgroundColor: "#060913", minHeight: "100vh" }}>
      <GlobalAnimations />
      <Routes>
        <Route path="/" element={<DashboardView {...dashboard} />} />
        <Route path="/performance" element={<PerformanceView />} />
        <Route path="/settings" element={<SettingsView />} />
      </Routes>
    </div>
  );
}
