import type { ThesisStatus, TimeframeBand } from '@/schemas'
import { Badge } from './ui/badge'
import { Card, CardContent, CardHeader } from './ui/card'
import { cn } from '@/lib/utils'

// DriversList — short_term + long_term drivers as a two-card pair (lg:flex-row,
// stacked on mobile). Empty drivers render 'No drivers surfaced' INSIDE the
// card; UNIFORM RULE (CONTEXT.md) — never silently absent / never collapsed.
// Pattern adapted from TickerRoute.tsx line 142 TimeframeCard pair layout
// (Phase 6 deep-dive). DECOUPLED from TimeframeCard: the recommendation IS
// the summary in DecisionRoute, so the body renders only drivers (the
// summary + thesis_status + confidence header is preserved as a small label
// row, but no body summary paragraph — the recommendation banner above
// already carries the synthesis verdict).

const STATUS_COLOR: Record<ThesisStatus, string> = {
  intact: 'bg-bullish/10 text-bullish border-bullish/30',
  improving: 'bg-bullish/10 text-bullish border-bullish/30',
  weakening: 'bg-amber/10 text-amber border-amber/30',
  broken: 'bg-bearish/10 text-bearish border-bearish/30',
  'n/a': 'bg-fg-muted/10 text-fg-muted border-fg-muted/30',
}

interface DriverCardProps {
  timeframe: 'short_term' | 'long_term'
  label: string
  band: TimeframeBand
}

function DriverCard({ timeframe, label, band }: DriverCardProps) {
  return (
    <Card
      className="flex-1 border-border bg-surface text-fg shadow-none"
      data-testid="drivers-card"
      data-timeframe={timeframe}
      data-thesis-status={band.thesis_status}
    >
      <CardHeader className="flex flex-row items-center justify-between gap-4 p-6 pb-3">
        <div className="font-mono text-xs uppercase tracking-wider text-fg-muted">
          {label}
        </div>
        <div className="flex items-center gap-3">
          <Badge
            variant="outline"
            className={cn('font-mono', STATUS_COLOR[band.thesis_status])}
            data-testid="drivers-thesis-status"
          >
            {band.thesis_status}
          </Badge>
          <span
            className="font-mono text-xs text-fg-muted"
            data-testid="drivers-confidence"
          >
            conf {band.confidence}
          </span>
        </div>
      </CardHeader>
      <CardContent className="p-6 pt-0">
        {band.drivers.length === 0 ? (
          <p
            data-testid="drivers-empty"
            className="text-sm italic text-fg-muted"
          >
            No drivers surfaced
          </p>
        ) : (
          <ul className="ml-4 list-disc space-y-1 text-sm text-fg-muted">
            {band.drivers.map((d, i) => (
              <li key={i} className="font-mono">
                {d}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

export interface DriversListProps {
  shortTerm: TimeframeBand
  longTerm: TimeframeBand
  className?: string
}

export function DriversList({
  shortTerm,
  longTerm,
  className,
}: DriversListProps) {
  return (
    <div
      className={cn('flex flex-col gap-6 lg:flex-row', className)}
      data-testid="drivers-list"
    >
      <DriverCard
        timeframe="short_term"
        label="Short-term drivers"
        band={shortTerm}
      />
      <DriverCard
        timeframe="long_term"
        label="Long-term drivers"
        band={longTerm}
      />
    </div>
  )
}
