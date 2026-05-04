import { useState } from 'react'
import { cn } from '@/lib/utils'

// EvidenceList — renders an evidence/drivers string array as a muted bullet
// list with mono font. Truncates to top N (default 3) with a "+N more"
// disclosure that expands inline. Used by all 3 lens components and by
// Wave 3's PersonaCard.
//
// Visual: hairline-restrained, no decorative icons. Each bullet is a small
// "• " prefix in fg-muted color with the evidence string in fg-muted as well.

export interface EvidenceListProps {
  items: string[]
  max?: number
  className?: string
}

export function EvidenceList({ items, max = 3, className }: EvidenceListProps) {
  const [expanded, setExpanded] = useState(false)
  if (items.length === 0) return null
  const visible = expanded ? items : items.slice(0, max)
  const hidden = Math.max(0, items.length - max)
  return (
    <ul
      className={cn('flex flex-col gap-1 text-xs text-fg-muted', className)}
      data-testid="evidence-list"
    >
      {visible.map((item, i) => (
        <li key={i} className="flex gap-2">
          <span aria-hidden className="select-none">
            ·
          </span>
          <span className="font-mono leading-snug">{item}</span>
        </li>
      ))}
      {hidden > 0 && !expanded && (
        <li>
          <button
            type="button"
            className="text-accent underline-offset-2 hover:underline"
            onClick={() => setExpanded(true)}
            data-testid="evidence-show-more"
          >
            +{hidden} more
          </button>
        </li>
      )}
    </ul>
  )
}
