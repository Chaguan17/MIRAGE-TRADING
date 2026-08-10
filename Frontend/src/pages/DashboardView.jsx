import React, { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import GlobalAnimations from "../components/GlobalAnimations";
import { STYLES } from "../components/dashboard/styles";
import DashboardHeader from "../components/dashboard/DashboardHeader";
import KPIGrid from "../components/dashboard/KPIGrid";
import PairStatsRow from "../components/dashboard/PairStatsRow";
import TradingChart from "../components/dashboard/TradingChart";
import ActiveTradesTable from "../components/dashboard/ActiveTradesTable";
import HistoryTable from "../components/dashboard/HistoryTable";
import NotificationDrawer from "../components/dashboard/NotificationDrawer";

export default function DashboardView({
  data,
  livePrices,
  historyFilter,
  setHistoryFilter,
  historyLimit,
  setHistoryLimit,
}) {
  const navigate = useNavigate();
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [lastReadCount, setLastReadCount] = useState(0);

  const notifications = data?.notifications || [];
  const unreadCount = Math.max(0, notifications.length - lastReadCount);

  const handleOpenNotifications = () => {
    setIsNotificationsOpen(true);
    setLastReadCount(notifications.length);
  };

  // Calcula el PnL diario en vivo (ganancias cerradas hoy + flotante con precios en tiempo real)
  const liveDailyPnL = useMemo(() => {
    if (!data) return 0;

    // Base cerrada del día (provista por el backend data.pnl_diario)
    const baseClosedDaily = data.pnl_diario !== undefined ? data.pnl_diario : 0;

    // PnL flotante actual en vivo de las operaciones abiertas
    const currentLiveFloating =
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

    return parseFloat((baseClosedDaily + currentLiveFloating).toFixed(2));
  }, [data, livePrices]);

  // FIX: lista de pares dinámica extraída del historial real (no hardcodeada)
  const availablePairs = useMemo(() => {
    if (!data) return [];
    const pairs = new Set();
    
    // Extraer pares del historial
    if (data.ultimas_operaciones) {
      data.ultimas_operaciones.forEach((op) => {
        if (op.pair) pairs.add(op.pair);
      });
    }
    
    // Extraer pares activos
    if (data.operaciones_activas) {
      data.operaciones_activas.forEach((op) => {
        if (op.pair) pairs.add(op.pair);
      });
    }
    
    // Si la lista está vacía, usar pares por defecto
    if (pairs.size === 0) {
      return data.pares_activos || ["BTCUSDT"];
    }
    
    return Array.from(pairs);
  }, [data]);

  // Filtrado de operaciones en tiempo de renderizado
  const filteredHistory = useMemo(() => {
    if (!data || !data.ultimas_operaciones) return [];
    const list = historyFilter === "ALL"
      ? data.ultimas_operaciones
      : data.ultimas_operaciones.filter((op) => op.pair === historyFilter);
    return list.slice(0, historyLimit);
  }, [data, historyFilter, historyLimit]);

  const pairStats = useMemo(() => {
    if (!data || !data.ultimas_operaciones) return [];
    const statsMap = {};
    data.ultimas_operaciones.forEach((op) => {
      const p = op.pair;
      if (!p) return;
      if (!statsMap[p]) statsMap[p] = { wins: 0, losses: 0, total: 0, pnl: 0 };
      statsMap[p].total++;
      statsMap[p].pnl += op.pnl_usdt || 0;
      if (op.result === "WIN") statsMap[p].wins++;
      else if (op.result === "LOSS") statsMap[p].losses++;
    });
    return Object.keys(statsMap).map((p) => {
      const s = statsMap[p];
      const wr = s.total > 0 ? ((s.wins / s.total) * 100).toFixed(1) : "0.0";
      return {
        pair: p,
        wr,
        total: s.total,
        wins: s.wins,
        losses: s.losses,
        pnl: s.pnl,
      };
    });
  }, [data]);

  if (!data)
    return (
      <div style={STYLES.loadingBox}>
        <GlobalAnimations />
        <div className="animate-spin spinner" />
      </div>
    );

  return (
    <div style={STYLES.layout} className="animate-fade-in">
      <GlobalAnimations />
      <DashboardHeader
        navigate={navigate}
        config={data?.config}
        onOpenNotifications={handleOpenNotifications}
        unreadCount={unreadCount}
      />
      <KPIGrid data={data} liveDailyPnL={liveDailyPnL} />
      <PairStatsRow pairStats={pairStats} activePairs={data.pares_activos} />
      
      {availablePairs.length > 0 && (
        <TradingChart 
          operaciones_activas={data.operaciones_activas}
          availablePairs={availablePairs}
          config={data?.config}
          liveConsensus={data?.live_consensus}
        />
      )}
      
      <ActiveTradesTable 
        operaciones_activas={data.operaciones_activas} 
        livePrices={livePrices} 
        leverage={data.config?.LEVERAGE || 10}
      />
      
      <HistoryTable 
        historyFilter={historyFilter}
        setHistoryFilter={setHistoryFilter}
        availablePairs={availablePairs}
        historyLimit={historyLimit}
        setHistoryLimit={setHistoryLimit}
        filteredHistory={filteredHistory}
      />

      <NotificationDrawer
        notifications={notifications}
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
      />
    </div>
  );
}
