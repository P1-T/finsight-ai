"use client";

import { useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries, LineSeries, ColorType, type IChartApi } from "lightweight-charts";
import type { ChartSeries } from "@/types/research";

type Props = { series: ChartSeries | null; loading: boolean; error: string | null };

export function StockPriceChart({ series, loading, error }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [chartError, setChartError] = useState<{ series: ChartSeries; message: string } | null>(null);
  const currentChartError = chartError?.series === series ? chartError.message : null;

  useEffect(() => {
    const element = container.current;
    if (!element || !series?.candles.length) return;

    let chart: IChartApi;
    try {
    chart = createChart(element, {
      width: element.clientWidth,
      height: 320,
      layout: { background: { type: ColorType.Solid, color: "#ffffff" }, textColor: "#687386" },
      grid: { vertLines: { color: "#f0f2f5" }, horzLines: { color: "#f0f2f5" } },
      rightPriceScale: { borderColor: "#e6e9ee" },
      timeScale: { borderColor: "#e6e9ee", timeVisible: false },
      crosshair: { vertLine: { color: "#aab4c2", labelBackgroundColor: "#172b4d" }, horzLine: { color: "#aab4c2", labelBackgroundColor: "#172b4d" } },
    });
    chartRef.current = chart;

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: "#168a67", downColor: "#d35b54", borderVisible: false,
      wickUpColor: "#168a67", wickDownColor: "#d35b54",
    });
    candles.setData(series.candles.map((point) => ({
      time: point.time,
      open: point.open,
      high: point.high,
      low: point.low,
      close: point.close,
    })));

    const sma20 = chart.addSeries(LineSeries, { color: "#d69b25", lineWidth: 2, priceLineVisible: false, lastValueVisible: false, title: "SMA 20" });
    sma20.setData(series.sma20.map((point) => ({ time: point.time, value: point.value })));
    const sma50 = chart.addSeries(LineSeries, { color: "#5279c7", lineWidth: 2, priceLineVisible: false, lastValueVisible: false, title: "SMA 50" });
    sma50.setData(series.sma50.map((point) => ({ time: point.time, value: point.value })));
    chart.timeScale().fitContent();

    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width;
      if (width) chart.applyOptions({ width });
    });
    observer.observe(element);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
    } catch {
      window.setTimeout(() => {
        setChartError({ series, message: "The chart could not be displayed. Try running the research again." });
      }, 0);
      return;
    }
  }, [series]);

  return (
    <div className="chart-shell" aria-label="Historical stock candlestick chart">
      {loading ? <div className="chart-placeholder"><span className="spinner" />Loading historical market data…</div> : null}
      {!loading && error ? <div className="chart-placeholder chart-error">{error}</div> : null}
      {!loading && !error && !series?.candles.length ? <div className="chart-placeholder">Run research to load historical price data.</div> : null}
      {!loading && !error && currentChartError ? <div className="chart-placeholder chart-error">{currentChartError}</div> : null}
      {!loading && !error && series?.candles.length && !currentChartError ? <div ref={container} className="chart-canvas" /> : null}
      <div className="chart-legend"><span><i className="legend-candle" /> OHLC</span><span><i className="legend-sma20" /> SMA 20</span><span><i className="legend-sma50" /> SMA 50</span></div>
      <p className="chart-attribution">Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">TradingView Lightweight Charts™</a></p>
    </div>
  );
}
