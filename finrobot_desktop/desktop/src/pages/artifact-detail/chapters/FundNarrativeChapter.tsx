// Fund chapter 05 — Narrative. The run's own prose (`outputs.summary_text`): what
// the pipeline concluded about the fund after reading its profile, cost and
// portfolio. Rendered verbatim inside the report's + AI NARRATIVE block — the
// chapter adds no commentary of its own, so the reader can always tell the engine's
// words from the numbers above them.
//
// A run that wrote no narrative (a failed or truncated narrative step) says so
// explicitly rather than rendering an empty chapter that looks like a rendering bug.

import { useI18n } from '../../../i18n'
import { Chapter, Narrative } from './ChapterBase'

interface Props {
  /** `outputs.summary_text`; null / blank when the run wrote no narrative. */
  summary: string | null | undefined
}

export function FundNarrativeChapter({ summary }: Props): React.ReactElement {
  const { t } = useI18n()
  const text = (summary ?? '').trim()

  return (
    <Chapter id="fund-narrative">
      {text === '' ? (
        <p
          style={{
            fontSize: 12.5,
            lineHeight: 1.6,
            color: 'var(--text-secondary)',
            margin: 0,
            maxWidth: 820,
          }}
        >
          {t('report.fund.narrative.empty')}
        </p>
      ) : (
        <Narrative>
          {/* pre-wrap: the engine's prose carries its own paragraph breaks and we
              render them as written instead of collapsing the whole narrative
              into one run-on line. */}
          <div style={{ whiteSpace: 'pre-wrap' }}>{text}</div>
        </Narrative>
      )}
    </Chapter>
  )
}
