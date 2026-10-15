// The β telemetry tile's caliber note must name the β>1 threshold, and when the
// artifact DECLARES the DCF/WACC β's basis (`beta_basis`) the note
// states that fact instead of the conditional rule. CF 2026-10-14: the tile said
// "DCF uses a Blume-adjusted β" with no threshold, so a reader applied Blume to a
// β of 0.53 (→ 0.69) while the WACC had actually used the raw 0.527 (β≤1 is
// deliberately unadjusted). Legacy artifacts carry no `beta_basis` → the note must
// keep its exact previous wording (the reader must not be told a caliber the
// artifact never declared).

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import { CompanySnapshot, type SnapshotMetric } from './CompanySnapshot'

function betaMetric(over: Partial<SnapshotMetric> = {}): SnapshotMetric {
  return { kind: 'beta', label: 'Beta', value: '0.53', raw: 0.53, ...over }
}

function renderSnapshot(metrics: SnapshotMetric[]): void {
  render(
    <CompanySnapshot
      identity={{}}
      metrics={metrics}
      quoteCurrency="USD"
      fetchedAt={null}
      labels={{ sector: 'Sector', industry: 'Industry', country: 'Country' }}
    />,
  )
}

describe('CompanySnapshot — the β tile names the declared basis', () => {
  it('states the DECLARED raw basis (no Blume adjustment applied)', () => {
    renderSnapshot([betaMetric({ basis: 'raw' })])

    expect(screen.getByText(/this same raw 5Y value/)).toBeInTheDocument()
    expect(screen.queryByText(/applies only when β>1/)).toBeNull()
  })

  it('states the DECLARED Blume basis (the β>1 adjustment was applied)', () => {
    renderSnapshot([betaMetric({ basis: 'blume' })])

    const note = screen.getByText(/DCF\/WACC β is Blume-adjusted/)
    expect(note).toBeInTheDocument()
    // The threshold is still named, so a reader cannot apply Blume to β≤1.
    expect(note).toHaveTextContent('β>1')
  })

  it('falls back to the conditional β>1 rule when no basis is declared (legacy)', () => {
    renderSnapshot([betaMetric()])

    const note = screen.getByText(/the DCF's Blume-adjusted β applies only when/)
    expect(note).toHaveTextContent('β>1 (β≤1 is used as-is)')
  })

  it('keeps the chip β-scoped (LOW/HIGH β vs MARKET), never a volatility claim', () => {
    renderSnapshot([betaMetric({ basis: 'raw', raw: 0.53 })])
    expect(screen.getByText('LOW β vs MARKET')).toBeInTheDocument()

    renderSnapshot([betaMetric({ basis: 'blume', raw: 1.9 })])
    expect(screen.getByText('HIGH β vs MARKET')).toBeInTheDocument()
  })
})
