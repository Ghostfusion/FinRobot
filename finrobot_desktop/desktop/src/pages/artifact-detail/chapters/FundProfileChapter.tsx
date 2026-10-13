// Fund chapter 01 — Fund Profile. WHAT the vehicle is and WHAT it costs to hold:
// identity (name / family / legal form / category / inception), size and pricing
// (total net assets, NAV per share against the market price, and the
// premium/discount between them), and the fee/income block (expense ratio against
// the vendor's category average, turnover, distribution yield).
//
// Three things this chapter refuses to do:
//   • print a bare `0` (or an em dash that reads like one) for a field the run did
//     not report — an unreported expense ratio must not read as a free fund, so
//     every absent value renders the explicit not-reported copy;
//   • re-derive a number the artifact already carries. The premium/discount is the
//     artifact's own `premium_discount_pct`, never recomputed from NAV vs price,
//     which would silently disagree with the backend when the two are stamped at
//     different instants;
//   • display an unlabelled decimal. Every ratio here is a FRACTION in the
//     artifact and is rendered through `fundPercent` (0.0015 → "0.15%").

import { useI18n } from '../../../i18n'
import { Chapter, SubChapter } from './ChapterBase'
import { MetricModule, type MetricCell } from './MetricModule'
import {
  fundCurrency,
  fundCurrencyCompact,
  fundDate,
  fundNum,
  fundPercent,
  fundString,
} from './fundValues'
import type { FundStructuredShape } from './types'

interface Props {
  /** `outputs.structured` of a fund_research artifact (flat shape). */
  fund: FundStructuredShape
  /** Currency the fund's per-share figures are quoted in. */
  currency: string
}

export function FundProfileChapter({ fund, currency }: Props): React.ReactElement {
  const { locale, t } = useI18n()

  const identityCells: MetricCell[] = [
    { label: t('report.fund.profile.name'), value: fundString(fund.name) },
    { label: t('report.fund.profile.family'), value: fundString(fund.fund_family) },
    { label: t('report.fund.profile.legalType'), value: fundString(fund.legal_type) },
    { label: t('report.fund.profile.category'), value: fundString(fund.category) },
    { label: t('report.fund.profile.inception'), value: fundDate(fund.inception_date, locale) },
  ]

  // Direction of the spread is a WORD, not just a sign the reader has to decode:
  // above NAV it is a premium, below NAV a discount, and for a NAV-priced fund
  // there is no second price to compare against at all.
  const spread = fundNum(fund.premium_discount)
  const spreadCap =
    fundNum(fund.market_price) === null
      ? t('report.fund.profile.navPriced')
      : spread === null
        ? null
        : spread > 0
          ? t('report.fund.profile.premium')
          : spread < 0
            ? t('report.fund.profile.discount')
            : t('report.fund.profile.atNav')

  const pricingCells: MetricCell[] = [
    {
      label: t('report.fund.profile.netAssets'),
      value: fundCurrencyCompact(fund.total_net_assets, currency, locale),
      sub: currency,
    },
    {
      label: t('report.fund.profile.nav'),
      value: fundCurrency(fund.nav_per_share, currency, locale),
      sub: currency,
    },
    {
      label: t('report.fund.profile.marketPrice'),
      value: fundCurrency(fund.market_price, currency, locale),
      sub: currency,
    },
    {
      label: t('report.fund.profile.premiumDiscount'),
      value: fundPercent(fund.premium_discount, locale, 2),
      sub: spreadCap,
    },
  ]

  const costCells: MetricCell[] = [
    {
      label: t('report.fund.profile.netExpense'),
      value: fundPercent(fund.net_expense_ratio, locale, 2),
    },
    {
      label: t('report.fund.profile.grossExpense'),
      value: fundPercent(fund.gross_expense_ratio, locale, 2),
    },
    {
      label: t('report.fund.profile.categoryAvgExpense'),
      value: fundPercent(fund.category_avg_expense_ratio, locale, 2),
    },
    {
      label: t('report.fund.profile.turnover'),
      value: fundPercent(fund.turnover, locale, 1),
    },
    {
      label: t('report.fund.profile.distributionYield'),
      value: fundPercent(fund.distribution_yield, locale, 2),
    },
  ]

  // Fee vs the vendor's own category average, stated as an arithmetic difference
  // the reader can check — the two figures it is computed from are both above,
  // printed as percentages. Rendered only when BOTH are reported; with one side
  // missing there is no comparison to make, and saying so beats comparing against
  // an implied zero.
  const net = fundNum(fund.net_expense_ratio)
  const category = fundNum(fund.category_avg_expense_ratio)
  const vsCategory =
    net === null || category === null
      ? t('report.fund.profile.expenseVsCategoryMissing')
      : t('report.fund.profile.expenseVsCategory', {
          delta: `${net - category >= 0 ? '+' : ''}${((net - category) * 100).toFixed(2)}`,
          category: fundPercent(category, locale, 2),
        })

  return (
    <Chapter id="fund-profile">
      <SubChapter heading={t('report.fund.profile.identityTitle')}>
        <MetricModule
          title={t('report.fund.profile.identityTitle')}
          accent="primary"
          cells={identityCells}
        />
      </SubChapter>
      <SubChapter heading={t('report.fund.profile.sizePricingTitle')}>
        <MetricModule
          title={t('report.fund.profile.sizePricingTitle')}
          accent="cyan"
          meta={t('report.fund.profile.perShareMeta', { currency })}
          cells={pricingCells}
        />
        <p style={note}>{t('report.fund.profile.premiumDiscountNote')}</p>
      </SubChapter>
      <SubChapter heading={t('report.fund.profile.costIncomeTitle')}>
        <MetricModule
          title={t('report.fund.profile.costIncomeTitle')}
          accent="violet"
          cells={costCells}
        />
        <p style={note}>{vsCategory}</p>
      </SubChapter>
    </Chapter>
  )
}

const note: React.CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'var(--text-secondary)',
  margin: '10px 0 0',
  maxWidth: 780,
}
