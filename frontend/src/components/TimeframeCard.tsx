import type { ThesisStatus, TimeframeBand } from '@/schemas'
import { Badge } from './ui/badge'
import { Card, CardContent, CardHeader } from './ui/card'
import { cn } from '@/lib/utils'

// TimeframeCard — renders one TimeframeBand (short_term OR long_term) as a
// card for the deep-dive view. Two TimeframeCards live side-by-side at the
// top of TickerRoute (below OpenClaudePin) per VIEW-05.
//
// Layout: header row with label (e.g. "Short-Term (1w-1m)") + thesis_status
// badge + confidence. Body: summary paragraph + drivers bullet list (top 5).
//
// thesis_status color mapping mirrors the directional-state color tokens:
//   intact / improving → bullish (positive thesis posture)
//   weakening          → amber (warning)
//   broken             → bearish (urgent)
//   n/a                → fg-muted (no opinion / lite-mode)

const STATUS_COLOR: Record<ThesisStatus, string> = {
  intact: 'bg-bullish/10 text-bullish border-bullish/30',
  improving: 'bg-bullish/10 text-bullish border-bullish/30',
  weakening: 'bg-amber/10 text-amber border-amber/30',
  broken: 'bg-bearish/10 text-bearish border-bearish/30',
  'n/a': 'bg-fg-muted/10 text-fg-muted border-fg-muted/30',
}

export interface TimeframeCardProps {
  label: string
  band: TimeframeBand
  className?: string
}

export function TimeframeCard({ label, band, className }: TimeframeCardProps) {
  return (
    <Card
      className={cn(
        'flex-1 border-border bg-surface text-fg shadow-none',
        className,
      )}
      data-testid="timeframe-card"
      data-thesis-status={band.thesis_status}
    >
      <CardHeader className="flex flex-row items-center justify-between gap-4 p-6 pb-3">
        <div className="font-medium" data-testid="timeframe-label">
          {label}
        </div>
        <div className="flex items-center gap-3">
          <Badge
            variant="outline"
            className={cn('font-mono', STATUS_COLOR[band.thesis_status])}
            data-testid="thesis-status-badge"
            data-thesis-status={band.thesis_status}
          >
            {band.thesis_status}
          </Badge>
          <span
            className="font-mono text-xs text-fg-muted"
            data-testid="timeframe-confidence"
          >
            conf {band.confidence}
          </span>
        </div>
      </CardHeader>
      <CardContent className="p-6 pt-0">
        <p
          className="mb-4 text-sm leading-relaxed text-fg"
          data-testid="timeframe-summary"
        >
          {band.summary}
        </p>
        {band.drivers.length > 0 && (
          <ul
            className="ml-4 list-disc space-y-1 text-sm text-fg-muted"
            data-testid="timeframe-drivers"
          >
            {band.drivers.slice(0, 5).map((d, i) => (
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
