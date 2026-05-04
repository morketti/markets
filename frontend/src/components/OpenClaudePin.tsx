import type { AgentSignal } from '@/schemas'
import { Card, CardContent } from './ui/card'
import { VerdictBadge } from './VerdictBadge'
import { cn } from '@/lib/utils'

// OpenClaudePin — Claude's inherent reasoning surfaced at the TOP of the
// deep-dive view, visually distinct from the 5 canonical-investor PersonaCards
// in the grid below.
//
// USER MEMORY LOCK (load-bearing per .claude memory feedback_claude_knowledge):
//   "include an Open Claude Analyst alongside canonical personas — never let
//    lenses replace inherent reasoning"
//
// VIEW-09 LOCK: Open Claude Analyst pinned at TOP — distinct from the 5
// PersonaCards. NEVER mixed into the grid. NEVER silently absent: when the
// claude_analyst signal is missing or data_unavailable=True the pin still
// renders with a muted "data unavailable" state so the slot is always
// architecturally present.
//
// Visual treatment: accent-tinted border + accent-tinted background fill
// (border-accent/40 bg-accent/5 per CONTEXT.md). "OPEN CLAUDE ANALYST" caption
// in accent color uppercase tracking-wider. Reasoning paragraph at text-base
// (slightly larger than PersonaCard's text-sm) to emphasize this is the
// pinned-at-top centerpiece. Up to 4 evidence bullets shown.

export interface OpenClaudePinProps {
  /**
   * The claude_analyst AgentSignal from snapshot.persona_signals. May be
   * undefined when the signal is absent from the snapshot — the component
   * still renders with a muted "data unavailable for this snapshot" state.
   */
  signal: AgentSignal | undefined
  className?: string
}

export function OpenClaudePin({ signal, className }: OpenClaudePinProps) {
  const muted = !signal || signal.data_unavailable
  const reasoning = signal?.evidence[0] ?? ''
  const drivers = signal?.evidence.slice(1) ?? []
  return (
    <Card
      className={cn(
        'border-accent/40 bg-accent/5 text-fg shadow-none',
        className,
      )}
      data-testid="open-claude-pin"
      data-muted={muted ? 'true' : 'false'}
    >
      <CardContent className="p-6">
        <div className="mb-3 flex items-center justify-between gap-4">
          <div
            className="font-mono text-xs font-medium uppercase tracking-wider text-accent"
            data-testid="open-claude-label"
          >
            Open Claude Analyst
          </div>
          {!muted && signal && (
            <div className="flex items-center gap-3">
              <VerdictBadge verdict={signal.verdict} />
              <span className="font-mono text-xs text-fg-muted">
                conf {signal.confidence}
              </span>
            </div>
          )}
        </div>
        {muted ? (
          <div
            className="text-sm text-fg-muted"
            data-testid="open-claude-data-unavailable"
          >
            Open Claude Analyst: data unavailable for this snapshot.
          </div>
        ) : (
          <>
            {reasoning && (
              <p
                className="mb-4 text-base leading-relaxed text-fg"
                data-testid="open-claude-reasoning"
              >
                {reasoning}
              </p>
            )}
            {drivers.length > 0 && (
              <ul
                className="ml-4 list-disc space-y-1 text-sm text-fg-muted"
                data-testid="open-claude-evidence"
              >
                {drivers.slice(0, 4).map((e, i) => (
                  <li key={i} className="font-mono">
                    {e}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
