import type { ConvictionBand, DecisionRecommendation } from '@/schemas'
import { cn } from '@/lib/utils'
import { ConvictionDots } from './ConvictionDots'

// RecommendationBanner — hero element of /decision/:symbol/:date?. Action
// drives color (Notion-Clean palette tokens); conviction drives visual
// weight (font + ConvictionDots count). 6 actions × 3 convictions = 18
// visual states. Independent from ActionHintBadge (Pitfall #4 — different
// schema field, different enum: ActionHintBadge is a 4-state badge for
// position_signal.action_hint; this is a 6-state hero banner for
// ticker_decision.recommendation).
//
// Locked color × weight matrix (CONTEXT.md + PLAN frontmatter):
//   add → bg-bullish/10 text-bullish border-bullish/30
//   buy → bg-bullish/15 text-bullish border-bullish/40
//   hold → bg-fg-muted/10 text-fg-muted border-fg-muted/30
//   trim → bg-amber/10 text-amber border-amber/30
//   take_profits → bg-amber/15 text-amber border-amber/40
//   avoid → bg-bearish/10 text-bearish border-bearish/30
//
//   low → text-2xl font-medium  (1 filled dot)
//   medium → text-3xl font-semibold  (2 filled dots)
//   high → text-4xl font-bold  (3 filled dots)
//
// Compile-time exhaustiveness via Record<DecisionRecommendation, ...> +
// Record<ConvictionBand, ...> — adding a new enum value at the schema layer
// flags both maps as missing keys, preventing silent visual regression.

const ACTION_COLOR: Record<DecisionRecommendation, string> = {
  add: 'bg-bullish/10 text-bullish border-bullish/30',
  buy: 'bg-bullish/15 text-bullish border-bullish/40',
  hold: 'bg-fg-muted/10 text-fg-muted border-fg-muted/30',
  trim: 'bg-amber/10 text-amber border-amber/30',
  take_profits: 'bg-amber/15 text-amber border-amber/40',
  avoid: 'bg-bearish/10 text-bearish border-bearish/30',
}

const ACTION_LABEL: Record<DecisionRecommendation, string> = {
  add: 'Add',
  buy: 'Buy',
  hold: 'Hold',
  trim: 'Trim',
  take_profits: 'Take Profits',
  avoid: 'Avoid',
}

const CONVICTION_FONT: Record<ConvictionBand, string> = {
  low: 'text-2xl font-medium',
  medium: 'text-3xl font-semibold',
  high: 'text-4xl font-bold',
}

const CONVICTION_DOTS: Record<ConvictionBand, 1 | 2 | 3> = {
  low: 1,
  medium: 2,
  high: 3,
}

export interface RecommendationBannerProps {
  recommendation: DecisionRecommendation
  conviction: ConvictionBand
  className?: string
}

export function RecommendationBanner({
  recommendation,
  conviction,
  className,
}: RecommendationBannerProps) {
  const ariaLabel = `Recommendation: ${ACTION_LABEL[recommendation]}, conviction ${conviction}`
  return (
    <div
      role="status"
      aria-label={ariaLabel}
      data-testid="recommendation-banner"
      data-recommendation={recommendation}
      data-conviction={conviction}
      className={cn(
        'flex items-center justify-between gap-6 rounded-md border px-6 py-5',
        ACTION_COLOR[recommendation],
        className,
      )}
    >
      <div
        className={cn(
          'font-mono leading-none tracking-tight',
          CONVICTION_FONT[conviction],
        )}
        data-testid="recommendation-action-label"
      >
        {ACTION_LABEL[recommendation]}
      </div>
      <div className="flex items-center gap-3">
        <ConvictionDots filled={CONVICTION_DOTS[conviction]} />
        <span
          className="font-mono text-xs uppercase tracking-wider opacity-70"
          data-testid="recommendation-conviction-caption"
        >
          {conviction} conviction
        </span>
      </div>
    </div>
  )
}
