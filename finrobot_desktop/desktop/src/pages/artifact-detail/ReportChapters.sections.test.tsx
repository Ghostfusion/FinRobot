// C3 guard — the rendered report body must match the section manifest.
//
// Why this exists: the report had TWO sources of order (labels.ts numbering/nav
// vs the hardcoded JSX sequence in ReportChapters.tsx) with a comment warning
// that they had to be reordered in lockstep and NOTHING enforcing it.
// labels.test.ts pins CHAPTER_ORDER against a literal, and every other consumer
// test mocks ReportChapters — so a reorder that touched one side shipped green
// and mis-numbered the report. This renders the REAL component and compares the
// rendered <section id> sequence with reportSections().
//
// It also fails on an id-bearing <section> the manifest does not list (a section
// added to the body but not to the nav), and on a listed section that never
// renders.

import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { ReportChapters } from './ReportChapters'
import { reportSectionEntries, type ReportSectionPresence } from './reportSections'
import { auditBannerContent, type NumericAuditShape } from './chapters'
import { hasComputeWarnings } from './ComputeWarningsPanel'
import { layerComputeWarnings, parseSurfacedContractFindings } from './reportData'
import { CHAPTER_ORDER } from './chapters/labels'
import { priorVersions } from '../../lib/artifactVersions'
import type { ArtifactDetail } from '../../hooks/useV5Artifacts'
import type { ArtifactSummaryV5 } from '../../types/v5'

// No live backend in jsdom: the earnings-call query would otherwise hit the net.
vi.stubGlobal(
  'fetch',
  vi.fn(() => Promise.reject(new Error('network disabled in this test'))),
)

function artifact(outputs: Record<string, unknown>): ArtifactDetail {
  return {
    id: 'art-1',
    ticker: 'AAA',
    type: 'equity_research',
    created_at: '2026-06-01T00:00:00+00:00',
    outputs,
    inputs: { data_source: 'FMP', data_fetched_at: '2026-06-01T00:00:00+00:00', raw_data: {} },
    assumptions: {},
    meta: { created_at: '2026-06-01T00:00:00+00:00', language: 'en' },
  }
}

function renderIds(art: ArtifactDetail, timeline: ArtifactSummaryV5[]): string[] {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const { container } = render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ReportChapters artifact={art} timeline={timeline} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return [...container.querySelectorAll('section[id]')].map((el) => el.id)
}

function summary(id: string): ArtifactSummaryV5 {
  return {
    id,
    ticker: 'AAA',
    cross_tickers: [],
    type: 'equity_research',
    created_at: '2026-05-01T00:00:00+00:00',
    headline: 'h',
    source: 'pipeline:equity_research',
    archived: false,
  }
}

/** The artifact root's `compute_version.formula_warnings`. The published
 *  ArtifactDetail type omits it (each pipeline writes its own root keys), so this
 *  narrows instead of trusting a cast. */
function formulaWarningsOf(art: ArtifactDetail): string[] {
  // `outputs` is listed so this stays a real (non-weak) view of the artifact —
  // no cast, and a fixture type change still fails loudly here.
  const root: { outputs: Record<string, unknown>; compute_version?: unknown } = art
  const candidate = root.compute_version
  if (
    candidate !== null &&
    typeof candidate === 'object' &&
    'formula_warnings' in candidate &&
    Array.isArray(candidate.formula_warnings)
  ) {
    return candidate.formula_warnings.filter((w): w is string => typeof w === 'string')
  }
  return []
}

/** Mirror of ArtifactDetailPage's manifest construction — same exported
 *  predicates the sections render by, so the test compares like with like. */
function expectedIds(art: ArtifactDetail, timeline: ArtifactSummaryV5[]): string[] {
  const outputs = (art.outputs ?? {}) as Record<string, unknown>
  const structured = (outputs['structured'] ?? {}) as Record<string, unknown>
  const warnings = (outputs['warnings'] as string[] | undefined) ?? []
  const layered = layerComputeWarnings(warnings)
  const presence: ReportSectionPresence = {
    versionDiff: priorVersions(timeline, art.type, art.id).length > 0,
    audit: auditBannerContent(
      (structured['numeric_audit'] ?? null) as NumericAuditShape | null,
      parseSurfacedContractFindings(warnings),
    ).visible,
    summary: String(outputs['summary_text'] ?? '').trim().length > 0,
    warnings: hasComputeWarnings(layered.caveats, layered.methodologyNotes, formulaWarningsOf(art)),
  }
  return reportSectionEntries('en', presence).map((e) => e.id)
}

describe('ReportChapters render order == section manifest', () => {
  it('renders exactly the 15 chapters, in CHAPTER_ORDER, when nothing optional exists', () => {
    const outputs = { structured: {}, warnings: [] }
    expect(renderIds(artifact(outputs), [])).toEqual([...CHAPTER_ORDER])
  })

  it('adds the auxiliary sections (version diff · audit · summary · caveats) with their content', () => {
    const outputs = {
      structured: {},
      summary_text: 'The engine ran the eight-step pipeline and concluded HOLD.',
      warnings: [
        '[CONTRACT/C1] headline target 2172.00 is 2.5x the entry price 864.00, outside the band',
        'Peer multiples computed on a subset — 3 of 6 peers.',
      ],
    }
    const timeline = [summary('art-1'), summary('art-0')] // art-0 is the prior version

    // Pinned explicitly (not just via the manifest helper) so a manifest that
    // drops an aux entry cannot make the two sides agree on the wrong thing.
    // `report-version-diff` is absent by design: that section is report CHROME
    // (VersionDiffBanner), mounted by ArtifactDetailPage above this body and not
    // part of the export — the rail links to it, the body never renders it.
    expect(renderIds(artifact(outputs), timeline)).toEqual([
      'report-audit-banner',
      'cover',
      'report-summary',
      ...CHAPTER_ORDER.filter((id) => id !== 'cover'),
      'report-warnings',
    ])
  })

  it('the manifest and the DOM agree for both a bare and a fully-populated artifact', () => {
    // The body never renders report-version-diff (chrome, see above) — everything
    // else the manifest lists must be here, in the manifest's order.
    const bodyIds = (art: ArtifactDetail, timeline: ArtifactSummaryV5[]): string[] =>
      expectedIds(art, timeline).filter((id) => id !== 'report-version-diff')

    const bare = artifact({ structured: {}, warnings: [] })
    expect(renderIds(bare, [])).toEqual(bodyIds(bare, []))

    const rich = artifact({
      structured: {},
      summary_text: 'summary',
      warnings: ['[CONTRACT/C1] withheld', 'Trailing-twelve-month TTM derived from quarters'],
    })
    const timeline = [summary('art-1'), summary('art-0')]
    expect(renderIds(rich, timeline)).toEqual(bodyIds(rich, timeline))
  })

  it('drops the caveats entry when the artifact carries no warnings at all', () => {
    const ids = renderIds(artifact({ structured: {}, warnings: [] }), [])
    expect(ids).not.toContain('report-warnings')
    expect(ids).not.toContain('report-summary')
    expect(ids).not.toContain('report-audit-banner')
  })
})
