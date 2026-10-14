# THC audit remediation (2026-10-14)

External reviewer audit of `art_2026-10-14T16:31:36_THC_equity_research_8d9bfa`
(Tenet Healthcare, `equity_research`, verdict **BUY**, point target `NULL`), forwarded
by the owner with "use pasted text as feedback for the latest THC report".

**Read this first:** the audited artifact was produced *before* commit `d4e9b2b` (the
GMED audit remediation, 19:18 the same day). Two of the reviewer's findings were
already fixed by that commit and one of them the artifact could not possibly show —
they are marked **[stale artifact]** below, and the live re-run is what settles them.

Every claim below was checked against (a) the artifact payload dumped to
`D:/tmp/thc_art.json`, (b) the code that produced it, and (c) the upstream source
(SEC companyfacts / the provider's own frames) where the claim was factual.

## Verdict on the audit

The reviewer's **internal-consistency arithmetic is correct**, and their two headline
diagnoses land: the 2.7x-undervalued BUY rested on a discount rate with no
issuer-specific market evidence, and the report's own cross-check contradicted it.

| # | Reviewer claim | Verified? | Cause | Action |
|---|---|---|---|---|
| 1 | WACC too low: β 0.80 (6.24%) implies a 16x exit vs 7.6x today / 6.2x own median; issuer beta is historically > 1 | **Confirmed** | `market.beta` was `null` for that run, so `dcf_seed._pick_with_provenance` fell back to the Damodaran **industry** levered beta (Hospitals 0.80) — an assumption about the industry, not a measurement of the issuer. The source reports **1.199** (5y monthly) for THC | β basis is now named on the report surface; a missing provider beta is retried before the proxy is used |
| 2 | The report contradicts itself: the only cross-check ($47–$216, mid $184) sits below the $266.91 tape, yet the headline is BUY | **Confirmed** | `_confidence_dial` withheld the point but still returned the ±25% dial band; `resolve_canonical_thesis` then read the direction off the band's **edge** ($549.05 → +105.7% → BUY) and `cross_checks` was read by nothing on the verdict path | A lone method contradicted by the report's own cross-check now holds the verdict **neutral** and the point stays withheld (the band still ships) |
| 3 | The "range" isn't a range: ±20%/±25% of $732.07, so "reads off $549 floor" carries no information | **Confirmed** (the payload itself labels it *"placeholder band, not a real distribution"*) | `_DCF_BAND_WIDTH` / `_DIAL_SINGLE_BAND_FRAC` are constants | The verdict no longer reads off a dial-derived edge when the evidence contradicts the method; the frontend no longer prints a **+174%** per-method upside on a withheld point |
| 3b | — (found while fixing #2: the gate never fired on the live re-run) | **Confirmed** | `fetch_reverse_multiple_band` never passed the run's share count to `compute_bands_via_data_layer`, so the own-history band resolved to **0 samples** — `"shares_outstanding unavailable — historical bands cannot be computed"` — for any name whose provider serves no per-year counts. The technical chapter's *identical* call passes `shares_override` and returns the full 948-sample band, so the same report could display an own-history band whose cross-check the verdict path had **never seen**: it arrived only after the verdict, via `audit.publish_band_cross_check` | The band loaders now share the run's share count, so the own-history band, its reverse-multiple row and its cross-check exist **before** the verdict; the late injector is a backstop, not the source |
| 4 | NCI likely mishandled: 3.17bn (XBRL) vs 2.24bn (provider) is NCI earnings, not a "caliber gap"; NCI deducted at book while FCF includes 100% of those earnings | **Confirmed** | The provider's own frames carry the answer (`Net Income Including Noncontrolling Interests` 3,174 vs `Net Income Common Stockholders` 2,241; a `Minority Interests` row of −933) but the divergence warning called the gap "concept / window / filing rounding" and never named NCI; `StockholdersEquity` 4,658 = 30,676 − 21,976 − 4,042 (NCI) | The warning now names the noncontrolling-interest scope, the amount and the consolidated-vs-parent basis — the NCI share is plumbed through the canonical contract so the call site can name the cause instead of guessing; the book-NCI deduction is cross-checked against the balance-sheet identity and disclosed (see *Not changed*) |
| 5 | Everything unreconciled: no authority record, 10-K text returned 0 chars, `filing.text()` crashed, footer still says "Source: 10-K filings" | **Partly stale** | **10-K extraction is fixed at HEAD** — a live probe returns `quality: ok` with Item 1 74,784 / Item 1A 70,099 / Item 7 151,233 chars (the artifact's warning string exists nowhere in the repo). The missing authority record is real: the disclosure was wired only to the canonical-cache path | Authority-record-missing now discloses on the raw-cache path too, so a run whose payload carries no reconciliation record cannot ship `data_authority: null` silently |
| 6 | Insider total doesn't tie: visible Form 4 sales ≈ $40.1M vs the report's −$49.99M | **Not a defect** | All 19 sale rows sum to exactly **$49,991,273.96** = `insider_sell_value`; the reviewer summed the UI's capped 12-row table ($40,489,121.18) | The table now says how many of how many rows it shows |
| s1 | Gross-margin card 41.7% vs the chart's ~82% | **[stale artifact]** | `info.grossMargins` scalar vs the statement frame (18,752 / 22,638 = 82.8%) — the GMED commit re-derives the ratio from the frame | Margins now carry an explicit basis (`row` vs `provider_scalar`); the scalar fallback fires only when the frame lacks the row, and it warns |
| s2 | `operating_income` null yet an 18.2% operating margin shown | **[stale artifact]** | Same family: `info.operatingMargins` with no published numerator | An operating margin is **never** published without the frame's own Operating Income row (withheld, basis `withheld_no_operating_income_row`, warned) — THC's 41.7%/18.2% scalars beside an unreported `operating_income` can no longer ship |
| s3 | XBRL `NetIncomeLoss:annual` pulled a stale 2010 fact | **Confirmed** | `_select_latest_fact` took a single `get_annual_fact` result, whose edgartools key is `(filing_date, period_end)` — filing date FIRST — so a late-filed FY2010 fact outranked FY2025 | Selection now gathers every fact for the concept and ranks by **`(period_end, filing_date)`**; the getter path survives only as the multi-fact-API fallback, and the stale annotation stays |
| s4 | "30-day window" news lists Feb–Apr 2026 items | **Confirmed** | `filter_fresh_news(30d)` is applied to news only; SEC 8-K catalysts are merged into the same event list unfiltered | `filter_fresh_sec_8k_catalysts` age-gates the 8-K events (dated older than the window, or undated = not provably fresh) at the last transform before the artifact event list; news events are untouched |
| s5 | Shares outstanding "implied" from market cap ÷ price (circular) | **Confirmed (the circularity, not the number)** | The published 80,519,000 matches the provider's `sharesOutstanding` exactly — but `extractor` computed `market_cap = shares × price`, making the two mutually derived, so any later share-count check was a tautology | `market_cap` is now the provider's reported cap (the shares×price derivation survives only as a labelled fallback). The share COUNT keeps its price-consistent rule — a live probe shows the source still reports single-CLASS counts for multi-class issuers (GOOG 5.527bn vs 12.230bn = 54.8%, META 13.4%, FOX 47.8%; BP and THC tie exactly), and the numerator is total equity value — but the divergence is now disclosed in a warning instead of being swapped silently |
| s6 | Preferred-stock caveat likely immaterial | **Confirmed, disclosed** | The artifact already carries a `review`-severity numeric-audit finding for `ev_bridge_unverified` | No change (already disclosed) |
| s7 | Monte Carlo is centred on the DCF, so "0th percentile" is circular | **Confirmed, disclosed** | `assumptions_used.centered_on = "base-case DCF assumptions"`, `independent: false`; the report prints the caveat verbatim | No change (the reviewer accepts the admission). The percentage is rendered rounded, so 0.2% prints as "0th" — cosmetic, left alone |
| s8 | `-$11.078B` flagged "unsupported" is a false positive (13.25 − 2.17 = 11.08) | **Confirmed** | `report_drift` classified the token as an *orphan* (the redaction set) because the signed value (−11.078bn) matched no leaf; its **magnitude** matches `net_debt` = 11,078,000,128 exactly, and the prose is expressing a subtraction | Orphan now means "near nothing the artifact computed" on either the signed or the magnitude reading — a sign convention is surfaced for review, never redacted |

## What changed

**Valuation policy (`valuation_synthesis.py`, `valuation_aggregator.py`, `equity_research.py`)**

- `cross_check_contradicts_method(methods, cross_checks, current_price)` — the new
  single reading of "the report's own triangulation points the other way". A
  cross-check band that brackets the market price claims no side; one corroborating
  check vetoes the whole reading (the direction then stands on an agreeing number).
- `_confidence_dial` calls it, so the withhold decision is still made in ONE place
  (the dial) and a lone contradicted method withholds the point even when its mid is
  inside the [0.5x, 2x] calibration band.
- `resolve_canonical_thesis` holds the verdict **HOLD** in that state and never reads
  a direction off the ±25% dial edge. HOLD is a judgment about the evidence, not a
  refusal to rate: the band, the method breakdown and the disagreement all publish.
- The out-of-band withhold note no longer claims the direction is "taken from the
  market implied" (it was, in fact, the band edge) — the note now says what the code
  does.
- `_dcf_assumptions` names the beta basis on the report row when the shipped beta is
  a sector proxy ("β0.80 (industry levered beta proxy — no issuer market beta)"), so
  the input a DCF answer is most sensitive to is the one the reader can argue with.
- The withheld-path narrative scrubber no longer censors the report's own published
  data: the insider-flow aggregates are whitelisted (THC's narrative read "insiders
  were net sellers of **[target withheld]** … with **[target withheld]** of
  open-market purchases" while the risk bullets on the same page quoted
  $49,991,274 and $10,223,358). The token is for a smuggled POINT target; a datum
  the artifact publishes is a citation.

**Report-surface honesty (frontend, `desktop/src/**`)**

- The football field no longer computes/prints a per-method upside when
  `valuation_withheld` — the lone DCF's **+174%** (the number the reviewer read as
  the headline claim) is gone; a footnote states per-method ranges are reference
  values when the point is withheld.
- The NEUTRAL sniper note is cause-aware: post-acquisition transition → transition
  copy; one method → "a single valuation method ran with no second method to
  corroborate it"; otherwise the divergence copy. It previously asserted
  "methods do not corroborate (DCF vs comps diverge)" **unconditionally** whenever
  the point was withheld, including on reports where no comps ran at all.
- The insider table labels itself as a capped subset ("showing the 12 most recent of
  20 … the flow summary above aggregates all 20"), so its total can no longer be
  mis-summed against the card.

**Drift classification (`report_drift.py`)** — orphan (the only redaction bucket)
now requires "near nothing" on both the signed and the magnitude reading.

**Own-history band reachability (`historical_loaders`, `equity_research`)**

- `fetch_reverse_multiple_band` now forwards the run's own share count
  (`shares_override`) to `compute_bands_via_data_layer`, and both pipeline call
  sites pass it. Without it the band resolved to **0 samples** and the EV/EBITDA
  reverse-multiple row *and* the own-history cross-check vanished from the
  synthesis, while the report still displayed the band — back-filled after the
  verdict by `audit.publish_band_cross_check`. That is how a verdict could be
  contradicted by a number printed on its own page; both band paths now read the
  same band, and the late injector is a backstop rather than the only source.

**Fundamentals and filings provenance**

- **XBRL fact selection** (`edgar_provider`): `_select_latest_fact` gathers every fact
  for a concept and ranks by **`(period_end, filing_date)`** — the period first, the
  filing date only as a same-period tie-break — so a late-filed fiscal-year fact with
  an old period cannot shadow the newest one (that is how THC's "latest annual net
  income" came out as FY2010). The single-getter path survives only as the fallback
  when the multi-fact API is unavailable.
- **The net-income divergence names NCI** (contract → normalize → extractor →
  pipeline): the provider's TTM NCI earnings share (`Net Income Including NCI` −
  `Net Income Common Stockholders`, else −`Minority Interests`) now reaches
  `income.nci_earnings`, so a gap that matches it is explained as a consolidation
  caliber difference (consolidated incl. NCI vs attributable to the parent) and an
  unexplained gap keeps the conservative wording.
- **Market cap is the provider's** (`extractor`): `shares × price` is no longer the
  published cap, so the two are not mutually derived; the derivation survives only as
  a labelled fallback. The share COUNT keeps its price-consistent rule — a live probe
  shows the source still reports single-CLASS counts for multi-class issuers (GOOG
  5.527bn vs cap/price 12.230bn = 54.8%, META 13.4%, FOX 47.8%; BP and THC tie
  exactly) while the numerator is total equity value — but the divergence is now
  disclosed in a warning instead of being swapped in silently.
- **Authority-record disclosure** (`layer`): a raw-cache payload carrying no
  reconciliation record now gets `DEGRADED_AUTHORITY_RECORD_MISSING` on the normalized
  provenance, exactly as the canonical-deserialize path does.
- **SEC 8-K age gate** (`catalyst`): the 8-K catalysts merged into the artifact event
  list are filtered to the same window the news uses (an undated 8-K is not provably
  fresh); news events are untouched.
- **Margin basis** (`yfinance_provider`): gross/operating margins record whether they
  came from the statement row or a provider scalar; the scalar fallback warns, and an
  operating margin is withheld outright when the frame has no Operating Income row.
- **Missing provider beta** (`yfinance_provider`): the `.info` read is retried once
  before the beta is left None, so a transient partial payload cannot silently hand
  the DCF a sector-proxy discount rate.
- **Equity identity in the XBRL snapshot**: with Assets, Liabilities and parent
  `StockholdersEquity` all present, the snapshot publishes the identity
  (`total_equity = A − L`, `noncontrolling_interest = total − parent`) and states that
  `StockholdersEquity` is parent-only — so the model can no longer render NCI away as
  "assets minus liabilities leaves $4.658B".

## Verification

- **Unit (new)**: `cross_check_contradicts_method` cases (other side / bracketing /
  corroborating / mixed / multi-method), the THC shape end-to-end (withheld + HOLD),
  and the two regressions that must NOT change (no cross-check ⇒ the edge read still
  ships; in-band + corroborating ⇒ the point still publishes); the narrative
  whitelist (insider figures survive the withheld scrub, a fabricated per-share
  target is still erased); `report_drift` magnitude classification; the band
  loader's share forwarding; the SEC 8-K age gate and its exclusion disclosure; the
  NCI-named divergence; the XBRL period ranking; the provider-cap share rule; the
  margin basis + withheld operating margin.
- **Gates**: backend `ruff@0.15.8 format --check` + `check` clean (587 files),
  `mypy finrobot` clean (246 files), `pytest tests/unit tests/audit tests/artifact
  tests/routes` → **5349 passed, 8 failed, 12 skipped**; the 8 are the pre-existing
  failures (3× `test_paths` home isolation, 2× `test_routes_settings` Windows file
  mode, `test_sdk::test_init_empty_default_model_fails_fast`, 2×
  `tests/audit/test_architecture` standing `probe.py`/`env.py` hits). Frontend:
  `tsc -b` clean, **1014 tests passed**, prettier clean, `lingui:compile` +
  `i18n:check` (972 active keys, no orphans), viewer bundle rebuilt.
- **Live, cache cleared, twice** — the first run is what exposed 3b:
  1. `art_…20:27:40…99cdca`: with the corrected β the lone DCF sat **1.995x** the
     tape — a hair inside the 2x calibration band — so the point PUBLISHED at
     **$541.80 (+99.5%)** while the report's cross-check ($70.16–$255.26) sat
     entirely below the price. The gate never fired because the cross-check arrived
     *after* the verdict (3b).
  2. `art_…20:37:52…bab351` (final): **HOLD, point withheld**; methods DCF $541.80
     (β1.13, WACC 7.45%) + EV/EBITDA $212.91 (the revived reverse-multiple row);
     published band $212.91–$541.80 **spans** the $271.60 tape → "FAIRLY VALUED …
     the methods do not support a one-sided call — verdict HOLD".
- **Payload rows on the final artifact**: WACC 7.45% on a provider-sourced β1.13
  (1.199, Blume-adjusted); NCI named in **both** net-income warnings ($933M, "not a
  typo"); gross/operating margin 82.83%/19.52% with operating income $4.418bn
  (were 41.7% / 18.2% with `operating_income: null`); XBRL annual net income
  2.367bn **@2025-12-31** (was 1.119bn @2010-12-31); equity identity published;
  provider market cap 21,868,961,792; authority record present; 10-K Items 1/1A/7 =
  74,784/70,099/151,233 chars; 8-K exclusion note present; **0** drift findings;
  insider sell = net = $49,991,273.96 across 20 rows.
- **DOM** (report page for the final artifact): cover reads "THC $271.60 · Fair
  value $212.91–$541.80 within range · HOLD · Fairly Valued"; the football field
  renders the withheld footnote ("Point target withheld — per-method upside is not
  published …") and **no** +174%; the insider table reads "Showing the 12 most recent
  of 20 filings in the window — the flow summary above aggregates all 20"; no
  `[target withheld]` token anywhere; the prose keeps $49,991,274 / $10,223,358.

**Observation, not fixed here:** the second live run's *news* feed came back empty
(`news_window.count = 0` vs 50 in the first, both with a cleared cache) — a live-feed
variance on a path this change does not touch. Worth a separate look if it recurs:
undated news items are the one shape `filter_fresh_news` cannot prove fresh.

## Not changed, deliberately

- **NCI valuation basis.** The bridge deducts the provider's book NCI
  ($4,042,000,000) while the DCF discounts 100% of the consolidated cash flows — the
  reviewer is right that this under-deducts relative to capitalizing NCI earnings
  (~$933M TTM ≈ $65/share at 10x). There is no market price for those minority
  stakes in any source we carry, so "value NCI at market" is not implementable here;
  re-modelling it to book-vs-earnings silently would move the target by ~13% on an
  assumption nobody sourced. The scope is now named in the divergence warning with
  the amount and the consolidated-vs-parent basis, the book figure is cross-checked
  against the balance-sheet identity published in the XBRL snapshot, and the basis is
  disclosed.
- **The dial band itself** (±25% single-method, ±20% per method). It stays as the
  disclosed band rather than being replaced by the Monte Carlo percentiles: that
  distribution is *centred on the base case* (`independent: false`) and its WACC
  σ (1pp) never reaches the market-implied rate, so using it would publish a wider
  band around the same biased mid. What was wrong — the verdict reading a direction
  off that band's edge — is fixed.
- **A terminal-exit-multiple sanity gate.** The model's implied 16x exit against the
  issuer's own 6.2x median is real evidence, but turning it into a threshold gate
  would be inventing a calibration constant; the contradiction gate already uses the
  same evidence through a published figure.
- **The "0th percentile" rounding** (0.2% → "0th") on a distribution the report
  already labels as not-independent evidence.
