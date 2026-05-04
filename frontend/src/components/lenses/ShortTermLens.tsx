import type {
  DecisionRecommendation,
  Snapshot,
} from '@/schemas'
import { TickerCard } from '../TickerCard'
import { EvidenceList } from '../EvidenceList'
import { Badge } from '../ui/badge'
import { cn } from '@/lib/utils'

// ShortTermLens — VIEW-03 implementation.
//
// Filter: tickers with bullish-direction recommendation only (per VIEW-03
// "tickers with BULLISH short_term signal"). Tickers with hold/trim/take_profits/
// avoid drop out.
//
// Sort: by short_term.confidence × directionSign(recommendation) DESCENDING.
// Since we filter to bullish only, directionSign is always +1, which is
// equivalent to sort by confidence DESC. Tie-break: alphabetical by ticker.
//
// Render per row: ticker (via TickerCard) + summary + drivers (top 5) +
// recommendation badge (small, mono, accent-colored) + conviction band.

const BULLISH: ReadonlySet<DecisionRecommendation> = new Set(['add', 'buy'])

function directionSign(rec: DecisionRecommendation): number {
  if (BULLISH.has(rec)) return 1
  if (rec === 'hold') return 0
  return -1
}

const RECOMMENDATION_COLOR: Record<DecisionRecommendation, string> = {
  add: 'bg-bullish/10 text-bullish border-bullish/30',
  buy: 'bg-bullish/20 text-bullish border-bullish/40',
  hold: 'bg-fg-muted/10 text-fg-muted border-fg-muted/30',
  trim: 'bg-amber/10 text-amber border-amber/30',
  take_profits: 'bg-bearish/10 text-bearish border-bearish/30',
  avoid: 'bg-bearish/20 text-bearish border-bearish/40',
}

export interface ShortTermLensProps {
  date: string
  snapshots: Record<string, Snapshot>
}

export function ShortTermLens({ date, snapshots }: ShortTermLensProps) {
  const rows = Object.values(snapshots)
    .filter((s) => {
      if (s.ticker_decision === null) return false
      return directionSign(s.ticker_decision.recommendation) > 0
    })
    .sort((a, b) => {
      const ad = a.ticker_decision!
      const bd = b.ticker_decision!
      const ascore = ad.short_term.confidence * directionSign(ad.recommendation)
      const bscore = bd.short_term.confidence * directionSign(bd.recommendation)
      if (bscore !== ascore) return bscore - ascore
      return a.ticker.localeCompare(b.ticker)
    })

  if (rows.length === 0) {
    return (
      <div className="p-6 text-sm text-fg-muted" data-testid="short-term-lens-empty">
        No bullish short-term opportunities for this date.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 pt-6" data-testid="short-term-lens">
      {rows.map((s) => {
        const td = s.ticker_decision!
        return (
          <TickerCard key={s.ticker} ticker={s.ticker} date={date}>
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <Badge
                  variant="outline"
                  className={cn(
                    'font-mono',
                    RECOMMENDATION_COLOR[td.recommendation],
                  )}
                  data-testid="short-term-recommendation"
                  data-recommendation={td.recommendation}
                >
                  {td.recommendation}
                </Badge>
                <span className="font-mono text-xs text-fg-muted">
                  conviction={td.conviction}
                </span>
                <span className="font-mono text-xs text-fg-muted">
                  conf={td.short_term.confidence}
                </span>
              </div>
              <p className="text-sm text-fg" data-testid="short-term-summary">
                {td.short_term.summary}
              </p>
              <EvidenceList items={td.short_term.drivers} max={5} />
            </div>
          </TickerCard>
        )
      })}
    </div>
  )
}
