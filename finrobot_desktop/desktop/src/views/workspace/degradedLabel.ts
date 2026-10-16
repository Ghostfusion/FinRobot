// Maps a backend degradation marker (NormalizedFinancials.provenance.degraded,
// defined in finrobot/engine/data/normalize/contracts.py) to a human label.
//
// 可溯源 red-line: a fallback/skip/divergence must be VISIBLE and READABLE — never
// leak the raw developer code (e.g. "circuit_open:fmp") to the analyst. Two of the
// markers are prefixed `<kind>:<detail>` (the skipped provider / the diverging
// field) and interpolate that detail into the label.

type Translate = (id: string, values?: Record<string, string | number>) => string

// Exact-match markers → i18n key suffix under `workspace.market.degraded.*`.
const EXACT_LABEL_KEYS: Record<string, string> = {
  close_only: 'closeOnly',
  ttm_lag: 'ttmLag',
  ccy_inferred: 'ccyInferred',
  price_fallback_close: 'priceFallbackClose',
  period_basis_unknown: 'periodBasisUnknown',
  price_history_stale: 'priceHistoryStale',
  // The PRICE feed's three quote codes (contracts.py DEGRADED_QUOTE_*). They ride
  // the same `Provenance.degraded` list as the financials' markers above — the
  // extractor merges both into `raw_data.provenance.degraded` — so they must be
  // readable here too: the 2026-10-16 NVDA review read the report's degraded
  // markers and only ever saw the raw `quote_ts_missing` code.
  quote_ts_missing: 'quoteTsMissing',
  quote_currency_missing: 'quoteCurrencyMissing',
  quote_currency_inferred: 'quoteCurrencyInferred',
}

export function degradedLabel(t: Translate, flag: string): string {
  const exact = EXACT_LABEL_KEYS[flag]
  if (exact) return t(`workspace.market.degraded.${exact}`)

  const sep = flag.indexOf(':')
  if (sep > 0) {
    const kind = flag.slice(0, sep)
    const detail = flag.slice(sep + 1)
    if (kind === 'circuit_open')
      return t('workspace.market.degraded.circuitOpen', { provider: detail.toUpperCase() })
    if (kind === 'provider_divergence')
      return t('workspace.market.degraded.providerDivergence', { field: detail })
    if (kind === 'price_divergence')
      return t('workspace.market.degraded.priceDivergence', { field: detail })
  }

  // Unknown marker — show it raw rather than swallow it (still visible, just not pretty).
  return flag
}
