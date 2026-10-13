import { useMemo } from 'react'

import { useI18n } from '../../i18n'

interface ChartProps {
  data: Record<string, number | string | boolean | null>[]
  title: string
  /** The DCF's own base WACC. When finite (with `baseTg`) the grid marks the
   *  cell matching the base case exactly, so the headline cell is unambiguous —
   *  the axis labels carry 2 decimals because a cell labelled "7.0%" holds a
   *  value computed at 6.97%. Absent/legacy ⇒ the old centre-cell marking. */
  baseWacc?: number | null
  /** The DCF's own base terminal growth rate. */
  baseTg?: number | null
}

// The 8 heatmap tiers, ordered HIGH implied value → LOW. These are the exact
// `hm-*` cell backgrounds (App.css): hm-5 = --legacy-green-30 (the most green,
// = highest implied price via heatmapClass mapping normalised≥0.9), down to
// hm--2 = --legacy-red-25 (the most red, = lowest implied price). The legend
// therefore reads green = higher implied value, red = lower implied value.
const LEGEND_RAMP = [
  'var(--legacy-green-30)',
  'var(--legacy-green-18)',
  'var(--legacy-green-08)',
  'var(--legacy-amber-06)',
  'var(--legacy-amber-12)',
  'var(--legacy-red-08)',
  'var(--legacy-red-15)',
  'var(--legacy-red-25)',
] as const

/**
 * Map normalised value [0, 1] to heatmap CSS class.
 */
function heatmapClass(normalised: number): string {
  if (normalised >= 0.9) return 'hm-5'
  if (normalised >= 0.75) return 'hm-4'
  if (normalised >= 0.6) return 'hm-3'
  if (normalised >= 0.5) return 'hm-2'
  if (normalised >= 0.4) return 'hm-1'
  if (normalised >= 0.25) return 'hm-0'
  if (normalised >= 0.1) return 'hm--1'
  return 'hm--2'
}

interface GridCell {
  wacc: number
  tg: number
  price: number
}

export default function SensitivityHeatmap({ data, title, baseWacc, baseTg }: ChartProps) {
  const { t } = useI18n()
  const memo = useMemo(() => {
    if (!data || data.length === 0) return null
    const cells: GridCell[] = data.map((d) => ({
      wacc: Number(d.wacc),
      tg: Number(d.tg),
      price: Number(d.implied_price),
    }))

    const waccSet = [...new Set(cells.map((c) => c.wacc))].sort((a, b) => a - b)
    const tgSet = [...new Set(cells.map((c) => c.tg))].sort((a, b) => a - b)

    const lookup = new Map<string, number>()
    for (const c of cells) {
      lookup.set(`${c.wacc}_${c.tg}`, c.price)
    }

    const prices = cells.map((c) => c.price)
    return {
      waccValues: waccSet,
      tgValues: tgSet,
      grid: lookup,
      minPrice: Math.min(...prices),
      maxPrice: Math.max(...prices),
    }
  }, [data])

  if (!memo) return null
  const { waccValues, tgValues, grid, minPrice, maxPrice } = memo

  const range = maxPrice - minPrice || 1
  // Legacy fallback: the grid centre (middle row, middle col). Superseded by the
  // exact base-case match whenever the DCF supplies its own base WACC / TGR —
  // the backend now makes the centre axis value the base WACC, but Gordon-floor
  // pruning can drop cells, so an EXACT match is the honest marker.
  const midWacc = waccValues[Math.floor(waccValues.length / 2)]
  const midTg = tgValues[Math.floor(tgValues.length / 2)]
  const hasBase =
    typeof baseWacc === 'number' &&
    Number.isFinite(baseWacc) &&
    typeof baseTg === 'number' &&
    Number.isFinite(baseTg)
  // Float-tolerant equality: serialized WACC/TGR round-trip, but a tolerance
  // guards against any residual representation drift.
  const matches = (a: number, b: number): boolean => Math.abs(a - b) <= Math.abs(b) * 1e-6 + 1e-12

  return (
    <div className="card animate-in">
      <div className="card-header">
        <span className="card-title">{title}</span>
      </div>
      <div className="card-body">
        <div className="heatmap-container">
          <table className="heatmap" role="table">
            <thead>
              <tr>
                <th className="corner" style={{ fontSize: '0.65rem' }}>
                  <span style={{ color: 'var(--accent)' }}>WACC</span>
                  {' \\ '}
                  <span style={{ color: 'var(--chart-1)' }}>TGR</span>
                </th>
                {tgValues.map((tg) => (
                  // Two decimals: a cell labelled "7.0%" held a value computed at
                  // 6.97% (the base WACC) — the rounded label sat beside an
                  // un-rounded computation. The base cell is now marked exactly.
                  <th key={tg}>{(tg * 100).toFixed(2)}%</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {waccValues.map((wacc) => (
                <tr key={wacc}>
                  <th>{(wacc * 100).toFixed(2)}%</th>
                  {tgValues.map((tg) => {
                    const price = grid.get(`${wacc}_${tg}`)
                    const normalised = price != null ? (price - minPrice) / range : 0.5
                    const isBase =
                      hasBase && matches(wacc, baseWacc as number) && matches(tg, baseTg as number)
                    // Centre-cell marking only survives as the legacy fallback.
                    const isCurrent = !hasBase && wacc === midWacc && tg === midTg
                    return (
                      <td
                        key={`${wacc}_${tg}`}
                        data-base={isBase ? 'true' : undefined}
                        className={`${heatmapClass(normalised)}${isBase ? ' base' : ''}${
                          isCurrent ? ' current' : ''
                        }`}
                        title={
                          isBase
                            ? t('chart.sensitivity.baseCell', {
                                wacc: (wacc * 100).toFixed(2),
                                tg: (tg * 100).toFixed(2),
                              })
                            : undefined
                        }
                      >
                        {price != null ? `$${price.toFixed(2)}` : '\u2014'}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div
          data-testid="heatmap-legend"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginTop: 12,
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'var(--text-muted)',
            letterSpacing: '0.03em',
          }}
        >
          <span>{t('chart.sensitivity.legend.lower')}</span>
          <span
            aria-hidden
            style={{
              display: 'flex',
              flex: '0 0 auto',
              height: 10,
              borderRadius: 2,
              overflow: 'hidden',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {/* Ramp ordered LOW→HIGH (red→green) left-to-right to match the
                "lower" → "higher" label flow; LEGEND_RAMP is HIGH→LOW so we
                walk it in reverse. */}
            {[...LEGEND_RAMP].reverse().map((c, i) => (
              <span key={i} style={{ width: 14, height: '100%', background: c }} />
            ))}
          </span>
          <span>{t('chart.sensitivity.legend.higher')}</span>
        </div>
      </div>
    </div>
  )
}
