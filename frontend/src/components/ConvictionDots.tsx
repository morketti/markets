import { cn } from '@/lib/utils'

// ConvictionDots — 3-dot indicator (1/2/3 filled for low/medium/high).
// Always renders 3 dots; never fewer. Pitfall #6 guard: Array.from({
// length: 3 }), never length: filled. Layout-shift-free secondary visual
// scan cue alongside the RecommendationBanner's font-weight signal.
//
// Visual treatment (Notion-Clean palette tokens):
//   filled dot → bg-fg solid
//   empty dot  → border border-fg-muted/50 (hairline, restrained)
// Container: flex items-center gap-1.5

export interface ConvictionDotsProps {
  /** 1, 2, or 3 — count of filled dots (low=1, medium=2, high=3). */
  filled: 1 | 2 | 3
  className?: string
}

export function ConvictionDots({ filled, className }: ConvictionDotsProps) {
  // Pitfall #6 guard — ALWAYS 3 dots; never length: filled.
  const states = Array.from({ length: 3 }, (_, i) =>
    i < filled ? 'filled' : 'empty',
  ) as ReadonlyArray<'filled' | 'empty'>

  return (
    <div
      className={cn('flex items-center gap-1.5', className)}
      data-testid="conviction-dots"
      data-filled={filled}
    >
      {states.map((state, i) => (
        <span
          key={i}
          data-testid="conviction-dot"
          data-state={state}
          className={cn(
            'h-2 w-2 rounded-full',
            state === 'filled' ? 'bg-fg' : 'border border-fg-muted/50',
          )}
          aria-hidden="true"
        />
      ))}
    </div>
  )
}
