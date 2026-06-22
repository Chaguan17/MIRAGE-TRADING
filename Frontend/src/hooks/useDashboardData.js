import { useState, useEffect, useRef } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_WS_URL = import.meta.env.VITE_API_WS_URL || "wss://stream.binance.com:9443/stream";

export function useDashboardData() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [livePrices, setLivePrices] = useState({});
  const [historyFilter, setHistoryFilter] = useState("ALL");
  const [historyLimit, setHistoryLimit] = useState(20);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectDelayRef = useRef(1000);
  const unmountedRef = useRef(false);

  const connectWebSocket = (pairs = []) => {
    if (unmountedRef.current) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const streams =
      pairs.length > 0
        ? pairs.map((p) => `${p.toLowerCase()}@ticker`).join("/")
        : "btcusdt@ticker/ethusdt@ticker/bnbusdt@ticker";

    const ws = new WebSocket(`${API_WS_URL}?streams=${streams}`);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.data?.s)
          setLivePrices((p) => ({
            ...p,
            [msg.data.s]: parseFloat(msg.data.c),
          }));
      } catch (_) {}
    };

    ws.onopen = () => {
      reconnectDelayRef.current = 1000;
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      const delay = Math.min(reconnectDelayRef.current, 30000);
      reconnectDelayRef.current = delay * 2;
      reconnectTimeoutRef.current = setTimeout(
        () => connectWebSocket(pairs),
        delay,
      );
    };

    wsRef.current = ws;
  };

  useEffect(() => {
    const fetchD = () => {
      fetch(`${API_BASE_URL}/api/dashboard`)
        .then((res) => res.json())
        .then((d) => {
          if (d.error) setError(d.error);
          else {
            setData(d);
            setError(null);
          }
        })
        .catch(() =>
          setError("Conexión perdida con el motor Mirage. Verifique el servidor backend.")
        );
    };
    fetchD();
    const timer = setInterval(fetchD, 3000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (data?.pares_activos) {
      if (wsRef.current) wsRef.current.close();
      connectWebSocket(data.pares_activos);
    } else {
      connectWebSocket();
    }
    return () => {
      unmountedRef.current = true;
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [data?.pares_activos]);

  return { data, error, livePrices, historyFilter, setHistoryFilter, historyLimit, setHistoryLimit };
}
