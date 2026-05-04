// Test fixture builders for loadScanData tests + lens component tests.
//
// Hand-rolled minimal-shape JSON that round-trips through SnapshotSchema.
// Each builder returns a fresh object so tests can mutate without polluting
// other tests.
//
// We import loadScanData here AND re-export the internal loadScan via a thin
// re-export shim. loadScanData.ts doesn't export loadScan directly (it's only
// the queryFn impl), but the test needs to call it without a QueryClient.

import type { Snapshot, Status } from '@/schemas'
import type { ScanIndex } from '../loadScanData'

export function makeStatus(tickers: string[], partial = false): Status {
  return {
    success: !partial,
    partial,
    completed_tickers: partial ? tickers.slice(0, -1) : [...tickers],
    failed_tickers: partial && tickers.length > 0 ? [tickers[tickers.length - 1]] : [],
    skipped_tickers: [],
    llm_failure_count: 0,
    lite_mode: false,
  }
}

export function makeIndex(
  tickers: string[],
  overrides: Partial<ScanIndex> = {},
): ScanIndex {
  const completedAt = new Date(Date.now() - 2 * 3_600_000).toISOString()
  const startedAt = new Date(Date.now() - 2.5 * 3_600_000).toISOString()
  return {
    date: '2026-05-04',
    schema_version: 2,
    run_started_at: startedAt,
    run_completed_at: completedAt,
    tickers: [...tickers],
    lite_mode: false,
    total_token_count_estimate: 12345,
    ...overrides,
  }
}

// Snapshot fixture — minimum-viable v2 shape that passes SnapshotSchema.
// Tests can mutate any field on the returned object before passing it to
// jsonResponse(). Defaults: position_signal/ticker_decision filled with
// realistic AAPL-like values; analytical_signals + persona_signals empty
// arrays; ohlc_history single-bar; indicators single-null arrays; headlines
// empty.
export function makeSnapshot(
  ticker: string,
  overrides: Partial<Snapshot> = {},
): Snapshot {
  const computedAt = new Date().toISOString()
  return {
    ticker,
    schema_version: 2,
    analytical_signals: [],
    position_signal: {
      ticker,
      computed_at: computedAt,
      state: 'fair',
      consensus_score: 0,
      confidence: 0,
      action_hint: 'hold_position',
      indicators: { rsi14: null, bb_position: null },
      evidence: [],
      data_unavailable: true,
      trend_regime: false,
    },
    persona_signals: [],
    ticker_decision: {
      ticker,
      computed_at: computedAt,
      schema_version: 2,
      recommendation: 'hold',
      conviction: 'low',
      short_term: {
        summary: 'placeholder',
        drivers: [],
        confidence: 0,
        thesis_status: 'n/a',
      },
      long_term: {
        summary: 'placeholder',
        drivers: [],
        confidence: 0,
        thesis_status: 'n/a',
      },
      open_observation: '',
      dissent: { has_dissent: false, dissenting_persona: null, dissent_summary: '' },
      data_unavailable: true,
    },
    ohlc_history: [
      { date: '2026-05-01', open: 100, high: 101, low: 99, close: 100, volume: 1000 },
    ],
    indicators: {
      ma20: [null],
      ma50: [null],
      bb_upper: [null],
      bb_lower: [null],
      rsi14: [null],
    },
    headlines: [],
    errors: [],
    ...overrides,
  } as Snapshot
}

// Lens-fixture variants — used by Lens component tests + Playwright E2E.
//
// makePositionRich: position_signal fully populated with given consensus_score
// and state/action_hint so PositionLens has something to sort.
export function makePositionRich(
  ticker: string,
  consensus_score: number,
  opts: {
    state?:
      | 'extreme_oversold'
      | 'oversold'
      | 'fair'
      | 'overbought'
      | 'extreme_overbought'
    action_hint?:
      | 'consider_add'
      | 'hold_position'
      | 'consider_trim'
      | 'consider_take_profits'
    confidence?: number
    evidence?: string[]
    short_term_recommendation?:
      | 'add'
      | 'trim'
      | 'hold'
      | 'take_profits'
      | 'buy'
      | 'avoid'
    short_term_confidence?: number
    long_term_thesis_status?: 'intact' | 'weakening' | 'broken' | 'improving' | 'n/a'
    long_term_confidence?: number
  } = {},
): Snapshot {
  const computedAt = new Date().toISOString()
  return {
    ticker,
    schema_version: 2,
    analytical_signals: [],
    position_signal: {
      ticker,
      computed_at: computedAt,
      state: opts.state ?? 'fair',
      consensus_score,
      confidence: opts.confidence ?? 60,
      action_hint: opts.action_hint ?? 'hold_position',
      indicators: { rsi14: 50, bb_position: 0 },
      evidence: opts.evidence ?? [
        'sample evidence 1',
        'sample evidence 2',
        'sample evidence 3',
      ],
      data_unavailable: false,
      trend_regime: false,
    },
    persona_signals: [],
    ticker_decision: {
      ticker,
      computed_at: computedAt,
      schema_version: 2,
      recommendation: opts.short_term_recommendation ?? 'hold',
      conviction: 'medium',
      short_term: {
        summary: `${ticker} short-term summary`,
        drivers: [`${ticker} driver 1`, `${ticker} driver 2`],
        confidence: opts.short_term_confidence ?? 50,
        thesis_status: 'n/a',
      },
      long_term: {
        summary: `${ticker} long-term summary`,
        drivers: [`${ticker} long driver 1`, `${ticker} long driver 2`],
        confidence: opts.long_term_confidence ?? 50,
        thesis_status: opts.long_term_thesis_status ?? 'intact',
      },
      open_observation: '',
      dissent: { has_dissent: false, dissenting_persona: null, dissent_summary: '' },
      data_unavailable: false,
    },
    ohlc_history: [
      { date: '2026-05-01', open: 100, high: 101, low: 99, close: 100, volume: 1000 },
    ],
    indicators: {
      ma20: [null],
      ma50: [null],
      bb_upper: [null],
      bb_lower: [null],
      rsi14: [null],
    },
    headlines: [],
    errors: [],
  } as Snapshot
}

// loadScanModule — a thin re-import shim so the test can call the internal
// loadScan without a QueryClient. We expose loadScan via a dynamic import
// and a hand-rolled re-export at the bottom of loadScanData.ts (added below
// only for testability).
export async function loadScanModule() {
  const mod = await import('../loadScanData')
  return {
    loadScan: (mod as unknown as { __loadScanForTest: (d: string) => Promise<unknown> })
      .__loadScanForTest,
    makeStatus,
    makeIndex,
    makeSnapshot,
  } as {
    loadScan: (date: string) => Promise<{
      status: Status
      index: ScanIndex
      snapshots: Record<string, Snapshot>
      failedTickers: string[]
    }>
    makeStatus: typeof makeStatus
    makeIndex: typeof makeIndex
    makeSnapshot: typeof makeSnapshot
  }
}
