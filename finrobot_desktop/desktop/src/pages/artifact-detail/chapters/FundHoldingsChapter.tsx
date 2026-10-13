// Fund chapter 03 — Holdings & Allocation. WHAT the fund actually owns.
//
// Four independent views of the same portfolio, each rendered only when the run
// reported it and each labelled with what its absence means:
//   • asset-class mix      — the shape of the portfolio (equity / bond / cash …);
//   • sector weights       — meaningless for a portfolio with no equity exposure,
//                            so its absence is stated rather than rendered as an
//                            empty table;
//   • credit quality + duration/maturity — meaningless for an all-equity fund
//                            (there are no bonds to rate or to time), same rule;
//   • top holdings + concentration — who is in the book and how lopsided it is.
//
// Weights are FRACTIONS in the artifact (0.068748 = 6.87%) and are formatted as
// such. The "say so plainly when one is absent" rule is why an absent mix prints a
// sentence, not a blank: an empty sector table reads as "no sector risk", which is
// the opposite of true for an unreported breakdown.

import type { CSSProperties } from 'react'
import { useI18n } from '../../../i18n'
import { Chapter, SubChapter, TableScroll } from './ChapterBase'
import { MetricModule, type MetricCell } from './MetricModule'
import { fundMixEntries, fundNum, fundNumber, fundPercent, fundString } from './fundValues'
import type { FundStructuredShape } from './types'

interface Props {
  /** `outputs.structured` of a fund_research artifact (flat shape). */
  fund: FundStructuredShape
}

export function FundHoldingsChapter({ fund }: Props): React.ReactElement {
  const { locale, t } = useI18n()

  const assetClasses = fundMixEntries(fund.asset_classes)
  const sectors = fundMixEntries(fund.sector_weights)
  const regions = fundMixEntries(fund.region_weights)
  const ratings = fundMixEntries(fund.bond_ratings)
  const holdings = (fund.top_holdings ?? []).filter((h) => fundNum(h?.weight) !== null)

  const duration = fundNum(fund.bond_duration)
  const maturity = fundNum(fund.bond_maturity)
  const equityPe = fundNum(fund.equity_pe)
  const bondMeasures: MetricCell[] = [
    {
      label: t('report.fund.holdings.duration'),
      value: fundNumber(fund.bond_duration, locale, 2),
    },
    {
      label: t('report.fund.holdings.maturity'),
      value: fundNumber(fund.bond_maturity, locale, 2),
    },
    {
      label: t('report.fund.holdings.equityPe'),
      value: fundNumber(fund.equity_pe, locale, 1),
    },
  ]

  const concentration: MetricCell[] = [
    {
      label: t('report.fund.holdings.top10'),
      value: fundPercent(fund.concentration?.top10_weight, locale, 2),
    },
    {
      label: t('report.fund.holdings.hhi'),
      value: fundNumber(fund.concentration?.hhi, locale, 4),
    },
    {
      label: t('report.fund.holdings.effectiveN'),
      value: fundNumber(fund.concentration?.effective_n, locale, 1),
    },
  ]

  return (
    <Chapter id="fund-holdings">
      <SubChapter heading={t('report.fund.holdings.allocationTitle')}>
        {assetClasses.length === 0 ? (
          <p style={note}>{t('report.fund.holdings.noAllocation')}</p>
        ) : (
          <MixTable
            labelHead={t('report.fund.holdings.allocationHead')}
            valueHead={t('report.fund.holdings.weightHead')}
            rows={assetClasses.map(([label, weight]) => ({
              key: label,
              label,
              value: fundPercent(weight, locale, 2),
            }))}
          />
        )}
      </SubChapter>

      <SubChapter heading={t('report.fund.holdings.sectorsTitle')}>
        {sectors.length === 0 ? (
          <p style={note}>{t('report.fund.holdings.noSectors')}</p>
        ) : (
          <MixTable
            labelHead={t('report.fund.holdings.sectorsHead')}
            valueHead={t('report.fund.holdings.weightHead')}
            rows={sectors.map(([label, weight]) => ({
              key: label,
              label,
              value: fundPercent(weight, locale, 2),
            }))}
          />
        )}
      </SubChapter>

      {regions.length > 0 && (
        <SubChapter heading={t('report.fund.holdings.regionsTitle')}>
          <MixTable
            labelHead={t('report.fund.holdings.regionsHead')}
            valueHead={t('report.fund.holdings.weightHead')}
            rows={regions.map(([label, weight]) => ({
              key: label,
              label,
              value: fundPercent(weight, locale, 2),
            }))}
          />
        </SubChapter>
      )}

      <SubChapter heading={t('report.fund.holdings.creditTitle')}>
        {ratings.length === 0 ? (
          <p style={note}>{t('report.fund.holdings.noCredit')}</p>
        ) : (
          <MixTable
            labelHead={t('report.fund.holdings.creditHead')}
            valueHead={t('report.fund.holdings.weightHead')}
            rows={ratings.map(([label, weight]) => ({
              key: label,
              label,
              value: fundPercent(weight, locale, 2),
            }))}
          />
        )}
        {/* Duration / maturity are reported for a bond book and are structurally
            absent for an equity fund; the cell renders the explicit not-reported
            copy so the row can never be mistaken for a 0-year duration. The
            portfolio P/E lives here too — a fund can report it with no bond book
            at all, and it must still reach the page. */}
        {(ratings.length > 0 || duration !== null || maturity !== null || equityPe !== null) && (
          <div style={{ marginTop: 12 }}>
            <MetricModule
              title={t('report.fund.holdings.bondMeasuresTitle')}
              accent="cyan"
              meta={t('report.fund.holdings.yearsMeta')}
              cells={bondMeasures}
            />
          </div>
        )}
      </SubChapter>

      <SubChapter heading={t('report.fund.holdings.topHoldingsTitle')}>
        {holdings.length === 0 ? (
          <p style={note}>{t('report.fund.holdings.noHoldings')}</p>
        ) : (
          <MixTable
            labelHead={t('report.fund.holdings.nameHead')}
            symbolHead={t('report.fund.holdings.symbolHead')}
            valueHead={t('report.fund.holdings.weightHead')}
            rows={holdings.map((h) => ({
              key: `${h.symbol ?? ''}-${h.name ?? ''}`,
              label: fundString(h.name),
              second: fundString(h.symbol),
              value: fundPercent(h.weight, locale, 2),
            }))}
          />
        )}
      </SubChapter>

      <SubChapter heading={t('report.fund.holdings.concentrationTitle')}>
        <MetricModule
          title={t('report.fund.holdings.concentrationTitle')}
          accent="primary"
          cells={concentration}
        />
        <p style={note}>{t('report.fund.holdings.concentrationNote')}</p>
      </SubChapter>
    </Chapter>
  )
}

interface MixRow {
  key: string
  label: string
  /** Optional second column (a holding's ticker). */
  second?: string
  value: string
}

/** A label (→ weight) table. `value` is pre-formatted by the caller (the fund's
 *  weights are look-through fractions, so only the caller knows the unit), and the
 *  row order is the artifact's own ranking — never re-sorted here. */
function MixTable({
  labelHead,
  symbolHead,
  valueHead,
  rows,
}: {
  labelHead: string
  /** Optional second column (a holding's ticker) — rendered when any row has one. */
  symbolHead?: string
  valueHead: string
  rows: MixRow[]
}): React.ReactElement {
  const twoCol = symbolHead !== undefined && rows.some((r) => r.second !== undefined)
  return (
    <TableScroll>
      <table style={table}>
        <thead>
          <tr>
            <th style={thLeft}>{labelHead}</th>
            {twoCol && <th style={thLeft}>{symbolHead}</th>}
            <th style={thRight}>{valueHead}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} style={{ borderTop: '1px solid var(--border-grid)' }}>
              <td style={tdLeft}>{r.label}</td>
              {twoCol && <td style={tdDim}>{r.second ?? ''}</td>}
              <td style={tdRight}>{r.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableScroll>
  )
}

const table: CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontFamily: 'var(--font-mono)',
  fontSize: 11.5,
  margin: '4px 0 0',
}

const thLeft: CSSProperties = {
  padding: '4px 8px',
  textAlign: 'left',
  color: 'var(--text-muted)',
  fontWeight: 500,
}

const thRight: CSSProperties = { ...thLeft, textAlign: 'right' }

const tdLeft: CSSProperties = { padding: '4px 8px', color: 'var(--text-primary)' }

const tdDim: CSSProperties = { padding: '4px 8px', color: 'var(--text-dim)' }

const tdRight: CSSProperties = {
  padding: '4px 8px',
  textAlign: 'right',
  color: 'var(--text-secondary)',
}

const note: CSSProperties = {
  fontSize: 12.5,
  lineHeight: 1.6,
  color: 'var(--text-secondary)',
  margin: '4px 0 0',
  maxWidth: 820,
}
