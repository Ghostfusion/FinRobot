# One identity, one evaluator — the numeric derivation architecture

Status: **implemented** (2026-10-14/15). Supersedes the ad-hoc "clause per discovered bug"
approach for published arithmetic; see `REPORT_INVARIANT_CLOSURE_DESIGN.md` for the clause
family this plugs into and `CF_AUDIT_REMEDIATION.md` for the audit that forced it.

---

## 1. The problem this removes

The audited CF report published **two answers for one multiple** — a $86.40 EV/EBITDA method
mid beside a $65.44 own-history cross-check, and a 4.9× price-implied multiple beside a 5.7×
"current" one — because one identity was written out in five places:

| Site | What it did |
|---|---|
| `multiples.calculate_ev` | `market_cap + total_debt − cash + preferred + NCI` |
| `multiples.current_ev_ebitda` | the same sum, re-written inline, over EBITDA |
| `multiples.ev_band_equity_per_share` | `ev − net_debt − preferred − NCI`, inline |
| `dcf.equity_bridge_value` | the same bridge again, claiming "single authority" |
| `sotp.compute_sotp_breakdown` | `ev_floor − net_debt` — the claims **missing** |
| `historical_valuation._compute_multiple` | `(market_cap + net_debt) / ebitda` — the band's own samples, on a *different* identity than the band's current marker |

and documented a third way (`technical_payload.py:198`, `equity_research.py:1243` and
`routes/valuation.py:511` all describe EV/EBITDA as `(market_cap + net_debt) / EBITDA`).

No provenance record can catch that: every figure is individually traceable and the
arithmetic still disagrees. The contract family had grown a clause per discovered bug
(C10a presence, C10b one provider, C10c identity, C10d caliber — and only then C10e
arithmetic) and still shipped the CF margin.

## 2. The change

**Every published arithmetic relationship is DECLARED once, evaluated once, and the gate walks
the declarations.**

```
finrobot/engine/models/identities.py     ← the registry (leaf: stdlib only, zero I/O)
├── QuantityKind   per_share | total_amount | ratio | multiple | rate | count
├── OperandRole    component | total | gate | identity
├── Identity       id · total · kind · form(sum|ratio|product) · contributors(weight, role,
│                  on_missing) · divisor · artifact paths · clause coverage
├── LEAF_KINDS     published leaf path → kind
├── IDENTITY_TOTAL_CONCEPTS + is_identity_total()
├── evaluate() · binds() · relative_residual() · artifact_operands() · leaf_paths() · dig()
└── REGISTRY_VERSION · identity_digest()
```

Consumers, none of which re-derive anything:

- **compute operators** — `calculate_ev`, `current_ev_ebitda`, `ev_band_equity_per_share`,
  `implied_ev_multiple`, `dcf.equity_bridge_value`, `sotp.compute_sotp_breakdown`,
  `historical_valuation._compute_multiple`. Each keeps its signature (so no caller churn) and
  its body becomes `evaluate(<id>, {...})`.
- **the contract gate** — clause `C10e` walks `checked_identities()` (the identities the artifact
  publishes a total for), resolves each identity's declared artifact paths against the artifact's
  **own leaves**, and reports a residual above the band its figures' declared precision allows
  (`identity_tolerance`, falling back to `IDENTITY_RESIDUAL_TOLERANCE` and saying so). It replaces
  the hand-written `_RATIO_IDENTITIES` tuple, so a new published quantity is covered the moment it
  is declared.
- **the drift scrubber** — `LEAF_KINDS` decides whether a prose $-amount is a restatement of a
  published TOTAL (never rewritten) or a per-share figure (may be rewritten).
- **the claim ledger** — `NumericClaim.kind`, from `LEAF_KINDS`.
- **the cache** — `identities.identity_digest()` is part of the canonical slot key, beside the
  provider-semantics digest (§5).

### Why these shapes (primary sources)

- **XBRL Calculations 1.1** (`https://www.xbrl.org/Specification/calculation-1.1/REC-2023-02-22/`)
  is the battle-tested form of "a published total must equal its own components": total concept
  + contributing concepts + contribution **weights**, checked only where the calculation
  **binds** (§5.1 — the total and its contributors are present), with the tolerance derived from
  the fact's own declared precision (§5.2.3-5.2.4). We adopt the structure, the weights, and the
  binding rule; we are deliberately **stricter** than `binds` (all operands required, not "at
  least one"), because a report that publishes a total beside one of its three components has
  not stated arithmetic we can contradict. We adopt the precision-derived tolerance as well:
  every leaf declares the precision its value is asserted accurate to beside its KIND
  (`DEFAULT_DIGITS`, XBRL's `decimals`), and `identities.identity_tolerance()` accumulates half a
  unit in each contributing last digit through the identity's form, so the same declaration
  governs a 5.7x multiple and a 0.39 margin. `IDENTITY_RESIDUAL_TOLERANCE` survives as the band
  NAMED when a leaf declares no precision (§4).
- **OpenLineage `columnLineage`** (`https://openlineage.io/docs/spec/facets/dataset-facets/column_lineage_facet/`)
  is the same idea at dataset granularity: per output field, `inputFields` with a
  `transformation` type DIRECT/INDIRECT. Our `OperandRole` carries the same distinction —
  `component` moves the value, `gate` only decides whether two numbers are comparable at all.
- **Avro schema resolution** (`https://avro.apache.org/docs/1.12.0/specification/`) and
  **protobuf "Updating a Message Type"** (`https://protobuf.dev/programming-guides/proto3/`)
  supply the cache rule in §5: data must be read with the schema that WROTE it, defaults only
  fill *absent* fields, and the wire format "doesn't provide a way to detect fields encoded
  using one definition and decoded using another".
- **F# units of measure** (`https://fsharp.github.io/fslang-spec/units-of-measure/`) is why the
  kinds are data rather than only types: measures are checked statically and **erased** at
  runtime, which is free inside our typed compute layer but useless at the JSON boundary where
  providers hand us untyped payloads.
- **SR 26-2, *Revised Guidance on Model Risk Management* (2026-04-17**, superseding SR 11-7)
  is the supervisory analogue, not an obligation: the guidance explicitly excludes "simple
  arithmetic calculations". Its structures map onto this one — model **inventory** → the
  registry; **aggregate risk** ("reliance on common assumptions, data, or methodologies") →
  identities that share operands; **effective challenge** → a gate with standing to change the
  output; **outcomes analysis** → the corpus sweep; **vendor validation** → declared provider
  field semantics.

## 3. Measurement (P0) — the population, before and after

`scripts/sweep_identities.py` runs the registry over every stored artifact (`artifacts.db`,
read-only; the same code path the gate uses). Run 2026-10-15 against 141 artifacts
(134 `equity_research`, 7 dcf/comps/ddm/lbo/fund):

| identity | bound | violated | worst | reading |
|---|---|---|---|---|
| `ev_build` | 134 | 0 | — | the EV sum holds to the dollar on every artifact that publishes it |
| `ev_ebitda` | 132 | 0 | — | the EV/EBITDA beside it is its own EV, not a net-debt-only twin |
| `ev_revenue` | 134 | 0 | — | same |
| `pe_ratio` | 139 | 26 | 8.7% | **all pre-fix**: `market.pe_ratio` predates the cap÷net-income derivation (the 26 carry `pe_basis: null`; every artifact since 2026-10-13T17:3x that declares the basis is exact) |
| `operating_margin` | 65 | 22 | 39.4% | **all pre-fix or stale-cache**: DVN/TROW/EXE/FOXA/NFLX published the vendor's `info.operatingMargins` scalar (41.1% beside operands giving 24.9%), the CF class; the newest artifact per ticker is clean. The PRODUCER was closed on 2026-10-15 (`extractor` derives the ratio from the block's own leaves, §8) — stored rows keep their published margin, so this column only shrinks as artifacts are re-run |
| `ebitda_margin` | 0 | 0 | — | not published as a leaf — declared, never binds (honest no-op) |
| `ev_to_equity` | 0 | 0 | — | compute-only: no artifact path, enforced where it is used (§6) |
| `net_debt` | 0 | 0 | — | nested operand, resolved through its two balance leaves |
| `market_cap` | exempt | — | — | see §4 |

Two things the measurement bought:

1. **Confidence to enforce.** `ev_*` identities are exact on 100% of artifacts, so making the
   gate walk them cannot produce noise.
2. **A catch the hand-written list missed.** The generalized clause fires on
   `art_2026-10-12T15:57:35_EHC` for `market.pe_ratio = 20.4867` against
   `market_cap / net_income = 20.1539` — a ratio contradiction the four-entry
   `_RATIO_IDENTITIES` tuple never looked at, because nobody had added it. That is the
   mechanism working: coverage comes from the declaration, not from a bug report.

## 4. Deliberate exemptions and non-goals

- **`market_cap` is declared but EXEMPT from the gate.** Yahoo derives `marketCap = shares ×
  price` and FMP rederives the count as `marketCap / price`, so a residual is a **clock**
  difference between two independently cached canons, not an error (CF: the cap implied
  $117.25 against a $119.46 close — 1.88%, exactly the "last session" move the report prints).
  It is enforced where the vintages are known — `coordinators/extractor` discloses a >1%
  divergence against the resolved quote. Registering it keeps one declaration of the product;
  `clause="exempt"` records why the gate does not walk it, instead of leaving a reader to
  wonder.
- **No per-artifact edge list.** The recommendation also floated publishing the derivation
  edges inside each artifact. The registry plus path-resolution makes an artifact checkable
  from its own leaves *without* a second copy of the declarations in the payload: the gate
  reads the registry, and the artifact supplies the numbers. Publishing edges would add bytes
  per artifact and a second thing to keep in sync, and no consumer needs them today. The
  reconciling fact is recorded on the payload — `NumericClaim.kind` says what each claimed
  number IS — and `identity_digest()` says which arithmetic the cache and the decisions were
  made under. If a consumer ever needs "this number came from that formula with those operands",
  the registry already answers it by id.
- **Tolerance is derived from declared precision** (2026-10-15), not a flat 1% band: each leaf
  declares the precision its value is asserted accurate to (`DEFAULT_DIGITS` by KIND — whole
  dollars, the cent for a quote, 4 decimals for a ratio — with `LEAF_DIGITS` for an exception),
  and `identity_tolerance()` accumulates half a unit in each contributing last digit through the
  identity's form. A rounding-level difference passes; a SMALLER contradiction than the flat band
  would have excused is now caught. `IDENTITY_RESIDUAL_TOLERANCE` is only the band a caller NAMES
  when a leaf declares no precision, and the C10e finding says which of the two it judged against.
  Measured 2026-10-15 over 142 stored artifacts (609 bound checks): **63 caught** at the
  declared-precision band against **48** at the coarse 1%. The 15 extra are sub-1% caliber
  mismatches the flat band excused — a KGC operating margin 0.8179% off its own
  `operating_income / revenue`, INVH 0.2478%, MLI 0.2282% (all three carrying the post-fix
  `pe_basis` note, so not the *pre-fix* scalar defect — but the SAME defect class one order of
  magnitude down: the provider's margin divides its own TTM frame revenue while the block prints a
  canonical `revenue` leaf, which the producer side now derives away, §8), plus ten pre-fix P/E rows
  whose provider ratio rode a different denominator. `ev_build`, `ev_ebitda` and `ev_revenue` stayed at ZERO caught at the
  tighter band — the clock difference the EV build discloses is not mistaken for a contradiction
  (its published $2.2e10 total is asserted accurate to the dollar, so the band is ~1e-10 relative).
- **Per-year preferred/NCI ARE fetched** for the historical band (2026-10-15): both providers'
  annual-history rows now carry `preferred_stock` / `noncontrolling_interest` per fiscal year (FMP
  already emitted them off its annual balance-sheet statement; yfinance reads them off the annual
  frame it already held, with `None` for a row the statement omits), the loader FX-scales them
  exactly like net debt, and `_compute_multiple` uses the YEAR's claim with the run-level figure as
  the fallback. The declared `on_missing="zero"` is now a per-year fallback rather than a blanket
  assumption: what `audit.ev_bridge` flags as unverifiable is one year whose statement omits the
  row, not every year of the window.
- **`_LATEST_TOTAL_ASSETS_CONCEPTS` no longer lists `AssetsCurrent` as a fallback** (fixed
  2026-10-15). Current assets read as *total* assets was the same class of caliber error as the
  identity-total defect and it fired only for a filer that tags neither `Assets` nor `TotalAssets` —
  whose equity identity built from it closed anyway (a partial standing in for the total is
  invisible to the arithmetic). The component is gone from the list, so such a filer now abstains:
  `latest_total_assets` stays absent, `_equity_identity_note` takes its `None` arm and the missing
  leaf is the capability warning's business — never a smaller magnitude published as the total. The
  asset, liabilities and equity lists now carry the same import-time refusal against
  `engine/models/identities.IDENTITY_TOTAL_CONCEPTS` (`is_identity_total`), so an identity total
  cannot re-enter a single-side slot. `AssetsCurrent` itself has no vocabulary to guard it — it is a
  COMPONENT, not an identity total — so the list is the only place that defect can be prevented.

## 5. Cache semantics (P4) — why a fixed build still shipped a stale number

The yfinance margins became frame-derived on 2026-10-14 (commit `4e1a75f`), yet the audited
report — generated 9 h later — was built from a canonical payload cached **14 h before** that
commit, under a 24 h TTL and an unchanged version tag. The tag was hand-maintained, so nothing
forced the author to notice the meaning had moved.

`cache.raw_slot_key` / `canonical_key` now carry a **derived** digest:

```
<type>:v<rev>-<semantics_digest(type, provider)>          raw slot
<type>:canonical:v<CCV>-<semantics_digest(type)>-<identity_digest()>   canonical slot
```

`semantics_digest` hashes the declared **field semantics** for that type/provider (unit, caliber,
basis) together with the SHA-256 of the producing provider module's source — so **any** provider
edit, down to a comment, moves the key and old rows miss instead of being re-normalized. The
human revision (`rev`, the old `_RAW_SLOT_VERSION` values and their incident-log comments) is
preserved for readability; `CANONICAL_CONTRACT_VERSION` is unchanged in role. The pin gate
(`tests/audit/test_provider_cache_payload_pins.py`) now pins the ACKNOWLEDGED digest per
(data_type, provider), so a provider edit still forces an explicit "did a cached row's meaning
move?" decision — by failing loudly rather than by remembering.

## 6. Operand roles (P3) and declared UI states (P5)

- **Roles.** `OperandRole.total` is refused as an operand by `_sum` (a total of another identity
  is not a component), and `IDENTITY_TOTAL_CONCEPTS` + `is_identity_total()` own the vocabulary.
  `edgar_provider` validates its liabilities concept list against it **at import**, so the tag
  that published NCI of −$5,748,000,000 (because `LiabilitiesAndStockholdersEquity` equals
  Assets by definition, making `assets − liabilities = 0` close) cannot be re-added by hand.
- **Declared states.** Two published sentences asserted a property of a NUMBER that the
  renderer inferred from magnitude:
  - `MarketImpliedCheck.premium_driver ∈ {growth, discount_rate}`, computed once in
    `dcf._premium_driver` — the cover branches on it (legacy payloads keep the local
    `implied_growth < 0` fallback);
  - `assumption_provenance["beta_basis"] ∈ {raw, blume}`, written where the Blume decision is
    actually made (`dcf_seed`). It cannot ride `raw_data.market`: the basis is decided in
    financial_modeling, AFTER data_collection froze the snapshot — and the tile that said "DCF
    uses a Blume-adjusted β" with no threshold had a reader computing 0.69 for a WACC that used
    the raw 0.527.

## 7. Verification

- `tests/unit/test_identity_agreement.py` — the structural claim: for an issuer carrying
  preferred AND NCI, `calculate_ev`, the DCF bridge, the band row, the band's samples, the SOTP
  floor and the artifact reader all return the SAME number; the implied-multiple round trip
  returns its input; a missing balance leg is not a zero; an identity total cannot be read as a
  component.
- `tests/unit/test_identity_tolerance.py` — the band itself: a margin rounded to its declared
  precision passes, a 0.5% contradiction is caught (the coarse 1% band excused it), the audited CF
  margin still fires with the band NAMED in the evidence, every leaf of every walked identity
  declares its kind AND its precision (the `valuation.ebitda_operating` gap this test now holds
  shut), and an identity whose leaf declares no precision falls back and says so.
- `scripts/sweep_identities.py` — the standing measurement (populations, violations, worst
  residual per identity), judging every identity at BOTH the declared-precision band and the
  coarse `--tolerance` band so the delta is visible. Run it before adding an identity or changing
  a tolerance.
- The contract fixtures moved by DESIGN, in the recorded verdict map only: of the 16, one line
  changed — `art_2026-10-12T21-39-32_AMZN_1749e7`'s `C10e` verdict flipped `false → true`,
  because that pre-fix artifact publishes `market.pe_ratio = 20.8793` against its own
  `market_cap / income.net_income = 20.693` (0.9% apart, against the 0.02% band its declared
  precision allows — and under the flat 1% band that used to excuse it; it carries
  `pe_basis: null`, i.e. the provider's EPS-denominated ratio). No payload byte changed:
  `scripts/extract_contract_fixtures.py` rewrote the verdicts and the diff is that one clause on
  that one fixture.

## 8. Producer-side closure (2026-10-15) — the identity must hold by construction

The gate can only ever *report* a contradiction; the defect it keeps finding is a producer that
publishes a ratio and its operands drawn from two different sources. Three producers were closed
and one name was fixed:

- **The operating margin is derived from the block's own leaves** (`coordinators/extractor` — the
  `pe_ratio` precedent, one field over). A provider's margin divides its OWN TTM frame's revenue,
  which is not the `income.revenue` leaf the same snapshot prints: live KGC published
  `operating_margin` 0.52478004 beside `4,409,000,000 / 8,470,900,224 = 0.52048777` (its frame
  revenue was 8,401,615,275, 0.8% away), and the audited CF run published 0.49325 beside 0.39088.
  The ratio is now `operating_income ÷ revenue` from the very fields the income block publishes,
  and `IncomeStatement.operating_margin_basis` names the numerator's authority. The provider's own
  value survives only as the LABELLED fallback (a snapshot with no operating income to divide);
  the label also names the superseded provider value once the two differ by more than
  `_OPERATING_MARGIN_SUPERSEDE_TOL` = 0.1% — not the P/E's 1%, because a 1% cap vintage is noise on
  a 20× ratio while a margin's caliber gap is 0.23–0.82% and the printed figure carries one decimal
  of a percent. The registry's `operating_margin` note now names that field, so the declaration says
  where the basis lives (`tests/unit/test_extractor_margin_authority.py`). The rule lives in ONE
  function, `extractor.derive_operating_margin`, because three publishers need it: the artifact's
  income block (label kept), the comps PEER row (`extract_company_financials`, label discarded — a
  comps row has no provenance block), and `override_company_with_xbrl`, which re-derives it when the
  XBRL adoption has moved `revenue`, the last point at which both figures are final. A second
  implementation of the same ratio is how the two sides drift.
- **The ASC-606 revenue SUBSET declares its caliber where it becomes a denominator.** A
  post-ASC-606 filer (AAPL/MSFT/GOOGL) tags no `Revenues` total, so
  `RevenueFromContractWithCustomer*` is the only revenue its filing carries — correct to use, and
  still NARROWER than a peer's total: any non-ASC-606 top line (interest, premiums, leasing) sits
  outside it. `xbrl_aligned_comps._asc606_subset_revenue_note` appends that sentence to the peer
  row's `ttm_divergence_note` (→ `PeerComps.warnings`) when the ADOPTED XBRL TTM revenue is the
  subset — and only then, because a rejected subset figure is not the number the row divides by. No
  arithmetic change; the subset concept stays in the lists (its rank is last, so it is used only
  when no total exists).
- **A ratio-capable synonym cannot enter a dollar leaf unit-less.** `GrossMargin` is not a us-gaap
  element, so it can only match a filer extension — and that name commonly holds a RATIO. It now
  needs an explicit USD unit (`_GROSS_PROFIT_UNIT_STRICT_CONCEPTS` →
  `_is_usd_unit(require_explicit=True)`), so a unit-less or `pure`-tagged `GrossMargin` abstains
  (the slot stays None and the gross-margin caliber falls to its declared provider_scalar/withheld
  path) instead of publishing 0.42 as $0.42M. The us-gaap element in the same slot (`GrossProfit`)
  keeps the lenient missing-unit default: the rule is per CONCEPT, because edgartools omits the
  unit on cleanly-typed currency facts often enough that refusing those would drop good US data.
- **Naming only.** `_HIST_FCF_CONCEPTS` held *financing*-activity concepts and fed
  `financing_cash_flow` (the slot was always right, the variable name was not) — renamed to
  `_HIST_FINANCING_CONCEPTS` / `financing`, so the next reader cannot wire financing flows into a
  free-cash-flow leaf. A real FCF is OCF − capex, i.e. `_HIST_OCF_CONCEPTS` less
  `_HIST_CAPEX_CONCEPTS`, which is what the DCF already uses.
