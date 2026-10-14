import type { DCFResult, CompsResult, HistoricalMetrics } from '../types/finance'
import { tSync } from '../i18n'

const MONTH_ABBR = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
]

/**
 * Non-colliding axis label for the DCF's TTM run-rate base row.
 *
 * The base row restates the DCF's fiscal anchor year but carries a TTM run-rate,
 * not that year's reported figure. Its old `${baseYear}` label COLLIDED with the
 * historical bar for the same year, so `mergeDcfBaseRow` dropped it as a
 * duplicate and the chart jumped the last FY bar → first forecast year (NVDA:
 * FY2026 215.9B → 2027E 424.2B), making the TTM×growth first forecast read as
 * +96%. Labelling it "TTM (Jul 2026)" keeps it distinct from the FY bar and
 * states the basis. Returns null when the base period end is unknown (a legacy
 * artifact without `forecast_basis`), keeping the plain year label.
 */
export function ttmBaseLabel(basePeriodEnd?: string | null): string | null {
  if (!basePeriodEnd) return null
  const match = /^(\d{4})-(\d{2})/.exec(basePeriodEnd)
  if (!match) return null
  const month = Number(match[2])
  if (!Number.isInteger(month) || month < 1 || month > 12) return null
  return `TTM (${MONTH_ABBR[month - 1]} ${match[1]})`
}

/**
 * The canonical TTM income block's own figures (``raw_data.income``), for the DCF
 * chart's BASE row.
 *
 * The base row is a PERIOD node, not a model assumption: it must carry what the
 * trailing twelve months actually produced, exactly as the chapter's
 * ProfitWaterfall cards and the report's data section do. Deriving it from the
 * model's own assumption instead (``inputs.revenue_base × inputs.ebitda_margin``)
 * put two different "TTM EBITDA" numbers in the SAME chapter: GMED 2026-10-14
 * plotted $695.6M (TTM revenue × the trailing-3yr median margin the FORECAST
 * applies) beside a waterfall card reading $953.7M (the statement's own EBIT + D&A)
 * and a data section publishing $953.7M — a 37% gap a reader cannot reconcile.
 * ``null`` / absent falls back to the model base (an artifact with no income block).
 */
export interface TtmActuals {
  ebitda: number | null
  ebitdaMargin: number | null
  operatingMargin: number | null
}

/**
 * Build Revenue & EBITDA bar chart data from DCF projections.
 * Year 0 = base year (actual), Years 1..N = forecast.
 *
 * `baseYear` is the DCF's OWN fiscal anchor (`assumption_current_actuals_fy` —
 * the last reported fiscal year at generation time), NOT the browser clock.
 * It is a required argument on purpose: this adapter derived the axis from
 * `new Date().getFullYear()` before, which labelled the base year with the
 * CURRENT calendar year — always ahead of the last reported fiscal year — and
 * pushed the whole projection a year past the DCF's own schedule (its FY2026-35
 * schedule rendered as 2027E-2036E). Combined with the chapter dropping the base
 * row (it restates the last historical bar), that punched a hole in the axis in
 * EVERY report: 2025 actual → 2027E forecast, no 2026. A wall-clock default here
 * would reintroduce exactly that, so the caller resolves the anchor.
 *
 * `basePeriodEnd` is the TTM base window's ISO end (`forecast_basis
 * .base_period_end`). When present the base row is labelled "TTM (Mon YYYY)"
 * instead of the bare anchor year — it must NOT collide with the historical bar
 * for that same fiscal year (see `ttmBaseLabel`) — and the first forecast year
 * carries its basis ("2027E (TTM+1)").
 *
 * `ttmActuals` carries the canonical TTM income block's own figures, so the base
 * row shows what the period ACTUALLY produced rather than the model's assumption
 * (see `TtmActuals`); absent, the model base stands in.
 */
export function dcfResultToRevenueEbitdaData(
  result: DCFResult,
  baseYear: number,
  firstForecastYear?: number | null,
  basePeriodEnd?: string | null,
  ttmActuals?: TtmActuals | null,
): Array<Record<string, number | string | boolean | null>> {
  const rows: Array<Record<string, number | string | boolean | null>> = []

  // Base year (actual). A TTM-based run-rate leaves its basis on the label so it
  // cannot collide with (and be dropped in favour of) the FY bar.
  const baseLabel = ttmBaseLabel(basePeriodEnd)
  rows.push({
    year: baseLabel ?? String(baseYear),
    revenue: result.inputs.revenue_base,
    ebitda: ttmActuals?.ebitda ?? result.inputs.revenue_base * result.inputs.ebitda_margin,
    is_forecast: false,
  })

  // Projected years. Prefer the backend's `financial_modeling.forecast_basis
  // .first_forecast_year` (the DCF base is a TTM figure, so the first forecast
  // year is not necessarily baseFY + 1 — labelling a twelve-month period ending
  // mid-2027 "2026E" was the defect); fall back to baseFY + 1 when it is absent.
  const start = firstForecastYear != null ? firstForecastYear : baseYear + 1
  for (let i = 0; i < result.projected_revenue.length; i++) {
    rows.push({
      // The first forecast year states its basis when the base was a TTM run-rate.
      year: i === 0 && baseLabel !== null ? `${start}E (TTM+1)` : `${start + i}E`,
      revenue: result.projected_revenue[i],
      ebitda: result.projected_ebitda[i],
      is_forecast: true,
    })
  }

  return rows
}

/**
 * Build margin trend data from DCF projections.
 *
 * EBITDA margin is taken straight from the projection. The `operating_margin`
 * series is the DERIVED EBIT margin (EBITDA margin − D&A%), since EBIT =
 * EBITDA − D&A; the DCF result carries no GAAP operating-income figure for
 * future years, so this is an assumption-driven approximation, not a reported
 * number. When `da_pct_revenue` is unknown we emit `null` rather than 0 —
 * defaulting D&A to zero would render operating_margin == ebitda_margin and
 * falsely imply the company has no depreciation drag.
 *
 * `baseYear` is the DCF's own fiscal anchor — see
 * `dcfResultToRevenueEbitdaData` for why it is required and never the browser
 * clock (a wall-clock base year put the projection a year ahead of the DCF
 * schedule and, once the base row was dropped as a duplicate, left a hole in
 * the axis: 2025 actual → 2027E forecast, no 2026).
 * `basePeriodEnd` is the TTM base window's ISO end — see
 * `dcfResultToRevenueEbitdaData`: it relabels the base row "TTM (Mon YYYY)" (so it
 * can't collide with the FY bar) and marks the first forecast year "(TTM+1)".
 */
export function dcfResultToMarginData(
  result: DCFResult,
  baseYear: number,
  firstForecastYear?: number | null,
  basePeriodEnd?: string | null,
  ttmActuals?: TtmActuals | null,
): Array<Record<string, number | string | boolean | null>> {
  const rows: Array<Record<string, number | string | boolean | null>> = []

  // null (not 0) when D&A% is unknown — see docstring.
  const daPct =
    result.inputs.da_pct_revenue != null && result.inputs.da_pct_revenue > 0
      ? result.inputs.da_pct_revenue
      : null
  const ebitMargin = (ebitdaMargin: number): number | null =>
    daPct != null ? ebitdaMargin - daPct : null

  // Base year — the period's OWN margins when the snapshot carries them (see
  // TtmActuals): the historical bars beside it are actuals, so a base row holding
  // the forecast's assumption would both mislabel the period and hide the margin
  // step the model deliberately takes from today into the projection.
  const baseEbitdaMargin = ttmActuals?.ebitdaMargin ?? result.inputs.ebitda_margin
  const baseLabel = ttmBaseLabel(basePeriodEnd)
  rows.push({
    year: baseLabel ?? String(baseYear),
    ebitda_margin: baseEbitdaMargin,
    operating_margin: ttmActuals?.operatingMargin ?? ebitMargin(baseEbitdaMargin),
    is_forecast: false,
  })

  // Projected years — first forecast year from forecast_basis when available,
  // else the baseFY + 1 rule (see dcfResultToRevenueEbitdaData).
  const start = firstForecastYear != null ? firstForecastYear : baseYear + 1
  for (let i = 0; i < result.projected_revenue.length; i++) {
    const rev = result.projected_revenue[i]
    const ebitda = result.projected_ebitda[i]
    const ebitdaMargin = rev > 0 ? ebitda / rev : 0
    rows.push({
      year: i === 0 && baseLabel !== null ? `${start}E (TTM+1)` : `${start + i}E`,
      ebitda_margin: ebitdaMargin,
      operating_margin: ebitMargin(ebitdaMargin),
      is_forecast: true,
    })
  }

  return rows
}

/**
 * Merge a historical series with the DCF rows, reconciling the base year.
 *
 * The DCF's base row rests on `revenue_base`, a TTM run-rate — NOT the last
 * reported fiscal year's figure. When the base row carries the anchor YEAR label
 * (a legacy artifact with no `forecast_basis`, see `ttmBaseLabel`) it collides with
 * the historical bar for that year, which is the reported actual and therefore the
 * authority; the base row is then dropped so the bar shown is the filing, not the
 * run-rate. When it carries a distinct TTM label ("TTM (Jul 2026)") it no longer
 * collides and is KEPT, so the run-rate basis is visible beside the FY bar.
 *
 * When the series does NOT reach the anchor year at all (the vendor annual series
 * can lag the DCF's own anchor), the base row bridges the two and is kept in every
 * case — dropping it would leave a hole in the axis (the "2025 actual → 2027E
 * forecast, no 2026" case this fixes).
 */
export function mergeDcfBaseRow(
  historical: Array<Record<string, number | string | boolean | null>>,
  dcfRows: Array<Record<string, number | string | boolean | null>>,
): Array<Record<string, number | string | boolean | null>> {
  if (dcfRows.length === 0) return historical
  const [base, ...forecast] = dcfRows
  const covered = historical.some((row) => row.year === base.year)
  return covered ? [...historical, ...forecast] : [...historical, base, ...forecast]
}

/**
 * Convert CompsResult into PeerComparisonChart format.
 * Target row is flagged with is_target: true.
 */
export function compsResultToPeerChartData(
  result: CompsResult,
): Array<Record<string, number | string | boolean | null>> {
  const all = [result.target, ...result.peers]
  return all.map((c) => ({
    ticker: c.ticker,
    ev_ebitda: c.ev_ebitda,
    // P/B rides along so the balance-sheet-financial branch can plot it as the
    // primary bar in place of EV/EBITDA (a category error for deposit-takers).
    pb_ratio: c.pb_ratio ?? null,
    pe_ratio: c.pe_ratio,
    is_target: c.ticker === result.target.ticker,
  }))
}

/**
 * Convert CompsResult into CompanyRadarChart format.
 * Each dimension is normalised so that the larger of (company, peer median) = 100,
 * giving both the company and benchmark shapes that are easy to compare visually.
 */
export function compsResultToRadarData(
  result: CompsResult,
): Array<Record<string, number | string | boolean | null>> {
  const t = result.target

  // Compute peer medians for margin dimensions (not in CompsResult directly)
  const medianOf = (values: number[]): number | null => {
    const valid = values.filter((v) => v != null && isFinite(v))
    if (valid.length === 0) return null
    const sorted = [...valid].sort((a, b) => a - b)
    const mid = Math.floor(sorted.length / 2)
    return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid]
  }

  const peerGrossMedian = medianOf(result.peers.map((p) => p.gross_margin))
  const peerOpMedian = medianOf(result.peers.map((p) => p.operating_margin))

  // lowerBetter marks the valuation-multiple axes (cheaper = better) vs the
  // margin axes (higher = better) so both can be mapped to a consistent
  // "outward = more favorable" radial direction below.
  const dims: {
    label: string
    company: number | null
    median: number | null
    lowerBetter: boolean
  }[] = [
    {
      label: tSync('chart.radar.dim.pe'),
      company: t.pe_ratio,
      median: result.median_pe,
      lowerBetter: true,
    },
    {
      label: tSync('chart.radar.dim.evEbitda'),
      company: t.ev_ebitda,
      median: result.median_ev_ebitda,
      lowerBetter: true,
    },
    {
      label: tSync('chart.radar.dim.evRevenue'),
      company: t.ev_revenue,
      median: result.median_ev_revenue,
      lowerBetter: true,
    },
    {
      label: tSync('chart.radar.dim.grossMargin'),
      company: t.gross_margin,
      median: peerGrossMedian,
      lowerBetter: false,
    },
    {
      label: tSync('chart.radar.dim.operatingMargin'),
      company: t.operating_margin,
      median: peerOpMedian,
      lowerBetter: false,
    },
  ]

  // Map each axis so "outward = more favorable vs the peer median" CONSISTENTLY:
  // a cheaper multiple (lower) AND a higher margin both push the company point OUT
  // past the benchmark ring. The old normalization divided by max(|company|,
  // |median|), so a cheaper — i.e. better — multiple plotted *smaller/inside* and
  // read backwards. The peer median is pinned to a fixed ring (100); the company
  // sits at favorability×100, capped to [0,200] so an extreme outlier (e.g. a
  // 226× P/E peer) can't blow out the axis. Ill-defined axes are dropped: a
  // multiple needs company>0 & median>0 (a negative P/E is N/A, not "cheap").
  return dims
    .filter((d) => {
      if (d.company == null || d.median == null || !isFinite(d.company) || !isFinite(d.median)) {
        return false
      }
      return d.lowerBetter ? d.company > 0 && d.median > 0 : d.median > 0
    })
    .map((d) => {
      const company = d.company as number
      const median = d.median as number
      const ratio = d.lowerBetter ? median / company : company / median
      return {
        dimension: d.label,
        value: Math.round(Math.max(0, Math.min(200, ratio * 100))),
        benchmark: 100,
      }
    })
}

// ── FinancialsTab adapters (from HistoricalMetrics) ────────────────────

export function historicalToRevenueEbitdaData(h: HistoricalMetrics) {
  return h.years.map((year, i) => ({
    year: String(year),
    revenue: h.revenue[i],
    ebitda: h.ebitda[i],
    is_forecast: false,
  }))
}

export function historicalToMarginData(h: HistoricalMetrics) {
  // MarginTrendChart.formatPercent already does value * 100,
  // so feed raw fractions (0-1 range) to match dcfResultToMarginData behavior.
  return h.years.map((year, i) => ({
    year: String(year),
    gross_margin: h.gross_margin[i],
    ebitda_margin: h.ebitda_margin[i],
    operating_margin: h.operating_margin[i],
    is_forecast: false,
  }))
}

/**
 * Bank-caliber trajectory (balance-sheet financials): Revenue + Net Income bars
 * plus a Return-on-Equity line. EBITDA / EBITDA-margin are a category error for
 * deposit-takers, so this replaces the Revenue&EBITDA + margin charts.
 *
 * ROE = net_income / shareholders_equity per year — emitted ONLY when that year's
 * equity is a positive finite number (the field is empty on artifacts generated
 * before the 2026-07-06 equity plumbing). A year without valid equity carries
 * roe=null and the chart degrades to Revenue + Net Income (never fabricated).
 */
export function historicalToBankTrajectoryData(h: HistoricalMetrics) {
  const equity = h.shareholders_equity ?? []
  return h.years.map((year, i) => {
    const eq = equity[i]
    const ni = h.net_income[i]
    const roe =
      typeof eq === 'number' && Number.isFinite(eq) && eq > 0 && ni != null ? ni / eq : null
    return { year: String(year), revenue: h.revenue[i], net_income: ni, roe }
  })
}

export function historicalToCashFlowData(h: HistoricalMetrics) {
  return h.years.map((year, i) => ({
    year: String(year),
    operating: h.operating_cash_flow[i],
    investing: h.investing_cash_flow[i],
    financing: h.financing_cash_flow[i],
  }))
}

/**
 * Annual BASIC EPS (not diluted — FMP's `eps` field is basic, and the
 * yfinance path preferentially matches a "Basic EPS" row when present; see
 * fmp_provider.py's per-year extraction comment) with YoY growth. Historical
 * P/E is intentionally NOT paired here: the backend only carries a
 * current-year P/E (prior years are null), so an EPS×P/E dual chart would
 * render a one-point P/E line. EPS itself is fully populated, so this powers
 * a clean EPS-trend bar chart instead. yoy uses abs(prev) as the base so a
 * swing off a tiny/negative EPS keeps its sign without flipping.
 */
export function historicalToEpsData(h: HistoricalMetrics) {
  return h.years.map((year, i) => {
    const eps = h.eps[i]
    const prev = i > 0 ? h.eps[i - 1] : null
    const yoy =
      prev != null && prev !== 0 && eps != null ? ((eps - prev) / Math.abs(prev)) * 100 : null
    return { year: String(year), eps, yoy }
  })
}
