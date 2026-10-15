import { describe, it, expect } from 'vitest'
import { normaliseCoverageSort, sortCoverageRows } from './coverageSort'
import type { CoverageRow } from '../../api/coverage'

function row(over: Partial<CoverageRow>): CoverageRow {
  return {
    ticker: 'AAA',
    owned: false,
    company: null,
    price: null,
    change_pct_1d: null,
    price_as_of: null,
    session_state: null,
    market_cap: null,
    revenue_ttm: null,
    ev_ebitda: null,
    pe: null,
    currency: null,
    latest_verdict: null,
    target_price: null,
    target_low: null,
    target_high: null,
    target_date: null,
    entry_price: null,
    upside_to_target_live: null,
    signal: null,
    artifact_count: 0,
    research_count: 0,
    latest_artifact_id: null,
    latest_type: null,
    latest_at: null,
    run_status: null,
    run_error: null,
    market_implied: null,
    market_stale: false,
    needs_refresh: [],
    warnings: [],
    sources: {
      price: null,
      change_pct_1d: null,
      market_cap: null,
      revenue_ttm: null,
      ev_ebitda: null,
      pe: null,
      upside_to_target_live: null,
      market_implied: null,
    },
    ...over,
  }
}

describe('sortCoverageRows', () => {
  it('returns the original array reference-order when sort is null', () => {
    const rows = [row({ ticker: 'B' }), row({ ticker: 'A' })]
    expect(sortCoverageRows(rows, null)).toEqual(rows)
  })

  it('sorts numbers descending and ascending', () => {
    const rows = [
      row({ ticker: 'A', pe: 10 }),
      row({ ticker: 'B', pe: 30 }),
      row({ ticker: 'C', pe: 20 }),
    ]
    expect(sortCoverageRows(rows, { key: 'pe', dir: 'desc' }).map((r) => r.ticker)).toEqual([
      'B',
      'C',
      'A',
    ])
    expect(sortCoverageRows(rows, { key: 'pe', dir: 'asc' }).map((r) => r.ticker)).toEqual([
      'A',
      'C',
      'B',
    ])
  })

  it('pins null values to the bottom in BOTH directions', () => {
    const rows = [
      row({ ticker: 'A', pe: 10 }),
      row({ ticker: 'N', pe: null }),
      row({ ticker: 'B', pe: 30 }),
    ]
    // desc: real numbers first (30,10), null last
    expect(sortCoverageRows(rows, { key: 'pe', dir: 'desc' }).map((r) => r.ticker)).toEqual([
      'B',
      'A',
      'N',
    ])
    // asc: real numbers first (10,30), null STILL last (never floated to top)
    expect(sortCoverageRows(rows, { key: 'pe', dir: 'asc' }).map((r) => r.ticker)).toEqual([
      'A',
      'B',
      'N',
    ])
  })

  it('sorts tickers as locale strings', () => {
    const rows = [row({ ticker: 'NVDA' }), row({ ticker: 'AAPL' }), row({ ticker: 'MSFT' })]
    expect(sortCoverageRows(rows, { key: 'ticker', dir: 'asc' }).map((r) => r.ticker)).toEqual([
      'AAPL',
      'MSFT',
      'NVDA',
    ])
  })

  it('does not mutate the input array', () => {
    const rows = [row({ ticker: 'B', pe: 1 }), row({ ticker: 'A', pe: 2 })]
    const before = rows.map((r) => r.ticker)
    sortCoverageRows(rows, { key: 'pe', dir: 'desc' })
    expect(rows.map((r) => r.ticker)).toEqual(before)
  })
})

describe('derived sort keys', () => {
  it('needs_action orders by priority score (run_failed > never_run > clean)', () => {
    const rows = [
      row({ ticker: 'CLEAN', artifact_count: 2, research_count: 2 }),
      row({
        ticker: 'FAILED',
        run_status: 'failed',
        needs_refresh: [{ kind: 'run_failed', detail: 'boom', artifact_id: null }],
      }),
      row({
        ticker: 'NEW',
        needs_refresh: [{ kind: 'never_run', detail: 'never', artifact_id: null }],
      }),
    ]
    expect(
      sortCoverageRows(rows, { key: 'needs_action', dir: 'desc' }).map((r) => r.ticker),
    ).toEqual(['FAILED', 'NEW', 'CLEAN'])
  })

  it('latest_report orders by report date, undated rows sink', () => {
    const rows = [
      row({ ticker: 'OLD', latest_at: '2026-01-01T00:00:00Z' }),
      row({ ticker: 'NONE', latest_at: null }),
      row({ ticker: 'NEW', latest_at: '2026-06-01T00:00:00Z' }),
    ]
    expect(
      sortCoverageRows(rows, { key: 'latest_report', dir: 'desc' }).map((r) => r.ticker),
    ).toEqual(['NEW', 'OLD', 'NONE'])
  })
})

describe('rating sort key', () => {
  it('ranks BUY (0) → HOLD (1) → SELL (2) ascending; descending flips it', () => {
    const rows = [
      row({ ticker: 'S', latest_verdict: 'SELL' }),
      row({ ticker: 'B', latest_verdict: 'BUY' }),
      row({ ticker: 'H', latest_verdict: 'HOLD' }),
    ]
    expect(sortCoverageRows(rows, { key: 'rating', dir: 'asc' }).map((r) => r.ticker)).toEqual([
      'B',
      'H',
      'S',
    ])
    expect(sortCoverageRows(rows, { key: 'rating', dir: 'desc' }).map((r) => r.ticker)).toEqual([
      'S',
      'H',
      'B',
    ])
  })

  it('sinks unrated / legacy verdicts to the bottom in BOTH directions', () => {
    const rows = [
      row({ ticker: 'N', latest_verdict: null }),
      row({ ticker: 'B', latest_verdict: 'BUY' }),
      row({ ticker: 'W', latest_verdict: 'WITHHELD' }),
      row({ ticker: 'S', latest_verdict: 'SELL' }),
    ]
    // asc: BUY, SELL, then the two unranked (stable) at the bottom.
    expect(sortCoverageRows(rows, { key: 'rating', dir: 'asc' }).map((r) => r.ticker)).toEqual([
      'B',
      'S',
      'N',
      'W',
    ])
    // desc: SELL, BUY, then the unranked STILL last (never floated to the top).
    expect(sortCoverageRows(rows, { key: 'rating', dir: 'desc' }).map((r) => r.ticker)).toEqual([
      'S',
      'B',
      'N',
      'W',
    ])
  })

  it('is case-insensitive on the verdict token', () => {
    const rows = [
      row({ ticker: 'L', latest_verdict: 'buy' }),
      row({ ticker: 'U', latest_verdict: 'SELL' }),
    ]
    expect(sortCoverageRows(rows, { key: 'rating', dir: 'asc' }).map((r) => r.ticker)).toEqual([
      'L',
      'U',
    ])
  })
})

describe('normaliseCoverageSort', () => {
  it('accepts a well-formed sort and preserves the key + dir', () => {
    expect(normaliseCoverageSort({ key: 'rating', dir: 'asc' })).toEqual({
      key: 'rating',
      dir: 'asc',
    })
    expect(normaliseCoverageSort({ key: 'needs_action', dir: 'desc' })).toEqual({
      key: 'needs_action',
      dir: 'desc',
    })
  })

  it('rejects a stale/unknown key so the page can fall back to its default', () => {
    expect(normaliseCoverageSort({ key: 'pe_ratio_v2', dir: 'asc' })).toBeNull()
    expect(normaliseCoverageSort({ key: 'rating', dir: 'sideways' })).toBeNull()
  })

  it('rejects null / undefined / non-objects and missing fields', () => {
    expect(normaliseCoverageSort(null)).toBeNull()
    expect(normaliseCoverageSort(undefined)).toBeNull()
    expect(normaliseCoverageSort('rating')).toBeNull()
    expect(normaliseCoverageSort({ key: 'rating' })).toBeNull()
    expect(normaliseCoverageSort({ dir: 'asc' })).toBeNull()
  })
})

describe('ownership sort key', () => {
  // Deliberately NOT in name order, so a pass can only come from the comparator.
  const rows = [
    row({ ticker: 'ZZZ', owned: true }),
    row({ ticker: 'AAA', owned: false }),
    row({ ticker: 'MMM', owned: true }),
    row({ ticker: 'BBB', owned: false }),
  ]

  it('groups owned names first, each group in ascending name order', () => {
    // The ask behind the key: your holdings at the top, alphabetical inside.
    expect(sortCoverageRows(rows, { key: 'owned', dir: 'desc' }).map((r) => r.ticker)).toEqual([
      'MMM',
      'ZZZ',
      'AAA',
      'BBB',
    ])
  })

  it('flips the GROUPS on direction, never the name order inside them', () => {
    expect(sortCoverageRows(rows, { key: 'owned', dir: 'asc' }).map((r) => r.ticker)).toEqual([
      'AAA',
      'BBB',
      'MMM',
      'ZZZ',
    ])
  })

  it('degrades to a plain name sort when nothing is owned', () => {
    const none = [row({ ticker: 'ZZZ' }), row({ ticker: 'AAA' }), row({ ticker: 'MMM' })]
    expect(sortCoverageRows(none, { key: 'owned', dir: 'desc' }).map((r) => r.ticker)).toEqual([
      'AAA',
      'MMM',
      'ZZZ',
    ])
  })

  it('is a recognised key, so a persisted pick survives a reload', () => {
    // normaliseCoverageSort rejects unknown keys and the page falls back to its
    // default order — `owned` must not silently become one of those.
    expect(normaliseCoverageSort({ key: 'owned', dir: 'desc' })).toEqual({
      key: 'owned',
      dir: 'desc',
    })
  })
})
