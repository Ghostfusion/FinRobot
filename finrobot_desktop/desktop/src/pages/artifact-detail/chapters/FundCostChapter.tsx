// Fund chapter 02 — Cost. What the fee actually costs a holder, in dollars.
//
// An expense ratio ("0.15%") is a rate, not a bill; the artifact's `cost_drag`
// block is the bill — dollars paid per $10,000 invested over the run's stated
// horizon, plus the fee's share of the return the portfolio earned BEFORE costs.
// Both come from the artifact verbatim (the backend owns the horizon and any
// compounding); this chapter only formats them and then shows the arithmetic
// behind the per-$10,000 figure so a reader can check it rather than take it.
//
// The reconstruction is deliberately labelled as such: it is the SIMPLE,
// undiscounted product of two disclosed inputs (net expense ratio × $10,000 ×
// horizon), which is what the headline equals when the run charges the fee on the
// opening balance and differs when it compounds — the note says so, instead of
// silently presenting our own arithmetic as the backend's number.

import { useI18n } from '../../../i18n'
import { formatCurrency } from '../../../utils/format'
import { Chapter, SubChapter } from './ChapterBase'
import { MetricModule, type MetricCell } from './MetricModule'
import { fundCurrency, fundNum, fundPercent } from './fundValues'
import type { FundStructuredShape } from './types'

interface Props {
  /** `outputs.structured` of a fund_research artifact (flat shape). */
  fund: FundStructuredShape
}

/** The per-$10,000 base the drag is quoted against — the artifact's own field name
 *  (`expense_drag_usd_per_10k`) and the unit the template sentence reads in. */
const DRAG_BASE_USD = 10_000

export function FundCostChapter({ fund }: Props): React.ReactElement {
  const { locale, t } = useI18n()
  const drag = fund.cost_drag ?? null
  const horizon = fundNum(drag?.horizon_years)
  const netRatio = fundNum(fund.net_expense_ratio)

  const cells: MetricCell[] = [
    {
      label: t('report.fund.cost.dragPer10k'),
      // `expense_drag_usd_per_10k` is USD by definition (the field names its own
      // base), so it is formatted in USD regardless of the fund's dealing
      // currency; an absent figure renders the explicit not-reported copy, never
      // a zero that would read as a free fund.
      value: fundCurrency(drag?.expense_drag_usd_per_10k, 'USD', locale),
      sub: horizon === null ? null : t('report.fund.cost.overYears', { years: horizon }),
    },
    {
      label: t('report.fund.cost.feeShare'),
      value: fundPercent(drag?.fee_share_of_gross_return, locale, 2),
    },
  ]

  // Simple, undiscounted reconstruction of the same cost from the disclosed rate.
  // Rendered only when the rate is reported; the horizon only widens it to N years.
  const annual = netRatio === null ? null : netRatio * DRAG_BASE_USD
  const arithmetic =
    netRatio === null || annual === null
      ? t('report.fund.cost.arithmeticUnavailable')
      : horizon === null
        ? t('report.fund.cost.arithmeticPerYear', {
            ratio: fundPercent(netRatio, locale, 2),
            annual: formatCurrency(annual, 'USD', locale),
          })
        : t('report.fund.cost.arithmetic', {
            ratio: fundPercent(netRatio, locale, 2),
            annual: formatCurrency(annual, 'USD', locale),
            years: horizon,
            total: formatCurrency(annual * horizon, 'USD', locale),
          })

  return (
    <Chapter id="fund-cost">
      <SubChapter heading={t('report.fund.cost.dragTitle')}>
        <MetricModule
          title={t('report.fund.cost.dragTitle')}
          accent="violet"
          columns={2}
          meta={t('report.fund.cost.dragMeta')}
          cells={cells}
        />
      </SubChapter>
      <SubChapter heading={t('report.fund.cost.arithmeticTitle')}>
        <p style={line}>{arithmetic}</p>
        <p style={note}>{t('report.fund.cost.arithmeticNote')}</p>
        <p style={note}>{t('report.fund.cost.feeShareNote')}</p>
      </SubChapter>
    </Chapter>
  )
}

const line: React.CSSProperties = {
  fontSize: 13.5,
  lineHeight: 1.7,
  color: 'var(--text-primary)',
  fontFamily: 'var(--font-mono)',
  margin: '0 0 4px',
  maxWidth: 820,
}

const note: React.CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'var(--text-secondary)',
  margin: '8px 0 0',
  maxWidth: 820,
}
