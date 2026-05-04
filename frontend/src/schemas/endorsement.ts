// novel-to-this-project — Phase 9 endorsement record schema mirroring
// analysts/endorsement_schema.py (Pydantic v2). z.literal(1) on schema_version
// is LOAD-BEARING: v1.x ENDORSE-04..07 will introduce z.literal(2) (or a
// discriminatedUnion) so v1 readers cannot silently misinterpret future
// records as having implicit "0% performance" once perf fields land.
//
// .strict() mirrors Pydantic extra='forbid' — unknown keys fail at parse time.

import { z } from 'zod'

export const EndorsementSchema = z
  .object({
    schema_version: z.literal(1), // strict — rejects v0 and future v2+
    ticker: z.string().min(1),
    source: z.string().min(1).max(200),
    // ISO date YYYY-MM-DD — call date (drives 90-day filter, NOT captured_at).
    date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    price_at_call: z.number().positive(),
    notes: z.string().max(2000),
    // ISO 8601 datetime; permissive parse (matches refresh.ts convention).
    captured_at: z.string().min(1),
  })
  .strict()

export type Endorsement = z.infer<typeof EndorsementSchema>
