import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SensitivityHeatmap from './SensitivityHeatmap'

const SAMPLE_DATA = [
  { wacc: 0.08, tg: 0.02, implied_price: 150 },
  { wacc: 0.08, tg: 0.025, implied_price: 170 },
  { wacc: 0.09, tg: 0.02, implied_price: 130 },
  { wacc: 0.09, tg: 0.025, implied_price: 145 },
  { wacc: 0.1, tg: 0.02, implied_price: 110 },
  { wacc: 0.1, tg: 0.025, implied_price: 125 },
]

describe('SensitivityHeatmap', () => {
  it('renders title', () => {
    render(<SensitivityHeatmap data={SAMPLE_DATA} title="Sensitivity Analysis" />)
    expect(screen.getByText('Sensitivity Analysis')).toBeInTheDocument()
  })

  it('returns null for empty data', () => {
    const { container } = render(<SensitivityHeatmap data={[]} title="Empty" />)
    expect(container.firstChild).toBeNull()
  })

  it('returns null for undefined data', () => {
    const { container } = render(
      <SensitivityHeatmap
        data={undefined as unknown as Record<string, number | string | boolean | null>[]}
        title="Null"
      />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders a table with correct structure', () => {
    render(<SensitivityHeatmap data={SAMPLE_DATA} title="Sensitivity" />)
    const table = screen.getByRole('table')
    expect(table).toBeInTheDocument()
  })

  it('renders WACC row labels as percentages to two decimals', () => {
    // Two decimals on purpose: the base WACC 6.97% used to render as "7.0%",
    // reading as if the cell were computed at a round 7% (owner review).
    render(<SensitivityHeatmap data={SAMPLE_DATA} title="Sensitivity" />)
    expect(screen.getByText('8.00%')).toBeInTheDocument()
    expect(screen.getByText('9.00%')).toBeInTheDocument()
    expect(screen.getByText('10.00%')).toBeInTheDocument()
  })

  it('marks the exact base-case cell when the DCF supplies its base assumptions', () => {
    // Non-round base values in the grid: only the matching (WACC, TGR) cell is
    // marked — the reader can see the headline cell without guessing.
    const data = [
      { wacc: 0.06971583960763642, tg: 0.025, implied_price: 226 },
      { wacc: 0.06971583960763642, tg: 0.03, implied_price: 240 },
      { wacc: 0.08, tg: 0.025, implied_price: 180 },
      { wacc: 0.08, tg: 0.03, implied_price: 190 },
    ]
    const { container } = render(
      <SensitivityHeatmap
        data={data}
        title="Sensitivity"
        baseWacc={0.06971583960763642}
        baseTg={0.025}
      />,
    )
    const marked = container.querySelectorAll('td[data-base="true"]')
    expect(marked).toHaveLength(1)
    expect(marked[0].textContent).toContain('$226.00')
    // Axis label carries the true base WACC, not a rounded "7.0%".
    expect(screen.getByText('6.97%')).toBeInTheDocument()
  })

  it('falls back to the grid-centre marking when no base assumptions are supplied', () => {
    const { container } = render(<SensitivityHeatmap data={SAMPLE_DATA} title="Sensitivity" />)
    expect(container.querySelectorAll('td[data-base="true"]')).toHaveLength(0)
    expect(container.querySelectorAll('td.current')).toHaveLength(1)
  })

  it('renders implied prices in cells to the cent (a price is exact — never rounded to whole dollars)', () => {
    render(<SensitivityHeatmap data={SAMPLE_DATA} title="Sensitivity" />)
    expect(screen.getByText('$150.00')).toBeInTheDocument()
    expect(screen.getByText('$110.00')).toBeInTheDocument()
  })

  // W3 — color-scale legend. The green end MUST read "higher implied value" and
  // the red end "lower implied value" (heatmapClass maps higher normalised price
  // → hm-5 = --legacy-green-30). The ramp runs red→green left-to-right so the
  // text labels frame it: "Lower implied value" [red…green] "Higher implied value".
  it('renders a color-scale legend with the correct (green = higher value) direction', () => {
    render(<SensitivityHeatmap data={SAMPLE_DATA} title="Sensitivity" />)
    const legend = screen.getByTestId('heatmap-legend')
    expect(legend).toBeInTheDocument()
    // EN catalog strings (app renders en by default in tests).
    expect(screen.getByText('Lower implied value')).toBeInTheDocument()
    expect(screen.getByText('Higher implied value')).toBeInTheDocument()
  })

  it('paints the legend ramp red→green (lowest value on the left, highest on the right)', () => {
    render(<SensitivityHeatmap data={SAMPLE_DATA} title="Sensitivity" />)
    const swatches = [...screen.getByTestId('heatmap-legend').querySelectorAll('span > span')].map(
      (s) => (s as HTMLElement).style.background,
    )
    expect(swatches[0]).toBe('var(--legacy-red-25)') // leftmost = lowest implied value
    expect(swatches[swatches.length - 1]).toBe('var(--legacy-green-30)') // rightmost = highest
  })
})
