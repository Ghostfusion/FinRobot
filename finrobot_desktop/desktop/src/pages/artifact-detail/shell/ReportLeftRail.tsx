// Left rail for the equity_research report — the single navigation flank.
//
// Replaces the old split of a left TOC + a right Version Timeline rail (which
// squeezed the reading column between two sidebars). Now one sticky rail holds:
//   • an identity card (ticker · verdict · company · 12-mo target + spot · confidence)
//   • a CONTENTS | VERSIONS tab switch
//       - CONTENTS: the report's section table of contents with scroll-spy
//         highlight, the active section's sub-headings, a reading-progress bar
//         and a back-to-top control
//       - VERSIONS: the version-history timeline (was the right rail)
// The report body reclaims the full width to the right.
//
// The TOC is the section manifest (reportSections.ts) — chapters AND the
// auxiliary non-chapter sections (audit banner / version diff / analysis
// summary / caveats). Accessibility notes: the <nav> is labelled, the active
// entry carries aria-current="location", the two views are a real tablist
// (roles + aria-selected + aria-controls), and the rail itself is a labelled
// complementary landmark. The previous implementation rendered a bare <nav>
// with a colour-only active state and no landmark — the report's own TitleBar
// already did this correctly, the rail did not.

import { useEffect, useRef, useState } from 'react'
import type { ArtifactSummaryV5 } from '../../../types/v5'
import { useI18n } from '../../../i18n'
import { formatCurrency, formatDate, formatPercent } from '../../../utils/format'
import {
  verdictLabel,
  verdictTone,
  normalizeConfidence,
  type ConfidenceTier,
} from '../../../utils/verdict'
import { ConfidenceChip } from '../../../components/ConfidenceChip'
import type { ReportSectionEntry } from '../reportSections'
import type { PriceSessionShape } from '../chapters'
import { VersionTimelineList } from './ReportRightRail'

/** The scroll container the report scrolls inside (`AppShell`). */
const SCROLL_CONTAINER_ID = 'main-scroll'
/** Where the reader's eye sits, as a fraction of the container height. A section
 *  becomes "current" once its top crosses this line. */
const EYE_LINE_RATIO = 0.3

interface ReportLeftRailProps {
  ticker: string
  companyName?: string | null
  verdict?: string | null
  snapshotPrice?: number | null
  /** Frozen prior-close → last-close delta, in the QUOTE currency. Absent when
   *  the run had fewer than 2 price bars → the caption renders nothing. */
  priceSession?: PriceSessionShape | null
  /** When the market snapshot was taken — labels the session delta so a
   *  closed-market view cannot read the last session as live. */
  snapshotAsOf?: string | null
  /** Point withheld because price is inside the fair-value band → "Fairly Valued"
   *  (confident HOLD), not a generic "WITHHELD". From deriveReportData. */
  fairlyValued?: boolean
  confidence?: ConfidenceTier | string | null
  quoteCurrency?: string
  /** The section manifest, in page order (reportSections.reportSectionEntries). */
  entries: ReportSectionEntry[]
  currentArtifactId: string
  timeline: ArtifactSummaryV5[]
  reportType: string
}

/** Which section the reader is currently in: the LAST section whose top has
 *  passed the eye line. Deterministic — unlike the previous `isIntersecting`
 *  watcher, which only ever SET the active id and therefore latched onto whichever
 *  section happened to intersect last, never clearing it (so the highlight could
 *  stick two sections behind, and a section shorter than the observation band —
 *  the closing disclaimer — could never win at all).
 *
 *  `tops` must be in document order and contain only RENDERED sections. Returns
 *  the first id when the reader is above every section (cover includes the top). */
export function pickActiveSection(
  tops: { id: string; top: number }[],
  eyeLine: number,
): string | null {
  let active: string | null = null
  for (const s of tops) {
    if (s.top > eyeLine) break
    active = s.id
  }
  return active ?? tops[0]?.id ?? null
}

/** Sub-headings of the section the reader is in — the report's second TOC level.
 *  Derived from the rendered DOM (USWDS builds its in-page nav from the headings
 *  inside main the same way) because the chapter bodies own their own
 *  sub-headings: a static list would rot the moment a chapter stops rendering one
 *  for a given ticker (KO has no DDM/LBO rows, banks have no FCFF-DCF panel).
 *  Each heading is given a stable id on first read so the rail can link to it. */
function useActiveChapterHeadings(
  activeId: string | null,
  contentKey: string,
): { id: string; label: string }[] {
  const [headings, setHeadings] = useState<{ id: string; label: string }[]>([])

  useEffect(() => {
    const section = activeId ? document.getElementById(activeId) : null
    if (!section) {
      setHeadings([])
      return
    }
    const found: { id: string; label: string }[] = []
    section.querySelectorAll('h3').forEach((h, i) => {
      const label = (h.textContent ?? '').trim()
      if (label.length === 0) return
      if (!h.id) h.id = `${activeId}-sub-${i}`
      found.push({ id: h.id, label })
    })
    setHeadings(found)
    // contentKey (the artifact id) re-reads the headings when the report body is
    // swapped under a mounted rail (version switch) with the same active section.
  }, [activeId, contentKey])

  return headings
}

export function ReportLeftRail({
  ticker,
  companyName = null,
  verdict = null,
  snapshotPrice = null,
  priceSession = null,
  snapshotAsOf = null,
  fairlyValued = false,
  confidence = null,
  quoteCurrency = 'USD',
  entries,
  currentArtifactId,
  timeline,
  reportType,
}: ReportLeftRailProps): React.ReactElement {
  const { locale, t } = useI18n()
  const [tab, setTab] = useState<'contents' | 'versions'>('contents')
  const [activeId, setActiveId] = useState<string>(entries[0]?.id ?? '')
  const [progress, setProgress] = useState(0)

  const sameTypeCount = timeline.filter((a) => a.type === reportType).length
  const verdictText = (verdict ?? '').toUpperCase()
  const tone = verdictText ? verdictTone(verdictText) : null
  const tier = normalizeConfidence(typeof confidence === 'string' ? confidence : null)

  // Identity-card headline = the CURRENT version's 12-mo TARGET, read from the
  // SAME timeline entry (`target_price`) the version rows render — so the card can
  // never disagree with its own v-row. Previously this card showed snapshotPrice
  // (the spot the target was computed against) as a bare, unlabelled number, which
  // read as contradicting the target shown in the v-rows + the report body. Spot
  // is kept as a small labelled caption for context.
  const targetPrice = timeline.find((a) => a.id === currentArtifactId)?.target_price ?? null

  // Scroll-spy + reading progress. The spy is driven by measured offsets rather
  // than IntersectionObserver: it is deterministic (see pickActiveSection), it
  // reads only the manifest's own sections, and it can be exercised without a
  // layout engine. The dependency is the manifest's id KEY, not the array — a
  // fresh entries array on every parent render used to tear down and rebuild the
  // observer on each render.
  const entryIds = entries.map((e) => e.id)
  const entryIdKey = entryIds.join('|')
  const entriesRef = useRef(entries)
  entriesRef.current = entries

  useEffect(() => {
    const container = document.getElementById(SCROLL_CONTAINER_ID)
    if (!container) return
    let frame = 0

    const measure = (): void => {
      frame = 0
      const ids = entriesRef.current.map((e) => e.id)
      const containerRect = container.getBoundingClientRect()
      // Sections that render nothing (content-gated aux entries) are simply not
      // in the DOM; they drop out of the measurement instead of pinning a stale
      // highlight.
      const tops: { id: string; top: number }[] = []
      for (const id of ids) {
        const el = document.getElementById(id)
        if (el) tops.push({ id, top: el.getBoundingClientRect().top - containerRect.top })
      }
      const scrollable = container.scrollHeight - container.clientHeight
      // Genuinely scrolled to the bottom (and the content was long enough to
      // scroll at all — otherwise "at the bottom" is trivially true for a report
      // shorter than the viewport and the spy would jump to the LAST section on
      // arrival). At the bottom the last rendered section is current even though
      // its top can never reach the eye line (the short closing disclaimer).
      const scrolledToEnd = scrollable > 2 && container.scrollTop >= scrollable - 2
      const next = scrolledToEnd
        ? (tops[tops.length - 1]?.id ?? null)
        : pickActiveSection(tops, container.clientHeight * EYE_LINE_RATIO)
      if (next) setActiveId(next)

      setProgress(scrollable > 0 ? Math.min(1, Math.max(0, container.scrollTop / scrollable)) : 0)
    }
    const schedule = (): void => {
      if (frame === 0) frame = requestAnimationFrame(measure)
    }

    measure()
    container.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return () => {
      if (frame !== 0) cancelAnimationFrame(frame)
      container.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
  }, [entryIdKey])

  const subHeadings = useActiveChapterHeadings(activeId || null, currentArtifactId)

  // The unnumbered note sections, presented as their own group below the
  // numbered spine (see the nav comment). Page order is preserved inside it.
  const noteEntries = entries.filter((entry) => entry.kind === 'aux')

  const backToTop = (): void => {
    document.getElementById(SCROLL_CONTAINER_ID)?.scrollTo?.({ top: 0, behavior: 'smooth' })
  }

  return (
    <aside
      data-testid="report-left-rail"
      aria-label={t('report.leftRail.label')}
      style={{
        position: 'sticky',
        top: 64,
        alignSelf: 'start',
        maxHeight: 'calc(100vh - 80px)',
        display: 'flex',
        flexDirection: 'column',
        paddingTop: 18,
        minHeight: 0,
      }}
    >
      {/* identity card */}
      <div
        style={{
          border: '1px solid var(--border-soft)',
          borderRadius: 'var(--radius-md)',
          background: 'var(--bg-card)',
          padding: '14px 15px',
          marginBottom: 18,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 3 }}>
          <span
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 19,
              fontWeight: 600,
              letterSpacing: '0.5px',
              color: 'var(--text-primary)',
            }}
          >
            {ticker}
          </span>
          {verdictText && tone && (
            <span
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 11,
                fontWeight: 600,
                letterSpacing: '0.16em',
                padding: '3px 9px',
                borderRadius: 6,
                background: tone.bg,
                color: tone.fg,
                border: `1px solid ${tone.border}`,
              }}
            >
              {verdictLabel(verdictText)}
            </span>
          )}
        </div>
        {companyName && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 11 }}>
            {companyName}
          </div>
        )}
        {typeof targetPrice === 'number' ? (
          <>
            <div
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 17,
                fontWeight: 600,
                color: 'var(--text-primary)',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {formatCurrency(targetPrice, quoteCurrency, locale, 2)}
            </div>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 10.5,
                color: 'var(--text-muted)',
                marginTop: 2,
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {t('report.leftRail.targetLabel')}
              {typeof snapshotPrice === 'number' &&
                ` · ${t('report.leftRail.spotLabel')} ${formatCurrency(snapshotPrice, quoteCurrency, locale, 2)}`}
            </div>
          </>
        ) : (
          // No point target. Two very different meanings — show the RIGHT one:
          //   • fairlyValued → price sits inside the fair-value range → "Fairly Valued"
          //     (a confident HOLD conclusion, NOT a failure). Same label the chips
          //     use (targetRange.fairValueLabel).
          //   • otherwise → genuine withhold (M&A / single-method) → "WITHHELD",
          //     mirroring the version row.
          // Spot stays as a small labelled caption: context, never the headline.
          <>
            <div
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 15,
                fontWeight: 600,
                letterSpacing: '0.04em',
                color: fairlyValued ? 'var(--text-secondary)' : 'var(--text-muted)',
              }}
            >
              {fairlyValued ? t('targetRange.fairValueLabel') : verdictLabel('WITHHELD', locale)}
            </div>
            {typeof snapshotPrice === 'number' && (
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10.5,
                  color: 'var(--text-muted)',
                  marginTop: 2,
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {t('report.leftRail.spotLabel')}{' '}
                {formatCurrency(snapshotPrice, quoteCurrency, locale, 2)}
              </div>
            )}
          </>
        )}
        <RailSessionChange session={priceSession} currency={quoteCurrency} asOf={snapshotAsOf} />
        {verdictText && (
          <div style={{ marginTop: 10 }}>
            <ConfidenceChip tier={tier} />
          </div>
        )}
      </div>

      {/* tab switch */}
      <div
        role="tablist"
        aria-label={t('report.toc.tabsLabel')}
        style={{
          display: 'flex',
          gap: 20,
          borderBottom: '1px solid var(--border-soft)',
          marginBottom: 12,
        }}
      >
        <RailTab
          id="rail-tab-contents"
          panelId="rail-panel-contents"
          active={tab === 'contents'}
          onClick={() => setTab('contents')}
          onArrow={() => setTab('versions')}
        >
          {t('report.toc.heading')}
        </RailTab>
        <RailTab
          id="rail-tab-versions"
          panelId="rail-panel-versions"
          active={tab === 'versions'}
          onClick={() => setTab('versions')}
          onArrow={() => setTab('contents')}
        >
          {t('report.timeline.versionCount', { count: sameTypeCount })}
        </RailTab>
      </div>

      {/* tab body — scrolls within the sticky rail */}
      <div style={{ overflowY: 'auto', minHeight: 0, paddingRight: 4, paddingBottom: 12 }}>
        <div
          id="rail-panel-contents"
          role="tabpanel"
          aria-labelledby="rail-tab-contents"
          hidden={tab !== 'contents'}
        >
          {/* Reading progress: the rail is the only persistent chrome on a long
              scroll, so it carries the "how much is left" signal. */}
          <div
            role="progressbar"
            aria-label={t('report.toc.progressLabel')}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(progress * 100)}
            data-testid="report-read-progress"
            style={{
              height: 2,
              background: 'var(--border-soft)',
              borderRadius: 2,
              marginBottom: 10,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${Math.round(progress * 100)}%`,
                height: '100%',
                background: 'var(--secondary)',
                transition: 'width 0.12s linear',
              }}
            />
          </div>

          <nav aria-label={t('report.toc.navLabel')}>
            {/* Presentation is TWO groups, in this order:
                  1. the numbered chapter spine, ascending 01…15;
                  2. the unnumbered note sections, in page order.
                The manifest keeps page order (the body render order and the hash
                validator both depend on it — see ReportChapters.sections.test),
                but the rail re-groups for reading: interleaving a § row between
                01 and 02 broke the NUMBER sequence, so the listing read as
                shuffled even though every number was correct. */}
            {entries
              .filter((entry) => entry.kind === 'chapter')
              .map((entry) => (
                <TocEntry
                  key={entry.id}
                  entry={entry}
                  active={entry.id === activeId}
                  subHeadings={subHeadings}
                />
              ))}

            {noteEntries.length > 0 && (
              <>
                <div
                  style={{
                    margin: '14px 0 4px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 9.5,
                    letterSpacing: '0.16em',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                  }}
                >
                  {t('report.toc.auxHeading')}
                </div>
                {noteEntries.map((entry) => (
                  <TocEntry
                    key={entry.id}
                    entry={entry}
                    active={entry.id === activeId}
                    subHeadings={subHeadings}
                  />
                ))}
              </>
            )}
          </nav>

          {/* Back-to-top: the report runs 15 chapters + appendices, so returning
              to the cover should not require a long reverse scroll. */}
          <button
            type="button"
            onClick={backToTop}
            data-testid="report-back-to-top"
            style={{
              marginTop: 12,
              padding: '5px 0',
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              color: 'var(--text-secondary)',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            ↑ {t('report.toc.backToTop')}
          </button>
        </div>

        <div
          id="rail-panel-versions"
          role="tabpanel"
          aria-labelledby="rail-tab-versions"
          hidden={tab !== 'versions'}
        >
          <VersionTimelineList
            ticker={ticker}
            currentArtifactId={currentArtifactId}
            timeline={timeline}
            reportType={reportType}
          />
        </div>
      </div>
    </aside>
  )
}

/** One table-of-contents row: number/marker + title, and — while it is the
 *  section the reader is in — that section's own sub-headings beneath it.
 *
 *  Contrast: inactive rows sit at --text-secondary (not --text-muted) because the
 *  TOC is the only way to read the report's structure, and the muted tier left the
 *  titles fainter than the surrounding chrome; the number/marker keeps a lighter
 *  tier than its title so the entry still reads as one line. */
function TocEntry({
  entry,
  active,
  subHeadings,
}: {
  entry: ReportSectionEntry
  active: boolean
  subHeadings: { id: string; label: string }[]
}): React.ReactElement {
  return (
    <div>
      <a
        href={`#${entry.id}`}
        data-testid={`toc-${entry.id}`}
        data-active={active ? 'true' : 'false'}
        // aria-current="location" = "current position within a document", which is
        // exactly what a TOC entry is. The colour change alone was invisible to
        // assistive tech.
        aria-current={active ? 'location' : undefined}
        style={{
          display: 'flex',
          gap: 9,
          alignItems: 'baseline',
          padding: '6px 0',
          textDecoration: 'none',
          fontFamily: 'var(--font-body)',
          fontSize: 12,
          lineHeight: 1.3,
          color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
          transition: 'color 0.16s',
        }}
      >
        <span
          aria-hidden
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: entry.kind === 'aux' ? 9 : 10,
            color: active ? 'var(--secondary)' : 'var(--text-muted)',
            width: 16,
            flexShrink: 0,
          }}
        >
          {/* Auxiliary sections carry no chapter number — a marker keeps the
              numbered spine visually distinct. */}
          {entry.kind === 'aux' ? '§' : entry.num}
        </span>
        {entry.title}
      </a>
      {/* Second level: the active section's own sub-headings. Only the active one
          expands, so the rail stays scannable. */}
      {active && subHeadings.length > 0 && (
        <div data-testid={`toc-sub-${entry.id}`} style={{ marginBottom: 4 }}>
          {subHeadings.map((sub) => (
            <a
              key={sub.id}
              href={`#${sub.id}`}
              style={{
                display: 'block',
                padding: '3px 0 3px 25px',
                textDecoration: 'none',
                fontFamily: 'var(--font-body)',
                fontSize: 11,
                lineHeight: 1.3,
                color: 'var(--text-muted)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {sub.label}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

function RailTab({
  id,
  panelId,
  active,
  onClick,
  onArrow,
  children,
}: {
  id: string
  panelId: string
  active: boolean
  onClick: () => void
  /** Move focus/selection to the sibling tab (APG: arrow keys move between tabs). */
  onArrow: () => void
  children: React.ReactNode
}): React.ReactElement {
  return (
    <button
      type="button"
      id={id}
      role="tab"
      aria-selected={active}
      aria-controls={panelId}
      // Roving tabindex: only the selected tab is in the tab order.
      tabIndex={active ? 0 : -1}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          e.preventDefault()
          onArrow()
        }
      }}
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        color: active ? 'var(--secondary)' : 'var(--text-secondary)',
        background: 'transparent',
        border: 'none',
        borderBottom: `1.5px solid ${active ? 'var(--secondary)' : 'transparent'}`,
        padding: '4px 0 9px',
        marginBottom: -1,
        cursor: 'pointer',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </button>
  )
}

/** The prior-close → last-close move, as a caption under the spot.
 *
 * The data layer computed this at fetch time and `builders.py` froze it into the
 * artifact, and NOTHING rendered it: the rail's headline is the TARGET, so the
 * spot caption is the only place the price appears as context — its daily change
 * belongs there.
 *
 * `NormalizedPrice.latest_session_change` documents the session as the one
 * `current_price` belongs to, NOT "today", so the copy says "last session" and the
 * tooltip carries the as-of date: a closed-market view must not read as live.
 *
 * Renders NOTHING when the run had fewer than 2 price bars (no session to diff) —
 * never a 0.00, which would claim a flat session that was never measured. */
function RailSessionChange({
  session,
  currency,
  asOf,
}: {
  session?: PriceSessionShape | null
  currency: string
  asOf?: string | null
}): React.ReactElement | null {
  const { locale, t } = useI18n()
  const change = session?.latest_session_change
  const pct = session?.latest_session_change_pct
  if (typeof change !== 'number' || !Number.isFinite(change)) return null

  const flat = change === 0
  // Up/down is a colour + glyph pair, never colour alone (CVD-safe).
  const tone = flat ? 'var(--text-muted)' : change > 0 ? 'var(--success)' : 'var(--danger)'
  const arrow = flat ? '·' : change > 0 ? '▲' : '▼'
  const hasPct = typeof pct === 'number' && Number.isFinite(pct)

  return (
    <div
      data-testid="rail-session-change"
      title={
        asOf
          ? t('report.leftRail.sessionChangeTitle', { date: formatDate(asOf, locale, 'short') })
          : undefined
      }
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 5,
        marginTop: 4,
        fontFamily: 'var(--font-mono)',
        fontSize: 10.5,
        color: tone,
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      <span>
        {arrow} {change > 0 ? '+' : ''}
        {formatCurrency(change, currency, locale, 2)}
      </span>
      {hasPct && (
        <span>
          ({pct > 0 ? '+' : ''}
          {formatPercent(pct, locale, 2, true)})
        </span>
      )}
      <span style={{ color: 'var(--text-muted)' }}>{t('report.leftRail.lastSession')}</span>
    </div>
  )
}
