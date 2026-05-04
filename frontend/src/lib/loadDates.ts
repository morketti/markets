import { useQuery } from '@tanstack/react-query'

import { datesUrl, fetchAndParse } from './fetchSnapshot'
import { DatesIndexSchema, type DatesIndex } from '@/schemas'

// loadDates — TanStack Query hook for the data/_dates.json index.
//
// data/_dates.json is the Wave 0 file written by routine/storage.py at the
// snapshots root (not date-scoped). It enumerates all available scan dates
// so the DateSelector can render a dropdown without Listing GitHub directories.
//
// staleTime is short (1 min) — _dates.json is small + cheap to refetch and
// updates exactly once per routine run; we don't want a stale list when the
// user opens the app shortly after a new snapshot lands.
//
// Errors NOT thrown into the ErrorBoundary: the dates index is load-bearing
// for nothing (it's purely UX — the DateSelector renders an empty dropdown
// gracefully). Components consume `useDates()` and check `data` themselves.

export function useDates() {
  return useQuery<DatesIndex, Error>({
    queryKey: ['dates'],
    queryFn: () => fetchAndParse(datesUrl(), DatesIndexSchema),
    staleTime: 60 * 1000,
    retry: false,
  })
}

// Test-only export — direct call into the loader so unit tests don't need a
// QueryClientProvider wrapper.
async function loadDates(): Promise<DatesIndex> {
  return fetchAndParse(datesUrl(), DatesIndexSchema)
}

export const __loadDatesForTest = loadDates
