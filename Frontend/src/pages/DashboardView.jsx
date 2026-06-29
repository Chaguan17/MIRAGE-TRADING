import React, { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import GlobalAnimations from "../components/GlobalAnimations";
import { STYLES } from "../components/dashboard/styles";
import DashboardHeader from "../components/dashboard/DashboardHeader";
import KPIGrid from "../components/dashboard/KPIGrid";
import PairStatsRow from "../components/dashboard/PairStatsRow";
import TradingChart from "../components/dashboard/TradingChart";
import ActiveTradesTable from "../components/dashboard/ActiveTradesTable";
import HistoryTable from "../components/dashboard/HistoryTable";

export default function DashboardView({
  data,
  livePrices,
  historyFilter,
  setHistoryFilter,
  historyLimit,
  setHistoryLimit,
}) {
  const navigate = useNavigate();

  // Calcula el PnL total en vivo (cerrado + flotante con precios actualizados)
  const liveTotalPnL = useMemo(() => {
    if (!data) return 0;
    const closedPnl =
      data.pnl_total -
      (data.operaciones_activas?.reduce(
        (acc, op) => acc + (op.current_pnl || 0),
        0,
      ) || 0);

    const currentLive =
      data.operaciones_activas?.reduce((acc, op) => {
        const price = livePrices[op.pair];
        if (price) {
          return (
            acc +
            (op.position_value || 0) *
              (price / op.entry - 1) *
              (op.type === "LONG" ? 1 : -1)
          );
        }
        return acc + (op.current_pnl || 0);
      }, 0) || 0;

    return parseFloat((closedPnl + currentLive).toFixed(2));
  }, [data, livePrices]);

  // FIX: lista de pares dinámica extraída del historial real (no hardcodeada)
  const availablePairs = useMemo(() => {
    if (!data) return [];
    const pairs = new Set();

    // Incluir pares del historial
    if (data.ultimas_operaciones) {
      data.ultimas_operaciones.forEach((op) => {
        if (op.pair && op.pair !== "UNKNOWN") pairs.add(op.pair);
      });
    }

    // Incluir pares activos configurados actualmente
    if (data.pares_activos) {
      data.pares_activos.forEach((p) => pairs.add(p));
    }

    return Array.from(pairs).sort();
  }, [data]);

  const filteredHistory = useMemo(() => {
    if (!data?.ultimas_operaciones) return [];
    let processed = [...data.ultimas_operaciones].reverse();
    if (historyFilter !== "ALL")
      processed = processed.filter((op) => op.pair === historyFilter);
    return processed.slice(0, historyLimit);
  }, [data, historyFilter, historyLimit]);

  const pairStats = useMemo(() => {
    if (!data || !data.tracker_stats) return [];
    
    return Object.entries(data.tracker_stats)
      .map(([pair, stats]) => ({
        pair,
        wr: stats.total > 0 ? stats.win_rate.toFixed(1) : "0.0",
        total: stats.total,
      }))
      .sort((a, b) => b.total - a.total);
  }, [data]);

  if (!data)
    return (
      <div style={STYLES.loading}>
        <GlobalAnimations />
        <div className="animate-spin spinner" />
      </div>
    );

  return (
    <div style={STYLES.layout} className="animate-fade-in">
      <GlobalAnimations />
      <DashboardHeader navigate={navigate} />
      <KPIGrid data={data} liveTotalPnL={liveTotalPnL} />
      <PairStatsRow pairStats={pairStats} activePairs={data.pares_activos} />
      
      {availablePairs.length > 0 && (
        <TradingChart 
          operaciones_activas={data.operaciones_activas}
          availablePairs={availablePairs}
        />
      )}
      
      <ActiveTradesTable 
        operaciones_activas={data.operaciones_activas} 
        livePrices={livePrices} 
      />
      
      <HistoryTable 
        historyFilter={historyFilter}
        setHistoryFilter={setHistoryFilter}
        availablePairs={availablePairs}
        historyLimit={historyLimit}
        setHistoryLimit={setHistoryLimit}
        filteredHistory={filteredHistory}
      />
    </div>
  );
}
