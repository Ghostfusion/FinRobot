// The section manifest is the single ordering source for the rail, the body and
// the deep-link validator. ReportChapters.sections.test.tsx proves the BODY
// matches it; this proves the manifest itself — the chapter spine is intact, the
// auxiliary sections appear in page order, and each is gated by its own flag.

import { describe, it, expect } from 'vitest'

import {
  AUX_SECTION_IDS,
  isReportSectionId,
  reportSectionEntries,
  type ReportSectionPresence,
} from './reportSections'
import { CHAPTER_ORDER, chapterNum } from './chapters/labels'

const NOTHING: ReportSectionPresence = {
  versionDiff: false,
  audit: false,
  summary: false,
  warnings: false,
}

const EVERYTHING: ReportSectionPresence = {
  versionDiff: true,
  audit: true,
  summary: true,
  warnings: true,
}

describe('reportSectionEntries — chapter spine', () => {
  it('is exactly the numbered chapters when no optional section has content', () => {
    const entries = reportSectionEntries('en', NOTHING)
    expect(entries.map((e) => e.id)).toEqual([...CHAPTER_ORDER])
    expect(entries.every((e) => e.kind === 'chapter')).toBe(true)
  })

  it('numbers the chapters 01..15 in reading order', () => {
    const entries = reportSectionEntries('en', NOTHING)
    expect(entries.map((e) => e.num)).toEqual(CHAPTER_ORDER.map((id) => chapterNum(id)))
    expect(entries.at(-1)?.num).toBe('15')
  })

  it('carries the localized title of every chapter', () => {
    const zh = reportSectionEntries('zh', NOTHING)
    expect(zh.find((e) => e.id === 'filings')?.title).toBe('申报文件与 XBRL')
    const en = reportSectionEntries('en', NOTHING)
    expect(en.find((e) => e.id === 'filings')?.title).toBe('Filings & XBRL')
  })
})

describe('reportSectionEntries — auxiliary sections', () => {
  it('places each optional section where the body renders it', () => {
    expect(reportSectionEntries('en', EVERYTHING).map((e) => e.id)).toEqual([
      'report-version-diff',
      'report-audit-banner',
      'cover',
      'report-summary',
      ...CHAPTER_ORDER.filter((id) => id !== 'cover'),
      'report-warnings',
    ])
  })

  it('marks them unnumbered aux entries', () => {
    const aux = reportSectionEntries('en', EVERYTHING).filter((e) => e.kind === 'aux')
    expect(aux.map((e) => e.id)).toEqual([...AUX_SECTION_IDS])
    expect(aux.every((e) => e.num === '' && e.title.length > 0)).toBe(true)
  })

  it('gates each entry on its own flag — no cross-talk', () => {
    for (const key of Object.keys(EVERYTHING) as (keyof ReportSectionPresence)[]) {
      const entries = reportSectionEntries('en', { ...NOTHING, [key]: true })
      const aux = entries.filter((e) => e.kind === 'aux')
      expect(aux).toHaveLength(1)
      expect(aux[0].id).toBe(
        {
          versionDiff: 'report-version-diff',
          audit: 'report-audit-banner',
          summary: 'report-summary',
          warnings: 'report-warnings',
        }[key],
      )
      // The chapter spine is untouched by any optional section.
      expect(entries.filter((e) => e.kind === 'chapter').map((e) => e.id)).toEqual([
        ...CHAPTER_ORDER,
      ])
    }
  })
})

describe('isReportSectionId', () => {
  it('accepts every chapter id and every auxiliary section id', () => {
    for (const id of [...CHAPTER_ORDER, ...AUX_SECTION_IDS]) {
      expect(isReportSectionId(id)).toBe(true)
    }
  })

  it('rejects anything else — a typo or stale hash is not a silent no-op', () => {
    for (const id of ['', 'thesis-2', 'chapter-1', '#cover', 'report-summary-2', 'valuation ']) {
      expect(isReportSectionId(id)).toBe(false)
    }
  })
})
