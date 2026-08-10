import { useState, useEffect, useRef, useCallback } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const BACKEND_WS_URL = (API_BASE_URL.replace("http", "ws")) + "/ws/dashboard";
const FUTURES_WS_URL = "wss://fstream.binance.com/stream";
const SPOT_WS_URL = "wss://stream.binance.com/stream";

export function useDashboardData() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [livePrices, setLivePrices] = useState({});
  const [historyFilter, setHistoryFilter] = useState("ALL");
  const [historyLimit, setHistoryLimit] = useState(20);
  const [binanceWsUrl, setBinanceWsUrl] = useState(FUTURES_WS_URL);

  const backendWsRef = useRef(null);
  const binanceWsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const binanceReconnectRef = useRef(null);
  const unmountedRef = useRef(false);

  // ── 1. Backend WebSocket (Dashboard state: PnL, trades, balance) ──
  const connectBackendWs = useCallback(() => {
    if (unmountedRef.current) return;
    // Close previous connection if any
    if (backendWsRef.current) {
      backendWsRef.current.onclose = null;
      backendWsRef.current.close();
      backendWsRef.current = null;
    }

    const ws = new WebSocket(BACKEND_WS_URL);

    ws.onopen = () => {
      setError(null);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.error) {
          setError(d.error);
        } else {
          setData(d);
          setError(null);
        }
      } catch (_) {}
    };

    ws.onclose = () => {
      if (unmountedRef.current || ws !== backendWsRef.current) return;
      // Reconnect after 2s
      reconnectTimeoutRef.current = setTimeout(connectBackendWs, 2000);
    };

    ws.onerror = () => {
      // Will trigger onclose, which handles reconnection
    };

    backendWsRef.current = ws;
  }, []);

  // ── 2. Binance WebSocket (Live prices for active pairs) ──
  const connectBinanceWs = useCallback((pairs = []) => {
    if (unmountedRef.current) return;

    // Close previous connection
    if (binanceWsRef.current) {
      binanceWsRef.current.onclose = null;
      binanceWsRef.current.close();
      binanceWsRef.current = null;
    }

    const streams =
      pairs.length > 0
        ? pairs.map((p) => `${p.toLowerCase()}@ticker`).join("/")
        : "btcusdt@ticker/ethusdt@ticker/bnbusdt@ticker";

    const ws = new WebSocket(`${binanceWsUrl}?streams=${streams}`);

    let messageReceived = false;

    ws.onmessage = (e) => {
      messageReceived = true;
      try {
        const msg = JSON.parse(e.data);
        if (msg.data?.s) {
          setLivePrices((prev) => ({
            ...prev,
            [msg.data.s]: parseFloat(msg.data.c),
          }));
        }
      } catch (_) {}
    };

    ws.onclose = () => {
      if (unmountedRef.current || ws !== binanceWsRef.current) return;
      binanceReconnectRef.current = setTimeout(() => connectBinanceWs(pairs), 3000);
    };

    binanceWsRef.current = ws;
  }, [binanceWsUrl]);

  // ── Init: Connect backend WS + initial REST fallback ──
  useEffect(() => {
    unmountedRef.current = false;

    // Try WebSocket first
    connectBackendWs();

    // Also do one REST fetch as immediate fallback while WS connects
    fetch(`${API_BASE_URL}/api/dashboard`)
      .then((res) => res.json())
      .then((d) => {
        if (d.error) setError(d.error);
        else { setData(d); setError(null); }
      })
      .catch(() => {
        // WS will handle it
      });

    return () => {
      unmountedRef.current = true;
      clearTimeout(reconnectTimeoutRef.current);
      clearTimeout(binanceReconnectRef.current);
      if (backendWsRef.current) backendWsRef.current.close();
      if (binanceWsRef.current) binanceWsRef.current.close();
    };
  }, [connectBackendWs]);

  // ── Connect Binance WS when pairs change ──
  const activePairsStr = (data?.pares_activos || []).join(",");
  
  useEffect(() => {
    if (activePairsStr) {
      connectBinanceWs(activePairsStr.split(","));
    } else {
      connectBinanceWs();
    }
  }, [activePairsStr, connectBinanceWs]);

  return { data, error, livePrices, historyFilter, setHistoryFilter, historyLimit, setHistoryLimit };
}
