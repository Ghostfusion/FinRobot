// Fund research (fund_research) chapter contract.
//
// Why this exists: the desktop had ONE report shape (the equity 15-chapter
// spine), so a fund artifact either fell into the compact viewer's flat key/value
// fallback or — worse — rendered through the equity chapters as a set of empty
// shells. This pins the fund report end to end:
//   • the five section ids, in order, are exactly the fund manifest's — so the
//     rail, the deep-link validator and the body cannot disagree;
//   • the UNIT contract holds at the display edge: the artifact stores FRACTIONS
//     (0.0015 = 15 bp of expense, 0.068748 = a 6.87% position) and the chapters
//     render them as the percentages they are — the "multiplied twice" failure
//     would print a 15 bp fee as "0.15%" of-what, or a 6.87% holding as "0.07%";
//   • an absent field reads "Not reported", never 0 or a bare dash that reads
//     like a number (an unreported expense ratio must not look like a free fund);
//   • the chart is the fund's own NAV/price series, and NOTHING on a fund page
//     implies a company's revenue / EBITDA / cash flow — a fund has none.
//
// Numbers below are a plausible IEI-like intermediate-Treasury ETF, chosen so no
// two formatted values collide (a duplicate string would make getByText ambiguous
// and hide a real rendering bug behind a test error).

import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

import { FundReportChapters } from './FundReportChapters'
import { deriveReportData } from './reportData'
import { fundSectionEntries, isReportSectionId } from './reportSections'
import { useUiPrefs } from '../../i18n'
import type { ArtifactDetail } from '../../hooks/useV5Artifacts'

/** A complete fund artifact: every pinned key present. */
const RICH = {
  ticker: 'IEI',
  instrument: 'fund',
  name: 'iShares 3-7 Year Treasury Bond ETF',
  fund_family: 'iShares',
  legal_type: 'Exchange Traded Fund',
  category: 'Intermediate Government',
  inception_date: '2007-01-05',
  currency: 'USD',
  total_net_assets: 13_400_000_000,
  nav_per_share: 120.55,
  market_price: 120.41,
  // market price BELOW nav → a discount. Negative = discount, positive = premium.
  premium_discount: -0.0012,
  net_expense_ratio: 0.0015, // 15 bp
  gross_expense_ratio: 0.0017,
  category_avg_expense_ratio: 0.0053,
  turnover: 0.2413,
  cost_drag: {
    expense_drag_usd_per_10k: 75,
    fee_share_of_gross_return: 0.0412,
    horizon_years: 5,
  },
  distribution_yield: 0.0382,
  returns: {
    cagr_1y: 0.0512,
    cagr_3y: -0.0173,
    cagr_5y: 0.0041,
    ytd: 0.0417,
    return_3m: -0.0067,
  },
  volatility: 0.0561,
  max_drawdown: -0.1132,
  sharpe: 0.42,
  asset_classes: { Bond: 0.9638, Cash: 0.0362 },
  // A Treasury book has no equity sectors at all — the fund page must say so.
  sector_weights: {},
  bond_ratings: { AAA: 0.55, AA: 0.45 },
  bond_duration: 3.42,
  bond_maturity: 4.11,
  equity_pe: 18.4,
  top_holdings: [
    { symbol: '91282C', name: 'US Treasury Note', weight: 0.068748 },
    { symbol: '912828', name: 'US Treasury Bond', weight: 0.0431 },
  ],
  concentration: { top10_weight: 0.4123, hhi: 0.0231, effective_n: 43.3 },
  nav_series: [
    { date: '2025-10-13', close: 113.42 },
    { date: '2026-10-12', close: 120.41 },
  ],
  warnings: [],
}

const SUMMARY = 'IEI holds intermediate Treasuries with a 3.4-year duration.'

function artifact(
  structured: Record<string, unknown>,
  summary: string | null = SUMMARY,
): ArtifactDetail {
  return {
    id: 'fund-art-1',
    ticker: 'IEI',
    type: 'fund_research',
    created_at: '2026-10-12T00:00:00+00:00',
    outputs: { structured, summary_text: summary, warnings: [] },
    inputs: {},
    assumptions: {},
    meta: {},
  }
}

function renderFund(art: ArtifactDetail): HTMLElement {
  return render(<FundReportChapters artifact={art} />).container
}

describe('FundReportChapters — the fund spine', () => {
  beforeEach(() => {
    // The chapters read their copy through lingui; pin the locale so the
    // assertions below compare against a known language rather than whatever the
    // previous test file left activated.
    useUiPrefs.setState({ locale: 'en' })
  })

  it('renders the five fund chapters in order, matching the fund manifest', () => {
    const container = renderFund(artifact(RICH))
    const ids = [...container.querySelectorAll('section[id]')].map((el) => el.id)

    expect(ids).toEqual([
      'fund-profile',
      'fund-cost',
      'fund-holdings',
      'fund-risk',
      'fund-narrative',
    ])
    // …which is the manifest the rail and the deep-link validator read.
    expect(ids).toEqual(fundSectionEntries('en').map((e) => e.id))
    for (const id of ids) expect(isReportSectionId(id)).toBe(true)
  })

  it('never renders an equity chapter for a fund', () => {
    const container = renderFund(artifact(RICH))

    for (const equityId of ['thesis', 'valuation', 'financial', 'filings', 'ownership', 'cover']) {
      expect(container.querySelector(`section#${equityId}`)).toBeNull()
    }
  })

  it('formats fractions as the percentages they are', () => {
    renderFund(artifact(RICH))

    expect(screen.getByText('0.15%')).toBeTruthy() // net expense ratio 0.0015
    expect(screen.getByText('0.53%')).toBeTruthy() // category average 0.0053
    expect(screen.getByText('24.1%')).toBeTruthy() // turnover 0.2413
    expect(screen.getByText('3.82%')).toBeTruthy() // distribution yield 0.0382
    expect(screen.getByText('6.87%')).toBeTruthy() // top holding 0.068748
    expect(screen.getByText('4.12%')).toBeTruthy() // fee share of gross return
    expect(screen.getByText('5.12%')).toBeTruthy() // 1-year 0.0512
    expect(screen.getByText('-1.73%')).toBeTruthy() // 3-year annualised, a loss
    expect(screen.getByText('-11.32%')).toBeTruthy() // max drawdown -0.1132
    expect(screen.getByText('55.00%')).toBeTruthy() // AAA share 0.55
    expect(screen.getByText('3.42')).toBeTruthy() // duration, in YEARS — not a percent
    expect(screen.getByText('0.0231')).toBeTruthy() // HHI
    expect(screen.getByText('43.3')).toBeTruthy() // effective N
  })

  it('names the premium/discount direction instead of leaving the sign to the reader', () => {
    renderFund(artifact(RICH))

    expect(screen.getByText('-0.12%')).toBeTruthy()
    expect(screen.getByText('Discount to NAV')).toBeTruthy()
    expect(screen.getByText(/positive figure means the fund trades ABOVE its NAV/)).toBeTruthy()
  })

  it('reads a premium as a premium when the market price sits above NAV', () => {
    renderFund(artifact({ ...RICH, market_price: 120.65, premium_discount: 0.0008 }))

    expect(screen.getByText('0.08%')).toBeTruthy()
    expect(screen.getByText('Premium to NAV')).toBeTruthy()
  })

  it('shows the per-$10,000 cost arithmetic so a reader can check it', () => {
    renderFund(artifact(RICH))

    expect(screen.getByText('$75.00')).toBeTruthy() // the artifact's own drag figure
    expect(
      screen.getByText(
        /Net expense ratio 0\.15% of \$10,000 = \$15\.00 a year; over 5 years = \$75\.00\./,
      ),
    ).toBeTruthy()
    expect(screen.getByText(/simple, undiscounted product/)).toBeTruthy()
  })

  it('renders a bond book without inventing sectors, and states the absence', () => {
    renderFund(artifact(RICH))

    expect(screen.getByText(/No sector breakdown is reported/)).toBeTruthy()
    expect(screen.getByText('AAA')).toBeTruthy()
    expect(screen.getByText('45.00%')).toBeTruthy()
    expect(screen.getByText('Duration (years)')).toBeTruthy()
  })

  it('states an absent credit mix for an equity fund rather than printing zeros', () => {
    renderFund(
      artifact({
        ...RICH,
        bond_ratings: {},
        bond_duration: null,
        bond_maturity: null,
        sector_weights: { Technology: 0.31, Financials: 0.19 },
      }),
    )

    expect(screen.getByText(/No credit-quality breakdown is reported/)).toBeTruthy()
    expect(screen.getByText('Technology')).toBeTruthy()
    expect(screen.getByText('31.00%')).toBeTruthy()
    // A fund with no bond book still reports a portfolio P/E — the bond-measures
    // module must not swallow it just because duration/maturity are absent.
    expect(screen.getByText('18.4')).toBeTruthy()
  })

  it('charts the fund’s own NAV series and no company P&L series', () => {
    const container = renderFund(artifact(RICH))

    expect(screen.getByTestId('fund-nav-chart')).toBeTruthy()
    expect(screen.getByText(/Trailing NAV \/ traded close/)).toBeTruthy()
    // Nothing on a fund page may imply an income statement: a fund has no
    // revenue, EBITDA or free cash flow, so those words (and their charts) have
    // no business here.
    expect(container.textContent).not.toMatch(/EBITDA|Revenue|Free Cash Flow|WACC|Enterprise Value/)
  })

  it('renders an explicit not-reported for absent fields, never a zero', () => {
    const container = renderFund(
      artifact({ ticker: 'VFIAX', instrument: 'fund', currency: 'USD' }, null),
    )

    const notReported = screen.getAllByText('Not reported')
    expect(notReported.length).toBeGreaterThan(5)
    // The three "measure inapplicable / series absent" statements, each its own
    // sentence rather than a blank section.
    expect(screen.getByText(/No asset-class breakdown is reported/)).toBeTruthy()
    expect(screen.getByText(/No credit-quality breakdown is reported/)).toBeTruthy()
    expect(screen.getByText(/No top-holdings list is reported/)).toBeTruthy()
    expect(screen.getByText(/carries no NAV or price series/)).toBeTruthy()
    expect(screen.queryByTestId('fund-nav-chart')).toBeNull()
    expect(screen.getByText(/This run wrote no narrative/)).toBeTruthy()
    expect(container.textContent).not.toContain('NaN')
    expect(container.textContent).not.toContain('undefined')
  })

  it('renders the run’s narrative prose verbatim', () => {
    renderFund(artifact(RICH))

    expect(screen.getByText(SUMMARY)).toBeTruthy()
  })

  it('keeps the page-level derivation safe for a fund artifact', () => {
    // The detail page calls deriveReportData for EVERY artifact to build the
    // toolbar / rail chrome. A fund carries none of the equity blocks, so the
    // derivation must resolve to nulls (never throw, never invent a thesis) for
    // the fund page to mount at all.
    const derived = deriveReportData(artifact(RICH), [], 'en')

    expect(derived.symbol).toBe('IEI')
    expect(derived.thesis).toBeNull()
    expect(derived.valuationSynthesis).toBeNull()
    expect(derived.creditRisk).toBeNull()
    expect(derived.quoteCurrency).toBe('USD')
  })
})
