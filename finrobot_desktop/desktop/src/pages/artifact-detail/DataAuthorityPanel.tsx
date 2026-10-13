// Metric-authority decision record — the "what else was on the table" surface.
//
// The data layer reconciles the same metric from several vendors and persists ONE
// reconciliation report per run (`raw_data.data_authority`, mirroring
// finrobot.engine.models.metric_authority.ReconciliationReport). A conflicting
// value is PUBLISHED, never averaged and never withheld: the canonical value
// stands and this record shows who else disagreed, by how much, and on what
// grounds the canonical one won. This panel is that record — REFERENCE material,
// not an alarm (the numeric-audit banner carries the alarm).
//
// It renders NOTHING when the block is absent (every artifact written before the
// field existed), and every field is read defensively: the artifact payload is
// `dict[str, Any]`, so a missing / null / wrong-typed field must degrade, never
// crash the reader. Reuses the report's existing collapsible treatment (native
// <details>, as in ComputeWarningsPanel) — no new page, no new nav entry.

import { useI18n } from '../../i18n'
import {
  formatCompactNumber,
  formatCurrency,
  formatNumberAuto,
  formatPercent,
} from '../../utils/format'

/** One vendor's value for the same metric, as recorded by the resolver. */
export interface DataAuthorityCandidate {
  source: string
  value: number | null
  /** False when the observation was never numerically comparable (rule 1) or
   *  failed hard validity (rule 2) — then `deviation_pct` is null. */
  eligible: boolean
  /** Relative deviation vs the selected value; null when not compared. */
  deviation_pct: number | null
  reason_code: string
}

/** One metric's resolved decision. */
export interface DataAuthorityDecision {
  metric: string
  status: string
  value: number | null
  unit: string
  currency: string | null
  selected_source: string | null
  is_authoritative: boolean
  reason_code: string
  /** The registry row's basis, verbatim (period + caliber). */
  basis: string
  disagreement_pct: number | null
  candidates: DataAuthorityCandidate[]
}

export interface DataAuthorityRecord {
  policy_version: string | null
  decisions: DataAuthorityDecision[]
}

// ── Defensive parsing ────────────────────────────────────────────────────────
// The payload crosses the backend boundary as an untyped dict; every accessor
// below tolerates a missing / null / wrong-typed field instead of asserting.

function asRecord(v: unknown): Record<string, unknown> | null {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : null
}

function asString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

function asNullableString(v: unknown): string | null {
  return typeof v === 'string' && v !== '' ? v : null
}

function asNumber(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

function parseCandidate(raw: unknown): DataAuthorityCandidate | null {
  const r = asRecord(raw)
  if (!r) return null
  const source = asString(r.source)
  if (!source) return null
  return {
    source,
    value: asNumber(r.value),
    eligible: r.eligible === true,
    deviation_pct: asNumber(r.deviation_pct),
    reason_code: asString(r.reason_code),
  }
}

/** Narrow `raw_data.data_authority` into the read model. Returns null when the
 *  block is absent, malformed, or carries no decisions — the caller then renders
 *  nothing at all (never an empty shell for a legacy artifact). */
export function parseDataAuthority(raw: unknown): DataAuthorityRecord | null {
  const r = asRecord(raw)
  if (!r) return null
  const rawDecisions = Array.isArray(r.decisions) ? r.decisions : []
  const decisions: DataAuthorityDecision[] = []
  for (const entry of rawDecisions) {
    const d = asRecord(entry)
    if (!d) continue
    const metric = asString(d.metric)
    if (!metric) continue
    const candidates = (Array.isArray(d.candidates) ? d.candidates : [])
      .map(parseCandidate)
      .filter((c): c is DataAuthorityCandidate => c !== null)
    decisions.push({
      metric,
      status: asString(d.status),
      value: asNumber(d.value),
      unit: asString(d.unit),
      currency: asNullableString(d.currency),
      selected_source: asNullableString(d.selected_source),
      is_authoritative: d.is_authoritative === true,
      reason_code: asString(d.reason_code),
      basis: asString(d.basis),
      disagreement_pct: asNumber(d.disagreement_pct),
      candidates,
    })
  }
  if (decisions.length === 0) return null
  return {
    policy_version: asNullableString(r.policy_version),
    decisions: decisions.slice().sort((a, b) => a.metric.localeCompare(b.metric)),
  }
}

// ── Labels ───────────────────────────────────────────────────────────────────
// Finance names stay English (the repo's i18n exemption list: EV/EBITDA, P/E…),
// mirroring ChapterAuditBanner's FIELD_LABELS. Falls back to Title Case.

const METRIC_LABELS: Record<string, string> = {
  revenue: 'Revenue',
  net_income: 'Net Income',
  total_cash: 'Total Cash',
  market_cap: 'Market Cap',
  current_price: 'Current Price',
  shares_outstanding: 'Shares Outstanding',
  ebitda: 'EBITDA',
  total_debt: 'Total Debt',
  gross_margin: 'Gross Margin',
}

function metricLabel(metric: string): string {
  const mapped = METRIC_LABELS[metric]
  if (mapped) return mapped
  return metric.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/** The five decision statuses → i18n keys. An unknown status falls through to a
 *  humanised raw code (still readable, never a raw dotted key). */
const STATUS_KEYS: Record<string, string> = {
  fallback: 'report.dataAuthority.status.fallback',
  conflict: 'report.dataAuthority.status.conflict',
  unavailable: 'report.dataAuthority.status.unavailable',
  definition_mismatch: 'report.dataAuthority.status.definition_mismatch',
}

/** Every reason code the leaf registry can emit → i18n keys. Kept complete so a
 *  decision can never show an unlabelled code. */
const REASON_KEYS: Record<string, string> = {
  authoritative_selected: 'report.dataAuthority.reason.authoritative_selected',
  sources_agree: 'report.dataAuthority.reason.sources_agree',
  within_tolerance: 'report.dataAuthority.reason.within_tolerance',
  canonical_value_invalid_fallback_selected:
    'report.dataAuthority.reason.canonical_value_invalid_fallback_selected',
  above_tolerance_published_flagged:
    'report.dataAuthority.reason.above_tolerance_published_flagged',
  no_eligible_observation: 'report.dataAuthority.reason.no_eligible_observation',
  definition_mismatch_period: 'report.dataAuthority.reason.definition_mismatch_period',
  definition_mismatch_currency: 'report.dataAuthority.reason.definition_mismatch_currency',
  definition_mismatch_unit: 'report.dataAuthority.reason.definition_mismatch_unit',
  definition_mismatch_caliber: 'report.dataAuthority.reason.definition_mismatch_caliber',
  non_finite_value: 'report.dataAuthority.reason.non_finite_value',
  non_positive_value: 'report.dataAuthority.reason.non_positive_value',
  stale_beyond_freshness_policy: 'report.dataAuthority.reason.stale_beyond_freshness_policy',
  after_run_as_of: 'report.dataAuthority.reason.after_run_as_of',
  non_independent_agreement: 'report.dataAuthority.reason.non_independent_agreement',
}

type Translate = (key: string, params?: Record<string, string | number>) => string

function codeLabel(code: string, table: Record<string, string>, t: Translate): string {
  if (!code) return ''
  const key = table[code]
  if (key) return t(key)
  return code.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

// ── Value formatting (unit-aware; every path tolerates a null) ───────────────

function formatAuthorityValue(
  value: number | null,
  unit: string,
  currency: string | null,
  locale: 'zh' | 'en',
): string {
  if (value === null) return '—'
  if (unit === 'ratio') return formatPercent(value, locale)
  const iso = /^[A-Z]{3}$/.test(unit)
    ? unit
    : currency && /^[A-Z]{3}$/.test(currency)
      ? currency
      : null
  if (iso) return formatCurrency(value, iso, locale)
  if (unit === 'shares') return formatCompactNumber(value, locale)
  return formatNumberAuto(value, locale)
}

export function DataAuthorityPanel({
  authority,
}: {
  authority: unknown
}): React.ReactElement | null {
  const { t, locale } = useI18n()
  const record = parseDataAuthority(authority)
  if (!record) return null

  // A conflict is PUBLISHED — only the non-accepted decisions need a row; the
  // accepted ones are summarised by a count (the canonical value is already on
  // the page). An unknown status counts as non-accepted on purpose: anything the
  // reader can't reconcile should be visible.
  const flagged = record.decisions.filter((d) => d.status !== 'accepted')
  const acceptedCount = record.decisions.length - flagged.length

  return (
    <div data-testid="report-data-authority" style={{ margin: '8px 0 24px' }}>
      {/* Native <details> (as ComputeWarningsPanel uses): the standalone HTML
          export keeps the toggle without JS. Default-OPEN — this is the record
          the conflict is measured against, not a footnote. */}
      <details
        open
        data-testid="report-data-authority-details"
        style={{
          padding: '12px 16px',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-soft)',
          borderRadius: 'var(--radius-sm)',
        }}
      >
        <summary
          style={{
            cursor: 'pointer',
            fontFamily: 'var(--font-mono)',
            fontSize: 10.5,
            letterSpacing: '0.08em',
            color: 'var(--text-muted)',
            listStyle: 'revert',
          }}
        >
          {t('report.dataAuthority.title')} · {flagged.length}
        </summary>

        <p
          style={{
            margin: '8px 0 0',
            fontFamily: 'var(--font-body)',
            fontSize: 12,
            lineHeight: 1.6,
            color: 'var(--text-muted)',
          }}
        >
          {t('report.dataAuthority.note')}
        </p>

        {flagged.length > 0 && (
          <ul
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
              margin: '12px 0 0',
              padding: 0,
              listStyle: 'none',
            }}
          >
            {flagged.map((d) => (
              <DecisionRow key={d.metric} decision={d} />
            ))}
          </ul>
        )}

        {acceptedCount > 0 && (
          <p
            data-testid="report-data-authority-accepted"
            style={{
              margin: '10px 0 0',
              fontFamily: 'var(--font-body)',
              fontSize: 12,
              lineHeight: 1.6,
              color: 'var(--text-secondary)',
            }}
          >
            {t('report.dataAuthority.accepted', { count: acceptedCount })}
          </p>
        )}
      </details>
    </div>
  )
}

function DecisionRow({ decision }: { decision: DataAuthorityDecision }): React.ReactElement {
  const { t, locale } = useI18n()
  const selected = decision.selected_source
  // The selected observation is the canonical value already shown above; the
  // alternatives are everyone else (all of them when nothing was eligible).
  const alternatives = decision.candidates.filter((c) => c.source !== selected)
  const statusText = codeLabel(decision.status, STATUS_KEYS, t)
  const reasonText = codeLabel(decision.reason_code, REASON_KEYS, t)

  return (
    <li
      data-testid="report-data-authority-decision"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        padding: '10px 12px',
        background: 'var(--surface-2)',
        border: '1px solid var(--border-faint)',
        borderRadius: 'var(--radius-sm)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 12.5,
            fontWeight: 600,
            letterSpacing: '0.02em',
            color: 'var(--text-primary)',
          }}
        >
          {metricLabel(decision.metric)}
        </span>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 12.5,
            color: 'var(--text-primary)',
          }}
        >
          {formatAuthorityValue(decision.value, decision.unit, decision.currency, locale)}
        </span>
        {statusText && (
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10.5,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--warning)',
              background: 'color-mix(in srgb, var(--warning) 14%, transparent)',
              border: '1px solid color-mix(in srgb, var(--warning) 40%, transparent)',
              borderRadius: 999,
              padding: '1px 8px',
            }}
          >
            {statusText}
          </span>
        )}
        <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
          {t('report.dataAuthority.selectedSource')}: {selected ?? '—'}
        </span>
      </div>

      {(reasonText || decision.basis) && (
        <p
          style={{
            margin: 0,
            fontSize: 11.5,
            lineHeight: 1.6,
            color: 'var(--text-muted)',
          }}
        >
          {reasonText}
          {reasonText && decision.basis ? ' — ' : ''}
          {decision.basis}
        </p>
      )}

      {alternatives.length > 0 && (
        <>
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--text-dim)',
            }}
          >
            {t('report.dataAuthority.alternatives')}
          </div>
          <ul
            data-testid="report-data-authority-alternatives"
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
              margin: 0,
              padding: 0,
              listStyle: 'none',
            }}
          >
            {alternatives.map((c) => (
              <li
                key={c.source}
                data-testid="report-data-authority-alternative"
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: 10,
                  flexWrap: 'wrap',
                  fontSize: 11.5,
                  color: 'var(--text-secondary)',
                }}
              >
                <span style={{ fontFamily: 'var(--font-mono)' }}>{c.source}</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>
                  {formatAuthorityValue(c.value, decision.unit, decision.currency, locale)}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--warning)' }}>
                  {c.deviation_pct !== null
                    ? formatPercent(c.deviation_pct, locale)
                    : t('report.dataAuthority.notCompared')}
                </span>
                {c.reason_code && (
                  <span style={{ color: 'var(--text-muted)' }}>
                    {codeLabel(c.reason_code, REASON_KEYS, t)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </li>
  )
}
