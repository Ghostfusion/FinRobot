# Report Invariant Closure — Design

Status: **accepted — the seven decisions were locked 2026-10-14 (§9), and Phase 1 has now landed
end to end**: the fifteen §4 clauses are promoted into the live persist gate (`C9` excepted — it
annotates, see §4.2), §4.4's writer unification ships with them, §5's back-fill tag closes the
ordering hole that produced instance B, and §9.3's `audit_badge` renders the read-time re-reading
on the artifact page. §4 is still a rule inventory with pinned instances rather than a change log.
**2026-10-16:** `C15` (§4.9) and `C16` (§4.10) join them after the owner review of QCOM
2026-10-12 — the live set is seventeen, and both annotate for the same staged reason `C9` and the
`C14` pair do.
What remains open is §6's ledger — the typed measurement and the reason-code registry — which is
what Phase 2 waits on.

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
| equity_research artifacts carrying the single-method "no cross-validation" note — `valuation_synthesis.degradation_note` (the same artifacts carry it in `thesis.price_target_basis`; searching the whole `structured` block reads 65) | **62** |
| `withhold_valuation=True` reached via `blocked_field` | 0 (every withhold came from the synthesis' own rule or `C7`) |
| **artifacts that published a BUY/SELL whose own published cross-check band sits entirely against the call** | **8** (HMY ×3, NFLX, SKM, THC ×2, UTHR) |
| findings named `insider_flow_amount_corrected` — the narrative wrote another metric's number into the insider-flow sentence and the pipeline silently repaired it afterwards | **21** |
| findings named `target_multiple_outside_band` — the published target sat outside the issuer's own multiple range | **23** |

The contradicted-verdict row is the architecture's problem in one number. It is not one bad
report; it is a recurring shape the gate is structurally unable to see, because **no clause
compares the verdict direction to the cross-checks the same payload prints.**

**This is a snapshot, not a constant.** The store is live and gains an artifact per run, so
every count here is an as-of number taken at `…20:37:52_THC_…`. A run that landed at 21:12 took
the same measurements to 105 artifacts / 91 with findings / 173 `review` / `contract_C7` ×32 /
the single-method note in 62 — which is why §7.1's catch lists carry a span rather than a bare
total.

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
`structured.valuation_withheld = null` **while `valuation_synthesis.valuation_withheld = false`**
(`outputs.structured` omits the slot entirely while `valuation_synthesis` writes `false` — C11's
catch list, below), `withheld_reason = null`, target $541.80 published,
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
| **cross-check band plausibility** | *nobody* | SKM published a cross-check band of **−$2.97 … −$1.23** against a $34.42 price — degenerate; HMY's $1.22–$3.74 against $16.71 is positive and fully sampled but sits ~5× below the tape, which `C8` catches, not `C9` | a band that is negative or degenerate is published as if it were evidence | **`C9`** |
| **conclusion-ratio operands (source / caliber / period) and numerator presence** | numeric audit on `FinancialData` only (`ev_bridge`, `ttm_period`, `currency_caliber`) | `ev_bridge_unverified` ×105 (review) | ratios whose operands come from **different providers** or whose numerator is `null` (THC `operating_margin = 0.18159` beside `operating_income = null`); the balance-sheet identity A = L + E (DQC_0004) is hand-written in one operator, not a clause | **`C10`** |
| **single definition** | *nobody* | `valuation_withheld` duplicated across two slots and the two writers already disagree in **65** of 105 artifacts (the root omits the slot, the synthesis writes `false`); band computed at 3 call sites; catalogue copy vs backend warning | two definitions of one quantity drift with nothing to catch it | **`C11`** |
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
  contradiction rule then publishes HOLD from the compute side, so the two agree) — locked §9.1.
- **reads** `outputs.structured.thesis.recommendation`,
  `outputs.structured.valuation_synthesis.{current_price, cross_checks[].{low,mid,high,name,label}}`,
  `outputs.structured.valuation_synthesis.methods[]`.
- **predicate** for `BUY`: no cross-check whose band contains `current_price`, **or** whose
  `mid > current_price`. For `SELL`: the mirror. A band that **brackets** the price claims no
  side; one corroborating check pointing the same way vetoes the violation. **A single
  uncorroborated contradicting band is enough** — measured 2026-10-14, every one of the 8 corpus
  hits carries exactly **one** cross-check entry, so a "≥2 checks must agree" guard would have
  fired on none of them, instance B included. Ignore a cross-check that `C9` has already flagged
  unusable — **measured consequence:** with that exclusion `C8` flags **7** of the 8 (SKM's band
  is the one `C9` rejects), so the two clauses cover the list only as a pair.
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
  **−2.97 … −1.23** against a $34.42 price, `sample_count` 948. Measured catch list = SKM only:
  HMY's `1.22 … 3.74` against $16.71 (and NFLX/UTHR/THC's bands) are positive, monotone and
  fully sampled, so `C9` does not fire on them — they are `C8` instances. `C9` is the *usability*
  rule; proximity to the tape is `C8`'s business.
- **Promoted `S` (2026-10-14), not the locked `H`.** The locked claim scope is "withhold the
  cross-check entries; do not withhold the target on this clause alone", and
  `enforce_artifact_contract` cannot drop a list entry: `_withhold` scrubs the headline slots. So an
  `H` arming would take SKM's target off for a display defect §4.2 forbids withholding the target
  for — and it would leave the nonsense band in `cross_checks` anyway, since the row is never
  removed. Heavier *and* less effective than the locked remedy, which is the same test the
  `C10`/`C12`/`C14` families fail. It annotates until the gate grows a claim-scope withhold (§9.2's
  mechanism, which the numeric-audit path already has through `withhold_keys`).

### 4.3 `C10` — conclusion ratios: same-source operands, and a numerator must exist
- **severity** `H`, **claim scope** (withhold the ratio leaves; promote the `FinancialData`
  finding to `blocked_field`). Count-thresholded per §9.2 (`error_if` for a published ratio,
  `warn_if` for a display-only field). Locked. **Promoted `S` (2026-10-14):** the predicates run as
  `S`/annotate until §9.2's count fields exist — the locked shape is the threshold, not a per-artifact veto, and
  a `C10a` veto armed alone would withhold the target on 69% of the catalogue (§7.1).
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
  `…financial_modeling.inputs.shares_outstanding`) and, in the frontend, any client-side
  arithmetic on `valuation.*`.
- **predicate** the two writers must use **one convention**: both emit the flag or neither does,
  and when both emit it the values must be equal. An explicit value on one side against an
  **omitted** slot is a divergence, not a permission — the earlier "or one of them must be
  absent" wording measured zero violations precisely because omission *is* the shape this defect
  takes. The duplicate is then removed in favour of a single writer.
- **pinned instance** the two `shares_outstanding` slots in every THC artifact; the two
  `valuation_withheld` slots; the +174% the frontend computed from a withheld point.
- **measured catch list** — **63 of 105**. The population makes the mechanism plain. The root
  writer emits the flag **only on the withheld path**; the synthesis writer **always** emits a
  bool:

  | `outputs.structured` | `valuation_synthesis` | n | what it is |
  |---|---|---|---|
  | absent | `false` | **63** | **every non-withheld artifact** ← the catch list |
  | `true` | `true` | 32 | every withheld artifact |
  | absent | absent | 8 | 3 equity + 5 other types |
  | `true` | absent | 2 | both ddm |

  So the clause is not catching an anomaly — it is flagging the NORMAL case (nothing was
  withheld), because one of the two writers is conditional on the very outcome it reports. Two
  writers, two conventions for one quantity: the *Duplication* class exactly, and it is why the
  clause is not preventive. The divergence never changed a verdict (both readings mean "not
  withheld"), which is precisely what made it invisible. Scope: an artifact with no synthesis
  block (a plain ddm/dcf dump, the 2 `true`/absent rows) has no pair to mirror, so it is out of
  scope — an earlier revision counted those and read 65. `financial_modeling.assumptions` is
  `null` in every artifact, so the third slot an earlier draft named does not exist.
- **promotion order is load-bearing, and the promotion criterion is a SPAN, not a zero.**
  Promoting `C11` as `H` **before** the single-writer fix would withhold the headline on every
  non-withheld report — that is, on every ordinary one. Sequence: unify the writers (the root
  emits on both paths, or the duplicate is retired in favour of one writer), then promote. But
  after the unification the **stored** corpus still reads 63: §9.3 annotates the archive on read
  and never rewrites it, so the promotion criterion cannot be "the scanner reports 0" — it is
  "the catch list's span has closed: no instance after the writer fix". That is the general rule
  for any clause whose defect class a shipped fix already closed (`C10a` at 16:44, `C10c` at
  19:59, `C6`/`C6b` at 20:27). What remains for `C11` after unification is regression protection:
  catching a second writer re-introduced. This is §9.5's expand → migrate → contract applied to a
  clause whose catch list is the writer, not the reader.
- **Shipped 2026-10-14** — the unification is in `artifact/builders.py`: the top-level
  mirror writes BOTH states and syncs the synthesis slot, so the point target is withheld iff
  either author withheld it and both slots then say so. The synthesis slot is written too
  because the audit path can withhold the point without the dial knowing (JPM's blocked EV field),
  which would otherwise leave the dial's record stale — the same defect one level down. Verified
  against the corpus with two live runs written after the change: GMED `art_…21:57:41` (target
  $90.37 PUBLISHED) carries root `False` + synthesis `False`, the explicit value the old writer
  never emitted; THC `art_…21:54:33` (withheld, `contract_C7`) carries `True` + `True`. The
  scanner then reads **63 of 107 with the catch list ending at `…20:27:40`** — the span has
  closed and the newest two artifacts are quiet, which is the promotion criterion above. The A/B
  DOM check (pre-change `c75ac2` vs post-change `81fd64`) is identical on every probed surface:
  `report-audit-banner` 1, `football-upside-withheld` 1, `report-data-authority` 1, cover text
  unchanged.
- **The promotion diff found the THIRD writer.** `valuation_withheld` has three writers, not two:
  the builders' mirror (above), the synthesis dial (`valuation_synthesis.py`), and — the one the
  first pass missed — `contract._withhold` itself, which runs at the persist boundary *after* both
  of them. Writing only the root there left root `True` beside a synthesis `False`, so the gate
  inflicted a `C11` violation on its own output (it fired on the next read and on every
  re-enforcement) and handed `technical_payload` a stale `has_anchor_target`. The promotion diff
  syncs the mirrored slot there too. That is the same defect one level up, twice — which is
  §7.1's argument for promoting a clause at all: arming `C11` is what *found* the third writer.

### 4.5 `C12` — recency and window closure
- **severity** two-threshold (§9.7, locked): `error_if` when the stale or undated item carried a
  published number, `warn_if` when it only populated a catalogue (remediation: exclude +
  disclose). **Promoted `S` (2026-10-14):** runs `S`/annotate — the `warn_if` floor — until §9.2's fields exist; the
  `error_if` half is what withholds, and it is not expressible today (§7.1).
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
- **severity** `S`, with the hard case **locked** (§9.4): a validator whose operands are a
  subset of the validated quantity's derivation — or whose `agreement_is_independent` is `false`
  — may not be the **sole** corroboration for a direction.
- **reads** `inputs.raw_data.data_authority.decisions[].{agreement_is_independent, candidates[]}`,
  `inputs.raw_data.market.market_cap` vs `{shares_outstanding, current_price}`,
  `outputs.structured.technical_analysis.monte_carlo.assumptions_used.{centered_on, independent}`.
- **predicate** `market_cap` must not equal `shares × price` unless labelled as a derived
  fallback; a Monte Carlo whose `centered_on` is the same base case it validates must publish
  `independent: false` (it does — keep it a gate). **Measured:** the tautology holds for
  **104 of 104** artifacts, so this clause cannot be a per-artifact finding — it is a rule about
  the `basis`/`independent` labels, and a `C13a` that flags every artifact is the over-broad case
  §7.1 exists to catch. `C13b` is likewise **preventive**: 48 artifacts declare
  `independent: false` (compliant) and the 44 that declare neither field are pre-fix, so the
  strict predicate has never fired. The broader "declares nothing" form measures 42% of the
  catalogue and is the over-broad case again (§7.1).
- **pinned instance** instance A: 21,491,326,290 ÷ 266.91 = 80,519,000.6 = the published count.

### 4.7 `C14` — prose grounding on direction, not just on digits
- **severity** `H`, claim scope (delete the clause, never rewrite it). **Promoted `S`
  (2026-10-14):** runs `S`/annotate — the locked remediation has no implementation in the persist gate. `enforce_artifact_contract`
  withholds VALUES (`_scrub_headline_slots`) and stamps the narrative; it cannot delete a sentence
  from `thesis.narrative`. Arming `C14` as `H` today would withhold the TARGET for a prose defect,
  which is not the locked remediation (§7.1).
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

**Staging note (2026-10-14) — "replaces" was one word too strong.** The fix has two halves and the
promoted set implements both, as a pair rather than as one rewritten clause:
live `C6` fires when a single-method headline's basis carries **no** disclosure at all, and the
promoted `C6b` fires when the note **denies** a cross-check the payload prints (instance B's shape).
Those are different predicates over the same sentences, so neither replaces the other — the
promotion diff keeps both, and additionally lets live `C6`'s evidence report the cross-check facts
the way `C6b`'s already does. Read "replaces" above as "replaces the *derivation*, not the
clause".

---

### 4.9 `C15` — prose may not claim a band relation its own numbers refute
- **severity** `S`, staged for the same reason as `C14` (§4.7): the locked remediation for a prose
  defect is to DELETE the sentence, and `enforce_artifact_contract` can only scrub values and stamp
  the narrative. Arming it `H` would withhold the TARGET for a sentence.
- **reads** `outputs.structured.thesis.{narrative, tagline, price_target_basis, catalysts[], risks[]}`,
  `outputs.summary_text` and `outputs.llm_narrative.*` (all via `_prose_strings`) against the run's own
  published `valuation_synthesis.{current_price, target_low, target_high}`.
- **predicate** a sentence claiming the band HOLDS the market price — a band verb whose OBJECT is the
  price ("wide enough to contain today's quote") — is judged only when the price is inside the
  published band; the inverse claim ("the price sits above the whole band") only when it is outside.
  The band named must be THIS run's band (a definite referent, and no qualifier naming another band:
  "52-week range", "sell-side range"), and the clause abstains when the relation cannot be settled
  from the payload (no price, no band, a zero-width band).
- **pinned instance** QCOM `art_2026-10-12T23:00:40…`: HOLD with a $124.44 target against a $174.43
  market price, justified in prose as the widened band being *"wide enough to contain today's
  quote"* — the price sits above the whole [$93.33, $155.54] band. Every amount in that sentence
  resolves to a real leaf, so `report_drift` sees nothing (it judges tokens, never relations), and
  `C8` never runs (it reads `cross_checks`, and only for BUY/SELL).
- **measured catch list 1 of 164** (`scripts/scan_artifact_contract.py --clause C15`). Two wider forms
  were tried first and rejected by false positive (§7.1): a bare claim-verb list flags 8 of the 9
  equity artifacts (7 falsely — those verbs take another object in a TRUE sentence: "the method's own
  range … bracketing the target", "no scenario inside the model"), and a band noun without a definite
  referent flags 2 (LPLA's claim is about the CROSS-CHECK's own band).
- **the other half of the same review:** the verdict's cause is stated where the narrative reads it
  (`valuation_synthesis.verdict_tier_note` → the published `price_target_basis`, which the prompt
  injects as its `Derivation:` line), and the prompt's price-level ladder now states the price's
  position against the published band. `C15` annotates a claim that slipped through; those two facts
  are what keep it from being written.

### 4.10 `C16` — a band printed in prose must not collapse onto one number
- **severity** `S`, same staging as `C14`/`C15` (locked remediation: delete the sentence).
- **reads** the same prose fields as `C15` (`_prose_strings`), and nothing else — it does not
  read the published band at all.
- **predicate** a sentence that (a) is about a band (`band | range | interval | spread |
  percentile`) and (b) prints two `$`-amounts joined by `to | through | and | - | – | —` whose
  parsed values are EQUAL. No attribution to a band is attempted (the sentence may name two);
  the evidence quotes the sentence so the reader can place it.
- **pinned instances** EXEL `…17:25:47` ("a DCF anchored at $64.05 with a $64.05-$64.05 band"
  against a real 51.24/64.05/76.86 method band), MU `…16:44:59`, EHC `…15:57:35`/`…20:52:12`
  ("The method's own band is wide ($151.38-$151.38)"), QCOM `…22:23:31`. Owner review of QCOM
  2026-10-12, item 3: "a ±20% placeholder band of $124.44 to $124.44" where the DCF's own band
  is $99.55-$149.32.
- **measured catch list 36 of 164 (22%), LIVE**, in two shapes whose dates separate them: the
  DCF/synthesis band restated as one number (2026-10-12..14 only — the 2026-10-16 price-level
  ladder supplies the method's real low/mid/high), and the Monte Carlo P5-P95 collapsed onto one
  number (still live on the newest artifacts: NVDA `…10-16T06:18:25`, MU `…10-16T05:13:05`, SOLS
  `…10-15T00:02:12`, against payload percentiles of 178.45/414.29, 529.87/1146.98, 58.40/144.42).
  The prompt DOES supply p5/p50/p95, so the second shape is the model's, not a missing fact.
  This is the prose-side backstop for `valuation_synthesis._prints_as_a_range` (2026-10-13), which
  guards the BASIS only, and for `C9`, which reads the STRUCTURED cross-checks. `report_drift`
  cannot cover it: both endpoints are real leaves, so no token is an orphan.
- **guard form, measured** the definite-referent guard `C15` uses gives 12 and MISSES the
  review's own sentence ("a ±20% placeholder band" has no definite referent); requiring only a
  band noun gives 36, all true. Kept the second.
- **the reader these two clauses read through** `_prose_strings` looked for `llm_narrative` and
  `summary_text` INSIDE `structured`, where they never are on a persisted payload — the fixture
  files carry `summary_text=""` and no `llm_narrative` at all, so the fixture oracle could not
  show the gap. It now takes both off `artifact.outputs`, which is where §4.7 always said they
  live, and the recorded catch lists above moved as a result (`C14b` 10 → 20, `C16` 30 → 36,
  `C15` gained OMC — a FALSE positive, whose METHOD-qualified "below the entire DCF band" is true
  of the DCF's own band, so the qualifier list now disqualifies method-named bands and `C15` is
  back to 1).

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

**Measured against HEAD (2026-10-14).** The first half of phase 1 has shipped, and the evidence is
that it is *one* service with *one* count: `fetch_reverse_multiple_band` is called at three sites —
`compute/coordinators/technical_payload.py` (the technical chapter) and `equity_research.py` twice
(the DCF-not-applicable fallback and the main synthesis) — and every one of them passes
`financial_data.market.shares_outstanding`, all reaching the same leaf
(`compute_bands_via_data_layer` → `resolve_band_shares`). The 20:35:32 log line above is that band
resolving *with* the override, eight minutes after instance B was written without it.

What is still open is the second half, and it is exactly the back-fill: `publish_band_cross_check`
(`compute/operators/audit/valuation_band.py`) still injects the row **post-verdict** when the
synthesis' own fetch came back empty — reading the frozen technical band, which is the same run's
data, so nothing is fabricated, but the ROW is still one the verdict never read. The pipeline's own
log line names that shape (`… band unavailable (no EV/EBITDA method row, no cross-check)`).
**Measured 2026-10-14, after the promotion (the reason the tag is not optional).** Of the 49 stored
artifacts that publish a cross-check row, **43 publish it beside no EV/EBITDA method row** — the
back-fill's signature, since the synthesis builds its own row from the same band as the method row,
so the two normally arrive together. All **7** of `C8`'s instances are in that set, instance B
(`99cdca`) among them. That means C8, armed at `H`, currently withholds on a row **the verdict never
read** in 100% of its standing catch list, and its evidence string — *"contradicts every published
cross-check"* — reads as though the call had the evidence and ignored it. The inference is the
*shape*, not a marker (a synthesis row can also lose its method row to a net-debt or negative-equity
drop while the cross-check survives); tagging at the back-fill site is exactly what makes those two
cases distinguishable again, which is why the smaller closure ships first.

**Measured again 2026-10-14, with the tag in the tree — the shape is now HISTORICAL.** Of the 57
stored artifacts that publish a cross-check row, the 43 back-fill-shaped ones — every one of which
also carries the frozen technical band the back-fill reads — span `…10-13T20:45` to `…10-14T20:27:40`,
and instance B is the LAST of them. The 14 newer rows, `…10-14T20:3x` through `…10-14T22:44`, all sit
beside an EV/EBITDA method row: the synthesis built them itself, so the pre-verdict band fetch now
resolves. (The row BMRN published at `…22:44:48` is one of them — its payload carries no technical
band at all, so the back-fill could not have produced it.) So the registration fix closed the
back-fill **in practice**, the tag is insurance on a path that no longer fires, and the precondition
closure below is regression protection rather than a live defect — the reading §4.3 already records
for `C10a`.

Two closures were available; the smaller one **shipped 2026-10-14**:

- **Shipped — the back-fill is tagged display-only.** `CrossCheck.consulted_by_verdict` carries the
  provenance (`True` from the synthesis, which builds the row while deciding; `False` only from
  `audit.publish_band_cross_check`, which publishes it after the verdict). `contract._consulted`
  gates `C8` — a row the call never had cannot be the evidence it ignored — while `C6b` keeps
  reading every printed row (it judges the report's display, not the decision) and now names the
  provenance in its evidence when every printed row is display-only. The artifact page renders the
  tagged rows as a caveat beside the football field (`football-cross-check-not-consulted`), because
  the whole point is that the reader is never shown a cross-check that reads as corroboration of a
  call that never saw it.
  The tag is provenance, not value: the two rows are the same band applied to the same EBITDA, so a
  clause could not tell them apart by shape (a synthesis row can also lose its method row to a
  net-debt or negative-equity drop). Consequence, and it is deliberate: **every stored row predates
  the tag and is therefore read as consulted**, so `C8`'s 7 instances keep their withhold exactly as
  measured above (§9.3 — the archive is annotated on read, never rewritten). The tag changes what
  artifacts written from 2026-10-14 onward can be judged on.
- Still open — make the synthesis' band a **precondition**: the directional call does not proceed
  without the band it is required to consult, or it records that it had none (the `Withheld`
  measure of §6). That is the closure that removes the back-fill's *cause*; the tag only stops the
  row from being misread.

Armed, `C8` refuses to publish what instance B published; that is the verification half, and as of
the 2026-10-14 promotion it is live.

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
  dict paths. **Measured 2026-10-14:** it carries them and *nothing in `finrobot/` builds or
  reads it*, so the fields have to arrive with the ledger itself — see §9.5's amendment.
- `FieldCaliber` (`artifact/field_registry.py`) is the static half and stays static;
  `data_authority.decisions[]` is the runtime half and stays in the data layer.
  **Measured 2026-10-14 — the caliber is a DISPLAY lookup, not the ledger's spine.** Of the 204
  stored numeric-audit findings (16 distinct `field_key`s), exactly **1** names a registered
  caliber; of the 13 `field_key`s the contract clauses emit, **zero** do. The two vocabularies are
  different kinds of name — the registry keys by the version-diff's display fields (`wacc`,
  `terminal_growth`, …), while the findings key by payload path or rule subject
  (`data_authority.ebitda`, `thesis.price_target`, `valuation_synthesis.cross_checks`,
  `valuation_withheld`). So the ledger cannot be assembled BY that join: it is assembled from the
  FINDINGS, which every claim has, and the caliber is attached only where one is registered —
  growing the registry to the finding vocabulary is its own change, and `pe_ratio` and
  `thesis.price_target` are the two user-facing keys that argue for doing it first.
  **Shipped 2026-10-14 — the ledger, as the findings index that measurement implies.**
  `artifact/numeric_ledger.py::build_numeric_ledger` returns one `NumericClaim` per field a
  verifier filed against (stored numeric-audit findings + the contract clauses, re-run as the
  badge re-runs them), so the claim vocabulary is the artifact's own; `NumericClaim` gained
  `basis` / `is_proxy` / `derivation` with producers in the same change (§9.5 records their
  reading). Measured at 120 artifacts: **528 claims over 29 `field_key`s — value resolved 124,
  declared basis 37, proxy 11, lineage 11**, and the largest keys are not numbers at all
  (`enterprise_value` 92, `xbrl_facts_snapshot._equity_identity` 73 — a blocker token,
  `valuation_withheld` 63 — a flag, `data_authority.decisions` 50 — a list). Two consequences for
  this section's own plan:
  - the claim set is complete (a claim exists wherever a finding does) while its provenance half
    is thin, so **the clauses cannot all be routed through it yet**: the migration is per-key and
    can start with the keys that NAME their source (`data_authority.<metric>`, 61 claims — the
    only ones carrying basis, proxy flag and lineage);
  - the field vocabulary is itself the work. Turning a rule subject into a measurable claim (which
    payload path backs `enterprise_value`, `pe_ratio`, `thesis.narrative`) is a producer-side
    change, not a ledger change — which is why the ledger ships first and the routing follows.
  **Shipped 2026-10-14 — the typed `Measure`, with a producer for every member.**
  `engine/models/measurement.py` holds the union (§6's four facts) plus `use_proxy()`, which is
  the type's whole point: a consumer cannot get a Proxy's number without naming itself, so a
  substitution leaves a trail instead of being a missing warning. The producer is the
  **data-authority decision** — §6's own "runtime half" — whose `measure` is now serialised into
  the payload beside the basis it types, and the mapping is derived from the record's own
  statements: an accepted value from the producer of record is `Present`, the SAME acceptance
  without an owner is `Proxy` (the measured margin shape: `yfinance` selected while the registry
  names another source as owner, `comparability caliber_divergent`), a **declined row** is
  `Withheld` (`sec_xbrl_preferred_stock_fill`: a real number FinRobot chooses not to state, which
  the decision's own `status` already flattened to `unavailable` — two different facts the type
  now keeps apart), and no eligible observation is `Unavailable`. The ledger reads the
  declaration rather than re-inferring it, and takes a proxied value through `use_proxy()`.
  Two honest limits, both measured:
  - the **provider's** finer fact — a margin taken from a scalar rather than the statement row it
    sits beside — still travels only as a warning string: the token (`provider_scalar`) exists in
    `yfinance_provider` and nowhere else, so typing it needs the provider → `NormalizedFinancials`
    → `FinancialData` hop, which is the next producer to convert (it is the one §6's own list
    of hand-written precursors names);
  - a measure's `reason_code` is carried **verbatim**, never re-spelled. §9.6 fixes
    UPPER_SNAKE_CASE, but the live vocabulary is lower_snake (`owner_decision_unwired`), so
    upper-casing at the measure site would mint the second spelling of every code — the lossiness
    §9.6 exists to end. That normalization is §9.6's, in one pass over the whole vocabulary.
- **`SelectionPolicy` — audited 2026-10-14; the audit is the deliverable.** The item asks that
  every library default crossing into the domain be re-expressed as an explicit, tested policy,
  with the FY2010 fact as the named precedent. Read against HEAD, the crossings are:
  - edgartools' getters rank a concept's facts by `(filing_date, period_end)` — filing date
    FIRST, which let THC's re-filed FY2010 net income out-rank FY2025 and ship as "latest
    annual" → `_concept_facts` / `_newest_usd_fact` / `_select_latest_fact` rank by **period_end
    first**, and the FY2010 case is a regression test;
  - `Ticker.history`'s adjusted-vs-unadjusted default (it changed across yfinance 1.x, silently
    rewriting every price series) → `auto_adjust=True` is passed at the call site with the reason
    in its docstring;
  - the vendor `info` margin scalars (computed on the provider's own basis, not the statement
    rows beside them) → the frame's own rows win, and a scalar is a declared `provider_scalar`
    (typing that token is the provider hop named above, still open);
  - edgartools' fund / N-PORT resolution (which report period counts as "latest") → the provider
    bounds it explicitly (a capped candidate list, its own timeout) and publishes the period it
    used.
  One arm was still silent, and it is closed here: when the multi-fact query API is unavailable,
  the selector falls back to edgartools' single-fact getters and thereby inherits their
  filing-date-first order. It now **warns, once per call**, naming the library's ordering — the
  arm is reachable only for a degraded build (production always has the query API), which is
  exactly when a different ordering would otherwise be invisible in the number a reader sees.
  That is the item's shape: not a new abstraction over four explicit sites, but the removal of the
  one crossing that no reader could have detected.
- A consumer needing a *measurement* cannot accept a `Proxy` without an explicit
  `use_proxy()` that records the disclosure string — so "silent substitution" becomes a type
  error rather than a missing warning. The fixes already shipped (`None ≠ 0`, "industry levered
  beta proxy", `withheld_no_operating_income_row`, margin `basis`) are the hand-written
  precursors of this type.
- `SelectionPolicy`: every library default crossing into the domain is re-expressed as an
  explicit, tested policy (the FY2010 fact was edgartools' `(filing_date, period_end)` default,
  nobody's decision).
- **Sequencing (§9.5, locked).** The three missing `NumericClaim` fields ship *with* the Phase-1
  clauses, because they are the clauses' input; the strict `Measure` type is enforced only once
  every producer populates them — expand → migrate → contract, with the exit criterion written
  down as "the scanner reports 0 claims whose `basis` is empty". Parallel change's own caveat is
  the reason for writing it down: a contract phase that never runs leaves two vocabularies live
  forever, which is the state this section exists to end.

---

## 7. Verification and rollout

1. **Quantify before promoting.** `python scripts/scan_artifact_contract.py --clause C8` over the
   whole store *before* the clause is wired into the live gate — a clause that flags 40% of the
   back catalogue is over-broad and gets re-calibrated first. The scanner is read-only by
   construction; use it as the promotion gate.

   **Measured 2026-10-14** — read-only, over the 97 stored `equity_research` artifacts present at
   the measurement (98 after the 21:12 run; see §1's snapshot note). 44 carry `cross_checks` and
   23 BUY/SELL artifacts carry none at all, so they are out of `C8`'s scope by construction.
   **Live** = the shape is still
   produced by HEAD's code; **historical** = it stops at a timestamp, i.e. a shipped fix already
   closed it and the clause's value there is regression protection.

   | Clause | Catch list | Span | Reading |
   |---|---|---|---|
   | `C6` | **27** / 12 tickers | …20:27:40 | a single-method report printing a cross-check while the note claims none — **live**; the last instance *is* instance B |
   | `C8` | **7** | — | the list §1.1 names minus SKM, whose band `C9` rejects — **`C8` + `C9` together = 8**; each instance carries exactly one cross-check entry |
   | `C8` + "≥2 must agree" | **0** | — | why §4.1 keeps the veto-only rule |
   | `C9` | **1** (SKM) | — | HMY's band is positive/monotone/948 samples → `C8`, not `C9` |
   | `C10a` ratio with a null numerator | **72** / 25 tickers | 10-10T21:58 … **10-14T16:44** | **historical**: `yfinance_provider.py:1110` already withholds the margin; every artifact from 19:18 on carries both operands |
   | `C10c` DQC_0004 identity | **73** / 24 tickers | 10-10T21:45 … **10-14T19:59** | `Assets`/`Liabilities`/`StockholdersEquity` present with `_equity_identity` **absent** — the identity is computed on one path only |
   | `C10d` caliber-divergent accepted | **35** artifacts / 102 decisions / 18 tickers | 10-13T22:53 … **21:12:35** | **live**: decisions accepted while `comparability = "caliber_divergent"`, several whose `basis` text names a provider other than `selected_source`; one finding per artifact, with the row count in the evidence |
   | `C10b` cross-provider operands | **0** | — | one `selected_source` per artifact (34 yfinance, 4 eodhd); no ratio pair crosses sources today |
   | `C11` mirrored slots | **63 / 105** | all | the catch list IS the non-withheld population: the root writer emits the flag only when it withholds while the synthesis always writes a bool. Representational, never verdict-changing — and 60% of the store, so it must not be promoted as `H` before the writers are unified, and its promotion criterion is a closed span, not a zero count (§4.4) |
   | `C12a` 8-K in the window | **10** / 5 tickers | 10-14T06:21 … **21:12:35** | **live**, and already *disclosed* as a warning string in two shapes; `C12` turns the disclosure into a gate |
   | `C12b` `news_window.count = 0` | **14** / 8 tickers | 10-14T00:23 … **20:37:52** | **live** — the empty feed is not THC-specific; the artifact still publishes `overall_sentiment` and key catalysts over it |
   | `C12c` stale fact published | **15** / 6 tickers | 10-13T20:18 … **16:31** | **live**: a fact the producer's own guard annotated (`stale: latest reported period is X, this fact is Y`) still ships in the current-fundamentals snapshot (EHC `OperatingIncomeLoss` frozen at 2022-12-31). The clause reads the annotation and holds no year band; the 9 artifacts whose oldest fact reaches back to 2009–2011 carry **no** annotation, which is the discrimination the producer's one-year rule already makes |
   | `C13a` `market_cap = shares × price` | **104 / 104** | all | universal, so it cannot be a per-artifact finding — only a rule about the `basis` label |
   | `C13b` self-centred Monte Carlo | **0** (48 declare `independent: false`) | — | the declaration is compliant wherever it exists and the strict predicate has never fired, so this is **preventive**. The 48-vs-44 split is the *declaration rate* — the 44 are pre-fix artifacts, span ending 10-13T18:39, carrying neither field — **not** a catch list. §4.6's "must publish `independent: false`" is what makes it a gate; the broader "declares nothing" form would flag 42% and is the over-broad case |
   | `C13c` `agreement_is_independent: false` | **0** | — | the flag has never been false; `C13`'s corroboration count is what gives it a consumer |
   | `C14` core, direction vs sign | **0** | — | no direction word contradicts its leaf — the shipped fix holds |
   | `C14` unresolved placeholder | **10** / 10 tickers | 10-14T00:16 … **19:59** | **live** (AFRM, ALL, AMZN, DVN, FOXA, GMED, NFLX, PGR, THC, UTHR): the prose carries `[target withheld]` where an **insider-flow amount** belongs — the scrubber took a figure the report publishes elsewhere (GMED *"[target withheld] of open-market purchases"* for a `$0` datum). The coarse "token anywhere in §4.7's prose" form measures **27** / 19 tickers and is rejected as over-broad by false positive: it fires on the legitimate withheld-path disclaimer (*"We initiate X at BUY on a directional read, not a point estimate"*), which is the producer's own honest copy |

   Two calibration consequences the table forces, beyond §4.1/§4.2:
   `C13a` **cannot** be a per-artifact finding (97/97 — it would flag the whole catalogue, which
   is the over-broad case §7.1 exists to catch), so it becomes a rule about whether the `basis`
   label declares the derivation; and `C13c` ships with **no** catch list, i.e. as a
   preventive clause whose justification is the inconsistency it would detect, not one it
   has. `C11`, by contrast, turned out to have 63 live instances the first probe missed — because
   the probe tested `a != b` behind an `is not None` guard, and the whole divergence is
   `null`-vs-`false`. That mistake is the argument for §7.2's "fixtures as payloads": a
   hand-written fixture would have carried the same guard, and a real payload does not.

   **Re-measured 2026-10-14 late, over 105 artifacts, against the clauses as implemented**
   (`scripts/scan_artifact_contract.py` — the clauses are in the registry, so the scanner always
   measures them; there is no staging flag any more): `C6b` 27, `C8` 7, `C9` 1, `C10a` 72,
   `C10b` 0, `C10c` 73, `C10d` 35 artifacts (102 accepted rows), `C11` 63, `C12a` 10, `C12b` 14,
   `C12c` 15, `C13b` 0, `C13c` 0, `C14a` 0, `C14b` 10 — **327 flags**. The scanner reproduces every
   probed number, which is what makes it the promotion instrument rather than a second opinion. Four
   rows above moved with the re-measurement (the store grew) and two of them changed *reading*:
   `C13b`'s 47 was a declaration rate, not a catch list, and `C14`'s placeholder had been tabulated
   in occurrences rather than artifacts (68 over 27, against the 10 the clause reports).

   **Where the counts stand since** (as-of readings over the growing store, §9.3's table carries
   the artifact counts): at 120 artifacts the scan reads **360 flags** — `C6b` 31, `C8` 7, `C9` 1,
   `C10a` 72, `C10c` 73, `C10d` 50, `C11` 63, `C12a` 24, `C12b` 14, `C12c` 15, `C14b` 10. The two
   `H` counts and every clause whose defect class has a shipped fix are unchanged; the `S`
   families that describe a live class (`C12a`, `C6b`, `C10d`) rose with the corpus. A per-clause
   count here is a date, not a constant — the clause docstrings say the same thing once, in
   `contract.py`.

   **Generalized 2026-10-15 (same day) — `C10e` now walks the IDENTITY REGISTRY.** The clause no
   longer carries a hand-written list of four ratios: it reads every declaration in
   `engine/models/identities.py` (`checked_identities()`), resolves each one's declared artifact
   paths against the artifact's own leaves, and reports the first residual above
   the band its figures' declared precision allows (`identities.identity_tolerance`), which falls
   back to `IDENTITY_RESIDUAL_TOLERANCE` (the renamed `RATIO_IDENTITY_TOLERANCE`) for a leaf that
   declares no precision and NAMES which band it used in the finding. Over 142 stored artifacts
   that band catches **63 of 609** bound checks against the coarse band's 48: the difference is
   sub-1% caliber mismatches a flat 1% excused (a KGC operating margin 0.8179% off its own
   `operating_income ÷ revenue`; INVH 0.2478%; MLI 0.2282%), while `ev_build` / `ev_ebitda` /
   `ev_revenue` stay at zero at the tighter band. Coverage now comes from the declaration rather
   than from the next bug report — which is how it immediately fired on
   `market.pe_ratio` 20.4867 against its own `market_cap ÷ income.net_income` = 20.1539 in
   `art_2026-10-12T15:57:35_EHC`, a ratio the four-entry tuple never looked at. The four ratios it
   replaced remain covered; `ev_build` / `ev_ebitda` / `ev_revenue` join them and are exact on
   100% of the 141 stored artifacts (measured — `scripts/sweep_identities.py`), and `market_cap` is
   declared `clause="exempt"` because a cap-vs-quote residual is a CLOCK difference the extractor
   already discloses against both instants. Design, sources and the deliberate non-goals:
   `docs/NUMERIC_DERIVATION_ARCHITECTURE.md`.

   **Added 2026-10-15 — `C10e`, the clause that divides a ratio by its own operands.** The family
   had `C10a` (the numerator must exist), `C10b` (both operands from ONE source), `C10c` (the
   balance-sheet identity recorded and closing) and `C10d` (a caliber-divergent accept must be
   disclosed) — and not one of them divides the two figures the artifact itself publishes. The CF
   audit (`docs/CF_AUDIT_REMEDIATION.md`) found the hole: a margin 21% above its own operands, above
   its own gross margin, with a provenance trail that was internally clean and a divergence count of
   zero. `C10e` reads only the artifact's own leaves (`income.operating_margin` against
   `income.operating_income ÷ income.revenue`, plus `income.ebitda_margin`, `valuation.ev_ebitda`,
   `valuation.ev_revenue`) against the tolerance it was born with (`RATIO_IDENTITY_TOLERANCE`,
   renamed `IDENTITY_RESIDUAL_TOLERANCE` by the generalization above), so it is source-agnostic
   and no decision record can talk it out of a finding.

   **Measured 2026-10-15** over the 140-row store: **22 artifacts / 12 tickers**, span
   10-14T05:39:47 … **10-15T00:50:08**, every one a yfinance run carrying Yahoo's
   `info.operatingMargins` scalar beside the TTM frame's own operands (CF: 0.49325 published
   against 3,025,000,000 ÷ 7,738,999,808 = 0.39088). The SPAN is the point — it does not stop at the
   provider fix (`4e1a75f`, 15:41:52 local) but at the cache invalidation shipped with this change:
   four of the 22 were generated AFTER that fix out of a payload cached before it (THC 21:54, KMX
   22:19, LPLA 23:50, CF 00:50), which is why the same change bumps the `financials` raw slot to v6
   and `CANONICAL_CONTRACT_VERSION` to 13. Six of the 22 sit in the pinned fixture set and now pin
   `C10e` there, so the pre-fix population stays the regression oracle for the clause.

   **Promoted severity, and why four clauses did not enter at §9's locked severity.** `C8`/`C11`
   entered at the severity §9 locks for them. `C9`, `C10`, `C12` and `C14` entered `S`/annotate
   although §9 locks them `H`, because their locked shape is not a per-artifact veto: `C9`'s locked
   claim scope is "drop the band entries, not the target" (§4.2) and the gate cannot drop a list
   entry — an `H` arming would withhold SKM's target for a display defect while leaving the nonsense
   band in `cross_checks`, i.e. heavier *and* less effective than the locked remedy. `C10` and `C12` are
   **count-thresholded** (`error_if` when the offending figure was *published*, `warn_if` when it only
   populated a catalogue or a display field) and `C14`'s locked remediation is "delete the sentence,
   never rewrite it" — which `enforce_artifact_contract` cannot perform, since it withholds VALUES and
   stamps the narrative rather than editing prose. Those mechanisms arrive with
   `ContractClause.warn_if`/`error_if` (§9.2). Arming `H` first would withhold a headline for a defect
   whose locked remediation is not a withhold — a `C10a` veto would have taken the target off the
   69% of the catalogue that trips it, and `C13b`'s broader form would have taken it off 42%.

   **The promotion criterion is a CLOSED SPAN, not a zero count, wherever a shipped fix already
   closed the defect class** — `C10a` (16:44), `C10c` (19:59), `C6b` (20:27), and `C11` once its
   writers are unified. §9.3 annotates the archive on read and never rewrites it, so the stored
   catch list for those clauses can never reach 0; what has to reach 0 is the count of instances
   produced AFTER the fix. That is what the span column is for, and it is why the scanner (which
   sweeps history) is a promotion instrument rather than the promotion test.

   **Promoted 2026-10-14.** The fifteen clauses are in `CONTRACT_CLAUSES` and
   `artifact/proposed_clauses.py` is gone — quantifying outside the registry first is the *practice*
   this section describes, not a second universe that ships. The severities are the ones argued
   above: `C8`/`C11` at `H`, `C9` and the other eleven at `S`. Read over the store immediately before the
   promotion (`--badge`: **0** withhold / **0** annotate / 105 clean) and immediately after
   (**70** withhold / **31** annotate / **6** clean over the 107 artifacts then stored), the delta is the back catalogue's
   `C11` population plus its `C8`/`C9` instances — every one of them written before its remediation
   shipped, and §9.3 is how a reader sees that without a stored record being rewritten. The live
   gate acts prospectively: on the two artifacts written after §4.4's unification, the promoted set
   reads `REVIEW (C10d, C12a)` and withholds nothing. `C11`'s span closed at `…20:27:40` (§4.4),
   which is the criterion this section sets — not a zero count.

   Re-measured once `C9` moved to `S` with the store at **110** (the corpus grows as runs land):
   **69** withhold / **35** annotate / **6** clean, **336** flags. The withhold set decomposes
   exactly — 62 artifacts are `C11`-only, 6 are `C8`-only, and 1 (`99cdca`) carries both — so the
   two armed clauses cover different artifacts rather than one subsuming the other. `C11`'s own
   list runs from `…10-10T21:45:27` to `…20:27:40`.


   The corpus also re-confirms §1's table at HEAD: **170** `review` findings, **0**
   `blocked_field`, `withhold_valuation` never true, `withheld_reason` = `contract_C7` ×31 / null
   ×66, `artifact_status` = `caveated` ×90 / `publishable` ×7; findings
   `ev_bridge_unverified` ×105, `target_multiple_outside_band` ×23,
   `insider_flow_amount_corrected` ×21, `metric_authority_unavailable` ×11,
   `insider_flow_amount_mismatch` ×7, `foreign_issuer_usd_tags` ×2,
   `net_income_exceeds_operating_income` ×1.

   The numbers are each clause's justification and go into its docstring (§7.5).
2. **Golden fixtures.** The pinned instances (§1.1) plus the GMED pair become fixtures in
   `tests/artifact/`, stored as payloads, not as hand-built objects — so a clause is tested
   against the artifact that produced the defect, including the `99cdca` ordering case.
   **Shipped:** 16 payloads under `tests/artifact/fixtures/contract/`, written by
   `scripts/extract_contract_fixtures.py` (a declared path spec per artifact — a full row reaches
   3 MB, `insider_transactions` alone is 1 MB — values verbatim) and asserted by
   `tests/artifact/test_contract_fixtures.py`, which re-runs every registered clause over
   each payload and compares against the verdict map recorded at extraction. 665 KB total. Two
   fixtures exist to stay QUIET — SMCI's withheld-path disclaimer for `C14b` and AMZN's 2009-era
   long history for `C12c` — because a false-positive guard that is never tested is a guard that
   silently rots.
3. **Metamorphic relations** for the numeric core, where no ground truth exists. Measured against
   the tree as it stands, two of the three already exist and the third belongs beside them rather
   than in a new file:

   - *scaling `shares_outstanding` by k scales every per-share output by 1/k and leaves the band's
     `sample_count` unchanged* — **added** to `tests/unit/test_valuation_band_cross_check.py`. This
     is the assertion that would have caught instance B, whose band resolved to 0 samples because
     the call omitted the run's share count; its sibling pins the other half, that a band with no
     sample count (0 or absent) never prints "0 samples" but says the count is unavailable.
   - *deleting a numerator yields no row instead of a zero* — already pinned there
     (`test_missing_ttm_ebitda_emits_no_entry`, `test_missing_shares_or_net_debt_emits_no_entry`).
   - *swapping the provider* — already pinned in `tests/unit/test_data_authority.py`: the
     `selected_source` follows the provider, and the decision record is order-independent
     (`test_reconcile_results_is_deterministic_and_sorted_by_metric`).

   **Correction to this rule as first written:** the *basis string* does NOT change with the
   provider. Measured 2026-10-14 by reconciling the same payload from `fmp` and from `yfinance`:
   `gross_margin`'s basis is *"gross_profit / revenue on FMP's TTM income-statement caliber"* for
   BOTH — the basis names the caliber's ORIGIN, not the source of this value. A basis string is
   therefore not evidence of who supplied the number, which is exactly why `C10d` reports "the
   basis text names a provider other than `selected_source`" as an observation to review rather
   than as a violation. See [metamorphic testing for scientific software](https://pmc.ncbi.nlm.nih.gov/articles/PMC7252536/)
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

## 9. Decision record — locked 2026-10-14

All seven decisions were resolved in favour of the recommended option. Each entry gives the
choice, the reasoning, what it changes in §4, and the source that settles it. Implementation is
Phase 1 (§7); the archive treatment in §9.3 is the only part that is not a code change.

### 9.1 `C8` severity — **`H`**: withhold the target, keep the verdict

- **Why.** (a) It is the doctrine already in the codebase — *"corrupt data withholds the value,
  never the judgment"* — and the fix that shipped in `4e1a75f` puts the dial on the same side:
  it returns HOLD and withholds the point, so an `H` clause agrees with compute instead of
  overriding it. (b) A published recommendation needs a *reasonable basis*; when the model's own
  cross-check sits entirely the other side of the price, the basis is absent — CFA Institute
  Standard V(A) *Diligence and Reasonable Basis* is the profession's statement of that
  obligation. (c) The information cost of withholding is small: target prices' short-term
  informativeness concentrates in the revision and the implied return, not in the level of the
  point estimate (Brav & Lehavy 2003). (d) Withholding is what the pipeline already does for the
  out-of-band case — 7 of the 8 corpus instances carry `withheld_reason = contract_C7` — so `H`
  makes the contradicted case consistent with the case that already works, and closes the one
  gap in that behaviour (instance B, where nothing was withheld).
- **What it changes in §4.** As written in §4.1: `H`, headline scope.
- **Rejected alternative.** `S` (banner). The corpus says a banner is ignored: 23
  `target_multiple_outside_band` findings and 171 findings in total, and zero withholds.

### 9.2 `C10` scope — **claim-scope withhold, count-thresholded**

- **Choice.** Promote the ratio findings from `review` to `blocked_field`, so
  `_attach_numeric_audit` nulls the leaf through the existing `withhold_keys` / `rich_withhold`
  path; the headline target is withheld only when a *published conclusion* rests on the bad leaf.
- **Thresholds are counts, not booleans** (dbt's `severity: error|warn` + `error_if`/`warn_if`
  shape): a scalar-vs-frame mismatch on a *published* ratio is an error; the same mismatch on a
  display-only field is a warning. `ContractClause` gains optional `warn_if`/`error_if` count
  fields so a clause can be "over-broad but reviewed" while it is calibrated.
- **Why hard.** A ratio whose numerator the artifact itself reports as `null` is not a number
  with a caveat; it is a number that does not exist. The SEC's own filing-validation regime
  treats *this* class — the identity that must hold (DQC_0004), values that cannot be negative
  (DQC_0015), the dimensional-equivalence check (DQC_0011) — as errors, not notes. Matching that
  severity keeps the report's own arithmetic accountable to the same standard as the filings it
  reads.

### 9.3 The eight contradicted artifacts — **leave the record, annotate on read; never rewrite**

- **Choice.** No re-run, no delete, no in-place edit. `scripts/scan_artifact_contract.py`
  (read-only, already the promotion instrument) gains a "would-flag under the live clause set"
  report, and the artifact page renders a derived `audit_badge` computed at read time from the
  stored payload. New reports are prevented by `C8`; the eight stay as the evidence of the flaw
  that motivated it.
- **Shipped (2026-10-14):** the report half is `--badge`, which transposes the per-clause catch
  lists into the artifact's own unit — one line per artifact with the clauses that would withhold
  it (`H`) or annotate it (`S`), plus the `archived` column read from the summary (archive is a
  24h-no-view staleness flag and lives on the summary, not on the payload a clause reads).
  **The artifact-page badge shipped 2026-10-14 too** — the second half is described below. Two
  readings, and they are the argument for the whole design:

  | clause set | would withhold | would annotate | clean |
  |---|---|---|---|
  | **live before the promotion** (`C1`–`C7`, 105 artifacts) | **0** | 0 | 105 |
  | **at the promotion** (all 22, 107 artifacts) | **70** | 31 | 6 |
  | **after `C9` moved to `S`** (110 artifacts) | **69** | 35 | 6 |
  | **at the badge ship** (120 artifacts) | **69** | 45 | 6 |

  The last two rows are the criterion this section argues for, measured: the withhold count is
  FROZEN at 69 across ten newly written artifacts, while the annotation count rose 35 → 45 over
  those same ten. The `H` clauses fire only on the pre-remediation back catalogue (their defect
  classes are closed going forward), while the `S` clauses keep finding the live store — which is
  what "a closed span, not a zero count" means for a rule whose cause has shipped.

  The first row is the finding: the shipped rules would not have withheld a single one of the
  contradicted artifacts. The second and third are that same defect class, now counted — 62 of the
  69 withholds are `C11`-only and 6 are `C8`-only (instance B carries both), which is why §4.4's
  unification had to precede the promotion, and every one of the 69 was written before its own
  remediation shipped. The badge is a **reading of the stored
  payload under today's registry, never a verdict on the record**: the record keeps its bytes, and
  the artifact's own `[CONTRACT/*]` warnings — present only on reports written after the clauses
  were armed — are the shipped side of the distinction.

  **Measured 2026-10-14, after the promotion (the page half's real scope).** The banner surfaces
  the HARD form only: `parseSurfacedContractFindings` keeps `[CONTRACT/Cn] evidence` and drops the
  `/note`, `/withheld` and `/internal` sub-tags by design. A live run through the promoted gate
  proves the split — `art_…22:36:07_BMRN_…_211597` carries three soft notes (`C6b`, `C10d`,
  `C12a`) in `outputs.warnings`, and the artifact page's banner renders none of them. So the soft
  clauses' annotations are machine evidence reaching no reader surface, and the badge is the only
  channel that can show them — which is exactly what it is for: its `annotate` half is not
  decoration, it is the reader-facing half of `S`.
  Note the `archived` column shows `no` everywhere: nothing in the store has aged past the 24h
  no-view window yet, so the column is exercised but not yet populated.
- **Shipped 2026-10-14 — the page badge, and it shipped the way the plan above said it had to.**
  Reading the viewer settled where the input would come from: `ChapterAuditBanner` renders
  `outputs.structured.numeric_audit` plus the `[CONTRACT/*]` findings it parses out of
  `outputs.warnings` — so the persist gate ALREADY surfaces contract findings to the page, and the
  back catalogue has none of those warnings because the clauses were not armed when it was
  written. That is exactly why this decision asks for a *read-time* derivation, and it has three
  parts:
  - **Python, behind the artifact route.** `artifact/audit_badge.py::derive_audit_badge` re-runs
    `CONTRACT_CLAUSES` over the stored payload; `GET /api/artifacts/{id}/audit-badge` serves the
    result. It is deliberately NOT a field on `GET /{id}`: the record's bytes stay exactly as
    stored, so nothing derived can be round-tripped back into the archive by a writer that
    re-posts what it fetched — and a TypeScript re-implementation would be a second definition of
    every rule (doctrine 1).
  - **One reading, two facts.** `surface=False` clauses are excluded (their evidence is plumbing
    the reader surface must not render; they still gate the record), and the record's own
    `shipped_withheld` / `shipped_withheld_reason` rides every response — a surface cannot show
    what today's rules would do without the record's own answer beside it. Verified live on
    stored artifacts: instance B (`99cdca`) reads *"Today's rules would withhold the target:*
    `C8` … `C11` …" with both evidence strings and closes with *"As shipped: nothing was
    withheld"*; the `contract_C7` artifacts (`81fd64`) read the annotate half only, with *"As
    shipped: the target was withheld (contract_C7)"*; and a report the promoted gate wrote
    (`9d0bc3`) reproduces the gate's own three notes (`C6b`, `C10d`, `C12a`) as annotations — the
    badge and the persist gate agree, as they must, because they run the same registry.
  - **The wording carries the table above's distinction** — a re-reading under today's rules,
    never a statement that the report shipped withheld (a badge reading `WITHHOLD` on a published
    report would be the reader's first impression of a correct document). The block renders beside
    `ChapterAuditBanner`, not inside it: the banner's visibility is defined by THIS report's
    findings, while the reading has to render whatever they say. And it renders nothing when
    nothing fires — the absence of a finding is not news.
  Its reading is *"would-flag under the live clause set"*: **70 withhold / 31 annotate / 6 clean
  over 107** at the promotion, 63 of those withholds being the `C11` population of §4.4 — ordinary
  reports, most of them healthy.
- **Why: the domain's own answer to a wrong filed report is an amendment, not an edit.**
  17 CFR 240.12b-15: an amendment is *"filed under cover of the form amended, marked with the
  letter 'A' … '10-K/A'"*, *"must set forth the complete text of each item as amended"*, and
  *"must be numbered sequentially and be filed separately for each statement or report
  amended"* — the original filing is never revised. For the retention mechanics,
  17 CFR 240.17a-4(f)(2)(i) permits exactly two designs: an electronic recordkeeping system with
  *"a complete time-stamped audit trail that includes all modifications to and deletions of the
  record … and will permit re-creation of the original record if it is modified or deleted"*, or
  one that preserves records *"exclusively in a non-rewriteable, non-erasable format"*. The badge
  is the first branch; `artifact/seal.py` already seals the payload, so the second is available
  to us as well.
- **Also the ethics frame.** The IIA Code of Ethics, Objectivity Rule 2.3 — *"Shall disclose all
  material facts known to them that, if not disclosed, may distort the reporting of activities
  under review"* — is precisely a badge obligation, not a rewrite obligation.
- **Explicitly not chosen:** re-running the eight. A re-run produces a *new* artifact and leaves
  the contradicted one in place anyway; it changes no record and costs 8 × ~3 minutes of
  provider calls. Deleting them destroys the audit trail that this design cites as evidence.

### 9.4 `C13` hard case — **a non-independent validator cannot be the sole corroboration**

- **Choice.** An independent check may *confirm* a direction; a self-reviewing one may only *fail
  to contradict* it. Implementation: a candidate with `agreement_is_independent: false` is
  excluded from the corroboration count the clauses read, and `C13` reports the resulting count.
- **Why.** This is a named threat category, not a preference. SR 26-2 requires effective
  challenge to be *"performed by individuals with the appropriate expertise … sufficient
  independence to maintain objectivity"*; the IIA Rules of Conduct 2.1–2.3 prohibit participating
  in *"any activity or relationship that may impair or be presumed to impair their unbiased
  assessment"* — the self-review threat. A Monte Carlo centred on the DCF it is validating, and a
  `market_cap` derived from `shares × price`, are both self-review: the "agreement" is an
  identity, not evidence.

### 9.5 Phase-2 `Measure` timing — **expand now, contract on an exit criterion**

- **Choice.** The three missing `NumericClaim` fields (`basis`, `is_proxy`, `derivation`) ship in
  the same release as the Phase-1 clauses — they are the clauses' input, so they cannot be
  deferred without the clauses reading raw dict paths. The strict `Measure` type is enforced only
  after every producer populates those fields.
- **Why phased.** Expand → migrate → contract is the standard way to make a breaking change
  without a big bang, and its own caveat is the reason the exit criterion is written into the
  doc: *"during the migrate phase the supplier has to support two different versions … If the
  contract phase is not executed you might end up in a worse state than you started."* Our exit
  criterion: `scan_artifact_contract.py` reports **0 claims with an empty `basis`**.
- **Explicitly rejected:** adopting the type everywhere now. The numeric core would have to
  change in the same release as the gate, which makes the gate's own effect on the corpus
  unmeasurable — the property §7 item 1 depends on.
- **Measured against HEAD (2026-10-14) — the first step was mis-stated by one level, and the
  correction matters.** `Finding` is the live vocabulary: the ten-odd audit verifiers,
  `artifact/contract.py` and every clause in that registry import it. `NumericClaim` is imported by
  **nothing under `finrobot/` except its own module** — the only importer in the tree is
  `tests/unit/test_numeric_claim.py`. So this is not a ledger that lacks three fields; it is a
  model with no producer and no consumer. Adding `basis`/`is_proxy`/`derivation` today would be
  unobservable: nothing constructs a claim, so nothing could populate or read them, and the exit
  criterion ("0 claims with an empty `basis`") would be measured over an empty set — a green
  number that means nothing. The real first step is therefore **build the ledger**: join the
  verifiers' findings with `field_registry` caliber at the artifact layer, route the clauses
  through the result, and add the three fields as part of that join. The decision's sequencing
  (expand → migrate → contract) and its exit criterion are unchanged; only the first mover is
  named correctly here.
- **Shipped 2026-10-14 — the ledger, with its three fields and its instrument.** The first mover
  is done: `artifact/numeric_ledger.py::build_numeric_ledger` builds one `NumericClaim` per field
  a verifier filed against (the artifact's stored numeric-audit findings plus the contract
  clauses, re-run exactly as the badge re-runs them), and `NumericClaim` gained `basis`,
  `is_proxy` and `derivation` in the same change — each with a producer, because the doctrine
  forbids a field nothing fills: `basis` is the data-authority decision's own basis for that
  metric (or the field's declared `*_basis` sibling), `is_proxy` is the record's
  `is_authoritative: false` (no wired source owns the metric), and `derivation` is the declared
  lineage (`source:`, `definition:`, `policy:`). `scan_artifact_contract.py --ledger` prints the
  coverage, **including the exit criterion's own number** rather than leaving it to be
  subtracted.
  **The criterion's first reading, and it is not close: 528 claims over 120 artifacts, of which
  491 carry no declared basis.** That is the expand phase measured honestly — the claims all
  exist (every one traces to a finding), while the provenance half is thin because the payload
  declares provenance for the keys that NAME their source (`data_authority.<metric>`, 61 claims,
  the only ones with a decision) and for almost nothing else. So the exit criterion is real,
  reachable and currently far away, which is exactly the state a first reading should show.

### 9.6 Reason-code registry — **one enumerated vocabulary keyed by `(reason_code, domain)`**

- **Spec** (mirrors `google.rpc.ErrorInfo`, AIP-193): `reason_code` is UPPER_SNAKE_CASE, ≤63
  characters, matching `[A-Z][A-Z0-9_]+[A-Z0-9]`, **stable forever**; `domain` groups it
  (`contract`, `data_authority`, `drift`, `audit`); every dynamic number lives in `metadata`,
  never in the code; the `(reason_code, domain)` pair is unique per logical cause and must not be
  reused for a different one.
- **Measured 2026-10-14 — the lossiness this decision exists to end, counted.** Of the 43 stored
  artifacts that ship withheld, **38 carry `withheld_reason = "contract_C7"` and not one of those
  38 records a cause clause anywhere in the payload**; the other five do (`contract_C1` ×2,
  `valuation_synthesis_dial` ×3). C7 is the no-resurrection *scrub* — an internal invariant whose
  job is to null a headline slot that survived a withhold — so those 38 pages tell a reader that a
  rule they cannot see has run, and never why the price is gone. One string slot, last writer
  wins: the scrub holds the only place a cause could have lived. That is why the shape has to be
  structured rather than a longer string — a cause and the scrubs that followed it are two
  different facts, and the reader needs both.
  Size, from the same HEAD: producers are `builders.py` ×3 (`numeric_audit_blocked_field` twice,
  `valuation_synthesis_dial` once) plus `contract._withhold`; readers are `builders.py`'s own
  reason read, the badge's `shipped_withheld_reason`, and the report parser's `[CONTRACT/Cn]`
  evidence (the cover reads the evidence, not the raw string); ~8 tests pin the string today.
- **Shipped 2026-10-14 — the vocabulary, the split, and the overwrite that caused the lossiness.**
  The structure is in and the measurement above is now a regression test:
  - `engine/models/withhold_reason.py` holds `WithholdReason` (`reason_code`, `domain`,
    `metadata`, `help_url`) and **the enumerated vocabulary** — one dict, `WITHHOLD_CODES`, where
    every code is declared once with its domain. Three rules are tests, not intentions: the code
    shape §9.6 fixes (`[A-Z][A-Z0-9_]+[A-Z0-9]`, ≤63), one `(reason_code, domain)` pair per cause,
    and dynamic numbers in `metadata`. `withhold_reason()` is the only constructor and it refuses
    a code that is not declared — a code spelled at a call site is how one cause gets two names.
  - **The cause is now preserved rather than overwritten.** Each H clause declares its own code
    beside its title (`C1` `TARGET_OUT_OF_BAND`, `C1b` `METHODS_DIVERGENT`, `C2` `MALFORMED_AMOUNT`,
    `C3` `BASIS_CONTRADICTS_HEADLINE`, `C4` `CALIBER_MISMATCH`, `C7`
    `HEADLINE_SLOT_RESURRECTED`, `C8` `VERDICT_VS_CROSS_CHECKS`, `C11`
    `SPLIT_WRITER_CONVENTION`), and a test asserts every H clause declares one and that no two
    claim the same cause. When an upstream producer already named the cause (the dial, the audit),
    the gate KEEPS it and records its own act — the clause ids — in `metadata`; only when nothing
    upstream spoke does a firing clause's code become the cause, and it is the first in registry
    order.
  - **One reader for both shapes.** A producer writes the model into the in-memory payload, pydantic
    serialises it on save, and a stored payload therefore reads back as a dict — so
    `as_withhold_reason()` accepts both. Skipping that is how the lossiness would have returned a
    second time, through a type instead of an overwrite: the first pass of this change did exactly
    that, and the audit-gate tests caught it.
  - The pre-2026-10-14 `withheld_reason` STRING is no longer written; it is still read, because the
    archive keeps its shape (§9.3). The `domain` set adds `valuation` for the dial: §9.6 names
    three domains as the grouping rule, and the dial withholds a point target without any clause
    firing, so filing it under a gate it never ran would be the same lossiness in miniature.
- **The shape, and what it replaces.** `withheld_reason: str` is
  `{reason_code, domain, metadata, help_url}`. `contract_C7` splits into at least two causes —
  the resurrection scrub and the out-of-band target — because one pair for two logically
  different errors is exactly the lossiness measured in §6, and AIP-193 forbids it. The
  coverage/report UI renders the code; the reader-facing sentence is generated from `metadata`.
- **Sources.** AIP-193 (`ErrorInfo`, and the `Help{description, url}` payload for the doc link);
  RFC 9457 for the URL-shaped variant (`type` as the stable problem identifier, with the IANA
  "HTTP Problem Types" registry as the precedent for a public registry). The XBRL US DQC rule ids
  (`DQC_0004`, `DQC_0015`, …) are the same idea in this domain: a stable id, versioned, with a
  published remediation.

### 9.7 `C12` catalogs — **two thresholds (`warn_after` / `error_after` shape)**

- **Choice.** `error_if` when the stale-or-undated item *carried a published number*; `warn_if`
  when it only populated a catalogue (news/8-K list), where the remediation is exclusion plus
  disclosure.
- **Why two thresholds.** Freshness policy in practice is two-threshold with a count and a
  period (dbt's `warn_after`/`error_after` = `{count, period}`) because the cost of staleness
  depends on what consumes the data. The SEC's own version of this rule for facts — DQC_0005,
  context dates after the period end — is an error only for the filing's own required facts. Our
  analogue: an FY2010 net income feeding a published multiple is an error; a February 8-K inside
  a "30-day window" catalogue is a warning with an exclusion footnote.

### 9.8 Cross-cutting consequence

`ContractClause` needs two additions to carry these decisions: optional `warn_if` / `error_if`
count thresholds (§9.2), and a `title`/`doc` pair so the reason-code registry (§9.6) has a
renderable name per clause. Both are additive and neither changes the existing seven clauses'
behaviour.

**Shipped 2026-10-14.** All four fields exist on the dataclass with defaults, and the decision's
own claim — additive, behaviour-preserving — is what makes that safe to land ahead of their first
user. The `title`/`doc` pair is populated for all 22 registered clauses
and already has a consumer: `scripts/scan_artifact_contract.py` heads each catch list with the
rule's name and its one-liner instead of a bare id, so the human-review payload reads the words
the registry will serve. `warn_if`/`error_if` are **declared and inert** — no clause sets them,
`enforce_artifact_contract` reads only `severity`/`check`/`surface`, and
`tests/artifact/test_contract_fixtures.py`'s verdict oracle is the proof (the suite is unchanged
by the addition).

What they still need is the COUNT itself: a `check` returns at most ONE `Finding`, and the
offending-item count a clause like `C10d` already prints in its evidence has no structured home.
That carrier is `NumericClaim`'s `basis`/`is_proxy`/`derivation` addition (§6/§9.5), so the
thresholds become readable in that change rather than in this one — which is why the fields land
here declared rather than consumed.

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

**Decision sources (§9)**

- CFA Institute, [Standard V(A) Diligence and Reasonable Basis](https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-v-a) —
  §9.1: a recommendation must rest on adequate research; a target its own evidence contradicts
  has no basis.
- Brav & Lehavy, [An Empirical Analysis of Analysts' Target Prices](https://webuser.bus.umich.edu/rlehavy/BL.pdf)
  (*Journal of Finance*, 2003) — §9.1: target-price informativeness concentrates in revisions and
  implied returns, not in the level of the point estimate, so withholding one costs little.
- [dbt: severity, error_if, warn_if](https://docs.getdbt.com/reference/resource-configs/severity)
  and [dbt: freshness](https://docs.getdbt.com/reference/resource-configs/freshness) —
  §9.2 and §9.7: count-based thresholds (`error_if: ">1000"`, `warn_if: ">10"`;
  `warn_after`/`error_after` as `{count, period}`) rather than a binary severity per rule.
- Danilo Sato / Martin Fowler, [Parallel Change (expand → migrate → contract)](https://martinfowler.com/bliki/ParallelChange.html) —
  §9.5, including the caveat about an unfinished contract phase.
- Google, [AIP-193: Errors](https://google.aip.dev/193) (`google.rpc.ErrorInfo`: `reason` as a
  stable UPPER_SNAKE identifier, unique `(reason, domain)` pairs, metadata carrying every dynamic
  value) and [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html) with the
  [IANA HTTP Problem Types registry](https://www.iana.org/assignments/http-problem-types) —
  §9.6.
- IIA, [Global Code of Ethics](https://www.theiia.org/en/standards/what-are-the-standards/mandatory-guidance/code-of-ethics/) —
  §9.3 (Rule 2.3: disclose material facts that would distort the reporting) and §9.4 (Rules
  2.1–2.3: no activity that "may impair or be presumed to impair their unbiased assessment").
- 17 CFR [§ 240.12b-15](https://www.law.cornell.edu/cfr/text/17/240.12b-15) (amendments must
  carry the complete amended text, be numbered, and be filed separately — the original is never
  revised) and 17 CFR [§ 240.17a-4(f)(2)(i)](https://www.law.cornell.edu/cfr/text/17/240.17a-4)
  (an electronic recordkeeping system keeps either a complete time-stamped audit trail that can
  re-create the original record, or records in a non-rewriteable, non-erasable format) — §9.3.
