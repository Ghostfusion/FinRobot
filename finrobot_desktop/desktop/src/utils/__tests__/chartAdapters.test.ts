import { describe, it, expect, vi } from 'vitest'
import {
  compsResultToRadarData,
  dcfResultToMarginData,
  dcfResultToRevenueEbitdaData,
  historicalToRevenueEbitdaData,
  mergeDcfBaseRow,
} from '../chartAdapters'
import type { CompsResult, DCFResult, HistoricalMetrics } from '../../types/finance'

// Only the fields the radar reads; the cast mirrors ChapterCompetitive's own
// `as unknown as CompsResult` (the full shape is large and irrelevant here).
function makeCompsResult(): CompsResult {
  return {
    target: {
      ticker: 'TGT',
      pe_ratio: 20, // vs median 40 → 2x cheaper → outward (capped 200)
      ev_ebitda: 20, // vs median 10 → expensive → inside (50)
      ev_revenue: 5, // vs median 5 → at median (100)
      gross_margin: 0.6, // vs peer median 0.4 → outward (150)
      operating_margin: 0.3, // vs peer median 0.2 → outward (150)
    },
    peers: [
      { gross_margin: 0.3, operating_margin: 0.1 },
      { gross_margin: 0.4, operating_margin: 0.2 },
      { gross_margin: 0.5, operating_margin: 0.3 },
    ],
    median_pe: 40,
    median_ev_ebitda: 10,
    median_ev_revenue: 5,
  } as unknown as CompsResult
}

function makeDcfResult(daPct: number | undefined): DCFResult {
  return {
    cost_of_equity: 0.1,
    wacc: 0.1,
    projection_years: 2,
    projected_revenue: [110, 120],
    projected_ebitda: [33, 36],
    projected_fcf: [20, 22],
    terminal_value: 500,
    pv_terminal: 300,
    pv_fcf_total: 40,
    enterprise_value: 340,
    equity_value: 320,
    implied_price: 32,
    sensitivity_table: null,
    inputs: {
      revenue_base: 100,
      revenue_growth_rates: [0.1, 0.09],
      ebitda_margin: 0.3,
      capex_pct_revenue: 0.03,
      nwc_pct_revenue: 0.01,
      da_pct_revenue: daPct,
      tax_rate: 0.21,
      risk_free_rate: 0.04,
      beta: 1.1,
      equity_risk_premium: 0.05,
      cost_of_debt: 0.04,
      debt_ratio: 0.2,
      terminal_growth_rate: 0.025,
      shares_outstanding: 10,
      net_debt: 20,
    },
  }
}

describe('dcfResultToMarginData operating margin (D5)', () => {
  it('derives EBIT margin = EBITDA margin - D&A% when D&A is known', () => {
    const rows = dcfResultToMarginData(makeDcfResult(0.05), 2025)
    // base year: ebitda_margin 0.30, operating 0.30 - 0.05 = 0.25
    expect(rows[0].ebitda_margin).toBeCloseTo(0.3)
    expect(rows[0].operating_margin).toBeCloseTo(0.25)
  })

  it('emits null operating_margin when D&A% is unknown — never equals EBITDA margin', () => {
    const rows = dcfResultToMarginData(makeDcfResult(undefined), 2025)
    for (const row of rows) {
      expect(row.operating_margin).toBeNull()
      // EBITDA margin still rendered; the two must not silently coincide.
      expect(row.ebitda_margin).not.toBeNull()
    }
  })

  it('treats da_pct_revenue=0 as unknown rather than zero-D&A', () => {
    const rows = dcfResultToMarginData(makeDcfResult(0), 2025)
    expect(rows[0].operating_margin).toBeNull()
  })
})

describe('compsResultToRadarData — outward = favorable vs peer median', () => {
  it('pins the benchmark ring to 100 and pushes cheaper multiples / higher margins outward', () => {
    const rows = compsResultToRadarData(makeCompsResult())
    // Fixed-order axes (pe, evEbitda, evRevenue, grossMargin, operatingMargin).
    expect(rows).toHaveLength(5)
    rows.forEach((r) => expect(r.benchmark).toBe(100)) // peer median = the ring
    expect(rows[0].value).toBe(200) // P/E 20 vs 40 → 2x cheaper, capped outward
    expect(rows[1].value).toBe(50) // EV/EBITDA 20 vs 10 → expensive, inside
    expect(rows[2].value).toBe(100) // EV/Rev at median
    expect(rows[3].value).toBe(150) // gross margin above peer median → outward
    expect(rows[4].value).toBe(150) // operating margin above peer median → outward
  })

  it('drops an ill-defined valuation axis (negative P/E) instead of plotting it', () => {
    const r = makeCompsResult()
    ;(r.target as { pe_ratio: number }).pe_ratio = -15 // a loss → P/E is N/A, not "cheap"
    const rows = compsResultToRadarData(r)
    expect(rows).toHaveLength(4) // the P/E axis is excluded, not mapped to a bogus value
  })
})

// ---------------------------------------------------------------------------
// DCF year axis. The adapters used to label the base year with the BROWSER clock
// (`new Date().getFullYear()`) and the projections `currentYear + 1 + i`, so the
// base row claimed a calendar year the report held no actuals for, the whole
// projection sat a year ahead of the DCF's own schedule, and — the chapter
// dropping the base row as a duplicate of the last historical bar — 2026
// disappeared from every trajectory chart (2025 actual → 2027E forecast).
// ---------------------------------------------------------------------------

/** Historical series ending at the last REPORTED fiscal year — the shape every
 *  artifact in the store carries while the wall clock is on the next year. */
function makeHistory(years: number[]): HistoricalMetrics {
  return {
    years,
    revenue: years.map((_, i) => 100 + i),
    ebitda: years.map((_, i) => 30 + i),
    gross_margin: years.map(() => 0.5),
    ebitda_margin: years.map(() => 0.3),
    operating_margin: years.map(() => 0.25),
  } as unknown as HistoricalMetrics
}

describe('DCF year axis — anchored on the DCF fiscal year, never the browser clock', () => {
  it('labels the base row with the anchor and the projection from anchor + 1', () => {
    const rows = dcfResultToRevenueEbitdaData(makeDcfResult(0.05), 2025)
    expect(rows.map((r) => r.year)).toEqual(['2025', '2026E', '2027E'])
    expect(rows[0].is_forecast).toBe(false)
    expect(rows.slice(1).every((r) => r.is_forecast === true)).toBe(true)
  })

  it('ignores the wall clock entirely', () => {
    vi.useFakeTimers()
    try {
      // Six years past the anchor: a clock-derived axis would relabel every
      // year, so the anchor has to win.
      vi.setSystemTime(new Date('2031-06-15T00:00:00Z'))
      const bars = dcfResultToRevenueEbitdaData(makeDcfResult(0.05), 2025)
      const margins = dcfResultToMarginData(makeDcfResult(0.05), 2025)
      expect(bars.map((r) => r.year)).toEqual(['2025', '2026E', '2027E'])
      expect(margins.map((r) => r.year)).toEqual(['2025', '2026E', '2027E'])
    } finally {
      vi.useRealTimers()
    }
  })

  it('drops the base row when the historical series already carries that year', () => {
    const merged = mergeDcfBaseRow(
      historicalToRevenueEbitdaData(makeHistory([2024, 2025])),
      dcfResultToRevenueEbitdaData(makeDcfResult(0.05), 2025),
    )
    // One bar per fiscal year, with the reported actual standing in for the
    // anchor (the base row rests on a TTM run-rate, not that year's filing).
    expect(merged.map((r) => r.year)).toEqual(['2024', '2025', '2026E', '2027E'])
  })

  it('keeps the base row when the series lags the anchor — no hole in the axis', () => {
    const merged = mergeDcfBaseRow(
      historicalToRevenueEbitdaData(makeHistory([2022, 2023])),
      dcfResultToRevenueEbitdaData(makeDcfResult(0.05), 2025),
    )
    // Jumping 2023 → 2026E would hide the gap the base row exists to close.
    expect(merged.map((r) => r.year)).toEqual(['2022', '2023', '2025', '2026E', '2027E'])
  })

  it('leaves the historical series untouched when there is no projection', () => {
    const hist = historicalToRevenueEbitdaData(makeHistory([2024, 2025]))
    expect(mergeDcfBaseRow(hist, [])).toBe(hist)
  })
})

// The DCF base is a TTM figure, so the first forecast year is not necessarily
// baseFY + 1 (a twelve-month window ending mid-2027 was labelled "2026E"). The
// backend's forecast_basis.first_forecast_year wins when present; the baseFY + 1
// rule survives as the fallback for legacy artifacts.
describe('DCF first forecast year — forecast_basis provenance', () => {
  it('prefers firstForecastYear when supplied', () => {
    const bars = dcfResultToRevenueEbitdaData(makeDcfResult(0.05), 2025, 2027)
    expect(bars.map((r) => r.year)).toEqual(['2025', '2027E', '2028E'])
    const margins = dcfResultToMarginData(makeDcfResult(0.05), 2025, 2027)
    expect(margins.map((r) => r.year)).toEqual(['2025', '2027E', '2028E'])
  })

  it('falls back to baseFY + 1 when firstForecastYear is absent or null', () => {
    const omitted = dcfResultToRevenueEbitdaData(makeDcfResult(0.05), 2025)
    expect(omitted.map((r) => r.year)).toEqual(['2025', '2026E', '2027E'])
    const explicitNull = dcfResultToMarginData(makeDcfResult(0.05), 2025, null)
    expect(explicitNull.map((r) => r.year)).toEqual(['2025', '2026E', '2027E'])
  })
})
