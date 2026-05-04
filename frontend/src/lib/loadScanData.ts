import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'

import { fetchAndParse, indexUrl, snapshotUrl, statusUrl } from './fetchSnapshot'
import {
  SnapshotSchema,
  StatusSchema,
  type Snapshot,
  type Status,
} from '@/schemas'

// loadScanData — orchestrates the fan-out fetch behind the Morning Scan view.
//
// One scan-day requires N+2 GitHub raw fetches:
//   1. _status.json      (run-final sentinel)
//   2. _index.json       (lists tickers + run_completed_at + lite_mode)
//   3. {TICKER}.json × N (per-ticker snapshots)
//
// Promise.allSettled on the per-ticker fan-out so a single ticker JSON 404 or
// schema-mismatch doesn't crash the whole view (CONTEXT.md UNIFORM RULE —
// partial-data degradation, not crash). Failed tickers surface in the
// returned `failedTickers` array so ScanRoute can render the "Partial data —
// N/M tickers loaded (X failed)" banner above the lens.
//
// schema_version: z.literal(2) is enforced by SnapshotSchema. v1 snapshots
// raise SchemaMismatchError → settled with status='rejected' → captured in
// failedTickers. Wave 4 ErrorBoundary picks them up and renders the explicit
// "schema upgrade required" banner per CONTEXT.md UNIFORM RULE.

// IndexSchema lives in this file (not src/schemas/) because data/{date}/_index.json
// is a per-day artifact distinct from data/_dates.json (which has its own
// DatesIndexSchema). Two different files, two different shapes.
const IndexSchema = z.object({
  date: z.string(),
  schema_version: z.literal(2),
  run_started_at: z.string(),
  run_completed_at: z.string(),
  tickers: z.array(z.string()),
  lite_mode: z.boolean(),
  total_token_count_estimate: z.number().nonnegative(),
})
export type ScanIndex = z.infer<typeof IndexSchema>

export interface ScanData {
  status: Status
  index: ScanIndex
  snapshots: Record<string, Snapshot>
  failedTickers: string[]
}

async function loadScan(date: string): Promise<ScanData> {
  const [status, index] = await Promise.all([
    fetchAndParse(statusUrl(date), StatusSchema),
    fetchAndParse(indexUrl(date), IndexSchema),
  ])

  const settled = await Promise.allSettled(
    index.tickers.map(async (ticker) => {
      const snap = await fetchAndParse(snapshotUrl(date, ticker), SnapshotSchema)
      return [ticker, snap] as const
    }),
  )

  const snapshots: Record<string, Snapshot> = {}
  const failedTickers: string[] = []
  for (let i = 0; i < settled.length; i++) {
    const r = settled[i]
    if (r.status === 'fulfilled') {
      snapshots[r.value[0]] = r.value[1]
    } else {
      failedTickers.push(index.tickers[i])
    }
  }

  return { status, index, snapshots, failedTickers }
}

// useScanData — TanStack hook consumed by ScanRoute. Inherits the
// QueryClientProvider defaults from main.tsx (staleTime 5min, no refetch on
// window focus, retry 1).
export function useScanData(date: string) {
  return useQuery<ScanData, Error>({
    queryKey: ['scan', date],
    queryFn: () => loadScan(date),
  })
}

// Test-only export — the orchestrator function is the meat of this module
// (the hook is just a TanStack wrapper around it). We expose it under a
// `__` prefix to signal "internal, used by tests only" rather than
// promoting it to a public surface.
export const __loadScanForTest = loadScan

// Header staleness — Root.tsx fetches _status.json + _index.json in isolation
// to compute the staleness badge without depending on the per-ticker fan-out.
// The full ScanData query owns the per-ticker fetches; this lightweight pair
// is independent so the badge can render even if the per-ticker fan-out is
// still in flight.
export interface HeaderScanMeta {
  status: Status
  index: ScanIndex
}

async function loadHeaderMeta(date: string): Promise<HeaderScanMeta> {
  const [status, index] = await Promise.all([
    fetchAndParse(statusUrl(date), StatusSchema),
    fetchAndParse(indexUrl(date), IndexSchema),
  ])
  return { status, index }
}

export function useHeaderScanMeta(date: string) {
  return useQuery<HeaderScanMeta, Error>({
    queryKey: ['scan-header', date],
    queryFn: () => loadHeaderMeta(date),
  })
}
