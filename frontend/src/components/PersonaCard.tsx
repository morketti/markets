import type { AgentSignal } from '@/schemas'
import { Card, CardContent, CardHeader } from './ui/card'
import { VerdictBadge } from './VerdictBadge'
import { EvidenceList } from './EvidenceList'
import { cn } from '@/lib/utils'

// PersonaCard — renders one persona AgentSignal as a card on the deep-dive
// view. The 5 canonical investor personas (buffett, munger, wood, burry,
// lynch) render in a grid below the OpenClaudePin. The 6th persona —
// claude_analyst — is rendered SEPARATELY by OpenClaudePin and is NEVER mixed
// into this grid (per VIEW-09 + user MEMORY.md feedback: include Claude's
// inherent reasoning alongside personas, never let lenses replace it).
//
// data_unavailable=True branch: when a persona signal failed (LLM schema
// failure, persona skipped in lite mode, etc.) the card still renders but
// with a muted "data unavailable" body — consumers can rely on the card
// being present for layout purposes regardless of upstream failure.

const PERSONA_LABEL: Record<string, string> = {
  buffett: 'Warren Buffett',
  munger: 'Charlie Munger',
  wood: 'Cathie Wood',
  burry: 'Michael Burry',
  lynch: 'Peter Lynch',
  claude_analyst: 'Open Claude Analyst',
}

export interface PersonaCardProps {
  signal: AgentSignal
  className?: string
}

export function PersonaCard({ signal, className }: PersonaCardProps) {
  const muted = signal.data_unavailable
  const label = PERSONA_LABEL[signal.analyst_id] ?? signal.analyst_id
  // First evidence line doubles as the reasoning summary for v1 (the routine
  // packs the persona's free-form reasoning into evidence[0]; later evidence
  // entries are the structured drivers).
  const reasoning = signal.evidence[0] ?? ''
  const drivers = signal.evidence.slice(1)
  return (
    <Card
      className={cn(
        'border-border bg-surface text-fg shadow-none',
        className,
      )}
      data-testid="persona-card"
      data-persona={signal.analyst_id}
    >
      <CardHeader className="flex flex-row items-center justify-between gap-4 p-6 pb-3">
        <div className="font-medium" data-testid="persona-label">
          {label}
        </div>
        {!muted && (
          <div className="flex items-center gap-3">
            <VerdictBadge verdict={signal.verdict} />
            <span
              className="font-mono text-xs text-fg-muted"
              data-testid="persona-confidence"
            >
              conf {signal.confidence}
            </span>
          </div>
        )}
      </CardHeader>
      <CardContent className="p-6 pt-0">
        {muted ? (
          <div
            className="text-sm text-fg-muted"
            data-testid="persona-data-unavailable"
          >
            data unavailable
          </div>
        ) : (
          <>
            {reasoning && (
              <p
                className="mb-3 text-sm leading-relaxed text-fg"
                data-testid="persona-reasoning"
              >
                {reasoning}
              </p>
            )}
            <EvidenceList items={drivers} max={3} />
          </>
        )}
      </CardContent>
    </Card>
  )
}
