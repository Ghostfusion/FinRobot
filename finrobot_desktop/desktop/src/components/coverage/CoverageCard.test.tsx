/**
 * CoverageCard — the reverse-DCF "expectations" line.
 *
 * Verifies the three market_implied states render with the right copy + tone,
 * and that the line is omitted when there's nothing honest to say (no DCF, a
 * fundamental with no solved growth, or a cold row still shimmering).
 */

import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { CoverageCard } from './CoverageCard'
import type { CoverageRow, MarketImpliedNature } from '../../api/coverage'

function row(over: Partial<CoverageRow>): CoverageRow {
  return {
    ticker: 'AAA',
    owned: false,
    company: null,
    price: 200,
    change_pct_1d: null,
    price_as_of: null,
    session_state: null,
    market_cap: null,
    revenue_ttm: null,
    ev_ebitda: null,
    pe: null,
    currency: 'USD',
    latest_verdict: null,
    target_price: null,
    target_date: null,
    entry_price: null,
    upside_to_target_live: null,
    signal: null,
    artifact_count: 0,
    research_count: 0,
    latest_artifact_id: null,
    latest_type: null,
    latest_at: null,
    run_status: null,
    run_error: null,
    market_implied: null,
    market_stale: false,
    needs_refresh: [],
    warnings: [],
    sources: {
      price: null,
      change_pct_1d: null,
      market_cap: null,
      revenue_ttm: null,
      ev_ebitda: null,
      pe: null,
      upside_to_target_live: null,
      market_implied: null,
    },
    ...over,
  }
}

function renderCard(over: Partial<CoverageRow>, marketPending = false): void {
  render(
    <MemoryRouter>
      <CoverageCard
        row={row(over)}
        density="comfort"
        marketPending={marketPending}
        onOpen={vi.fn()}
      />
    </MemoryRouter>,
  )
}

const nat = (over: Partial<MarketImpliedNature>): MarketImpliedNature => ({
  kind: 'fundamental',
  implied_growth: null,
  implied_wacc: null,
  horizon_years: 5,
  growth_ceiling: null,
  ceiling_price: null,
  ...over,
})

describe('CoverageCard market-implied line', () => {
  it('renders option_value in danger tone with the ceiling in the tooltip', () => {
    renderCard({
      market_implied: nat({ kind: 'option_value', growth_ceiling: 0.5, ceiling_price: 90 }),
    })
    const el = screen.getByText(/Option-value/)
    expect(el).toBeInTheDocument()
    expect(el.style.color).toBe('var(--danger)')
  })

  it('renders near_ceiling in warning tone', () => {
    renderCard({ market_implied: nat({ kind: 'near_ceiling' }) })
    const el = screen.getByText(/Near-ceiling/)
    expect(el).toBeInTheDocument()
    expect(el.style.color).toBe('var(--warning)')
  })

  it('renders fundamental with the implied growth as neutral context', () => {
    renderCard({ market_implied: nat({ kind: 'fundamental', implied_growth: 0.28 }) })
    const el = screen.getByText(/priced in/)
    expect(el.textContent).toMatch(/28\.0%/)
    expect(el.style.color).toBe('var(--text-secondary)')
  })

  it('omits the line for fundamental with no solved growth (never "—")', () => {
    renderCard({ market_implied: nat({ kind: 'fundamental', implied_growth: null }) })
    expect(screen.queryByText('Mkt implied')).not.toBeInTheDocument()
  })

  it('omits the line when there is no DCF (market_implied null)', () => {
    renderCard({ market_implied: null })
    expect(screen.queryByText('Mkt implied')).not.toBeInTheDocument()
  })

  it('omits the line while a cold row is still shimmering', () => {
    renderCard(
      {
        price: null,
        market_implied: nat({ kind: 'option_value', growth_ceiling: 0.5, ceiling_price: 90 }),
      },
      true,
    )
    expect(screen.queryByText(/Option-value/)).not.toBeInTheDocument()
  })
})

describe('CoverageCard price-target gauge', () => {
  function renderC(over: Partial<CoverageRow>, marketPending = false): HTMLElement {
    const { container } = render(
      <MemoryRouter>
        <CoverageCard
          row={row(over)}
          density="comfort"
          marketPending={marketPending}
          onOpen={vi.fn()}
        />
      </MemoryRouter>,
    )
    return container.querySelector('.target-gauge') as HTMLElement
  }

  it('renders the target value + a green marker when the target is ABOVE price', () => {
    const el = renderC({ price: 399.76, target_price: 558.78, upside_to_target_live: 0.3978 })
    expect(el).not.toBeNull()
    expect(el.textContent).toContain('558.78')
    const value = el.querySelector('.target-gauge__value') as HTMLElement
    expect(value.style.color).toBe('var(--success)')
    const mark = el.querySelector('.target-gauge__mark') as HTMLElement
    // Above price → marker sits right of the centre tick (>50%).
    expect(parseFloat(mark.style.left)).toBeGreaterThan(50)
  })

  it('renders a red marker LEFT of centre when the target is BELOW price', () => {
    const el = renderC({ price: 296.42, target_price: 195.04, upside_to_target_live: -0.342 })
    expect(el.textContent).toContain('195.04')
    const value = el.querySelector('.target-gauge__value') as HTMLElement
    expect(value.style.color).toBe('var(--danger)')
    const mark = el.querySelector('.target-gauge__mark') as HTMLElement
    expect(parseFloat(mark.style.left)).toBeLessThan(50)
  })

  it('omits the gauge when there is no stored target (degrade, never a broken bar)', () => {
    const el = renderC({ price: 411.15, target_price: null })
    expect(el).toBeNull()
  })

  it('omits the gauge when there is no live price', () => {
    const el = renderC({ price: null, target_price: 195.04 }, true)
    expect(el).toBeNull()
  })
})

describe('CoverageCard freshness / session affordance', () => {
  function renderC(over: Partial<CoverageRow>, marketPending = false): HTMLElement {
    const { container } = render(
      <MemoryRouter>
        <CoverageCard
          row={row(over)}
          density="comfort"
          marketPending={marketPending}
          onOpen={vi.fn()}
        />
      </MemoryRouter>,
    )
    return container.querySelector('.coverage-card__provider') as HTMLElement
  }

  it('a CLOSED market shows a static "Close · date", never the refreshing pulse', () => {
    const el = renderC(
      { session_state: 'closed', price_as_of: '2026-06-05T20:00:00Z' },
      true, // revalidate in flight — must NOT pulse over a settled close
    )
    expect(el.textContent).toContain('Close · 2026-06-05')
    expect(el.textContent).not.toContain('refreshing')
    expect(el.getAttribute('data-session')).toBe('closed')
    expect(el.getAttribute('data-refreshing')).toBeNull()
  })

  it('a LIVE market revalidating shows the refreshing affordance', () => {
    const el = renderC({ session_state: 'live', price_as_of: '2026-06-08T15:00:00Z' }, true)
    expect(el.getAttribute('data-refreshing')).toBe('true')
    expect(el.textContent).toContain('refreshing')
    expect(el.getAttribute('data-session')).toBeNull()
  })

  it('a CLOSED market labels the 1D change with the session date, not "1D"', () => {
    const { container } = render(
      <MemoryRouter>
        <CoverageCard
          row={row({
            session_state: 'closed',
            change_pct_1d: -6.56,
            price_as_of: '2026-06-05T20:00:00Z',
          })}
          density="comfort"
          onOpen={vi.fn()}
        />
      </MemoryRouter>,
    )
    const change = container.querySelector('.coverage-card__change') as HTMLElement
    expect(change.textContent).toContain('-6.56% · 06-05')
    expect(change.textContent).not.toContain('1D')
  })
})

describe('CoverageCard verdict signal chroma', () => {
  function signal(over: Partial<CoverageRow>): string | null {
    const { container } = render(
      <MemoryRouter>
        <CoverageCard row={row(over)} density="comfort" onOpen={vi.fn()} />
      </MemoryRouter>,
    )
    return (container.querySelector('.coverage-card') as HTMLElement).getAttribute('data-signal')
  }

  it('maps the three directional verdicts to their hue bucket', () => {
    expect(signal({ latest_verdict: 'BUY' })).toBe('buy')
    expect(signal({ latest_verdict: 'SELL' })).toBe('sell')
    expect(signal({ latest_verdict: 'HOLD' })).toBe('hold')
  })

  it('treats NOT RUN (null) and the legacy WITHHELD/REVIEW token as neutral', () => {
    expect(signal({ latest_verdict: null })).toBe('neutral')
    expect(signal({ latest_verdict: 'WITHHELD' })).toBe('neutral')
    expect(signal({ latest_verdict: 'REVIEW' })).toBe('neutral')
  })
})

describe('CoverageCard owned checkbox', () => {
  function renderOwned(
    over: Partial<CoverageRow>,
    opts: {
      pending?: boolean
      onSetOwned?: (ticker: string, owned: boolean) => void
      onOpen?: () => void
    } = {},
  ): void {
    render(
      <MemoryRouter>
        <CoverageCard
          row={row(over)}
          density="comfort"
          onOpen={opts.onOpen ?? vi.fn()}
          onSetOwned={opts.onSetOwned}
          ownedPending={opts.pending}
        />
      </MemoryRouter>,
    )
  }

  it('reflects the row owned flag', () => {
    renderOwned({ ticker: 'AAA', owned: true })
    expect(screen.getByLabelText('Mark AAA as owned')).toBeChecked()
  })

  it('calls setOwned with the ticker + new value on toggle, without opening the card', () => {
    const onSetOwned = vi.fn()
    const onOpen = vi.fn()
    renderOwned({ ticker: 'NFLX', owned: false }, { onSetOwned, onOpen })
    fireEvent.click(screen.getByLabelText('Mark NFLX as owned'))
    expect(onSetOwned).toHaveBeenCalledTimes(1)
    expect(onSetOwned).toHaveBeenCalledWith('NFLX', true)
    // The card is role=link with click-to-open; the checkbox must NOT bubble.
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('is disabled while that ticker’s write is in flight', () => {
    renderOwned({ ticker: 'AAA', owned: false }, { pending: true })
    expect(screen.getByLabelText('Mark AAA as owned')).toBeDisabled()
  })
})

describe('CoverageCard delete control', () => {
  function renderDelete(
    over: Partial<CoverageRow>,
    opts: { onDelete?: (ticker: string) => void; onOpen?: () => void } = {},
  ): void {
    render(
      <MemoryRouter>
        <CoverageCard
          row={row(over)}
          density="comfort"
          onOpen={opts.onOpen ?? vi.fn()}
          onDelete={opts.onDelete}
        />
      </MemoryRouter>,
    )
  }

  it('opens the confirm on the X and never triggers the card open handler', () => {
    const onOpen = vi.fn()
    renderDelete({ ticker: 'NFLX', artifact_count: 3 }, { onOpen })
    fireEvent.click(screen.getByTestId('coverage-delete-NFLX'))
    expect(screen.getByTestId('coverage-delete-confirm-NFLX')).toBeInTheDocument()
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('does not open the card on an Enter keydown at the X', () => {
    const onOpen = vi.fn()
    renderDelete({ ticker: 'NFLX' }, { onOpen })
    fireEvent.keyDown(screen.getByTestId('coverage-delete-NFLX'), { key: 'Enter' })
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('Cancel closes the confirm without calling the mutation', () => {
    const onDelete = vi.fn()
    renderDelete({ ticker: 'NFLX', artifact_count: 3 }, { onDelete })
    fireEvent.click(screen.getByTestId('coverage-delete-NFLX'))
    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.queryByTestId('coverage-delete-confirm-NFLX')).not.toBeInTheDocument()
    expect(onDelete).not.toHaveBeenCalled()
  })

  it('Escape cancels the confirm', () => {
    renderDelete({ ticker: 'NFLX', artifact_count: 3 }, {})
    fireEvent.click(screen.getByTestId('coverage-delete-NFLX'))
    fireEvent.keyDown(screen.getByTestId('coverage-delete-confirm-NFLX'), { key: 'Escape' })
    expect(screen.queryByTestId('coverage-delete-confirm-NFLX')).not.toBeInTheDocument()
  })

  it('a backdrop click cancels the confirm', () => {
    renderDelete({ ticker: 'NFLX', artifact_count: 3 }, {})
    fireEvent.click(screen.getByTestId('coverage-delete-NFLX'))
    fireEvent.click(screen.getByTestId('coverage-delete-confirm-NFLX'))
    expect(screen.queryByTestId('coverage-delete-confirm-NFLX')).not.toBeInTheDocument()
  })

  it('confirming calls onDelete with the ticker and closes', () => {
    const onDelete = vi.fn()
    const onOpen = vi.fn()
    renderDelete({ ticker: 'NFLX', artifact_count: 3 }, { onDelete, onOpen })
    fireEvent.click(screen.getByTestId('coverage-delete-NFLX'))
    fireEvent.click(screen.getByTestId('coverage-delete-confirm-btn-NFLX'))
    expect(onDelete).toHaveBeenCalledTimes(1)
    expect(onDelete).toHaveBeenCalledWith('NFLX')
    expect(screen.queryByTestId('coverage-delete-confirm-NFLX')).not.toBeInTheDocument()
    // The destructive path must never also navigate to the ticker.
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('names the ticker and the artifact count in the body', () => {
    renderDelete({ ticker: 'NFLX', artifact_count: 5 }, {})
    fireEvent.click(screen.getByTestId('coverage-delete-NFLX'))
    const dialog = screen.getByTestId('coverage-delete-confirm-NFLX')
    expect(dialog).toHaveTextContent('Delete NFLX?')
    expect(dialog).toHaveTextContent('NFLX leaves the desk')
    expect(dialog).toHaveTextContent('5 stored artifacts')
    expect(dialog).toHaveTextContent('This cannot be undone')
  })

  it('uses the empty wording when the card has no artifacts', () => {
    renderDelete({ ticker: 'NFLX', artifact_count: 0 }, {})
    fireEvent.click(screen.getByTestId('coverage-delete-NFLX'))
    const dialog = screen.getByTestId('coverage-delete-confirm-NFLX')
    expect(dialog).toHaveTextContent('It has no stored artifacts')
    expect(dialog).not.toHaveTextContent('0 stored artifacts')
  })
})

describe('CoverageCard footer layout', () => {
  it('gives the report summary its own row, with the status pill and owned checkbox below', () => {
    // The three used to share one row, which ellipsised the summary away behind
    // the pill and the checkbox ("1 reports - lat…"). The summary now owns the
    // row; both controls drop to the row beneath it.
    renderCard({ ticker: 'NFLX', artifact_count: 3, research_count: 3 })
    const footer = document.querySelector('.coverage-card__footer')
    expect(footer).not.toBeNull()
    const summary = footer?.querySelector('.coverage-card__report')
    const meta = footer?.querySelector('.coverage-card__footer-meta')
    expect(summary).not.toBeNull()
    expect(meta).not.toBeNull()
    // Summary first, and NOT part of the secondary row.
    expect(footer?.firstElementChild).toBe(summary)
    expect(meta?.contains(summary as Node)).toBe(false)
    // Both controls now live in that second row.
    expect(meta?.querySelector('.coverage-card__status')).not.toBeNull()
    expect(meta?.querySelector('input[type="checkbox"]')).not.toBeNull()
  })
})

describe('CoverageCard re-run tick', () => {
  function renderSelectable(over: Partial<CoverageRow>, selected = false) {
    const onOpen = vi.fn()
    const onToggleSelect = vi.fn()
    render(
      <MemoryRouter>
        <CoverageCard
          row={row(over)}
          density="comfort"
          onOpen={onOpen}
          selected={selected}
          onToggleSelect={onToggleSelect}
        />
      </MemoryRouter>,
    )
    return { onOpen, onToggleSelect }
  }

  it('ticks without opening the ticker workspace (the card is a link)', () => {
    const { onOpen, onToggleSelect } = renderSelectable({ ticker: 'KGC' })
    fireEvent.click(screen.getByLabelText('Select KGC to re-run'))
    expect(onToggleSelect).toHaveBeenCalledWith('KGC', true)
    // The card's own click handler opens the ticker; the tick must swallow it.
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('unticking reports false, so the page can drop the name', () => {
    const { onToggleSelect } = renderSelectable({ ticker: 'KGC' }, true)
    fireEvent.click(screen.getByLabelText('Select KGC to re-run'))
    expect(onToggleSelect).toHaveBeenCalledWith('KGC', false)
  })

  it('renders the control only when the page offers a selection', () => {
    renderCard({ ticker: 'KGC' })
    expect(screen.queryByTestId('coverage-select-KGC')).not.toBeInTheDocument()
  })

  it('marks the ticked card for the wall (data-selected)', () => {
    renderSelectable({ ticker: 'KGC' }, true)
    expect(screen.getByTestId('coverage-card-KGC')).toHaveAttribute('data-selected', 'true')
  })

  it('leaves an unticked card unmarked', () => {
    renderSelectable({ ticker: 'KGC' })
    expect(screen.getByTestId('coverage-card-KGC')).not.toHaveAttribute('data-selected')
  })
})
