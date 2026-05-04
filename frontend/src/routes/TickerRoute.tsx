import { useParams } from 'react-router'

// Wave 1 stub — Wave 3 populates with the deep-dive view (dual-timeframe
// cards + OHLC chart + persona signal cards + grouped news + Open Claude
// Analyst pinned at TOP per user MEMORY.md feedback_claude_knowledge).
export default function TickerRoute() {
  const { symbol, date } = useParams<{ symbol: string; date?: string }>()
  return (
    <section>
      <h1 className="font-mono text-2xl font-semibold tracking-tight">
        {symbol} — {date ?? 'today'}
      </h1>
      <p className="mt-2 text-sm text-fg-muted">
        Wave 3 will fill in the deep-dive view here.
      </p>
    </section>
  )
}
