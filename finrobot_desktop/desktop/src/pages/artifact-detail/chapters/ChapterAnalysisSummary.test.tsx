// Auxiliary section — the engine's own analysis summary (outputs.summary_text).
// Content-gated and collapsed: it must disappear entirely when the artifact has
// no summary, and it must not smuggle heading elements into the report outline
// (MarkdownLite renders markdown headings as <strong>, so an engine summary
// starting with "# FinRobot Analysis Report" cannot inject an <h1>).

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ChapterAnalysisSummary } from './ChapterAnalysisSummary'

describe('ChapterAnalysisSummary', () => {
  it('renders nothing without a summary', () => {
    const { container: empty } = render(<ChapterAnalysisSummary text={null} />)
    expect(empty.innerHTML).toBe('')
    const { container: blank } = render(<ChapterAnalysisSummary text={'   \n  '} />)
    expect(blank.innerHTML).toBe('')
  })

  it('renders the engine record, collapsed, as the manifest id', () => {
    const { container } = render(
      <ChapterAnalysisSummary
        text={'# FinRobot Analysis Report\n\nRating: **HOLD** (medium confidence).'}
      />,
    )
    const section = container.querySelector('section#report-summary')
    expect(section).not.toBeNull()
    expect(section?.querySelector('details')?.hasAttribute('open')).toBe(false)
    expect(screen.getByText('Analysis Summary')).toBeTruthy()
    expect(screen.getByText('ENGINE RECORD')).toBeTruthy()
    expect(screen.getByText(/medium confidence/)).toBeTruthy()
    // The markdown heading became a <strong>, so the report outline is untouched.
    expect(container.querySelector('h1, h2, h3')).toBeNull()
  })
})
