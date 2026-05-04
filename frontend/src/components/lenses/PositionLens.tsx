import type { Snapshot } from '@/schemas'
import { TickerCard } from '../TickerCard'
import { ActionHintBadge } from '../ActionHintBadge'
import { EvidenceList } from '../EvidenceList'

// PositionLens — VIEW-02 implementation.
//
// Filter: include only tickers where position_signal exists AND
// data_unavailable === false. Tickers without position data (lite_mode runs,
// failed POSE analyzer) silently drop out of this lens — they appear in the
// failedTickers banner instead.
//
// Sort: by |consensus_score| DESCENDING. Tickers with the most-extreme
// position (oversold AND overbought, both ends of the ladder) surface first
// because consensus_score is bipolar [-1, +1]. Tie-break: alphabetical by
// ticker for deterministic ordering.
//
// Render per row: state pill + score + confidence + ActionHintBadge in the
// upper line; EvidenceList (top 3) below. The TickerCard wrapper makes the
// whole row a Link to /ticker/:symbol/:date for the Wave 3 deep-dive.

export interface PositionLensProps {
  date: string
  snapshots: Record<string, Snapshot>
}

export function PositionLens({ date, snapshots }: PositionLensProps) {
  const rows = Object.values(snapshots)
    .filter(
      (s) => s.position_signal !== null && s.position_signal.data_unavailable === false,
    )
    .sort((a, b) => {
      const ascore = Math.abs(a.position_signal!.consensus_score)
      const bscore = Math.abs(b.position_signal!.consensus_score)
      if (bscore !== ascore) return bscore - ascore
      return a.ticker.localeCompare(b.ticker)
    })

  if (rows.length === 0) {
    return (
      <div
        className="p-6 text-sm text-fg-muted"
        data-testid="position-lens-empty"
      >
        No position-adjustment data for this date.
      </div>
    )
  }

  return (
    <div
      className="flex flex-col gap-4 pt-6"
      data-testid="position-lens"
    >
      {rows.map((s) => {
        const ps = s.position_signal!
        return (
          <TickerCard key={s.ticker} ticker={s.ticker} date={date}>
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <span
                  className="font-mono text-sm text-fg-muted"
                  data-testid="position-state"
                >
                  state={ps.state}
                </span>
                <span className="font-mono text-sm text-fg-muted">
                  score={ps.consensus_score.toFixed(2)}
                </span>
                <span className="font-mono text-sm text-fg-muted">
                  conf={ps.confidence}
                </span>
                <ActionHintBadge hint={ps.action_hint} />
              </div>
              <EvidenceList items={ps.evidence} max={3} />
            </div>
          </TickerCard>
        )
      })}
    </div>
  )
}
