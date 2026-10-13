// Coverage Desk API — typed request functions for /api/coverage/*. Hand-written
// interfaces (not generated schema.d.ts) mirror the backend Pydantic models,
// matching the established inline-type pattern for endpoints newer than the last
// `npm run generate:api` (see VersionDiffBanner).

import { BASE_URL } from './client'
import { fetchWithTimeout } from './fetch'
import { FetchHttpError } from '../utils/errorMessage'
import { extractErrorDetail } from './errors'
import type { NumberSource } from '../components/SourcedNumber'

// ── Types (mirror finrobot/coverage/models.py) ───────────────────────────────

export interface CoverageMember {
  ticker: string
  added_at: string
  note: string | null
  priority: number
}

export interface CoverageGroup {
  id: string
  name: string
  description: string | null
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface CoverageGroupSummary extends CoverageGroup {
  member_count: number
}

export interface CoverageGroupDetail extends CoverageGroup {
  members: CoverageMember[]
}

export interface NeedsRefreshReason {
  kind: string
  detail: string
  artifact_id: string | null
}

export type SignalStatus = 'hit' | 'watching' | 'failed'
export type RunStatus = 'created' | 'running' | 'completed' | 'failed'

// What the LIVE price implies, re-solved from the ticker's latest stored DCF
// (mirrors MarketImpliedNature in finrobot/engine/models/financial.py). A
// per-name classification, NOT a cross-name implied-growth ranking — the reverse
// solver fits a flat constant while the forward DCF decays, so a cross-name gap
// would rank growth-curve steepness, not expectation stretch.
export type MarketImpliedKind = 'fundamental' | 'option_value' | 'near_ceiling'

export interface MarketImpliedNature {
  kind: MarketImpliedKind
  // Constant annual revenue growth the live price implies (fundamental only).
  implied_growth: number | null
  implied_wacc: number | null
  horizon_years: number
  // Ceiling context for the unreachable paths (option_value / near_ceiling).
  growth_ceiling: number | null
  ceiling_price: number | null
}

// Per-cell provenance for the numeric columns (mirrors CoverageRowSources in
// finrobot/coverage/models.py). Each slot feeds a <SourcedNumber> popover; a
// null slot (degraded fetch) renders the bare value.
export interface CoverageRowSources {
  price: NumberSource | null
  change_pct_1d: NumberSource | null
  market_cap: NumberSource | null
  revenue_ttm: NumberSource | null
  ev_ebitda: NumberSource | null
  pe: NumberSource | null
  upside_to_target_live: NumberSource | null
  market_implied: NumberSource | null
}

export interface CoverageRow {
  ticker: string
  // Analyst's own-book marker — GLOBAL per ticker (one flag across every group),
  // set from the card footer checkbox via PUT /api/coverage/owned/{ticker}. Also
  // the `owned` axis of the re-run-all filter (mirrors select_targets).
  owned: boolean
  company: string | null
  price: number | null
  change_pct_1d: number | null
  price_as_of: string | null
  // Whether `price` is a live intraday quote, a session close (weekend / after-
  // hours / holiday), or undeterminable — classified server-side at read time
  // against the exchange clock. Drives the card's freshness affordance: a closed
  // market shows a static "Close · date", never a "refreshing"/live pulse.
  session_state: 'live' | 'closed' | 'unknown' | null
  market_cap: number | null
  revenue_ttm: number | null
  ev_ebitda: number | null
  pe: number | null
  currency: string | null
  latest_verdict: string | null
  target_price: number | null
  target_date: string | null
  entry_price: number | null
  upside_to_target_live: number | null
  signal: SignalStatus | null
  // artifact_count = every artifact for the ticker (research + dcf/lbo/comps/…);
  // research_count = only thesis-bearing research (verdict set). The card labels
  // "研报" off research_count so a model run never inflates the report tally.
  artifact_count: number
  research_count: number
  latest_artifact_id: string | null
  latest_type: string | null
  latest_at: string | null
  run_status: RunStatus | null
  run_error: string | null
  // What the live price implies vs the name's stored DCF — null when the ticker
  // has no DCF, no live price, or on the cache-only first paint.
  market_implied: MarketImpliedNature | null
  // The market cells came from a cache snapshot past its freshness TTL — real
  // last-known numbers (rendered with their price_as_of age), NOT pending. The
  // card shows them with a "refreshing" affordance, never a blank shimmer; a
  // background revalidate (refresh=true) replaces them. false = fresh, or a cold
  // row whose market is genuinely absent (price null → shimmer).
  market_stale: boolean
  needs_refresh: NeedsRefreshReason[]
  warnings: string[]
  sources: CoverageRowSources
}

// Result of the destructive "delete ticker" action (mirrors the router's DELETE
// /api/coverage/groups/{id}/members/{ticker}). `removed_from_group` is false when
// the ticker was never a member yet its artifacts were still deleted (idempotent
// cleanup); `artifact_ids` is every row that was removed for the ticker.
export interface CoverageTickerDeletion {
  ticker: string
  removed_from_group: boolean
  artifacts_deleted: number
  artifact_ids: string[]
}

export interface CoverageOverview {
  group_id: string
  group_name: string
  rows: CoverageRow[]
  generated_at: string
  partial: boolean
  // True when assembled from the canonical cache with NO network (the instant
  // first paint). Market cells are last-known snapshots; per-row market_stale
  // flags the ones past TTL. The client revalidates via a refresh=true pass.
  cache_only: boolean
  // True when a network refresh made ZERO price provider calls because every
  // row's market is closed and already at its latest settled close (the calendar
  // no-op). Lets the refresh button confirm "已是最新收盘" instead of implying it
  // pulled live quotes. Always false on the cache-only paint.
  refresh_noop: boolean
}

// ── Re-run-all batch (mirrors finrobot/run_concurrency.py + coverage/batch.py) ─
// The router POSTs the filter selection, then the UI polls the batch progress
// endpoint every 2s until state === 'completed'. Every field the panel renders
// rides here — no second source of truth.

export type CoverageBatchState = 'queued' | 'running' | 'completed'
export type CoverageBatchItemState = 'queued' | 'running' | 'completed' | 'failed'

// One provider's concurrency ceiling (declared) or lack thereof (undeclared).
// `binding` marks the provider that fixed the batch's limit; `source` is the
// human-readable citation (e.g. "moomoo OpenAPI gateway: 4 concurrent
// connections (owner-declared)").
export interface ProviderLimitView {
  provider: string
  max_concurrency: number | null
  source: string | null
  declared: boolean
  binding: boolean
}

export interface CoverageBatchItem {
  ticker: string
  state: CoverageBatchItemState
  run_id: string | null
  error: string | null
}

// The four buckets the panel's rating checkboxes filter on. UNRATED covers both
// "no verdict yet" and legacy non-directional tokens (WITHHELD/REVIEW) — the
// backend select_targets keys off `(verdict or 'UNRATED').upper()`.
export type CoverageRating = 'BUY' | 'HOLD' | 'SELL' | 'UNRATED'

export interface CoverageRerunRequest {
  // null = no ownership filter; true = only owned; false = only not-owned.
  owned: boolean | null
  // null / empty = no rating filter; all four = no filter (equivalent).
  ratings: CoverageRating[] | null
  pipeline_type: string
  language?: 'en' | 'zh' | null
}

export interface CoverageBatchProgress {
  batch_id: string
  group_id: string
  pipeline_type: string
  state: CoverageBatchState
  // In-flight ceiling actually used: min(ceiling, every declared provider limit).
  limit: number
  // The desktop LLM budget (RUN_CEILING) — `limit` may never exceed it.
  ceiling: number
  // The declared provider whose value == limit, else null (then the ceiling binds).
  binding_provider: string | null
  binding_reason: string
  providers: ProviderLimitView[]
  undeclared_count: number
  total: number
  queued: number
  running: number
  completed: number
  failed: number
  items: CoverageBatchItem[]
  created_at: string
}

// ── Requests ─────────────────────────────────────────────────────────────────

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetchWithTimeout(`${BASE_URL}${path}`, init)
  if (!r.ok) {
    // FastAPI ships a 中文 user-facing `detail` on coverage errors (422 ticker
    // 非法 / 已在组内 / 分组名重复, 502 provider 失败, 503 能力未配置). statusText
    // is empty/English under HTTP/2 — read the body once and carry detail into
    // the typed error so mapErrorToUserMessage surfaces the real reason instead
    // of a generic "添加失败" (BUG-053).
    const detail = await extractErrorDetail(r, '')
    throw new FetchHttpError(r.status, r.statusText, detail)
  }
  if (r.status === 204) return undefined as T
  return r.json() as Promise<T>
}

const jsonInit = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const coverageApi = {
  listGroups: () => req<CoverageGroupSummary[]>('/api/coverage/groups'),

  // Auto-add: enrol an opened ticker into the default Studied Tickers workspace
  // (find-or-create, idempotent). The write side of "opening /stocks/:ticker
  // enrols it"; surfaced UI does not expose manual group membership edits.
  addStudiedTicker: (ticker: string) =>
    req<CoverageGroupDetail>('/api/coverage/studied-tickers/members', jsonInit('POST', { ticker })),

  // refresh=false → instant cache-only paint (server reads canonical cache,
  // allow-stale, no network). refresh=true → bounded network revalidate.
  overview: (id: string, refresh = false) => {
    const suffix = refresh ? '?refresh=true' : ''
    return req<CoverageOverview>(`/api/coverage/groups/${id}/overview${suffix}`)
  },

  // Set the global owned flag for one ticker (upsert). Returns the stored value,
  // so the caller can confirm what landed rather than assume the request side.
  setOwned: (ticker: string, owned: boolean) =>
    req<{ ticker: string; owned: boolean }>(
      `/api/coverage/owned/${encodeURIComponent(ticker)}`,
      jsonInit('PUT', { owned }),
    ),

  // Remove a ticker from the group AND delete every stored artifact for it — one
  // destructive action, so the card and its reports leave the desk together.
  // Idempotent: a ticker that was never a member still deletes its artifacts and
  // reports removed_from_group=false (a re-fired cleanup must not 404 halfway).
  deleteTicker: (groupId: string, ticker: string) =>
    req<CoverageTickerDeletion>(
      `/api/coverage/groups/${encodeURIComponent(groupId)}/members/${encodeURIComponent(ticker)}`,
      { method: 'DELETE' },
    ),

  // Kick off a filtered re-run of every matching card. Returns the initial batch
  // progress (state 'queued'|'running'); the client then polls batchProgress.
  rerunAll: (groupId: string, body: CoverageRerunRequest) =>
    req<CoverageBatchProgress>(`/api/coverage/groups/${groupId}/rerun`, jsonInit('POST', body)),

  batchProgress: (batchId: string) =>
    req<CoverageBatchProgress>(`/api/coverage/batches/${encodeURIComponent(batchId)}`),
}
