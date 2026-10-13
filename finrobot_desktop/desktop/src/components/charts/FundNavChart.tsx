// FundNavChart — a fund's trailing per-share NAV / traded-close line.
//
// Deliberately NOT one of the statement charts (RevenueEbitdaChart / CashFlowChart
// / MarginTrendChart): a fund files no income statement, so nothing on this chart
// may be read as a company's revenue, EBITDA or cash flow. The single series is
// the fund's own per-share NAV — for a NAV-priced mutual fund the traded close IS
// that NAV, and for an exchange-traded fund it is the market price of a share of
// the fund. One series, one meaning.
//
// House chart conventions: cosmic design tokens, JetBrains Mono axis ticks, and
// the shared CosmicTooltip (the default Recharts tooltip blends into the surface).
// The caller gates on a non-empty series — a fund whose run fetched no bars
// renders no chart rather than an empty frame.

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useI18n } from '../../i18n'
import { formatCurrency, formatDate } from '../../utils/format'
import { CosmicTooltip } from './chartTooltip'

/** One dated point of the trailing series (oldest → newest), as persisted by the
 *  fund run under `outputs.structured.nav_series`. */
export interface FundNavPoint {
  date: string
  close: number
}

interface FundNavChartProps {
  points: FundNavPoint[]
  /** ISO code of the currency the closes are quoted in. */
  currency: string
}

const AXIS_TICK = {
  fill: 'var(--text-muted)',
  fontSize: 11,
  fontFamily: "'JetBrains Mono', monospace",
} as const

export default function FundNavChart({
  points,
  currency,
}: FundNavChartProps): React.ReactElement | null {
  const { locale, t } = useI18n()
  if (points.length === 0) return null

  // Pad the value axis 4% each side so the line never sits on the frame. A
  // single-point series would otherwise collapse to a zero-height domain.
  const closes = points.map((p) => p.close)
  const low = Math.min(...closes)
  const high = Math.max(...closes)
  const pad = high - low > 0 ? (high - low) * 0.04 : Math.max(Math.abs(high) * 0.01, 0.01)
  const domain: [number, number] = [low - pad, high + pad]

  return (
    <div data-testid="fund-nav-chart" style={{ marginTop: 12 }}>
      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          color: 'var(--text-muted)',
          letterSpacing: '0.04em',
          marginBottom: 6,
        }}
      >
        {t('report.fund.risk.chartCaption', { currency })}
      </div>
      <div style={{ height: 220, minWidth: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="fund-nav-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--accent-cyan)" stopOpacity={0.28} />
                <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={AXIS_TICK}
              tickFormatter={(d: string) => formatDate(d, locale, 'short')}
              minTickGap={28}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={domain}
              tick={AXIS_TICK}
              width={68}
              tickFormatter={(v: number) => formatCurrency(v, currency, locale)}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              content={
                <CosmicTooltip
                  format={(v) => formatCurrency(v, currency, locale)}
                  labelFormat={(d) => formatDate(String(d), locale, 'short')}
                />
              }
            />
            <Area
              type="monotone"
              dataKey="close"
              stroke="var(--accent-cyan)"
              strokeWidth={1.6}
              fill="url(#fund-nav-fill)"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
