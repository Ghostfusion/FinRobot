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
