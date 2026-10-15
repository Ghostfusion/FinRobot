# CF audit remediation (2026-10-15)

An external reviewer re-derived the latest CF artifact from its own inputs — deliberately **without**
checking market data, XBRL or news against outside sources — and reported eight defects. This is the
claim-by-claim disposition: what reproduced, what did not, what the fix was in the code that produced
it, and what the review missed.

Audited artifact: `art_2026-10-15T00:50:08_CF_equity_research_9ab092` (CF Industries Holdings,
`equity_research`, SELL, target $80.69, confidence high), generated 19:50 local 2026-10-14.

Method: the artifact's payload, the canonical snapshot (`GET /api/data/CF/financials`), the live
Yahoo statement frames the provider reads, the rendered report (`/stocks/CF/runs/<id>`), the
producer's own code, and `git log -S` on every clause named below. The reviewer's arithmetic was
re-run in full: every figure in their "what checks out" list reproduces, as do all four NCI
scenarios in finding 3 and both EV/EBITDA constructions in finding 2 (to the cent).

## Verdict on the audit

| # | Reviewer claim | Verified? | Cause in code | Fix |
|---|---|---|---|---|
| 1 | Operating margin 49.33% is impossible (TTM operating income 3,025M ÷ revenue 7,739M = 39.09%, and it exceeds the 42.49% gross margin) | **Confirmed** — already fixed at HEAD; the artifact predates the fix | `yfinance_provider._fetch_financials` published Yahoo's `info.operatingMargins` scalar beside frame-derived `operating_income`/`revenue`; the C10d caliber note named only `ebitda`/`gross_margin`/`total_debt` | The margins are derived from the frame the snapshot publishes (fix `4e1a75f`, 2026-10-14 15:41). What was still broken is why a *fixed* build shipped it: the payload was cached 06:19:09Z, before the fix, under a 24h TTL and an unchanged version tag → `financials` raw slot **v6** + `CANONICAL_CONTRACT_VERSION` **13**, and **new clause `C10e`** (a published ratio must equal its own operands) so the class cannot ship silently again |
| 2 | EV/EBITDA has two bases: the thesis' 4.9× (market cap + net debt, $19.2B) vs the valuation chapter's 5.6× (the $22.05B EV including NCI) | **Confirmed** | `_ev_ebitda_method` computed the price-implied multiple as `price × shares + net debt` (4.910×) while the technical chapter's `historical_bands.current` is the canonical EV ÷ operating EBITDA (5.635×) — the same label on two constructions | Both sides now route through the existing single authorities (`multiples.implied_ev_multiple` / `ev_band_equity_per_share`), so the method's own sentence, the rail's "now" and the data page's EV/TTM-EBITDA are one number |
| 3 | NCI is deducted in the DCF ($3,172M ≈ $21/share) but not in the EV/EBITDA method; the asymmetry moves the target $71–92 | **Confirmed** (all four scenarios reproduce: NCI in both → $71.08, neither → $92.04, DCF without NCI → $96.81, median-at-4.20× ± NCI → $80.15 / $101.11) | `valuation_aggregator._ev_ebitda_method` bridged **net debt only** while the cross-check printed beside it passed `preferred_stock` + `noncontrolling_interest` through `ev_band_equity_per_share` — one report, two bridges for one multiple | The method takes the full bridge (net debt + preferred + NCI). Pinned by `test_ev_ebitda_method_and_cross_check_share_one_bridge`, which fails if either side loses a leg |
| 4 | The "Priced for growth" callout contradicts the report (implied growth is −9.8%/yr; the gap is the discount rate) | **Confirmed** | `ReverseDcfHeadline`'s reframing sentence branched on the SIZE of the premium (`multiple ≥ 1.05`) and hard-coded "that premium is a bet on the implied growth", in a panel that already prints the market's implied growth | The sentence branches on the DRIVER too: a negative implied growth reads "Priced on the discount rate … a bet on the discount rate, not on growth" |
| 5 | Market cap doesn't match price × shares (17.74B vs 18.08B, ~2%) | **Confirmed** — and its cause is the artifact's own session change | `market_cap` rides the FINANCIALS canonical while `current_price` rides the PRICE canonical; the two have independent TTLs, so the cap is one session old (cap ÷ shares = $117.25 against the run's $119.46 close — the same +1.88% the report prints as "last session") | The extractor now discloses the divergence whenever the cap's implied price and the resolved quote disagree by more than 1% — a threshold that is meaningful because Yahoo derives `marketCap = shares × price`, so same-instant data closes to the cent |
| 6a | The tactical cover uses the DCF's $75.85, not the headline $80.69 | **Confirmed, by design** (R/R 3.04 recomputes on that cover) | `sniper.take_profit` is the DCF intrinsic, and the thesis copy says so ("DCF intrinsic $75.85 … · cover=$75.85") plus a notice that the box is a tactical reference, not the thesis | No change |
| 6b | Two 13F rows report an inconsistent value per share (Geode ≈ $117, Jones ≈ $106 vs $108.3) | **Confirmed, and wider** — four rows are off the quarter's basis (Geode $116.95, Jones $105.70, Mediolanum $105.40, Raiffeisen $108.01, against $108.26 for the other 16) | Nothing compared a row's own two figures: a 13F-HR reports SHARES and VALUE for one security at one period end, so every row on the same CUSIP must imply the same price | `ownership.holding_value_basis_warning` names the rows whose implied price disagrees with the same CUSIP/quarter median, and says which aggregates inherit it (top-5 concentration, listed-share total) — abstaining below three rows |
| 6c | The EPS chart stops at FY2024 | **Refuted** | — | The rendered chart reads `2022 2023 2024 2025 → $16.45 $7.89 $6.75 $8.98`; `historical_metrics.eps` carries all four years and the chart filters only on non-null |
| 6d | The DCF panel labels β 0.53 but the WACC uses a Blume-adjusted β of about 0.69 | **Refuted as a number** — and the copy invited it | `cost_of_equity` 6.5292% = 4.3% + **0.527** × 4.23%, i.e. the raw β: `adjust_beta_blume` is asymmetric and leaves β ≤ 1 alone (`wacc.py`). With 0.69 the WACC would be 6.583%, not 6.0101%. But the tile note said "DCF uses a Blume-adjusted β" with no threshold, which is exactly how a reader computes 0.69 | The tile note, and the term dictionary's β entry, now state the β > 1 condition |

## Found by this pass, not in the review

| Defect | Cause in code | Fix |
|---|---|---|
| The valuation chapter and thesis printed **"46.8% of the $80.69 enterprise value"** — the enterprise value is $15,783,943,454, and it still prints correctly in the risk bullets that *are* not scanned | `_reconcile_narrative_targets` rewrites any un-whitelisted prose `$-amount` to the canonical target. Magnitude-suffixed totals (`$3.41T`) were already skipped; the un-suffixed comma form was not, so a correct sentence was rewritten into a number that contradicted its own risk list | A total cannot be a per-share restatement: the scrubber now skips an amount more than 10× every per-share reference it holds, or ≥ $1,000,000 |
| The XBRL snapshot published **noncontrolling interest −5,748,000,000** (assets 15,099 − "liabilities" 15,099 = 0) | `edgar_provider._LATEST_TOTAL_LIABILITIES_CONCEPTS` listed `LiabilitiesAndStockholdersEquity` — the balance-sheet identity total, which equals Assets by definition — as a liabilities fallback. C10c could not see it: the record is internally consistent (0 = 0, parent + NCI = 0) | The concept is no longer a liabilities source (an issuer without a true liabilities tag abstains), and `_equity_identity_note` withholds an identity whose liabilities equal its assets |
| `C10d` (caliber-divergent accepts) could not have covered the operating margin even after the provider fix | `operating_margin` was never a compared/decided metric, so there was no decision record to annotate — and no clause divided a ratio by its operands at all | The new `C10e` clause reads only the artifact's own leaves, so it needs no decision record: measured 22 artifacts / 12 tickers over the 140-row store |
| The reject-and-retry class behind finding 5 is one line of arithmetic away from the reviewer's finding 2 | both were "two price/EV bases inside one artifact" | fixed together (see 2, 3, 5) |

## Live re-run (fresh process, current code, artifact persisted)

`python scripts/_regen_aapl_report.py`'s assembly, run for CF with the CLI's model resolution
(`use_env=True`), producing `art_2026-10-15T04:04:35_CF_equity_research_299087`. The cache version
bump means this run REFETCHED the financials payload rather than re-reading the pre-fix row.

| Number | Audited artifact (`…T00:50:08`) | After the fixes (`…T04:04:35`) |
|---|---|---|
| `income.operating_margin` | 0.49325 — its own operands give 39.09%, and it exceeds the same block's 42.49% gross margin | **0.390877** = `operating_income ÷ revenue` to the last digit |
| EV/EBITDA method mid | $86.40 (net debt only) | **$65.44** (net debt + preferred + NCI) |
| EV/EBITDA method band | $45.86 – $126.95 | **$24.90 – $105.99** — now identical to the cross-check's own quantiles |
| Own-history cross-check | $24.90 / $80.15 / $105.99 (excluded from the blend) | unchanged, and no longer *different* from the method beside it |
| Blend → published target | $80.69 (band $75.85–$86.40) | **$70.98** (band $65.44–$75.67) — the reviewer's predicted "about $71" |
| Re-rating sentence | "4.9× → own 5y trailing band mid 3.6×" | "**5.7×** → own 5y **p25–p75 midpoint** 3.6× (0.63×)" |
| Verdict | SELL | **SELL** |
| Market cap vs price | $17.744B ⇒ $117.25 against a $119.46 quote, undisclosed | $18.079B = price × shares exactly, so no note is needed |
| Equity-identity NCI | −$5,748,000,000 | identity withholds (the L+E tag is no longer a liabilities source; the leaf is null) |
| 13F value per share | 4 rows off the quarter's basis, undisclosed | 3 rows named (Geode $116.95, Jones $105.70, Mediolanum $105.40) |
| "16% net income disagreement" | "a caliber gap (concept / window / filing rounding)" | "**is the noncontrolling-interest share of earnings** — 401,000,000 of it" |
| Contract `C10e` | clause did not exist | quiet on this artifact; fires on 22 of the 140 stored artifacts (the pre-fix population) |

Two things this run does NOT exercise, and where their evidence lives instead:

- The prose scrubber: this run's narrative never cites the enterprise value, so there is no live
  instance to compare. The fix is pinned by unit tests (a total is never rewritten; a plausible
  drift still is) and by the fact that the artifact *predating* the fix is the one that printed
  `$80.69 enterprise value`.
- The market-cap/price disclosure: the refetch made the cap and the quote the same session, so the
  note correctly stays silent. Its firing case is pinned by
  `test_extract_discloses_a_market_cap_one_session_behind_the_quote`.

## Verified, not a defect

- **The audit's own arithmetic**: the blend `(75.85 × 0.85 + 86.40 × 0.72) / 1.57 = 80.69`, net debt
  $1.13B, EBITDA $3.913B, net margin 27.1%, 52-week position 67%, drawdown −15.7%, Merton DD 4.86 with
  16.9% debt/value, top-5 concentration 77.5% of *listed* shares (8.2% of outstanding), R/R 3.04, the
  terminal-value share (46.8%) and the terminal multiple (16.2×).
- **The $3,172M NCI is real**, not a phantom: Yahoo's quarterly balance sheet at 2026-06-30 carries
  `Minority Interest 3,172,000,000` (total equity gross minority 8,920M = 5,748 parent + 3,172), and
  the TTM income frame carries `Minority Interests −401M` — which is exactly the artifact's
  "net income disagreement (16.0%)" (2,500 consolidated vs 2,099 parent). The pre-fix payload could
  not name that cause; HEAD's provider code does.
- **"Confidence: HIGH"**: the basis string publishes what the tier means ("wt = data-quality weight,
  NOT prediction accuracy") and the run's own gaps (one failed step, two methods, 16% net-income
  caliber gap) are all disclosed elsewhere in the artifact. The word "high" is a labelling policy,
  not a miscalculation.
- **The −14.1% revenue decay**: flat across all ten years, which the method's own assumptions string
  read as a fade (`10yr growth -14%→3.0%`); the terminal 46.8% share IS disclosed in the thesis and
  the valuation overview. The label now says "p25–p75 midpoint" instead of "band mid" so the
  reversion target is findable on the rail (the band's median is 4.20×, the midpoint of its
  published p25/p75 is 3.63×).
