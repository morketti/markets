// One-off generator to produce per-ticker fixture JSONs that round-trip
// through SnapshotSchema. Run with `node _generate.mjs` from this dir to
// regenerate. The output JSON files are committed; the generator is checked
// in too so future schema bumps can rebuild them deterministically.

import { writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))

function ohlcBars(start = '2026-04-01', n = 30, basePrice = 100) {
  const bars = []
  const startDate = new Date(start + 'T00:00:00Z')
  for (let i = 0; i < n; i++) {
    const d = new Date(startDate.getTime() + i * 86400 * 1000)
    const dateStr = d.toISOString().slice(0, 10)
    const px = basePrice + Math.sin(i / 3) * 2 + i * 0.1
    bars.push({
      date: dateStr,
      open: Number((px - 0.5).toFixed(2)),
      high: Number((px + 1.0).toFixed(2)),
      low: Number((px - 1.0).toFixed(2)),
      close: Number(px.toFixed(2)),
      volume: 1_000_000 + i * 10_000,
    })
  }
  return bars
}

function indicatorsFor(bars) {
  const n = bars.length
  return {
    ma20: bars.map((_, i) => (i < 19 ? null : Number((bars[i].close - 0.3).toFixed(2)))),
    ma50: bars.map(() => null), // 30 bars not enough for MA50 warmup
    bb_upper: bars.map((_, i) => (i < 19 ? null : Number((bars[i].close + 2.0).toFixed(2)))),
    bb_lower: bars.map((_, i) => (i < 19 ? null : Number((bars[i].close - 2.0).toFixed(2)))),
    rsi14: bars.map((_, i) => (i < 13 ? null : 45 + (i % 30))),
  }
}

function analyticalSignal(ticker, analyst_id, verdict, confidence, evidence) {
  return {
    ticker,
    analyst_id,
    computed_at: '2026-05-04T12:15:00Z',
    verdict,
    confidence,
    evidence,
    data_unavailable: false,
  }
}

function personaSignal(ticker, analyst_id, verdict, confidence, evidence) {
  return {
    ticker,
    analyst_id,
    computed_at: '2026-05-04T12:20:00Z',
    verdict,
    confidence,
    evidence,
    data_unavailable: false,
  }
}

function makeSnapshot({
  ticker,
  positionState,
  consensusScore,
  actionHint,
  shortTermRecommendation,
  shortTermConfidence,
  longTermThesisStatus,
  longTermConfidence,
  basePrice,
}) {
  const bars = ohlcBars('2026-04-01', 30, basePrice)
  return {
    ticker,
    schema_version: 2,
    analytical_signals: [
      analyticalSignal(ticker, 'fundamentals', 'bullish', 65, [
        `${ticker}: P/E within sector range`,
        `${ticker}: ROE above peers`,
      ]),
      analyticalSignal(ticker, 'technicals', 'neutral', 50, [
        `${ticker}: MA20 flat`,
        `${ticker}: ADX 18`,
      ]),
      analyticalSignal(ticker, 'news_sentiment', 'bullish', 60, [
        `${ticker}: Positive earnings preview`,
      ]),
      analyticalSignal(ticker, 'valuation', 'neutral', 55, [
        `${ticker}: At fair value relative to thesis_price`,
      ]),
    ],
    position_signal: {
      ticker,
      computed_at: '2026-05-04T12:25:00Z',
      state: positionState,
      consensus_score: consensusScore,
      confidence: 70,
      action_hint: actionHint,
      indicators: {
        rsi14: 65,
        bb_position: 0.5,
        zscore_ma50: 1.2,
        stoch_k: 70,
        williams_r: -30,
        macd_hist_z: 0.4,
      },
      evidence: [
        `${ticker}: RSI(14)=65 elevated`,
        `${ticker}: Price above BB upper`,
        `${ticker}: z-score vs MA50 = +1.2`,
        `${ticker}: ADX(14) below 25 — mean-reversion regime`,
      ],
      data_unavailable: false,
      trend_regime: false,
    },
    persona_signals: [
      personaSignal(ticker, 'buffett', 'neutral', 55, [
        `${ticker}: Wide moat but valuation rich`,
      ]),
      personaSignal(ticker, 'munger', 'bullish', 65, [
        `${ticker}: Quality compounder, hold`,
      ]),
      personaSignal(ticker, 'wood', 'strong_bullish', 80, [
        `${ticker}: Disruptive thesis intact`,
      ]),
      personaSignal(ticker, 'burry', 'bearish', 60, [
        `${ticker}: Frothy market, risk-off`,
      ]),
      personaSignal(ticker, 'lynch', 'bullish', 62, [
        `${ticker}: Story still compounding`,
      ]),
      personaSignal(ticker, 'claude_analyst', 'neutral', 55, [
        `${ticker}: Mixed signals — directional view low conviction`,
      ]),
    ],
    ticker_decision: {
      ticker,
      computed_at: '2026-05-04T12:28:00Z',
      schema_version: 2,
      recommendation: shortTermRecommendation,
      conviction: 'medium',
      short_term: {
        summary: `${ticker} short-term: ${shortTermRecommendation}`,
        drivers: [
          `${ticker}: technicals neutral, news_sentiment bullish`,
          `${ticker}: position_signal state=${positionState}`,
          `${ticker}: 4 of 6 personas constructive`,
        ],
        confidence: shortTermConfidence,
        thesis_status: 'n/a',
      },
      long_term: {
        summary: `${ticker} long-term thesis: ${longTermThesisStatus}`,
        drivers: [
          `${ticker}: fundamentals bullish on ROE`,
          `${ticker}: valuation neutral at thesis_price`,
          `${ticker}: structural moat tested by sector rotation`,
        ],
        confidence: longTermConfidence,
        thesis_status: longTermThesisStatus,
      },
      open_observation: `${ticker}: Open Claude analyst flags mixed signal — short-term tactical bias diverges from long-term thesis posture.`,
      dissent: {
        has_dissent: true,
        dissenting_persona: 'burry',
        dissent_summary: `${ticker}: Burry persona flags ≥30-pt confidence gap vs consensus`,
      },
      data_unavailable: false,
    },
    ohlc_history: bars,
    indicators: indicatorsFor(bars),
    headlines: [
      {
        source: 'Yahoo Finance',
        published_at: '2026-05-03T18:00:00Z',
        title: `${ticker}: Earnings preview — analysts expect beat`,
        url: `https://finance.yahoo.com/news/${ticker}-earnings-preview`,
      },
      {
        source: 'Reuters',
        published_at: '2026-05-03T15:30:00Z',
        title: `${ticker}: Sector rotation continues`,
        url: `https://reuters.com/markets/${ticker}`,
      },
      {
        source: 'Bloomberg RSS',
        published_at: '2026-05-02T10:00:00Z',
        title: `${ticker}: Insider buying notice filed`,
        url: `https://bloomberg.com/news/${ticker}-insider`,
      },
    ],
    errors: [],
  }
}

const tickers = [
  // AAPL: position_signal.state='oversold', consensus_score=-0.65 (high |score|),
  //       action_hint='consider_add'; bullish short-term ('add', conf=70);
  //       long-term thesis='intact'.
  {
    ticker: 'AAPL',
    positionState: 'oversold',
    consensusScore: -0.65,
    actionHint: 'consider_add',
    shortTermRecommendation: 'add',
    shortTermConfidence: 70,
    longTermThesisStatus: 'intact',
    longTermConfidence: 75,
    basePrice: 195,
  },
  // NVDA: position_signal.state='overbought', consensus_score=+0.78 (highest |score|,
  //       sorts first in PositionLens); action_hint='consider_take_profits';
  //       short-term recommendation='take_profits' (bearish — ShortTermLens excludes);
  //       long-term thesis='broken' (LongTermLens picks up).
  {
    ticker: 'NVDA',
    positionState: 'overbought',
    consensusScore: 0.78,
    actionHint: 'consider_take_profits',
    shortTermRecommendation: 'take_profits',
    shortTermConfidence: 65,
    longTermThesisStatus: 'broken',
    longTermConfidence: 50,
    basePrice: 850,
  },
  // MSFT: position_signal.state='fair', consensus_score=+0.05 (low |score|, sorts last);
  //       short-term recommendation='buy', conf=85 (highest in ShortTermLens);
  //       long-term thesis='weakening' (LongTermLens picks up after NVDA-broken).
  {
    ticker: 'MSFT',
    positionState: 'fair',
    consensusScore: 0.05,
    actionHint: 'hold_position',
    shortTermRecommendation: 'buy',
    shortTermConfidence: 85,
    longTermThesisStatus: 'weakening',
    longTermConfidence: 60,
    basePrice: 410,
  },
]

for (const cfg of tickers) {
  const snap = makeSnapshot(cfg)
  const out = resolve(__dirname, `${cfg.ticker}.json`)
  writeFileSync(out, JSON.stringify(snap, null, 2) + '\n', 'utf-8')
  console.log(`wrote ${out}`)
}
