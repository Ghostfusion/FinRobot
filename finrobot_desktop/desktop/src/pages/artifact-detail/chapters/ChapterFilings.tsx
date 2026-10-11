// Chapter 13 — Filings & XBRL. The primary-source appendix: WHICH SEC filings
// the run actually read (10-K, the 10-Q history, the 8-K event record), what the
// extracted 10-K sections look like, and the XBRL concept snapshot the numbers
// were reconciled against — each with a link to the filing on sec.gov.
//
// Why it exists: `structured.sec_filings` / `structured.xbrl_facts_snapshot` have
// been persisted since the SEC wiring landed and were rendered NOWHERE, so the
// report could state "10-K" without ever showing the filing it came from. An
// analyst checking a number had to leave the product.
//
// Deliberately an INDEX, not a text dump: the 10-K payload also carries the full
// section text (hundreds of KB) — that belongs to the artifact's audit trail /
// RAG store, not to a reading surface. This chapter shows section availability
// and extraction quality, so a fallback-extracted MD&A is visible as such.
//
// The material 8-K items are READ in the Catalyst Signal chapter (the pipeline
// turns non-routine items into catalysts); this chapter is the filing index, so
// the two never restate each other.

import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'

import { Chapter, SubChapter, TableScroll, tableStyle } from './ChapterBase'
import type {
  SecEvent8KShape,
  SecFilingsShape,
  SecFilingSectionShape,
  SecTenQShape,
  XbrlFactShape,
  XbrlFactsSnapshotShape,
} from './types'
import type { Locale } from '../../../i18n'
import { useI18n } from '../../../i18n'
import { formatCompactNumber, formatDate } from '../../../utils/format'

interface Props {
  /** structured.sec_filings — the 10-K / 10-Q / 8-K payloads the data step read. */
  filings: SecFilingsShape | null
  /** structured.xbrl_facts_snapshot — us-gaap concept → fact list. */
  xbrl: XbrlFactsSnapshotShape | null
}

export function ChapterFilings({ filings, xbrl }: Props): React.ReactElement {
  const { locale } = useI18n()
  const tenK = filings?.['10k'] ?? null
  const tenQs = newestFirst(filings?.['10q_history'])
  const eightKs = newestFirst(filings?.['8k_events'])

  // Flatten the concept-keyed bag into rows. Each key owns a fact LIST; a legacy
  // or hand-edited artifact can carry anything, so guard instead of asserting.
  const xbrlRows: { key: string; fact: XbrlFactShape }[] = []
  for (const [key, facts] of Object.entries(xbrl ?? {})) {
    if (!Array.isArray(facts)) continue
    for (const fact of facts) xbrlRows.push({ key, fact })
  }
  xbrlRows.sort((a, b) => a.key.localeCompare(b.key))

  const hasTenK = tenK?.has_10k === true
  if (!hasTenK && tenQs.length === 0 && eightKs.length === 0 && xbrlRows.length === 0) {
    return (
      <Chapter id="filings">
        <div style={gapCallout}>
          <div style={gapCalloutTitle}>
            {tr('本次运行未附 SEC 申报数据', 'No SEC filing layer in this run', locale)}
          </div>
          <p style={gapCalloutBody}>
            {tr(
              '可能是非美国发行人（无 EDGAR 申报），或尚未在设置中配置 SEC 身份。其余章节的数值来自行情数据源。',
              'Either the issuer files nothing with EDGAR (non-US listing), or the SEC identity is not configured. Every other chapter still reads from the market-data provider.',
              locale,
            )}
          </p>
          <Link to="/settings" style={gapCalloutCta}>
            {tr('前往设置 SEC 身份', 'Configure SEC identity', locale)}
          </Link>
        </div>
      </Chapter>
    )
  }

  return (
    <Chapter id="filings">
      <SubChapter heading={tr('10-K 年报', 'Form 10-K', locale)}>
        {hasTenK && tenK ? (
          <>
            <div style={metaLine}>
              <span>
                {tr('申报日', 'Filed', locale)}{' '}
                <strong style={metaStrong}>
                  {formatDate(tenK.latest_10k_date, locale, 'short')}
                </strong>
              </span>
              {tenK.latest_10k_accession && (
                <span>
                  {tr('编号', 'Accession', locale)}{' '}
                  <span style={metaMono}>{tenK.latest_10k_accession}</span>
                </span>
              )}
              {tenK.is_amended && <span style={badge}>{tr('修订版', 'Amended', locale)}</span>}
              {tenK.sections_extraction_quality && tenK.sections_extraction_quality !== 'ok' && (
                <span style={badgeWarn}>
                  {extractionQualityLabel(tenK.sections_extraction_quality, locale)}
                </span>
              )}
              {tenK.source_url && (
                <a
                  href={tenK.source_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  style={filingLink}
                >
                  {tr('在 sec.gov 查看', 'View on sec.gov', locale)} ↗
                </a>
              )}
            </div>
            <SectionTable sections={tenK.sections ?? []} locale={locale} />
          </>
        ) : (
          <MissingNote>
            {tr('本次运行未取得 10-K。', 'No 10-K was retrieved for this run.', locale)}
          </MissingNote>
        )}
      </SubChapter>

      <SubChapter heading={tr('10-Q 季报历史', 'Form 10-Q History', locale)}>
        {tenQs.length > 0 ? (
          <TableScroll>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>{tr('表格', 'Form', locale)}</th>
                  <th style={thStyle}>{tr('申报日', 'Filed', locale)}</th>
                  <th style={thStyle}>{tr('报告期', 'Period', locale)}</th>
                  <th style={thStyle}>{tr('编号', 'Accession', locale)}</th>
                  <th style={thStyle}>{tr('来源', 'Source', locale)}</th>
                </tr>
              </thead>
              <tbody>
                {tenQs.map((row) => (
                  <TenQRow key={row.accession_no} row={row} locale={locale} />
                ))}
              </tbody>
            </table>
          </TableScroll>
        ) : (
          <MissingNote>
            {tr('本次运行未取得 10-Q。', 'No 10-Q was retrieved for this run.', locale)}
          </MissingNote>
        )}
      </SubChapter>

      <SubChapter heading={tr('8-K 重大事项', 'Form 8-K Events', locale)}>
        {eightKs.length > 0 ? (
          <>
            <TableScroll>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>{tr('申报日', 'Filed', locale)}</th>
                    <th style={thStyle}>{tr('事项', 'Items', locale)}</th>
                    <th style={thStyle}>{tr('来源', 'Source', locale)}</th>
                  </tr>
                </thead>
                <tbody>
                  {eightKs.map((row) => (
                    <EightKRow key={row.accession_no} row={row} locale={locale} />
                  ))}
                </tbody>
              </table>
            </TableScroll>
            <p style={footNote}>
              {tr(
                '此处仅为申报索引；非例行事项已在「催化剂信号」章节按语义解读。',
                'Filing index only — non-routine items are read semantically in the Catalyst Signal chapter.',
                locale,
              )}
            </p>
          </>
        ) : (
          <MissingNote>
            {tr('本次运行未取得 8-K。', 'No 8-K was retrieved for this run.', locale)}
          </MissingNote>
        )}
      </SubChapter>

      <SubChapter heading={tr('XBRL 科目快照', 'XBRL Concept Snapshot', locale)}>
        {xbrlRows.length > 0 ? (
          <TableScroll>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>{tr('us-gaap 科目', 'us-gaap concept', locale)}</th>
                  <th style={{ ...thStyle, textAlign: 'right' }}>{tr('数值', 'Value', locale)}</th>
                  <th style={thStyle}>{tr('期末', 'Period end', locale)}</th>
                  <th style={thStyle}>{tr('单位', 'Units', locale)}</th>
                </tr>
              </thead>
              <tbody>
                {xbrlRows.map(({ key, fact }, i) => (
                  <tr key={`${key}-${i}`}>
                    <td style={{ ...tdStyle, fontFamily: 'var(--font-mono)', fontSize: 11.5 }}>
                      {key}
                    </td>
                    <td
                      style={{ ...tdStyle, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}
                    >
                      {formatCompactNumber(fact.value, locale)}
                    </td>
                    <td style={tdStyle}>{formatDate(fact.period_end, locale, 'short')}</td>
                    <td style={tdStyle}>{fact.units ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableScroll>
        ) : (
          <MissingNote>
            {tr(
              '本次运行未取得 XBRL 科目（对账使用）。',
              'No XBRL facts were retrieved for this run (they are used for reconciliation).',
              locale,
            )}
          </MissingNote>
        )}
      </SubChapter>
    </Chapter>
  )
}

/** 10-K extracted sections: availability + extraction route, never the text. */
function SectionTable({
  sections,
  locale,
}: {
  sections: SecFilingSectionShape[]
  locale: Locale
}): React.ReactElement {
  if (sections.length === 0) {
    return (
      <MissingNote>
        {tr(
          '10-K 已取得，但未抽取到章节正文。',
          'The 10-K was retrieved but no sections were extracted.',
          locale,
        )}
      </MissingNote>
    )
  }
  return (
    <TableScroll>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>{tr('章节', 'Section', locale)}</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>{tr('字符数', 'Chars', locale)}</th>
            <th style={thStyle}>{tr('抽取方式', 'Extracted via', locale)}</th>
          </tr>
        </thead>
        <tbody>
          {sections.map((s) => (
            <tr key={s.canonical_id}>
              <td style={tdStyle}>{s.title}</td>
              <td style={{ ...tdStyle, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                {/* char_count is authoritative; text length is the fallback for a
                    payload that predates it. */}
                {formatCompactNumber(s.char_count ?? s.text?.length ?? 0, locale)}
              </td>
              <td style={tdStyle}>{extractionRouteLabel(s.extracted_via, locale)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableScroll>
  )
}

function TenQRow({ row, locale }: { row: SecTenQShape; locale: Locale }): React.ReactElement {
  return (
    <tr>
      <td style={tdStyle}>{row.form}</td>
      <td style={tdStyle}>{formatDate(row.filing_date, locale, 'short')}</td>
      <td style={tdStyle}>{formatDate(row.period_of_report, locale, 'short')}</td>
      <td style={{ ...tdStyle, fontFamily: 'var(--font-mono)', fontSize: 11.5 }}>
        {row.accession_no}
      </td>
      <td style={tdStyle}>
        <SourceLink url={row.source_url ?? null} locale={locale} />
      </td>
    </tr>
  )
}

function EightKRow({ row, locale }: { row: SecEvent8KShape; locale: Locale }): React.ReactElement {
  return (
    <tr>
      <td style={tdStyle}>{formatDate(row.filing_date, locale, 'short')}</td>
      <td style={tdStyle}>{row.items && row.items.length > 0 ? row.items.join(', ') : '—'}</td>
      <td style={tdStyle}>
        <SourceLink url={row.source_url ?? null} locale={locale} />
      </td>
    </tr>
  )
}

function SourceLink({ url, locale }: { url: string | null; locale: Locale }): React.ReactElement {
  if (!url) return <span style={{ color: 'var(--text-dim)' }}>—</span>
  return (
    <a href={url} target="_blank" rel="noreferrer noopener" style={filingLink}>
      {tr('查看', 'Open', locale)} ↗
    </a>
  )
}

function MissingNote({ children }: { children: React.ReactNode }): React.ReactElement {
  return <div style={missingNote}>{children}</div>
}

function tr(zh: string, en: string, locale: Locale): string {
  return locale === 'en' ? en : zh
}

/** The 10-K's section-extraction quality → analyst language. */
function extractionQualityLabel(quality: string, locale: Locale): string {
  if (quality === 'amended_redirected') {
    return tr('已改用原始 10-K', 'Redirected to the original 10-K', locale)
  }
  if (quality === 'fallback_to_full_text') {
    return tr('回退至全文', 'Fell back to full text', locale)
  }
  return quality
}

/** Per-section extraction route → analyst language (never the raw machine token). */
function extractionRouteLabel(via: string | undefined, locale: Locale): string {
  if (via === 'edgartools_attribute') return tr('结构化属性', 'Structured attribute', locale)
  if (via === 'filing_text_fallback') return tr('全文回退', 'Full-text fallback', locale)
  return via ?? '—'
}

/** Newest filing first. The provider already returns them in that order; sorting
 *  defensively keeps the table honest for a re-serialized artifact. */
function newestFirst<T extends { filing_date: string }>(rows: T[] | undefined): T[] {
  return [...(rows ?? [])].sort((a, b) => (a.filing_date < b.filing_date ? 1 : -1))
}

const thStyle: CSSProperties = {
  textAlign: 'left',
  padding: '10px 14px',
  fontSize: 10.5,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  fontWeight: 500,
  borderBottom: '1px solid var(--border-soft)',
}

const tdStyle: CSSProperties = {
  padding: '10px 14px',
  fontSize: 12,
  color: 'var(--text-secondary)',
  borderBottom: '1px solid var(--border-hairline)',
}

const metaLine: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 14,
  margin: '2px 0 12px',
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  color: 'var(--text-muted)',
}

const metaStrong: CSSProperties = {
  color: 'var(--text-primary)',
  fontWeight: 600,
}

const metaMono: CSSProperties = {
  color: 'var(--text-secondary)',
}

const badge: CSSProperties = {
  padding: '2px 7px',
  borderRadius: 4,
  border: '1px solid var(--border-soft)',
  color: 'var(--text-muted)',
}

const badgeWarn: CSSProperties = {
  padding: '2px 7px',
  borderRadius: 4,
  border: '1px solid color-mix(in srgb, var(--warning) 40%, transparent)',
  color: 'var(--warning)',
}

const filingLink: CSSProperties = {
  color: 'var(--secondary)',
  textDecoration: 'none',
}

const footNote: CSSProperties = {
  margin: '10px 0 0',
  fontSize: 11.5,
  color: 'var(--text-muted)',
}

const missingNote: CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11.5,
  color: 'var(--text-muted)',
  padding: '14px 18px',
  background: 'var(--bg-card-50)',
  border: '1px dashed var(--border-soft)',
  borderRadius: 'var(--radius-sm)',
}

const gapCallout: CSSProperties = {
  padding: '16px 18px',
  background: 'var(--bg-card-50)',
  border: '1px dashed var(--border-soft)',
  borderRadius: 'var(--radius-sm)',
}

const gapCalloutTitle: CSSProperties = {
  fontFamily: 'var(--font-display)',
  fontSize: 15,
  fontWeight: 600,
  color: 'var(--text-primary)',
  marginBottom: 6,
}

const gapCalloutBody: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'var(--text-muted)',
}

const gapCalloutCta: CSSProperties = {
  display: 'inline-block',
  marginTop: 10,
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  color: 'var(--secondary)',
  textDecoration: 'none',
}
