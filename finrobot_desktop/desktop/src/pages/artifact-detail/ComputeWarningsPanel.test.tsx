// The methodology-notes group must render OPEN by default (owner review: the
// collapsed disclosure hid the transparency notes reviewers always need) while
// staying collapsible. Genuine caveats are unchanged.

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ComputeWarningsPanel } from './ComputeWarningsPanel'

describe('ComputeWarningsPanel', () => {
  it('renders the methodology notes open by default', () => {
    render(
      <ComputeWarningsPanel
        caveats={['A genuine caveat']}
        methodologyNotes={['A template note']}
      />,
    )
    const details = screen.getByTestId('report-methodology-notes')
    expect(details.tagName).toBe('DETAILS')
    expect(details.hasAttribute('open')).toBe(true)
    // Still a disclosure the reader can fold away.
    expect(details.querySelector('summary')).not.toBeNull()
  })

  it('renders genuine caveats as before', () => {
    render(<ComputeWarningsPanel caveats={['A genuine caveat']} methodologyNotes={[]} />)
    expect(screen.getByTestId('report-warnings-caveats')).toBeInTheDocument()
  })

  it('renders nothing when there are no warnings at all', () => {
    const { container } = render(<ComputeWarningsPanel caveats={[]} methodologyNotes={[]} />)
    expect(container.firstChild).toBeNull()
  })
})
