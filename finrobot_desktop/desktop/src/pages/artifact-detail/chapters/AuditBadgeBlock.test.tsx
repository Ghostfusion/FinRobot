import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { AuditBadgeBlock } from './AuditBadgeBlock'
import type { AuditBadgeShape } from '../../../hooks/useV5Artifacts'

const WITHHOLD = {
  id: 'C11',
  title: 'One quantity, one definition',
  evidence: 'the two writers of valuation_withheld disagree',
}
const ANNOTATE = {
  id: 'C6b',
  title: 'Note vs cross-checks',
  evidence: 'the report claims it had no cross-validation while publishing 1 cross-check(s)',
}

function badge(over: Partial<AuditBadgeShape> = {}): AuditBadgeShape {
  return {
    would_withhold: [],
    would_annotate: [],
    shipped_withheld: false,
    ...over,
  }
}

describe('AuditBadgeBlock', () => {
  it('renders nothing when no rule fires', () => {
    const { container } = render(<AuditBadgeBlock badge={badge()} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing without a badge — the export ships a frozen document, not a reading', () => {
    const { container } = render(<AuditBadgeBlock badge={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('shows a withholding clause with the registrys own id, title and evidence', () => {
    render(<AuditBadgeBlock badge={badge({ would_withhold: [WITHHOLD] })} />)
    const block = screen.getByTestId('report-audit-badge-withhold')
    // The surface names the rule exactly as the Python registry does: id + title,
    // plus the instance-level evidence. A re-typed name here would be a second truth.
    expect(block.textContent).toContain('C11')
    expect(block.textContent).toContain(WITHHOLD.title)
    expect(block.textContent).toContain(WITHHOLD.evidence)
    expect(screen.queryByTestId('report-audit-badge-annotate')).not.toBeInTheDocument()
  })

  it('shows an annotation-only finding without claiming anything was withheld', () => {
    render(<AuditBadgeBlock badge={badge({ would_annotate: [ANNOTATE] })} />)
    const block = screen.getByTestId('report-audit-badge-annotate')
    expect(block.textContent).toContain('C6b')
    expect(block.textContent).toContain(ANNOTATE.evidence)
    expect(screen.queryByTestId('report-audit-badge-withhold')).not.toBeInTheDocument()
  })

  it('reports the shipped state beside the reading, in every firing case', () => {
    // The two readings ship together by construction: a surface can show what today's
    // rules would do, but never without the record's own state next to it (§9.3).
    const { unmount } = render(
      <AuditBadgeBlock
        badge={badge({
          would_withhold: [WITHHOLD],
          shipped_withheld: true,
          shipped_withheld_reason: 'contract_C7',
        })}
      />,
    )
    expect(screen.getByTestId('report-audit-badge-shipped')).toBeInTheDocument()
    unmount()

    render(<AuditBadgeBlock badge={badge({ would_annotate: [ANNOTATE] })} />)
    expect(screen.getByTestId('report-audit-badge-shipped')).toBeInTheDocument()
  })
})
