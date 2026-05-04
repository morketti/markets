import type { Snapshot, ThesisStatus } from '@/schemas'
import { TickerCard } from '../TickerCard'
import { EvidenceList } from '../EvidenceList'
import { Badge } from '../ui/badge'
import { cn } from '@/lib/utils'

// LongTermLens — implementation of VIEW-04 (filter) for the Wave 2 scan-list
// surface. The deep-dive content for VIEW-04 lands in Wave 3; this lens shows
// the SUMMARY rows that link to /ticker/:symbol/:date.
//
// Filter: thesis_status ∈ {weakening, broken}. Tickers with intact / improving /
// n/a thesis drop out (they aren't actionable from a "needs-attention" lens).
//
// Sort: severity first (broken before weakening), then long_term.confidence
// ASCENDING — less-confident bear theses on a broken thesis are MORE concerning
// (the synthesizer is uncertain even though the thesis is breaking). Tie-break:
// alphabetical by ticker.
//
// Render per row: ticker + thesis_status pill + summary + drivers (top 3).

const THESIS_RANK: Record<ThesisStatus, number> = {
  broken: 0,
  weakening: 1,
  improving: 2,
  intact: 3,
  'n/a': 4,
}

const THESIS_COLOR: Record<ThesisStatus, string> = {
  broken: 'bg-bearish/20 text-bearish border-bearish/40',
  weakening: 'bg-amber/10 text-amber border-amber/30',
  improving: 'bg-bullish/10 text-bullish border-bullish/30',
  intact: 'bg-fg-muted/10 text-fg-muted border-fg-muted/30',
  'n/a': 'bg-fg-muted/10 text-fg-muted border-fg-muted/30',
}

const ALERT_THESIS: ReadonlySet<ThesisStatus> = new Set(['weakening', 'broken'])

export interface LongTermLensProps {
  date: string
  snapshots: Record<string, Snapshot>
}

export function LongTermLens({ date, snapshots }: LongTermLensProps) {
  const rows = Object.values(snapshots)
    .filter(
      (s) =>
        s.ticker_decision !== null &&
        ALERT_THESIS.has(s.ticker_decision.long_term.thesis_status),
    )
    .sort((a, b) => {
      const ad = a.ticker_decision!
      const bd = b.ticker_decision!
      const arank = THESIS_RANK[ad.long_term.thesis_status]
      const brank = THESIS_RANK[bd.long_term.thesis_status]
      if (arank !== brank) return arank - brank
      if (ad.long_term.confidence !== bd.long_term.confidence) {
        return ad.long_term.confidence - bd.long_term.confidence
      }
      return a.ticker.localeCompare(b.ticker)
    })

  if (rows.length === 0) {
    return (
      <div className="p-6 text-sm text-fg-muted" data-testid="long-term-lens-empty">
        No weakening or broken theses for this date.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 pt-6" data-testid="long-term-lens">
      {rows.map((s) => {
        const td = s.ticker_decision!
        const thesis = td.long_term.thesis_status
        return (
          <TickerCard key={s.ticker} ticker={s.ticker} date={date}>
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <Badge
                  variant="outline"
                  className={cn('font-mono', THESIS_COLOR[thesis])}
                  data-testid="thesis-status"
                  data-thesis={thesis}
                >
                  thesis: {thesis}
                </Badge>
                <span className="font-mono text-xs text-fg-muted">
                  conf={td.long_term.confidence}
                </span>
              </div>
              <p className="text-sm text-fg" data-testid="long-term-summary">
                {td.long_term.summary}
              </p>
              <EvidenceList items={td.long_term.drivers} max={3} />
            </div>
          </TickerCard>
        )
      })}
    </div>
  )
}
