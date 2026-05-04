import { z } from 'zod'

// DatesIndex — mirror of routine/storage.py:_write_dates_index output
// (data/_dates.json at the snapshots root). Wave 0 NEW file.
//
// schema_version: z.literal(1) — this index has its own contract independent
// of the per-ticker payload's v2 schema. Storage.py writes v1 today; bumps
// happen if/when this file's shape changes.
//
// dates_available is sorted ascending (storage.py guarantees) but the schema
// does NOT enforce sortedness — we accept whatever the writer emits and let
// the frontend's date-selector UI sort/format as needed.
export const DatesIndexSchema = z.object({
  schema_version: z.literal(1),
  dates_available: z.array(z.string().regex(/^\d{4}-\d{2}-\d{2}$/)),
  updated_at: z.string(),
})
export type DatesIndex = z.infer<typeof DatesIndexSchema>
