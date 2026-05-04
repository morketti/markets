// novel-to-this-project — TanStack Query hook for the on-open refresh.
// Mounted on TickerRoute AND DecisionRoute; queryKey ['refresh', symbol]
// dedupes across the two routes (08-CONTEXT.md researcher rec #1 lock —
// dual-timeframe focus user opens both views; one fetch per symbol).
//
// keepPreviousData (placeholderData: keepPreviousData) is the v5 idiom —
// when the symbol changes, the previous symbol's data lingers in `data`
// until the new fetch resolves, preventing UI flicker on ticker swap.
//
// retry: 1 → on transient 5xx / network error, try once more before
// surfacing isError to the UI. Combined with the snapshot-stays-canonical
// fallback in <CurrentPriceDelta />, an actual hard failure surfaces as a
// muted "Refresh unavailable" notice — never a crash.

import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { fetchAndParse } from '@/lib/fetchSnapshot'
import { RefreshResponseSchema, type RefreshResponse } from '@/schemas/refresh'

// Same-origin path. In Vercel preview/prod the SPA-rewrite narrowing
// (frontend/vercel.json /((?!api/).*)) ensures /api/refresh is NOT
// rewritten to /index.html. In dev (Vite) the function is unavailable; the
// component is expected to render the snapshot fallback path.
export const refreshUrl = (symbol: string): string =>
  `/api/refresh?ticker=${encodeURIComponent(symbol)}`

export function useRefreshData(symbol: string) {
  return useQuery<RefreshResponse>({
    queryKey: ['refresh', symbol],
    queryFn: () => fetchAndParse(refreshUrl(symbol), RefreshResponseSchema),
    staleTime: 5 * 60 * 1000, // 5 min — refresh once per ticker view
    placeholderData: keepPreviousData, // no flicker on symbol swap
    retry: 1,
    enabled: symbol.length > 0,
  })
}
