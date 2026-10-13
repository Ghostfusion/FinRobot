// Auxiliary section — the pipeline's OWN analysis summary (outputs.summary_text).
//
// Why it exists: `outputs.summary_text` is persisted on every equity_research
// artifact and was rendered nowhere in the report — only the compact viewer for
// other artifact types read it. So the one place the engine states, in its own
// words, what it did and concluded was unreachable from the report it describes.
//
// Placement: behind the cover (CFA / sell-side convention: front matter, then a
// summary, then the argument) and OPEN by default — reviewers reported the
// collapsed disclosure hid the two sections they always need; it stays
// COLLAPSIBLE so a reader can still fold a 2k-char roll-up away. Not a
// substitute for the thesis chapter: the thesis is the argument, this is the
// engine's record of the run.
//
// Content-gated: renders nothing when the artifact carries no summary (legacy /
// non-equity artifacts), and the section manifest drops the nav entry with it.

import type { CSSProperties } from 'react'

import { MarkdownLite } from '../../../components/MarkdownLite'
import type { Locale } from '../../../i18n'
import { useI18n } from '../../../i18n'

interface Props {
  /** outputs.summary_text — the pipeline's own summary of the run. */
  text: string | null | undefined
}

export function ChapterAnalysisSummary({ text }: Props): React.ReactElement | null {
  const { locale } = useI18n()
  const body = (text ?? '').trim()
  if (body.length === 0) return null

  return (
    <section
      id="report-summary"
      data-testid="report-summary"
      aria-labelledby="report-summary-title"
      style={wrap}
    >
      <details open>
        <summary style={summaryRow}>
          <span id="report-summary-title" style={title}>
            {tr('分析摘要', 'Analysis Summary', locale)}
          </span>
          {/* Provenance kicker, matching the report's "+ AI NARRATIVE" convention:
              the reader can always tell generated prose from a computed figure. */}
          <span style={eyebrow}>{tr('引擎记录', 'ENGINE RECORD', locale)}</span>
          <span aria-hidden style={chevron}>
            ▸
          </span>
        </summary>
        <div style={bodyStyle}>
          <MarkdownLite text={body} />
        </div>
      </details>
    </section>
  )
}

function tr(zh: string, en: string, locale: Locale): string {
  return locale === 'en' ? en : zh
}

const wrap: CSSProperties = {
  margin: '12px 0 4px',
  border: '1px solid var(--border-soft)',
  borderRadius: 'var(--radius-sm)',
  background: 'var(--bg-card-50)',
}

const summaryRow: CSSProperties = {
  display: 'flex',
  alignItems: 'baseline',
  gap: 10,
  padding: '10px 16px',
  cursor: 'pointer',
  listStyle: 'revert',
}

const title: CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: 'var(--text-primary)',
}

const eyebrow: CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 9.5,
  letterSpacing: '0.14em',
  color: 'var(--text-dim)',
}

const chevron: CSSProperties = {
  marginLeft: 'auto',
  fontSize: 10,
  color: 'var(--text-muted)',
}

const bodyStyle: CSSProperties = {
  padding: '0 16px 14px',
  fontSize: 13,
  lineHeight: 1.7,
  color: 'var(--text-secondary)',
}
