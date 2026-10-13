// Fund chapter 04 — Risk & Return. The trailing record of the NAV/price the fund
// actually delivered, plus the risk that produced it.
//
// Returns are FRACTIONS in the artifact (0.0382 = 3.82%) and are rendered as
// percentages; `cagr_3y` / `cagr_5y` are annualised, which the labels say so the
// three horizons are not read as one comparable column. Volatility and max
// drawdown are fractions too — max drawdown is a loss, so it is toned as one.
//
// The chart is the fund's OWN per-share NAV / traded close (`nav_series`, oldest →
// newest). It is drawn only when the artifact carries the series: a fund's run can
// legitimately have no price bars (a NAV-priced fund with no fetched history), and
// inventing a curve — or borrowing a statement chart — would be the one thing this
// section must never do. A fund has no revenue, EBITDA or free cash flow, so no
// company P&L series may appear here even by accident.

import { useI18n } from '../../../i18n'
import FundNavChart, { type FundNavPoint } from '../../../components/charts/FundNavChart'
import { Chapter, SubChapter } from './ChapterBase'
import { MetricModule, type MetricCell } from './MetricModule'
import { fundNum, fundNumber, fundPercent } from './fundValues'
import type { FundStructuredShape } from './types'

interface Props {
  /** `outputs.structured` of a fund_research artifact (flat shape). */
  fund: FundStructuredShape
  /** Currency the NAV / price series is quoted in. */
  currency: string
}

export function FundRiskChapter({ fund, currency }: Props): React.ReactElement {
  const { locale, t } = useI18n()
  const returns = fund.returns ?? null

  const returnCells: MetricCell[] = [
    {
      label: t('report.fund.risk.cagr1y'),
      value: fundPercent(returns?.cagr_1y, locale, 2),
      tone: signTone(returns?.cagr_1y),
    },
    {
      label: t('report.fund.risk.cagr3y'),
      value: fundPercent(returns?.cagr_3y, locale, 2),
      tone: signTone(returns?.cagr_3y),
    },
    {
      label: t('report.fund.risk.cagr5y'),
      value: fundPercent(returns?.cagr_5y, locale, 2),
      tone: signTone(returns?.cagr_5y),
    },
    {
      label: t('report.fund.risk.ytd'),
      value: fundPercent(returns?.ytd, locale, 2),
      tone: signTone(returns?.ytd),
    },
    {
      label: t('report.fund.risk.r3m'),
      value: fundPercent(returns?.return_3m, locale, 2),
      tone: signTone(returns?.return_3m),
    },
  ]

  const measureCells: MetricCell[] = [
    {
      label: t('report.fund.risk.volatility'),
      value: fundPercent(fund.volatility, locale, 2),
    },
    {
      // A drawdown is a loss: a negative figure is toned down, and the label says
      // "loss from peak" so a positive sign is never read as a gain.
      label: t('report.fund.risk.maxDrawdown'),
      value: fundPercent(fund.max_drawdown, locale, 2),
      tone: (fundNum(fund.max_drawdown) ?? 0) < 0 ? 'down' : undefined,
    },
    {
      label: t('report.fund.risk.sharpe'),
      value: fundNumber(fund.sharpe, locale, 2),
    },
  ]

  // Only well-formed points reach the chart: a series missing a date or a finite
  // close would otherwise shift the whole axis with a NaN.
  const series: FundNavPoint[] = (fund.nav_series ?? []).filter(
    (p): p is FundNavPoint =>
      typeof p?.date === 'string' && p.date !== '' && fundNum(p?.close) !== null,
  )

  return (
    <Chapter id="fund-risk">
      <SubChapter heading={t('report.fund.risk.returnsTitle')}>
        <MetricModule
          title={t('report.fund.risk.returnsTitle')}
          accent="success"
          columns={3}
          meta={t('report.fund.risk.annualisedMeta')}
          cells={returnCells}
        />
        <p style={note}>{t('report.fund.risk.returnsNote')}</p>
      </SubChapter>
      <SubChapter heading={t('report.fund.risk.measuresTitle')}>
        <MetricModule
          title={t('report.fund.risk.measuresTitle')}
          accent="cyan"
          cells={measureCells}
        />
      </SubChapter>
      <SubChapter heading={t('report.fund.risk.chartTitle')}>
        {series.length === 0 ? (
          <p style={note}>{t('report.fund.risk.noSeries')}</p>
        ) : (
          <>
            <FundNavChart points={series} currency={currency} />
            <p style={note}>{t('report.fund.risk.chartNote')}</p>
          </>
        )}
      </SubChapter>
    </Chapter>
  )
}

/** Direction tone for a return: up (green in this palette) for a gain, down for a
 *  loss, and NO tone when the run did not report the figure — colouring an absent
 *  value would assert a direction the artifact does not have. */
function signTone(value: number | null | undefined): 'up' | 'down' | undefined {
  const v = fundNum(value)
  if (v === null) return undefined
  return v >= 0 ? 'up' : 'down'
}

const note: React.CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'var(--text-secondary)',
  margin: '10px 0 0',
  maxWidth: 820,
}
