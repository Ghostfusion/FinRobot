import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ChapterFinancialAnalysis } from './ChapterFinancialAnalysis'
import type { DcfShape } from './types'
import type { HistoricalMetrics } from '../../../types/finance'

// Captures the props the revenue chart receives, so the year axis this chapter
// ASSEMBLES (fiscal anchor + base-row merge) is asserted end to end and not only
// through the adapter's own unit tests. `vi.hoisted` because the vi.mock factory
// below is lifted above these imports.
const { revenueChartProps } = vi.hoisted(() => ({ revenueChartProps: vi.fn() }))

// raw_data is FinancialData.model_dump() — money line items nest under income.*.
// This guards the 2026-05-29 fix: the chapter used to read rawData.ebitda etc.
// from the TOP level, so the EBITDA / net-income cards silently never rendered.

vi.mock('../../../i18n', () => ({
  useI18n: () => ({
    locale: 'zh',
    t: (key: string) => {
      const map: Record<string, string> = {
        'chapter.financial.kv.revenueBase': '营收',
        'chapter.financial.kv.netIncome': '净利润',
      }
      return map[key] ?? key
    },
  }),
}))

// historical trend is now passed as a FROZEN prop (historicalMetrics), not a
// live hook — the KV cards don't depend on it, so pass null here.

// Charts are irrelevant to the KV-card regression; render them as no-ops — but
// the revenue chart records its props, since the DCF year axis is built here.
vi.mock('../../../components/charts/RevenueEbitdaChart', () => ({
  default: (props: unknown) => {
    revenueChartProps(props)
    return null
  },
}))
vi.mock('../../../components/charts/MarginTrendChart', () => ({ default: () => null }))
vi.mock('../../../components/charts/BankTrajectoryChart', () => ({ default: () => null }))
vi.mock('../../../components/charts/EpsTrendChart', () => ({ default: () => null }))
vi.mock('../../../components/charts/CashFlowChart', () => ({ default: () => null }))

const RAW_DATA = {
  fiscal_period_end: '2024-09-30',
  income: {
    revenue: 391_035_000_000,
    ebitda: 131_900_000_000,
    net_income: 93_736_000_000,
  },
}

describe('ChapterFinancialAnalysis KV cards', () => {
  it('reads money line items from income.* (not the top level)', () => {
    render(
      <ChapterFinancialAnalysis
        dcf={null}
        rawData={RAW_DATA}
        historicalMetrics={null}
        reportingCurrency="USD"
      />,
    )
    // EBITDA card only renders when baseEbitda !== null — i.e. when income.ebitda
    // is read correctly. Pre-fix (top-level read) this card was always absent.
    expect(screen.getByText('EBITDA')).toBeInTheDocument()
    expect(screen.getByText('净利润')).toBeInTheDocument()
    // Revenue (Base) is a TTM figure (Σ latest 4 quarters), NOT a completed
    // fiscal year — the badge must say TTM (+ the TTM window's end month), not
    // "FY2024" (BUG-10 regression: that claimed a completed fiscal year the
    // pipeline never asserts, since fiscal_period_end is the TTM period end).
    expect(screen.getByText('TTM · 2024-09')).toBeInTheDocument()
    expect(screen.queryByText('FY2024')).not.toBeInTheDocument()
  })

  it('does NOT surface cards when income bucket is absent', () => {
    render(
      <ChapterFinancialAnalysis
        dcf={null}
        rawData={{}}
        historicalMetrics={null}
        reportingCurrency="USD"
      />,
    )
    expect(screen.queryByText('EBITDA')).not.toBeInTheDocument()
  })
})

// Minimal history so the bank trajectory (and its calm note) render; the adapters
// touch every array, so all are present even though the charts are mocked out.
const HIST = {
  years: [2023, 2024],
  revenue: [1e11, 1.1e11],
  revenue_growth_yoy: [null, 0.1],
  cogs: [null, null],
  gross_profit: [null, null],
  gross_margin: [null, null],
  sga: [0, 0],
  sga_ratio: [null, null],
  ebitda: [4e10, 4.4e10],
  ebitda_margin: [0.4, 0.4],
  operating_income: [3e10, 3.2e10],
  operating_margin: [0.3, 0.29],
  net_income: [3e10, 3.2e10],
  eps: [10, 11],
  pe_ratio: [null, 12],
  operating_cash_flow: [0, 0],
  investing_cash_flow: [0, 0],
  financing_cash_flow: [0, 0],
  shareholders_equity: [],
  cagr_revenue: 0.1,
  ticker: 'BNK',
  price_data_available: true,
} as unknown as import('../../../types/finance').HistoricalMetrics

describe('ChapterFinancialAnalysis bank branch (financial_sector)', () => {
  it('omits the EBITDA row and renders the bank trajectory + calm caliber note', () => {
    render(
      <ChapterFinancialAnalysis
        dcf={null}
        rawData={RAW_DATA}
        historicalMetrics={HIST}
        reportingCurrency="USD"
        financialSector
      />,
    )
    // EBITDA is a category error for a bank — the waterfall row is gone.
    expect(screen.queryByText('EBITDA')).not.toBeInTheDocument()
    // Net income is still surfaced.
    expect(screen.getByText('净利润')).toBeInTheDocument()
    // Calm caliber note (zh locale in this file's i18n mock) explains the omission.
    expect(screen.getByText(/口径错误/)).toBeInTheDocument()
  })

  it('non-bank control keeps the EBITDA row (byte-identical path)', () => {
    render(
      <ChapterFinancialAnalysis
        dcf={null}
        rawData={RAW_DATA}
        historicalMetrics={HIST}
        reportingCurrency="USD"
        financialSector={false}
      />,
    )
    expect(screen.getByText('EBITDA')).toBeInTheDocument()
    expect(screen.queryByText(/口径错误/)).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// DCF year axis. The chapter used to take the DCF's base year from the BROWSER
// clock and then drop that row as a duplicate of the last historical bar — a bar
// it did not duplicate, because the series ends at the last REPORTED fiscal year
// (FY2025, while the clock says 2026). 2026 ended up on neither side of the
// merge, so the axis jumped 2025 actual → 2027E forecast in every report.
// ---------------------------------------------------------------------------

/** Trend series ending at FY2025 — the shape every artifact in the store has.
 *  Every array is present (the adapters touch them all — see HIST above). */
const TREND_TO_2025 = {
  years: [2022, 2023, 2024, 2025],
  revenue: [4.42e10, 3.58e10, 3.9e10, 4.43e10],
  revenue_growth_yoy: [null, -0.19, 0.09, 0.14],
  cogs: [null, null, null, null],
  gross_profit: [null, null, null, null],
  gross_margin: [0.57, 0.55, 0.56, 0.55],
  sga: [0, 0, 0, 0],
  sga_ratio: [null, null, null, null],
  ebitda: [1.73e10, 0.99e10, 1.27e10, 1.49e10],
  ebitda_margin: [0.39, 0.28, 0.33, 0.34],
  operating_income: [1.5e10, 0.8e10, 1.1e10, 1.3e10],
  operating_margin: [0.35, 0.24, 0.29, 0.3],
  net_income: [1.3e10, 0.7e10, 1.0e10, 1.2e10],
  eps: [10, 11, 12, 13],
  pe_ratio: [null, 12, 14, 15],
  operating_cash_flow: [0, 0, 0, 0],
  investing_cash_flow: [0, 0, 0, 0],
  financing_cash_flow: [0, 0, 0, 0],
  shareholders_equity: [],
  cagr_revenue: 0.1,
  ticker: 'QCOM',
  price_data_available: true,
} as unknown as import('../../../types/finance').HistoricalMetrics

/** A DCF block with 2 projected years — only the year axis matters here. */
function makeDcfShape(fiscalYear: number | null): import('./types').DcfShape {
  return {
    projected_revenue: [4.41e10, 4.41e10],
    projected_ebitda: [1.44e10, 1.44e10],
    projection_years: 2,
    assumption_current_actuals_fy: fiscalYear,
    inputs: { revenue_base: 4.407e10, ebitda_margin: 0.327, da_pct_revenue: 0.044 },
  } as unknown as import('./types').DcfShape
}

function renderDcfChapter(dcf: import('./types').DcfShape): void {
  revenueChartProps.mockClear()
  render(
    <ChapterFinancialAnalysis
      dcf={dcf}
      rawData={null}
      historicalMetrics={TREND_TO_2025}
      reportingCurrency="USD"
    />,
  )
}

/** The x-axis categories the revenue chart was handed, in order. */
function chartYears(): string[] {
  const props = revenueChartProps.mock.calls.at(-1)?.[0] as { data: { year: string }[] } | undefined
  return (props?.data ?? []).map((row) => row.year)
}

describe('ChapterFinancialAnalysis DCF year axis (2026 must not vanish)', () => {
  it('bridges the last actual year to the DCF schedule — no hole in the axis', () => {
    renderDcfChapter(makeDcfShape(2025))
    expect(chartYears()).toEqual(['2022', '2023', '2024', '2025', '2026E', '2027E'])
  })

  it('falls back to the last reported fiscal year when the anchor field is absent', () => {
    renderDcfChapter(makeDcfShape(null))
    expect(chartYears()).toEqual(['2022', '2023', '2024', '2025', '2026E', '2027E'])
  })
})

// ---------------------------------------------------------------------------
// Forecast basis (i1): the DCF base is a TTM run-rate, so labelling it with the
// anchor YEAR collided with the FY bar, the base row was dropped as a duplicate,
// and the chart jumped FY2025 → 2026E — the TTM×growth first forecast read as a
// near-doubling. The base row now carries "TTM (Mon YYYY)" and the first forecast
// year states its basis.
// ---------------------------------------------------------------------------

/** A DCF block whose forecast_basis makes the TTM base explicit. */
function makeTtmDcfShape(): DcfShape {
  return {
    ...makeDcfShape(2025),
    forecast_basis: { base: 'ttm', base_period_end: '2025-07-26', first_forecast_year: 2026 },
  } as unknown as DcfShape
}

describe('ChapterFinancialAnalysis forecast basis (TTM base visible)', () => {
  it('renders the TTM base with a non-colliding label and marks the first forecast year', () => {
    renderDcfChapter(makeTtmDcfShape())
    expect(chartYears()).toEqual([
      '2022',
      '2023',
      '2024',
      '2025',
      'TTM (Jul 2025)',
      '2026E (TTM+1)',
      '2027E',
    ])
  })
})

// ---------------------------------------------------------------------------
// Series honesty (change 3 / i4/i5): the DCF carries NO forecast gross margin —
// the forecast rows are EBITDA / operating margin only. The chart must say so, or
// the ~66% forecast EBITDA margin reads as a gross-margin forecast vs a ~75% TTM
// actual.
// ---------------------------------------------------------------------------

describe('ChapterFinancialAnalysis series honesty labels', () => {
  it('labels the margin series: forecast = EBITDA / operating margin, gross margin history-only', () => {
    renderDcfChapter(makeTtmDcfShape())
    const note = screen.getByTestId('margin-forecast-caliber')
    expect(note.textContent).toContain('预测年份只给 EBITDA 利润率与营业(EBIT)利润率')
    expect(note.textContent).toContain('毛利率曲线为历史口径')
  })

  it('states the annual-vs-TTM EBITDA caliber beside the revenue/EBITDA chart', () => {
    renderDcfChapter(makeTtmDcfShape())
    const note = screen.getByTestId('ebitda-caliber-note')
    // TREND_TO_2025 carries no frozen label → the static zh disclosure renders.
    expect(note.textContent).toContain('营业利润 + 折旧摊销')
  })

  it('prefers the frozen payload caliber label when present', () => {
    revenueChartProps.mockClear()
    render(
      <ChapterFinancialAnalysis
        dcf={makeTtmDcfShape()}
        rawData={null}
        historicalMetrics={
          {
            ...TREND_TO_2025,
            ebitda_caliber: 'FROZEN CALIBER LABEL',
          } as unknown as HistoricalMetrics
        }
        reportingCurrency="USD"
      />,
    )
    expect(screen.getByTestId('ebitda-caliber-note').textContent).toBe('FROZEN CALIBER LABEL')
  })
})
