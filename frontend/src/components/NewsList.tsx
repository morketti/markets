import type { Snapshot } from '@/schemas'
import { cn } from '@/lib/utils'

// NewsList — renders snapshot.headlines grouped by source with within-group
// sort by published_at DESC (most recent first). Each headline is a click-
// through link opening in a new tab (target='_blank' rel='noopener noreferrer').
//
// VIEW-08 "since snapshot" delta: when a headline's published_at is newer
// than the snapshot's computed_at, render a "NEW" tag inline. This Wave 3
// renders the tag based on raw timestamp comparison; Phase 8 mid-day refresh
// adds the merge logic that surfaces post-snapshot headlines from a fresh
// fetch.
//
// Date parsing is defensive — RSS feeds return both ISO-8601 and RFC-822
// timestamps and we don't strictly enforce one format in the schema. If
// new Date(...) returns NaN we treat the headline as not-new (don't tag) and
// fall back to the raw string for display.

export interface NewsListProps {
  headlines: Snapshot['headlines']
  /** ISO-8601 string from snapshot ticker_decision.computed_at (or _index.json). */
  snapshotComputedAt: string
  className?: string
}

interface GroupedHeadlines {
  source: string
  items: Snapshot['headlines']
}

function groupBySource(headlines: Snapshot['headlines']): GroupedHeadlines[] {
  const map = new Map<string, Snapshot['headlines']>()
  for (const h of headlines) {
    const arr = map.get(h.source) ?? []
    arr.push(h)
    map.set(h.source, arr)
  }
  // Sort each group by published_at DESC (most recent first)
  const groups: GroupedHeadlines[] = []
  for (const [source, items] of map) {
    const sorted = [...items].sort((a, b) =>
      b.published_at.localeCompare(a.published_at),
    )
    groups.push({ source, items: sorted })
  }
  return groups
}

function parseTimestamp(s: string): number {
  const t = new Date(s).getTime()
  return Number.isNaN(t) ? 0 : t
}

function relativeShort(iso: string): string {
  const t = parseTimestamp(iso)
  if (t === 0) return iso
  return new Date(t).toISOString().slice(0, 10)
}

export function NewsList({
  headlines,
  snapshotComputedAt,
  className,
}: NewsListProps) {
  if (headlines.length === 0) {
    return (
      <div
        className="text-sm text-fg-muted"
        data-testid="news-list-empty"
      >
        No headlines for this ticker in the snapshot.
      </div>
    )
  }
  const groups = groupBySource(headlines)
  const snapshotMs = parseTimestamp(snapshotComputedAt)
  return (
    <div className={cn('flex flex-col gap-6', className)} data-testid="news-list">
      {groups.map(({ source, items }) => (
        <div key={source} data-testid="news-source-group" data-source={source}>
          <h3
            className="mb-3 font-mono text-xs uppercase tracking-wider text-fg-muted"
            data-testid="news-source-heading"
          >
            {source}
          </h3>
          <ul className="flex flex-col gap-3">
            {items.map((h) => {
              const headlineMs = parseTimestamp(h.published_at)
              const isNew = snapshotMs > 0 && headlineMs > snapshotMs
              return (
                <li
                  key={h.url}
                  className="flex items-start gap-3"
                  data-testid="news-item"
                  data-is-new={isNew ? 'true' : 'false'}
                >
                  {isNew && (
                    <span
                      className="mt-0.5 shrink-0 rounded border border-accent/40 bg-accent/20 px-2 py-0.5 font-mono text-xs text-accent"
                      data-testid="news-new-tag"
                    >
                      NEW
                    </span>
                  )}
                  <a
                    href={h.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="line-clamp-2 flex-1 text-sm text-fg hover:text-accent"
                    data-testid="news-title-link"
                  >
                    {h.title}
                  </a>
                  <time
                    className="shrink-0 font-mono text-xs text-fg-muted"
                    dateTime={h.published_at}
                    data-testid="news-published-at"
                  >
                    {relativeShort(h.published_at)}
                  </time>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </div>
  )
}
