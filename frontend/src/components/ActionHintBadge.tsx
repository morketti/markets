import { Badge } from './ui/badge'
import { cn } from '@/lib/utils'
import type { ActionHint } from '@/schemas'

// ActionHintBadge — color-coded badge for the 4-state ActionHint surfaced
// from PositionSignal. Notion-Clean palette mapping:
//   consider_add            → bullish (green)
//   hold_position           → fg-muted (gray)
//   consider_trim           → amber
//   consider_take_profits   → bearish (red)

const COLOR: Record<ActionHint, string> = {
  consider_add: 'bg-bullish/10 text-bullish border-bullish/30',
  hold_position: 'bg-fg-muted/10 text-fg-muted border-fg-muted/30',
  consider_trim: 'bg-amber/10 text-amber border-amber/30',
  consider_take_profits: 'bg-bearish/10 text-bearish border-bearish/30',
}

export interface ActionHintBadgeProps {
  hint: ActionHint
  className?: string
}

export function ActionHintBadge({ hint, className }: ActionHintBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn('font-mono', COLOR[hint], className)}
      data-testid="action-hint-badge"
      data-hint={hint}
    >
      {hint.replace(/_/g, ' ')}
    </Badge>
  )
}
