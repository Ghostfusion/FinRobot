// The report rail's navigation contract: a labelled complementary landmark, a
// labelled nav whose current entry carries aria-current, a real tablist for
// CONTENTS | VERSIONS, the aux-section marker, the reading-progress bar, the
// back-to-top control and the active section's sub-headings.
//
// Before this change the rail was a bare <aside> with an unlabelled <nav>, an
// active state expressed ONLY as a colour, plain buttons with no tab semantics,
// a scroll-spy that could only ever set (never clear) the active id, and no way
// back to the top of a 14-chapter document.

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { ReportLeftRail, pickActiveSection } from '../ReportLeftRail'
import { reportSectionEntries, type ReportSectionEntry } from '../../reportSections'

/** Give the listed element ids a top offset (everything else stays at 0). jsdom
 *  has no layout, so the scroll-spy's measurements need a fixed stage. */
function stubRects(tops: Record<string, number>): void {
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (
    this: Element,
  ): DOMRect {
    const top = tops[this.id] ?? 0
    return {
      top,
      bottom: top + 100,
      height: 100,
      left: 0,
      right: 0,
      width: 100,
      x: 0,
      y: top,
      toJSON: () => ({}),
    }
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

const ALL_SECTIONS = reportSectionEntries('en', {
  versionDiff: true,
  audit: true,
  summary: true,
  warnings: true,
})

const CHAPTERS_ONLY = reportSectionEntries('en', {
  versionDiff: false,
  audit: false,
  summary: false,
  warnings: false,
})

function renderRail(entries: ReportSectionEntry[] = ALL_SECTIONS, extra?: React.ReactNode) {
  return render(
    <MemoryRouter>
      <div id="main-scroll">
        <ReportLeftRail
          ticker="AAA"
          verdict="BUY"
          entries={entries}
          currentArtifactId="a1"
          timeline={[]}
          reportType="equity_research"
        />
        {extra}
      </div>
    </MemoryRouter>,
  )
}

describe('ReportLeftRail accessibility', () => {
  it('is a labelled complementary landmark containing a labelled navigation', () => {
    renderRail()
    expect(screen.getByRole('complementary', { name: 'Report navigation' })).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Report sections' })).toBeTruthy()
  })

  it('marks the current section with aria-current, not only with colour', () => {
    renderRail()
    const first = screen.getByTestId(`toc-${ALL_SECTIONS[0].id}`)
    expect(first.getAttribute('aria-current')).toBe('location')
    // Every other entry must be silent about currency.
    expect(
      screen.getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'location'),
    ).toHaveLength(1)
  })

  it('exposes CONTENTS | VERSIONS as a tablist with roving tabindex', () => {
    renderRail()
    const contents = screen.getByRole('tab', { name: 'REPORT NAV' })
    const versions = screen.getByRole('tab', { name: /versions/i })
    expect(contents.getAttribute('aria-selected')).toBe('true')
    expect(versions.getAttribute('aria-selected')).toBe('false')
    expect(contents.getAttribute('tabindex')).toBe('0')
    expect(versions.getAttribute('tabindex')).toBe('-1')
    expect(contents.getAttribute('aria-controls')).toBe('rail-panel-contents')

    fireEvent.click(versions)
    expect(screen.getByRole('tab', { name: /versions/i }).getAttribute('aria-selected')).toBe(
      'true',
    )
    expect(screen.getByText('No history yet. Run analysis again to build a timeline.')).toBeTruthy()
    expect(document.getElementById('rail-panel-contents')?.hasAttribute('hidden')).toBe(true)
  })

  it('moves between the tabs with the arrow keys (APG)', () => {
    renderRail()
    fireEvent.keyDown(screen.getByRole('tab', { name: 'REPORT NAV' }), { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: /versions/i }).getAttribute('aria-selected')).toBe(
      'true',
    )
  })
})

describe('ReportLeftRail contents', () => {
  it('renders every manifest entry, marking the unnumbered auxiliary sections', () => {
    renderRail()
    const nav = screen.getByRole('navigation', { name: 'Report sections' })
    for (const entry of ALL_SECTIONS) {
      expect(within(nav).getByTestId(`toc-${entry.id}`)).toBeTruthy()
    }
    // Aux entries carry the marker instead of a chapter number.
    expect(within(nav).getAllByText('§')).toHaveLength(4)
    expect(within(nav).getByText('12')).toBeTruthy() // filings
  })

  it('reports reading progress as a progressbar', () => {
    renderRail()
    const bar = screen.getByRole('progressbar', { name: 'Reading progress' })
    expect(bar.getAttribute('aria-valuemin')).toBe('0')
    expect(bar.getAttribute('aria-valuemax')).toBe('100')
    expect(bar.getAttribute('aria-valuenow')).toBe('0')
  })

  it('offers a back-to-top control at the end of the list', () => {
    renderRail()
    const backToTop = screen.getByTestId('report-back-to-top')
    expect(backToTop.textContent).toContain('Back to top')
    fireEvent.click(backToTop)
  })
})

describe('ReportLeftRail second level', () => {
  it("lists the active section's sub-headings as links, with stable ids", () => {
    renderRail(
      CHAPTERS_ONLY,
      <section id="cover">
        <h3>What the Market Is Pricing In</h3>
        <h3>Bull / Bear Case</h3>
      </section>,
    )
    const sublist = screen.getByTestId('toc-sub-cover')
    const links = within(sublist).getAllByRole('link')
    expect(links.map((a) => a.textContent)).toEqual([
      'What the Market Is Pricing In',
      'Bull / Bear Case',
    ])
    // The heading is addressable, so the sub-entry is a real deep link.
    expect(links[0].getAttribute('href')).toBe('#cover-sub-0')
    expect(document.getElementById('cover-sub-0')?.textContent).toBe(
      'What the Market Is Pricing In',
    )
  })

  it('only expands the section the reader is in — no links into the others', () => {
    // jsdom reports every rect as 0, so the spy needs stubs to be deterministic:
    // the thesis section sits below the fold, the cover is above it.
    stubRects({ cover: 0, thesis: 400 })
    renderRail(
      CHAPTERS_ONLY,
      <>
        <section id="cover">
          <h3>Cover sub-heading</h3>
        </section>
        <section id="thesis">
          <h3>Thesis sub-heading</h3>
        </section>
      </>,
    )
    expect(
      screen.queryAllByTestId(/^toc-sub-/).map((el) => el.getAttribute('data-testid')),
    ).toEqual(['toc-sub-cover'])
    // No id is minted into a section that was never read.
    expect(document.getElementById('thesis-sub-0')).toBeNull()
  })
})

describe('ReportLeftRail scroll-spy', () => {
  it('picks the last section whose top passed the eye line, never the last rendered', () => {
    stubRects({ cover: -400, thesis: -120, overview: 300 })
    renderRail(
      CHAPTERS_ONLY.slice(0, 3),
      <>
        <section id="cover">
          <h3>c</h3>
        </section>
        <section id="thesis">
          <h3>t</h3>
        </section>
        <section id="overview">
          <h3>o</h3>
        </section>
      </>,
    )
    expect(screen.getByTestId('toc-thesis').getAttribute('aria-current')).toBe('location')
    expect(screen.getByTestId('toc-cover').getAttribute('aria-current')).toBeNull()
    expect(screen.getByTestId('toc-overview').getAttribute('aria-current')).toBeNull()
  })
})

describe('pickActiveSection', () => {
  it('returns the last section at or above the eye line', () => {
    expect(
      pickActiveSection(
        [
          { id: 'a', top: -10 },
          { id: 'b', top: 5 },
          { id: 'c', top: 100 },
        ],
        0,
      ),
    ).toBe('a')
  })

  it('falls back to the first section while the reader is above all of them', () => {
    expect(
      pickActiveSection(
        [
          { id: 'a', top: 5 },
          { id: 'b', top: 50 },
        ],
        0,
      ),
    ).toBe('a')
  })

  it('is empty-safe', () => {
    expect(pickActiveSection([], 0)).toBeNull()
  })
})
