import { useRef } from 'react'
import { Outlet, Link, useMatches, useNavigate } from 'react-router'

import { useHeaderScanMeta } from '@/lib/loadScanData'
import { StalenessBadge } from '@/components/StalenessBadge'

// Root — Wave 2-3 layout. Header renders:
//   - brand link (left)
//   - ticker search input (VIEW-13 — Wave 3) — type-then-Enter navigates to
//     /ticker/:typed/:date
//   - StalenessBadge (right) populated from _status.json + _index.json fetch
//     for the currently-active scan date
//
// Active date detection: useMatches scans the matched route hierarchy and
// pulls the :date param from /scan/:date or /ticker/:symbol/:date?. If no
// scan/ticker route is active (e.g. on `/`), default to 'today'.
//
// VIEW-13 typeahead surface: v1 is intentionally simple — direct text→
// /ticker/:symbol navigation on Enter. Company-name fuzzy match is v1.x;
// yfinance ticker symbols are the v1 search surface (the routine consumes
// ticker symbols anyway). The input uppercases the value at submit time so
// "aapl" → "AAPL" matches the Phase 5 storage path layout.

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

function TickerSearch() {
  const navigate = useNavigate()
  const date = useActiveDate()
  const inputRef = useRef<HTMLInputElement>(null)

  function submit() {
    const v = inputRef.current?.value.trim().toUpperCase() ?? ''
    if (!v) return
    navigate(`/ticker/${v}/${date}`)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <input
      ref={inputRef}
      type="text"
      placeholder="Ticker (e.g. AAPL)"
      className="w-40 rounded border border-border bg-bg px-3 py-1.5 font-mono text-sm uppercase placeholder:text-fg-muted placeholder:normal-case focus:border-accent focus:outline-none"
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          e.preventDefault()
          submit()
        }
      }}
      data-testid="ticker-search-input"
      aria-label="Search ticker"
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
          <div className="flex items-center gap-3">
            <TickerSearch />
            <div
              data-testid="staleness-slot"
              className="flex items-center gap-3"
            >
              <HeaderStaleness />
            </div>
          </div>
        </div>
      </header>
      <main className="flex-1 px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
