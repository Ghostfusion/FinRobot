// Coverage card sorting — pure, so it unit-tests without the DOM, and the page
// and store share one definition of "what's sortable" and "how nulls sort". The
// page exposes a small sort box (needs-attention / name / rating / ownership + a
// direction toggle) and persists the pick in coverageStore; the boxed keys are a
// deliberate subset of what this core can order (see SORT_SELECT_KEYS in
// CoveragePage).
//
// `owned` is the one COMPOUND key — it orders by the flag first and then by name
// ascending, so picking it groups your holdings at the top of the wall
// alphabetically rather than merely ranking ticked cards above unticked ones.
//
// Missing values (null/undefined) always sink to the bottom regardless of
// direction: an analyst scanning a column wants the real numbers grouped at the
// top, never a wall of "—" pushed up by an ascending sort. `rating` reuses that
// rule — an unrated name (no verdict / legacy WITHHELD) has no rank and sinks.

import type { CoverageRow } from '../../api/coverage'
import { coveragePriority } from './coveragePriority'

export type CoverageSortKey =
  | 'needs_action'
  | 'ticker'
  | 'latest_report'
  | 'upside_to_target_live'
  | 'price'
  | 'change_pct_1d'
  | 'market_cap'
  | 'revenue_ttm'
  | 'ev_ebitda'
  | 'pe'
  | 'artifact_count'
  | 'rating'
  | 'owned'

export type SortDir = 'asc' | 'desc'

export interface CoverageSort {
  key: CoverageSortKey
  dir: SortDir
}

// Every key the sort core can order — the runtime complement to CoverageSortKey,
// used by normaliseCoverageSort to reject a stale/hand-edited persisted value
// (a renamed key would otherwise leave the wall in whatever order it loaded).
const SORT_KEYS: Record<CoverageSortKey, true> = {
  needs_action: true,
  ticker: true,
  latest_report: true,
  upside_to_target_live: true,
  price: true,
  change_pct_1d: true,
  market_cap: true,
  revenue_ttm: true,
  ev_ebitda: true,
  pe: true,
  artifact_count: true,
  rating: true,
  owned: true,
}

// Verdict → rank. Direction is the caller's: asc = BUY, HOLD, SELL (best first);
// desc flips it. Anything not here (null, WITHHELD/REVIEW, a future token) has no
// rank and sorts as null → bottom in BOTH directions (the file's null rule).
const RATING_RANK: Record<string, number> = { BUY: 0, HOLD: 1, SELL: 2 }

// The comparable scalar for a row under a given key. Derived keys
// (needs_action → priority score, latest_report → epoch ms, rating → verdict
// rank) compute here so the sort core stays a single null-aware compare.
function sortValue(row: CoverageRow, key: CoverageSortKey): number | string | null {
  if (key === 'needs_action') return coveragePriority(row).score
  if (key === 'latest_report') return row.latest_at ? Date.parse(row.latest_at) : null
  if (key === 'rating') return RATING_RANK[(row.latest_verdict ?? '').toUpperCase()] ?? null
  if (key === 'ticker') return row.ticker
  // `owned` is answered by sortCoverageRows' own compound comparator before the
  // generic path, so it never arrives here — returned as a null rather than
  // `row[key]` (a boolean) to keep this function's scalar type honest.
  if (key === 'owned') return null
  return row[key]
}

/**
 * Coerce a persisted / unknown value into a valid sort or null. The page falls
 * back to its DEFAULT_SORT on null, so a stale key in localStorage (renamed,
 * removed, or hand-edited) can never render the wall in an unknown order — it
 * degrades to the resting needs-attention order instead. Returns null for
 * anything that isn't a well-formed `{ key: CoverageSortKey, dir: 'asc'|'desc' }`.
 */
export function normaliseCoverageSort(value: unknown): CoverageSort | null {
  if (!value || typeof value !== 'object') return null
  const { key, dir } = value as { key?: unknown; dir?: unknown }
  if (typeof key !== 'string' || SORT_KEYS[key as CoverageSortKey] !== true) return null
  if (dir !== 'asc' && dir !== 'desc') return null
  return { key: key as CoverageSortKey, dir }
}

export function sortCoverageRows(rows: CoverageRow[], sort: CoverageSort | null): CoverageRow[] {
  if (!sort) return rows
  const { key, dir } = sort
  const factor = dir === 'asc' ? 1 : -1
  // The compound key: flag first, then name ASCENDING inside each group. `dir`
  // flips the GROUPS only (desc = owned first, the direction this key is picked
  // with) — the grouping is the point of the key, so a name-descending tail on a
  // flipped ownership sort would be an odd thing to hand the user. Name order
  // uses the same localeCompare the `ticker` key does, so "A→Z" means one thing
  // everywhere on this screen.
  if (key === 'owned') {
    const ownedFirst = dir !== 'asc'
    return [...rows].sort((a, b) => {
      const rankA = a.owned ? 0 : 1
      const rankB = b.owned ? 0 : 1
      if (rankA !== rankB) return ownedFirst ? rankA - rankB : rankB - rankA
      return a.ticker.localeCompare(b.ticker)
    })
  }
  return [...rows].sort((a, b) => {
    const av = sortValue(a, key)
    const bv = sortValue(b, key)
    const aNull = av === null || av === undefined || (typeof av === 'number' && Number.isNaN(av))
    const bNull = bv === null || bv === undefined || (typeof bv === 'number' && Number.isNaN(bv))
    if (aNull && bNull) return 0
    if (aNull) return 1 // a sinks regardless of dir
    if (bNull) return -1
    if (key === 'ticker') return factor * String(av).localeCompare(String(bv))
    return factor * ((av as number) - (bv as number))
  })
}
