// The fund research report body — five chapters rendered from ONE `fund_research`
// artifact, in reading order: profile (what the vehicle is and what it costs) →
// cost (the fee in dollars, with its arithmetic) → holdings & allocation (what it
// owns) → risk & return (what it delivered) → narrative (the engine's own words).
//
// Why a body of its own rather than the equity ReportChapters: a fund files no
// income statement. Every equity chapter (thesis / DCF / valuation / filings /
// ownership) would render an empty shell for it, and the equity section manifest
// would offer a table of contents whose every entry scrolls to a gap note. The
// fund report carries its own chapter spine and its own manifest
// (reportSections.fundSectionEntries) instead.
//
// Shared by the in-app detail page (ArtifactDetailPage) and the standalone HTML
// export (export/ReportExportBody) so both render byte-identical content.
//
// `structured` is FLAT on a fund artifact (ticker / nav_per_share / returns / … at
// the top level), so this container narrows outputs.structured once and hands the
// same read model to every chapter — no chapter re-casts.

import type { ArtifactDetail } from '../../hooks/useV5Artifacts'
import {
  FundCostChapter,
  FundHoldingsChapter,
  FundNarrativeChapter,
  FundProfileChapter,
  FundRiskChapter,
} from './chapters'
import type { FundStructuredShape } from './chapters/types'

export function FundReportChapters({ artifact }: { artifact: ArtifactDetail }): React.ReactElement {
  const outputs = artifact.outputs ?? {}
  const structured = (outputs.structured ?? {}) as FundStructuredShape
  // The fund's dealing currency, when the run stamped one. USD is the contract's
  // default (NormalizedFundProfile.currency) — never guessed per field.
  const currency = typeof structured.currency === 'string' ? structured.currency : 'USD'
  const summary = typeof outputs.summary_text === 'string' ? outputs.summary_text : null

  return (
    <div style={{ minWidth: 0, padding: '12px 0 60px' }}>
      <FundProfileChapter fund={structured} currency={currency} />
      <FundCostChapter fund={structured} />
      <FundHoldingsChapter fund={structured} />
      <FundRiskChapter fund={structured} currency={currency} />
      <FundNarrativeChapter summary={summary} />
    </div>
  )
}
