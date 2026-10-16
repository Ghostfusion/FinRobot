// Guards the metric-authority decision record surface (`raw_data.data_authority`).
//
// The panel exists so a PUBLISHED conflict is legible: which value is canonical,
// which vendor is the producer of record, and what else was on the table with its
// deviation. Two properties are load-bearing and pinned here:
//   • the record renders NOTHING when the block is absent / malformed (every
//     artifact written before the field existed) — never an empty shell;
//   • a non-accepted decision renders its ALTERNATIVES with their deviation (the
//     whole point of publishing a conflict instead of averaging it away).
// Every field is read defensively: the payload is an untyped dict, so a dropped /
// null / wrong-typed field must degrade, never throw.

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import { DataAuthorityPanel, parseDataAuthority } from './DataAuthorityPanel'

// The canonical conflict: FMP is the producer of record at 1.0B; yfinance
// disagrees by 18% (over the 15% tolerance); edgar_tools reads a different
// period, so it was never compared numerically.
const CONFLICT: Record<string, unknown> = {
  policy_version: 'metric_authority_v1',
  run_as_of: null,
  clock: '2026-10-13T00:00:00+00:00',
  decisions: [
    {
      metric: 'revenue',
      status: 'conflict',
      value: 1_000_000_000,
      unit: 'USD',
      currency: 'USD',
      selected_source: 'fmp',
      is_authoritative: true,
      reason_code: 'above_tolerance_published_flagged',
      policy_version: 'metric_authority_v1',
      definition_version: 'revenue_1',
      basis: 'TTM as-reported revenue, FMP caliber',
      comparability: 'as_reported_period',
      tolerance_pct: 0.15,
      tolerance_abs: null,
      period_end: '2026-06-30',
      period_basis: 'ttm',
      disagreement_pct: 0.18,
      agreement_is_independent: true,
      candidates: [
        {
          source: 'fmp',
          value: 1_000_000_000,
          eligible: true,
          deviation_pct: null,
          deviation_abs: null,
          reason_code: 'authoritative_selected',
          non_independent: false,
        },
        {
          source: 'yfinance',
          value: 1_180_000_000,
          eligible: true,
          deviation_pct: 0.18,
          deviation_abs: 180_000_000,
          reason_code: 'above_tolerance_published_flagged',
          non_independent: false,
        },
        {
          source: 'edgar_tools',
          value: null,
          eligible: false,
          deviation_pct: null,
          deviation_abs: null,
          reason_code: 'definition_mismatch_period',
          non_independent: false,
        },
      ],
      reconciled_at: '2026-10-13T00:00:00+00:00',
    },
    {
      metric: 'net_income',
      status: 'accepted',
      value: 250_000_000,
      unit: 'USD',
      currency: 'USD',
      selected_source: 'fmp',
      is_authoritative: true,
      reason_code: 'authoritative_selected',
      basis: 'TTM as-reported net income, FMP caliber',
      disagreement_pct: null,
      candidates: [],
    },
  ],
}

describe('DataAuthorityPanel', () => {
  // ── Absence / malformed payload → zero footprint ──────────────────────────

  it.each<[string, unknown]>([
    ['undefined', undefined],
    ['null', null],
    ['an empty object', {}],
    ['no decisions', { policy_version: 'metric_authority_v1', decisions: [] }],
    ['a non-object', 'metric_authority_v1'],
    ['a decisions value that is not an array', { decisions: 'nope' }],
    ['decision entries with no metric', { decisions: [{ status: 'conflict' }, null, 7] }],
  ])('renders nothing when data_authority is %s', (_label, authority) => {
    const { container } = render(<DataAuthorityPanel authority={authority} />)
    expect(container.firstChild).toBeNull()
    expect(screen.queryByTestId('report-data-authority')).toBeNull()
  })

  it('parseDataAuthority returns null for every absent/malformed shape', () => {
    expect(parseDataAuthority(undefined)).toBeNull()
    expect(parseDataAuthority(null)).toBeNull()
    expect(parseDataAuthority({})).toBeNull()
    expect(parseDataAuthority({ decisions: [] })).toBeNull()
    expect(parseDataAuthority({ decisions: [{ status: 'conflict' }] })).toBeNull()
  })

  // ── The conflict record ───────────────────────────────────────────────────

  it('renders the non-accepted decision with its alternatives and their deviation', () => {
    render(<DataAuthorityPanel authority={CONFLICT} />)

    const panel = screen.getByTestId('report-data-authority')
    expect(panel).toBeInTheDocument()

    // Metric · value · selected source · status.
    expect(screen.getByText('Revenue')).toBeTruthy()
    expect(screen.getByText(/1,000,000,000/)).toBeTruthy()
    expect(screen.getByText(/Selected source: fmp/)).toBeTruthy()
    expect(screen.getByText('Conflict')).toBeTruthy()

    // Alternatives: the disagreeing vendor WITH its deviation (the reason the
    // record exists — dropping either would hide the conflict).
    const alternatives = screen.getAllByTestId('report-data-authority-alternative')
    expect(alternatives).toHaveLength(2)
    expect(screen.getByText('yfinance')).toBeTruthy()
    expect(screen.getByText('18.0%')).toBeTruthy()
    // The ineligible read is still published, marked "not compared" (no deviation).
    expect(screen.getByText('edgar_tools')).toBeTruthy()
    expect(screen.getByText('not compared')).toBeTruthy()
    expect(screen.getAllByText('not compared')).toHaveLength(1)
    // The ineligible candidate's reason replaces nothing — it is shown verbatim.
    expect(screen.getByText('different period')).toBeTruthy()

    // The basis of the row is carried through (period + caliber).
    expect(screen.getByText(/TTM as-reported revenue, FMP caliber/)).toBeTruthy()

    // Reference material: the record states the canonical value stands.
    expect(screen.getByText(/never averaged/)).toBeTruthy()
  })

  it('summarises accepted decisions with a count instead of a row', () => {
    render(<DataAuthorityPanel authority={CONFLICT} />)
    // net_income is accepted → counted, never itemised.
    expect(screen.queryByText('Net Income')).toBeNull()
    expect(screen.getAllByTestId('report-data-authority-decision')).toHaveLength(1)
    expect(screen.getByTestId('report-data-authority-accepted').textContent).toContain('1')
  })

  it('renders only the count line when every decision was accepted', () => {
    render(
      <DataAuthorityPanel
        authority={{
          policy_version: 'metric_authority_v1',
          decisions: [{ metric: 'revenue', status: 'accepted', value: 1, unit: 'USD' }],
        }}
      />,
    )
    expect(screen.queryAllByTestId('report-data-authority-decision')).toHaveLength(0)
    expect(screen.getByTestId('report-data-authority-accepted').textContent).toContain('1')
  })

  it('marks a fallback decision with its named fallback source', () => {
    render(
      <DataAuthorityPanel
        authority={{
          decisions: [
            {
              metric: 'current_price',
              status: 'fallback',
              value: 81.29,
              unit: 'USD',
              currency: 'USD',
              selected_source: 'yfinance',
              reason_code: 'canonical_value_invalid_fallback_selected',
              candidates: [
                { source: 'fmp', value: -1, eligible: false, reason_code: 'non_positive_value' },
                { source: 'yfinance', value: 81.29, eligible: true, reason_code: 'sources_agree' },
              ],
            },
          ],
        }}
      />,
    )
    expect(screen.getByText('Current Price')).toBeTruthy()
    expect(screen.getByText('Fallback')).toBeTruthy()
    expect(screen.getByText(/Selected source: yfinance/)).toBeTruthy()
    // The rejected owner read is listed with its own reason, no deviation.
    expect(screen.getByText('fmp')).toBeTruthy()
    expect(screen.getByText('non-positive value')).toBeTruthy()
  })

  it('tolerates wrong-typed fields without crashing', () => {
    const { container } = render(
      <DataAuthorityPanel
        authority={{
          policy_version: 123,
          decisions: [
            {
              metric: 'gross_margin',
              status: 7,
              value: 'nope',
              unit: null,
              currency: { bad: true },
              selected_source: 5,
              reason_code: null,
              basis: ['not', 'a', 'string'],
              candidates: 'not-an-array',
            },
          ],
        }}
      />,
    )
    expect(container.textContent).toContain('Gross Margin')
    // value non-finite → the honest placeholder, never "NaN".
    expect(container.textContent).toContain('—')
    expect(container.textContent).not.toContain('NaN')
  })

  // ── Coverage counts + the PRICE record (change 7) ─────────────────────────
  // The audited run carried NO financials record (`data_authority` null). The panel
  // must say so explicitly with the coverage counts — a bare "· 0" read as "zero
  // conflicts" — and render the PRICE canonical's own record separately.

  it('states the missing financials record explicitly with the coverage counts', () => {
    render(
      <DataAuthorityPanel
        authority={null}
        coverage={{ metrics_decided: 0, metrics_without_record: 4, divergence_warnings: 1 }}
      />,
    )
    expect(screen.getByTestId('report-data-authority-no-record').textContent).toMatch(
      /NOT the same as zero conflicts/,
    )
    const coverage = screen.getByTestId('report-data-authority-coverage').textContent
    expect(coverage).toContain('4')
    expect(coverage).toContain('1')
    // The header no longer reads a bare "0".
    expect(screen.getByTestId('report-data-authority-details')).toHaveTextContent(
      'no financial-metrics record',
    )
  })

  it('renders the PRICE decision record separately, labelled as the price record', () => {
    render(
      <DataAuthorityPanel
        authority={null}
        priceAuthority={{
          policy_version: 'metric_authority_v1',
          decisions: [
            {
              metric: 'current_price',
              status: 'accepted',
              value: 228.52,
              unit: 'USD',
              currency: 'USD',
              selected_source: 'eodhd',
              is_authoritative: true,
              reason_code: 'sources_agree',
              candidates: [],
            },
          ],
        }}
      />,
    )
    expect(screen.getByTestId('report-data-authority-price')).toHaveTextContent(
      'Price decision record',
    )
    // The authoritative current price is reader-visible through its accepted count…
    expect(screen.getByTestId('report-data-authority-price-accepted').textContent).toContain('1')
    // …and it is NOT folded into the financials record (which is absent here).
    expect(screen.queryByTestId('report-data-authority-accepted')).toBeNull()
    expect(screen.getByTestId('report-data-authority-no-record')).toBeInTheDocument()
  })

  // ── Provenance degradation markers (the PRICE feed's quote codes) ─────────
  // The audited NVDA artifact's price feed carried `quote_ts_missing` +
  // `quote_currency_inferred` in `raw_data.provenance.degraded` — markers that
  // qualify the published price. The panel used to read only the COUNTS of that
  // same block, so both flags reached no report surface (the 2026-10-16 review:
  // "the report does not surface them").

  it('surfaces the provenance degraded markers as labels, never the raw code', () => {
    render(
      <DataAuthorityPanel
        authority={null}
        coverage={{ degraded: ['quote_ts_missing', 'quote_currency_inferred'] }}
      />,
    )
    const row = screen.getByTestId('report-data-authority-degraded')
    expect(row).toHaveTextContent('Quote timestamp missing')
    expect(row).toHaveTextContent('Quote currency inferred')
    expect(row.textContent ?? '').not.toContain('quote_ts_missing')
    expect(row.textContent ?? '').not.toContain('quote_currency_inferred')
  })

  it('renders nothing when the provenance block carries no markers and no counts', () => {
    const { container } = render(
      <DataAuthorityPanel authority={null} coverage={{ degraded: [] }} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when neither a record nor a coverage count is present', () => {
    const { container } = render(<DataAuthorityPanel authority={null} priceAuthority={null} />)
    expect(container.firstChild).toBeNull()
  })
})
