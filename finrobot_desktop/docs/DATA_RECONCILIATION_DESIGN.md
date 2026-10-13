# Data reconciliation & metric authority — design

Status: **accepted** (owner-pasted policy, implemented this session).
Scope: `finrobot_desktop/finrobot/` (V2 engine).

> **Security.** This document names environment variables and public vendor URLs only.
> It never contains a credential value. See `DATA_PROVIDERS_V3_DESIGN.md` §10.

---

## 1. Problem

The data layer fetches one metric from several vendors and had no formal record of what it
decided. `engine/data/validator.py` compared the primary vendor's dict against a second
vendor's dict and emitted prose; `engine/models/metric_authority.py` declared a producer of
record per published number and published conflicts instead of averaging them — but the two
halves were not joined:

- the comparison never checked that the two numbers were the **same metric on the same
  basis** (a period or caliber gap produced a numeric "conflict" that no one could classify);
- the **alternatives were discarded** — nothing recorded which value was selected, what else
  was available, or on what grounds one won;
- **validity and freshness were not gates**: a stale or non-finite preferred value was still
  the canonical answer, and a stale value could beat a fresh, valid alternative;
- tolerances lived in **two places** (`validator._RELATIVE_FIELDS`, the leaf registry's
  `METRIC_TOLERANCE_PCT`) and "we do not compare this field" was recorded as an **omitted
  field with a prose explanation** rather than a declaration;
- nothing gated on **knowledge time**, so a backtest could see a correction the run could not
  have known;
- agreement between two variants of the SAME vendor (or a value **derived from** the other)
  counted as confirmation.

## 2. Locked decisions

| Decision | Choice |
|---|---|
| Where the policy lives | The existing leaf registry `engine/models/metric_authority.py` — ONE row per metric, ONE tolerance home. No second registry. |
| Where the engine lives | Same leaf module (pure, stdlib, no I/O) so `engine/data`, `engine/compute/operators/audit` and `artifact/` can all consume decisions. |
| Where observations are built | `engine/data/authority.py` — the only layer that sees provider results. |
| Canonical selection | By **producer identity** (registry `producer_id` → `calibers` → fallbacks), never by dict order, never by argument order, never by averaging. |
| A fallback | Only when the owner observation is **ineligible** (non-finite / non-positive / stale / after the run's as-of), and the decision then says `status="fallback"`, `is_authoritative=False`, with the reason. The leaf's `resolve_metric` promise ("a fallback is never promoted to canonical") is preserved — a fallback is disclosed, not promoted. |
| Conflicting but valid | Publish the canonical AND the disagreement (`status="conflict"`, `disagreement_pct`, every candidate's deviation). Never withhold a valid number on a conflict. |
| Different caliber by construction | Declared in the row (`comparability="caliber_divergent"`), so EBITDA / total debt / margins never raise a spurious conflict — the finding that used to live as prose in the validator's docstring. |
| Fail closed | No eligible observation ⇒ `status="unavailable"`, `value=None`, with the reason. Never `0`, never a neutral default, never a blend of incompatible observations. |
| Basis labels | Typed fields, never `warnings` (coverage computes `partial = any(row.warnings)`). |

## 3. The decision order (deterministic, no LLM in the loop)

1. **Semantic compatibility** — group observations by the row's `comparability` class and its
   key (`unit` + `currency` + `period_end` + `period_basis`; session date for prices). A
   non-matching observation is reported as `definition_mismatch_period` / `_currency` /
   `_unit`, never compared numerically.
2. **Hard validity** — non-finite, non-positive where the metric is positive-valued, stale
   beyond the row's `freshness_max_age_s`, or **published after the run's as-of** ⇒
   ineligible, each with its own reason code. The as-of gate reads the SOURCE's knowledge
   time (`published_at`) only: `retrieved_at` is when *we* looked, which is after the run
   started by construction (every live run sets the ceiling to its own start instant), so
   gating on it excluded the entire live data set — measured: EHC 2026-10-13 came out with
   eight `unavailable` decisions and a caveated artifact on a healthy fetch.
3. **Source authority** — the eligible observation that is the registry's producer of record
   wins; if it is ineligible, the best eligible alternative wins as a disclosed `fallback`.
4. **Freshness & quality** — expressed through rule 2's gates plus rule 3's fallback: a
   preferred provider's stale or invalid value never silently beats a fresh valid one, and
   the fallback is named.
5. **Disagreement** — per metric: relative deviation, plus an absolute test when the row
   declares `tolerance_abs`. Over tolerance ⇒ `conflict` + the candidate's deviation. This is
   a *screening* statistic, not a claim that the number is wrong.
6. **Fail closed** — nothing eligible ⇒ `unavailable`.

Independence: a candidate that collapses to the same canonical source id as the selected
observation (cache variants of one vendor, registry-id aliases) or that is `derived_from` the
selected source is marked non-independent, and a decision whose only agreement is
non-independent says `agreement_is_independent=False`.

## 4. What is published

- **Per observation** (`MetricObservation`, in-memory): source, value, unit, currency,
  period end/basis, effective/retrieved/published time, derivation lineage, quality flags.
- **Per metric** (`MetricDecision`, persisted): status, value, selected source,
  `is_authoritative`, reason code, policy version, definition version, the row's basis,
  comparability class, both tolerances, period, `disagreement_pct`,
  `agreement_is_independent`, and **every** candidate with its own reason and deviation.
- **Per run** (`ReconciliationReport`): policy version, the run's as-of, and all decisions.

These ride the canonical contracts (`Provenance`-stamped `Normalized*` snapshots) into
`FinancialData.data_authority` and therefore into the artifact's `raw_data`, so a stored
report can always answer *which provider supplied which number, and what else was on the
table*. An append-only log (`~/.finrobot/metric_authority/<SYMBOL>.jsonl`) records one line
per fetch for cross-run disagreement tracking.

## 5. How it reaches the reader

- Prose: one line per non-clean decision, prefixed `Data authority:`, added to the run's
  warnings.
- Structured: `structured.numeric_audit` findings (`metric_authority_conflict`,
  `metric_authority_unavailable`, `metric_authority_definition_mismatch`, severity
  `review`), rendered by the existing audit banner. A conflict **annotates** (artifact
  `caveated`); it never withholds a price target — the canonical value is still published,
  which is the thing the conflict is measured against.

**Where each record is published.** One fetch produces up to two reports — the FINANCIALS
slate (revenue, net income, cash, market cap, shares, EBITDA, debt, margin) and the PRICE
slate (current price, and only that). The artifact publishes the **FINANCIALS** report as
`raw_data.data_authority` (the panel and the findings read that block); the PRICE decision
rides its own canonical snapshot (`NormalizedPrice.reconciliation`) and the append-only log,
and the price's reader-facing provenance stays where it already was: `MarketData.provenance`
(`provider` + `as_of` + `degraded`), `quote_is_live` / `quote_as_of`, and the
`price_field_divergences` → `price_divergence:<field>` marker when two feeds disagree. Both
reports are in `~/.finrobot/metric_authority/<SYMBOL>.jsonl`. Publishing the price decision
in the artifact as well (a `MarketData.data_authority` field) is the obvious next step and is
NOT done here — the price's provider and basis are already published fields, so nothing is
hidden; only the agreement dimension is reported through the marker rather than the panel.

## 6. Not implemented (deliberate, with reasons)

- **No dashboard.** The cross-run log has a programmatic reader (and tests) but no UI; the
  per-run decision record is what the reader sees. A dashboard is a product decision.
- **No ensemble/median across providers.** The policy allows one only for metrics with
  validated definitions, independence and error behaviour; nothing in this repo meets that
  bar today, so a majority vote is not implemented on purpose (§4 of the policy).
- **No automatic correction of a "wrong-looking" value.** A conflict is published, never
  repaired by argument. Metrics whose providers genuinely measure different things are
  declared `caliber_divergent` instead of being loosened into agreement.
- **Knowledge time for vendor reads is best-effort.** `published_at` is only known for
  filing-backed reads; a vendor statement read carries `published_at=None`, so the as-of gate
  cannot fire for it at all. Using our own retrieval time instead is not a substitute — it is
  after the run started by construction, and doing so excluded every observation of every live
  run (measured: EHC 2026-10-13, eight `unavailable` decisions on a healthy fetch). A vendor
  revision that postdates a simulated decision point is therefore not detectable from what we
  store; that is the honest limit, stated rather than papered over.
