import { computeStaleness, type StalenessLevel } from '@/lib/staleness'
import { Badge } from './ui/badge'
import { cn } from '@/lib/utils'

// StalenessBadge — header badge per VIEW-11.
//
// Inputs: snapshotIso (run_completed_at from _index.json) + partial flag
// (from _status.json). Computes GREEN/AMBER/RED via lib/staleness and
// applies Notion-Clean palette tokens via the COLOR map below.
//
// The shadcn Badge primitive ships with default `bg-primary` etc. styling we
// don't want — we pass `variant="outline"` (which only sets `text-foreground`
// border) and override className entirely with our state-color class. The
// `title` attribute carries the human-readable detail (snapshot age + partial
// detail) for hover tooltip; Wave 4 may swap to a Radix Tooltip primitive.
//
// Color tokens come from src/index.css @theme directive:
//   --color-bullish: #4ADE80   → GREEN dot/text
//   --color-amber:   #FBBF24   → AMBER dot/text
//   --color-bearish: #F87171   → RED dot/text
// Background uses /10 alpha and border /30 alpha for subtle Notion-Clean fill.

export interface StalenessBadgeProps {
  snapshotIso: string
  partial: boolean
  // `now` is injectable for deterministic tests — defaults to live Date.
  now?: Date
}

const COLOR: Record<StalenessLevel, string> = {
  GREEN: 'bg-bullish/10 text-bullish border-bullish/30',
  AMBER: 'bg-amber/10 text-amber border-amber/30',
  RED: 'bg-bearish/10 text-bearish border-bearish/30',
}

export function StalenessBadge({ snapshotIso, partial, now }: StalenessBadgeProps) {
  const level = computeStaleness(snapshotIso, partial, now)
  const refMs = (now ?? new Date()).getTime()
  const snapMs = new Date(snapshotIso).getTime()
  const ageHrs = Number.isFinite(snapMs)
    ? ((refMs - snapMs) / 3_600_000).toFixed(1)
    : '?'
  const tooltip = `Snapshot age ${ageHrs}h${partial ? ' · partial' : ''}`
  return (
    <Badge
      variant="outline"
      className={cn('font-mono', COLOR[level])}
      title={tooltip}
      data-testid="staleness-badge"
      data-level={level}
    >
      {level}
    </Badge>
  )
}
