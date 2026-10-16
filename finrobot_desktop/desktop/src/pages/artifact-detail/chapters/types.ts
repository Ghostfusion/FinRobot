// Lightweight typed views over artifact.outputs.structured.* dicts.
// The backend ships these as `dict[str, Any]` so the React side narrows
// per-section. Keeping these here (not in shared types/) so the report
// view owns its read model — other consumers should NOT couple to these.

// HistoricalMetrics is the ONE field here that IS a first-class shared type
// (the same model the live ['historical'] path returns) — now FROZEN into the
// artifact, so the read model references the canonical shape rather than
// re-declaring it.
import type { HistoricalMetrics } from '../../../types/finance'

export interface ThesisShape {
  recommendation?: string
  price_target?: number
  price_target_basis?: string
  catalysts?: string[]
  risks?: string[]
  narrative?: string
  tagline?: string | null
  key_takeaways?: string[] | null
  company_overview?: string | null
  valuation_overview?: string | null
  competitor_analysis?: string | null
  news_summary?: string | null
  /** LLM-authored only when the verdict strongly disagrees with the stock's own
   * trailing-1y price action (BACKLOG A2/P1-1) — what the market's recent move is
   * pricing in and why the call differs. null on an ordinary, non-divergent call. */
  momentum_divergence_note?: string | null
}

export interface DcfShape {
  wacc?: number
  cost_of_equity?: number | null
  projection_years?: number
  projected_revenue?: number[]
  projected_ebitda?: number[]
  projected_fcf?: number[]
  terminal_value?: number
  pv_terminal?: number
  /** Steady-state Gordon perpetuity BASE (capex→maintenance anchor, ΔNWC→
   * marginal ratio) — NOT projected_fcf[-1]; disclosed so the terminal value
   * is reconstructible from printed inputs. Absent on legacy artifacts. */
  terminal_fcf?: number | null
  /** Implied terminal-year EV/EBITDA (terminal value ÷ terminal EBITDA) — the
   *  exit multiple the perpetuity embeds, compared against today's multiple.
   *  Absent on legacy artifacts. */
  terminal_ev_ebitda?: number | null
  /** Terminal-year NOPAT re-investment rate (capex − D&A + ΔNWC) ÷ NOPAT — the
   *  growth-funding assumption behind the perpetuity. Absent on legacy. */
  terminal_reinvestment_rate?: number | null
  /** Terminal-year NOPAT (EBIT × (1 − tax)). Absent on legacy artifacts. */
  terminal_nopat?: number | null
  /** Equity bridge components (EV → net debt → equity, incl. NCI) persisted so
   *  the DCF result is reconstructible. Keyed dict, absent on legacy. */
  equity_bridge?: Record<string, number | null> | null
  /** Forecast-basis provenance: the explicit DCF window starts from a TTM base,
   *  so the first labelled projection year is NOT necessarily baseFY + 1. When
   *  present, `first_forecast_year` is the authority for the axis. Absent on
   *  legacy artifacts → the client falls back to baseFY + 1. */
  forecast_basis?: {
    /** 'ttm' when the model is anchored on a trailing-twelve-month figure. */
    base?: string | null
    /** ISO date of the TTM base window end, or null. */
    base_period_end?: string | null
    /** First labelled forecast year (e.g. 2027), or null. */
    first_forecast_year?: number | null
  } | null
  pv_fcf_total?: number
  enterprise_value?: number
  equity_value?: number
  implied_price?: number
  sensitivity_table?: Record<string, unknown> | null
  // ±2pp EBITDA-margin swing: [implied_price_at_-2pp, implied_price_at_+2pp],
  // low→high. Either end null when that shifted margin degrades (out of band /
  // Gordon guard); the whole field null when neither end is valid. Backend-
  // computed — never re-derived in the client. Absent on legacy artifacts.
  margin_swing?: [number | null, number | null] | null
  // Current-reality actuals for the four DCF drivers (keys revenue_growth /
  // ebitda_margin / capex_pct_revenue / nwc_pct_revenue) — the "Current" column of
  // the model-vs-current reconciliation. Calibers are MIXED (disclosed per cell):
  // ebitda_margin is always TTM; capex_pct_revenue is TTM when the canonical
  // snapshot resolved one (see assumption_current_actuals_capex_ttm — the only
  // driver whose caliber varies per ticker/run) and otherwise the latest fiscal
  // year; revenue_growth / nwc_pct_revenue are always the latest fiscal year (see
  // assumption_current_actuals_fy). Per-driver null when the source lacks a usable
  // point; whole field null on legacy artifacts. Deterministic (backend); the
  // client renders it verbatim, never re-computing a driver.
  assumption_current_actuals?: Record<string, number | null> | null
  // Fiscal year of the latest-FY current actuals (ΔNWC / growth, and capex on the
  // fallback path) — labels those cells "FY<year>" beside the TTM-labelled cells.
  // null on legacy.
  assumption_current_actuals_fy?: number | null
  // True when assumption_current_actuals.capex_pct_revenue is TTM-caliber; false
  // when it fell back to the latest fiscal year (the canonical snapshot's cash-
  // flow statement was thin/unavailable for this ticker); null/undefined on legacy
  // artifacts (predates this field) or when the actuals were never computed — the
  // reconciliation table then falls back to the FY label so it never claims a
  // caliber it can't back up (BUG-023 displayed==actual family).
  assumption_current_actuals_capex_ttm?: boolean | null
  // Reverse-DCF reality check: what growth/WACC the CURRENT market price implies.
  // growth_unreachable=true ⇒ no plausible growth reaches the price (option-value
  // stock); ceiling_price is the most the DCF can reach at growth_ceiling.
  market_implied?: {
    horizon_years: number
    implied_growth?: number | null
    implied_wacc?: number | null
    growth_unreachable: boolean
    growth_ceiling?: number | null
    ceiling_price?: number | null
    // DECLARED by the compute layer (`dcf._premium_driver`): which side of the
    // equation the premium over the model's value is a bet on. Absent on legacy
    // artifacts, where the premium sentence falls back to the local
    // `implied_growth < 0` test. A renderer must never infer this from the SIZE of
    // the premium — that is what printed "a bet on the implied growth" beside a
    // NEGATIVE implied growth.
    premium_driver?: 'growth' | 'discount_rate' | null
  } | null
  inputs?: {
    revenue_base?: number
    revenue_growth_rates?: number[]
    ebitda_margin?: number
    terminal_growth_rate?: number
    // Return on new invested capital the perpetuity assumes — the assumption the
    // terminal reinvestment rate (g ÷ ROIC) is built from. Absent on legacy.
    terminal_roic?: number
    tax_rate?: number
    beta?: number
    risk_free_rate?: number
    debt_ratio?: number
    // key → analyst-prose sourcing string ("35.0% (trailing 3yr median)"). The
    // "Model uses" column of the reconciliation — rendered VERBATIM, never
    // reformatted (the value already carries its own unit; BUG-030 / frontend
    // contract). Absent on legacy artifacts.
    assumption_provenance?: Record<string, string>
    // True when the explicit-window ΔNWC/revenue median was clamped into the
    // ±10% modelling band — drives the ⚠ on the ΔNWC reconciliation row. A
    // structured boolean so the ⚠ never parses the provenance prose.
    nwc_clamped?: boolean
  }
}

// ---------------------------------------------------------------------------
// Standalone DDM / LBO tool read models. Unlike DCF (financial_modeling) and
// comps (peer_analysis), these two have NO dedicated report chapter — they only
// appear as a football-field method row in the full report. The standalone DDM /
// LBO artifacts persist the raw DDMResult / LBOResult model_dump() at
// outputs.structured top level (builders.build_ddm_artifact / build_lbo_artifact),
// so the tool detail page renders them through DdmBody / LboBody (chapters/) using
// the SAME shared primitives (MetricModule / SubChapter / tableStyle) the report
// chapters use — one visual language, no raw K-V dump. Mirror
// finrobot.engine.models.financial.{DDMResult,DDMInputs,LBOResult,LBOYear,LBOInputs};
// keep in sync when those models change.
// ---------------------------------------------------------------------------

export interface DdmInputsShape {
  dividend_per_share?: number
  dividend_growth_rates?: number[]
  payout_ratio?: number
  risk_free_rate?: number
  beta?: number
  equity_risk_premium?: number
  terminal_growth_rate?: number
  terminal_payout_ratio?: number | null
  shares_outstanding?: number
  current_price?: number
  book_value_per_share?: number | null
  return_on_equity?: number | null
  net_interest_margin?: number | null
  // key (snake_case) → human-readable prose explanation of how each input was
  // derived (e.g. "34.4% (trailing 3yr EBITDA margin median)"). The VALUES are
  // already analyst prose; the tool page humanises the KEY and renders the value
  // verbatim (see CompactArtifactViewer ProvenanceList).
  assumption_provenance?: Record<string, string>
}

export interface DdmShape {
  cost_of_equity?: number
  projected_dividends?: number[]
  pv_dividends?: number[]
  pv_dividends_total?: number
  terminal_dividend?: number
  terminal_value?: number
  pv_terminal?: number
  equity_value_per_share?: number
  inputs?: DdmInputsShape
}

/** One year of the LBO debt schedule. All numbers deterministically computed. */
export interface LboYearShape {
  year: number
  revenue: number
  ebitda: number
  da: number
  ebit: number
  interest_expense: number
  ebt: number
  taxes: number
  net_income: number
  capex: number
  delta_nwc: number
  fcf: number
  mandatory_amort: number
  cash_sweep_amount: number
  total_debt_paydown: number
  revolver_draw: number
  ending_debt: number
}

export interface LboInputsShape {
  ticker?: string
  ltm_ebitda?: number
  entry_ebitda?: number | null
  entry_ev_ebitda?: number
  exit_ev_ebitda?: number
  holding_period_years?: number
  revenue_base?: number
  revenue_growth_rate?: number
  ebitda_margin?: number
  leverage_multiple?: number
  interest_rate?: number
  mandatory_amort_pct?: number
  tax_rate?: number
  assumption_provenance?: Record<string, string>
}

export interface LboSensitivityShape {
  entry_multiples?: number[]
  exit_multiples?: number[]
  irr_grid?: (number | null)[][]
  moic_grid?: (number | null)[][]
}

export interface LboShape {
  // Null throughout when the lbo_calculation step degraded (e.g. an impossible
  // capital structure) — the tool page degrades to the inputs + warnings rather
  // than crashing on a missing schedule (mirrors the MU peak-EBITDA case).
  entry_ev?: number | null
  entry_debt?: number | null
  entry_equity?: number | null
  schedule?: LboYearShape[]
  exit_ebitda?: number | null
  exit_ev?: number | null
  exit_equity?: number | null
  // MOIC/IRR contract (see lbo-recall): None = impossible capital structure
  // (negative entry equity); 0×/-1 = a genuine total loss (equity wiped).
  moic?: number | null
  irr?: number | null
  sensitivity?: LboSensitivityShape | null
  irr_formula_warning?: string | null
  capital_structure_warning?: string | null
}

export interface CatalystEventShape {
  category: string
  headline: string
  sentiment: 'positive' | 'negative' | 'neutral'
  impact_score: number
  // Internal net-sentiment weight (news 0.7 / 8-K 1.0), never rendered — the
  // Catalysts/News chapters dropped its column as fake precision. The backend now
  // excludes it from serialization (exclude=True), so it appears only on pre-fix
  // artifacts; optional and ignored everywhere.
  probability?: number
  reasoning?: string
  // Source provenance for the chronological news feed (ChapterNews). `published`
  // is an ISO date (null when the source didn't carry one → sorts last); `url`
  // is the source endpoint (finnhub.io = API endpoint, NOT an article page;
  // www.sec.gov = a real filing) — null when source-less. The Catalysts chapter
  // ignores both; the News feed renders an honest source chip from the domain.
  published?: string | null
  url?: string | null
}

export interface CatalystAnalysisShape {
  events?: CatalystEventShape[]
  overall_sentiment?: string
  key_catalysts?: string[]
  net_sentiment?: number
  category_breakdown?: Record<string, number>
  top_positive?: CatalystEventShape[]
  top_negative?: CatalystEventShape[]
}

export interface CompanyFinancialsShape {
  ticker: string
  name?: string | null
  revenue: number
  ebitda: number
  net_income: number
  market_cap: number
  gross_margin: number | null
  operating_margin: number | null
  pe_ratio?: number | null
  ev_ebitda?: number | null
  ev_revenue?: number | null
  // Price-to-book (market_cap / book equity). Banks' primary comps caliber — the
  // competitive table swaps its EV/EBITDA column to this for balance-sheet
  // financials (EV/EBITDA is a category error for deposit-takers).
  pb_ratio?: number | null
  // NOPAT core P/E (market_cap / NOPAT). Same caliber the trailing comps_pe
  // valuation target is computed on (peer_median_core_pe × core_eps), so the
  // table can reconcile with the football-field "Comps (core P/E)" row. Filled
  // by calculate_core_pe in the backend; None when operating income / tax was
  // unavailable.
  core_pe_ratio?: number | null
}

export interface PeerCompsShape {
  target?: CompanyFinancialsShape
  peers?: CompanyFinancialsShape[]
  median_ev_ebitda?: number | null
  median_pe?: number | null
  median_ev_revenue?: number | null
  // Peer median P/B — the bank-caliber comps multiple the competitive table leads
  // on for balance-sheet financials (in place of EV/EBITDA).
  median_pb?: number | null
  // Peer median of the NOPAT core P/E — the multiple the trailing comps target
  // uses. Distinct from median_pe (as-reported, the forward-EPS path multiple).
  median_core_pe?: number | null
  peer_justification?: string
  positioning_narrative?: string
}

/** Distribution parameters the Monte Carlo recorded. `centered_on` / `independent`
 *  let the chapter state — honestly — that the distribution is centred on the
 *  base-case DCF assumptions (an assumption-sensitivity band, NOT independent
 *  evidence). Both absent on artifacts written before the fields existed. */
export interface MonteCarloAssumptionsShape {
  /** What the simulated distribution is centred on, e.g. "base_case_dcf". */
  centered_on?: string | null
  /** False when the distribution is NOT independent evidence (the default read:
   *  it perturbs the base-case DCF it is compared against). */
  independent?: boolean | null
  [key: string]: unknown
}

export interface MonteCarloShape {
  implied_prices?: number[]
  percentiles?: Record<string, number>
  mean?: number
  std?: number
  current_price_percentile?: number
  histogram_bins?: number[]
  histogram_counts?: number[]
  assumptions_used?: MonteCarloAssumptionsShape | null
  n_valid?: number
}

export interface SniperShape {
  // Trade-level fields are null in NEUTRAL (levels-only) mode — see `direction`.
  ideal_buy?: number | null
  secondary_buy?: number | null
  stop_loss?: number | null
  take_profit?: number | null
  position_size_pct?: number | null
  safety_margin?: number | null
  support_level?: number
  resistance_level?: number
  risk_reward_ratio?: number | null
  // "LONG" | "SHORT" | "NEUTRAL" — drives entry/exit labels. SHORT (SELL-rated)
  // flips ideal_buy → short entry, take_profit → cover target (below entry),
  // stop_loss → above entry. NEUTRAL = valuation unreliable → no directional
  // trade, only support/resistance. Absent on legacy artifacts (treat as LONG).
  direction?: string
  sell_mode?: boolean
  // True when the margin-of-safety dial's entry level sat ABOVE the market, so
  // `ideal_buy` was clamped DOWN to the current price (the "buy now" is honest:
  // the required discount is already met). Absent on legacy artifacts → the
  // ideal-buy cell keeps its old sub-label.
  ideal_buy_at_market?: boolean | null
  // The discount the market already offers (1 - current/target). Rendered beside
  // `ideal_buy_at_market` so the clamped entry carries the achieved margin.
  safety_margin_achieved?: number | null
  invariant_warnings?: string[]
}

export interface HistoricalBandShape {
  metric?: 'ev_ebitda' | 'p_fcf' | string
  current?: number | null
  median?: number | null
  p25?: number | null
  p75?: number | null
  p90?: number | null
  timeline?: Array<[string, number]>
  sample_count?: number
  classification?: 'expensive' | 'fair' | 'cheap' | 'unknown'
  // Trailing window (years) the percentiles were computed over — the report's
  // unified band window, matching the valuation-method band. Lets the panel
  // label the band (e.g. "5y"). Absent on artifacts written before the field.
  window_years?: number | null
  warnings?: string[]
  // Structural-break disclosure (technical_payload): a YoY EBITDA step >= 3x inside
  // the band window makes the P25/P90 quantiles a pre-ramp artefact, so the
  // classification is directional only. `classification_caveat` is a short sentence
  // to render beside the CHEAP/FAIR/EXPENSIVE badge; null when no break. Absent on
  // artifacts written before the fields.
  classification_caveat?: string | null
  structural_break?: {
    from_fiscal_year?: string
    to_fiscal_year?: string
    from_ebitda?: number
    to_ebitda?: number
    step_multiple?: number
  } | null
}

export interface TechnicalAnalysisShape {
  monte_carlo?: MonteCarloShape | null
  sniper?: SniperShape | null
  historical_bands?: HistoricalBandShape | null
  warnings?: string[]
}

// ---------------------------------------------------------------------------
// SEC ownership & governance — Chapter 12 read model
// Mirrors finrobot.engine.models.sec.* with read-only field subsets. Keep in
// sync when models change. Provenance is required on every datum (matches
// CLAUDE.md "数字溯源" contract).
// ---------------------------------------------------------------------------

export interface FilingProvenanceShape {
  form: string // "10-K" / "10-Q" / "8-K" / "4" / "13F-HR" / "DEF 14A"
  filing_date: string // ISO date
  accession_no: string
  period_of_report?: string | null
  source_url?: string | null
}

/** Canonical insider transaction types (matches Form 4 transaction codes in
 * finrobot/engine/models/sec.py — keep these two in lockstep). Anything
 * outside this union signals a backend mapping miss and surfaces as the raw
 * value in the UI (the `transactionLabel` fallback). */
export type InsiderTransactionType =
  | 'sale'
  | 'purchase'
  | 'exercise'
  | 'other_disposition'
  | 'grant'
  | 'award'
  // SEC Form 4 §8 canonical codes — mirrors ownership._FORM4_CODE_TO_TYPE.
  | 'tax_withholding' // F — withhold shares for exercise price / tax
  | 'conversion' // C — conversion of derivative
  | 'exercise_otm' // O — exercise of out-of-money derivative
  | 'exercise_itm_atm' // X — exercise of in/at-money derivative
  | 'disposition_to_issuer' // D — disposition back to issuer
  | 'discretionary' // I — discretionary 16b-3(f) transaction
  | 'equity_swap' // K — equity swap or similar
  | 'tender' // U — tender in change-of-control
  | 'voluntary_report' // V — voluntary early report
  | 'estate' // W — acquisition/disposition by will/descent
  | 'voting_trust' // Z — deposit/withdrawal from voting trust
  | 'small_acquisition' // L — small acquisition under 16a-6
  | 'gift' // G — bona fide gift
  | 'expiration_short' // E — expiration of short derivative position
  | 'expiration_long' // H — expiration of long derivative position
  | 'other' // J — other (free-text described)

export interface InsiderTransactionShape {
  filing_date: string
  accession_no: string
  insider_name: string
  insider_position?: string | null
  transaction_type: InsiderTransactionType | string
  code: string
  shares: number
  value: number
  price_per_share?: number | null
  security_type?: string
  security_title?: string
  footnote_ids?: string
  footnotes_text?: string
  provenance: FilingProvenanceShape
}

export interface InstitutionalHoldingShape {
  holder_name: string
  holder_cik?: string | null
  cusip: string
  name_of_issuer: string
  title_of_class?: string
  shares: number
  value_usd: number
  period_end: string
  shares_change_pct?: number | null
  provenance: FilingProvenanceShape
}

export interface ProxyCompensationShape {
  filing_date: string
  accession_no: string
  ceo_name?: string | null
  // Where ceo_name came from. The comp figures always come from this DEF 14A,
  // but the NAME may be overridden by a fresher authority after a succession:
  // 'form4' = Form-4 officer title; 'sox302_cert' = the Ex-31.1 signer of the
  // latest 10-Q/10-K (the current principal executive officer by law).
  ceo_name_source?: 'def14a' | 'form4' | 'sox302_cert' | null
  // Filing the name was read from, when source !== 'def14a'.
  ceo_name_provenance?: FilingProvenanceShape | null
  ceo_total_compensation?: number | null
  ceo_yoy_change_pct?: number | null
  ceo_pay_ratio?: number | null
  provenance: FilingProvenanceShape
}

export interface ScheduleThirteenAlertShape {
  filer_name: string
  filer_cik?: string | null
  filing_date: string
  accession_no: string
  schedule_type: '13D' | '13G' | string
  /** AS-FILED count — never silently rewritten by the backend. */
  shares: number
  pct_of_class?: number | null
  transaction_summary?: string
  /** Which basis the as-filed count is on. `pre_split` means the filing predates
   *  an issuer stock split, so `shares` is not comparable to the current shares
   *  outstanding; `shares_adjusted` (shares × split_factor) then carries the
   *  split-adjusted count. `null` when no percentage was parsed (basis unknown).
   *  Absent on artifacts written before the field. */
  share_basis?: 'pre_split' | 'post_split' | null
  split_factor?: number | null
  shares_adjusted?: number | null
  /** Days between the filing date and the run's as-of; `stale` when > 400 (a 13G
   *  annual amendment has been missed). */
  filing_age_days?: number | null
  stale?: boolean
}

export type OwnershipDegradedReason =
  | 'identity_missing'
  | 'no_recent_filings'
  | 'fetch_error'
  | 'parse_failed'

export interface OwnershipGovernanceShape {
  insider_transactions?: InsiderTransactionShape[]
  institutional_holdings?: InstitutionalHoldingShape[]
  proxy_compensation?: ProxyCompensationShape | null
  schedule13_alerts?: ScheduleThirteenAlertShape[]
  generated_at?: string
  degraded_sections?: string[]
  // ^ e.g. ["institutional_holdings"] when sec_holdings_cache is empty.
  /** Fraction (0–1) of the issuer's institutionally-held shares the cached 13F
   *  holder list actually covers. < 1 ⇒ the list is a partial sample, so a
   *  client-side concentration must not be presented as the issuer's holder base.
   *  Absent on artifacts written before the field. */
  institutional_coverage_pct?: number | null
  /** Total shares held across the listed institutional holders — the denominator
   *  the concentration is measured against. Absent on legacy artifacts. */
  institutional_shares_listed?: number | null
  /** True when the cached 13F period the holders came from has no completion
   *  marker — a PARTIAL refresh, so the coverage % and any top-5 concentration
   *  are computed over a partial index and must be labelled as such. Absent on
   *  legacy artifacts (treated as complete/unknown). */
  institutional_index_partial?: boolean
  /** Non-fatal disclosure strings from the SEC ownership step (e.g. partial 13F
   *  coverage). Reader-facing; the chapter surfaces them under the institutions
   *  table. Absent on legacy artifacts. */
  warnings?: string[]
  degraded_reasons?: Partial<Record<string, OwnershipDegradedReason>>
  // ^ section key (matches degraded_sections entries) → reason code.
  // UI maps reason → i18n key for accurate messaging instead of one-size-fits-all.
}

// SEC filings + XBRL — the ChapterFilings appendix (the primary-source layer the
// numbers were read from). Shapes mirror the ACTUAL provider payloads in
// engine/data/providers/edgar_provider.py (_fetch_10k / _fetch_10q / _fetch_8k)
// and the persisted `structured.sec_filings` / `structured.xbrl_facts_snapshot`
// keys. The earlier draft of this block described a 10-K with `filing_date` /
// `accession_no` fields that the provider has never emitted (`latest_10k_date` /
// `latest_10k_accession`) — a type that lies is worse than none, so it is
// rewritten to the real keys.

export interface SecFilingSectionShape {
  /** Canonical Item id, e.g. "item_1a_risk_factors". */
  canonical_id: string
  /** Display title, e.g. "Item 1A — Risk Factors". */
  title: string
  /** Extracted section text (may be large — the chapter renders counts, not text). */
  text: string
  char_count: number
  /** 'edgartools_attribute' | 'filing_text_fallback' (BM25 full-text fallback). */
  extracted_via?: string
}

/** Latest 10-K payload (`_fetch_10k`). `has_10k: false` when the issuer files no
 *  10-K (non-US issuer / ETF) — the chapter then shows the gap honestly. */
export interface SecTenKShape {
  has_10k: boolean
  form?: string | null
  latest_10k_date?: string | null
  latest_10k_accession?: string | null
  is_amended?: boolean
  /** 'ok' | 'amended_redirected' | 'fallback_to_full_text'. */
  sections_extraction_quality?: string
  sections?: SecFilingSectionShape[]
  source_url?: string | null
  company_name?: string | null
  cik?: string | null
}

/** One 10-Q row (`_fetch_10q`). */
export interface SecTenQShape {
  form: string
  filing_date: string
  period_of_report?: string | null
  accession_no: string
  mdna_chars?: number
  source_url?: string | null
}

/** One 8-K event (`_fetch_8k`). `items` are raw Item codes ("1.01", "8.01"…);
 *  the CATALYST chapter renders the material ones with plain-language labels —
 *  this chapter is the filing index (dates, codes, links), never a second copy. */
export interface SecEvent8KShape {
  filing_date: string
  period_of_report?: string | null
  accession_no: string
  items?: string[]
  text?: string
  source_url?: string | null
}

export interface SecFilingsShape {
  '10k'?: SecTenKShape | null
  '10q_history'?: SecTenQShape[]
  '8k_events'?: SecEvent8KShape[]
}

/** One XBRL fact record (xbrl_concept_snapshot): the real matched us-gaap concept
 *  plus its value. `matched_concept` preserves the provider concept on the
 *  disambiguated NetIncomeLoss keys. */
export interface XbrlFactShape {
  concept: string
  value: number
  period_end?: string | null
  units?: string | null
  matched_concept?: string | null
  /** Set when the fact must not be read as current — e.g. the derived-Q4 caveat,
   * or staleness ("the newest reported period is X, this fact is Y"): EHC stopped
   * tagging OperatingIncomeLoss after FY2022, so the snapshot row would otherwise
   * present a four-year-old number as the operating income (owner review
   * 2026-10-13). */
  warning?: string | null
}

/** Sparse bag keyed by us-gaap concept (each key owns its fact list). */
export type XbrlFactsSnapshotShape = Record<string, XbrlFactShape[]>

// Two currency tags carried by the equity_research structured payload (BUG-030).
// quote_currency labels per-share & market-cap fields (price, 52w hi/lo, DCF
// implied price, sniper levels, price target, market_cap); reporting_currency
// labels income-statement / balance-sheet absolutes (revenue, EBITDA, EV, debt,
// cash, CEO comp). They DISAGREE for foreign-listed ADRs (TSM: USD / TWD).
// Absent on older artifacts → callers default to USD so US reports are unchanged.
export interface CurrencyTagsShape {
  quote_currency?: string
  reporting_currency?: string
}

// ---------------------------------------------------------------------------
// Numeric-audit gate (backend ArtifactAudit, finrobot/engine/models/numeric_claim.py).
// One Finding = one audit verdict on one number. The artifact builder runs the
// definitional verifiers over the finalized snapshot and ships the rollup here.
// `withhold_valuation` nulls the POINT price_target + sets valuation_withheld;
// the directional recommendation is PRESERVED (the REVIEW verdict is deleted),
// so the UI only RENDERS the data-health caveat, it never re-decides the call.
// ---------------------------------------------------------------------------

/** Per-finding severity. `review` is an advisory data-quality flag (the word is
 * the data-quality axis, NOT the deleted verdict); `blocked_field` withholds
 * that number (and any price target derived from it). `info` is advisory. */
export type NumericAuditSeverity = 'info' | 'review' | 'blocked_field'

/** Report-level rollup. `publishable` → render as-is (no banner). `caveated` →
 * ship with a muted data-quality caveat banner (the directional verdict still
 * stands; a point target may be withheld). `unpublishable` → core data
 * unresolvable (critical-failure path, red). Renamed from the old `review_only`
 * (commit ④) so the status reads as run-metadata, not a verdict. */
export type NumericAuditStatus = 'publishable' | 'caveated' | 'unpublishable'

export interface NumericAuditFinding {
  /** Which number, e.g. "ev_ebitda" / "pe_ratio" / "enterprise_value". */
  field_key: string
  /** Stable rule id, e.g. "financial_sector_ev_meaningless". */
  check: string
  severity: NumericAuditSeverity
  /** Human-readable reason carrying the actual numbers — drives the banner body. */
  evidence: string
}

export interface NumericAuditShape {
  findings?: NumericAuditFinding[]
  artifact_status?: NumericAuditStatus
  withhold_valuation?: boolean
}

// ---------------------------------------------------------------------------
// Frozen valuation synthesis — the football-field data, computed at generation
// against the SNAPSHOT price and persisted into the artifact (builders.py).
// Mirrors finrobot.engine.models.financial.ValuationSynthesis. The report MUST
// render the football field from THIS (not a live /api/valuation/aggregate
// refetch) so every price in the report is the one snapshot the narrative and
// the cover target were written against — reproducible + internally consistent.
// `current_price` is the generation-time quote; `methods[].name` is the method
// key (dcf / comps_pe / ev_ebitda / …) the FootballField maps to a label.
// ---------------------------------------------------------------------------

export interface ValuationMethodShape {
  name: string
  low: number
  mid: number
  high: number
  confidence: number
  source: string
  assumptions?: string | null
}

/** An INDEPENDENT cross-check on the valuation — e.g. the issuer's OWN EV/EBITDA
 *  history applied to TTM EBITDA → an implied price range. Rendered beside the
 *  blended methods but visually distinct: it is NOT part of the published target
 *  blend (it never votes on the headline). `basis`/`note` are analyst prose
 *  (verbatim) exposed as tooltips. */
export interface CrossCheckShape {
  name?: string | null
  label: string
  low: number
  mid: number
  high: number
  basis?: string | null
  note?: string | null
  // Structural-break disclosure for the cross-check's OWN band window ("cheap" is
  // computed over a window containing a >=3x EBITDA step, so the badge is
  // directional only). null when the window has no break. The same sentence is
  // appended to `basis` (dedupe when rendering). Absent on artifacts predating it.
  band_break_caveat?: string | null
  // Whether the DECISION had this row when it was written (design §5). False marks
  // the audit back-fill: the row is published AFTER the call was written, from the
  // technical chapter's frozen band, so the call never read it — display-only
  // evidence, which must not read as corroboration of the target beside it. Absent
  // on artifacts predating 2026-10-14 → read as consulted.
  consulted_by_verdict?: boolean | null
}

export interface ValuationSynthesisShape {
  methods: ValuationMethodShape[]
  /** Independent cross-checks on the valuation (e.g. the issuer's own EV/EBITDA
   *  history applied to TTM EBITDA). NOT part of the published target — the
   *  football field renders them as distinct reference rows. Absent on legacy
   *  artifacts. */
  cross_checks?: CrossCheckShape[] | null
  weighted_price?: number | null
  /** The quote the whole report is anchored to — frozen at data-fetch time. */
  current_price: number
  upside_downside?: number | null
  outlier_methods?: string[]
  warnings?: string[]
  /** Legacy binary gate — superseded by `confidence`. Kept for back-compat reads
   * of older artifacts; new surfaces read the tier, not this flag. */
  reliable?: boolean
  // ── Confidence dial (commit ③; ADR 估值优雅降级). The synthesis ALWAYS yields a
  // directional call; uncertainty is a tier + a widening band, never a withhold of
  // the call. Absent on legacy artifacts → callers default to 'low'.
  confidence?: 'high' | 'medium' | 'low' | 'very_low'
  /** Low/high ends of the headline target band (widen as confidence drops).
   * null when the point target is honestly withheld (valuation_withheld). */
  target_low?: number | null
  target_high?: number | null
  /** Method the headline point anchors on (dcf / comps_pe / …). The point sits
   * AT the anchor, never a blended midpoint of divergent methods. */
  anchor_method?: string | null
  /** True when the POINT target is honestly withheld — the directional verdict
   * still ships. Replaces the old recommendation==='REVIEW' sentinel. */
  valuation_withheld?: boolean
  /** Human-readable disclosure of what degraded + which proxy/anchor was used. */
  degradation_note?: string | null
  /** True when the issuer is mid-way through a post-acquisition transition — the
   *  reason the point target was withheld (NOT method divergence). Lets the NEUTRAL
   *  sniper note name the real cause instead of asserting "DCF vs comps diverge". */
  mna_transition?: boolean
  /** True for a balance-sheet financial (bank / insurer) whose cash-flow methods
   * (FCFF-DCF, EV/EBITDA, P/FCF) are category errors and suppressed at the source.
   * Lets the DCF / Monte-Carlo / EV-EBITDA-band / sensitivity chapters frame the
   * absent panels as 'not applicable to a balance-sheet financial' rather than
   * 'missing — re-run', WITHOUT re-deriving the classification in the client. */
  financial_sector?: boolean
}

// Scenario SOTP (Batch 3B v1): the reverse-SOTP market-implied decomposition for
// an option-value name (TSLA-class). An INDEPENDENT channel — NOT a method in the
// football field's point synthesis (kept out so it never trips the reliability
// gate). The valuation chapter renders it as a floor / implied-option-premium
// panel. All numbers are COMPUTED (deterministic) and 100% sourceable; price_floor
// is a FLOOR, not a target.
export interface SegmentValuationShape {
  name: string
  metric_label: string
  metric_value: number
  multiple: number
  multiple_source: string
  implied_ev: number
}

// Forward STREET-anchored scenario band (Batch 3B v2): the three legs are the
// 12-month analyst price-target DISTRIBUTION (street low/consensus/high). range_position
// is street positioning within that range — NEVER a robotaxi-success probability, and
// the legs are 12-month FORWARD values (the reverse-SOTP floor above is a present value).
export interface SOTPScenarioBandShape {
  // C (4-point merge): the reverse-SOTP cash-flow floor rides as an INDEPENDENT
  // present-value anchor beside the 12-month street cluster (bear/base/bull, forward).
  // floor_coverage = cash_flow_floor / current_price is the ONLY floor-vs-price
  // relation (same present-value caliber); a floor→street ratio is forbidden
  // (cross-caliber) and never appears — do NOT place the price marker on a
  // [floor, bull] axis.
  cash_flow_floor?: number | null
  floor_coverage?: number | null
  bear: number
  base: number
  bull: number
  median?: number | null
  current_price: number
  range_position: number
  analyst_count?: number | null
  confidence: string
  source: string
  as_of: string
  warnings?: string[]
}

// Lightweight, display-only reportable-segment revenue mix (BACKLOG A4,
// 2026-07-09) — the Company Overview chapter's non-SOTP sibling. Populated for
// tickers the SOTP option-value gate did NOT fire for (see SOTPBreakdownShape
// below for that heavier reverse-decomposition channel). SEC XBRL ASC-280
// reportable segments ONLY (an FMP product-mix fallback was tried and removed
// the same day — different, unaudited caliber + demonstrably unreliable, KO
// live). An issuer with no cleanly-anchorable XBRL segment breakdown ships NO
// SegmentOverview (honest "not available"), never a substitute.
export interface SegmentShareShape {
  name: string
  revenue?: number | null
  // Share of the SUM of segments in THIS breakdown — NOT a share of the
  // company's consolidated total revenue (see SegmentOverviewShape.warnings
  // for the corporate/eliminations reconciliation caveat).
  revenue_share?: number | null
  operating_income?: number | null
  gross_profit?: number | null
}

export interface SegmentOverviewShape {
  ticker: string
  as_of: string
  source: 'sec_xbrl_business_segment'
  period_label: string
  segments: SegmentShareShape[]
  warnings?: string[]
}

export interface SOTPBreakdownShape {
  ticker: string
  as_of: string
  modelable_segments: SegmentValuationShape[]
  ev_floor: number
  net_debt: number
  equity_floor: number
  price_floor: number
  shares_outstanding: number
  current_price: number
  market_equity: number
  implied_option_ev: number
  implied_option_pct: number
  option_ev_if_success?: number | null
  option_anchor_source?: string | null
  implied_success_probability?: number | null
  floor_exceeds_market?: boolean
  market_exceeds_success_ceiling?: boolean
  scenario_band?: SOTPScenarioBandShape | null
  warnings?: string[]
}

// Frozen forward-estimate provenance (builders.py persists this slim block at
// generation). The forward NUMBERS live in valuation_synthesis.methods; this is
// only what the football field / footnote need to label the forward comps row
// ("FY2026E") and cite its source WITHOUT a live aggregate refetch.
export interface ForwardEstimatesShape {
  /** Forecast fiscal-year-end the forward EPS/EBITDA/FCF belong to (e.g. "2026-09-30"). */
  fiscal_period?: string | null
  source?: string | null
  confidence?: string | null
}

// Frozen structural (Merton/KMV) credit risk. The pipeline solves the equity-as-
// a-call-on-assets identity for the latent asset value + asset volatility, then
// reports distance to default and the model-implied default probability. `state`
// is the load-bearing field: it says which of four readings this issuer got, and
// every numeric field is optional so an uncomputed state is EMPTY — never a zero
// that would read as "no default risk".
export interface CreditRiskShape {
  state?: 'computed' | 'no_debt' | 'not_applicable' | 'not_computable'
  method?: string
  horizon_years?: number | null
  equity_value?: number | null
  debt_barrier?: number | null
  /** 'total_debt' today — the provider reports no short/long split. */
  barrier_basis?: string | null
  asset_value?: number | null
  asset_volatility?: number | null
  equity_volatility?: number | null
  volatility_bars?: number | null
  risk_free_rate?: number | null
  distance_to_default?: number | null
  default_probability?: number | null
  debt_to_value?: number | null
  /** The model's own risky-debt yield minus the risk-free rate, annualized. */
  implied_credit_spread?: number | null
  iterations?: number | null
  converged?: boolean | null
  warnings?: string[]
}

// Frozen prior-close → last-close price delta, in the QUOTE currency (frozen by
// builders.py from the same PRICE canonical the data step narrated). Absent when
// the run had fewer than 2 price bars — there is no session to diff, which is a
// different thing from a 0.00 move.
export interface PriceSessionShape {
  latest_session_change?: number | null
  latest_session_change_pct?: number | null
}

export interface ArtifactStructured {
  thesis?: ThesisShape
  currency?: CurrencyTagsShape
  financial_modeling?: DcfShape
  peer_analysis?: PeerCompsShape
  valuation_synthesis?: ValuationSynthesisShape
  forward_estimates?: ForwardEstimatesShape
  catalyst_analysis?: CatalystAnalysisShape
  technical_analysis?: TechnicalAnalysisShape
  ownership_governance?: OwnershipGovernanceShape
  sec_filings?: SecFilingsShape
  xbrl_facts_snapshot?: XbrlFactsSnapshotShape
  numeric_audit?: NumericAuditShape
  sotp_breakdown?: SOTPBreakdownShape
  // BACKLOG A4 (2026-07-09): display-only sibling for tickers the SOTP gate
  // above did NOT fire for — see SegmentOverviewShape.
  segment_overview?: SegmentOverviewShape
  // Multi-year trend series, frozen at generation (builders.py persists the
  // pipeline's HistoricalMetrics) so ChapterFinancialAnalysis reads the charts
  // from the snapshot instead of a live ['historical'] refetch.
  historical_metrics?: HistoricalMetrics
  // Structural (Merton/KMV) credit risk — its own key, never merged into the
  // valuation: it prices the DEBT leg of the capital structure off the equity
  // view. Absent on artifacts written before the step existed.
  credit_risk?: CreditRiskShape
  // The prior-close → last-close delta the data step computed and builders.py
  // froze. Persisted since the price-session freeze landed and rendered nowhere
  // until the rail's spot caption read it.
  price_session?: PriceSessionShape
}

// ── Fund research (fund_research) ─────────────────────────────────────────────
//
// `outputs.structured` for a fund artifact is FLAT: the fund pipeline writes these
// keys at the top level (there is no `fund_profile` sub-object to nest under, and
// none of the equity section keys exist). Every ratio / return / yield / weight
// below is a FRACTION — 0.0015 = 15 bp of expense, 0.0687 = a 6.87% position.

/** One dated point of a fund's trailing NAV / traded-close series (oldest →
 *  newest). For a NAV-priced mutual fund the close IS the fund's NAV. */
export interface FundNavPointShape {
  date: string
  close: number
}

/** The fee's arithmetic cost over a holding horizon, as disclosed by the run. */
export interface FundCostDragShape {
  /** Fee paid per $10,000 invested over `horizon_years`. */
  expense_drag_usd_per_10k?: number | null
  /** Fee as a fraction of the GROSS return the portfolio earned. */
  fee_share_of_gross_return?: number | null
  horizon_years?: number | null
}

/** Trailing returns, all fractions. `cagr_3y` / `cagr_5y` are annualised. */
export interface FundReturnsShape {
  cagr_1y?: number | null
  cagr_3y?: number | null
  cagr_5y?: number | null
  ytd?: number | null
  return_3m?: number | null
}

/** Portfolio concentration. `hhi` is the Herfindahl index (0–1); `effective_n` is
 *  its reciprocal — the number of equal-sized positions the mix behaves like. */
export interface FundConcentrationShape {
  top10_weight?: number | null
  hhi?: number | null
  effective_n?: number | null
}

export interface FundHoldingShape {
  symbol?: string | null
  name?: string | null
  /** FRACTION of the portfolio (0.068748 = 6.87%). */
  weight?: number | null
}

export interface FundStructuredShape {
  ticker?: string | null
  /** Display name of the fund (e.g. "iShares 3-7 Year Treasury Bond ETF"). */
  name?: string | null
  /** `"fund"` — the classifier's instrument tag (the object itself only exists
   *  for a fund, so this is a provenance echo, never the discriminator). */
  instrument?: string | null
  category?: string | null
  fund_family?: string | null
  legal_type?: string | null
  inception_date?: string | null
  /** Fund currency (ISO code), when the run stamped one. Defaults to USD. */
  currency?: string | null
  total_net_assets?: number | null
  nav_per_share?: number | null
  /** null for a NAV-priced-only fund → no premium/discount can exist. */
  market_price?: number | null
  /** Market price vs NAV. Sign convention: positive = trades ABOVE NAV (a
   *  premium), negative = below (a discount). */
  premium_discount?: number | null
  net_expense_ratio?: number | null
  gross_expense_ratio?: number | null
  category_avg_expense_ratio?: number | null
  /** Annual holdings turnover, fraction. */
  turnover?: number | null
  cost_drag?: FundCostDragShape | null
  distribution_yield?: number | null
  returns?: FundReturnsShape | null
  volatility?: number | null
  max_drawdown?: number | null
  sharpe?: number | null
  /** label → fraction of the portfolio. */
  asset_classes?: Record<string, number> | null
  sector_weights?: Record<string, number> | null
  region_weights?: Record<string, number> | null
  bond_ratings?: Record<string, number> | null
  /** Years. null/absent for an equity fund (no bonds → no duration). */
  bond_duration?: number | null
  bond_maturity?: number | null
  equity_pe?: number | null
  top_holdings?: FundHoldingShape[] | null
  concentration?: FundConcentrationShape | null
  /** The fund's own SEC N-PORT portfolio — the FULL reported book, not the
   *  vendor's top-N excerpt. Weights are FRACTIONS like every other fund weight.
   *  Absent/empty whenever SEC could not serve the filing, in which case
   *  `top_holdings` is all that exists. */
  portfolio_holdings?: FundHoldingShape[] | null
  /** `sec_nport` when the portfolio (and the concentration panel above) came from
   *  the fund's filing, else the vendor id behind `top_holdings`. */
  portfolio_source?: string | null
  /** N-PORT report period end — the panel's as-of date. A filing is quarterly,
   *  so a reader must see this rather than assume the weights are live. */
  portfolio_as_of?: string | null
  /** Positions in the filing; the rendered list is capped well below it. */
  portfolio_holding_count?: number | null
  /** Trailing NAV / traded-close series. Key omitted when the fund has no bars. */
  nav_series?: FundNavPointShape[] | null
  warnings?: string[]
}
