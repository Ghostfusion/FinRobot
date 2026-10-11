// The Print / PDF action: the toolbar owns nothing about pagination — it hands
// the surface to the system print dialog and App.css's @media print block does
// the layout work (chrome stripped, dark theme lifted). Locks that the action
// exists and reaches window.print.

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { ReportToolbar } from '../ReportToolbar'

function renderToolbar() {
  return render(
    <MemoryRouter>
      <ReportToolbar
        ticker="AAA"
        artifactId="a1"
        reportType="equity_research"
        targetPrice={300}
        targetLow={null}
        targetHigh={null}
        valuationWithheld={false}
        quoteCurrency="USD"
        snapshotPrice={290}
        snapshotAsOf="2026-06-01T00:00:00Z"
        onExportHtml={() => {}}
      />
    </MemoryRouter>,
  )
}

describe('ReportToolbar', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('offers a Print / PDF action that invokes the system print dialog', () => {
    const print = vi.fn()
    vi.stubGlobal('print', print)
    renderToolbar()
    fireEvent.click(screen.getByText(/Print \/ PDF/))
    expect(print).toHaveBeenCalledTimes(1)
  })
})
