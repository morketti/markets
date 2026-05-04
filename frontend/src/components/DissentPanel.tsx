import type { DissentSection } from '@/schemas'
import { cn } from '@/lib/utils'

// DissentPanel — ALWAYS rendered (Pitfall #12 confirmation-bias guard).
// has_dissent: false renders muted "All personas converged" panel (intentional
// silence — beats silent absence so the user reads "no one disagrees" rather
// than "panel forgot to load"). has_dissent: true renders bordered panel with
// dissenting persona + summary.
//
// Pitfall #2 LOCK (user MEMORY feedback_claude_knowledge): when
// dissenting_persona === 'claude_analyst', use accent-tinted treatment
// (border-accent/40 bg-accent/5) — same palette as OpenClaudePin. Open
// Claude is visually DISTINCT from the 5 canonical investor personas.
// Header text reads "Open Claude Dissent" (not generic "{Persona} Dissents")
// — the wording itself signals "Claude's reasoning surfaced alongside
// personas, never replaced".
//
// PERSONA_LABEL is a local const (single-use; refactor only when a future
// plan needs the lookup elsewhere — premature factor-out is anti-pattern).

const PERSONA_LABEL: Record<string, string> = {
  buffett: 'Warren Buffett',
  munger: 'Charlie Munger',
  wood: 'Cathie Wood',
  burry: 'Michael Burry',
  lynch: 'Peter Lynch',
  claude_analyst: 'Open Claude Analyst',
}

export interface DissentPanelProps {
  dissent: DissentSection
  className?: string
}

export function DissentPanel({ dissent, className }: DissentPanelProps) {
  const { has_dissent, dissenting_persona, dissent_summary } = dissent
  // Pitfall #12 — NO early-return null branch. Both branches render the
  // <div data-testid="dissent-panel"> shell.

  if (!has_dissent) {
    return (
      <div
        data-testid="dissent-panel"
        data-has-dissent="false"
        className={cn(
          'rounded-md border border-border/30 bg-surface/50 px-6 py-4 text-fg-muted',
          className,
        )}
      >
        <span className="font-mono text-xs uppercase tracking-wider">
          Dissent
        </span>
        <p className="mt-2 text-sm">
          All personas converged. No dissent surfaced.
        </p>
      </div>
    )
  }

  const isClaude = dissenting_persona === 'claude_analyst'
  const personaLabel = dissenting_persona
    ? PERSONA_LABEL[dissenting_persona] ?? dissenting_persona
    : 'Unknown persona'
  const headerText = isClaude
    ? 'Open Claude Dissent'
    : `${personaLabel} Dissents`

  return (
    <div
      data-testid="dissent-panel"
      data-has-dissent="true"
      data-dissenter={dissenting_persona ?? ''}
      className={cn(
        'rounded-md border px-6 py-4 text-fg',
        isClaude
          ? 'border-accent/40 bg-accent/5'
          : 'border-amber/30 bg-amber/10',
        className,
      )}
    >
      <div className="flex items-center justify-between gap-4">
        <span
          className={cn(
            'font-mono text-xs uppercase tracking-wider',
            isClaude && 'text-accent',
          )}
          data-testid="dissent-header"
        >
          {headerText}
        </span>
        <span
          className="font-mono text-xs text-fg-muted"
          data-testid="dissent-persona-label"
        >
          {personaLabel}
        </span>
      </div>
      {dissent_summary === '' ? (
        <p
          data-testid="dissent-summary-missing"
          className="mt-2 text-sm italic text-fg-muted"
        >
          No summary provided.
        </p>
      ) : (
        <p
          className="mt-2 text-sm leading-relaxed"
          data-testid="dissent-summary"
        >
          {dissent_summary}
        </p>
      )}
    </div>
  )
}
