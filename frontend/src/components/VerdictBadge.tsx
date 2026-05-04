import { Badge } from './ui/badge'
import { cn } from '@/lib/utils'
import type { Verdict } from '@/schemas'

// VerdictBadge — color-coded badge for the 5-state Verdict ladder used across
// AgentSignal records (analytical + persona). Notion-Clean palette tokens.
//
// Mapping:
//   strong_bullish / bullish     → bullish (green)
//   neutral                      → fg-muted (gray)
//   bearish / strong_bearish     → bearish (red)
// Strong variants use a slightly more saturated background; non-strong use /10.

const COLOR: Record<Verdict, string> = {
  strong_bullish: 'bg-bullish/20 text-bullish border-bullish/40',
  bullish: 'bg-bullish/10 text-bullish border-bullish/30',
  neutral: 'bg-fg-muted/10 text-fg-muted border-fg-muted/30',
  bearish: 'bg-bearish/10 text-bearish border-bearish/30',
  strong_bearish: 'bg-bearish/20 text-bearish border-bearish/40',
}

export interface VerdictBadgeProps {
  verdict: Verdict
  className?: string
}

export function VerdictBadge({ verdict, className }: VerdictBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn('font-mono', COLOR[verdict], className)}
      data-testid="verdict-badge"
      data-verdict={verdict}
    >
      {verdict}
    </Badge>
  )
}
