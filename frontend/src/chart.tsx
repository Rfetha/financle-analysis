import { useEffect, useRef } from "react";
import { createChart, type CandlestickData, type IChartApi } from "lightweight-charts";

type Candle = { ts: number; open: number; high: number; low: number; close: number; volume: number };

export function Chart({ ticker, range = "6mo", interval = "1d" }: {
  ticker: string; range?: string; interval?: string;
}) {
  const box = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!box.current) return;
    chart.current = createChart(box.current, {
      height: 320,
      layout: { background: { color: "#0d1117" }, textColor: "#e6edf3" },
      grid: { vertLines: { color: "#21262d" }, horzLines: { color: "#21262d" } },
      timeScale: { timeVisible: interval !== "1d" },
    });
    const series = chart.current.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350",
      wickUpColor: "#26a69a", wickDownColor: "#ef5350", borderVisible: false,
    });

    let cancelled = false;
    fetch(`/api/ohlcv/${ticker}?range=${range}&interval=${interval}`)
      .then((r) => r.json())
      .then((data: { candles: Candle[] }) => {
        if (cancelled) return;
        const bars: CandlestickData[] = data.candles.map((c) => ({
          time: c.ts as never, open: c.open, high: c.high, low: c.low, close: c.close,
        }));
        series.setData(bars);
        chart.current?.timeScale().fitContent();
      })
      .catch(() => {});

    return () => {
      cancelled = true;
      chart.current?.remove();
    };
  }, [ticker, range, interval]);

  return <div ref={box} style={{ margin: "8px 0", borderRadius: 8, overflow: "hidden" }} />;
}
