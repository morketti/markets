// Barrel re-export — single import surface for everything in src/schemas/.
//
// Wave 2-4 components import via:
//   import { SnapshotSchema, type Snapshot } from '@/schemas'
//
// This keeps consumers decoupled from the per-Pydantic-file split and lets
// us reorganize the schema files later without touching components.

export {
  AgentSignalSchema,
  AnalystIdSchema,
  VerdictSchema,
  type AgentSignal,
  type AnalystId,
  type Verdict,
} from './agent_signal'

export {
  ActionHintSchema,
  PositionSignalSchema,
  PositionStateSchema,
  type ActionHint,
  type PositionSignal,
  type PositionState,
} from './position_signal'

export {
  ConvictionBandSchema,
  DecisionRecommendationSchema,
  DissentSectionSchema,
  ThesisStatusSchema,
  TickerDecisionSchema,
  TimeframeBandSchema,
  TimeframeSchema,
  type ConvictionBand,
  type DecisionRecommendation,
  type DissentSection,
  type ThesisStatus,
  type TickerDecision,
  type Timeframe,
  type TimeframeBand,
} from './ticker_decision'

export {
  HeadlineSchema,
  IndicatorsSchema,
  OHLCBarSchema,
  SnapshotSchema,
  type Headline,
  type Indicators,
  type OHLCBar,
  type Snapshot,
} from './snapshot'

export { StatusSchema, type Status } from './status'

export { DatesIndexSchema, type DatesIndex } from './dates_index'
