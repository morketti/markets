import type { AgentSignal } from '@/schemas'
import { Card, CardContent, CardHeader } from './ui/card'
import { VerdictBadge } from './VerdictBadge'
import { EvidenceList } from './EvidenceList'
import { cn } from '@/lib/utils'

// AnalyticalSignalCard — renders one of the 4 analytical AgentSignals
// (fundamentals / technicals / news_sentiment / valuation) as a slightly
// more compact card than PersonaCard. These are deterministic Python-side
// signals (Phase 3 + 4) — no "voice" framing. The analyst_id surfaces as a
// caption rather than a persona name.

const ANALYST_LABEL: Record<string, string> = {
  fundamentals: 'Fundamentals',
  technicals: 'Technicals',
  news_sentiment: 'News & Sentiment',
  valuation: 'Valuation',
}

export interface AnalyticalSignalCardProps {
  signal: AgentSignal
  className?: string
}

export function AnalyticalSignalCard({
  signal,
  className,
}: AnalyticalSignalCardProps) {
  const muted = signal.data_unavailable
  const label = ANALYST_LABEL[signal.analyst_id] ?? signal.analyst_id
  return (
    <Card
      className={cn(
        'border-border bg-surface text-fg shadow-none',
        className,
      )}
      data-testid="analytical-signal-card"
      data-analyst={signal.analyst_id}
    >
      <CardHeader className="flex flex-row items-center justify-between gap-4 p-6 pb-3">
        <div
          className="font-mono text-xs uppercase tracking-wider text-fg-muted"
          data-testid="analytical-label"
        >
          {label}
        </div>
        {!muted && (
          <div className="flex items-center gap-3">
            <VerdictBadge verdict={signal.verdict} />
            <span className="font-mono text-xs text-fg-muted">
              conf {signal.confidence}
            </span>
          </div>
        )}
      </CardHeader>
      <CardContent className="p-6 pt-0">
        {muted ? (
          <div className="text-sm text-fg-muted">data unavailable</div>
        ) : (
          <EvidenceList items={signal.evidence} max={3} />
        )}
      </CardContent>
    </Card>
  )
}
