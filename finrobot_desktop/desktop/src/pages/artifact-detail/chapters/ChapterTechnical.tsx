// Chapter 10 — Technical Analysis. Snapshot price chip plus three
// quant overlays baked into the equity_research artifact:
//   - Monte Carlo distribution (inline SVG histogram + percentile markers)
//   - Sniper levels (KvGrid of buy/stop/target + R/R)
//   - Historical EV/EBITDA bands (inline SVG timeline + P25/median/P75/P90)
//
// Price / 52w / beta are the FROZEN data-fetch snapshot (the same snapshot the
// valuation used), NOT a live refetch — a research report is a point-in-time
// artifact, so its "current price" is the one the analysis was written against.
// Live market data lives in the workspace dashboard, not the report.

import { Chapter, SubChapter } from './ChapterBase'
import { MetricModule, type MetricCell } from './MetricModule'
import { useI18n } from '../../../i18n'
import { TermTip } from '../../../components/TermTip'
import { formatCurrency } from '../../../utils/format'
import type {
  HistoricalBandShape,
  MonteCarloShape,
  SniperShape,
  TechnicalAnalysisShape,
} from './types'

interface ChapterTechnicalProps {
  technical: TechnicalAnalysisShape | null
  // True for a balance-sheet financial (bank / insurer): the quant overlays are all
  // DCF / enterprise-value derived (Monte Carlo IS a DCF distribution, the EV/EBITDA
  // band IS an enterprise-value multiple), so they are withheld at the source as
  // category errors — frame the empty state as "not applicable", not "re-run".
  financialSector: boolean
  // Every amount in this chapter is a per-share price (current/52w/MC/sniper)
  // → quote currency (BUG-030).
  quoteCurrency: string
  // Frozen data-fetch snapshot — the report's anchor price, raw 5Y beta, and 52w
  // range. `snapshotBeta` is the raw provider regression beta; the Valuation
  // chapter's β is this same beta Blume-adjusted toward 1.0 for WACC (so the two
  // legitimately differ — see the β glossary).
  snapshotPrice: number | null
  snapshotBeta: number | null
  snapshot52wHigh: number | null
  snapshot52wLow: number | null
  // The published verdict (`thesis.recommendation`, e.g. "HOLD"). The tactical box
  // publishes mechanical LONG/SHORT reference levels derived from the DCF fair value
  // even when the verdict is HOLD, so the two must be reconciled in the reader's view
  // (owner review: HOLD beside an "Ideal Buy 246.88 above the 228.52 market, R/R 0.94").
  recommendation?: string | null
  // Cause inputs for the NEUTRAL sniper note. The backend keys NEUTRAL purely on
  // `has_anchor_target = not valuation_withheld`, NOT on whether the methods actually
  // diverge — so a lone method (THC: one DCF, no comps) was narrated as "DCF vs comps
  // diverge" (external audit). We pick the wording that matches the REAL cause.
  /** valuation_synthesis.mna_transition — the target was withheld because the issuer
   *  is mid-way through a post-acquisition transition, not because methods diverged. */
  mnaTransition?: boolean
  /** valuation_synthesis.methods.length — 1 means no second method existed to
   *  corroborate the sole method's output (a derivation, not a divergence). */
  methodCount?: number
}

export function ChapterTechnical({
  technical,
  financialSector,
  quoteCurrency,
  snapshotPrice,
  snapshotBeta,
  snapshot52wHigh,
  snapshot52wLow,
  recommendation = null,
  mnaTransition = false,
  methodCount = 0,
}: ChapterTechnicalProps): React.ReactElement {
  const { t, locale } = useI18n()
  const fmtPx = (v: number): string => formatCurrency(v, quoteCurrency, locale, 2)
  const current = snapshotPrice
  const high52 = snapshot52wHigh
  const low52 = snapshot52wLow
  const beta = snapshotBeta
  const range52Position =
    current !== null && high52 !== null && low52 !== null && high52 > low52
      ? ((current - low52) / (high52 - low52)) * 100
      : null

  const rawCells: Array<MetricCell | false> = [
    current !== null && {
      // Frozen snapshot price — no intraday change% (that's a live-quote field);
      // the report's "as of" stamp lives in the toolbar.
      label: t('chapter.technical.kv.currentPrice'),
      value: fmtPx(current),
    },
    low52 !== null && { label: t('chapter.technical.kv.low52w'), value: fmtPx(low52) },
    high52 !== null && { label: t('chapter.technical.kv.high52w'), value: fmtPx(high52) },
    range52Position !== null && {
      label: t('chapter.technical.kv.position52w'),
      value: `${range52Position.toFixed(0)}%`,
      // Natural micro-encoding: where the price sits in its own 52-week band.
      ratio: range52Position / 100,
      // Four tiers, not three: with a single 20–80 "mid-range" bucket a 22%
      // print carried a mid-range caption — technically inside the bucket,
      // but a reader sees "bottom quarter" (external audit 2026-07-07).
      sub:
        range52Position >= 80
          ? t('chapter.technical.position.nearHigh')
          : range52Position >= 50
            ? t('chapter.technical.position.upperRange')
            : range52Position > 20
              ? t('chapter.technical.position.lowerRange')
              : t('chapter.technical.position.nearLow'),
    },
    beta !== null && {
      // Reconciled against the DCF/WACC β in the Valuation chapter via the
      // shared "β" glossary term (TermTip): this is the raw provider 5Y
      // regression beta; the valuation chapter's β is this same figure after
      // an asymmetric Blume adjustment (see the glossary hover), so the two
      // can legitimately differ without one being wrong.
      label: <TermTip term="β">{t('chapter.technical.kv.beta5y')}</TermTip>,
      value: beta.toFixed(2),
      sub: t('chapter.technical.kv.vsSpx'),
    },
  ]
  const cells: MetricCell[] = rawCells.filter((c): c is MetricCell => c !== false)

  const mc = technical?.monte_carlo ?? null
  const sniper = technical?.sniper ?? null
  const bands = technical?.historical_bands ?? null
  const anyOverlay = mc !== null || sniper !== null || bands !== null

  // Tactical-vs-verdict reconciliation: a full directional LONG reference box beside
  // a HOLD verdict is contradictory unless the box is labelled for what it is. The
  // numbers stay published (they ARE the mechanical reference levels); the HOLD
  // verdict adds the note that reconciles them. (Chose the reconcile-note route over
  // gating the cells: the levels remain analytically useful to monitor, and hiding
  // them would drop published numbers.)
  const holdReconciliation =
    (recommendation ?? '').toUpperCase() === 'HOLD'
      ? locale === 'zh'
        ? 'HOLD——下列为机械参考位,不是交易信号:方向性价位由 DCF 公允价值机械推导,在 HOLD 评级下仅作监控参考,并非建仓指示。'
        : 'HOLD — mechanical reference levels, not a trade signal. The directional levels below are derived mechanically from the DCF fair value; with the published verdict on HOLD they are levels to monitor, not an entry instruction.'
      : null

  // NEUTRAL sniper note, worded to the ACTUAL cause of the withheld target (the
  // backend sets NEUTRAL whenever the point target is withheld, regardless of WHY).
  // mna_transition ⇒ post-acquisition transition; a lone method ⇒ nothing to
  // corroborate it; otherwise ⇒ genuine cross-method divergence. Pre-resolved here so
  // the panel stays free of cause logic (mirrors holdNote).
  const neutralNote = t(
    mnaTransition
      ? 'chapter.technical.sniper.withheldMnaTransition'
      : methodCount === 1
        ? 'chapter.technical.sniper.withheldSingleMethod'
        : 'chapter.technical.sniper.withheldUnreliable',
  )

  return (
    <Chapter id="technical">
      {cells.length > 0 ? (
        <MetricModule
          title={locale === 'en' ? 'Price & Range Snapshot' : '价格与区间快照'}
          accent="cyan"
          cells={cells}
          columns={2}
        />
      ) : (
        <p style={mutedNote}>{t('chapter.technical.empty.price')}</p>
      )}

      {!anyOverlay && (
        <p style={mutedNote} data-testid="technical-cold-state">
          {financialSector
            ? t('chapter.cashflowMethods.notApplicableForFinancials')
            : t('chapter.technical.empty.overlay')}
        </p>
      )}

      {mc !== null && (
        <SubChapter heading={t('chapter.technical.subheading.monteCarlo')}>
          <MonteCarloPanel mc={mc} current={current} t={t} fmtPx={fmtPx} />
        </SubChapter>
      )}

      {sniper !== null && (
        <SniperPanel
          sniper={sniper}
          t={t}
          fmtPx={fmtPx}
          current={current}
          holdNote={holdReconciliation}
          neutralNote={neutralNote}
        />
      )}

      {bands !== null && (
        <SubChapter heading={t('chapter.technical.subheading.historicalBands')}>
          <HistoricalBandPanel band={bands} t={t} />
        </SubChapter>
      )}
    </Chapter>
  )
}

// ---------------------------------------------------------------------------
// Monte Carlo: histogram + percentile markers + current-price reference line
// ---------------------------------------------------------------------------

function MonteCarloPanel({
  mc,
  current,
  t,
  fmtPx,
}: {
  mc: MonteCarloShape
  current: number | null
  t: (key: string, params?: Record<string, string | number>) => string
  fmtPx: (v: number) => string
}): React.ReactElement {
  const bins = mc.histogram_bins ?? []
  const counts = mc.histogram_counts ?? []
  const percentiles = mc.percentiles ?? {}
  const mean = mc.mean
  const std = mc.std
  const pctCurrent = mc.current_price_percentile
  const n = mc.n_valid

  const minPrice = bins.length > 0 ? bins[0] : 0
  const maxPrice = bins.length > 0 ? bins[bins.length - 1] : 0
  const maxCount = counts.length > 0 ? Math.max(...counts) : 1
  const width = 720
  const height = 220
  const padX = 36
  // 30 (not 24) leaves headroom above the histogram for a staggered second
  // label row (layoutMarkerRows) without clipping against the SVG viewBox
  // when two percentile markers land close together.
  const padY = 30
  const innerW = width - padX * 2
  const innerH = height - padY * 2

  const xScale = (p: number): number =>
    maxPrice > minPrice ? padX + ((p - minPrice) / (maxPrice - minPrice)) * innerW : padX

  // Percentile markers cluster whenever the current price sits near a
  // percentile (P95 and "Current" land on top of each other for a name
  // trading near its distribution's tail) — every marker shares the same
  // label y, so overlapping labels rendered as illegible stacked text.
  // Assign each marker a row (0 = default, above the axis; 1+ = staggered
  // further up) so labels within MARKER_LABEL_MIN_GAP px of an
  // already-placed label on a row bump to the next row instead of
  // overlapping it.
  const markerSpecs = [
    percentiles['5'] !== undefined && {
      key: 'p5',
      x: xScale(percentiles['5']),
      label: 'P5',
      color: 'var(--warning)',
    },
    percentiles['50'] !== undefined && {
      key: 'p50',
      x: xScale(percentiles['50']),
      label: 'P50',
      color: 'var(--accent-cyan)',
    },
    percentiles['95'] !== undefined && {
      key: 'p95',
      x: xScale(percentiles['95']),
      label: 'P95',
      color: 'var(--warning)',
    },
    current !== null &&
      current >= minPrice &&
      current <= maxPrice && {
        key: 'current',
        x: xScale(current),
        label: 'Current',
        color: 'var(--success)',
      },
  ].filter((m): m is { key: string; x: number; label: string; color: string } => m !== false)
  const markerRows = layoutMarkerRows(markerSpecs)

  return (
    <div>
      <div style={statRow}>
        <Stat
          label={t('chapter.technical.mc.mean')}
          value={mean !== undefined ? fmtPx(mean) : '—'}
        />
        <Stat label={t('chapter.technical.mc.std')} value={std !== undefined ? fmtPx(std) : '—'} />
        <Stat label="P5" value={percentiles['5'] !== undefined ? fmtPx(percentiles['5']) : '—'} />
        <Stat
          label="P50"
          value={percentiles['50'] !== undefined ? fmtPx(percentiles['50']) : '—'}
        />
        <Stat
          label="P95"
          value={percentiles['95'] !== undefined ? fmtPx(percentiles['95']) : '—'}
        />
        <Stat
          label={t('chapter.technical.mc.currentPct')}
          value={pctCurrent !== undefined ? `${pctCurrent.toFixed(0)}th` : '—'}
        />
        <Stat
          label={t('chapter.technical.mc.sims')}
          value={n !== undefined ? n.toLocaleString() : '—'}
        />
      </div>

      {/* Assumption-sensitivity disclosure (under the Current Pct figure): the
          distribution is centred on the base-case DCF assumptions, so its P50
          merely restates the DCF and its "current percentile" is NOT independent
          evidence. Rendered unless the backend explicitly marks it independent
          (never the case today) — legacy artifacts (field absent) still show it,
          because the disclosure is true of the method itself. */}
      {mc.assumptions_used?.independent !== true && (
        <p data-testid="mc-assumptions-note" style={mutedNote}>
          {t('chapter.technical.mc.assumptionsNote')}
        </p>
      )}

      {bins.length > 1 && counts.length > 0 && (
        <svg
          role="img"
          aria-label="Monte Carlo implied price distribution"
          data-testid="mc-histogram"
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', display: 'block', marginTop: 12 }}
        >
          {counts.map((c, i) => {
            const x0 = xScale(bins[i])
            const x1 = xScale(bins[i + 1])
            const h = (c / maxCount) * innerH
            return (
              <rect
                key={i}
                x={x0}
                y={padY + innerH - h}
                width={Math.max(1, x1 - x0 - 1)}
                height={h}
                fill="var(--secondary)"
                opacity={0.55}
              />
            )
          })}
          {markerSpecs.map((m) => (
            <Marker
              key={m.key}
              x={m.x}
              label={m.label}
              color={m.color}
              height={innerH}
              padY={padY}
              row={markerRows.get(m.key) ?? 0}
            />
          ))}
        </svg>
      )}
    </div>
  )
}

function Marker({
  x,
  label,
  color,
  height,
  padY,
  row = 0,
}: {
  x: number
  label: string
  color: string
  height: number
  padY: number
  /** Stagger row from layoutMarkerRows — 0 sits directly above the axis line
   * (the original position); each row above that lifts the label further up
   * so labels whose lines land close together don't overlap. The dashed
   * marker line itself never moves — only the text. */
  row?: number
}): React.ReactElement {
  return (
    <g>
      <line
        x1={x}
        x2={x}
        y1={padY}
        y2={padY + height}
        stroke={color}
        strokeWidth={1.5}
        strokeDasharray="4 3"
      />
      <text
        x={x}
        y={padY - 6 - row * MARKER_LABEL_ROW_HEIGHT}
        textAnchor="middle"
        fontFamily="var(--font-mono)"
        fontSize={10}
        fill={color}
      >
        {label}
      </text>
    </g>
  )
}

// Two markers whose x-positions are closer than this (in the SVG's local
// coordinate space) render labels that visually collide — "Current" landing
// on top of "P95" for a name trading near its Monte Carlo distribution's
// tail was the reported symptom. ~28px comfortably clears a 4-5 char mono
// label ("P95", "Current") at fontSize 10 with textAnchor="middle".
const MARKER_LABEL_MIN_GAP = 28
const MARKER_LABEL_ROW_HEIGHT = 11

// Greedy left-to-right label stacking: sort markers by x, then for each one
// walk up rows until it lands MARKER_LABEL_MIN_GAP away from the last label
// placed on that row. Two markers at (nearly) the same x end up on different
// rows instead of drawing overlapping text; markers far enough apart share
// row 0 (the original, un-staggered layout).
function layoutMarkerRows(markers: { key: string; x: number }[]): Map<string, number> {
  const rows = new Map<string, number>()
  const lastXByRow: number[] = []
  for (const m of [...markers].sort((a, b) => a.x - b.x)) {
    let row = 0
    while (lastXByRow[row] !== undefined && m.x - lastXByRow[row] < MARKER_LABEL_MIN_GAP) {
      row += 1
    }
    lastXByRow[row] = m.x
    rows.set(m.key, row)
  }
  return rows
}

// ---------------------------------------------------------------------------
// Sniper: deterministic price levels — buy / stop / target + R/R
// ---------------------------------------------------------------------------

function SniperPanel({
  sniper,
  t,
  fmtPx,
  current = null,
  holdNote = null,
  neutralNote,
}: {
  sniper: SniperShape
  t: (key: string, params?: Record<string, string | number>) => string
  fmtPx: (v: number) => string
  // The snapshot price, so a "20-day support" that IS the price can say so.
  current?: number | null
  // The verdict-vs-tactical-box reconciliation, pre-resolved by the chapter so this
  // panel stays free of verdict/locale logic. Rendered only when the box actually
  // publishes directional cells (in NEUTRAL there are none).
  holdNote?: string | null
  // The NEUTRAL withheld-target note, worded to the real cause by the chapter and
  // rendered only in NEUTRAL (where the point target was withheld).
  neutralNote: string
}): React.ReactElement {
  type Cell = MetricCell
  // Two distinct readouts, NOT one trading-desk block (BACKLOG PM-review ②):
  //   • levelCells   — objective price-history facts (20-day support / resistance),
  //     independent of the DCF. The analytical technical content; always shown when
  //     present, including NEUTRAL where they're the only honest level left.
  //   • tacticalCells — the mechanical entry / stop / target / R-R / sizing derived
  //     from the DCF fair value. Extracted into a clearly-labelled, visually
  //     subordinate "Tactical Trade Reference" module so the technical chapter reads
  //     as IB research, not a retail day-trading signal. Empty in NEUTRAL → that
  //     module renders nothing (MetricModule returns null on zero cells).
  const levelCells: Cell[] = []
  const tacticalCells: Cell[] = []

  // NEUTRAL (levels-only): the valuation synthesis flagged itself unreliable, so
  // the headline target was withheld. No directional trade may be anchored to it
  // — every trade-level field is null and only support/resistance render, with an
  // explicit note so the empty trade section never reads as a silent drop (B1).
  const isNeutral = sniper.direction === 'NEUTRAL'
  // SHORT (SELL-rated) flips the trade structure: ideal_buy/secondary_buy are
  // SHORT entries, take_profit is the cover target BELOW entry, stop_loss is
  // ABOVE entry. Labels switch so a SELL report never reads as a long.
  const isShort = !isNeutral && (sniper.direction === 'SHORT' || sniper.sell_mode === true)

  if (sniper.ideal_buy != null) {
    // The entry level can sit ABOVE the market when the required discount is
    // already met — the backend then clamps `ideal_buy` DOWN to the current
    // price and flags `ideal_buy_at_market`. Without the sub-label the row read
    // as a contradiction ("ideal buy 54% above the price, yet Buy now"). We keep
    // the Ideal Buy label + clamped price and disclose WHY, carrying both the
    // required and the achieved discount.
    const required =
      typeof sniper.safety_margin === 'number' && Number.isFinite(sniper.safety_margin)
        ? sniper.safety_margin
        : null
    const achieved =
      typeof sniper.safety_margin_achieved === 'number' &&
      Number.isFinite(sniper.safety_margin_achieved)
        ? sniper.safety_margin_achieved
        : null
    const atMarket = !isShort && sniper.ideal_buy_at_market === true
    let sub: string | undefined
    if (atMarket && required !== null && achieved !== null) {
      sub = t('chapter.technical.sniper.safetyMarginAtMarket', {
        required: (required * 100).toFixed(0),
        achieved: (achieved * 100).toFixed(0),
      })
    } else if (atMarket) {
      sub = t('chapter.technical.sniper.safetyMarginAtMarketSolo')
    } else if (!isShort && required !== null) {
      sub = t('chapter.technical.sniper.safetyMargin', { pct: (required * 100).toFixed(0) })
    }
    tacticalCells.push({
      label: isShort
        ? t('chapter.technical.sniper.idealShort')
        : t('chapter.technical.sniper.idealBuy'),
      value: fmtPx(sniper.ideal_buy),
      tone: isShort ? undefined : 'up',
      sub,
    })
  }
  if (sniper.secondary_buy != null) {
    tacticalCells.push({
      label: isShort
        ? t('chapter.technical.sniper.secondaryShort')
        : t('chapter.technical.sniper.secondaryBuy'),
      value: fmtPx(sniper.secondary_buy),
      sub: isShort
        ? t('chapter.technical.sniper.atResistance')
        : t('chapter.technical.sniper.atSupport'),
    })
  }
  if (sniper.stop_loss != null) {
    tacticalCells.push({
      label: t('chapter.technical.sniper.stopLoss'),
      value: fmtPx(sniper.stop_loss),
      tone: 'down',
    })
  }
  if (sniper.take_profit != null) {
    tacticalCells.push({
      label: isShort
        ? t('chapter.technical.sniper.coverTarget')
        : t('chapter.technical.sniper.takeProfit'),
      value: fmtPx(sniper.take_profit),
      tone: 'up',
      sub: isShort
        ? t('chapter.technical.sniper.dcfCover')
        : t('chapter.technical.sniper.dcfTarget'),
    })
  }
  if (sniper.risk_reward_ratio != null) {
    const rr = sniper.risk_reward_ratio
    tacticalCells.push({
      label: t('chapter.technical.sniper.rrRatio'),
      value: rr.toFixed(2),
      tone: rr >= 2 ? 'up' : rr >= 1 ? undefined : 'down',
    })
  }
  if (sniper.position_size_pct != null) {
    tacticalCells.push({
      label: t('chapter.technical.sniper.suggestedSize'),
      value: `${sniper.position_size_pct.toFixed(1)}%`,
      sub: t('chapter.technical.sniper.ofPortfolio'),
    })
  }

  if (sniper.support_level != null) {
    // The trailing-20-session minimum of CLOSES. When the latest close IS that
    // minimum the level equals the market price, and "support" then reads as a
    // cushion below the tape that does not exist (NVDA 2026-10-16: support $217.23
    // == the $217.23 close, which an external reviewer read as a field echo). The
    // number is a real price-history fact — label the fact.
    const supportIsPrice =
      current != null && Math.abs(sniper.support_level - current) < 0.005
    levelCells.push({
      label: t('chapter.technical.sniper.support20d'),
      value: fmtPx(sniper.support_level),
      ...(supportIsPrice
        ? { sub: t('chapter.technical.sniper.support20dIsPrice') }
        : {}),
    })
  }
  if (sniper.resistance_level != null) {
    levelCells.push({
      label: t('chapter.technical.sniper.resistance20d'),
      value: fmtPx(sniper.resistance_level),
    })
  }

  return (
    <div style={{ margin: '22px 0' }}>
      {isNeutral && (
        <p style={mutedNote} data-testid="sniper-neutral-note">
          {neutralNote}
        </p>
      )}
      {/* Objective technical levels — the analytical content of this section. */}
      <MetricModule
        title={t('chapter.technical.subheading.sniper')}
        accent="cyan"
        cells={levelCells}
        columns={2}
      />
      {/* Tactical execution levels are a derived, optional adjunct — not the
          investment thesis. The caption frames them as such; in NEUTRAL the array
          is empty and this whole block renders nothing. */}
      {tacticalCells.length > 0 && (
        <>
          <p style={tacticalNote} data-testid="sniper-tactical-note">
            {t('chapter.technical.sniper.tacticalFraming')}
          </p>
          {holdNote && (
            <p style={holdReconciliationNote} data-testid="sniper-hold-reconciliation">
              {holdNote}
            </p>
          )}
          <MetricModule
            title={t('chapter.technical.subheading.tacticalReference')}
            accent="primary"
            cells={tacticalCells}
            columns={2}
          />
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Historical EV/EBITDA bands: timeline + P25 / median / P75 / P90 bands
// ---------------------------------------------------------------------------

const CLASSIFICATION_COLORS: Record<string, string> = {
  expensive: 'var(--danger)',
  fair: 'var(--accent-cyan)',
  cheap: 'var(--success)',
  unknown: 'var(--text-muted)',
}

function HistoricalBandPanel({
  band,
  t,
}: {
  band: HistoricalBandShape
  t: (key: string, params?: Record<string, string | number>) => string
}): React.ReactElement {
  const timeline = band.timeline ?? []
  const cls = band.classification ?? 'unknown'
  const color = CLASSIFICATION_COLORS[cls] ?? 'var(--text-muted)'
  // Display label localised; raw `cls` stays the enum for color/logic above.
  const clsLabel = t(`chapter.technical.band.${cls in CLASSIFICATION_COLORS ? cls : 'unknown'}`)

  const width = 720
  const height = 220
  const padX = 44
  const padY = 24
  const innerW = width - padX * 2
  const innerH = height - padY * 2

  const values = timeline.map(([, v]) => v)
  const minVal =
    values.length > 0 ? Math.min(...values, band.p25 ?? Infinity, band.median ?? Infinity) : 0
  const maxVal =
    values.length > 0
      ? Math.max(...values, band.p75 ?? -Infinity, band.p90 ?? -Infinity, band.current ?? -Infinity)
      : 0
  const spanV = maxVal - minVal || 1

  const yScale = (v: number): number => padY + innerH - ((v - minVal) / spanV) * innerH
  const xScale = (i: number): number =>
    timeline.length > 1 ? padX + (i / (timeline.length - 1)) * innerW : padX

  const path = timeline
    .map(([, v], i) => `${i === 0 ? 'M' : 'L'}${xScale(i)},${yScale(v)}`)
    .join(' ')

  return (
    <div>
      <div style={{ ...statRow, alignItems: 'center' }}>
        <Stat
          label={t('chapter.technical.band.current')}
          value={
            band.current !== undefined && band.current !== null
              ? `${band.current.toFixed(1)}x`
              : '—'
          }
        />
        <Stat
          label={t('chapter.technical.band.median')}
          value={
            band.median !== undefined && band.median !== null ? `${band.median.toFixed(1)}x` : '—'
          }
        />
        <Stat
          label="P25"
          value={band.p25 !== undefined && band.p25 !== null ? `${band.p25.toFixed(1)}x` : '—'}
        />
        <Stat
          label="P75"
          value={band.p75 !== undefined && band.p75 !== null ? `${band.p75.toFixed(1)}x` : '—'}
        />
        <Stat
          label="P90"
          value={band.p90 !== undefined && band.p90 !== null ? `${band.p90.toFixed(1)}x` : '—'}
        />
        <span
          data-testid="band-classification"
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            padding: '4px 10px',
            borderRadius: 3,
            border: `1px solid ${color}`,
            color,
            marginLeft: 'auto',
          }}
        >
          {clsLabel}
        </span>
      </div>

      {/* Structural-break caveat: the CHEAP/FAIR/EXPENSIVE badge is computed over the
          band window, so when a YoY EBITDA step sits inside it the P25/P90 quantiles
          are driven by the pre-step base — the badge is directional only. Rendered
          beside the badge so it is never read as a clean signal. */}
      {band.classification_caveat && (
        <p data-testid="band-classification-caveat" style={bandCaveatStyle}>
          {band.classification_caveat}
        </p>
      )}

      {timeline.length > 1 && (
        <svg
          role="img"
          aria-label="Historical EV/EBITDA timeline"
          data-testid="band-timeline"
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', display: 'block', marginTop: 12 }}
        >
          {band.p90 !== undefined && band.p90 !== null && (
            <BandLine
              y={yScale(band.p90)}
              label="P90"
              color="var(--warning)"
              width={width}
              padX={padX}
            />
          )}
          {band.p75 !== undefined && band.p75 !== null && (
            <BandLine
              y={yScale(band.p75)}
              label="P75"
              color="var(--secondary)"
              width={width}
              padX={padX}
            />
          )}
          {band.median !== undefined && band.median !== null && (
            <BandLine
              y={yScale(band.median)}
              label="Median"
              color="var(--accent-cyan)"
              width={width}
              padX={padX}
            />
          )}
          {band.p25 !== undefined && band.p25 !== null && (
            <BandLine
              y={yScale(band.p25)}
              label="P25"
              color="var(--success)"
              width={width}
              padX={padX}
            />
          )}
          <path d={path} stroke="var(--text-primary)" strokeWidth={1.5} fill="none" />
          {band.current !== undefined && band.current !== null && timeline.length > 0 && (
            <circle cx={xScale(timeline.length - 1)} cy={yScale(band.current)} r={5} fill={color} />
          )}
        </svg>
      )}
    </div>
  )
}

function BandLine({
  y,
  label,
  color,
  width,
  padX,
}: {
  y: number
  label: string
  color: string
  width: number
  padX: number
}): React.ReactElement {
  return (
    <g>
      <line
        x1={padX}
        x2={width - padX}
        y1={y}
        y2={y}
        stroke={color}
        strokeWidth={1}
        strokeDasharray="3 3"
        opacity={0.7}
      />
      <text x={width - padX + 4} y={y + 3} fontFamily="var(--font-mono)" fontSize={10} fill={color}>
        {label}
      </text>
    </g>
  )
}

// ---------------------------------------------------------------------------
// Shared inline atoms
// ---------------------------------------------------------------------------

function Stat({ label, value }: { label: string; value: string }): React.ReactElement {
  return (
    <div>
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          color: 'var(--text-muted)',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 13,
          color: 'var(--text-primary)',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {value}
      </div>
    </div>
  )
}

const statRow: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 18,
  alignItems: 'flex-end',
  margin: '4px 0 8px',
}

// Caliber caveat under the band badge (structural EBITDA break inside the window):
// warning-adjacent, because it says the CHEAP/FAIR/EXPENSIVE badge is directional.
const bandCaveatStyle: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 10.5,
  lineHeight: 1.6,
  color: 'var(--text-muted)',
  background: 'var(--bg-card-50)',
  borderLeft: '2px solid color-mix(in srgb, var(--warning) 55%, transparent)',
  borderRadius: 'var(--radius-sm)',
  padding: '6px 10px',
  margin: '0 0 8px',
}

const mutedNote: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11.5,
  color: 'var(--text-muted)',
  padding: '14px 18px',
  background: 'var(--bg-card-50)',
  border: '1px dashed var(--border-soft)',
  borderRadius: 'var(--radius-sm)',
}

// Lead-in framing for the Tactical Trade Reference module: a quiet caption (no
// boxed/dashed treatment — that reads as a warning) that signals the levels below
// are a derived implementation adjunct, not the report's view.
const tacticalNote: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  lineHeight: 1.65,
  letterSpacing: '0.02em',
  color: 'var(--text-muted)',
  margin: '20px 0 0',
}

// Reconciliation of the tactical box with a HOLD verdict: warning-toned (unlike the
// quiet tactical caption) because the two DO read as contradictory without it — a
// directional LONG reference beside a HOLD headline.
const holdReconciliationNote: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 11,
  lineHeight: 1.65,
  letterSpacing: '0.02em',
  color: 'var(--warning)',
  background: 'color-mix(in srgb, var(--warning) 10%, transparent)',
  border: '1px solid color-mix(in srgb, var(--warning) 38%, transparent)',
  borderLeft: '3px solid var(--warning)',
  borderRadius: 'var(--radius-sm)',
  padding: '8px 12px',
  margin: '10px 0 0',
}
