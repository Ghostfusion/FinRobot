// The exported HTML's body. Mirrors ArtifactDetailPage's in-app type branch so a
// standalone export shows the SAME thing the page does: a multi-chapter report for
// equity_research (15 chapters) and fund_research (its own fund spine), and the
// compact single-computation viewer for every other type (dcf / ddm / lbo / comps /
// earnings / ic_memo / …).
//
// Before this branch existed, the export rendered <ReportChapters> for EVERY
// type, so exporting a dcf / ddm / lbo / comps artifact produced an empty
// 15-chapter equity shell (null thesis / valuation / ownership) — the very
// BUG-20260602-039 shell the in-app viewer already avoids via CompactArtifactViewer.
//
// `isReportArtifact` (not `isEquityResearch`) is the predicate because the
// decision here is "is this a long-scroll report?", and a fund is one too —
// routing it to the compact viewer would flatten its five chapters into an
// unstructured key/value dump.

import type { ArtifactDetail } from '../hooks/useV5Artifacts'
import type { ArtifactSummaryV5 } from '../types/v5'
import { isReportArtifact } from '../lib/artifactKind'
import { ReportChapters } from '../pages/artifact-detail/ReportChapters'
import { CompactArtifactViewer } from '../pages/artifact-detail/CompactArtifactViewer'

export function ReportExportBody({
  artifact,
  timeline,
}: {
  artifact: ArtifactDetail
  timeline: ArtifactSummaryV5[]
}): React.ReactElement {
  return isReportArtifact(artifact.type) ? (
    <ReportChapters artifact={artifact} timeline={timeline} />
  ) : (
    <CompactArtifactViewer artifact={artifact} />
  )
}
