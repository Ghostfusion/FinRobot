# Report audit remediation — 2026-10-13 NVDA full report

An external reviewer audited `art_2026-10-13T23:06:12_NVDA_equity_research_abfc58`
against itself and against outside sources. This document records what was actually
wrong, what changed, and what remains a stated limit. Every root cause below was traced
to code before a change was made; nothing here is a re-narration of the report.

## Shipped fixes

| Reviewer defect | Root cause found in code | Fix |
|---|---|---|
| Key Takeaways: `$259.87 of purchases` (the DCF target) against `$0` purchases | the prompt supplied the true `$0` leaf, but the claim checker matches an amount to ANY computed leaf — `$259.87` is the target, so the misattribution passed a membership test | prompt rule (`insider_buy_value == 0` must be stated as "no open-market purchases"; no other number may be quoted as a purchase amount) **plus** a new relationship verifier `audit/insider_flow.py` — and, because the same misattribution recurred on the next live run with the new target ($231.38, this time also as the "largest single sale"), the builder now CORRECTS the offending token to the computed leg before the narrative is mirrored, and discloses every substitution as `[NUMERIC-AUDIT/correction]`. A figure that cannot be attributed safely (two nouns claiming one token, or a printed value that is itself a sibling insider leaf) is reported and left untouched rather than silently moved |
| `Quote currency: UNKNOWN` for the price while the artifact is USD | EODHD, the PRICE primary, hardcodes `exchange`/`quote_currency` = None and its `/eod` rows carry no currency | the provider now resolves the ticker's exchange suffix (`NVDA.US` → US/USD) and normalizes to `quote_currency_inferred` instead of `quote_currency_missing`; an unplaceable venue still abstains as `UNKNOWN` |
| `Fetched 3:00 PM` matching neither the fetch nor the close; `degraded = []` beside the price's real markers | the published provenance drops the fetch instant, and only the FINANCIALS canonical's provenance reached the LLM prompt; the UI printed the data vintage under a "FETCHED AT" label in local time | the prompt render carries both canonicals' `provenance` + `reconciliation` with the owner named; `raw_data.provenance` gains `retrieved_at`/`from_cache`/`price_retrieved_at`/`price_from_cache`/`session_as_of`; the UI renders UTC and labels the vintage "DATA AS OF" with the retrieval instant separately |
| `Data Authority · 0` and `Reconciliation: null` while a 37% `total_cash` divergence sat in `warnings` | the FINANCIALS canonical was served from a cache row written before the `reconciliation` field existed (no contract bump, by design), so the extractor's price fallback published a `current_price`-only list as the financials authority; `total_cash` is a compared but NON-key field, so it never became a structured marker | the price record moves to its own `raw_data.price_authority`; `data_authority` is financials-only (`None` = no record); the cache-hit path stamps `authority_record_missing`; `provenance` publishes `metrics_decided`/`metrics_without_record`/`divergence_warnings`; the panel renders an explicit no-record state |
| Catalyst narrative: "2 acquisition-category 8-Ks", "total 6" filings; the 8/17 8-K tagged Acquisition | `summarize_catalyst_outlook` counted NEWS items by category and the prompt injected that count unlabelled; `_sec_8k_to_catalyst` mapped Item 1.01 (material agreement) to `acquisition` | the breakdown is source-split (`news_category_breakdown` vs `sec_8k_category_breakdown`) and the prompt labels each as its source; Item mapping follows the SEC reading (2.01 = acquisition, 5.02 = management, everything else = `other`, never a default `regulatory`) |
| 13G counts not split-adjusted (BlackRock 180.59M at 7.30%); stale 2024 filings; "5.4% coverage" read as fact | the cover-page numbers were published verbatim; nothing modelled a share basis or a filing age, and `period_completeness()` had no production consumer | `share_basis`/`split_factor`/`shares_adjusted` derived from the filing's own shares ÷ pct (integer factor 2..20 ⇒ `pre_split`), `filing_age_days` + `stale` (>400 days, one warning naming the filers), and `institutional_index_partial` so coverage/concentration are labelled as computed over a partial index |
| "trailing 4yr revenue CAGR 40.0%" | the assumption-provenance string labelled the CLAMPED first-year seed growth (`_GROWTH_CAP`) as the trailing CAGR, counting years instead of intervals (the real value is 100.05% over 3 intervals) | the true trailing CAGR is emitted with the interval count and the cap stated explicitly; the LBO seed's sibling string gets the same interval fix |
| Forecast chart reads +96% (TTM × 1.40 plotted after FY2026); EPS/cash-flow windows | the TTM run-rate base row was dropped because its `2026` label collided with the FY2026 bar, and the forecast rows carry calendar labels for a TTM-based projection; the axis then hid neighbouring ticks | the base row is labelled `TTM (Jul 2026)`, the first forecast `2027E (TTM+1)`, and the x-axis renders every tick (`interval={0}`). The EPS/cash-flow truncation did NOT reproduce (both charts reach FY2026 — DOM evidence recorded); the existing lag warning remains the guard |
| TTM EBITDA = operating income + D&A while the FY bar implies a different D&A | history uses the provider's own `ebitda` field, TTM uses the computed caliber — two definitions in one chart | the caliber is labelled and published (`historical_metrics.ebitda_caliber`) instead of silently mixing |
| FY margins in prose vs TTM margins in tiles, neither labelled | the narrative's margins come from the annual XBRL snapshot; the tiles read the TTM income statement | the XBRL facts are labelled `period_basis`/`period_label` in the prompt, the prompt carries a period-labeling rule, and the tiles tag TTM |
| `1 corroborating method(s)`; "perpetual" 10-year growth; beta 2.22 vs 1.81 | a plural template used for one method; the reverse-DCF solve is flat-constant over the horizon, not a perpetuity; the tile shows the provider beta while the DCF uses the Blume-adjusted one | singular-aware blend label; the constant-horizon wording; the tile carries a caliber sub-label and the cross-reference to the adjusted beta |
| Own-multiple cross-check `$493 (+115%)` "CHEAP" off a window opening on the FY2023 EBITDA ramp | only a sample-count guard existed; the band has no structural-break disclosure and the cross-check row could not carry one | an EBITDA structural break (≥3× year-over-year step) is detected on the band, disclosed as `structural_break` + `classification_caveat`, threaded to `CrossCheck.band_break_caveat` (including the path that actually fired on the audited report — the row is re-published from the frozen technical band when the synthesis' own band fetch returns nothing, and that path now carries the caveat too), and rendered beside the badge and the cross-check row. The quantiles are deliberately unchanged — see limits |
| Terminal EV/EBITDA 7.6× buried in a footnote | it was rendered only under the football field | promoted to a DCF assumption cell (`Terminal EV/EBITDA`, `vs X× today`) |
| HOLD verdict beside a directional tactical box (ideal buy above market, 1.4% size, R/R 0.94) | the box gates on `has_anchor_target` only, never on the verdict | the box keeps its numbers and now carries a HOLD reconciliation note |
| "a demanding bar" while the model itself averages 21.5% growth | the prompt injected the market-implied growth but never the model's own average | the prompt now supplies the fade endpoints and the model's own average over the same window, and names the flat-vs-fade distinction |
| Peer analysis blamed "the whitelist" | nothing told the prompt why the peer set was absent | a PEER-SET ABSENCE rule names the failed fetch and forbids blaming the whitelist |
| Reflection AI "advanced talks" scored as an impact-4 acquisition; Vera Rubin "production start" recycled | news impact came from a classifier with no notion of an unverified report, and prompt discipline did not distinguish reported from agreed | prompt rule: a single-source report of talks is REPORTED/early-stage and never "agreed"; a milestone announced before the item's own date is not a new catalyst; every injected event line now carries its source count and published date |
| `$150B buyback (2026-09-28)` absent from the catalyst feed | NOT staleness: the news feed is a same-day ~20-item window and the SEC 8-K index's newest filing is 2026-09-03 — a 12-day-old announcement was structurally invisible | both feeds' coverage windows are published (`news_window`, `sec_8k_window`) with a staleness warning when the 8-K index predates the news window, so the blindness is visible instead of inferred as completeness |
| `2025-10` truncated date; markdown ate `fetched_at`/`from_cache`; clipped tiles | `summary_text` was sliced at 2000 characters mid-token; the markdown tokenizer treated intraword `_…_` as emphasis; the tile row forced five equal columns with `overflow:hidden` beside a fixed gauge | boundary-aware truncation with an explicit marker (headline previews too); an intraword-underscore guard (viewer bundle rebuilt); a wrapping `auto-fit` grid with the gauge row allowed to wrap |

## Stated limits (not defects, not silently dropped)

- **No company-guidance feed.** The reviewer's "the report should say it is deliberately
  ignoring guidance" cannot be satisfied by disclosure of a number the pipeline does not
  fetch: there is no guidance source in the data layer. What IS disclosed now is the rate
  the model actually starts from, the cap applied to it, and the historical actual it was
  seeded against.
- **The own-history band's quantiles are unchanged.** The band is a raw trailing-window
  distribution; the 2023 ramp distorts its p25/p90 and therefore the `CHEAP` badge and the
  `$493` cross-check row. The fix shipped is the caveat the reviewer accepted as an
  alternative ("either caveat it or drop it"). Changing the quantile method (winsorizing,
  or windowing to post-ramp years) would move a published valuation number and stays a
  product decision.
- **13F index completeness is a cache fact, not a modelling one.** When the reverse index
  holds only part of a quarter the coverage percentage and top-5 concentration are labelled
  as partial; they are still computed over the rows on file. Refreshing the index is
  `scripts/refresh_sec_holdings.py`.
- **Source independence is not modelled.** `source_count` after clustering cannot tell two
  independent outlets from two syndications of one report, so no impact cap is applied
  automatically; the narrative is required to describe such an item as a report.
- **`data_fetched_at` keeps its meaning** (the data's vintage). The retrieval instant is
  published beside it rather than redefining a field that the artifact's own `as_of` and the
  semantic diff read.
- **The 52-week range's basis (close vs intraday) is not labelled.** The degraded marker
  `close_only` already flags the close-fallback case; a positive basis label would need the
  provider's intraday flag plumbed to the tile.
