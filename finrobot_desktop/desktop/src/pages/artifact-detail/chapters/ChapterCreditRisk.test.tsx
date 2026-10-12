// Chapter 11 — Credit & Default Risk. Locks the contract that makes this chapter
// trustworthy rather than decorative:
//   • a computed reading reaches the page with its numbers (DD, PD, leverage,
//     implied spread) AND the barrier-basis caveat, which is a fact about the
//     numbers rather than a footnote;
//   • the four states render as four different things — a debt-free balance sheet
//     is not 'not computable', and a bank is not either;
//   • NO ZERO is ever rendered in place of an absent number (the failure mode that
//     would read as "no default risk"), and a cell is pushed only when its field
//     is present;
//   • the section is addressable as `#credit` so a deep link resolves.
//
// Numbers are the live MSFT/KO readings from the pipeline step, so the formatting
// assertions (the <0.01% / ≈0 bp floors) match what a real artifact produces.

import { describe, it, expect } from 'vitest'
import { render, screen, type RenderResult } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { ChapterCreditRisk } from './ChapterCreditRisk'
import type { CreditRiskShape } from './types'

const BARRIER_CAVEAT =
  'debt barrier = total debt: the KMV convention (short-term debt + ½·long-term ' +
  'debt) needs a provider that splits the balance sheet, so this distance to ' +
  'default is conservative — the barrier sits at least as high as KMV’s'

const COMPUTED: CreditRiskShape = {
  state: 'computed',
  method: 'merton_kmv',
  horizon_years: 1,
  equity_value: 4_100_000_000_000,
  debt_barrier: 131_000_000_000,
  barrier_basis: 'total_debt',
  asset_value: 4_131_290_422_455.171,
  asset_volatility: 0.31843559060275395,
  equity_volatility: 0.3282389185846557,
  volatility_bars: 251,
  risk_free_rate: 0.043,
  distance_to_default: 10.866622089230477,
  default_probability: 8.312114224863827e-28,
  debt_to_value: 0.03113784732957519,
  implied_credit_spread: 4.163336342344337e-17,
  iterations: 2,
  converged: true,
  warnings: [BARRIER_CAVEAT],
}

function renderChapter(credit: CreditRiskShape | null): RenderResult {
  return render(
    <MemoryRouter>
      <ChapterCreditRisk credit={credit} />
    </MemoryRouter>,
  )
}

describe('ChapterCreditRisk — computed', () => {
  it('renders the reading, addressable as #credit', () => {
    const { container } = renderChapter(COMPUTED)

    expect(container.querySelector('section#credit')).toBeTruthy()
    expect(screen.getByText('Credit Readout')).toBeTruthy()
    expect(screen.getByText('Distance to Default')).toBeTruthy()
    expect(screen.getByText('10.87')).toBeTruthy()
    expect(screen.getByText('3.1%')).toBeTruthy() // market leverage
    expect(screen.getByText('32.8%')).toBeTruthy() // equity volatility
    expect(screen.getByText('TRAILING 251 BARS')).toBeTruthy()
  })

  it('floors a vanishing probability and spread instead of printing noise', () => {
    renderChapter(COMPUTED)

    // 8.31e-28 and 4.16e-17 are numerically zero. Printing them would claim a
    // precision the model does not have.
    expect(screen.getByText('<0.01%')).toBeTruthy()
    expect(screen.getByText('≈0 bp')).toBeTruthy()
  })

  it('never renders a zero in place of a number', () => {
    renderChapter(COMPUTED)

    expect(screen.queryByText('0.00')).toBeNull()
  })

  it('carries the barrier-basis caveat and the standing assumptions', () => {
    renderChapter(COMPUTED)

    expect(screen.getByTestId('credit-warnings').textContent).toContain('debt barrier = total debt')
    expect(screen.getByText(/KMV’s convention is short-term debt/)).toBeTruthy()
    expect(screen.getByText(/lognormal asset value/)).toBeTruthy()
  })

  it('omits a cell whose field is absent rather than filling it', () => {
    const { implied_credit_spread: _drop, ...rest } = COMPUTED
    void _drop
    renderChapter(rest as CreditRiskShape)

    expect(screen.getByText('10.87')).toBeTruthy() // the reading still renders
    expect(screen.queryByText('≈0 bp')).toBeNull()
    expect(screen.queryByText(/bp$/)).toBeNull()
  })

  it('states a non-converged fixed point instead of hiding it', () => {
    renderChapter({ ...COMPUTED, converged: false, iterations: 100 })

    expect(screen.getByText('NOT CONVERGED — SEE LIMITS')).toBeTruthy()
    expect(screen.getByText(/did not converge/)).toBeTruthy()
  })
})

describe('ChapterCreditRisk — the three non-computed states', () => {
  it('reads a debt-free balance sheet as its own state, not as missing data', () => {
    const { container } = renderChapter({
      state: 'no_debt',
      horizon_years: 1,
      equity_value: 500_000_000,
      debt_barrier: 0,
      barrier_basis: 'total_debt',
      warnings: ['no debt on the balance sheet: the structural model has no barrier to breach'],
    })

    expect(container.querySelector('[data-testid="credit-no-debt"]')).toBeTruthy()
    expect(screen.getByText(/No debt on the balance sheet/)).toBeTruthy()
    expect(screen.getByText(/undefined for this issuer by construction/)).toBeTruthy()
    // No barrier to breach is NOT a zero distance to default.
    expect(screen.queryByText('Distance to Default')).toBeNull()
    expect(screen.queryByText('0.00')).toBeNull()
  })

  it('reports a balance-sheet financial as not applicable, with the reason', () => {
    renderChapter({
      state: 'not_applicable',
      horizon_years: 1,
      warnings: ['structural credit risk not applicable: this is a balance-sheet financial'],
    })

    expect(screen.getByTestId('credit-not_applicable')).toBeTruthy()
    expect(screen.getByText(/deposits and float are operating raw material/)).toBeTruthy()
    // A category error is not a re-run problem, so no settings CTA is offered.
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('reports a missing input verbatim, with a way to fix it', () => {
    const reason =
      'structural credit risk not computed: the provider reports no total debt for this issuer (None ≠ $0)'
    renderChapter({ state: 'not_computable', horizon_years: 1, warnings: [reason] })

    expect(screen.getByTestId('credit-not_computable')).toBeTruthy()
    expect(screen.getByText(reason)).toBeTruthy()
    expect(screen.getByRole('link')).toBeTruthy()
  })

  it('says so when the artifact predates the step (null payload)', () => {
    renderChapter(null)

    expect(screen.getByTestId('credit-absent')).toBeTruthy()
    expect(screen.getByText(/predates the credit-risk step/)).toBeTruthy()
    expect(screen.queryByText('Distance to Default')).toBeNull()
  })
})
