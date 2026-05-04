// novel-to-this-project — Phase 9 Decision-Route panel rendering last-90-days
// endorsements per ticker. NO performance number per ENDORSE-03 (deferred to
// v1.x ENDORSE-06). Notion-Clean palette discipline: every color is a CSS
// variable token (text-fg / text-fg-muted / border-border / bg-surface /
// bg-bg). Zero inline hex.
//
// 4 render branches: loading / error / empty / populated. The component
// receives data already filtered + sorted by useEndorsements (select callback
// in loadEndorsements.ts) — it does NOT re-shuffle.

import { useEndorsements } from '@/lib/loadEndorsements'
import type { Endorsement } from '@/schemas/endorsement'

interface EndorsementsListProps {
  symbol: string
}

export function EndorsementsList({ symbol }: EndorsementsListProps) {
  const { data, isLoading, isError } = useEndorsements(symbol)

  if (isLoading) {
    return (
      <section
        className="rounded-md border border-border bg-surface px-6 py-4"
        data-testid="endorsements-loading"
      >
        <span className="font-mono text-xs uppercase tracking-wider text-fg-muted">
          Endorsements
        </span>
        <p className="mt-2 text-sm text-fg-muted">Loading…</p>
      </section>
    )
  }

  if (isError) {
    return (
      <section
        className="rounded-md border border-border bg-surface px-6 py-4"
        data-testid="endorsements-error"
      >
        <span className="font-mono text-xs uppercase tracking-wider text-fg-muted">
          Endorsements
        </span>
        <p className="mt-2 text-sm text-fg-muted">Endorsements unavailable</p>
      </section>
    )
  }

  const items = data ?? []

  return (
    <section
      className="rounded-md border border-border bg-surface px-6 py-4"
      data-testid="endorsements-list"
    >
      <span className="font-mono text-xs uppercase tracking-wider text-fg-muted">
        Endorsements (last 90 days)
      </span>
      {items.length === 0 ? (
        <p className="mt-3 text-sm leading-relaxed text-fg-muted">
          No endorsements captured for {symbol.toUpperCase()} in the last 90
          days. Use{' '}
          <code className="font-mono text-xs">markets add_endorsement</code> to
          capture one.
        </p>
      ) : (
        <ul className="mt-3 flex flex-col gap-4">
          {items.map((e) => (
            <EndorsementCard
              key={`${e.source}-${e.date}-${e.captured_at}`}
              e={e}
            />
          ))}
        </ul>
      )}
    </section>
  )
}

function EndorsementCard({ e }: { e: Endorsement }) {
  return (
    <li
      className="rounded-md border border-border bg-bg p-4"
      data-testid="endorsement-card"
    >
      <header className="text-sm font-medium text-fg">{e.source}</header>
      <p className="mt-1 font-mono text-xs text-fg-muted">
        {e.date} · ${e.price_at_call.toFixed(2)}
      </p>
      {e.notes && (
        <p className="mt-2 text-sm leading-relaxed text-fg">{e.notes}</p>
      )}
      <p className="mt-2 text-xs text-fg-muted">
        captured {formatRelative(e.captured_at)}
      </p>
    </li>
  )
}

function formatRelative(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return 'recently'
  const days = Math.floor((Date.now() - then) / (24 * 60 * 60 * 1000))
  if (days < 1) return 'today'
  if (days === 1) return '1 day ago'
  return `${days} days ago`
}
