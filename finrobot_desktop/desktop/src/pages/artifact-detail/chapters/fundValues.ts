// Shared formatting for the fund report's chapters (fund_research).
//
// Unit contract (the trap this module exists to close): every ratio, return,
// yield and weight the fund pipeline persists is a FRACTION — 0.0015 = 15 bp of
// expense, 0.0382 = a 3.82% yield, 0.068748 = a 6.87% position. So the fund
// chapters route every one of those through `fundPercent` (raw ratio → percent)
// and never through `alreadyPercent`, which would print 0.15 as "0.15%" and call
// a 15 bp fee a 15% one.
//
// Absent ≠ zero: a field the run did not report renders the explicit
// `report.fund.notReported` copy. A fund with no reported expense ratio must not
// read as a free fund, and a blank / "—" cell reads as a number the reader simply
// has to squint at.

import { tSync, type Locale } from '../../../i18n'
import {
  formatCurrency,
  formatCurrencyCompact,
  formatDate,
  formatNumber,
  formatPercent,
} from '../../../utils/format'

const NOT_REPORTED_KEY = 'report.fund.notReported'

/** A finite number, or null for absent / null / NaN / Infinity input. */
export function fundNum(value: number | null | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

/** Ratio → percent ("0.15%" for 0.0015), or the explicit not-reported copy. */
export function fundPercent(value: number | null | undefined, locale: Locale, digits = 2): string {
  const v = fundNum(value)
  return v === null ? tSync(NOT_REPORTED_KEY) : formatPercent(v, locale, digits)
}

/** Plain number ("1.24"), or the explicit not-reported copy. */
export function fundNumber(value: number | null | undefined, locale: Locale, digits = 2): string {
  const v = fundNum(value)
  return v === null ? tSync(NOT_REPORTED_KEY) : formatNumber(v, locale, digits)
}

/** Currency amount, or the explicit not-reported copy. */
export function fundCurrency(
  value: number | null | undefined,
  currency: string,
  locale: Locale,
  digits = 2,
): string {
  const v = fundNum(value)
  return v === null ? tSync(NOT_REPORTED_KEY) : formatCurrency(v, currency, locale, digits)
}

/** Compact currency ("$58.4B"), or the explicit not-reported copy. */
export function fundCurrencyCompact(
  value: number | null | undefined,
  currency: string,
  locale: Locale,
): string {
  const v = fundNum(value)
  return v === null ? tSync(NOT_REPORTED_KEY) : formatCurrencyCompact(v, currency, locale)
}

/** Calendar day, or the explicit not-reported copy. */
export function fundDate(value: string | null | undefined, locale: Locale): string {
  const s = (value ?? '').trim()
  return s === '' ? tSync(NOT_REPORTED_KEY) : formatDate(s, locale, 'short')
}

/** A reported string (name, family, legal type …), or the explicit not-reported copy. */
export function fundString(value: string | null | undefined): string {
  const s = (value ?? '').trim()
  return s === '' ? tSync(NOT_REPORTED_KEY) : s
}

/** A `{label: fraction}` mix as `[label, fraction]` pairs, largest first. Ties keep
 *  the artifact's own order (Array#sort is stable) — the mix is re-ordered for
 *  reading, never re-weighted. */
export function fundMixEntries(mix: Record<string, number> | null | undefined): [string, number][] {
  return Object.entries(mix ?? {})
    .filter(([, weight]) => fundNum(weight) !== null)
    .sort((a, b) => b[1] - a[1])
}
