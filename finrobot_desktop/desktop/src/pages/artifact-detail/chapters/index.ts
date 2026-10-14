// Barrel export for the report's chapter components (and the content classifiers
// the section manifest shares with them).

export { ChapterCover } from './ChapterCover'
export { ChapterThesis } from './ChapterThesis'
export { ChapterCompanyOverview } from './ChapterCompanyOverview'
export { ChapterFinancialAnalysis } from './ChapterFinancialAnalysis'
export { ChapterValuation, ValuationBody } from './ChapterValuation'
export { ChapterNews } from './ChapterNews'
export { ChapterSensitivity, SensitivityBody } from './ChapterSensitivity'
export { ChapterCatalysts } from './ChapterCatalysts'
export { ChapterTechnical } from './ChapterTechnical'
export { ChapterCreditRisk } from './ChapterCreditRisk'
export { ChapterCompetitive, CompetitiveBody } from './ChapterCompetitive'
// Standalone tool-page bodies — reuse the report's chapter primitives without the
// numbered <Chapter> chrome (rendered by CompactArtifactViewer under its own header).
export { DcfForecastTable } from './DcfForecastTable'
export { DdmBody } from './DdmPanel'
export { LboBody } from './LboPanel'
// Fund research (fund_research) chapter spine — rendered by FundReportChapters in
// the fund report body's reading order.
export { FundProfileChapter } from './FundProfileChapter'
export { FundCostChapter } from './FundCostChapter'
export { FundHoldingsChapter } from './FundHoldingsChapter'
export { FundRiskChapter } from './FundRiskChapter'
export { FundNarrativeChapter } from './FundNarrativeChapter'
export { ChapterFinancialData } from './ChapterFinancialData'
export { ChapterOwnershipGovernance } from './ChapterOwnershipGovernance'
export { ChapterDisclaimer } from './ChapterDisclaimer'

export type {
  ArtifactStructured,
  ThesisShape,
  DcfShape,
  ValuationMethodShape,
  ValuationSynthesisShape,
  SOTPBreakdownShape,
  SegmentValuationShape,
  SegmentOverviewShape,
  SegmentShareShape,
  ForwardEstimatesShape,
  CreditRiskShape,
  PriceSessionShape,
  CatalystAnalysisShape,
  CatalystEventShape,
  PeerCompsShape,
  CompanyFinancialsShape,
  MonteCarloShape,
  SniperShape,
  HistoricalBandShape,
  TechnicalAnalysisShape,
  OwnershipGovernanceShape,
  InsiderTransactionShape,
  InstitutionalHoldingShape,
  ProxyCompensationShape,
  ScheduleThirteenAlertShape,
  FilingProvenanceShape,
  SecFilingsShape,
  SecTenKShape,
  SecTenQShape,
  SecEvent8KShape,
  SecFilingSectionShape,
  XbrlFactShape,
  XbrlFactsSnapshotShape,
  FundStructuredShape,
  FundNavPointShape,
  FundCostDragShape,
  FundReturnsShape,
  FundConcentrationShape,
  FundHoldingShape,
  NumericAuditShape,
  NumericAuditFinding,
  NumericAuditSeverity,
  NumericAuditStatus,
} from './types'

export { ChapterAuditBanner, auditBannerContent } from './ChapterAuditBanner'
export { AuditBadgeBlock } from './AuditBadgeBlock'
export type { AuditBannerContent } from './ChapterAuditBanner'
export { ChapterFilings } from './ChapterFilings'
export { ChapterAnalysisSummary } from './ChapterAnalysisSummary'
