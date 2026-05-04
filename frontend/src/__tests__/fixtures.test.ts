import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { SnapshotSchema, StatusSchema } from '../schemas'
import { z } from 'zod'

// Round-trip test: every fixture JSON must parse cleanly through the
// production zod schemas. This is the gate that prevents fixture drift —
// if SnapshotSchema changes shape, this test breaks immediately rather than
// the Playwright E2E flaking later.

const FIX_DIR = resolve(__dirname, '../../tests/fixtures/scan')

const IndexSchema = z.object({
  date: z.string(),
  schema_version: z.literal(2),
  run_started_at: z.string(),
  run_completed_at: z.string(),
  tickers: z.array(z.string()),
  lite_mode: z.boolean(),
  total_token_count_estimate: z.number().nonnegative(),
})

function loadJSON(name: string): unknown {
  const raw = readFileSync(resolve(FIX_DIR, name), 'utf-8')
  return JSON.parse(raw)
}

describe('scan fixtures round-trip', () => {
  it('_status.json parses through StatusSchema', () => {
    const r = StatusSchema.safeParse(loadJSON('_status.json'))
    expect(r.success).toBe(true)
  })

  it('_index.json parses through IndexSchema', () => {
    const r = IndexSchema.safeParse(loadJSON('_index.json'))
    expect(r.success).toBe(true)
  })

  for (const ticker of ['AAPL', 'NVDA', 'MSFT']) {
    it(`${ticker}.json parses through SnapshotSchema`, () => {
      const r = SnapshotSchema.safeParse(loadJSON(`${ticker}.json`))
      if (!r.success) {
        // surface the zod error for fast diagnosis
        console.error(`${ticker} validation issues:`, r.error.issues.slice(0, 3))
      }
      expect(r.success).toBe(true)
    })
  }
})
