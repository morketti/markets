import { useQuery } from '@tanstack/react-query'

import { fetchAndParse, snapshotUrl } from './fetchSnapshot'
import { SnapshotSchema, type Snapshot } from '@/schemas'

// loadTickerData — TanStack Query hook for the per-ticker deep-dive view.
//
// Fetches data/{date}/{ticker}.json and zod-validates against SnapshotSchema
// (schema_version: z.literal(2) — strict). Failure modes (FetchNotFoundError /
// SchemaMismatchError / generic Error) are surfaced as `error` from the hook
// — TickerRoute distinguishes them for UI.
//
// queryKey: ['ticker', date, symbol] — TanStack Query cache de-dupes across
// remount + back-button navigation. The same key was already loaded by
// useScanData's per-ticker fan-out for the same date+ticker, but the
// cache key is different ('scan' vs 'ticker') so they don't share. v1.x can
// optimize by populating the per-ticker cache from useScanData's result; v1
// just fetches independently (~30s GitHub raw CDN edge cache makes this
// effectively free).

export function useTickerData(date: string, symbol: string) {
  return useQuery<Snapshot, Error>({
    queryKey: ['ticker', date, symbol],
    queryFn: () => fetchAndParse(snapshotUrl(date, symbol), SnapshotSchema),
    // Inherits 5min staleTime from QueryClient defaults (main.tsx).
  })
}

// Test-only export — the orchestrator function for unit tests without
// QueryClient setup. Mirrors the loadScanData pattern (`__` prefix signals
// internal-for-testing).
export const __loadTickerForTest = (date: string, symbol: string): Promise<Snapshot> =>
  fetchAndParse(snapshotUrl(date, symbol), SnapshotSchema)
