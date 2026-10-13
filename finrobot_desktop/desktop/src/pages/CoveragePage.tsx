// CoveragePage — the coverage archive / management route (`/coverage`). The
// search-first homepage lives at `/research`; this screen is the studied ticker
// desk: a wall of ticker cards plus a slim header rail. The whole studied
// universe is always shown, but the rail now carries the controls the owner
// asked for: a sort box (needs-attention / name / rating + a direction toggle),
// a "re-run all" button, and the manual refresh. The cards self-report verdict,
// freshness, and an amber edge when one needs attention. There is ONE surfaced
// list — Studied Tickers (the system coverage group); multi-group machinery stays
// backend-only. Card click opens `/stocks/:ticker`, where research runs and
// artifact history live.
//
// A ticker is the primary object: a live market snapshot AND many research
// artifacts. The card shows the snapshot + latest verdict + report count; the
// detail workspace owns running research and reviewing historical runs.

import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n'
import { useCoverageStore } from '../stores/coverageStore'
import { useCoverageGroups, useCoverageOverview, useSetOwned } from '../hooks/useCoverage'
import { CoverageEmptyState } from '../components/coverage/CoverageEmptyState'
import { CoverageCardGrid } from '../components/coverage/CoverageCardGrid'
import { CoverageRerunPanel } from '../components/coverage/CoverageRerunPanel'
import {
  normaliseCoverageSort,
  sortCoverageRows,
  type CoverageSort,
  type CoverageSortKey,
  type SortDir,
} from '../components/coverage/coverageSort'

// Resting order (no persisted choice yet): most-urgent first, so the names that
// need the analyst surface at the top of the wall.
const DEFAULT_SORT: CoverageSort = { key: 'needs_action', dir: 'desc' }

// The three keys the sort box exposes (a deliberate subset of CoverageSortKey).
// `defaultDir` is the direction a key snaps to when picked, so "rating" opens
// best-first (BUY first) rather than inheriting the needs-attention desc.
const SORT_SELECT_KEYS: readonly CoverageSortKey[] = ['needs_action', 'ticker', 'rating']
const SORT_KEY_LABEL: Record<string, string> = {
  needs_action: 'coverage.sort.needsAction',
  ticker: 'coverage.sort.name',
  rating: 'coverage.sort.rating',
}
const SORT_DEFAULT_DIR: Partial<Record<CoverageSortKey, SortDir>> = {
  needs_action: 'desc',
  ticker: 'asc',
  rating: 'asc',
}

export function CoveragePage(): React.ReactElement {
  const { t } = useI18n()
  const navigate = useNavigate()

  const groupsQuery = useCoverageGroups()
  const groups = groupsQuery.data ?? []

  // One shipped density (comfort). The toggle was cut; the store field stays so
  // the card/grid sizing props keep working, pinned to comfort.
  const density = useCoverageStore((s) => s.density)

  // Card sort — persisted view-state. The stored value is normalised on read, so
  // a stale/unknown persisted key falls back to DEFAULT_SORT instead of leaving
  // the wall in an undefined order.
  const storedSort = useCoverageStore((s) => s.sort)
  const setSort = useCoverageStore((s) => s.setSort)
  const sort = useMemo(() => normaliseCoverageSort(storedSort) ?? DEFAULT_SORT, [storedSort])

  // Global owned flag writes. In-flight is scoped to the clicked ticker so only
  // that card's checkbox locks (the mutation carries its variables).
  const setOwned = useSetOwned()
  const ownedPendingTicker = setOwned.isPending ? (setOwned.variables?.ticker ?? null) : null

  // "Re-run all" panel visibility.
  const [rerunOpen, setRerunOpen] = useState(false)

  // Market-degraded retry bar (BUG-032): the cache-only paint filled the table
  // but the network revalidate failed, so the numbers are last-known (possibly
  // stale), not fresh. We surface a dismissible retry bar; dismissal is sticky
  // until a fresh failure (the marketError → false → true transition re-shows it).
  const [marketRetryDismissed, setMarketRetryDismissed] = useState(false)

  // The single surfaced list is the system "Studied Tickers" group; there is no
  // group switcher in the UX. Fall back to the first group only if the system
  // flag isn't present (older seed).
  const activeGroup = groups.find((g) => g.is_system) ?? groups[0]
  const activeGroupId = activeGroup?.id ?? null

  const overviewQuery = useCoverageOverview(activeGroupId)
  const rows = useMemo(() => overviewQuery.data?.rows ?? [], [overviewQuery.data])

  // The whole universe, always — ordered by the persisted sort box (default
  // urgent-first) for a stable, useful wall.
  const visibleRows = useMemo(() => sortCoverageRows(rows, sort), [rows, sort])

  // Re-arm the market-degraded retry bar on each fresh failure: when marketError
  // flips false→true (e.g. a retry failed again, or a new group's revalidate
  // fails), clear a prior dismissal so the user sees it again.
  const prevMarketErrorRef = useRef(false)
  useEffect(() => {
    if (overviewQuery.marketError && !prevMarketErrorRef.current) setMarketRetryDismissed(false)
    prevMarketErrorRef.current = overviewQuery.marketError
  }, [overviewQuery.marketError])

  // ── Groups still loading → full-page placeholder, NOT a false empty state ──
  // Cold start: while groups load, activeGroupId is null → useCoverageOverview
  // is disabled → in TanStack v5 a disabled query reports isLoading=false, so
  // rows=[] would fall into the rows.length===0 empty state ("还没有 ticker")
  // and flash "no coverage" to a user who actually has coverage (UX-007). Gate
  // the whole page on the groups load instead.
  if (groupsQuery.isLoading) {
    return (
      <div style={{ height: '100%', padding: '20px 24px' }}>
        <Placeholder text={t('coverage.loading')} />
      </div>
    )
  }

  // ── Groups request failed → error state, NOT the starter ──────────────────
  if (groupsQuery.isError) {
    return (
      <ErrorState
        message={t('coverage.error.groupsFailed')}
        retryLabel={t('coverage.error.retry')}
        onRetry={() => void groupsQuery.refetch()}
      />
    )
  }

  // ── No coverage yet → archive-empty state ────────────────────────────────
  // Loading + error are handled above, so reaching here means groups resolved
  // to empty. Research starts from `/research`; this route stays the management
  // surface and points the user back to the search-first entry.
  if (groups.length === 0) {
    return <CoverageEmptyState />
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        padding: '20px 24px',
      }}
    >
      {/* Header rail — the sort box on the left; the re-run-all + refresh
          controls on the right. The refresh button re-runs the network
          revalidate; backend single-flight + the calendar no-op make a
          closed-market refresh free, so it can't be abused. */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          marginBottom: 14,
          flexShrink: 0,
        }}
      >
        <CoverageSortControl sort={sort} onChange={(next) => setSort(next)} />

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            type="button"
            data-testid="coverage-rerun-open"
            onClick={() => setRerunOpen(true)}
            className="coverage-hover-btn"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 7,
              padding: '6px 13px',
              borderRadius: 'var(--radius-pill)',
              fontFamily: 'var(--font-mono)',
              fontSize: 11.5,
              fontWeight: 500,
              letterSpacing: '0.04em',
              background: 'var(--bg-card-overlay)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-soft)',
              cursor: 'pointer',
            }}
          >
            {t('coverage.rerun.button')}
          </button>
          <CoverageRefreshControl
            refreshing={overviewQuery.refreshing}
            noop={overviewQuery.refreshNoop}
            onRefresh={() => overviewQuery.refetch()}
          />
        </div>
      </div>

      {/* Market-degraded retry bar (BUG-032): the table is alive (cache-only
          paint) but the network revalidate failed, so the numbers are last-known
          (possibly stale), not fresh. Offer a retry on the revalidate query and
          let the user dismiss the bar. */}
      {overviewQuery.marketError && !marketRetryDismissed && (
        <MarketRetryBar
          message={t('coverage.error.marketFailed')}
          retryLabel={t('coverage.error.retry')}
          dismissLabel={t('coverage.error.dismiss')}
          onRetry={() => overviewQuery.refetch()}
          onDismiss={() => setMarketRetryDismissed(true)}
        />
      )}

      {/* Card wall — every card is a direct link to the ticker workspace. */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          minWidth: 0,
        }}
      >
        {overviewQuery.isLoading ? (
          <Placeholder text={t('coverage.loading')} />
        ) : overviewQuery.isError ? (
          <ErrorState
            message={t('coverage.error.overviewFailed')}
            retryLabel={t('coverage.error.retry')}
            onRetry={() => void overviewQuery.refetch()}
          />
        ) : rows.length === 0 ? (
          <Placeholder text={t('coverage.emptyGroup')} />
        ) : (
          <CoverageCardGrid
            rows={visibleRows}
            density={density}
            marketPending={overviewQuery.marketPending}
            onOpen={(ticker) => navigate(`/stocks/${ticker}`)}
            onSetOwned={(ticker, owned) => setOwned.mutate({ ticker, owned })}
            ownedPendingTicker={ownedPendingTicker}
          />
        )}
      </div>

      {rerunOpen && activeGroupId && (
        <CoverageRerunPanel
          groupId={activeGroupId}
          rows={rows}
          onClose={() => setRerunOpen(false)}
          // The batch flipped the rows' run_state server-side; refetch so the
          // cards pick up the new status instead of the pre-run snapshot.
          onCompleted={() => overviewQuery.refetch()}
        />
      )}
    </div>
  )
}

// Sort box — a labelled select (exactly the three surfaced keys) plus a
// direction toggle. The direction snaps to the key's sensible default on pick
// (name/rating ascend, needs-attention descends), and the toggle flips it.
function CoverageSortControl({
  sort,
  onChange,
}: {
  sort: CoverageSort
  onChange: (sort: CoverageSort) => void
}): React.ReactElement {
  const { t } = useI18n()
  // A key outside the three (never produced by this control, but defensively
  // possible from a hand-edited store) renders as needs-attention rather than a
  // blank select.
  const value: CoverageSortKey = SORT_SELECT_KEYS.includes(sort.key) ? sort.key : 'needs_action'

  return (
    <div
      data-testid="coverage-sort"
      style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}
    >
      <label
        htmlFor="coverage-sort-select"
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          letterSpacing: '0.03em',
          color: 'var(--text-muted)',
        }}
      >
        {t('coverage.sort.label')}
      </label>
      <select
        id="coverage-sort-select"
        data-testid="coverage-sort-select"
        value={value}
        aria-label={t('coverage.sort.aria')}
        onChange={(e) => {
          const key = e.target.value as CoverageSortKey
          onChange({ key, dir: SORT_DEFAULT_DIR[key] ?? 'asc' })
        }}
        style={{
          padding: '5px 9px',
          borderRadius: 'var(--radius-pill)',
          border: '1px solid var(--border-soft)',
          background: 'var(--bg-card-overlay)',
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-mono)',
          fontSize: 11.5,
          cursor: 'pointer',
        }}
      >
        {SORT_SELECT_KEYS.map((key) => (
          <option key={key} value={key}>
            {t(SORT_KEY_LABEL[key])}
          </option>
        ))}
      </select>
      <button
        type="button"
        data-testid="coverage-sort-dir"
        onClick={() => onChange({ key: sort.key, dir: sort.dir === 'asc' ? 'desc' : 'asc' })}
        aria-label={t('coverage.sort.dirToggle')}
        title={sort.dir === 'asc' ? t('coverage.sort.dirAsc') : t('coverage.sort.dirDesc')}
        className="coverage-hover-btn"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 28,
          height: 26,
          padding: 0,
          borderRadius: 'var(--radius-pill)',
          border: '1px solid var(--border-soft)',
          background: 'var(--bg-card-overlay)',
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-mono)',
          fontSize: 12,
          cursor: 'pointer',
        }}
      >
        {sort.dir === 'asc' ? '↑' : '↓'}
      </button>
    </div>
  )
}

// Manual refresh control. Re-runs the network revalidate and confirms the
// outcome inline: "Refreshing…" while in flight, then a transient "Up to date ·
// market closed" (the calendar no-op — closed market, already at the latest
// settled close, zero provider calls) or "Updated" (live numbers pulled). The
// confirmation only fires for a USER click (clickedRef), so the initial
// background revalidate doesn't flash one. No timezone math here: the no-op
// verdict is decided server-side against each exchange's clock.
function CoverageRefreshControl({
  refreshing,
  noop,
  onRefresh,
}: {
  refreshing: boolean
  noop: boolean
  onRefresh: () => void
}): React.ReactElement {
  const { t } = useI18n()
  const clickedRef = useRef(false)
  const prevRefreshing = useRef(refreshing)
  const [outcome, setOutcome] = useState<'upToDate' | 'updated' | null>(null)

  // A refresh the user triggered just finished → confirm its outcome briefly.
  useEffect(() => {
    if (prevRefreshing.current && !refreshing && clickedRef.current) {
      clickedRef.current = false
      setOutcome(noop ? 'upToDate' : 'updated')
    }
    prevRefreshing.current = refreshing
  }, [refreshing, noop])

  // Auto-clear the transient confirmation.
  useEffect(() => {
    if (!outcome) return
    const id = window.setTimeout(() => setOutcome(null), 2600)
    return () => window.clearTimeout(id)
  }, [outcome])

  const handleClick = () => {
    if (refreshing) return
    setOutcome(null)
    clickedRef.current = true
    onRefresh()
  }

  const statusText = refreshing
    ? t('coverage.refresh.refreshing')
    : outcome === 'upToDate'
      ? t('coverage.refresh.upToDate')
      : outcome === 'updated'
        ? t('coverage.refresh.updated')
        : null

  return (
    <div data-testid="coverage-refresh" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {statusText && (
        <span
          data-testid="coverage-refresh-status"
          aria-live="polite"
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            letterSpacing: '0.02em',
            color: outcome === 'updated' ? 'var(--accent-cyan)' : 'var(--text-muted)',
          }}
        >
          {statusText}
        </span>
      )}
      <button
        type="button"
        data-testid="coverage-refresh-btn"
        onClick={handleClick}
        disabled={refreshing}
        aria-label={t('coverage.refresh.aria')}
        className="coverage-hover-btn"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 7,
          padding: '6px 13px',
          borderRadius: 'var(--radius-pill)',
          fontFamily: 'var(--font-mono)',
          fontSize: 11.5,
          fontWeight: 500,
          letterSpacing: '0.04em',
          background: 'var(--bg-card-overlay)',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border-soft)',
          cursor: refreshing ? 'default' : 'pointer',
          opacity: refreshing ? 0.6 : 1,
        }}
      >
        <svg
          width="13"
          height="13"
          viewBox="0 0 14 14"
          fill="none"
          aria-hidden="true"
          style={refreshing ? { animation: 'spin 0.8s linear infinite' } : undefined}
        >
          <path
            d="M12.4 7a5.4 5.4 0 1 1-1.55-3.8M12.5 1.4V4H9.9"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {t('coverage.refresh.button')}
      </button>
    </div>
  )
}

function Placeholder({ text }: { text: string }): React.ReactElement {
  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
      }}
    >
      {text}
    </div>
  )
}

// Error state — distinct from the empty state on purpose (BUG-051): a request
// FAILURE must never look like "no data". Offers a retry.
function ErrorState({
  message,
  retryLabel,
  onRetry,
}: {
  message: string
  retryLabel: string
  onRetry: () => void
}): React.ReactElement {
  return (
    <div
      data-testid="coverage-error"
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        color: 'var(--danger)',
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
        textAlign: 'center',
        padding: 24,
      }}
    >
      <span>{message}</span>
      <button
        type="button"
        onClick={onRetry}
        className="btn-shimmer"
        style={{ padding: '6px 16px', fontSize: 11 }}
      >
        {retryLabel}
      </button>
    </div>
  )
}

// Slim inline bar shown when the cache-only paint stands in but the network
// revalidate failed (BUG-032). Retry re-runs the revalidate; dismiss hides the
// bar (the numbers stay last-known either way).
function MarketRetryBar({
  message,
  retryLabel,
  dismissLabel,
  onRetry,
  onDismiss,
}: {
  message: string
  retryLabel: string
  dismissLabel: string
  onRetry: () => void
  onDismiss: () => void
}): React.ReactElement {
  return (
    <div
      data-testid="coverage-market-retry"
      style={{
        display: 'flex',
        flexShrink: 0,
        alignItems: 'center',
        gap: 12,
        marginBottom: 12,
        padding: '8px 14px',
        border: '1px solid var(--danger)',
        borderRadius: 'var(--radius-md)',
        background: 'var(--danger-soft)',
        color: 'var(--text-secondary)',
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
      }}
    >
      <span style={{ flex: 1, minWidth: 0 }}>{message}</span>
      <button
        type="button"
        onClick={onRetry}
        className="btn-shimmer"
        style={{ padding: '4px 12px', fontSize: 11, flexShrink: 0 }}
      >
        {retryLabel}
      </button>
      <button
        type="button"
        onClick={onDismiss}
        aria-label={dismissLabel}
        title={dismissLabel}
        style={{
          flexShrink: 0,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 22,
          height: 22,
          padding: 0,
          border: 'none',
          background: 'transparent',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
        }}
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path
            d="M2.5 2.5l7 7M9.5 2.5l-7 7"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
      </button>
    </div>
  )
}
