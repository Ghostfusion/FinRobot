// useCoverage — TanStack Query hooks over the surfaced Coverage API. Server
// state (system group / overview) lives here; local sort density lives in
// coverageStore. Opening a ticker auto-enrols it into Studied Tickers.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  coverageApi,
  type CoverageBatchProgress,
  type CoverageGroupSummary,
  type CoverageGroupDetail,
  type CoverageOverview,
  type CoverageRerunRequest,
  type CoverageTickerDeletion,
} from '../api/coverage'
import { useToastStore } from '../stores/toastStore'
import { tSync } from '../i18n'
import { mapErrorToUserMessage } from '../utils/errorMessage'

const KEYS = {
  groups: ['coverage', 'groups'] as const,
  overview: (id: string) => ['coverage', 'overview', id] as const,
  // Every overview (primary cache-only paint AND its nested `fresh` revalidate)
  // rides this prefix — used to patch the global owned flag across all of them.
  overviewPrefix: ['coverage', 'overview'] as const,
  batch: (id: string) => ['coverage', 'batch', id] as const,
}

export function useCoverageGroups() {
  return useQuery<CoverageGroupSummary[]>({
    queryKey: KEYS.groups,
    queryFn: () => coverageApi.listGroups(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}

export interface CoverageOverviewState {
  data: CoverageOverview | undefined
  isLoading: boolean
  isError: boolean
  /** The background network revalidate is in flight. Drives the global
   *  "refreshing" affordance; the card shimmers ONLY its cold cells (no snapshot
   *  yet) — rows that already hold a stale snapshot show their last-known value
   *  with a refreshing hint, never a blank shimmer. */
  marketPending: boolean
  /** The revalidate FAILED while the cache-only paint stands in — market numbers
   *  are the last-known snapshot (possibly stale), not fresh. The page surfaces a
   *  retry affordance wired to refetch() (BUG-032). */
  marketError: boolean
  /** Re-run the network revalidate — used by the error-state retry (BUG-051),
   *  the market-degraded retry bar (BUG-032), and the manual 刷新 button. */
  refetch: () => void
  /** A network revalidate is fetching right now — the initial background pass OR
   *  a manual refresh. Unlike ``marketPending`` (which only covers the FIRST
   *  paint, gated on ``!fresh.data``), this stays true through every manual
   *  refetch, so the 刷新 button can show its in-flight state on repeat clicks. */
  refreshing: boolean
  /** The last network refresh made ZERO price provider calls — every row was a
   *  closed-market calendar no-op (already at its latest settled close). Lets the
   *  button confirm "已是最新收盘" instead of implying it pulled live quotes. */
  refreshNoop: boolean
}

/**
 * Stale-while-revalidate overview. Phase 1 (`refresh=false`) is the instant
 * cache-only paint: the server reads the canonical cache (allow-stale, no
 * network) so the desk fills in ~ms at any N — no more waiting on the cold
 * provider fan-out (measured 6.6s/6 tickers, >180s/100). Phase 2 (`refresh=true`)
 * is the background network revalidate: a bounded fan-out repopulates the cache
 * and returns fresh numbers, swapped into the primary view. The revalidate query
 * nests under the primary key so member-mutation invalidations (prefix-matched on
 * `['coverage','overview',id]`) hit both phases.
 */
export function useCoverageOverview(groupId: string | null): CoverageOverviewState {
  const cached = useQuery<CoverageOverview>({
    queryKey: KEYS.overview(groupId ?? ''),
    queryFn: () => coverageApi.overview(groupId as string, false),
    enabled: !!groupId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
  const fresh = useQuery<CoverageOverview>({
    queryKey: [...KEYS.overview(groupId ?? ''), 'fresh'],
    queryFn: () => coverageApi.overview(groupId as string, true),
    // Fire once the instant paint has landed; the network result then supersedes
    // the cache-only snapshot.
    enabled: !!groupId && !!cached.data,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
  const data = fresh.data ?? cached.data
  return {
    data,
    isLoading: !data && cached.isLoading,
    isError: !data && cached.isError,
    // Background revalidate in flight (and not yet resolved). The card uses this
    // together with per-row market_stale/price to decide shimmer (cold) vs
    // refreshing-hint (stale snapshot present).
    marketPending: !fresh.data && fresh.isFetching,
    // Revalidate failed but the cache-only paint kept the table alive — the
    // numbers are last-known, not fresh. Drives the degraded retry bar.
    marketError: !fresh.data && fresh.isError && !!cached.data,
    refetch: () => void fresh.refetch(),
    refreshing: fresh.isFetching,
    refreshNoop: data?.refresh_noop ?? false,
  }
}

/**
 * Auto-add an opened ticker to the default Studied Tickers workspace.
 * Fired once per successful /stocks/:ticker open (the search → workspace
 * contract). Idempotent server-side, so re-opens are cheap no-ops. Invalidates
 * the group list (member_count) + every overview (the studied group's table
 * gains a row); we don't know the studied group's id here, so the broad
 * `['coverage','overview']` prefix covers it without threading the id through.
 */
export function useAddStudiedTicker() {
  const qc = useQueryClient()
  return useMutation<CoverageGroupDetail, Error, string>({
    mutationFn: (ticker) => coverageApi.addStudiedTicker(ticker),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.groups })
      qc.invalidateQueries({ queryKey: KEYS.overviewPrefix })
    },
  })
}

/**
 * Toggle a ticker's global owned flag. The flag is per-TICKER, not per-group, so
 * a successful write must patch the row in EVERY cached overview — not just the
 * one on screen. `setQueriesData` over the `['coverage','overview']` prefix hits
 * both the cache-only paint and its nested `fresh` revalidate cache; a full
 * invalidate would re-run the network revalidate for a flag the server already
 * confirmed via the PUT response, so we rewrite the row in place instead.
 */
export function useSetOwned() {
  const qc = useQueryClient()
  return useMutation<{ ticker: string; owned: boolean }, Error, { ticker: string; owned: boolean }>(
    {
      mutationFn: ({ ticker, owned }) => coverageApi.setOwned(ticker, owned),
      onSuccess: ({ ticker, owned }) => {
        qc.setQueriesData<CoverageOverview>({ queryKey: KEYS.overviewPrefix }, (prev) => {
          if (!prev) return prev
          return {
            ...prev,
            rows: prev.rows.map((r) => (r.ticker === ticker ? { ...r, owned } : r)),
          }
        })
      },
    },
  )
}

/**
 * Delete a ticker from the desk: drop its membership AND every stored artifact
 * for it in one action. Success invalidates THIS group's overview (both the
 * cache-only paint and its nested `fresh` revalidate, prefix-matched by the
 * group's key) so the card leaves the wall, and confirms through the toast
 * store — the app's surface for a completed destructive action. On failure the
 * card stays put, so the toast carries the reason instead of a silent no-op.
 */
export function useDeleteCoverageTicker(groupId: string) {
  const qc = useQueryClient()
  const addToast = useToastStore((s) => s.addToast)
  return useMutation<CoverageTickerDeletion, Error, string>({
    mutationFn: (ticker) => coverageApi.deleteTicker(groupId, ticker),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: KEYS.overview(groupId) })
      addToast({
        type: 'success',
        title: tSync('coverage.delete.done', {
          ticker: result.ticker,
          n: result.artifacts_deleted,
        }),
      })
    },
    onError: (err: Error) => {
      addToast({
        type: 'error',
        title: tSync('coverage.delete.failed'),
        description: mapErrorToUserMessage(err),
      })
    },
  })
}

/**
 * Start a filtered re-run-all batch. Returns the initial CoverageBatchProgress;
 * the caller keeps its `batch_id` and hands it to `useCoverageBatch` to poll.
 */
export function useRerunAll(groupId: string) {
  return useMutation<CoverageBatchProgress, Error, CoverageRerunRequest>({
    mutationFn: (body) => coverageApi.rerunAll(groupId, body),
  })
}

/**
 * Live batch progress. Polls every 2s ONLY while the batch is not yet
 * `completed`, and never when there's no batch (batchId null). staleTime 0 so a
 * poll always reads the live server snapshot, not a cached one.
 */
export function useCoverageBatch(batchId: string | null) {
  return useQuery<CoverageBatchProgress>({
    queryKey: KEYS.batch(batchId ?? ''),
    queryFn: () => coverageApi.batchProgress(batchId as string),
    enabled: !!batchId,
    staleTime: 0,
    refetchOnWindowFocus: false,
    refetchInterval: (query) => (query.state.data?.state === 'completed' ? false : 2000),
  })
}
