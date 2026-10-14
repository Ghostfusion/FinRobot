import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import RevenueEbitdaChart from './RevenueEbitdaChart'

const SAMPLE_DATA = [
  { year: 2022, revenue: 50_000_000_000, ebitda: 15_000_000_000, is_forecast: false },
  { year: 2023, revenue: 55_000_000_000, ebitda: 17_000_000_000, is_forecast: false },
  { year: 2024, revenue: 60_000_000_000, ebitda: 19_000_000_000, is_forecast: true },
]

describe('RevenueEbitdaChart', () => {
  it('renders title', () => {
    render(<RevenueEbitdaChart data={SAMPLE_DATA} title="Revenue & EBITDA" />)
    expect(screen.getByText('Revenue & EBITDA')).toBeInTheDocument()
  })

  it('returns null for empty data', () => {
    const { container } = render(<RevenueEbitdaChart data={[]} title="Empty" />)
    expect(container.firstChild).toBeNull()
  })

  it('returns null for undefined data', () => {
    const { container } = render(
      <RevenueEbitdaChart
        data={undefined as unknown as Record<string, number | string | boolean | null>[]}
        title="Null"
      />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders container with correct styling', () => {
    render(<RevenueEbitdaChart data={SAMPLE_DATA} title="Revenue & EBITDA" />)
    const heading = screen.getByText('Revenue & EBITDA')
    expect(heading.tagName).toBe('SPAN')
  })

  // The x-axis must label EVERY year, including the wide DCF forecast-basis labels
  // ("TTM (Jul 2026)" / "2027E (TTM+1)") that made Recharts' default auto-interval
  // hide their neighbours. Pinned by `interval={0}` on the XAxis, but NOT assertable
  // here: jsdom gives the ResponsiveContainer no layout, so Recharts renders no ticks
  // (verified 0 tick nodes, with and without a ResizeObserver / getBoundingClientRect
  // stub). Verified in the live DOM of the audited report instead.
})
