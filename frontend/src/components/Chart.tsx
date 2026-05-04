import { useEffect, useRef } from 'react'
import {
  CandlestickSeries,
  ColorType,
  LineSeries,
  LineStyle,
  createChart,
  type IChartApi,
  type Time,
} from 'lightweight-charts'

import type { Snapshot } from '@/schemas'

// Chart — lightweight-charts 5.2 React wrapper for the deep-dive page.
//
// Renders the per-ticker OHLC history as candlesticks plus 4 indicator
// overlays (MA20, MA50, Bollinger upper, Bollinger lower) and an RSI(14)
// sub-pane below. ALL series come from the snapshot's pre-computed indicator
// arrays — the frontend NEVER recomputes indicator math (analysts/_indicator_math.py
// is the single source of truth byte-identical with what the analysts use for
// verdicts).
//
// API version note: lightweight-charts 5.0+ replaced chart.addCandlestickSeries()
// / chart.addLineSeries() with chart.addSeries(CandlestickSeries, options) +
// chart.addSeries(LineSeries, options). This component uses the v5 API.
//
// Notion-Clean palette: layout background transparent (let the page bg show
// through); gridlines #252628 (--color-grid, barely visible); candles bullish
// #4ADE80 / bearish #F87171; MA20 accent blue #5B9DFF; MA50 muted #8B8E94; BB
// lines accent dotted; RSI amber #FBBF24 in a sub-pane occupying the bottom
// ~22% of the chart.
//
// Indicator series often have leading nulls (warmup periods — MA50 needs 50
// bars before its first value, RSI(14) needs 14, etc.). pairLines() drops
// those entries instead of passing them to setData (which would reject nulls
// or render gaps).

interface ChartProps {
  ohlcHistory: Snapshot['ohlc_history']
  indicators: Snapshot['indicators']
  height?: number
}

// Mobile responsive height: lightweight-charts respects pinch-zoom on touch
// devices natively when handleScroll/handleScale are enabled. We also size
// the container shorter on narrow viewports so the chart fits without
// pushing the rest of the page below the fold.
function pickHeight(viewportWidth: number, override?: number): number {
  if (override !== undefined) return override
  if (viewportWidth < 640) return 280 // sm-: phone portrait
  if (viewportWidth < 1024) return 360 // md: tablet
  return 480 // lg+: desktop
}

// Notion-Clean palette tokens — kept in sync with src/index.css @theme.
const PALETTE = {
  bg: '#0E0F11',
  fg: '#E8E9EB',
  fgMuted: '#8B8E94',
  border: '#2A2C30',
  grid: '#252628',
  accent: '#5B9DFF',
  bullish: '#4ADE80',
  bearish: '#F87171',
  amber: '#FBBF24',
} as const

export function Chart({ ohlcHistory, indicators, height }: ChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const initialWidth = containerRef.current.clientWidth || 800
    const initialHeight = pickHeight(
      typeof window !== 'undefined' ? window.innerWidth : 1024,
      height,
    )

    const chart = createChart(containerRef.current, {
      height: initialHeight,
      layout: {
        background: { type: ColorType.Solid, color: PALETTE.bg },
        textColor: PALETTE.fg,
      },
      grid: {
        vertLines: { color: PALETTE.grid },
        horzLines: { color: PALETTE.grid },
      },
      rightPriceScale: {
        borderColor: PALETTE.border,
        scaleMargins: { top: 0.05, bottom: 0.28 },
      },
      timeScale: {
        borderColor: PALETTE.border,
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: { mode: 1 /* CrosshairMode.Normal */ },
      // VIEW-12 mobile touch: pan via horiz drag, pinch-zoom via pinch.
      // vertTouchDrag stays false so vertical page-scroll passes through —
      // otherwise the chart "captures" the gesture and the user can't scroll
      // past the chart on mobile.
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
      width: initialWidth,
    })
    chartRef.current = chart

    // ---- OHLC candlesticks ----
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: PALETTE.bullish,
      downColor: PALETTE.bearish,
      borderVisible: false,
      wickUpColor: PALETTE.bullish,
      wickDownColor: PALETTE.bearish,
    })
    candles.setData(
      ohlcHistory.map((b) => ({
        time: b.date as Time,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    )

    // ---- Helper: zip indicator series to ohlc dates, drop null entries ----
    // Indicator arrays are aligned 1:1 to ohlc_history by index. Warmup
    // periods produce leading nulls (e.g. MA20[0..18] all null). We pair
    // (date, value) and filter out null/undefined so setData receives only
    // valid points (no gaps in the rendered line).
    const pairLines = (
      vals: ReadonlyArray<number | null>,
    ): { time: Time; value: number }[] => {
      const out: { time: Time; value: number }[] = []
      for (let i = 0; i < ohlcHistory.length; i++) {
        const v = vals[i]
        if (v != null && Number.isFinite(v)) {
          out.push({ time: ohlcHistory[i].date as Time, value: v })
        }
      }
      return out
    }

    // ---- MA20 (accent blue, solid) ----
    const ma20 = chart.addSeries(LineSeries, {
      color: PALETTE.accent,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    ma20.setData(pairLines(indicators.ma20))

    // ---- MA50 (muted gray, solid) ----
    const ma50 = chart.addSeries(LineSeries, {
      color: PALETTE.fgMuted,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    ma50.setData(pairLines(indicators.ma50))

    // ---- Bollinger Bands upper + lower (accent blue, dotted) ----
    const bbUpper = chart.addSeries(LineSeries, {
      color: PALETTE.accent,
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    bbUpper.setData(pairLines(indicators.bb_upper))

    const bbLower = chart.addSeries(LineSeries, {
      color: PALETTE.accent,
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    bbLower.setData(pairLines(indicators.bb_lower))

    // ---- RSI(14) on a separate price scale (sub-pane below main chart) ----
    // priceScaleId='rsi' moves the series to its own scale; scaleMargins
    // .top=0.78 + .bottom=0 gives the sub-pane the bottom ~22% of the chart.
    const rsi = chart.addSeries(LineSeries, {
      priceScaleId: 'rsi',
      color: PALETTE.amber,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    rsi.setData(pairLines(indicators.rsi14))
    chart.priceScale('rsi').applyOptions({
      scaleMargins: { top: 0.78, bottom: 0 },
      borderColor: PALETTE.border,
    })

    chart.timeScale().fitContent()

    // ---- Resize observer: keep chart width matched to container ----
    // Also recomputes height bracket on viewport changes (rotate phone /
    // resize desktop window across the sm/md/lg breakpoints).
    const resizeObs = new ResizeObserver((entries) => {
      for (const e of entries) {
        const w = e.contentRect.width
        const h = pickHeight(
          typeof window !== 'undefined' ? window.innerWidth : 1024,
          height,
        )
        chart.applyOptions({ width: w, height: h })
      }
    })
    resizeObs.observe(containerRef.current)

    return () => {
      resizeObs.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [ohlcHistory, indicators, height])

  return (
    <div
      ref={containerRef}
      className="w-full rounded-md border border-border bg-bg"
      data-testid="chart-container"
    />
  )
}
