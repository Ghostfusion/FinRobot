// Single source of truth for "is this artifact the 15-chapter research report?".
//
// Only equity_research renders as the 15-chapter long-scroll; every other type
// (dcf / ddm / lbo / comps / earnings / ic_memo / peer_research / ad_hoc) is a
// single deterministic computation rendered through the compact viewer. Shared
// by the in-app detail page (ArtifactDetailPage) AND the standalone HTML export
// (export/ReportExportBody) so both make the SAME branch — forcing a compact
// artifact through the 15-chapter shell renders empty chapters + an irrelevant
// TOC / Ownership rail (BUG-20260602-039). Keeping the predicate here stops the
// export path from silently drifting back to the report shell for every type.
export function isEquityResearch(type: string): boolean {
  return type === 'equity_research'
}

/** Types that render as a MULTI-CHAPTER long-scroll report (rail + numbered
 *  sections) instead of the compact single-computation viewer.
 *
 *  `fund_research` joins `equity_research` here: a fund (ETF / mutual fund /
 *  closed-end fund) files no income statement, so it renders its own five-chapter
 *  report — profile → cost → holdings & allocation → risk & return → narrative —
 *  rather than the equity spine (a fund has no thesis, DCF, valuation band or SEC
 *  filings, so the equity chapters would all be empty shells). Both report
 *  flavours share the page chrome; only the section manifest differs. */
export function isReportArtifact(type: string): boolean {
  return type === 'equity_research' || type === 'fund_research'
}
