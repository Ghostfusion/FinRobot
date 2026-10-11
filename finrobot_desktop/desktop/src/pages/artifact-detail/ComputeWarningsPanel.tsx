// The compute-warnings footer, layered: genuine caveats up front (amber ⚠), and
// the always-fires template boilerplate sunk into a default-collapsed "Methodology
// notes" section. Shared by the full report (ReportChapters) and the compact viewer
// so the two — and the standalone HTML export — render the layering identically,
// never each re-implementing it. Buckets come pre-classified from
// reportData.layerComputeWarnings (the single source of truth); this component is
// pure presentation.

import { useI18n } from '../../i18n'

/** Whether the panel renders at all — the SAME gate the component applies, exported
 *  so the section manifest (reportSections.ts) can list/hide the nav entry for the
 *  panel without re-deriving the rule (a second copy would let the nav advertise a
 *  section the body drops). */
export function hasComputeWarnings(
  caveats: string[],
  methodologyNotes: string[],
  formulaWarnings: string[] = [],
): boolean {
  return caveats.length + methodologyNotes.length + formulaWarnings.length > 0
}

export function ComputeWarningsPanel({
  caveats,
  methodologyNotes,
  formulaWarnings = [],
  id,
}: {
  caveats: string[]
  methodologyNotes: string[]
  /** Engine formula-level warnings (compute_version.formula_warnings) — a separate
   *  channel from outputs.warnings; genuine compute caveats, shown with the ⚠ set. */
  formulaWarnings?: string[]
  /** DOM id so the left-rail TOC can link to this section. The compact viewer
   *  omits it (no TOC there). */
  id?: string
}): React.ReactElement | null {
  const { t } = useI18n()
  const alerts = [...caveats, ...formulaWarnings]
  if (!hasComputeWarnings(caveats, methodologyNotes, formulaWarnings)) return null

  return (
    <section id={id} data-testid="report-warnings" style={{ margin: '32px 0' }}>
      {alerts.length > 0 && (
        <div
          data-testid="report-warnings-caveats"
          style={{
            padding: '14px 18px',
            background: 'color-mix(in srgb, var(--warning) 6%, transparent)',
            border: '1px solid color-mix(in srgb, var(--warning) 32%, transparent)',
            borderRadius: 'var(--radius-sm)',
            fontSize: 12,
            color: 'var(--warning)',
          }}
        >
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10.5,
              letterSpacing: '0.08em',
              marginBottom: 6,
            }}
          >
            ⚠ {t('report.computeWarnings')}
          </div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {alerts.map((w, i) => (
              <li key={i} style={{ marginBottom: 4 }}>
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {methodologyNotes.length > 0 && (
        // Calm / muted, NOT amber: these are transparency notes that fire on nearly
        // every report, not defects. Default-collapsed via native <details> (works
        // without JS → the standalone export keeps the toggle); nothing is dropped,
        // everything is one click away.
        <details
          data-testid="report-methodology-notes"
          style={{
            marginTop: alerts.length > 0 ? 10 : 0,
            padding: '10px 16px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-soft)',
            borderRadius: 'var(--radius-sm)',
            fontSize: 12,
            color: 'var(--text-secondary)',
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
            {t('report.methodologyNotes')} · {methodologyNotes.length}
          </summary>
          <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
            {methodologyNotes.map((w, i) => (
              <li key={i} style={{ marginBottom: 4 }}>
                {w}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
