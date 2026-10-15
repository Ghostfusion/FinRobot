import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// CoverageHero pulls in SplineHero (remote <script>) — stub it.
vi.mock('../components/coverage/CoverageHero', () => ({ CoverageHero: () => null }))

function makeOverview() {
  return {
    data: undefined as unknown,
    isLoading: false,
    isError: false,
    marketPending: false,
    marketError: false,
    refetch: vi.fn(),
    refreshing: false,
    refreshNoop: false,
  }
}

const hooks = {
  groups: { data: undefined as unknown, isLoading: false, isError: false, refetch: vi.fn() },
  overview: makeOverview(),
  // The page mounts useSetOwned; the re-run panel (opened on demand) mounts
  // useRerunAll + useCoverageBatch.
  setOwned: {
    mutate: vi.fn(),
    isPending: false,
    variables: undefined as { ticker: string; owned: boolean } | undefined,
  },
  rerun: { mutate: vi.fn(), isPending: false, isError: false },
  batch: { data: undefined as unknown, isError: false },
  // Destructive delete is mounted with the active group id; capture both it and
  // the ticker the card hands the mutation so the (groupId, ticker) wiring is
  // asserted end-to-end.
  deleteTicker: { mutate: vi.fn() },
  deleteGroupId: '' as string,
}

vi.mock('../hooks/useCoverage', () => ({
  useCoverageGroups: () => hooks.groups,
  useCoverageOverview: () => hooks.overview,
  useSetOwned: () => hooks.setOwned,
  useRerunAll: () => hooks.rerun,
  useCoverageBatch: () => hooks.batch,
  useDeleteCoverageTicker: (groupId: string) => {
    hooks.deleteGroupId = groupId
    return hooks.deleteTicker
  },
}))

import { CoveragePage } from './CoveragePage'

// A full CoverageRow for the page fixtures below (the wall renders every field).
function pageRow(ticker: string) {
  return {
    ticker,
    owned: false,
    company: null,
    price: null,
    change_pct_1d: null,
    price_as_of: null,
    session_state: null,
    market_cap: null,
    revenue_ttm: null,
    ev_ebitda: null,
    pe: null,
    currency: null,
    latest_verdict: null,
    target_price: null,
    target_low: null,
    target_high: null,
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
  }
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CoveragePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CoveragePage error states (BUG-051)', () => {
  beforeEach(() => {
    hooks.groups = { data: undefined, isLoading: false, isError: false, refetch: vi.fn() }
    hooks.overview = makeOverview()
    hooks.setOwned = { mutate: vi.fn(), isPending: false, variables: undefined }
  })

  it('shows an error (not the starter) when the groups request fails', () => {
    hooks.groups = { data: undefined, isLoading: false, isError: true, refetch: vi.fn() }
    renderPage()
    expect(screen.getByTestId('coverage-error')).toBeInTheDocument()
    // The empty-state starter must NOT appear on a failure.
    expect(screen.queryByTestId('coverage-empty')).not.toBeInTheDocument()
  })

  it('shows an error (not "empty group") when the overview request fails', () => {
    hooks.groups = {
      data: [{ id: 'g1', name: 'AI', member_count: 1 }],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }
    hooks.overview = {
      data: undefined,
      isLoading: false,
      isError: true,
      marketPending: false,
      marketError: false,
      refetch: vi.fn(),
      refreshing: false,
      refreshNoop: false,
    }
    renderPage()
    expect(screen.getByTestId('coverage-error')).toBeInTheDocument()
  })
})

describe('CoveragePage refresh control', () => {
  beforeEach(() => {
    hooks.groups = {
      data: [{ id: 'g1', name: 'Studied Tickers', member_count: 1, is_system: true }],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }
    hooks.overview = {
      ...makeOverview(),
      data: {
        group_id: 'g1',
        group_name: 'Studied Tickers',
        rows: [],
        generated_at: '2026-06-08T09:00:00Z',
        partial: false,
        cache_only: false,
        refresh_noop: false,
      },
    }
    hooks.setOwned = { mutate: vi.fn(), isPending: false, variables: undefined }
  })

  it('renders the refresh button and re-runs the revalidate on click', () => {
    renderPage()
    const btn = screen.getByTestId('coverage-refresh-btn')
    expect(btn).toHaveTextContent('Refresh')
    fireEvent.click(btn)
    expect(hooks.overview.refetch).toHaveBeenCalledTimes(1)
  })
})

describe('CoveragePage header rail', () => {
  beforeEach(() => {
    hooks.groups = {
      data: [{ id: 'g1', name: 'Studied Tickers', member_count: 1, is_system: true }],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }
    hooks.overview = {
      ...makeOverview(),
      data: {
        group_id: 'g1',
        group_name: 'Studied Tickers',
        rows: [
          {
            ticker: 'AAPL',
            owned: false,
            company: null,
            price: null,
            change_pct_1d: null,
            price_as_of: null,
            session_state: null,
            market_cap: null,
            revenue_ttm: null,
            ev_ebitda: null,
            pe: null,
            currency: null,
            latest_verdict: 'BUY',
            target_price: null,
            target_low: null,
            target_high: null,
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
          },
        ],
        generated_at: '2026-06-08T09:00:00Z',
        partial: false,
        cache_only: false,
        refresh_noop: false,
      },
    }
    hooks.setOwned = { mutate: vi.fn(), isPending: false, variables: undefined }
    hooks.rerun = { mutate: vi.fn(), isPending: false, isError: false }
    hooks.batch = { data: undefined, isError: false }
  })

  it('renders the sort box with the surfaced keys, ownership last', () => {
    renderPage()
    const select = screen.getByTestId('coverage-sort-select') as HTMLSelectElement
    expect(Array.from(select.options).map((o) => o.textContent)).toEqual([
      'Needs attention',
      'Name',
      'Rating',
      'Ownership',
    ])
  })

  it('opens the re-run-all panel from the rail', () => {
    renderPage()
    expect(screen.queryByTestId('coverage-rerun-panel')).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId('coverage-rerun-open'))
    expect(screen.getByTestId('coverage-rerun-panel')).toBeInTheDocument()
  })
})

describe('CoveragePage delete ticker', () => {
  beforeEach(() => {
    hooks.groups = {
      data: [{ id: 'g1', name: 'Studied Tickers', member_count: 1, is_system: true }],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }
    hooks.overview = {
      ...makeOverview(),
      data: {
        group_id: 'g1',
        group_name: 'Studied Tickers',
        rows: [
          {
            ticker: 'AAPL',
            owned: false,
            company: null,
            price: null,
            change_pct_1d: null,
            price_as_of: null,
            session_state: null,
            market_cap: null,
            revenue_ttm: null,
            ev_ebitda: null,
            pe: null,
            currency: null,
            latest_verdict: 'BUY',
            target_price: null,
            target_low: null,
            target_high: null,
            target_date: null,
            entry_price: null,
            upside_to_target_live: null,
            signal: null,
            artifact_count: 2,
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
          },
        ],
        generated_at: '2026-06-08T09:00:00Z',
        partial: false,
        cache_only: false,
        refresh_noop: false,
      },
    }
    hooks.setOwned = { mutate: vi.fn(), isPending: false, variables: undefined }
    hooks.deleteTicker = { mutate: vi.fn() }
    hooks.deleteGroupId = ''
  })

  it('confirms the delete with the active group id and the clicked ticker', () => {
    renderPage()
    fireEvent.click(screen.getByTestId('coverage-delete-AAPL'))
    fireEvent.click(screen.getByTestId('coverage-delete-confirm-btn-AAPL'))
    // The hook binds the active group; the card supplies the ticker → both land.
    expect(hooks.deleteGroupId).toBe('g1')
    expect(hooks.deleteTicker.mutate).toHaveBeenCalledTimes(1)
    expect(hooks.deleteTicker.mutate).toHaveBeenCalledWith('AAPL')
  })
})

describe('CoveragePage re-run selected', () => {
  beforeEach(() => {
    hooks.groups = {
      data: [{ id: 'g1', name: 'Studied Tickers', member_count: 2, is_system: true }],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }
    hooks.overview = {
      ...makeOverview(),
      data: {
        group_id: 'g1',
        group_name: 'Studied Tickers',
        rows: [pageRow('AAPL'), pageRow('KGC')],
        generated_at: '2026-06-08T09:00:00Z',
        partial: false,
        cache_only: false,
        refresh_noop: false,
      },
    }
    hooks.rerun = { mutate: vi.fn(), isPending: false, isError: false }
    hooks.batch = { data: undefined, isError: false }
  })

  it('starts at zero ticks, and the button says so', () => {
    renderPage()
    const btn = screen.getByTestId('coverage-rerun-selected')
    expect(btn).toBeDisabled()
    expect(btn).toHaveTextContent('Re-run selected (0)')
  })

  it('re-runs ONLY the ticked cards, then hands that batch to the panel', () => {
    renderPage()
    fireEvent.click(screen.getByLabelText('Select KGC to re-run'))
    const btn = screen.getByTestId('coverage-rerun-selected')
    expect(btn).not.toBeDisabled()
    expect(btn).toHaveTextContent('Re-run selected (1)')

    fireEvent.click(btn)
    expect(hooks.rerun.mutate).toHaveBeenCalledTimes(1)
    const [body, opts] = hooks.rerun.mutate.mock.calls[0]
    // The tick set IS the selection: no filter rides along that could widen it to
    // the whole wall, and the count the user saw is the count that was sent.
    expect(body).toEqual({
      tickers: ['KGC'],
      owned: null,
      ratings: null,
      pipeline_type: 'research',
      language: null,
    })
    // The panel opens on the batch the POST returned, naming the explicit set.
    act(() => opts.onSuccess({ batch_id: 'cb_1' }))
    expect(screen.getByTestId('coverage-rerun-panel')).toBeInTheDocument()
    expect(screen.getByTestId('coverage-rerun-selected-set')).toHaveTextContent('KGC')
  })

  it('drops a tick whose card left the wall (no phantom count it cannot re-run)', () => {
    renderPage()
    fireEvent.click(screen.getByLabelText('Select KGC to re-run'))
    expect(screen.getByTestId('coverage-rerun-selected')).toHaveTextContent('Re-run selected (1)')

    // KGC leaves the group (deleted here, or removed from another window). The
    // hook mock only takes effect on a render, so nudge the page with a
    // page-owned state write — the same render the overview refetch would cause.
    hooks.overview = {
      ...hooks.overview,
      data: { ...(hooks.overview.data as { rows: unknown[] }), rows: [pageRow('AAPL')] },
    }
    fireEvent.click(screen.getByTestId('coverage-sort-dir'))

    expect(screen.getByTestId('coverage-rerun-selected')).toHaveTextContent('Re-run selected (0)')
    expect(screen.getByTestId('coverage-rerun-selected')).toBeDisabled()
  })

  it('spends the ticks once the batch is accepted (no second identical fan-out)', () => {
    renderPage()
    fireEvent.click(screen.getByLabelText('Select KGC to re-run'))
    fireEvent.click(screen.getByTestId('coverage-rerun-selected'))
    act(() => hooks.rerun.mutate.mock.calls[0][1].onSuccess({ batch_id: 'cb_1' }))
    expect(screen.getByTestId('coverage-rerun-selected')).toBeDisabled()
    expect(screen.getByTestId('coverage-card-KGC')).not.toHaveAttribute('data-selected')
  })
})
