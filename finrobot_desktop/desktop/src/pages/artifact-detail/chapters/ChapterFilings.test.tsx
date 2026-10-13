// Chapter 13 — Filings & XBRL. Locks the three things that made this chapter
// worth adding, and the one thing it must never do:
//   • the persisted SEC payload finally reaches the page (10-K metadata +
//     section availability, the 10-Q history, the 8-K index, the XBRL facts);
//   • each filing links out to sec.gov — the analyst can check the source;
//   • a run with NO filing layer says so instead of rendering an empty shell;
//   • it is an INDEX: the 10-K section TEXT (hundreds of KB, persisted for the
//     audit trail / RAG) must never be dumped into the reading surface.

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { ChapterFilings } from './ChapterFilings'
import type { SecFilingsShape, XbrlFactsSnapshotShape } from './types'

const LONG_SECTION_TEXT = 'Item 7 full corpus text that must never be rendered. '.repeat(40)

const FILINGS: SecFilingsShape = {
  '10k': {
    has_10k: true,
    form: '10-K',
    latest_10k_date: '2026-02-14',
    latest_10k_accession: '0000320193-26-000010',
    is_amended: false,
    sections_extraction_quality: 'fallback_to_full_text',
    source_url: 'https://www.sec.gov/Archives/edgar/data/320193/10k.htm',
    sections: [
      {
        canonical_id: 'item_1_business',
        title: 'Item 1 — Business',
        text: 'business text',
        char_count: 41230,
        extracted_via: 'edgartools_attribute',
      },
      {
        canonical_id: 'item_7_mdna',
        title: "Item 7 — Management's Discussion and Analysis",
        text: LONG_SECTION_TEXT,
        char_count: 1860,
        extracted_via: 'filing_text_fallback',
      },
    ],
  },
  '10q_history': [
    {
      form: '10-Q',
      filing_date: '2026-05-02',
      period_of_report: '2026-03-31',
      accession_no: '0000320193-26-000050',
      mdna_chars: 120,
      source_url: 'https://www.sec.gov/Archives/edgar/data/320193/10q.htm',
    },
  ],
  '8k_events': [
    {
      filing_date: '2026-04-30',
      period_of_report: '2026-04-30',
      accession_no: '0000320193-26-000040',
      items: ['2.02', '9.01'],
      text: 'earnings release text',
      source_url: 'https://www.sec.gov/Archives/edgar/data/320193/8k.htm',
    },
    {
      filing_date: '2026-03-01',
      accession_no: '0000320193-26-000020',
      items: ['1.01'],
      source_url: null,
    },
  ],
}

const XBRL: XbrlFactsSnapshotShape = {
  'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax': [
    {
      concept: 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
      value: 391035000000,
      period_end: '2025-12-31',
      units: 'USD',
    },
  ],
  'us-gaap:NetIncomeLoss:ttm': [
    { concept: 'us-gaap:NetIncomeLoss:ttm', value: 97900000000, units: 'USD' },
  ],
}

describe('XBRL fact warnings', () => {
  it('renders a stale fact warning instead of presenting the number as current', () => {
    // EHC stopped tagging OperatingIncomeLoss after FY2022, so the snapshot row
    // is a four-year-old figure; the backend flags it and the row must SAY so
    // (owner review 2026-10-13).
    renderChapter(null, {
      'us-gaap:OperatingIncomeLoss': [
        {
          concept: 'us-gaap:OperatingIncomeLoss',
          value: 539_500_000,
          period_end: '2022-12-31',
          units: 'USD',
          warning: 'stale: latest reported period is 2026-06-30, this fact is 2022-12-31',
        },
      ],
    })
    expect(
      screen.getByText('stale: latest reported period is 2026-06-30, this fact is 2022-12-31'),
    ).toBeInTheDocument()
  })

  it('renders no warning note for a current fact', () => {
    renderChapter(null, {
      'us-gaap:Assets': [
        { concept: 'us-gaap:Assets', value: 7_457_500_000, period_end: '2026-06-30', units: 'USD' },
      ],
    })
    expect(screen.queryByText(/stale:/)).toBeNull()
  })
})

function renderChapter(filings: SecFilingsShape | null, xbrl: XbrlFactsSnapshotShape | null) {
  return render(
    <MemoryRouter>
      <ChapterFilings filings={filings} xbrl={xbrl} />
    </MemoryRouter>,
  )
}

describe('ChapterFilings', () => {
  it('renders the 10-K metadata, extraction quality and section index', () => {
    renderChapter(FILINGS, XBRL)
    expect(screen.getByText('2026-02-14')).toBeTruthy()
    expect(screen.getByText('0000320193-26-000010')).toBeTruthy()
    expect(screen.getByText('Item 1 — Business')).toBeTruthy()
    expect(screen.getByText("Item 7 — Management's Discussion and Analysis")).toBeTruthy()
    // Section availability is readable as counts + extraction route, not raw text.
    expect(screen.getByText('41.2K')).toBeTruthy()
    expect(screen.getByText('Structured attribute')).toBeTruthy()
    // The full-text fallback must be visible as such — a degraded MD&A extraction
    // is exactly what an analyst needs to know.
    expect(screen.getByText('Fell back to full text')).toBeTruthy()
    expect(screen.getByText('Full-text fallback')).toBeTruthy()
  })

  it('never dumps the persisted section text into the page', () => {
    const { container } = renderChapter(FILINGS, XBRL)
    expect(container.textContent).not.toContain('Item 7 full corpus text')
    expect(container.textContent).not.toContain('earnings release text')
  })

  it('links every filing out to sec.gov', () => {
    renderChapter(FILINGS, XBRL)
    const tenK = screen.getByText(/View on sec.gov/)
    expect(tenK.getAttribute('href')).toBe('https://www.sec.gov/Archives/edgar/data/320193/10k.htm')
    expect(tenK.getAttribute('target')).toBe('_blank')
    expect(tenK.getAttribute('rel')).toBe('noreferrer noopener')
  })

  it('lists the 10-Q history newest-first with its period and accession', () => {
    renderChapter(FILINGS, XBRL)
    expect(screen.getByText('10-Q')).toBeTruthy()
    expect(screen.getByText('2026-03-31')).toBeTruthy()
    expect(screen.getByText('0000320193-26-000050')).toBeTruthy()
  })

  it('indexes the 8-K events by item code and points material items at the catalyst chapter', () => {
    renderChapter(FILINGS, XBRL)
    expect(screen.getByText('2.02, 9.01')).toBeTruthy()
    expect(screen.getByText('1.01')).toBeTruthy()
    expect(screen.getByText(/non-routine items are read semantically/i)).toBeTruthy()
    // A filing with no URL shows a dash, never a broken link.
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('renders the XBRL concept snapshot as a table', () => {
    renderChapter(FILINGS, XBRL)
    expect(screen.getByText('us-gaap:NetIncomeLoss:ttm')).toBeTruthy()
    expect(
      screen.getByText('us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'),
    ).toBeTruthy()
  })

  it('says so when the run has no filing layer at all', () => {
    renderChapter(null, null)
    expect(screen.getByText('No SEC filing layer in this run')).toBeTruthy()
    expect(screen.getByText('Configure SEC identity').getAttribute('href')).toBe('/settings')
  })

  it('keeps the chapter honest when only part of the filing layer landed', () => {
    // A partial SEC fetch: the 8-K cache answered while the 10-K / 10-Q / XBRL
    // calls timed out (or the issuer files no 10-K). The chapter shows what
    // arrived AND names each gap — never a silently short table.
    renderChapter(
      {
        '10k': { has_10k: false },
        '10q_history': [],
        '8k_events': [
          { filing_date: '2026-03-01', accession_no: 'acc-1', items: ['1.01'], source_url: null },
        ],
      },
      {},
    )
    expect(screen.getByText('No 10-K was retrieved for this run.')).toBeTruthy()
    expect(screen.getByText('No 10-Q was retrieved for this run.')).toBeTruthy()
    expect(screen.getByText(/No XBRL facts were retrieved/)).toBeTruthy()
    expect(screen.getByText('1.01')).toBeTruthy()
  })
})
