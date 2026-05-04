import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'

// Chart tests — mock lightweight-charts createChart() and the SeriesDefinition
// exports so we can inspect what setData calls receive without booting an
// actual canvas (lightweight-charts requires WebGL/canvas which jsdom lacks).
//
// Coverage goals:
//   1. Component renders a div with data-testid='chart-container'.
//   2. setData receives candles built from the full ohlc_history.
//   3. setData on indicator lines drops null entries (warmup-period nulls
//      from snapshot.indicators.ma20[0..18]) — this is the load-bearing
//      pairLines() invariant.
//   4. RSI sub-pane gets its priceScale margins applied.
//   5. chart.remove() is called on unmount (cleanup discipline).

// --- Mock setup ---
// Each setData call records (seriesType, data) into setDataCalls so the test
// can assert on both shape and ordering. Each addSeries call records
// (definitionTag, options).

interface RecordedSetData {
  seriesType: string
  data: unknown[]
}
interface RecordedAddSeries {
  definition: string
  options: Record<string, unknown> | undefined
}
interface RecordedPriceScale {
  id: string
  applied: Record<string, unknown>
}

const setDataCalls: RecordedSetData[] = []
const addSeriesCalls: RecordedAddSeries[] = []
const priceScaleApplied: RecordedPriceScale[] = []
const removeCalls: number[] = []
const timeScaleFits: number[] = []

vi.mock('lightweight-charts', () => {
  // SeriesDefinition tags — match the export names.
  const CandlestickSeries = { type: 'Candlestick' } as const
  const LineSeries = { type: 'Line' } as const

  function makeSeries(seriesType: string) {
    return {
      setData: (data: unknown[]) => {
        setDataCalls.push({ seriesType, data })
      },
      applyOptions: () => {},
    }
  }

  function createChart(_container: HTMLElement, _options: unknown) {
    let removed = 0
    return {
      addSeries: (
        definition: { type: string },
        options: Record<string, unknown> | undefined,
      ) => {
        addSeriesCalls.push({ definition: definition.type, options })
        return makeSeries(definition.type)
      },
      priceScale: (id: string) => ({
        applyOptions: (applied: Record<string, unknown>) => {
          priceScaleApplied.push({ id, applied })
        },
      }),
      timeScale: () => ({ fitContent: () => timeScaleFits.push(Date.now()) }),
      applyOptions: () => {},
      remove: () => {
        removed++
        removeCalls.push(removed)
      },
    }
  }

  return {
    createChart,
    CandlestickSeries,
    LineSeries,
    ColorType: { Solid: 'solid' },
    LineStyle: { Solid: 0, Dotted: 2, Dashed: 1 },
  }
})

// ResizeObserver doesn't exist in jsdom — minimal polyfill.
class MockResizeObserver {
  observe(): void {}
  disconnect(): void {}
  unobserve(): void {}
}
;(globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
  MockResizeObserver

// Import AFTER the mock is registered.
import { Chart } from '../Chart'
import type { Snapshot } from '@/schemas'

function makeOhlc(n: number): Snapshot['ohlc_history'] {
  const out: Snapshot['ohlc_history'] = []
  for (let i = 0; i < n; i++) {
    const day = String(i + 1).padStart(2, '0')
    const base = 100 + i * 0.1
    out.push({
      date: `2026-04-${day}`,
      open: base,
      high: base + 1,
      low: base - 1,
      close: base + 0.5,
      volume: 1_000_000,
    })
  }
  return out
}

// 30-bar fixture; ma20 has nulls in the first 19 entries (warmup), values in
// the last 11. The component MUST drop the nulls before passing to setData.
function makeIndicators(n: number, warmup: number): Snapshot['indicators'] {
  const filled = (start: number) =>
    Array.from({ length: n }, (_, i) => (i < start ? null : 100 + i * 0.5))
  return {
    ma20: filled(warmup),
    ma50: filled(warmup),
    bb_upper: filled(warmup),
    bb_lower: filled(warmup),
    rsi14: filled(warmup),
  }
}

describe('Chart', () => {
  beforeEach(() => {
    setDataCalls.length = 0
    addSeriesCalls.length = 0
    priceScaleApplied.length = 0
    removeCalls.length = 0
    timeScaleFits.length = 0
  })

  it('renders a container div with data-testid', () => {
    const { getByTestId } = render(
      <Chart ohlcHistory={makeOhlc(5)} indicators={makeIndicators(5, 0)} />,
    )
    expect(getByTestId('chart-container')).toBeInTheDocument()
  })

  it('passes the full ohlc_history to the candlestick series setData', () => {
    const ohlc = makeOhlc(30)
    render(<Chart ohlcHistory={ohlc} indicators={makeIndicators(30, 19)} />)
    const candle = setDataCalls.find((c) => c.seriesType === 'Candlestick')
    expect(candle).toBeDefined()
    expect(candle!.data).toHaveLength(30)
    const first = candle!.data[0] as Record<string, unknown>
    expect(first.time).toBe('2026-04-01')
    expect(first.open).toBe(100)
  })

  it('drops null indicator entries before passing to setData (pairLines invariant)', () => {
    const ohlc = makeOhlc(30)
    // Warmup of 19 → first 19 entries null on each indicator series → setData
    // should receive 11 (= 30 - 19) non-null pairs.
    render(<Chart ohlcHistory={ohlc} indicators={makeIndicators(30, 19)} />)
    // 4 line series for MA20 / MA50 / BB upper / BB lower + 1 for RSI = 5 total
    const lineCalls = setDataCalls.filter((c) => c.seriesType === 'Line')
    expect(lineCalls).toHaveLength(5)
    for (const lc of lineCalls) {
      expect(lc.data).toHaveLength(11)
      // First non-null bar is at index 19 → date '2026-04-20'
      const first = lc.data[0] as Record<string, unknown>
      expect(first.time).toBe('2026-04-20')
    }
  })

  it('applies scaleMargins on the rsi sub-pane priceScale', () => {
    render(
      <Chart ohlcHistory={makeOhlc(20)} indicators={makeIndicators(20, 14)} />,
    )
    const rsi = priceScaleApplied.find((p) => p.id === 'rsi')
    expect(rsi).toBeDefined()
    const margins = rsi!.applied.scaleMargins as { top: number; bottom: number }
    expect(margins.top).toBeGreaterThan(0.7)
    expect(margins.bottom).toBe(0)
  })

  it('calls chart.remove() on unmount', () => {
    const { unmount } = render(
      <Chart ohlcHistory={makeOhlc(5)} indicators={makeIndicators(5, 0)} />,
    )
    expect(removeCalls).toHaveLength(0)
    unmount()
    expect(removeCalls).toHaveLength(1)
  })

  it('adds 5 line series + 1 candlestick series total', () => {
    render(
      <Chart ohlcHistory={makeOhlc(20)} indicators={makeIndicators(20, 14)} />,
    )
    const candles = addSeriesCalls.filter((c) => c.definition === 'Candlestick')
    const lines = addSeriesCalls.filter((c) => c.definition === 'Line')
    expect(candles).toHaveLength(1)
    expect(lines).toHaveLength(5) // ma20 + ma50 + bb_upper + bb_lower + rsi14
  })
})
