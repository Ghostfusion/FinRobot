import { useI18n } from '../../../i18n'
import type { AuditBadgeEntryShape, AuditBadgeShape } from '../../../hooks/useV5Artifacts'

/** What TODAY's output-contract rules make of a stored report (design §9.3).
 *
 *  The persist gate judges an artifact once, on the way in; a rule armed after a
 *  report was written therefore cannot speak about it from the artifact's own bytes —
 *  and the archive is never rewritten (the record keeps its bytes). This block is the
 *  other reading: the page hands it a derivation the API computes by re-running the
 *  live clause registry over the stored payload.
 *
 *  Two things it must never do, both of which the wording carries:
 *  · it never says the report IS withheld. It says what today's rules WOULD withhold,
 *    and reports the record's own `shipped_withheld` beside it — the reader has to be
 *    able to tell a re-reading from a fact about the published document (a badge that
 *    read `WITHHOLD` on a healthy published report would be their first impression of
 *    a correct document);
 *  · it never names a rule itself. The clause id, title and evidence all come from the
 *    registry, so the surface cannot drift from the rule it describes.
 *
 *  It renders nothing when nothing fires: the absence of a finding is not news, and
 *  the report's own withheld state is already on the cover.
 */
export function AuditBadgeBlock({
  badge,
}: {
  badge?: AuditBadgeShape | null
}): React.ReactElement | null {
  const { t } = useI18n()
  if (!badge) return null
  const { would_withhold: withhold, would_annotate: annotate } = badge
  if (withhold.length === 0 && annotate.length === 0) return null

  const entries = (rows: AuditBadgeEntryShape[]) => (
    <ul style={listStyle}>
      {rows.map((entry) => (
        <li key={entry.id} style={itemStyle}>
          <span style={ruleStyle}>
            {entry.id} — {entry.title}
          </span>
          {': '}
          {entry.evidence}
        </li>
      ))}
    </ul>
  )

  return (
    <section
      id="report-audit-badge"
      data-testid="report-audit-badge"
      role="note"
      style={sectionStyle}
    >
      <p style={titleStyle}>{t('report.auditBadge.title')}</p>
      {withhold.length > 0 && (
        <div data-testid="report-audit-badge-withhold">
          <p style={lineStyle}>{t('report.auditBadge.wouldWithhold')}</p>
          {entries(withhold)}
        </div>
      )}
      {annotate.length > 0 && (
        <div data-testid="report-audit-badge-annotate">
          <p style={lineStyle}>{t('report.auditBadge.wouldAnnotate')}</p>
          {entries(annotate)}
        </div>
      )}
      <p style={lineStyle} data-testid="report-audit-badge-shipped">
        {badge.shipped_withheld
          ? t('report.auditBadge.shipped', { reason: badge.shipped_withheld_reason ?? '' })
          : t('report.auditBadge.shippedClean')}
      </p>
    </section>
  )
}

const sectionStyle: React.CSSProperties = {
  margin: '0 0 24px',
  padding: '14px 18px',
  // Dashed + muted, deliberately NOT the banner's amber warning box: this is a
  // re-reading beside the report, not a finding of the report's own audit.
  border: '1px dashed var(--border)',
  borderRadius: 'var(--radius-md)',
  background: 'var(--surface)',
}

const titleStyle: React.CSSProperties = {
  margin: '0 0 8px',
  fontFamily: 'var(--font-display)',
  fontSize: 12,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

const lineStyle: React.CSSProperties = {
  margin: '0 0 4px',
  fontSize: 12,
  color: 'var(--text-muted)',
}

const listStyle: React.CSSProperties = {
  margin: '0 0 8px',
  paddingLeft: 18,
  fontSize: 12,
  lineHeight: 1.55,
  color: 'var(--text-muted)',
}

const itemStyle: React.CSSProperties = { marginBottom: 2 }

const ruleStyle: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  color: 'var(--text-dim)',
}
