import { z } from 'zod'

// Status — mirror of routine/storage.py write_daily_snapshot Phase C output
// (data/{date}/_status.json). Read by the frontend BEFORE any per-ticker
// snapshot: if absent, the routine is mid-write or crashed and the frontend
// renders "snapshot pending" instead of stale per-ticker data.
//
// Note: _status.json does NOT carry schema_version per the Wave 0 lock —
// it's the run-final sentinel and its shape evolves separately from the
// per-ticker payload.
export const StatusSchema = z.object({
  success: z.boolean(),
  partial: z.boolean(),
  completed_tickers: z.array(z.string()),
  failed_tickers: z.array(z.string()),
  skipped_tickers: z.array(z.string()),
  llm_failure_count: z.number().int().min(0),
  lite_mode: z.boolean(),
})
export type Status = z.infer<typeof StatusSchema>
