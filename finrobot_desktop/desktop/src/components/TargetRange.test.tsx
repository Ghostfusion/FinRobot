// TargetRange's withheld state is reason-aware: a point withheld BECAUSE the price
// sits inside the fair-value band → "Fairly Valued" + "within range" (fairly valued, a
// confident HOLD); a point withheld out-of-band (genuine uncertainty) keeps the honest
// "Point target withheld" framing. Strict band containment mirrors the backend
// `_range_spans_market` and matches the band visual the analyst sees.

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import { TargetRange } from './TargetRange'

describe('TargetRange', () => {
  it('in-band withhold → "Fairly Valued" + within-range, never "withheld"', () => {
    // JPM-shape: price $334 sits inside the band [$263, $356] → fairly valued.
    render(
      <TargetRange
        point={null}
        low={263}
        high={356}
        currentPrice={334}
        confidence="high"
        quoteCurrency="USD"
      />,
    )
    expect(screen.getByText('Fairly Valued')).toBeInTheDocument()
    expect(screen.getByText(/Within fair-value range/i)).toBeInTheDocument()
    expect(screen.queryByText(/Point target withheld/i)).toBeNull()
  })

  it('out-of-band withhold → honest "Point target withheld" (not fairly valued)', () => {
    // TSLA-shape: price $418 sits far ABOVE the band [$11, $26] → genuine uncertainty.
    render(
      <TargetRange
        point={null}
        low={11}
        high={26}
        currentPrice={418}
        confidence="very_low"
        quoteCurrency="USD"
      />,
    )
    expect(screen.getByText(/Point target withheld/i)).toBeInTheDocument()
    expect(screen.queryByText('Fairly Valued')).toBeNull()
  })

  it('published point → shows the target number, no withheld/fair-value copy', () => {
    render(
      <TargetRange
        point={300}
        low={270}
        high={330}
        currentPrice={240}
        confidence="medium"
        quoteCurrency="USD"
        anchorMethod="dcf"
      />,
    )
    expect(screen.getByText('$300.00')).toBeInTheDocument()
    expect(screen.queryByText('Fairly Valued')).toBeNull()
    expect(screen.queryByText(/withheld/i)).toBeNull()
  })
})

describe('TargetRange price-basis legend', () => {
  const base = {
    point: 300,
    low: 270,
    high: 330,
    currentPrice: 240,
    confidence: 'medium' as const,
    quoteCurrency: 'USD',
  }

  it('defaults to "Close" (never the misleading "Live") when the quote is not live', () => {
    render(<TargetRange {...base} />)
    expect(screen.getByText(/^Close \$240\.00$/)).toBeInTheDocument()
    expect(screen.queryByText(/^Live \$240\.00/)).toBeNull()
  })

  it('renders "Live" only when quote_is_live is true', () => {
    render(<TargetRange {...base} quoteIsLive />)
    expect(screen.getByText(/^Live \$240\.00$/)).toBeInTheDocument()
    expect(screen.queryByText(/^Close /)).toBeNull()
  })

  it('stamps the as-of date on a non-live close', () => {
    render(<TargetRange {...base} quoteAsOf="2026-10-12" />)
    expect(screen.getByText(/^Close \$240\.00 · Oct 12$/)).toBeInTheDocument()
  })

  it('ignores the as-of date while live', () => {
    render(<TargetRange {...base} quoteIsLive quoteAsOf="2026-10-12" />)
    expect(screen.getByText(/^Live \$240\.00$/)).toBeInTheDocument()
    expect(screen.queryByText(/Oct 12/)).toBeNull()
  })
})
