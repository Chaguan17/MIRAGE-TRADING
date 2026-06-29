import React, { useEffect, useRef, useState } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';
import { STYLES } from './styles';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function TradingChart({ operaciones_activas, availablePairs }) {
  const chartContainerRef = useRef(null);
  const [chartData, setChartData] = useState([]);
  const [selectedPair, setSelectedPair] = useState(availablePairs[0] || 'BTCUSDT');
  const [loading, setLoading] = useState(false);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!availablePairs.includes(selectedPair) && availablePairs.length > 0) {
      setSelectedPair(availablePairs[0]);
    }
  }, [availablePairs, selectedPair]);

  // Fetch OHLCV data
  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE_URL}/api/chart/${selectedPair}`);
        if (!res.ok) throw new Error("Error fetching chart data");
        const data = await res.json();
        
        // Remove duplicates and sort by time
        const uniqueData = Array.from(new Map(data.map(item => [item.time, item])).values());
        uniqueData.sort((a, b) => a.time - b.time);
        
        if (isMounted) setChartData(uniqueData);
      } catch (err) {
        console.error("Chart fetch error:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchData();
    // Refresh chart data every 15 seconds
    const interval = setInterval(fetchData, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedPair]);

  // Initialize Chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { type: 'solid', color: '#0b1120' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(30, 41, 59, 0.5)' },
        horzLines: { color: 'rgba(30, 41, 59, 0.5)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#1e293b',
      },
      timeScale: {
        borderColor: '#1e293b',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // Update data & active trades markers
  useEffect(() => {
    if (!seriesRef.current || chartData.length === 0) return;
    
    // Dynamic precision based on asset price
    const lastPrice = chartData[chartData.length - 1].close;
    let precision = 2;
    let minMove = 0.01;
    
    if (lastPrice < 0.1) {
      precision = 5;
      minMove = 0.00001;
    } else if (lastPrice < 1) {
      precision = 4;
      minMove = 0.0001;
    } else if (lastPrice < 10) {
      precision = 3;
      minMove = 0.001;
    } else {
      precision = 2;
      minMove = 0.01;
    }

    seriesRef.current.applyOptions({
      priceFormat: {
        type: 'price',
        precision: precision,
        minMove: minMove,
      }
    });

    seriesRef.current.setData(chartData);
  }, [chartData]);

  // Price Lines
  useEffect(() => {
    if (!seriesRef.current) return;
    const series = seriesRef.current;
    
    if (series.priceLines) {
       series.priceLines.forEach(pl => series.removePriceLine(pl));
    }
    series.priceLines = [];

    const activeForPair = (operaciones_activas || []).filter(op => op.pair === selectedPair);
    
    activeForPair.forEach(op => {
      if (!op.entry || !op.sl || !op.tp) return;
      
      const entryLine = series.createPriceLine({
        price: op.entry,
        color: '#3b82f6',
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: `ENTRY ${op.type}`,
      });
      
      const slLine = series.createPriceLine({
        price: op.sl,
        color: '#ef4444',
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'SL',
      });

      const tpLine = series.createPriceLine({
        price: op.tp,
        color: '#10b981',
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'TP',
      });
      
      series.priceLines.push(entryLine, slLine, tpLine);
    });

  }, [operaciones_activas, selectedPair]);

  return (
    <div style={STYLES.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={STYLES.cardTitle}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#aa3bff" strokeWidth="2" style={{ marginRight: "10px" }}>
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          Mercado en Vivo
        </h3>
        <select 
          value={selectedPair} 
          onChange={e => setSelectedPair(e.target.value)}
          style={{
            background: "#1e293b", color: "#f8fafc", border: "1px solid #334155", 
            padding: "8px 12px", borderRadius: "8px", outline: "none",
            fontWeight: "bold"
          }}
        >
          {availablePairs.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>
      
      {loading && chartData.length === 0 && (
        <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
          Cargando gráfico de {selectedPair}...
        </div>
      )}
      <div ref={chartContainerRef} style={{ width: '100%', height: '400px', position: 'relative' }} />
    </div>
  );
}
