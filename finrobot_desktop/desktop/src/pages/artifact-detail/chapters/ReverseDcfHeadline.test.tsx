// The reverse-DCF headline's reframing sentence must name the premium's DRIVER,
// not just its size. A price above the model's central cash-flow value has two
// possible sources — the model's growth path is too pessimistic, or its discount
// rate is too high — and the panel already prints the market's own implied growth
// beside the sentence, so claiming a growth bet while that number is NEGATIVE
// contradicts the panel itself (CF 2026-10-14: "the market is pricing in
// ~-9.8%/yr" beside "that premium is a bet on the implied growth", while the
// thesis attributed the gap to the 4.83%-vs-6.01% discount rate).

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ReverseDcfHeadline } from './ReverseDcfHeadline'
import type { DcfShape, ValuationMethodShape } from './types'

function marketImplied(over: Partial<NonNullable<DcfShape['market_implied']>>) {
  return {
    horizon_years: 10,
    implied_growth: 0.2,
    growth_unreachable: false,
    implied_wacc: 0.0483,
    growth_ceiling: null,
    ceiling_price: null,
    ...over,
  } as NonNullable<DcfShape['market_implied']>
}

/** CF's own numbers: DCF mid 75.85 against a 119.46 quote ⇒ 1.6× the central value. */
const CF_DCF_METHOD = {
  name: 'dcf',
  low: 60.67971643556535,
  mid: 75.84964554445669,
  high: 91.01957465334803,
  confidence: 0.85,
} as ValuationMethodShape

function renderHeadline(implied: NonNullable<DcfShape['market_implied']>): void {
  render(
    <ReverseDcfHeadline
      marketImplied={implied}
      dcfMethod={CF_DCF_METHOD}
      currentPrice={119.46}
      quoteCurrency="USD"
    />,
  )
}

describe('ReverseDcfHeadline — the premium sentence names its driver', () => {
  it('reads a NEGATIVE implied growth as a discount-rate bet, never a growth bet', () => {
    renderHeadline(marketImplied({ implied_growth: -0.0975830078125 }))

    expect(screen.getByText('Priced on the discount rate')).toBeInTheDocument()
    const sentence = screen.getByText(/the price is 1\.6× the model's central cash-flow value/)
    expect(sentence).toHaveTextContent('discount rate, not on growth')
    expect(sentence).toHaveTextContent('-9.8%/yr')
    // The claim the artifact contradicted must be gone.
    expect(screen.queryByText(/bet on the implied growth/)).toBeNull()
  })

  it('keeps the growth reading when the implied growth is positive', () => {
    renderHeadline(marketImplied({ implied_growth: 0.2 }))

    expect(screen.getByText('Priced for growth')).toBeInTheDocument()
    expect(screen.getByText(/a bet on the implied growth, not a value entry/)).toBeInTheDocument()
  })

  it('still reads a discount as below cash-flow value', () => {
    render(
      <ReverseDcfHeadline
        marketImplied={marketImplied({ implied_growth: 0.02 })}
        dcfMethod={{ ...CF_DCF_METHOD, mid: 200, low: 180, high: 220 } as ValuationMethodShape}
        currentPrice={119.46}
        quoteCurrency="USD"
      />,
    )

    expect(screen.getByText('Below cash-flow value')).toBeInTheDocument()
  })
})
