# Report audit remediation — 2026-10-14 GMED full report

An external reviewer audited `art_2026-10-14T16:12:39_GMED_equity_research_c9080e` against
its own arithmetic and ran one sensitivity on its biggest assumption. This document records
what was actually wrong, what changed, and what remains a stated limit or an open design
question. Every root cause below was traced to code (and, where the claim was factual,
against GMED's own SEC filings) before a change was made; nothing here is a re-narration of
the report.

The reviewer's "what checks out" section (net-cash bridge, share count, P/E 19.0×,
EV/EBITDA 10.1×, EV/Revenue 3.1×, 52-week position, Merton distance to default 9.26, the
football-field cross-check, the ±25% band, the sensitivity matrix, the insider-sale sum, and
their independent DCF rebuild landing at $217.86 against the report's $218.12) reproduced
here. So did their headline diagnosis: **the DCF's growth input was wrong**, and it was
wrong in a way the report's own disclosure block already contradicted.

## Shipped fixes

| Reviewer defect | Root cause found in code | Fix |
|---|---|---|
| The DCF opens at 40% growth, taken from a 42.2% trailing 3yr CAGR that the NuVasive acquisition inflated; the report's own block shows FY2025 growth of +16.7% | `seed_dcf_inputs`'s trailing-CAGR branch seeded `max(min(cagr, _GROWTH_CAP), _GROWTH_FLOOR)` and nothing reconciled it against the latest actual: `dcf_current_actuals` — the figure the report's model-vs-current table PRINTS — was display-only and never read back (`dcf_seed.py`, `_STEP_CHANGE_RATIO` did not exist) | a trailing CAGR more than 2× the latest actual YoY growth is a step change inside the window, not a run-rate: the fade now rebases on the current actual and says so in the provenance string ("seeded from the latest actual 16.7% instead … a step change inside the window"). A genuine hyper-grower (100% CAGR on a +65% actual = 1.5×) is untouched, and a flat/negative latest year keeps the old path — see limits |
| TTM EBITDA is $953.68M in the data section but $695.6M on the trajectory chart | the chart's base row was built as `inputs.revenue_base × inputs.ebitda_margin` — the FORECAST's trailing-3yr median margin (22.1%) applied to TTM revenue, in the same chapter whose waterfall card read `income.ebitda` | `dcfResultToRevenueEbitdaData` / `dcfResultToMarginData` take the snapshot's TTM actuals (`TtmActuals`) for the base row; the chapter passes `income.ebitda` / `income.ebitda ÷ income.revenue` / `income.operating_margin`, so the chart, the card and the data section are now the same numbers |
| "Two D&A calibers" does not explain a 37% gap | true — and for this artifact the label was simply FALSE: `historical_metrics.ebitda_caliber` was a frozen constant claiming the annual bars take the provider's EBITDA verbatim while the TTM is EBIT + D&A, whereas GMED's newest annual bar (814,033,000) WAS 537,191,000 + 276,842,000, the same formula | the label is now selected from the series (`ebitda_caliber_label`): same-caliber when the newest bar is EBIT + D&A within 1%, the mixed-caliber warning otherwise (NVDA's ~$14B-vs-$3.7B case still gets it), and the warning when a leg is missing |
| `$953.68M EBITDA − $279.91M D&A` implies a 21.4% operating margin, not the stated 24.8% | `operating_margin` and `gross_margin` in the flat snapshot came from Yahoo's `info.operatingMargins` / `info.grossMargins` scalars while `operating_income`/`ebitda` came from the TTM statement frame: live GMED = 24.755% vs its own 673,764,000 ÷ 3,144,934,000 = 21.424%, and 68.975% vs 68.548% from the frame's own Gross Profit. The scalar also feeds the LLM prompt and the comps EBIT fallback (`multiples.py`) | both ratios are derived from the same TTM frame rows they sit beside (falling back to the scalar only when the frame is absent) |
| `[target withheld] of open-market purchases` should read `$0` | the withheld-point scrubber erased EVERY non-whitelisted prose `$-amount`, and `$0` cannot be a per-share target, so a real datum was destroyed | a zero amount is never redacted (`_reconcile_narrative_targets`), and the docstring states the carve-out |
| The insider-flow caveat looks like a false positive | it was: erasing the `$0` left the clause with the net-flow magnitude as its only amount, so `insider_flow_amount_mismatch` read "-$4,413,467" as a *purchases* figure | fixed by the row above — the same sentence that was correct before the scrubber touched it now survives and passes the relationship check (pinned by a test that runs the reconciled text through the verifier) |
| The 13F "top 5 = 80%" is measured against a 2%-coverage base | the concentration itself is already labelled ("of listed institutional shares") and carries a coverage caveat — but the caveat said it covered "{pct}% of **institutionally-held** shares" while the value is listed ÷ shares **outstanding** (the backend warning says "shares outstanding" correctly) | the caveat's denominator is corrected in both catalogs |

## Verified, not a defect

- **"Net cash and segment operating income are both $483.23M" is a coincidence.** GMED's FY2025
  10-K instance tags `us-gaap:OperatingIncomeLoss` = **483,229,000** on a *segment* context
  (`contextRef="c-287"`), and the SEC-derived net cash (cash 507,745,000 + short-term
  investments 87,397,000 − debt 111,913,000 = **483,229,000**) lands on the same number to the
  dollar; the canonical net cash is 483,230,016, so the two differ by $1,016. The segment path
  (`edgar_provider.extract_segment_facts`) reads only dimensioned XBRL facts — no balance-sheet
  or cash helper can reach it. No change: a genuinely reported segment figure that happens to
  equal a balance-sheet aggregate.
- **The EPS chart does not stop at 2024.** Rendered DOM for the audited artifact shows 2022 /
  2023 / 2024 / 2025 with $1.89 / $1.09 / $0.76 / **$3.98**; the adapter's only filter is
  `eps != null` and `historical_metrics.eps` reaches FY2025. (Same non-reproduction the NVDA
  audit recorded, where the chart reached FY2026.)
- **"FY2025 net income exceeds operating income" is arithmetic on the SEC's numbers, not a
  contradiction.** `NetIncomeLoss` 537,868,000 vs `OperatingIncomeLoss` 479,816,000 (both read
  from the filing and both reproduced in the artifact) with pretax income of 605,068,000 and
  the 10-K's own 11.1% effective rate — interest and other income explain the gap. Worth a
  disclosure line; not a wrong number.
- **The `10.1× vs 21.1× median` cheapness claim does not depend on the buggy $695.6M.** On the
  real TTM EBITDA (953.7M) it is 10.1×; on the SEC's as-reported operating caliber (639.5M +
  D&A) it is ~10.5×. The reviewer's 13.9× was an artifact of the chart defect now fixed.

## Live re-run (cache cleared, every fix in place)

`art_2026-10-14T19:18:07_GMED_equity_research_27c788`, same ticker, same provider chain:

| Number | Before | After |
|---|---|---|
| DCF year-1 growth | 40.0% (42.2% CAGR, capped) | **16.65%** — the FY2025 actual the report publishes as "current" |
| Projected revenue, year 10 | $21.0bn | **$8.0bn** (the reviewer's "~$19bn by year 8 is hard to defend") |
| Point target | withheld (`contract_C7`, single method at 2.9× price) | **published $90.61** (band $67.96–$113.26, confidence medium) |
| Verdict / confidence | BUY at `very_low` on a withheld point | HOLD at `medium` (the verdict is the synthesis' market-implied read, not the DCF) |
| Chart's "TTM (Jun 2026)" EBITDA bar | $695.6M | **$953.7M** — equal to the waterfall card and the data section |
| `income.operating_margin` | 24.755% (Yahoo scalar) | **21.424%** — its own rows |
| `income.gross_margin` | 68.975% (Yahoo scalar) | **68.548%** — the frame's own Gross Profit ÷ revenue |
| `historical_metrics.ebitda_caliber` | "two different D&A calibers" (false here) | "the same operating caliber … directly comparable" |
| Narrative | "[target withheld] of open-market purchases" ×2 + a forged `insider_flow_amount_mismatch` finding | `$0 of open-market purchases` throughout, no such finding |

The reviewer's own sensitivity predicted ≈$91 at 16.7% growth; the rebased DCF lands at
$90.61 — 0.4% apart. The DCF-to-market ratio falls from 2.9× to 1.19×, i.e. back inside the
[0.5×, 2×] single-method band, so the withhold path no longer fires.

Two further defects were found *by running it* and fixed in the same pass:

- the rebased seed's provenance still printed "capped to 40.0% for the first forecast year"
  beside a schedule opening at 16.7% (`_trailing_cagr_label` now suppresses the clamp clause
  on the rebased path);
- the narrative shipped "insiders were net sellers of **$90.61** over the last 90 days" — the
  price target written as the net insider flow. The plural-aggregate verifier cannot see it
  (its noun is "sellers"), and the target reconciler *enforced* it, since $90.61 is the
  canonical target it rewrites drifting amounts to. The net-flow leg is now checked on
  magnitude (`_NET_FLOW_RE` + `ownership_governance.insider_net_flow`) and corrected with a
  disclosed finding like every other flow correction.

## Stated limits and open items (reported, not changed)

- **The single-method BUY is a policy question, not a bug.** The report already withholds the
  point target, explains why in `valuation_synthesis.degradation_note` ("single method dcf $218
  is 2.9x the market price, outside the [0.5x,2x] single-method calibration band"), and leads its
  risks section with it. Whether a lone out-of-band method should still carry a DIRECTIONAL
  verdict (`contract_C7`: "direction taken from the market implied") is the owner's call; the
  rebase above removes this triggering instance, since the DCF now lands inside the band and the
  point target publishes.
- **The EBITDA-margin anchor is unchanged on purpose.** The projection uses a trailing-3yr
  median EBITDA margin (22.1%) against a TTM margin of 30.3% — conservative, and moving it would
  raise every valuation (the opposite of what this audit asks for).
- **Provider caliber divergence on operating income is disclosed, not reconciled.** Yahoo's
  annual "Operating Income" (FY2025 537,191,000) sits ~12% above the SEC's as-reported
  `OperatingIncomeLoss` (479,816,000) because it includes non-operating income; the TTM pair
  diverges ~5% (673,764,000 vs 639,523,000). The `data_authority` record already marks the
  EBITDA caliber `caliber_divergent` / `is_authoritative: false` with its basis string, and both
  operands of every published ratio are now the same provider's. Reconciling to the SEC caliber
  is a data-layer project.
- **The segment block can ship a nameless row with no revenue.** GMED's segment row arrives as
  "Reportable Segment" with `revenue: null` and the warning "segment 'Reportable': no matching
  business-segment revenue member" — the operating income is real, the join to the segment's
  revenue member is not. Disclosed by its own warning; fixing the axis/member join in
  `extract_segment_facts` is a separate task.
- **The net-flow check is magnitude-only.** "Insiders were net sellers of $4.41M" is checked
  against `|insider_net_flow|`; the direction is carried by the words and is NOT verified, so a
  correctly-sized figure with the wrong direction word would pass. The aggregate legs
  ("purchases"/"sales") have the same shape by construction — they compare a printed amount to
  a computed leg.
- **The equity-volatility/beta pairing is unchecked.** 48.5% annualized equity vol beside a 0.96
  provider beta is internally unlikely but both are provider inputs to different models (Merton
  distance to default vs CAPM). A paired plausibility check is a candidate audit finding.
- **The 4.23% equity risk premium is a sourced choice** (published as "Damodaran implied ERP").
  A higher ERP raises the WACC and lowers fair value; with the growth rebase the value now sits
  near market, so the sensitivity matters less than before.
- **Unchanged from the previous audit**: no company-guidance feed; `peer_candidates` has no free
  source (FMP 429s), so the peer leg degrades and the cross-check set is thin; foreign private
  issuers (40-F/6-K filers) get no SEC filings leg.
