import React from "react";
import { STYLES } from "./styles";

export default function PairStatsRow({ pairStats, activePairs }) {
  if (!pairStats || pairStats.length === 0) return null;

  return (
    <div style={STYLES.pairStatsRow}>
      {pairStats.map((s) => (
        <div key={s.pair} style={STYLES.pairStatCard}>
          <span style={STYLES.pairStatName}>{s.pair}</span>
          <div style={STYLES.pairStatDivider} />
          <div style={STYLES.pairStatDetails}>
            <span style={STYLES.pairStatWr(parseFloat(s.wr) >= 50)}>
              <div
                style={STYLES.dot(activePairs?.includes(s.pair))}
              />
              {s.wr}%
            </span>
            <span style={STYLES.pairStatCount}>{s.total} Trades</span>
          </div>
        </div>
      ))}
    </div>
  );
}
