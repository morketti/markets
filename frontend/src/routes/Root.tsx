import { Outlet, Link, useMatches } from 'react-router'

import { useHeaderScanMeta } from '@/lib/loadScanData'
import { StalenessBadge } from '@/components/StalenessBadge'

// Root — Wave 2 layout. Header now renders StalenessBadge populated from the
// _status.json + _index.json fetch for the currently-active scan date.
//
// Active date detection: useMatches scans the matched route hierarchy and
// pulls the :date param from /scan/:date or /ticker/:symbol/:date?. If no
// scan/ticker route is active (e.g. on `/`), default to 'today'.
//
// The staleness fetch is independent of ScanRoute's per-ticker fan-out
// (useScanData) — both use TanStack Query so they share cache for
// _status.json + _index.json on the same date.

function useActiveDate(): string {
  const matches = useMatches()
  for (const m of matches) {
    const params = m.params as { date?: string; symbol?: string }
    if (params?.date) return params.date
  }
  return 'today'
}

function HeaderStaleness() {
  const date = useActiveDate()
  const { data, isLoading, error } = useHeaderScanMeta(date)
  if (isLoading) {
    return (
      <span
        className="font-mono text-xs text-fg-muted"
        data-testid="staleness-loading"
      >
        —
      </span>
    )
  }
  if (error || !data) {
    return (
      <span
        className="font-mono text-xs text-fg-muted"
        data-testid="staleness-error"
      >
        —
      </span>
    )
  }
  return (
    <StalenessBadge
      snapshotIso={data.index.run_completed_at}
      partial={data.status.partial}
    />
  )
}

export default function Root() {
  return (
    <div className="flex min-h-full flex-col bg-bg text-fg">
      <header className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between gap-6">
          <Link
            to="/scan/today"
            className="font-mono text-sm font-semibold tracking-tight text-fg"
            data-testid="brand-link"
          >
            MARKETS
          </Link>
          <div
            data-testid="staleness-slot"
            className="flex items-center gap-3"
          >
            <HeaderStaleness />
          </div>
        </div>
      </header>
      <main className="flex-1 px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
