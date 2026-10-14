// The coverage table must follow run state WITHOUT a manual reload.
//
// Regression guard for the reported bug: a full KGC report ran, its artifact was
// in the store, and its coverage card only appeared after the user reloaded the
// page. `useCoverageOverview` re-fetches only on an explicit invalidation (member
// mutation / batch completion / 刷新), and the query-client defaults are
// staleTime 5 min + refetchOnWindowFocus:false — so nothing re-read the table when
// a report finished in the ticker workspace. The bridge subscribes to the run
// stream store and invalidates the coverage queries on the two transitions that
// change what a row shows:
//
//   1. a ticker gains a run  → the row's run state changes
//   2. that run terminates   → its artifact exists, so verdict/target change
//
// …and on nothing else: SSE step ticks must stay free, because the overview
// refresh is a provider fan-out.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { useCoverageRunBridge } from './useCoverage'
import { useRunStreamStore, type RunState } from '../stores/runStreamStore'

function run(overrides: Partial<RunState> = {}): RunState {
  return {
    runId: 'run-1',
    ticker: 'KGC',
    pipelineType: 'research',
    steps: [],
    status: 'running',
    progress: 0,
    error: null,
    startedAt: 0,
    dismissed: false,
    artifactId: null,
    artifactType: null,
    cancelling: false,
    ...overrides,
  }
}

function renderBridge() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const invalidate = vi.spyOn(client, 'invalidateQueries')
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  const view = renderHook(() => useCoverageRunBridge(), { wrapper })
  const setRuns = (runs: Record<string, RunState>) => {
    act(() => {
      useRunStreamStore.setState({ runs })
    })
  }
  return { invalidate, setRuns, ...view }
}

beforeEach(() => {
  useRunStreamStore.setState({ runs: {} })
})

describe('useCoverageRunBridge', () => {
  it('invalidates once when a ticker gains a run, and once when it terminates', async () => {
    const { invalidate, setRuns } = renderBridge()
    // Mounting the shell is the baseline, not a change.
    expect(invalidate).not.toHaveBeenCalled()

    setRuns({ KGC: run() })
    await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(1))

    setRuns({ KGC: run({ status: 'completed', artifactId: 'art_kgc' }) })
    await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(2))
    expect(invalidate.mock.calls[0][0]).toEqual({ queryKey: ['coverage'] })
  })

  it('treats a failed run as terminal — the row must stop reading "running"', async () => {
    const { invalidate, setRuns } = renderBridge()

    setRuns({ KGC: run() })
    await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(1))

    setRuns({ KGC: run({ status: 'failed', error: 'peer set unavailable' }) })
    await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(2))
  })

  it('does not re-fetch on SSE step ticks or progress frames', async () => {
    const { invalidate, setRuns } = renderBridge()

    setRuns({ KGC: run() })
    await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(1))

    setRuns({
      KGC: run({ progress: 0.4, steps: [{ name: 'data_collection', status: 'completed' }] }),
    })
    setRuns({
      KGC: run({ progress: 0.8, steps: [{ name: 'financial_modeling', status: 'running' }] }),
    })
    setRuns({ KGC: run({ progress: 0.9, cancelling: true }) })

    expect(invalidate).toHaveBeenCalledTimes(1)
  })
})
