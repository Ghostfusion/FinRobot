# Report Invariant Closure — Design

Status: **proposed**. Nothing in this document is implemented. §9 lists the decisions the
owner has to make before any of it ships; §4 is a rule inventory with pinned instances, not a
change log.

Scope: the output-contract gate (`finrobot/artifact/contract.py`), the numeric-audit rule set
(`engine/compute/operators/audit/`), and the payload shapes they read. Phase 2 (§6) touches
`engine/data/` and the `compute/` leaf layer.

> **Security.** This document names env vars, payload paths and public source URLs only. No
> credential value, and `.env` is never committed (root `.gitignore` covers it).

---

## 1. Why this document exists

Two external audits (GMED `d4e9b2b`, THC `4e1a75f`) found ~20 confirmed defects, each traced to
code and to the upstream source. They were not 20 independent slips: they fall into **six
classes** (§1.2), and every class is a *relationship between fields* — precisely what the test
suite cannot see. At both HEADs the tree was green: 5,350 backend tests, 1,014 frontend tests,
ruff, mypy strict.

The pipeline is not without a gate. It has one, it is well designed, and **it has never once
blocked a field.** Measured over `~/.finrobot/artifacts.db`, 2026-10-14 (104 stored artifacts,
all types):

| Measurement | Value |
|---|---|
| artifacts with ≥1 numeric-audit finding | 90 of 104 |
| findings emitted, by severity | `review` **171**, `blocked_field` **0** |
| payloads that contain the string `blocked_field` anywhere | **0** |
| contract clauses that have ever fired in the corpus | `C1` ×2, `C7` ×31 |
| equity_research artifacts carrying the single-method "no cross-validation" note | 59 |
| `withhold_valuation=True` reached via `blocked_field` | 0 (every withhold came from the synthesis' own rule or `C7`) |
| **artifacts that published a BUY/SELL whose own published cross-check band sits entirely against the call** | **8** (HMY ×3, NFLX, SKM, THC ×2, UTHR) |
| findings named `insider_flow_amount_corrected` — the narrative wrote another metric's number into the insider-flow sentence and the pipeline silently repaired it afterwards | **21** |
| findings named `target_multiple_outside_band` — the published target sat outside the issuer's own multiple range | **23** |

The contradicted-verdict row is the architecture's problem in one number. It is not one bad
report; it is a recurring shape the gate is structurally unable to see, because **no clause
compares the verdict direction to the cross-checks the same payload prints.**

### 1.1 Three pinned instances

All three are real stored artifacts; every number below was read from the payload.

**A — `art_2026-10-14T16:31:36_THC_equity_research_8d9bfa`** (audited; BUY)
`valuation_synthesis.valuation_withheld = true`, `thesis.recommendation = "BUY"`,
`target_low/high = 549.05/915.09` (= ±25% of the lone DCF mid $732.07),
`current_price = 266.91`, `cross_checks[0] = 47.48 … 216.31` — **entirely below the tape and
below the published band**. `thesis.price_target_basis` says so out loud: *"The BUY verdict
reads off the nearest published range bound ($549.05), not the withheld interior point"*.
`withheld_reason = "contract_C7"` (the resurrection scrub — the only clause that fired).
`inputs.raw_data.market.beta = null` while `financial_modeling.inputs.beta = 0.7997` with
`assumption_provenance.beta = "0.80 (Hospitals/Healthcare Facilities industry levered beta)"`.
`income.operating_margin = 0.18159` while `income.operating_income = null` and
`income.gross_margin = 0.41661` (the chart beside it drew 82.8%). One finding, `review`.

**B — `art_2026-10-14T20:27:40_THC_equity_research_99cdca`** (the run *after* the β fix; BUY,
target **published**) — the sharpest one, because it is a post-fix artifact:
`valuation_withheld = null`, `withheld_reason = null`, target $541.80 published,
band $406.35–$677.25, `current_price = 271.60`, and `cross_checks[0] = 70.16 … 255.26` in the
same object. `degradation_note` = *"single method dcf with no cross-validation — band widened,
confidence medium"* — **the report asserts it had no cross-validation while printing one**,
because the note keys on *methods* and never looks at *cross-checks*. `target/entry = 541.80 /
271.60 = 1.995`, a hair inside the single-method `C1` band `[0.5x, 2x]`, so `C1` passed. The
numeric audit *did* catch it — `target_multiple_outside_band`: *"the $541.80 target implies 11.1x
TTM EBITDA **vs the issuer's own 5-year p90 of 7.4x** — the target sits above its own historical
multiple range"* — at severity **`review`**, i.e. a banner. Nothing withheld.

That same artifact carries a third finding, and it is the mutation class in the flesh:
`insider_flow_amount_corrected` — *"the narrative stated $541.80 as the net flow figure; the
published text was corrected to the computed value $49,991,274 (the printed amount belonged to
another metric)"*. The prose was **written wrongly**, the target leaked into the insider-flow
sentence, and the pipeline silently repaired it afterwards and reported the repair as a note.
That check fired **21 times** across the corpus.

**C — `art_2026-10-14T20:37:52_THC_equity_research_bab351`** (final; HOLD) — the shape the gate
should enforce: two methods (DCF $541.80, EV/EBITDA $212.91), band $212.91–$541.80 **spanning**
the $271.60 tape, `thesis.price_target_basis = "FAIRLY VALUED … verdict HOLD"`, 0 drift
findings, `withheld_reason = "contract_C7"`, one `review` finding.

GMED's pair for the same table: `…16:12:39_…c9080e` (DCF opened at 40% growth from an
acquisition-inflated CAGR; chart TTM EBITDA $695.6M against the card's $953.7M;
`income.operating_margin` 24.755% beside its own rows' 21.424%; narrative
"`[target withheld]` of open-market purchases" where the datum was `$0`) and
`…19:18:07_…27c788` (16.65% growth, $90.61 target published, margins 21.424%/68.548%).

### 1.2 The six classes and what they mean

| Class | Instances across both audits | Established classification |
|---|---|---|
| **Duplication** — one quantity, several definitions | chart EBITDA = forecast margin × TTM revenue; 13F coverage denominator in the frontend catalogue vs the backend warning; the band computed at three call sites with different arguments (`shares_override` forwarded in the technical chapter, not on the report path → **0 samples**); `valuation_synthesis.valuation_withheld` **and** `structured.valuation_withheld` written by hand | Rajalingham/Chadwick/Knight, *Duplication*: *"a variable defined twice… during debugging the two growth rates might be identical; during use they might differ"* — [eusprig.org §5](https://eusprig.org/wp-content/uploads/0805.4224.pdf) |
| **Omission** — a leg exists but is not wired into the decision | `cross_checks` read by nothing on the verdict path; `nci_earnings` not plumbed, so the income gap was guessed as "concept / window / filing rounding"; the authority record disclosed on one cache path only; GMED's `assumption_current_actuals` (the number the report *prints*) never read back by the seed | same taxonomy, *Omission*: *"especially dangerous, because they have low detection rates"* |
| **Substitution without a type change** — an assumption published as a measurement | β `null` → industry levered proxy 0.80 (source reports 1.199); the ±25% placeholder band consumed as a distribution; provider margin scalars standing in for frame ratios (24.755% vs 21.424%); `market_cap = shares × price` in the audited artifact (21,491,326,290 ÷ 266.91 = 80,519,000.6, exactly the published share count) | Panko, [hard-coding input values into formulas](https://arxiv.org/abs/0803.0169); *Reasoning* error in the taxonomy; abstention-as-an-output in the [reject-option literature](https://dl.acm.org/doi/10.1007/S10994-024-06534-X) |
| **Staleness / unowned selection** | XBRL annual net income resolved to **FY2010** (edgartools ranks by `(filing_date, period_end)`, filing date first — nobody chose that); 8-K catalysts merged into a "30-day news" window whose filter covers news only; a trailing-3yr CAGR window spanning an acquisition | taxonomy, *Temporal*: *"referencing a piece of data that has become invalid due to time lapse"* ≈ [DQC_0005](https://xbrl.us/home/priorities/data-quality/rules-guidance/) |
| **Descriptions not derived from the data they describe** | `historical_metrics.ebitda_caliber` was a frozen constant claiming a D&A-caliber difference; a provenance string printed "capped to 40.0%" beside a 16.7% schedule; the note claiming direction was "taken from the market implied" when it was read off a dial edge; `degradation_note` claiming "no cross-validation" beside a cross-check (instance B) | taxonomy, *Semantic/structural*: *"documented assumptions are not reflected in the model, causing confusion"* |
| **Circular lineage and mutation-with-authority** | `market_cap = shares × price` makes every later share-count check a tautology; Monte Carlo centred on the DCF it validates ("0th percentile"); the target reconciler *wrote* the price target into the insider-flow sentence; the withheld scrubber deleted `$0` and the verifier then read the mutated text and forged a finding | taxonomy, *Logic → circular reference*: *"the formula uses its own value in its calculation"* |

KPMG's classic review found ≥5 errors in 95% of financial models reviewed (cited in the
taxonomy paper above). Finding ~20 in two reports is normal density. **The deliverable is the
detection architecture, not more care.**

---

## 2. The gate already exists — do not rebuild it

`finrobot/artifact/contract.py` is exactly the artifact this problem needs, and its own
docstring states the design contract:

> *"Every upstream gate sees a fragment: the data-health gate sees a `ValuationSynthesis`, the
> numeric audit sees a `FinancialData` snapshot, the narrative reconcile sees one prose field.
> None of them ever sees the assembled artifact … this contract runs in the gap and asserts
> whole-artifact invariants the fragment gates are structurally blind to."*

| Piece | Where | What it gives us |
|---|---|---|
| `ContractClause(id, severity: "H"｜"S", check: Callable[[Artifact], Finding｜None], surface: bool)` | `artifact/contract.py` | the rule shape: pure, zero I/O, never re-runs the computation, no bare threshold literal |
| `CONTRACT_CLAUSES = [C1 H, C1b H, C2 H, C3 H, C4 H, C6 S, C7 H (surface=False)]` | same | the clause inventory and the two withhold scopes |
| `enforce_artifact_contract(artifact)` | called at `engine/pipelines/runner.py:807` — the single persist boundary | the insertion point; runs after every builder, before `store.save` |
| `Finding(field_key, check, severity, evidence)` + `rollup_status` + `Severity = info｜review｜blocked_field` | `engine/models/numeric_claim.py` | one immutable finding model shared by both gates; worst-severity rollup |
| `_attach_numeric_audit(...)` | `artifact/builders.py:332` | the single sink every builder routes through; attaches `structured.numeric_audit`, sets `artifact_status`, and on `withhold_valuation` runs `rich_withhold` |
| 10 pure verifiers (`sector_sign`, `currency_caliber`, `ev_bridge`, `ttm_period`, `metric_authority`, `insider_flow`, `claim_anchor`, `narrative_divergence`, `narrative_numeric_grounding`, `valuation_band`) | `engine/compute/operators/audit/` | the existing rule pack, already producing findings against real payloads |
| `scripts/scan_artifact_contract.py` | `finrobot_desktop/scripts/` | a read-only conformance scanner over the whole store — the rollout instrument (§7) |
| `field_registry.FieldCaliber` (unit, currency, `period`, `currency_source`) | `artifact/field_registry.py` | the static half of a measurement ledger; `period` already drives a comparability gate |
| `inputs.raw_data.data_authority.decisions[]` (`status`, `basis`, `comparability`, `agreement_is_independent`, `reason_code`, `candidates[].{eligible, deviation_pct}`) | payload | the runtime half — the data layer already answers "is this a measurement, and from whom?" |

**Doctrine that must be preserved** (quoted from the two module docstrings, not invented here):

1. *"corrupt / out-of-band data withholds the price, never the judgment; there is no 'REVIEW'
   refuse-to-rate state any more"* — a clause withholds a **value**, never flips a verdict.
2. *"It never raises (an exception would blank the whole run)"* — a violation degrades.
3. *"the gate stays dumb … zero I/O, never imports `compute/` / `data/` / `pipelines/`"* — rules
   read the assembled payload; they never re-derive it.
4. *"holds no bare threshold literal (the bands are imported calibrated constants from the
   leaf)"* — `engine/models/valuation_thresholds.py`.
5. `blocked_field` on a leaf → withhold **that leaf**; `H` on the contract → withhold the
   headline target. Two scopes, both existing.

---

## 3. Gap analysis — clause by clause

| Rule class | Owner today | Coverage measured | The gap | Proposed |
|---|---|---|---|---|
| headline vs market | `C1` | fired ×2 | blind to a target inside `[0.5x, 2x]` while a published cross-check says otherwise (instance B: 1.995×) | extend via `C8` |
| method vs method | `C1b` | never fired | — (correct as-is) | keep |
| malformed amount in prose | `C2` | never fired | — | keep |
| basis matches headline | `C3` | never fired | — | keep |
| currency caliber | `C4` | never fired | — | keep |
| single-method disclosure | `C6` (S) | note in 59 artifacts | the note is derived from **method count only**, so it asserts "no cross-validation" while a cross-check is printed (instance B) | fix `C6` derivation — §4.8 |
| resurrection scrub | `C7` (H, internal) | fired ×31 | working as designed | keep |
| **verdict vs its own published cross-checks** | *nobody* | **8 artifacts shipped a contradicted BUY/SELL** | no clause reads `cross_checks` against the direction | **`C8`** |
| **cross-check band plausibility** | *nobody* | SKM published a cross-check band of **−$2.97 … −$1.23** against a $34.42 price; HMY $1.22–$3.74 against $16.71 | a band that is negative or degenerate is published as if it were evidence | **`C9`** |
| **conclusion-ratio operands (source / caliber / period) and numerator presence** | numeric audit on `FinancialData` only (`ev_bridge`, `ttm_period`, `currency_caliber`) | `ev_bridge_unverified` ×106 (review) | ratios whose operands come from **different providers** or whose numerator is `null` (THC `operating_margin = 0.18159` beside `operating_income = null`); the balance-sheet identity A = L + E (DQC_0004) is hand-written in one operator, not a clause | **`C10`** |
| **single definition** | *nobody* | `valuation_withheld` duplicated across two slots; band computed at 3 call sites; catalogue copy vs backend warning | two definitions of one quantity drift with nothing to catch it | **`C11`** |
| **recency and window closure** | `ttm_period` audits the TTM period only | FY2010 fact; 8-K inside a 30-day window | selection policy is a library default; a merged event list is filtered per source, not per predicate | **`C12`** |
| **independence / non-circularity** | `agreement_is_independent` exists in `data_authority`; `band_break_caveat` exists and is `null` everywhere observed | no consumer | MC centred on its own base case; `market_cap` derived from `shares × price` | **`C13`** |
| **prose direction grounding** (not just malformed amounts) | `C2`, `report_drift`, `narrative_numeric_grounding` (a digit must exist) | drift found 1 orphan in the audited THC artifact; `insider_flow_amount_corrected` ×21 (a repair, at `review`) | "insiders were net **sellers** of $X" is checked on magnitude and on the noun, never on the direction word; the reconciler may *insert* the target — and did, 21 times | **`C14`** |

---

## 4. Rule inventory (proposed)

Every clause follows the existing signature and lives in `CONTRACT_CLAUSES`. `reads` names the
exact payload paths (verified against stored artifacts, not guessed). IDs `C8+` are free —
`C5` is skipped in the live inventory.

### 4.1 `C8` — the verdict may not contradict its own published cross-checks
- **severity** `H` (headline scope: withhold the target, keep the verdict; the synthesis' own
  contradiction rule then publishes HOLD from the compute side, so the two agree).
- **reads** `outputs.structured.thesis.recommendation`,
  `outputs.structured.valuation_synthesis.{current_price, cross_checks[].{low,mid,high,name,label}}`,
  `outputs.structured.valuation_synthesis.methods[]`.
- **predicate** for `BUY`: no cross-check whose band contains `current_price`, **or** whose
  `mid > current_price`. For `SELL`: the mirror. A band that **brackets** the price claims no
  side; one corroborating check pointing the same way vetoes the violation (≥2 checks must agree
  to contradict). Ignore a cross-check that `C9` has already flagged unusable.
- **why it cannot be fooled** it reads the numbers the reader reads, in the same object, after
  the narrative is written.
- **pinned instance** B (cross-check $70.16–$255.26 vs $271.60 tape, BUY at $541.80) and the 8
  corpus artifacts (HMY ×3, NFLX, SKM, THC ×2, UTHR).
- **emit** `[CONTRACT/C8]` + `valuation_withheld` + the withheld narrative stamp.

### 4.2 `C9` — a cross-check that is not evidence must not be published as evidence
- **severity** `H`, **claim scope** (withhold the cross-check entries; do not withhold the
  target on this clause alone).
- **reads** `outputs.structured.valuation_synthesis.cross_checks[]`,
  `outputs.structured.technical_analysis.historical_bands.{sample_count, p25, median, p75, current, warnings}`,
  `inputs.raw_data.market.current_price`.
- **predicate** a fundamental band for a positive-price equity must have `low > 0`,
  `high > low`, a monotone `low ≤ mid ≤ high`, and a stated sample count > 0. A failing band is
  dropped and reported (the payload already carries the field `band_break_caveat`, `null`
  everywhere observed — this clause is what should populate it).
- **pinned instance** `art_2026-10-14T16:44:09_SKM_equity_research_2e8161`: cross-check
  **−2.97 … −1.23** against a $34.42 price; `…16:38:42_HMY_…` 1.22 … 3.74 against $16.71.

### 4.3 `C10` — conclusion ratios: same-source operands, and a numerator must exist
- **severity** `H`, **claim scope** (withhold the ratio leaves; promote the `FinancialData`
  finding to `blocked_field`).
- **reads** `inputs.raw_data.income.{gross_margin, operating_margin, operating_income, revenue, ebitda, net_income, nci_earnings}`,
  the same leaves inside `inputs.raw_data.data_authority.decisions[].{metric, selected_source, status, period_end, comparability}`,
  `inputs.raw_data.balance.noncontrolling_interest`, `inputs.raw_data.valuation.{ev_ebitda, ev_ebitda_reported}`.
- **predicate** (a) a published ratio must have both operands present and sourced from the same
  `selected_source` and period — otherwise the ratio is withheld with `basis="caliber_mismatch"`
  (the THC fixes already emit `withheld_no_operating_income_row`; this makes it a gate instead of
  a code path); (b) `Assets = Liabilities + Equity` and `Equity_total − NCI = Equity_parent`
  (DQC_0004 shape — currently hand-written as `_equity_identity_note`).
- **pinned instance** instance A (`operating_margin` 0.18159 with `operating_income: null`;
  `gross_margin` 0.41661 vs the frame's 82.8%); GMED (24.755% vs 21.424%).

### 4.4 `C11` — one quantity, one definition
- **severity** `H`, claim scope.
- **reads** the mirrored slots (`outputs.structured.valuation_withheld` vs
  `outputs.structured.valuation_synthesis.valuation_withheld`; `…target_low/high` vs
  `…methods[].low/high`; `inputs.raw_data.market.shares_outstanding` vs
  `…financial_modeling.inputs.shares_outstanding` vs `assumptions.parameters.shares_outstanding`)
  and, in the frontend, any client-side arithmetic on `valuation.*`.
- **predicate** mirrored slots must be equal, or one of them must be absent. Divergence is a
  finding; the duplicate is removed in favour of a single writer.
- **pinned instance** the three `shares_outstanding` slots in every THC artifact; the two
  `valuation_withheld` slots; the +174% the frontend computed from a withheld point.

### 4.5 `C12` — recency and window closure
- **severity** `H` when the stale fact feeds a published number, `S` otherwise.
- **reads** `outputs.structured.historical_metrics.*` against
  `outputs.structured.financial_modeling.inputs.ttm_period_end` and
  `inputs.raw_data.market.quote_as_of`; `outputs.structured.thesis.catalysts[]` and the raw
  event list against the stated window.
- **predicate** every dated series entry must sit inside the period the label claims; an
  undated item is not provably fresh; a merged event list is filtered **after** the merge, not
  per source.
- **pinned instance** the **FY2010** XBRL net income in the audited THC artifact; Feb–Apr 8-Ks
  inside a "30-day window".

### 4.6 `C13` — independence and non-circularity
- **severity** `S` (with one hard case: a validator whose operands are a subset of the
  validated quantity's derivation may not be the **sole** corroboration for a direction).
- **reads** `inputs.raw_data.data_authority.decisions[].{agreement_is_independent, candidates[]}`,
  `inputs.raw_data.market.market_cap` vs `{shares_outstanding, current_price}`,
  `outputs.structured.technical_analysis.monte_carlo.assumptions_used.{centered_on, independent}`.
- **predicate** `market_cap` must not equal `shares × price` unless labelled as a derived
  fallback; a Monte Carlo whose `centered_on` is the same base case it validates must publish
  `independent: false` (it does — keep it a gate).
- **pinned instance** instance A: 21,491,326,290 ÷ 266.91 = 80,519,000.6 = the published count.

### 4.7 `C14` — prose grounding on direction, not just on digits
- **severity** `H`, claim scope (delete the clause, never rewrite it).
- **reads** `outputs.structured.thesis.{narrative, catalysts[], risks[], price_target_basis}`,
  `outputs.llm_narrative.*`, `outputs.summary_text` against
  `outputs.structured.ownership_governance.{insider_net_flow, insider_buy_value, insider_sell_value}`
  and the frozen numeric leaves.
- **predicate** every amount must resolve to a leaf by **value and sign-or-magnitude**, and
  every direction word attached to it (`net sellers` / `net buyers` / `decrease` / `increase`)
  must agree with that leaf's sign. A clause may be deleted or flagged — **never rewritten with
  a number the sentence did not reference**.
- **pinned instance** GMED `…c9080e`: "`[target withheld]` of open-market purchases" for a `$0`
  datum. THC `99cdca`: *"the narrative stated $541.80 as the net flow figure; the published text
  was corrected to the computed value $49,991,274 (the printed amount belonged to another
  metric)"* — the same write path, caught and repaired **after** publication 21 times in the
  corpus. And the net-flow sentence that received the $90.61 target from the reconciler.

### 4.8 `C6` fix — derive the note from evidence, not from vocabulary
`C6` today concludes "no cross-validation" from the **absence of a second method**. Instance B
proves the conclusion must be computed from the presence of *cross-checks*: rewrite the clause's
evidence string from `cross_checks` (count, names, whether any brackets the price) and let the
synthesis' `degradation_note` quote it. This is the same defect class as the frozen
`ebitda_caliber` constant: a label that encodes a rule rather than a reading.

---

## 5. Ordering: the gate must see the evidence the report prints

Instance B is an **ordering** failure, not a missing-rule failure. In the run that produced
`99cdca` (20:27:40), the verdict path computed the own-history band **without** the run's share
count (`fetch_reverse_multiple_band` did not forward `shares_override`), so the band resolved to
**0 samples** and the verdict saw **no** cross-check; the cross-check in the payload arrived
*after* the verdict, injected by `audit.publish_band_cross_check` from the technical chapter's
948-sample band. The report therefore printed a cross-check its own decision had never read.

The log settles it: the report-side band first reports 948 samples in the run that produced the
*next* artifact — `finrobot.engine.pipelines.equity_research` `run_2be9149550b4` at **20:35:32**,
*"valuation synthesis: own-history EV/EBITDA band p25 3.91 · median 6.18 · p75 6.72 (948
samples)"* — eight minutes **after** the artifact that shipped the contradicted BUY was written.
Its sibling branch (`… band unavailable (no EV/EBITDA method row, no cross-check)`) is what the
verdict prints when it has no band to consult at all.

Two phases, then:

1. **Pre-verdict — evidence registration.** Every number a consumer is required to consult must
   exist, be frozen, and be *recorded as consumed* before the verdict is written. The
   `cross_checks` entry is produced by the same single band service the technical chapter uses
   (one function, one share count). A consumer that needs a band it does not have must produce a
   `Withheld` measure, never a silent zero.
2. **Post-assembly — claim verification.** `enforce_artifact_contract` at `runner.py:807`, as
   today, extended with §4. It verifies the **result**; it never re-decides the verdict
   (doctrine 1).

The division of labour matters and is already proven by `4e1a75f`: the compute layer owns the
**decision** (the dial now consults the cross-checks and returns HOLD), and the contract owns the
**verification** (a clause that would have refused to publish instance B's target). Neither
layer alone closes the class.

---

## 6. Phase 2 — one typed measurement, one vocabulary

Eight disclosure vocabularies exist today, none machine-readable and none blocking:
`assumption_provenance`, `data_authority.decisions[].{basis, comparability}`,
`withheld_reason` (a single string; both pinned THC artifacts carry `"contract_C7"` and neither
says *why*), `degradation_note`, `warnings[]`, numeric-audit `Finding`s, `report_drift` findings,
per-field `basis` strings, and the two mirrored `valuation_withheld` slots.

Phase 2 converges them:

```python
# engine/models/measurement.py (new, leaf layer)
Measure = Present(value, source, period, as_of, derivation: list[str]) \
        | Proxy(value, proxy_of: str)   # industry beta, sector multiple, scalar fallback
        | Withheld(reason_code: str, evidence: str) \
        | Unavailable(reason_code: str)
```

- `NumericClaim` (`engine/models/numeric_claim.py`) already carries `value, currency, period,
  source, as_of, findings` — it is missing exactly `basis`, `is_proxy`, `derivation`. Adding
  those three turns it into the ledger entry the clauses read, instead of clauses reading raw
  dict paths.
- `FieldCaliber` (`artifact/field_registry.py`) is the static half and stays static;
  `data_authority.decisions[]` is the runtime half and stays in the data layer.
- A consumer needing a *measurement* cannot accept a `Proxy` without an explicit
  `use_proxy()` that records the disclosure string — so "silent substitution" becomes a type
  error rather than a missing warning. The fixes already shipped (`None ≠ 0`, "industry levered
  beta proxy", `withheld_no_operating_income_row`, margin `basis`) are the hand-written
  precursors of this type.
- `SelectionPolicy`: every library default crossing into the domain is re-expressed as an
  explicit, tested policy (the FY2010 fact was edgartools' `(filing_date, period_end)` default,
  nobody's decision).

---

## 7. Verification and rollout

1. **Quantify before promoting.** `python scripts/scan_artifact_contract.py --clause C8` over the
   whole store *before* the clause is wired into the live gate — a clause that flags 40% of the
   back catalogue is over-broad and gets re-calibrated first. The scanner is read-only by
   construction; use it as the promotion gate.
2. **Golden fixtures.** The pinned instances (§1.1) plus the GMED pair become fixtures in
   `tests/artifact/`, stored as payloads, not as hand-built objects — so a clause is tested
   against the artifact that produced the defect, including the `99cdca` ordering case.
3. **Metamorphic relations** for the numeric core, where no ground truth exists: scaling
   `shares_outstanding` by *k* must scale every per-share output by 1/*k* and leave the band's
   `sample_count` unchanged (this catches instance B in one assertion: 0 vs 948); deleting a
   numerator must withhold every ratio that used it; swapping the provider must change the
   `basis` strings. See [metamorphic testing for scientific software](https://pmc.ncbi.nlm.nih.gov/articles/PMC7252536/)
   and the [banking-software application](https://www.cs.montana.edu/izurieta/pubs/IRI_2023.pdf).
4. **Per-clause unit tests** in `tests/unit/test_artifact_contract.py` (existing file), each
   clause with one passing and one violating payload, and a test that a violation **never raises**.
5. **No clause ships without a measured catch list** — the scanner output is the clause's
   justification, quoted in its docstring.

---

## 8. Doctrine — what a clause may never do

- Never flip a verdict, never withhold a *judgment*; withhold a value (doctrine 1).
- Never raise, never blank a run (doctrine 2).
- Never import `compute/`, `data/` or `pipelines/`, never re-run a computation (doctrine 3).
- Never hold a bare threshold literal; thresholds come from
  `engine/models/valuation_thresholds.py` (doctrine 4).
- Never **rewrite** prose. Delete a clause or flag it — the reconciler's authority to insert a
  number ("insiders were net sellers of $90.61") is the one write path that fabricated a fact.
- Never treat a placeholder as a distribution: a constant-derived band (±20% / ±25%) may be
  published as a range, never read as evidence of direction.

---

## 9. Open decisions for the owner

| # | Decision | Options |
|---|---|---|
| 1 | Severity of `C8` | `H` (withhold the target, keep the verdict) — recommended, consistent with doctrine 1 — or `S` (banner only), which reproduces today's behaviour |
| 2 | `C10` scope | Claim-scope withhold of the ratio leaves + promote the `FinancialData` findings to `blocked_field` (**recommended**) vs a banner |
| 3 | Do the 8 contradicted artifacts get re-run / badged? | (a) leave the archive, fix forward; (b) badge them with a `C8` note on read; (c) delete |
| 4 | `C13` hard case | Should a non-independent validator be *unable* to be the sole corroboration for a direction? (**recommended**) or advisory only |
| 5 | Phase-2 `Measure` | adopt now across `beta`/`shares`/margins/`nci`/`market_cap`, or defer until §4 has run in production for a release |
| 6 | Reason-code vocabulary | one registry for `withheld_reason` (`contract_C7` says nothing today) — needed for the coverage UI |
| 7 | `C12` catalogs | a hard clause on dated series vs soft, given the 8-K staleness is a data-availability issue, not a calc error |

---

## 10. References

**Internal** (read before changing anything in this area): `docs/REPORT_AUDIT_REMEDIATION.md`,
`docs/GMED_AUDIT_REMEDIATION.md`, `docs/THC_AUDIT_REMEDIATION.md`,
`docs/DATA_RECONCILIATION_DESIGN.md`; `artifact/contract.py`, `engine/models/numeric_claim.py`,
`artifact/field_registry.py`, `engine/models/valuation_thresholds.py`.

**External**

- Federal Reserve / OCC / FDIC, [Revised Guidance on Model Risk Management (SR 26-2, Apr 2026,
  superseding SR 11-7)](https://www.federalreserve.gov/supervisionreg/srletters/SR2602.pdf) —
  effective challenge, conceptual soundness, outcomes analysis, documentation/inventory, and
  validation of *vendor data and parameter values*. Note its scope: it excludes both generative
  AI and "simple arithmetic … spreadsheets", which is exactly why a report that composes models,
  arithmetic and an LLM needs this document's hybrid of MRM provenance and GenAI grounding.
- NIST, [AI RMF: Generative AI Profile (NIST.AI.600-1)](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) —
  content provenance is one of its four primary considerations; confabulation is a named risk.
- XBRL US Data Quality Committee, [Approved Validation Rules](https://xbrl.us/home/priorities/data-quality/rules-guidance/) —
  196 machine-checkable rules (v30, Sept 2026) of exactly the shape proposed here; `DQC_0004`
  (A = L + E), `DQC_0011` (dimensional equivalents — the GMED segment coincidence),
  `DQC_0005` (context dates after period end), `DQC_0015` (negative values).
- Rajalingham, Chadwick & Knight, [Classification of Spreadsheet Errors](https://eusprig.org/wp-content/uploads/0805.4224.pdf);
  Panko, [hard-coding input values into formulas](https://arxiv.org/abs/0803.0169) — the
  duplication / omission / temporal / circular-reference taxonomy used in §1.2.
- Chow-style [reject option and selective prediction](https://dl.acm.org/doi/10.1007/S10994-024-06534-X) —
  why `Withheld` must be a first-class output rather than a missing number.
- [Parse, don't validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/),
  [make illegal states unrepresentable](https://functional-architecture.org/make_illegal_states_unrepresentable/) —
  §6's `Measure` type.
- [Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993), [W3C PROV-DM](https://www.w3.org/TR/prov-dm/),
  [OpenLineage object model](https://openlineage.io/docs/1.48.0/spec/object-model) — the shape of
  the per-report quality ledger.
- [Metamorphic testing for scientific software](https://pmc.ncbi.nlm.nih.gov/articles/PMC7252536/),
  [applied to banking software](https://www.cs.montana.edu/izurieta/pubs/IRI_2023.pdf) — §7.3.
- [FActScore](https://arxiv.org/abs/2305.14251) — atomic decomposition as the measurement of
  prose grounding (§4.7).
