// novel-to-this-project — Phase 8 frontend hero element. Replaces the
// Phase-7 PHASE-8-HOOK placeholder in DecisionRoute. Mounted ALSO on
// TickerRoute (08-CONTEXT.md researcher rec #1 — dual-timeframe focus).
// Preserves data-testid='current-price-placeholder' for grep-target
// continuity (Phase 7's E2E + DecisionRoute test grep that attribute).
//
// Notion-Clean palette discipline: every color via CSS variable tokens
// (text-fg, text-fg-muted, text-bullish, text-bearish, border-border,
// bg-surface). NO inline hex. NO tw-arbitrary values.
//
// Render branches (locked by tests):
//   1. isPending      → muted "Refreshing {symbol}…"
//   2. isError OR full-failure envelope → muted "Refresh unavailable —
//      showing snapshot price" with snapshot price as fallback
//   3. Success/partial → current_price + delta % vs snapshotLastPrice +
//      "Refreshed Ns ago" footer; partial w/ rss-unavailable adds
//      "Headlines unavailable" footnote
//
// Snapshot stays canonical: when refresh fails we ALWAYS render the
// snapshot baseline (or em-dash if absent). NEVER throw, NEVER white-screen.

import { useRefreshData } from '@/lib/useRefreshData'
import { isRefreshFailure } from '@/schemas/refresh'

interface CurrentPriceDeltaProps {
  symbol: string
  /** Snapshot baseline price for delta math. Falls back to em-dash if absent. */
  snapshotLastPrice?: number | null
  /** Snapshot computed_at — reserved for future "as of" tooltip; unused in v1. */
  snapshotComputedAt?: string
}

const PLACEHOLDER_TESTID = 'current-price-placeholder'

const fmtPrice = (n: number | null | undefined): string =>
  typeof n === 'number' && Number.isFinite(n) ? `$${n.toFixed(2)}` : '$—'

export function CurrentPriceDelta({
  symbol,
  snapshotLastPrice,
}: CurrentPriceDeltaProps) {
  const { data, isPending, isError, dataUpdatedAt } = useRefreshData(symbol)

  // 1. Loading branch — muted placeholder, testid preserved.
  if (isPending) {
    return (
      <div
        data-testid={PLACEHOLDER_TESTID}
        className="rounded-md border border-dashed border-border bg-surface px-4 py-3 text-sm text-fg-muted"
      >
        Refreshing {symbol}…
      </div>
    )
  }

  // 2. Failure branch — isError (network/HTTP/zod failure) OR full-failure
  //    envelope (api/refresh.py returned error: true). Snapshot stays canonical.
  const isFailureEnvelope = data !== undefined && isRefreshFailure(data)
  if (isError || isFailureEnvelope) {
    const baseline = fmtPrice(snapshotLastPrice ?? null)
    return (
      <div
        data-testid={PLACEHOLDER_TESTID}
        className="rounded-md border border-dashed border-border bg-surface px-4 py-3 text-sm text-fg-muted"
      >
        <span className="font-mono">{baseline}</span>{' '}
        <span className="italic">
          Refresh unavailable — showing snapshot price.
        </span>
      </div>
    )
  }

  // 3. Success / partial branch — `data` has current_price (narrowed by
  //    the negative-failure check above). Render hero price + delta.
  if (data === undefined || isRefreshFailure(data)) {
    // Belt-and-suspenders — should be unreachable, but never crash.
    return (
      <div
        data-testid={PLACEHOLDER_TESTID}
        className="rounded-md border border-dashed border-border bg-surface px-4 py-3 text-sm text-fg-muted"
      >
        <span className="italic">Refresh unavailable — showing snapshot price.</span>
      </div>
    )
  }

  const current = data.current_price
  const hasBaseline =
    typeof snapshotLastPrice === 'number' &&
    Number.isFinite(snapshotLastPrice) &&
    snapshotLastPrice > 0
  const deltaPct = hasBaseline
    ? ((current - (snapshotLastPrice as number)) /
        (snapshotLastPrice as number)) *
      100
    : null

  let deltaClass = 'text-fg-muted'
  if (deltaPct != null) {
    if (deltaPct > 0) deltaClass = 'text-bullish'
    else if (deltaPct < 0) deltaClass = 'text-bearish'
    // zero → muted (neutral)
  }

  const refreshedSecondsAgo = dataUpdatedAt
    ? Math.max(0, Math.round((Date.now() - dataUpdatedAt) / 1000))
    : 0

  const headlinesUnavailable =
    data.partial && data.errors.includes('rss-unavailable')

  return (
    <div
      data-testid={PLACEHOLDER_TESTID}
      className="rounded-md border border-border bg-surface px-4 py-3"
    >
      <div className="flex items-baseline gap-3">
        <span
          className="font-mono text-2xl font-semibold text-fg"
          data-testid="current-price-value"
        >
          {fmtPrice(current)}
        </span>
        {deltaPct != null && (
          <span
            data-testid="price-delta"
            className={`font-mono text-lg font-medium ${deltaClass}`}
          >
            {deltaPct > 0 ? '+' : ''}
            {deltaPct.toFixed(2)}%
          </span>
        )}
      </div>
      <p className="mt-1 text-xs text-fg-muted">
        Refreshed {refreshedSecondsAgo}s ago
        {headlinesUnavailable && (
          <span className="ml-2 italic">· Headlines unavailable</span>
        )}
      </p>
    </div>
  )
}
