// The report's navigable sections, in the order they appear on the page.
//
// ONE source of truth for three consumers that used to be able to disagree:
//   • the left rail's table of contents (ReportLeftRail)
//   • the report body's render order (ReportChapters)
//   • deep-link / hash validation (ArtifactDetailPage)
//
// The report is no longer "just the 14 numbered chapters": three sections that
// carry real reader-visible content have no chapter number —
//   report-version-diff  "what changed vs the prior version" (app chrome)
//   report-audit-banner  the data-caveat / output-contract findings
//   report-summary       the pipeline's own analysis summary
//   report-warnings      caveats + collapsed methodology notes
// — and omitting them from the TOC (the pre-2026-10 state) made body sections
// unreachable from the nav, which is exactly what the TOC is for. They are
// `aux` entries: unnumbered, content-gated (never listed when they render
// nothing), and rendered with a marker instead of a number.
//
// Presence gates are NOT re-derived here: each owning component exports the
// predicate it renders by (hasPriorVersion / auditBannerVisible /
// hasComputeWarnings), so the nav can never list a section the body drops or
// hide one it renders.
//
// ⚠ REPORT_SECTION_TEMPLATE is the page order. ReportChapters renders in this
// same order and ReportChapters.sections.test.tsx asserts the rendered DOM
// matches the manifest — a reorder that touches one and not the other fails the
// suite instead of silently mis-numbering the report.

import type { Locale } from '../../i18n'
import { CHAPTER_ORDER, chapterLabel, type ChapterId } from './chapters/labels'

/** Sections that are part of the report but not numbered chapters. */
export const AUX_SECTION_IDS = [
  'report-version-diff',
  'report-audit-banner',
  'report-summary',
  'report-warnings',
] as const

export type AuxSectionId = (typeof AUX_SECTION_IDS)[number]

export type ReportSectionKind = 'chapter' | 'aux'

/** Is this a section id the report can carry at all — the chapter spine or one of
 *  the auxiliary sections? Used to validate a URL hash: an unknown id is a typo or
 *  a stale link and is reported as such instead of silently scrolling nowhere.
 *  Membership is static; whether an aux section actually RENDERS still depends on
 *  the artifact (see ReportSectionPresence), so a hash naming an absent aux
 *  section resolves to nothing without being called a typo. */
export function isReportSectionId(id: string): id is ChapterId | AuxSectionId {
  return (
    (CHAPTER_ORDER as readonly string[]).includes(id) ||
    (AUX_SECTION_IDS as readonly string[]).includes(id)
  )
}

export interface ReportSectionEntry {
  /** DOM id of the <section> (also the URL hash target). */
  id: string
  /** Two-digit chapter number; '' for auxiliary sections. */
  num: string
  title: string
  sub?: string
  kind: ReportSectionKind
}

/** Which optional sections the current artifact actually renders. Computed by
 *  the callers from the same predicates the sections themselves use. */
export interface ReportSectionPresence {
  /** A prior same-type version exists → VersionDiffBanner renders (app only). */
  versionDiff: boolean
  /** ChapterAuditBanner has a finding / contract row / withhold to show. */
  audit: boolean
  /** outputs.summary_text carries text. */
  summary: boolean
  /** ComputeWarningsPanel has caveats / formula warnings / methodology notes. */
  warnings: boolean
}

/** Short, stable section titles (the same inline-table convention as
 *  chapters/labels.ts — these are report copy, not app chrome). */
const AUX_LABELS: Record<AuxSectionId, Record<Locale, string>> = {
  'report-version-diff': { zh: '与上一版本的变化', en: 'Changes vs Prior Version' },
  'report-audit-banner': { zh: '数据审计与输出合约', en: 'Data Audit & Output Contract' },
  'report-summary': { zh: '分析摘要（引擎记录）', en: 'Analysis Summary (engine record)' },
  'report-warnings': { zh: '风险提示与方法说明', en: 'Caveats & Methodology Notes' },
}

type Slot =
  | { kind: 'chapter'; id: ChapterId }
  | { kind: 'aux'; id: AuxSectionId; presence: keyof ReportSectionPresence }

/** The page order. The four aux slots are content-gated; everything else is a
 *  chapter that always renders (its own chapter body may show a gap note). */
const REPORT_SECTION_TEMPLATE: readonly Slot[] = [
  { kind: 'aux', id: 'report-version-diff', presence: 'versionDiff' },
  { kind: 'aux', id: 'report-audit-banner', presence: 'audit' },
  { kind: 'chapter', id: 'cover' },
  // CFA / peer-report convention: a summary sits behind the cover and ahead of
  // the argument. Collapsed by default (see ChapterAnalysisSummary) so it can
  // never push the cover→thesis flow down the page.
  { kind: 'aux', id: 'report-summary', presence: 'summary' },
  ...CHAPTER_ORDER.filter((id) => id !== 'cover').map((id): Slot => ({ kind: 'chapter', id })),
  { kind: 'aux', id: 'report-warnings', presence: 'warnings' },
]

/** The report's sections in page order, with the unrendered optional ones dropped. */
export function reportSectionEntries(
  locale: Locale,
  presence: ReportSectionPresence,
): ReportSectionEntry[] {
  const entries: ReportSectionEntry[] = []
  for (const slot of REPORT_SECTION_TEMPLATE) {
    if (slot.kind === 'aux') {
      if (!presence[slot.presence]) continue
      entries.push({
        id: slot.id,
        num: '',
        title: AUX_LABELS[slot.id][locale],
        kind: 'aux',
      })
      continue
    }
    const label = chapterLabel(slot.id, locale)
    entries.push({
      id: slot.id,
      num: label.num,
      title: label.title,
      sub: label.sub,
      kind: 'chapter',
    })
  }
  return entries
}
