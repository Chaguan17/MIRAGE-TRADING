import React from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { STYLES, chartColors } from "./styles";

export default function EquityChart({ chartData }) {
  return (
    <div style={{ ...STYLES.card, marginBottom: "1.5rem" }}>
      <div style={STYLES.chartHeader}>
        <h3 style={STYLES.chartTitle}>Curva de Equidad Algorítmica</h3>
        <span style={STYLES.chartBadge}>En tiempo real</span>
      </div>
      <div style={{ height: "280px", width: "100%" }}>
        <ResponsiveContainer>
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorPnL" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor={chartColors.accent}
                  stopOpacity={0.4}
                />
                <stop
                  offset="95%"
                  stopColor={chartColors.accent}
                  stopOpacity={0.01}
                />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="4 4"
              vertical={false}
              stroke="#1e293b"
            />
            <XAxis dataKey="time" hide />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 11, fontWeight: 600 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(val) => `$${val}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--bg-card)",
                border: "1px solid #1e293b",
                borderRadius: "12px",
                boxShadow: "0 10px 25px rgba(0,0,0,0.4)",
              }}
              itemStyle={{ color: "#fff", fontWeight: "bold" }}
              labelStyle={{ color: "var(--text-muted)", fontSize: "11px" }}
            />
            <Area
              type="monotone"
              dataKey="pnl"
              stroke={chartColors.accent}
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#colorPnL)"
              activeDot={{ r: 5, strokeWidth: 0, fill: "white" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
