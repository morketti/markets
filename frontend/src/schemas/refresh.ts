// novel-to-this-project — refresh response schema mirroring api/refresh.py
// (snake_case discipline locked in 08-CONTEXT.md). Three locked envelope
// shapes from the Wave 0 backend:
//
//   success: {ticker, current_price, price_timestamp, recent_headlines[],
//             errors:[], partial:false}
//   partial: {ticker, current_price, price_timestamp, recent_headlines:[],
//             errors:["rss-unavailable"], partial:true}
//   failure: {ticker, error:true, errors:[...], partial:true}
//             (NO current_price field — locked in api/refresh.py builder)
//
// Modeled as z.union of a Success variant (current_price required) and a
// Failure variant (error: literal(true), no current_price). Discriminated
// narrowing via isRefreshFailure helper — checks the `error` flag explicitly
// since success shape may have `error` absent rather than `error: false`.

import { z } from 'zod'

export const RefreshHeadlineSchema = z.object({
  source: z.string().min(1),
  // RSS feeds emit either ISO-8601 with offset or RFC-822; we accept any
  // non-empty string and let consumers parse defensively (mirrors
  // HeadlineSchema in snapshot.ts which is intentionally permissive).
  published_at: z.string().min(1),
  title: z.string().min(1),
  url: z.string().url(),
})
export type RefreshHeadline = z.infer<typeof RefreshHeadlineSchema>

// SUCCESS / PARTIAL — current_price required. partial: boolean (true when
// errors[] non-empty, false when fully clean).
const RefreshSuccessSchema = z.object({
  ticker: z.string().min(1),
  current_price: z.number().positive(),
  price_timestamp: z.string().datetime({ offset: true }),
  recent_headlines: z.array(RefreshHeadlineSchema),
  errors: z.array(z.string()),
  partial: z.boolean(),
})
export type RefreshSuccess = z.infer<typeof RefreshSuccessSchema>

// FULL FAILURE — error: true, no current_price field. errors[] non-empty
// per the api/refresh.py builder contract.
const RefreshFailureSchema = z.object({
  ticker: z.string().min(1),
  error: z.literal(true),
  errors: z.array(z.string()).min(1),
  partial: z.literal(true),
})
export type RefreshFailure = z.infer<typeof RefreshFailureSchema>

// Union (not discriminatedUnion — the SUCCESS shape may omit `error`
// entirely, so `error` is not a strict discriminator). z.union tries each
// variant in order; isRefreshFailure() is the user-facing narrowing helper.
export const RefreshResponseSchema = z.union([
  RefreshFailureSchema,
  RefreshSuccessSchema,
])
export type RefreshResponse = z.infer<typeof RefreshResponseSchema>

// Type guard — narrows to RefreshFailure for render-time branching.
export const isRefreshFailure = (r: RefreshResponse): r is RefreshFailure =>
  'error' in r && r.error === true
