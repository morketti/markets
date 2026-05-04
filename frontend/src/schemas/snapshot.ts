import { z } from 'zod'

import { AgentSignalSchema } from './agent_signal'
import { PositionSignalSchema } from './position_signal'
import { TickerDecisionSchema } from './ticker_decision'

// Snapshot — the per-ticker JSON shape at data/{date}/{TICKER}.json POST
// Wave 0 (routine/storage.py:_build_ticker_payload).
//
// schema_version: z.literal(2) — strict, NOT z.number(). v1 snapshots from
// pre-Wave-0 dev runs MUST surface as schema-mismatch errors (CONTEXT.md
// UNIFORM RULE), not silently coerce.
//
// indicators: 5 series (ma20, ma50, bb_upper, bb_lower, rsi14), each aligned
// 1:1 to ohlc_history dates. Each entry can be null (warmup window or
// inf-coerced edge case — routine/storage.py:_series_to_jsonable).
//
// headlines: raw {source, published_at, title, url} dicts as ingested by
// ingestion/news.fetch_news(return_raw=True). published_at is whatever the
// RSS feed provided — we don't strictly enforce ISO-8601 (some feeds emit
// RFC-822); store as string and let consumers parse defensively.

export const OHLCBarSchema = z.object({
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  volume: z.number().int().nonnegative(),
})
export type OHLCBar = z.infer<typeof OHLCBarSchema>

export const IndicatorsSchema = z.object({
  ma20: z.array(z.number().nullable()),
  ma50: z.array(z.number().nullable()),
  bb_upper: z.array(z.number().nullable()),
  bb_lower: z.array(z.number().nullable()),
  rsi14: z.array(z.number().nullable()),
})
export type Indicators = z.infer<typeof IndicatorsSchema>

export const HeadlineSchema = z.object({
  source: z.string().min(1),
  published_at: z.string(),
  title: z.string().min(1),
  url: z.string().url(),
})
export type Headline = z.infer<typeof HeadlineSchema>

export const SnapshotSchema = z.object({
  ticker: z.string().min(1),
  schema_version: z.literal(2),
  analytical_signals: z.array(AgentSignalSchema),
  position_signal: PositionSignalSchema.nullable(),
  persona_signals: z.array(AgentSignalSchema),
  ticker_decision: TickerDecisionSchema.nullable(),
  ohlc_history: z.array(OHLCBarSchema),
  indicators: IndicatorsSchema,
  headlines: z.array(HeadlineSchema),
  errors: z.array(z.string()),
})
export type Snapshot = z.infer<typeof SnapshotSchema>
