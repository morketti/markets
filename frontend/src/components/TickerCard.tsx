import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Card, CardContent } from './ui/card'
import { cn } from '@/lib/utils'

// TickerCard — shared row primitive used by all 3 lens components.
//
// Renders a clickable Link to /ticker/:symbol/:date so any row in any lens
// deep-links to the Wave 3 deep-dive page. Notion-Clean styling: 1F2024
// surface, hairline 2A2C30 border (via bg-surface + border-border tokens
// from src/index.css @theme), generous p-6 padding, gap-4 between ticker
// label and lens-specific children content.
//
// The shadcn Card primitive ships with `bg-card` token we don't have — we
// pass our explicit `bg-surface border-border` className to override.

export interface TickerCardProps {
  ticker: string
  date: string
  children: ReactNode
  className?: string
}

export function TickerCard({ ticker, date, children, className }: TickerCardProps) {
  return (
    <Link
      to={`/ticker/${ticker}/${date}`}
      className="block rounded-lg transition-colors hover:bg-surface/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      data-testid="ticker-card-link"
      data-ticker={ticker}
    >
      <Card
        className={cn(
          'border-border bg-surface text-fg shadow-none',
          className,
        )}
      >
        <CardContent className="flex items-start gap-4 p-6">
          <div
            className="w-20 shrink-0 font-mono text-lg font-semibold"
            data-testid="ticker-symbol"
          >
            {ticker}
          </div>
          <div className="min-w-0 flex-1">{children}</div>
        </CardContent>
      </Card>
    </Link>
  )
}
