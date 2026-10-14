// Vitest coverage for chapter 12 (Ownership & Governance).
// Covers: empty (no ownership_governance at all), degraded sub-block,
// populated state across all four sub-blocks (insiders / institutions /
// compensation / 13D-G alerts).

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { ChapterOwnershipGovernance } from './ChapterOwnershipGovernance'
import type {
  FilingProvenanceShape,
  InsiderTransactionShape,
  InstitutionalHoldingShape,
  OwnershipGovernanceShape,
  ProxyCompensationShape,
  ScheduleThirteenAlertShape,
} from './types'

function wrap(node: React.ReactElement) {
  return <MemoryRouter>{node}</MemoryRouter>
}

const baseProv = (form: string): FilingProvenanceShape => ({
  form,
  filing_date: '2026-02-15',
  accession_no: '0001234567-26-000123',
  source_url: 'https://www.sec.gov/cgi-bin/browse-edgar',
})

describe('ChapterOwnershipGovernance', () => {
  it('renders settings CTA when ownership_governance is absent', () => {
    render(wrap(<ChapterOwnershipGovernance ownership={null} reportingCurrency="USD" />))
    expect(screen.getByText(/SEC EDGAR identity required/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open Settings/i })).toHaveAttribute(
      'href',
      '/settings',
    )
  })

  it('renders insider transactions table when populated', () => {
    const insider: InsiderTransactionShape = {
      filing_date: '2026-04-12',
      accession_no: '0001234567-26-000456',
      insider_name: 'Jensen Huang',
      insider_position: 'CEO',
      transaction_type: 'sale',
      code: 'S',
      shares: 240000,
      value: 28800000,
      price_per_share: 120,
      provenance: baseProv('4'),
    }
    const ownership: OwnershipGovernanceShape = {
      insider_transactions: [insider],
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.getByText('Jensen Huang')).toBeInTheDocument()
    expect(screen.getByText(/Insider Transactions/i)).toBeInTheDocument()
    // Sale label rendered from i18n catalog (en), not raw "sale"
    expect(screen.getByText('Sale')).toBeInTheDocument()
  })

  // External audit: the list caps at 12 rows while the flow aggregate sums EVERY
  // row the card received (THC: 12 shown of 20). An analyst summed the visible 12
  // and reported a $9.9M gap vs the aggregate that does not exist. The list must
  // disclose the subset it shows.
  it('labels the insider list as a subset when it caps at 12 of more rows', () => {
    const rows: InsiderTransactionShape[] = Array.from({ length: 20 }, (_, i) => ({
      filing_date: `2026-04-${String(20 - i).padStart(2, '0')}`,
      accession_no: `0001234567-26-0000${String(i).padStart(2, '0')}`,
      insider_name: `Insider ${i}`,
      transaction_type: 'sale',
      code: 'S',
      shares: 1000,
      value: 100_000,
      provenance: baseProv('4'),
    }))
    const ownership: OwnershipGovernanceShape = {
      insider_transactions: rows,
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    const cap = screen.getByTestId('insider-table-cap').textContent ?? ''
    expect(cap).toMatch(/12/) // rows shown
    expect(cap).toMatch(/20/) // rows the aggregate covers
    expect(cap).toMatch(/aggregates all 20/i)
  })

  it('omits the subset label when the list is not capped', () => {
    const rows: InsiderTransactionShape[] = Array.from({ length: 3 }, (_, i) => ({
      filing_date: `2026-04-0${i + 1}`,
      accession_no: `0001234567-26-00010${i}`,
      insider_name: `Insider ${i}`,
      transaction_type: 'purchase',
      code: 'P',
      shares: 1000,
      value: 100_000,
      provenance: baseProv('4'),
    }))
    const ownership: OwnershipGovernanceShape = {
      insider_transactions: rows,
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.queryByTestId('insider-table-cap')).not.toBeInTheDocument()
  })

  it('renders institutional holdings sorted by value descending', () => {
    const small: InstitutionalHoldingShape = {
      holder_name: 'Small Fund',
      cusip: '67066G104',
      name_of_issuer: 'NVIDIA CORP',
      shares: 100_000,
      value_usd: 12_000_000,
      period_end: '2026-03-31',
      provenance: baseProv('13F-HR'),
    }
    const big: InstitutionalHoldingShape = {
      holder_name: 'BlackRock',
      cusip: '67066G104',
      name_of_issuer: 'NVIDIA CORP',
      shares: 100_000_000,
      value_usd: 12_000_000_000,
      period_end: '2026-03-31',
      shares_change_pct: 4.2,
      provenance: baseProv('13F-HR'),
    }
    const ownership: OwnershipGovernanceShape = {
      institutional_holdings: [small, big],
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    const rows = screen.getAllByRole('row')
    // First row = header; second row = highest-value (BlackRock)
    expect(rows[1].textContent).toContain('BlackRock')
    expect(rows[2].textContent).toContain('Small Fund')
  })

  it('labels institutional rows by 13F share class when the same holder files multiple classes (GOOGL/GOOG)', () => {
    const classA: InstitutionalHoldingShape = {
      holder_name: 'BlackRock, Inc.',
      cusip: '02079K305',
      name_of_issuer: 'ALPHABET INC',
      title_of_class: 'CAP STK CL A',
      shares: 446_980_992,
      value_usd: 80_000_000_000,
      period_end: '2026-03-31',
      provenance: baseProv('13F-HR'),
    }
    const classC: InstitutionalHoldingShape = {
      holder_name: 'BlackRock, Inc.',
      cusip: '02079K107',
      name_of_issuer: 'ALPHABET INC',
      title_of_class: 'CAP STK CL C',
      shares: 364_758_302,
      value_usd: 65_000_000_000,
      period_end: '2026-03-31',
      provenance: baseProv('13F-HR'),
    }
    const ownership: OwnershipGovernanceShape = {
      institutional_holdings: [classA, classC],
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    // Both rows keep the same holder name (real, distinct 13F filings —
    // never merged) but each carries a distinct, SEC-sourced class badge so
    // the two "BlackRock, Inc." rows don't read as a duplicate-data bug.
    expect(screen.getAllByText('BlackRock, Inc.')).toHaveLength(2)
    expect(screen.getByText('Class A')).toBeInTheDocument()
    expect(screen.getByText('Class C')).toBeInTheDocument()
  })

  it('omits the share-class badge when every row shares the same class (single-class ticker)', () => {
    const rowA: InstitutionalHoldingShape = {
      holder_name: 'Vanguard',
      cusip: '037833100',
      name_of_issuer: 'APPLE INC',
      title_of_class: 'COM',
      shares: 1_000_000,
      value_usd: 200_000_000,
      period_end: '2026-03-31',
      provenance: baseProv('13F-HR'),
    }
    const rowB: InstitutionalHoldingShape = {
      holder_name: 'BlackRock',
      cusip: '037833100',
      name_of_issuer: 'APPLE INC',
      title_of_class: 'COM',
      shares: 900_000,
      value_usd: 180_000_000,
      period_end: '2026-03-31',
      provenance: baseProv('13F-HR'),
    }
    const ownership: OwnershipGovernanceShape = {
      institutional_holdings: [rowA, rowB],
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.queryByText('Class', { exact: false })).not.toBeInTheDocument()
  })

  it('renders cold-state placeholder for degraded sub-section', () => {
    const ownership: OwnershipGovernanceShape = {
      institutional_holdings: [],
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: ['institutional_holdings'],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    // Honest cold-state copy: the old text promised a "background sync" that
    // never runs (auto-refresh is off by default). It now tells the user the
    // sync must be enabled/triggered in Settings, with a CTA to get there.
    expect(screen.getByText(/13F holdings cache not built/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open Settings/i })).toBeInTheDocument()
  })

  it('renders proxy compensation KvGrid with CEO totals', () => {
    const comp: ProxyCompensationShape = {
      filing_date: '2025-12-15',
      accession_no: '0001234567-25-000789',
      ceo_name: 'Tim Cook',
      ceo_total_compensation: 63_209_845,
      ceo_yoy_change_pct: 18.4,
      ceo_pay_ratio: 1447,
      provenance: baseProv('DEF 14A'),
    }
    const ownership: OwnershipGovernanceShape = {
      proxy_compensation: comp,
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.getByText('Tim Cook')).toBeInTheDocument()
    expect(screen.getByText('1447:1')).toBeInTheDocument()
  })

  it('does not render stale proxy payloads with title-as-name and revenue-sized comp', () => {
    const comp: ProxyCompensationShape = {
      filing_date: '2026-01-08',
      accession_no: '0001308179-26-000008',
      ceo_name: 'Chief Executive Officer',
      ceo_total_compensation: 416_200_000_000,
      provenance: baseProv('DEF 14A'),
    }
    const ownership: OwnershipGovernanceShape = {
      proxy_compensation: comp,
      generated_at: '2026-05-28T01:21:46Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.queryByText('Chief Executive Officer')).not.toBeInTheDocument()
    expect(screen.queryByText(/\$416/)).not.toBeInTheDocument()
    expect(screen.getByText(/CEO compensation unavailable/i)).toBeInTheDocument()
  })

  it('uses reason-specific message when backend supplies degraded_reasons', () => {
    // Backend emits `no_recent_filings` when SEC identity is configured but the
    // ticker simply has no Form 4 in the last 90 days (small caps, post-grant
    // quiet periods, etc). UI must NOT show "check SEC identity" — that blames
    // the user for a perfectly valid backend state.
    const ownership: OwnershipGovernanceShape = {
      insider_transactions: [],
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: ['insider_transactions'],
      degraded_reasons: { insider_transactions: 'no_recent_filings' },
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(
      screen.getByText(/no insider transactions filed in the past 90 days/i),
    ).toBeInTheDocument()
  })

  it('falls back to generic degraded message when reason is missing', () => {
    const ownership: OwnershipGovernanceShape = {
      insider_transactions: [],
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: ['insider_transactions'],
      // No degraded_reasons supplied → fallback to generic message
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.getByText(/older report has no specific reason/i)).toBeInTheDocument()
    expect(screen.queryByText(/verify SEC identity/i)).not.toBeInTheDocument()
  })

  it('renders Schedule 13D as activist with warning tone', () => {
    const alert: ScheduleThirteenAlertShape = {
      filer_name: 'Pershing Square',
      filing_date: '2026-04-30',
      accession_no: '0001234567-26-000999',
      schedule_type: '13D',
      shares: 25_000_000,
      pct_of_class: 6.8,
      transaction_summary: 'Activist position — engaging with management.',
    }
    const ownership: OwnershipGovernanceShape = {
      schedule13_alerts: [alert],
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.getByText('Pershing Square')).toBeInTheDocument()
    expect(screen.getByText('13D')).toBeInTheDocument()
    expect(screen.getByText(/Activist position/)).toBeInTheDocument()
  })
})

describe('ChapterOwnershipGovernance signal strip', () => {
  const tx = (transaction_type: string, code: string, value: number): InsiderTransactionShape => ({
    filing_date: '2026-04-01',
    accession_no: '0001234567-26-000001',
    insider_name: 'Insider',
    transaction_type,
    code,
    shares: 1000,
    value,
    provenance: baseProv('4'),
  })
  const hold = (value_usd: number, holder_name: string): InstitutionalHoldingShape => ({
    holder_name,
    cusip: '000000000',
    name_of_issuer: 'ACME',
    shares: 1,
    value_usd,
    period_end: '2026-03-31',
    provenance: baseProv('13F-HR'),
  })

  const ownership: OwnershipGovernanceShape = {
    insider_transactions: [
      tx('purchase', 'P', 5_000_000),
      tx('sale', 'S', 2_000_000),
      tx('grant', 'A', 99_000_000), // compensation — must NEVER enter the net
      tx('tax_withholding', 'F', 1_000_000), // compensation mechanics — excluded
    ],
    institutional_holdings: [
      hold(30e9, 'A'),
      hold(25e9, 'B'),
      hold(20e9, 'C'),
      hold(10e9, 'D'),
      hold(10e9, 'E'),
      hold(5e9, 'F'),
    ], // total 100e9, top-5 = 95e9 → 95%
    generated_at: '2026-05-27T09:00:00Z',
    degraded_sections: [],
  }

  it('nets only open-market P/S — grants and tax-withholding never enter the flow', () => {
    const { container } = render(
      wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />),
    )
    const strip = container.querySelector('[data-testid="ownership-signal-strip"]')
    expect(strip).not.toBeNull()
    const text = strip?.textContent ?? ''
    expect(text).toMatch(/Insider open-market flow/i)
    // net = $5M buy − $2M sell = +$3.0M; the $99M grant + $1M tax stay out of it.
    expect(text).toMatch(/net \+\$3/)
    expect(text).toMatch(/2 non-market excluded/)
    // The grant's $99M must not leak into the strip (it shows in the table below).
    expect(text).not.toMatch(/99/)
  })

  it('shows institutional top-5 concentration share', () => {
    const { container } = render(
      wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />),
    )
    const text =
      container.querySelector('[data-testid="ownership-signal-strip"]')?.textContent ?? ''
    expect(text).toMatch(/Institutional concentration/i)
    expect(text).toMatch(/95%/) // top 5 of 6 holders = 95e9 / 100e9
  })
})

describe('ChapterOwnershipGovernance partial 13F coverage', () => {
  const holder = (
    name: string,
    shares: number,
    value_usd: number,
    shares_change_pct?: number | null,
  ): InstitutionalHoldingShape => ({
    holder_name: name,
    cusip: '000000000',
    name_of_issuer: 'ACME',
    shares,
    value_usd,
    period_end: '2026-03-31',
    ...(shares_change_pct !== undefined ? { shares_change_pct } : {}),
    provenance: baseProv('13F-HR'),
  })

  it('measures concentration against the listed base and discloses partial coverage', () => {
    const ownership: OwnershipGovernanceShape = {
      // Top 5 hold 300k of the 1M listed shares → 30%. The list itself covers
      // only 40% of the issuer's institutional shares → partial.
      institutional_holdings: [
        holder('A', 100_000, 30e9),
        holder('B', 90_000, 25e9),
        holder('C', 50_000, 20e9),
        holder('D', 40_000, 10e9),
        holder('E', 20_000, 10e9),
        holder('F', 10_000, 5e9),
      ],
      institutional_shares_listed: 1_000_000,
      institutional_coverage_pct: 0.4,
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    const { container } = render(
      wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />),
    )
    const text =
      container.querySelector('[data-testid="ownership-signal-strip"]')?.textContent ?? ''
    expect(text).toMatch(/30%/) // 300k / 1M listed — the true denominator
    expect(text).toMatch(/of listed institutional shares/i)
    // Partial-coverage caveat names the true coverage.
    const caveat = container.querySelector('[data-testid="ownership-coverage-caveat"]')
    expect(caveat).not.toBeNull()
    expect(caveat?.textContent).toMatch(/40%/)
  })

  it('renders the QoQ reason instead of a bare dash when no prior quarter is cached', () => {
    const ownership: OwnershipGovernanceShape = {
      institutional_holdings: [holder('A', 100_000, 30e9), holder('B', 90_000, 25e9)],
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.getAllByText('no prior quarter cached').length).toBeGreaterThan(0)
  })

  it('keeps real QoQ figures when some holders carry them', () => {
    const ownership: OwnershipGovernanceShape = {
      institutional_holdings: [holder('A', 100_000, 30e9, 4.2), holder('B', 90_000, 25e9, null)],
      generated_at: '2026-05-27T09:00:00Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.getByText('+4.2%')).toBeInTheDocument()
    // Mixed case → the (unexplained) null keeps the honest dash, not the reason.
    expect(screen.queryByText('no prior quarter cached')).toBeNull()
  })

  it('explains a missing CEO pay figure instead of rendering a bare dash', () => {
    const ownership: OwnershipGovernanceShape = {
      proxy_compensation: {
        filing_date: '2026-01-08',
        accession_no: '0001308179-26-000008',
        ceo_name: 'Jane Doe',
        // Pay figure absent (proxy parse missed the number; name still resolved).
        ceo_total_compensation: null,
        provenance: baseProv('DEF 14A'),
      },
      generated_at: '2026-05-28T01:21:46Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.getByText('Jane Doe')).toBeInTheDocument()
    expect(screen.getByText('not extracted from proxy')).toBeInTheDocument()
  })
})

describe('ChapterOwnershipGovernance 13D/G split basis & staleness', () => {
  const alert = (overrides: Partial<ScheduleThirteenAlertShape>): ScheduleThirteenAlertShape => ({
    filer_name: 'BlackRock Inc.',
    filing_date: '2024-01-26',
    accession_no: '0001086364-24-004712',
    schedule_type: '13G',
    shares: 180_593_555,
    pct_of_class: 7.3,
    ...overrides,
  })

  it('shows the split-adjusted count alongside the as-filed count, plus a basis badge', () => {
    render(
      wrap(
        <ChapterOwnershipGovernance
          ownership={{
            schedule13_alerts: [
              alert({
                share_basis: 'pre_split',
                split_factor: 10,
                shares_adjusted: 1_805_935_550,
                filing_age_days: 991,
                stale: true,
              }),
            ],
            generated_at: '2026-10-13T23:04:06Z',
            degraded_sections: [],
          }}
          reportingCurrency="USD"
        />,
      ),
    )
    // As-filed count is still on screen (180,593,555 → "180.59M").
    expect(screen.getByText(/180\.59M/)).toBeInTheDocument()
    const adjusted = screen.getByTestId('ownership-shares-adjusted')
    expect(adjusted.textContent).toMatch(/1\.81B/)
    expect(adjusted.textContent).toMatch(/×10 split-adjusted/)
    // The exact as-filed figure stays attributable via the hover title.
    expect(adjusted.getAttribute('title')).toMatch(/180,593,555/)
    expect(screen.getByTestId('ownership-basis-badge').textContent).toBe('PRE-SPLIT ×10')
    expect(screen.getByTestId('ownership-stale-marker').textContent).toMatch(/STALE/)
    expect(screen.getByTestId('ownership-stale-marker').textContent).toMatch(/991d/)
  })

  it('renders a post-split badge but no adjusted count when no adjustment is needed', () => {
    const ownership: OwnershipGovernanceShape = {
      schedule13_alerts: [
        alert({
          filer_name: 'FMR LLC',
          shares: 998_190_803,
          pct_of_class: 4.069,
          filing_date: '2024-11-12',
          share_basis: 'post_split',
          split_factor: null,
          shares_adjusted: null,
          filing_age_days: 700,
          stale: true,
        }),
      ],
      generated_at: '2026-10-13T23:04:06Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.getByTestId('ownership-basis-badge').textContent).toBe('POST-SPLIT')
    expect(screen.queryByTestId('ownership-shares-adjusted')).toBeNull()
    expect(screen.getByTestId('ownership-stale-marker').textContent).toMatch(/700d/)
  })

  it('renders no basis badge or stale marker for a fresh, unparsed-basis filing', () => {
    const ownership: OwnershipGovernanceShape = {
      schedule13_alerts: [alert({ pct_of_class: null, share_basis: null, stale: false })],
      generated_at: '2026-10-13T23:04:06Z',
      degraded_sections: [],
    }
    render(wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />))
    expect(screen.queryByTestId('ownership-basis-badge')).toBeNull()
    expect(screen.queryByTestId('ownership-stale-marker')).toBeNull()
  })
})

describe('ChapterOwnershipGovernance partial 13F index', () => {
  it('labels the concentration as computed over a partial index when the period is incomplete', () => {
    const ownership: OwnershipGovernanceShape = {
      institutional_holdings: [
        {
          holder_name: 'A',
          cusip: '000000000',
          name_of_issuer: 'ACME',
          shares: 100_000,
          value_usd: 30e9,
          period_end: '2026-06-30',
          provenance: baseProv('13F-HR'),
        },
      ],
      institutional_shares_listed: 100_000,
      // Coverage magnitude looks full (1.0) but the period had no completion
      // marker → the index is still partial and must be labelled.
      institutional_coverage_pct: 1.0,
      institutional_index_partial: true,
      generated_at: '2026-10-13T23:04:06Z',
      degraded_sections: [],
    }
    const { container } = render(
      wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />),
    )
    const caveat = container.querySelector('[data-testid="ownership-coverage-caveat"]')
    expect(caveat).not.toBeNull()
    expect(caveat?.textContent).toMatch(/partial refresh/i)
  })

  it('does not label a complete index as partial', () => {
    const ownership: OwnershipGovernanceShape = {
      institutional_holdings: [
        {
          holder_name: 'A',
          cusip: '000000000',
          name_of_issuer: 'ACME',
          shares: 100_000,
          value_usd: 30e9,
          period_end: '2026-06-30',
          provenance: baseProv('13F-HR'),
        },
      ],
      institutional_shares_listed: 100_000,
      institutional_coverage_pct: 1.0,
      institutional_index_partial: false,
      generated_at: '2026-10-13T23:04:06Z',
      degraded_sections: [],
    }
    const { container } = render(
      wrap(<ChapterOwnershipGovernance ownership={ownership} reportingCurrency="USD" />),
    )
    expect(container.querySelector('[data-testid="ownership-coverage-caveat"]')).toBeNull()
  })
})
