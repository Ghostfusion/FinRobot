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
- **the contract gate** — clause `C10e` walks `checked_identities()`, resolves each identity's
  declared artifact paths against the artifact's **own leaves**, and reports a residual above
  `IDENTITY_RESIDUAL_TOLERANCE`. It replaces the hand-written `_RATIO_IDENTITIES` tuple, so a
  new published quantity is covered the moment it is declared.
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
  not stated arithmetic we can contradict. The tolerance is still a relative constant rather
  than precision-derived — our leaves round per field at display time, and a field-declared
  digit count is the follow-up that would close that gap.
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
| `operating_margin` | 65 | 22 | 39.4% | **all pre-fix or stale-cache**: DVN/TROW/EXE/FOXA/NFLX published the vendor's `info.operatingMargins` scalar (41.1% beside operands giving 24.9%), the CF class; the newest artifact per ticker is clean |
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
- **Tolerance is a relative constant** (`IDENTITY_RESIDUAL_TOLERANCE = 0.01`), not derived from
  published precision as XBRL does. Field-declared display precision is the follow-up.
- **Per-year preferred/NCI are not fetched** for the historical band: the samples apply the
  RUN's claims (declared `on_missing="zero"`, the assumption `audit.ev_bridge` already flags as
  unverifiable). What changed is that the samples and the band's current marker now evaluate the
  SAME identity; a per-year fetch would retire the assumption.
- **`_LATEST_TOTAL_ASSETS_CONCEPTS` still lists `AssetsCurrent` as a fallback** — current assets
  read as *total* assets is the same class of caliber error as the identity-total defect, but it
  fires only for a filer that tags neither `Assets` nor `TotalAssets`. Noted, not fixed
  (unmeasured, and outside this change's scope).

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
- `scripts/sweep_identities.py` — the standing measurement (populations, violations, worst
  residual per identity). Run it before adding an identity or changing a tolerance.
- The contract fixtures are unchanged (16/16 byte-identical after the generalization): no
  stored artifact's verdict moved.
