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
import { degradedLabel } from '../../views/workspace/degradedLabel'
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
  /** The session / period THIS candidate's own value is stamped for. The deviation
   *  alone cannot say whether two sources measured the same instant, so the record
   *  carries each side's own stamp: 2026-10-16 CRWV published "eodhd 69.69 vs
   *  yfinance 62.12, 10.9% above tolerance" where one side was a dated session
   *  close and the other a bare live quote (`{"price": …}`, nothing else).
   *
   *  ``null`` = the provider stamped no session (a fact about the quote);
   *  ``undefined`` = the record predates this field (a legacy artifact). Never
   *  conflate them — only the first may be rendered as "no session stamp". */
  period_end?: string | null
  period_basis?: string | null
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
  /** What two numbers must share before a comparison means anything —
   *  `session_price` = bar session + quote currency (the `current_price` row). */
  comparability: string
  /** The session / period the PUBLISHED value is stamped for. */
  period_end: string | null
  period_basis: string | null
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
    // Absent stays absent (a record written before the field existed); a present
    // null stays null (the provider stamped no session).
    period_end: 'period_end' in r ? asNullableString(r.period_end) : undefined,
    period_basis: 'period_basis' in r ? asNullableString(r.period_basis) : undefined,
  }
}

/** How a value is stamped in time, as the record states it — never left implicit.
 *  `session_price` rows (the price) are stamped by BAR SESSION; a null stamp there
 *  is the fact that the provider named no session, not a missing field to fill.
 *  Statement metrics are stamped by period end instead. */
function instantStamp(
  decision: { comparability: string; period_end: string | null | undefined },
  t: Translate,
): string {
  // ``undefined`` is a legacy record that predates the field: say nothing rather
  // than claim the provider stamped no session.
  if (decision.period_end === undefined) return ''
  if (!decision.period_end) {
    return decision.comparability === 'session_price'
      ? t('report.dataAuthority.noSessionStamp')
      : ''
  }
  return decision.comparability === 'session_price'
    ? t('report.dataAuthority.sessionStamp', { date: decision.period_end })
    : t('report.dataAuthority.periodStamp', { date: decision.period_end })
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
      comparability: asString(d.comparability),
      period_end: asNullableString(d.period_end),
      period_basis: asNullableString(d.period_basis),
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

/** Coverage counts the data layer publishes beside the records
 *  (`raw_data.provenance.metrics_decided` / `metrics_without_record` /
 *  `divergence_warnings`). Every field is `int | null`. */
export interface DataAuthorityCoverage {
  metricsDecided: number | null
  metricsWithoutRecord: number | null
  divergenceWarnings: number | null
}

/** Narrow `raw_data.provenance` into the coverage read model. Returns null when no
 *  count is present (a legacy artifact) — the caller then renders no coverage line. */
export function parseAuthorityCoverage(raw: unknown): DataAuthorityCoverage | null {
  const r = asRecord(raw)
  if (!r) return null
  const coverage: DataAuthorityCoverage = {
    metricsDecided: asNumber(r.metrics_decided),
    metricsWithoutRecord: asNumber(r.metrics_without_record),
    divergenceWarnings: asNumber(r.divergence_warnings),
  }
  if (
    coverage.metricsDecided === null &&
    coverage.metricsWithoutRecord === null &&
    coverage.divergenceWarnings === null
  ) {
    return null
  }
  return coverage
}

/** The degradation markers the SAME `raw_data.provenance` block carries beside
 *  its counts (`degraded`, from the canonicals' `Provenance.degraded` — the
 *  extractor merges the financials' markers with the PRICE feed's quote codes,
 *  e.g. `quote_ts_missing` / `quote_currency_inferred`). These qualify the
 *  numbers this panel is the record for — an accepted-but-degraded quote is
 *  still reader-relevant — so they must reach the report, not stay in the
 *  engine's own summary text. Returns [] for a legacy artifact. */
export function parseProvenanceFlags(raw: unknown): string[] {
  const r = asRecord(raw)
  if (!r || !Array.isArray(r.degraded)) return []
  return r.degraded.filter((f): f is string => typeof f === 'string' && f !== '')
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

// Shared panel styles (the note / list / count blocks render in both the
// financials record and the price record, so they are declared once).
const panelBoxStyle: React.CSSProperties = {
  padding: '12px 16px',
  background: 'var(--bg-card)',
  border: '1px solid var(--border-soft)',
  borderRadius: 'var(--radius-sm)',
}
const panelSummaryStyle: React.CSSProperties = {
  cursor: 'pointer',
  fontFamily: 'var(--font-mono)',
  fontSize: 10.5,
  letterSpacing: '0.08em',
  color: 'var(--text-muted)',
  listStyle: 'revert',
}
const panelNoteStyle: React.CSSProperties = {
  margin: '8px 0 0',
  fontFamily: 'var(--font-body)',
  fontSize: 12,
  lineHeight: 1.6,
  color: 'var(--text-muted)',
}
const panelListStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  margin: '12px 0 0',
  padding: 0,
  listStyle: 'none',
}
const panelCountStyle: React.CSSProperties = {
  margin: '10px 0 0',
  fontFamily: 'var(--font-body)',
  fontSize: 12,
  lineHeight: 1.6,
  color: 'var(--text-secondary)',
}
// The panel's ONE badge: the decision status pill and the provenance-flag pills
// below are the same amber micro-mono chip, so the two read as the same kind of
// marker rather than two visual languages.
const panelBadgeStyle: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 10.5,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'var(--warning)',
  background: 'color-mix(in srgb, var(--warning) 14%, transparent)',
  border: '1px solid color-mix(in srgb, var(--warning) 40%, transparent)',
  borderRadius: 999,
  padding: '1px 8px',
}
// The degraded-flag line: a dim mono label + its badges, on one wrapping row.
const panelFlagRowStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 6,
  margin: '10px 0 0',
  fontFamily: 'var(--font-mono)',
  fontSize: 10.5,
  letterSpacing: '0.08em',
  color: 'var(--text-muted)',
}

export function DataAuthorityPanel({
  authority,
  priceAuthority,
  coverage,
}: {
  authority: unknown
  priceAuthority?: unknown
  coverage?: unknown
}): React.ReactElement | null {
  const { t, locale } = useI18n()
  const record = parseDataAuthority(authority)
  const priceRecord = parseDataAuthority(priceAuthority)
  const cov = parseAuthorityCoverage(coverage)
  const marks = parseProvenanceFlags(coverage)
  // Nothing to say when neither a record nor a coverage count nor a degradation
  // marker reached the artifact (every artifact written before these fields
  // existed) — never an empty shell.
  if (!record && !priceRecord && !cov && marks.length === 0) return null

  // A conflict is PUBLISHED — only the non-accepted decisions need a row; the
  // accepted ones are summarised by a count (the canonical value is already on
  // the page). An unknown status counts as non-accepted on purpose: anything the
  // reader can't reconcile should be visible.
  const flagged = record ? record.decisions.filter((d) => d.status !== 'accepted') : []
  const acceptedCount = record ? record.decisions.length - flagged.length : 0
  const priceFlagged = priceRecord
    ? priceRecord.decisions.filter((d) => d.status !== 'accepted')
    : []
  const priceAccepted = priceRecord ? priceRecord.decisions.length - priceFlagged.length : 0
  // Does the price record actually STAMP its candidates? A legacy artifact predates
  // the field, and the record's note must not promise rows that aren't there.
  const priceCandidatesStampSessions = (priceRecord?.decisions ?? []).some((d) =>
    d.candidates.some((c) => c.period_end !== undefined),
  )
  // The FINANCIALS record is absent for the audited run. The panel must say so
  // explicitly — a bare "· 0" reads as "zero conflicts", which is the defect.
  const financialsMissing = record === null

  return (
    <div data-testid="report-data-authority" style={{ margin: '8px 0 24px' }}>
      {/* Native <details> (as ComputeWarningsPanel uses): the standalone HTML
          export keeps the toggle without JS. Default-OPEN — this is the record
          the conflict is measured against, not a footnote. */}
      <details open data-testid="report-data-authority-details" style={panelBoxStyle}>
        <summary style={panelSummaryStyle}>
          {t('report.dataAuthority.title')} ·{' '}
          {financialsMissing
            ? locale === 'zh'
              ? '财务指标无决策记录'
              : 'no financial-metrics record'
            : flagged.length}
        </summary>

        {record && <p style={panelNoteStyle}>{t('report.dataAuthority.note')}</p>}

        {financialsMissing && (
          <p data-testid="report-data-authority-no-record" style={panelNoteStyle}>
            {locale === 'zh'
              ? '未为「财务指标」持久化指标权威决策记录——这不等于零冲突:本次运行的对账结果未落库,对账状态未知,请按未核对处理。'
              : 'No metric-authority decision record was persisted for the financial metrics — this is NOT the same as zero conflicts. The reconciliation simply did not reach this run, so treat the financial figures as unreconciled.'}
          </p>
        )}

        {cov && (
          <p data-testid="report-data-authority-coverage" style={panelNoteStyle}>
            {locale === 'zh'
              ? `覆盖:财务指标决策 ${cov.metricsDecided ?? '—'} 项 · 已比对但无记录 ${cov.metricsWithoutRecord ?? '—'} 项 · 校验分歧警告 ${cov.divergenceWarnings ?? '—'} 条`
              : `Coverage: ${cov.metricsDecided ?? '—'} financial-metric decision(s) · ${cov.metricsWithoutRecord ?? '—'} compared metric(s) with no record · ${cov.divergenceWarnings ?? '—'} validator divergence warning(s)`}
          </p>
        )}

        {/* The provenance block's degradation markers (financials + the PRICE
            feed's quote codes). They qualify the numbers this record is about —
            an accepted quote with no tick time, or an inferred quote currency,
            is exactly what a reader must not have to infer from the price. */}
        {marks.length > 0 && (
          <div data-testid="report-data-authority-degraded" style={panelFlagRowStyle}>
            <span style={{ textTransform: 'uppercase' }}>{t('report.dataAuthority.degraded')}</span>
            {marks.map((flag) => (
              <span key={flag} style={panelBadgeStyle}>
                {degradedLabel(t, flag)}
              </span>
            ))}
          </div>
        )}

        {flagged.length > 0 && (
          <ul style={panelListStyle}>
            {flagged.map((d) => (
              <DecisionRow key={d.metric} decision={d} />
            ))}
          </ul>
        )}

        {acceptedCount > 0 && (
          <p data-testid="report-data-authority-accepted" style={panelCountStyle}>
            {t('report.dataAuthority.accepted', { count: acceptedCount })}
          </p>
        )}
      </details>

      {/* The PRICE canonical's own decision record (`raw_data.price_authority`).
          Rendered separately and labelled as the PRICE's record: its
          `current_price` decision is how the authoritative price becomes
          reader-visible — it must never be read as the financials' record. */}
      {priceRecord && (
        <details
          open
          data-testid="report-data-authority-price"
          style={{ ...panelBoxStyle, marginTop: 10 }}
        >
          <summary style={panelSummaryStyle}>
            {locale === 'zh' ? '价格决策记录' : 'Price decision record'} · {priceFlagged.length}
          </summary>
          <p style={panelNoteStyle}>
            {locale === 'zh'
              ? '权威现价(current_price)的对账记录——封面与各章节所用价格的来源。'
              : 'The reconciliation record behind the authoritative current price — the value the cover and every chapter publish.'}
            {/* Only promise the per-row stamps when the record carries them: a
                legacy payload predates the field, and a note about stamps that are
                not on screen would be worse than no note. */}
            {priceCandidatesStampSessions &&
              (locale === 'zh'
                ? '每一行都标注该数值所属的交易日;若某个来源自身没有时段标记,它报出的可能是另一个时点的价格,其差额并不说明已发布价格有误。'
                : 'Each row states the session its value is stamped for; a source that stamps none of its own may be quoting a different instant, so its gap is not evidence about the published one.')}
          </p>
          {priceFlagged.length > 0 && (
            <ul style={panelListStyle}>
              {priceFlagged.map((d) => (
                <DecisionRow key={d.metric} decision={d} />
              ))}
            </ul>
          )}
          {priceAccepted > 0 && (
            <p data-testid="report-data-authority-price-accepted" style={panelCountStyle}>
              {t('report.dataAuthority.accepted', { count: priceAccepted })}
            </p>
          )}
        </details>
      )}
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
  // What instant the PUBLISHED value is for. "Current Price $69.69" alone reads as
  // the price now; the record says which session it is stamped for (or that the
  // provider stamped none).
  const valueStamp = instantStamp(decision, t)

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
        {valueStamp && (
          <span
            data-testid="report-data-authority-decision-instant"
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              color: 'var(--text-muted)',
            }}
          >
            {valueStamp}
          </span>
        )}
        {statusText && <span style={panelBadgeStyle}>{statusText}</span>}
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
            {alternatives.map((c) => {
              // Each candidate carries its OWN stamp: the published row's session
              // is not the alternative's, and a reader comparing two numbers must be
              // able to see whether they are the same measurement.
              const candidateStamp = instantStamp(
                { comparability: decision.comparability, period_end: c.period_end },
                t,
              )
              return (
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
                  {candidateStamp && (
                    <span
                      data-testid="report-data-authority-alternative-instant"
                      style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}
                    >
                      {candidateStamp}
                    </span>
                  )}
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
              )
            })}
          </ul>
        </>
      )}
    </li>
  )
}
