/**
 * CoverageRerunPanel — filter count + live batch-progress rendering.
 *
 * Verifies the submit count matches the shared filter predicate (the SAME rule
 * the backend select_targets applies), and that a polled CoverageBatchProgress
 * payload renders its counts, the detected cap + binder, and each item's state.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { CoverageBatchProgress, CoverageRow } from '../../api/coverage'

// The panel's only server boundary is these two hooks; stub them so the test
// drives the query/mutation state directly (no HTTP).
const hooks = {
  rerun: {
    mutate: vi.fn() as unknown as (body: unknown, opts?: unknown) => void,
    isPending: false,
    isError: false,
  },
  batch: {
    data: undefined as CoverageBatchProgress | undefined,
    isError: false,
  },
}

vi.mock('../../hooks/useCoverage', () => ({
  useRerunAll: () => hooks.rerun,
  useCoverageBatch: () => hooks.batch,
}))

import { CoverageRerunPanel, countRerunTargets, rerunFilters } from './CoverageRerunPanel'

function row(over: Partial<CoverageRow>): CoverageRow {
  return {
    ticker: 'AAA',
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

const ROWS: CoverageRow[] = [
  row({ ticker: 'B', latest_verdict: 'BUY', owned: true }),
  row({ ticker: 'H', latest_verdict: 'HOLD', owned: true }),
  row({ ticker: 'S', latest_verdict: 'SELL', owned: false }),
  row({ ticker: 'N', latest_verdict: null, owned: false }),
]

const PROGRESS: CoverageBatchProgress = {
  batch_id: 'cb_ab12',
  group_id: 'cov_ab',
  pipeline_type: 'research',
  state: 'running',
  limit: 4,
  ceiling: 4,
  binding_provider: 'moomoo',
  binding_reason: 'moomoo: 4 concurrent connections (owner-declared)',
  providers: [
    {
      provider: 'moomoo',
      max_concurrency: 4,
      source: 'owner-declared',
      declared: true,
      binding: true,
    },
  ],
  undeclared_count: 6,
  total: 3,
  queued: 1,
  running: 1,
  completed: 2,
  failed: 0,
  items: [
    { ticker: 'NFLX', state: 'queued', run_id: null, error: null },
    { ticker: 'AAPL', state: 'running', run_id: 'r1', error: null },
    { ticker: 'MSFT', state: 'completed', run_id: 'r2', error: null },
  ],
  created_at: '2026-10-13T05:00:00Z',
}

function renderPanel(rows: CoverageRow[] = ROWS, onCompleted = vi.fn()): void {
  render(
    <CoverageRerunPanel groupId="cov_ab" rows={rows} onClose={vi.fn()} onCompleted={onCompleted} />,
  )
}

beforeEach(() => {
  hooks.rerun = { mutate: vi.fn(), isPending: false, isError: false }
  hooks.batch = { data: undefined, isError: false }
})

describe('rerun filter predicate (mirrors backend select_targets)', () => {
  it('all four ratings selected → no rating filter (ratings null)', () => {
    const filters = rerunFilters(false, new Set(['BUY', 'HOLD', 'SELL', 'UNRATED']))
    expect(filters).toEqual({ owned: null, ratings: null })
  })

  it('a subset of ratings → only that subset, and owned only → owned true', () => {
    const filters = rerunFilters(true, new Set(['BUY']))
    expect(filters).toEqual({ owned: true, ratings: ['BUY'] })
  })

  it('counts owned + rating matches; UNRATED covers a null verdict', () => {
    // owned only, all ratings → the two owned rows.
    expect(
      countRerunTargets(ROWS, rerunFilters(true, new Set(['BUY', 'HOLD', 'SELL', 'UNRATED']))),
    ).toBe(2)
    // no owned filter, only BUY → the one BUY row.
    expect(countRerunTargets(ROWS, rerunFilters(false, new Set(['BUY'])))).toBe(1)
    // no owned filter, only UNRATED → the null-verdict row.
    expect(countRerunTargets(ROWS, rerunFilters(false, new Set(['UNRATED'])))).toBe(1)
    // no filters → every row.
    expect(countRerunTargets(ROWS, rerunFilters(false, new Set()))).toBe(4)
  })
})

describe('CoverageRerunPanel', () => {
  it('shows the count of currently-matching cards and updates it on filter change', () => {
    renderPanel()
    const submit = screen.getByTestId('coverage-rerun-submit')
    // Default: no owned filter, all ratings → all four.
    expect(submit).toHaveTextContent('Re-run 4 reports')

    fireEvent.click(screen.getByLabelText('Owned only'))
    expect(submit).toHaveTextContent('Re-run 2 reports')

    // Narrow to BUY only → the single owned BUY row.
    fireEvent.click(screen.getByLabelText('Hold'))
    fireEvent.click(screen.getByLabelText('Sell'))
    fireEvent.click(screen.getByLabelText('Not run'))
    expect(submit).toHaveTextContent('Re-run 1 reports')
  })

  it('renders the progress counts, the detected cap + binder, and each item state', () => {
    hooks.batch = { data: PROGRESS, isError: false }
    renderPanel()

    expect(screen.getByTestId('coverage-rerun-counts')).toHaveTextContent(
      '1 queued · 1 running · 2 done · 0 failed',
    )
    const cap = screen.getByTestId('coverage-rerun-cap')
    expect(cap).toHaveTextContent('Detected cap: 4 concurrent runs')
    expect(cap).toHaveTextContent('bound by moomoo')

    expect(screen.getByTestId('coverage-rerun-item-NFLX')).toHaveTextContent('NFLX')
    expect(screen.getByTestId('coverage-rerun-item-NFLX')).toHaveTextContent('queued')
    expect(screen.getByTestId('coverage-rerun-item-AAPL')).toHaveTextContent('running')
    expect(screen.getByTestId('coverage-rerun-item-MSFT')).toHaveTextContent('done')
  })

  it('falls back to the ceiling binder when no provider binds the limit', () => {
    hooks.batch = {
      data: { ...PROGRESS, binding_provider: null, binding_reason: 'LLM run ceiling: 4' },
      isError: false,
    }
    renderPanel()
    expect(screen.getByTestId('coverage-rerun-cap')).toHaveTextContent('bound by the run ceiling')
  })

  it('refetches the overview once when the batch completes', async () => {
    const onCompleted = vi.fn()
    hooks.batch = { data: { ...PROGRESS, state: 'completed' }, isError: false }
    renderPanel(ROWS, onCompleted)
    await waitFor(() => expect(onCompleted).toHaveBeenCalledTimes(1))
  })
})

describe('CoverageRerunPanel watching a caller-started batch', () => {
  it('names the explicit set and drops the filter UI, which cannot express it', () => {
    hooks.batch = { data: PROGRESS, isError: false }
    render(
      <CoverageRerunPanel
        groupId="cov_ab"
        rows={ROWS}
        onClose={vi.fn()}
        startedBatch={{ batchId: 'cb_ab12', tickers: ['AAPL', 'MSFT'] }}
      />,
    )
    // No filters, no submit: "re-run selected" already fired the batch on click.
    expect(screen.queryByTestId('coverage-rerun-submit')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Owned only')).not.toBeInTheDocument()
    // The set is named before the first poll lands, and the readout renders.
    const set = screen.getByTestId('coverage-rerun-selected-set')
    expect(set).toHaveTextContent('Submitted 2 tickers')
    expect(set).toHaveTextContent('AAPL · MSFT')
    expect(screen.getByTestId('coverage-rerun-counts')).toHaveTextContent('1 queued')
    expect(screen.getByTestId('coverage-rerun-item-AAPL')).toHaveTextContent('running')
  })
})
