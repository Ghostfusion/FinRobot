// The report rail's navigation contract: a labelled complementary landmark, a
// labelled nav whose current entry carries aria-current, a real tablist for
// CONTENTS | VERSIONS, the aux-section marker, the reading-progress bar, the
// back-to-top control and the active section's sub-headings.
//
// Before this change the rail was a bare <aside> with an unlabelled <nav>, an
// active state expressed ONLY as a colour, plain buttons with no tab semantics,
// a scroll-spy that could only ever set (never clear) the active id, and no way
// back to the top of a 15-chapter document.

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { ReportLeftRail, pickActiveSection } from '../ReportLeftRail'
import { reportSectionEntries, type ReportSectionEntry } from '../../reportSections'
import type { PriceSessionShape } from '../../chapters'

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

function renderRail(
  entries: ReportSectionEntry[] = ALL_SECTIONS,
  extra?: React.ReactNode,
  card?: {
    priceSession?: PriceSessionShape | null
    snapshotAsOf?: string | null
    quoteIsLive?: boolean
    quoteAsOf?: string | null
  },
) {
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
          snapshotPrice={187.42}
          priceSession={card?.priceSession ?? null}
          snapshotAsOf={card?.snapshotAsOf ?? null}
          quoteIsLive={card?.quoteIsLive ?? false}
          quoteAsOf={card?.quoteAsOf ?? null}
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
    expect(within(nav).getByText('13')).toBeTruthy() // filings
  })

  it('presents the numbered spine first, in ascending order, then the note group', () => {
    renderRail()
    const nav = screen.getByRole('navigation', { name: 'Report sections' })
    const chapters = ALL_SECTIONS.filter((e) => e.kind === 'chapter')
    const notes = ALL_SECTIONS.filter((e) => e.kind === 'aux')

    // Chapter rows first (01…15), then the unnumbered notes — never interleaved.
    // An interleaved § row sat between 01 and 02 and made the numbering read as
    // shuffled even though every number was correct.
    const rendered = [...nav.querySelectorAll('a[data-testid^="toc-"]')].map((a) =>
      a.getAttribute('data-testid'),
    )
    expect(rendered).toEqual([
      ...chapters.map((e) => `toc-${e.id}`),
      ...notes.map((e) => `toc-${e.id}`),
    ])

    const markers = [...nav.querySelectorAll('a[data-testid^="toc-"]')].map(
      (a) => a.querySelector('span')?.textContent ?? '',
    )
    expect(markers.slice(0, chapters.length)).toEqual(chapters.map((e) => e.num))
    expect(markers.slice(chapters.length)).toEqual(notes.map(() => '§'))

    // The note group is labelled, so the unnumbered rows are not read as a gap in
    // the sequence.
    expect(within(nav).getByText('Notes')).toBeTruthy()
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

describe('ReportLeftRail — the session delta beside the spot', () => {
  it('renders the frozen prior-close → last-close move, labelled as the last session', () => {
    renderRail(ALL_SECTIONS, undefined, {
      priceSession: { latest_session_change: 12.46, latest_session_change_pct: 2.384 },
      snapshotAsOf: '2026-10-10T20:00:00Z',
    })

    const line = screen.getByTestId('rail-session-change')
    expect(line.textContent).toContain('+$12.46')
    expect(line.textContent).toContain('+2.38%')
    // The data layer documents this as the session `current_price` belongs to,
    // NOT "today" — a closed-market view must not read as live.
    expect(line.textContent).toContain('last session')
    expect(line.textContent).not.toContain('today')
    // …and the as-of date rides the tooltip so the basis is checkable.
    expect(line.getAttribute('title')).toContain('prior close')
  })

  it('marks a decline with its own glyph and sign', () => {
    renderRail(ALL_SECTIONS, undefined, {
      priceSession: { latest_session_change: -3.75, latest_session_change_pct: -1.96 },
      snapshotAsOf: '2026-10-10T20:00:00Z',
    })

    const line = screen.getByTestId('rail-session-change')
    expect(line.textContent).toContain('▼')
    expect(line.textContent).toContain('-$3.75')
    expect(line.textContent).toContain('-1.96%')
  })

  it('renders a measured flat session as flat', () => {
    renderRail(ALL_SECTIONS, undefined, {
      priceSession: { latest_session_change: 0, latest_session_change_pct: 0 },
    })

    const line = screen.getByTestId('rail-session-change')
    expect(line.textContent).toContain('·')
    expect(line.textContent).toContain('$0.00')
  })

  it('renders nothing when the run had no session to diff', () => {
    renderRail()
    expect(screen.queryByTestId('rail-session-change')).toBeNull()
  })

  it('renders nothing when the payload carries no change even with the block present', () => {
    renderRail(ALL_SECTIONS, undefined, {
      priceSession: { latest_session_change: null, latest_session_change_pct: null },
    })

    expect(screen.queryByTestId('rail-session-change')).toBeNull()
  })

  it('still renders the price caption when there is no session block', () => {
    renderRail(ALL_SECTIONS, undefined, { snapshotAsOf: '2026-10-10T20:00:00Z' })

    expect(screen.queryByTestId('rail-session-change')).toBeNull()
    expect(screen.getByText(/187.42/)).toBeTruthy()
  })
})

// 2026-10-16 CRWV: the caption read "spot $69.69" for a price the payload itself
// stamps `quote_is_live: false` / `quote_as_of: 2026-10-15` — the run's own
// degradation marker said "provider served no tick time, so the price is the
// session close". The caption names what the price IS, from that flag.
describe('ReportLeftRail — the price caption names the price basis', () => {
  it('calls a session close a close, and dates it', () => {
    renderRail(ALL_SECTIONS, undefined, { quoteAsOf: '2026-10-15T00:00:00Z' })

    expect(screen.getByText(/Close \$187\.42 · Oct 15/)).toBeTruthy()
    expect(screen.queryByText(/spot/i)).toBeNull()
  })

  it('calls a live intraday quote live, and dates nothing', () => {
    renderRail(ALL_SECTIONS, undefined, {
      quoteIsLive: true,
      quoteAsOf: '2026-10-15T00:00:00Z',
    })

    expect(screen.getByText(/Live \$187\.42/)).toBeTruthy()
    expect(screen.queryByText(/Oct 15/)).toBeNull()
  })
})
