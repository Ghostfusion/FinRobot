// CoverageRerunPanel — the coverage desk's re-run surface: "re-run all reports"
// with filters (owned + rating), or the readout for a batch the caller already
// started from the per-card "Re-run" ticks ("re-run selected"), plus a live
// batch-progress readout either way. Opened from the CoveragePage header rail.
//
// The filter predicate here is the ONE definition the submit count and the POST
// body both use, and it mirrors the backend's `select_targets` exactly:
//   owned   : null → no ownership filter; true → only owned; false → only not-owned
//   ratings : null/empty → no rating filter; else keep rows whose
//             `(latest_verdict or 'UNRATED').upper()` is in the set
// "All four ratings selected" is normalised to null (no filter) — the backend
// treats it the same, so we don't send the redundant superset.
//
// After POST the panel polls GET /api/coverage/batches/{id} every 2s (the
// `useCoverageBatch` query owns the interval + the stop condition) until the
// batch is `completed`, then asks the page to refetch the overview so the cards
// pick up the new run status.

import { useEffect, useMemo, useRef, useState } from 'react'
import { useI18n } from '../../i18n'
import type {
  CoverageBatchItemState,
  CoverageBatchProgress,
  CoverageRating,
  CoverageRow,
} from '../../api/coverage'
import { useCoverageBatch, useRerunAll } from '../../hooks/useCoverage'

// Filter order shown in the UI (and the order the ratings are POSTed in).
export const RERUN_RATINGS: readonly CoverageRating[] = ['BUY', 'HOLD', 'SELL', 'UNRATED']

export interface RerunFilters {
  owned: boolean | null
  ratings: CoverageRating[] | null
}

// Normalise the UI's raw checkbox state into the wire filter: all-or-none
// ratings collapse to null (no filter); otherwise only the chosen subset.
export function rerunFilters(
  ownedOnly: boolean,
  selected: ReadonlySet<CoverageRating>,
): RerunFilters {
  const chosen = RERUN_RATINGS.filter((r) => selected.has(r))
  const ratings = chosen.length === 0 || chosen.length === RERUN_RATINGS.length ? null : [...chosen]
  return { owned: ownedOnly ? true : null, ratings }
}

/** The shared predicate — MUST stay in lockstep with backend select_targets. */
export function matchesRerunFilters(row: CoverageRow, filters: RerunFilters): boolean {
  if (filters.owned !== null && row.owned !== filters.owned) return false
  if (filters.ratings === null || filters.ratings.length === 0) return true
  const verdict = (row.latest_verdict ?? 'UNRATED').toUpperCase()
  return filters.ratings.some((r) => r === verdict)
}

/** How many loaded cards the current filters would re-run (drives the button). */
export function countRerunTargets(rows: CoverageRow[], filters: RerunFilters): number {
  let n = 0
  for (const row of rows) if (matchesRerunFilters(row, filters)) n += 1
  return n
}

// Static label lookups (kept as literal-key maps so the i18n orphan check sees
// every id referenced).
const RATING_LABEL_KEY: Record<CoverageRating, string> = {
  BUY: 'coverage.rerun.rating.buy',
  HOLD: 'coverage.rerun.rating.hold',
  SELL: 'coverage.rerun.rating.sell',
  UNRATED: 'coverage.rerun.rating.unrated',
}

const STATE_LABEL_KEY: Record<CoverageBatchItemState, string> = {
  queued: 'coverage.rerun.state.queued',
  running: 'coverage.rerun.state.running',
  completed: 'coverage.rerun.state.completed',
  failed: 'coverage.rerun.state.failed',
}

// A batch the CALLER already started (the rail's "re-run selected" fires on click
// rather than from this panel's submit). The ticker set rides along because the
// progress payload only lands after the first poll — the panel must be able to say
// what it is watching before then.
export interface StartedBatch {
  batchId: string
  tickers: string[]
}

interface Props {
  groupId: string
  // The rows the cards currently show — the count is computed from these, so the
  // button's number always matches what the user sees on the wall.
  rows: CoverageRow[]
  onClose: () => void
  // Fired once when the polled batch reaches `completed` — the page refetches
  // the overview so the cards pick up the new run status.
  onCompleted?: () => void
  // Already-started batch to watch (see StartedBatch). Present → the filter UI is
  // replaced by the explicit ticker set: `owned`/`ratings` describe a predicate
  // over the wall, which cannot express "these three cards".
  startedBatch?: StartedBatch | null
}

export function CoverageRerunPanel({
  groupId,
  rows,
  onClose,
  onCompleted,
  startedBatch = null,
}: Props): React.ReactElement {
  const { t } = useI18n()
  const [ownedOnly, setOwnedOnly] = useState(false)
  // Default: every rating bucket selected — i.e. no rating filter.
  const [selected, setSelected] = useState<ReadonlySet<CoverageRating>>(
    () => new Set(RERUN_RATINGS),
  )
  const [batchId, setBatchId] = useState<string | null>(null)

  const rerun = useRerunAll(groupId)
  // The batch to poll: the one the caller started, else the one submit started.
  const watchedBatchId = startedBatch?.batchId ?? batchId
  const batchQuery = useCoverageBatch(watchedBatchId)
  const batch = batchQuery.data
  const title = startedBatch ? t('coverage.rerunSelected.title') : t('coverage.rerun.title')

  const filters = useMemo(() => rerunFilters(ownedOnly, selected), [ownedOnly, selected])
  const matchCount = useMemo(() => countRerunTargets(rows, filters), [rows, filters])

  // Refetch the overview ONCE per completed batch (the poll can re-render after
  // completion; onCompleted is an inline prop whose identity changes each render,
  // so a bare effect dep would re-fire it).
  const completedRef = useRef<string | null>(null)
  useEffect(() => {
    if (!batch || batch.state !== 'completed') return
    if (completedRef.current === batch.batch_id) return
    completedRef.current = batch.batch_id
    onCompleted?.()
  }, [batch, onCompleted])

  const toggleRating = (rating: CoverageRating) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(rating)) next.delete(rating)
      else next.add(rating)
      return next
    })
  }

  const handleSubmit = () => {
    if (rerun.isPending || matchCount === 0) return
    rerun.mutate(
      { owned: filters.owned, ratings: filters.ratings, pipeline_type: 'research', language: null },
      { onSuccess: (progress) => setBatchId(progress.batch_id) },
    )
  }

  return (
    <div
      data-testid="coverage-rerun-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 60,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: 90,
        background: 'rgba(0,0,0,0.45)',
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        data-testid="coverage-rerun-panel"
        // Clicks inside the panel must not reach the backdrop's close handler.
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 460,
          maxWidth: 'calc(100vw - 32px)',
          maxHeight: 'calc(100vh - 140px)',
          overflow: 'auto',
          padding: '18px 20px',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-soft)',
          background: 'var(--bg-elevated, var(--bg-card-overlay))',
          boxShadow: '0 24px 60px rgba(0,0,0,0.5)',
          fontFamily: 'var(--font-body)',
        }}
      >
        <header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 14,
          }}
        >
          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: '0.02em',
              color: 'var(--text-primary)',
            }}
          >
            {title}
          </span>
          <button
            type="button"
            data-testid="coverage-rerun-close"
            onClick={onClose}
            aria-label={t('coverage.rerun.close')}
            className="coverage-hover-btn"
            style={{
              padding: '3px 9px',
              borderRadius: 'var(--radius-pill)',
              border: '1px solid var(--border-soft)',
              background: 'transparent',
              color: 'var(--text-secondary)',
              fontSize: 11,
              cursor: 'pointer',
            }}
          >
            {t('coverage.rerun.close')}
          </button>
        </header>

        {/* Filters + submit — the "re-run all" mode. A caller-started batch is an
            explicit SET, which no predicate can express, so this whole block gives
            way to the ticker list below it. */}
        {!startedBatch && (
          <>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 12,
                fontSize: 12,
                color: 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={ownedOnly}
                onChange={(e) => setOwnedOnly(e.target.checked)}
                style={{ margin: 0, width: 13, height: 13, accentColor: 'var(--accent-cyan)' }}
              />
              {t('coverage.rerun.ownedOnly')}
            </label>

            <div style={{ marginBottom: 8, fontSize: 11, color: 'var(--text-muted)' }}>
              {t('coverage.rerun.ratings')}
            </div>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '8px 16px',
                marginBottom: 18,
              }}
            >
              {RERUN_RATINGS.map((rating) => (
                <label
                  key={rating}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    fontSize: 12,
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(rating)}
                    onChange={() => toggleRating(rating)}
                    style={{ margin: 0, width: 13, height: 13, accentColor: 'var(--accent-cyan)' }}
                  />
                  {t(RATING_LABEL_KEY[rating])}
                </label>
              ))}
            </div>

            <button
              type="button"
              data-testid="coverage-rerun-submit"
              onClick={handleSubmit}
              disabled={rerun.isPending || matchCount === 0}
              className="btn-shimmer"
              style={{
                width: '100%',
                padding: '8px 16px',
                fontSize: 12,
                opacity: rerun.isPending || matchCount === 0 ? 0.55 : 1,
                cursor: rerun.isPending || matchCount === 0 ? 'default' : 'pointer',
              }}
            >
              {rerun.isPending
                ? t('coverage.rerun.submitting')
                : t('coverage.rerun.submit', { n: matchCount })}
            </button>

            {rerun.isError && (
              <div
                data-testid="coverage-rerun-start-error"
                style={{ marginTop: 10, color: 'var(--danger)', fontSize: 11 }}
              >
                {t('coverage.rerun.startFailed')}
              </div>
            )}
          </>
        )}

        {/* The explicit set a caller-started batch is running: what the readout
            below is counting, before the first poll lands. */}
        {startedBatch && (
          <div data-testid="coverage-rerun-selected-set" style={{ marginBottom: 4 }}>
            <div style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>
              {t('coverage.rerunSelected.set', { n: startedBatch.tickers.length })}
            </div>
            <div
              style={{
                marginTop: 4,
                fontFamily: 'var(--font-mono)',
                fontSize: 11.5,
                color: 'var(--text-muted)',
                wordBreak: 'break-word',
              }}
            >
              {startedBatch.tickers.join(' · ')}
            </div>
          </div>
        )}

        {batch && <BatchProgress progress={batch} />}
        {batchQuery.isError && watchedBatchId && (
          <div
            data-testid="coverage-rerun-progress-error"
            style={{ marginTop: 12, color: 'var(--danger)', fontSize: 11 }}
          >
            {t('coverage.rerun.progressFailed')}
          </div>
        )}
      </div>
    </div>
  )
}

// The live readout: aggregate counts, the detected cap + its binder, and the
// per-ticker item list.
function BatchProgress({ progress }: { progress: CoverageBatchProgress }): React.ReactElement {
  const { t } = useI18n()
  return (
    <div
      data-testid="coverage-rerun-progress"
      style={{ marginTop: 16, borderTop: '1px solid var(--border-faint)', paddingTop: 12 }}
    >
      <div
        data-testid="coverage-rerun-counts"
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 11.5,
          color: 'var(--text-secondary)',
          marginBottom: 6,
        }}
      >
        {t('coverage.rerun.counts', {
          queued: progress.queued,
          running: progress.running,
          completed: progress.completed,
          failed: progress.failed,
        })}
      </div>
      <div
        data-testid="coverage-rerun-cap"
        title={progress.binding_reason}
        style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}
      >
        {t('coverage.rerun.cap', { n: progress.limit })}
        {' · '}
        {progress.binding_provider
          ? t('coverage.rerun.boundBy', { provider: progress.binding_provider })
          : t('coverage.rerun.boundByCeiling')}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 10 }}>
        {progress.binding_reason}
      </div>
      <ul
        data-testid="coverage-rerun-items"
        style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 4 }}
      >
        {progress.items.map((item) => (
          <li
            key={item.ticker}
            data-testid={`coverage-rerun-item-${item.ticker}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 10,
              fontFamily: 'var(--font-mono)',
              fontSize: 11.5,
              color: 'var(--text-secondary)',
            }}
          >
            <span>{item.ticker}</span>
            <span
              data-state={item.state}
              style={{ color: item.state === 'failed' ? 'var(--danger)' : 'var(--text-muted)' }}
              title={item.error ?? undefined}
            >
              {t(STATE_LABEL_KEY[item.state])}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
