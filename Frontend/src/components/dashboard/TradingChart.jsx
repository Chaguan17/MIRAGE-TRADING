import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const FUTURES_WS = "wss://fstream.binance.com/ws";
const SPOT_WS = "wss://stream.binance.com/ws";

const TF_OPTIONS = [
  { label: '1m', value: '1m' },
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '1H', value: '1h' },
  { label: '4H', value: '4h' },
  { label: '1D', value: '1d' },
];

function getPrecision(price) {
  if (price < 0.01) return { precision: 6, minMove: 0.000001 };
  if (price < 0.1) return { precision: 5, minMove: 0.00001 };
  if (price < 1) return { precision: 4, minMove: 0.0001 };
  if (price < 10) return { precision: 3, minMove: 0.001 };
  return { precision: 2, minMove: 0.01 };
}

export default function TradingChart({ operaciones_activas, availablePairs }) {
  const [chartWsUrl, setChartWsUrl] = useState(FUTURES_WS);
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const priceLineRefs = useRef([]);
  const wsRef = useRef(null);
  const lastBarRef = useRef(null);

  const [selectedPair, setSelectedPair] = useState(availablePairs[0] || 'BTCUSDT');
  const [selectedTF, setSelectedTF] = useState('5m');
  const [loading, setLoading] = useState(true);
  const [lastPrice, setLastPrice] = useState(null);
  const [priceChange, setPriceChange] = useState(0);

  // Keep selectedPair valid
  useEffect(() => {
    if (!availablePairs.includes(selectedPair) && availablePairs.length > 0) {
      setSelectedPair(availablePairs[0]);
    }
  }, [availablePairs, selectedPair]);

  // ── Create chart once ──
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 420,
      layout: {
        background: { type: 'solid', color: '#080d1a' },
        textColor: '#64748b',
        fontSize: 11,
        fontFamily: 'JetBrains Mono, monospace',
      },
      grid: {
        vertLines: { color: 'rgba(100, 116, 139, 0.06)' },
        horzLines: { color: 'rgba(100, 116, 139, 0.06)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: 'rgba(170, 59, 255, 0.3)',
          width: 1,
          style: 3,
          labelBackgroundColor: '#aa3bff',
        },
        horzLine: {
          color: 'rgba(170, 59, 255, 0.3)',
          width: 1,
          style: 3,
          labelBackgroundColor: '#aa3bff',
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(30, 41, 59, 0.5)',
        scaleMargins: { top: 0.05, bottom: 0.2 },
      },
      timeScale: {
        borderColor: 'rgba(30, 41, 59, 0.5)',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 5,
        barSpacing: 8,
      },
      handleScroll: { vertTouchDrag: false },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#00ffaa',
      downColor: '#ff3b69',
      borderVisible: false,
      wickUpColor: '#00ffaa',
      wickDownColor: '#ff3b69',
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, []);

  // ── Fetch historical data & connect WebSocket ──
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return;

    let isMounted = true;
    setLoading(true);

    // Cleanup previous WS
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const fetchAndSubscribe = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/chart/${selectedPair}?tf=${selectedTF}`);
        if (!res.ok) throw new Error("Error fetching chart data");
        const rawData = await res.json();

        const uniqueMap = new Map();
        rawData.forEach(item => uniqueMap.set(item.time, item));
        const data = Array.from(uniqueMap.values()).sort((a, b) => a.time - b.time);

        if (!isMounted) return;

        const { precision, minMove } = getPrecision(data[data.length - 1]?.close || 1);
        candleSeriesRef.current.applyOptions({
          priceFormat: { type: 'price', precision, minMove },
        });

        candleSeriesRef.current.setData(data);

        const volData = data.map(d => ({
          time: d.time,
          value: d.volume || 0,
          color: d.close >= d.open ? 'rgba(0, 255, 170, 0.15)' : 'rgba(255, 59, 105, 0.15)',
        }));
        volumeSeriesRef.current.setData(volData);

        const last = data[data.length - 1];
        lastBarRef.current = last;
        if (last) {
          setLastPrice(last.close);
          if (data.length > 1) {
            const prev = data[data.length - 2];
            setPriceChange(((last.close - prev.close) / prev.close) * 100);
          }
        }

        setLoading(false);

        // Connect Binance WS for real-time updates
        const wsSymbol = selectedPair.toLowerCase();
        const ws = new WebSocket(`${chartWsUrl}/${wsSymbol}@kline_${selectedTF}`);

        let msgReceived = false;

        ws.onmessage = (event) => {
          msgReceived = true;
          if (!isMounted) return;
          try {
            const msg = JSON.parse(event.data);
            const k = msg.k;
            if (!k) return;

            const bar = {
              time: Math.floor(k.t / 1000),
              open: parseFloat(k.o),
              high: parseFloat(k.h),
              low: parseFloat(k.l),
              close: parseFloat(k.c),
            };
            const vol = {
              time: bar.time,
              value: parseFloat(k.v),
              color: bar.close >= bar.open ? 'rgba(0, 255, 170, 0.15)' : 'rgba(255, 59, 105, 0.15)',
            };

            candleSeriesRef.current?.update(bar);
            volumeSeriesRef.current?.update(vol);

            setLastPrice(bar.close);
            if (lastBarRef.current) {
              setPriceChange(((bar.close - lastBarRef.current.open) / lastBarRef.current.open) * 100);
            }
            lastBarRef.current = bar;
          } catch (_) {}
        };

        wsRef.current = ws;

        if (chartWsUrl === FUTURES_WS) {
          setTimeout(() => {
            if (!msgReceived && isMounted && ws === wsRef.current) {
              console.warn("⚠️ Chart Futures WS silent. Switching to Spot WS...");
              setChartWsUrl(SPOT_WS);
            }
          }, 6000);
        }
      } catch (err) {
        console.error("Chart fetch error:", err);
        if (isMounted) setLoading(false);
      }
    };

    fetchAndSubscribe();

    return () => {
      isMounted = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [selectedPair, selectedTF, chartWsUrl]);

  // ── Price Lines for active trades ──
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    const series = candleSeriesRef.current;

    // Remove old lines
    priceLineRefs.current.forEach(pl => {
      try { series.removePriceLine(pl); } catch (_) {}
    });
    priceLineRefs.current = [];

    const activeForPair = (operaciones_activas || []).filter(op => op.pair === selectedPair);

    activeForPair.forEach(op => {
      if (!op.entry) return;

      const entryLine = series.createPriceLine({
        price: op.entry,
        color: '#3b82f6',
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: `▸ ${op.type} ENTRY`,
      });
      priceLineRefs.current.push(entryLine);

      if (op.tp && op.tp > 0) {
        const tpLine = series.createPriceLine({
          price: op.tp,
          color: '#00ffaa',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: '◎ TP',
        });
        priceLineRefs.current.push(tpLine);
      }

      if (op.sl && op.sl > 0) {
        const slLine = series.createPriceLine({
          price: op.sl,
          color: '#ff3b69',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: '✕ SL',
        });
        priceLineRefs.current.push(slLine);
      }
    });
  }, [operaciones_activas, selectedPair]);

  const activeOp = (operaciones_activas || []).find(op => op.pair === selectedPair);
  const isPositive = priceChange >= 0;

  return (
    <div style={chartCardStyle}>
      {/* ── Header ── */}
      <div style={headerStyle}>
        <div style={headerLeftStyle}>
          <select
            value={selectedPair}
            onChange={e => setSelectedPair(e.target.value)}
            style={pairSelectStyle}
          >
            {availablePairs.map(p => <option key={p} value={p}>{p}</option>)}
          </select>

          {lastPrice !== null && (
            <div style={priceDisplayStyle}>
              <span style={{ fontSize: '1.4rem', fontWeight: '800', color: '#f8fafc', fontFamily: 'JetBrains Mono, monospace' }}>
                {lastPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
              </span>
              <span style={{
                fontSize: '0.8rem',
                fontWeight: '700',
                color: isPositive ? '#00ffaa' : '#ff3b69',
                background: isPositive ? 'rgba(0,255,170,0.08)' : 'rgba(255,59,105,0.08)',
                padding: '3px 8px',
                borderRadius: '6px',
              }}>
                {isPositive ? '+' : ''}{priceChange.toFixed(2)}%
              </span>
            </div>
          )}
        </div>

        <div style={headerRightStyle}>
          {/* Active position indicator */}
          {activeOp && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '5px 10px', borderRadius: '8px', fontSize: '0.7rem', fontWeight: '800',
              background: activeOp.type === 'LONG' ? 'rgba(0,255,170,0.1)' : 'rgba(255,59,105,0.1)',
              color: activeOp.type === 'LONG' ? '#00ffaa' : '#ff3b69',
              border: `1px solid ${activeOp.type === 'LONG' ? 'rgba(0,255,170,0.2)' : 'rgba(255,59,105,0.2)'}`,
              textTransform: 'uppercase',
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: activeOp.type === 'LONG' ? '#00ffaa' : '#ff3b69',
                boxShadow: `0 0 8px ${activeOp.type === 'LONG' ? '#00ffaa' : '#ff3b69'}`,
              }} />
              {activeOp.type} Activo
            </div>
          )}

          {/* Timeframe selector */}
          <div style={tfBarStyle}>
            {TF_OPTIONS.map(tf => (
              <button
                key={tf.value}
                onClick={() => setSelectedTF(tf.value)}
                style={{
                  ...tfBtnStyle,
                  ...(selectedTF === tf.value ? tfBtnActiveStyle : {}),
                }}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Chart ── */}
      <div style={{ position: 'relative' }}>
        {loading && (
          <div style={loadingOverlayStyle}>
            <div style={spinnerStyle} />
            <span style={{ color: '#64748b', fontSize: '0.8rem', marginTop: '12px' }}>
              Cargando {selectedPair}...
            </span>
          </div>
        )}
        <div ref={chartContainerRef} style={{ width: '100%', height: '420px' }} />
      </div>

      {/* ── Footer with legend ── */}
      {activeOp && (
        <div style={footerStyle}>
          <div style={legendItemStyle('#3b82f6')}>
            <span style={legendDotStyle('#3b82f6')} /> Entrada: {activeOp.entry}
          </div>
          <div style={legendItemStyle('#00ffaa')}>
            <span style={legendDotStyle('#00ffaa')} /> TP: {activeOp.tp || '—'}
          </div>
          <div style={legendItemStyle('#ff3b69')}>
            <span style={legendDotStyle('#ff3b69')} /> SL: {activeOp.sl || '—'}
          </div>
          {activeOp.is_trailing && (
            <div style={legendItemStyle('#f59e0b')}>
              <span style={legendDotStyle('#f59e0b')} /> Trailing Activo
            </div>
          )}
          {activeOp.is_breakeven && (
            <div style={legendItemStyle('#06b6d4')}>
              <span style={legendDotStyle('#06b6d4')} /> Breakeven
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Styles ─────────────────────────────────────────────────────
const chartCardStyle = {
  background: 'linear-gradient(180deg, #0a0f1e 0%, #080d1a 100%)',
  border: '1px solid rgba(170, 59, 255, 0.12)',
  borderRadius: '20px',
  padding: '1.25rem 1.5rem',
  marginBottom: '1.5rem',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
};

const headerStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '1rem',
  flexWrap: 'wrap',
  gap: '12px',
};

const headerLeftStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '16px',
  flexWrap: 'wrap',
};

const headerRightStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  flexWrap: 'wrap',
};

const priceDisplayStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
};

const pairSelectStyle = {
  background: 'rgba(170, 59, 255, 0.08)',
  color: '#f8fafc',
  border: '1px solid rgba(170, 59, 255, 0.2)',
  padding: '8px 16px',
  borderRadius: '10px',
  outline: 'none',
  fontWeight: '800',
  fontSize: '0.9rem',
  fontFamily: 'JetBrains Mono, monospace',
  cursor: 'pointer',
  letterSpacing: '0.5px',
};

const tfBarStyle = {
  display: 'flex',
  gap: '2px',
  background: 'rgba(30, 41, 59, 0.4)',
  borderRadius: '10px',
  padding: '3px',
};

const tfBtnStyle = {
  background: 'transparent',
  color: '#64748b',
  border: 'none',
  padding: '6px 12px',
  borderRadius: '8px',
  fontSize: '0.7rem',
  fontWeight: '700',
  cursor: 'pointer',
  transition: 'all 0.15s ease',
  fontFamily: 'JetBrains Mono, monospace',
  letterSpacing: '0.5px',
};

const tfBtnActiveStyle = {
  background: 'rgba(170, 59, 255, 0.15)',
  color: '#aa3bff',
  boxShadow: '0 0 12px rgba(170, 59, 255, 0.1)',
};

const loadingOverlayStyle = {
  position: 'absolute',
  inset: 0,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'rgba(8, 13, 26, 0.9)',
  zIndex: 10,
  borderRadius: '12px',
};

const spinnerStyle = {
  width: '28px',
  height: '28px',
  border: '3px solid rgba(170, 59, 255, 0.15)',
  borderTopColor: '#aa3bff',
  borderRadius: '50%',
  animation: 'spin 0.8s linear infinite',
};

const footerStyle = {
  display: 'flex',
  gap: '20px',
  marginTop: '12px',
  paddingTop: '12px',
  borderTop: '1px solid rgba(30, 41, 59, 0.4)',
  flexWrap: 'wrap',
};

const legendItemStyle = (color) => ({
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  fontSize: '0.7rem',
  fontWeight: '600',
  color,
  fontFamily: 'JetBrains Mono, monospace',
});

const legendDotStyle = (color) => ({
  display: 'inline-block',
  width: '8px',
  height: '3px',
  borderRadius: '2px',
  background: color,
  boxShadow: `0 0 6px ${color}`,
});
