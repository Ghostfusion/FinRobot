# Corporate Finance & Investment — learnings from the q-fin.GN corpus

`303` of 3095 corpus papers matched this category (299 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category's tradable core is one prediction model and one valuation protocol.** Four of the six
papers are corporate-finance context, not signals: a paired pre/post ratio test on six Indian bank mergers
(arXiv:2308.16054), a cognitive literature review of CSR and governance (arXiv:2102.09218), a
2,000-reference essay on M&A in "diffusion-type" systems (arXiv:1502.02537), and an LLM benchmark for IPO
diligence (arXiv:2606.23032). The two constructions with implementable operators are a deep-learning
deal-level M&A predictor (arXiv:2404.07298) and a milestone-gated real-options overlay whose probabilities
come from AHP scoring (arXiv:2609.24181). Everything else is either an event study needing
as-reported point-in-time fundamentals the catalog does not serve, or a due-diligence *analysis* pipeline
whose output is a rubric score rather than a return. The single binding data gap for this category is
**point-in-time fundamentals**: the catalog's `fundamental_data` rows return current statements, not the
as-reported, restatement-aware history that every M&A value test here presupposes.

## 1. What the corpus actually offers

- **Deal-level M&A prediction has a measurable but thin lift over logistic regression.** On 1997–2019 deal
  data, a Temporal Dynamic Industry Network (TDIN) reaches AUC 0.5819 versus 0.5451 for Palepu's acquisition
  likelihood model — a **6.6% relative increase** (arXiv:2404.07298). Both are close to 0.5; the paper's own
  framing is that the model's value is *deal-level, continuous-time, per-target recommendations*, not raw
  discrimination power.
- **The TDIN components were ablated, and the network matters most.** Full model AUC 0.5819; remove the dynamic
  industry network → 0.5492 (−5.62%), remove the GNN choice module → 0.5541 (−4.78%), remove peer-effect
  modelling → 0.5557 (−4.50%), remove 10-K textual embeddings → 0.5603 (−3.71%), remove the RNN timing module
  → 0.5685 (−2.30%) (arXiv:2404.07298). Training data: SDC Platinum M&A events, Compustat accounting variables,
  SEC 10-K Item 1 "Business Description" text, and Hoberg–Phillips TNIC industry classifications; observation
  window 1997–2020; **385 "frequent acquirers"** defined as firms with ≥4 deals.
- **The M&A predictor needs no resampling.** Sparse positive pairs are absorbed into the point-process
  intensity rather than fixed by oversampling, which the paper argues removes a bias source in prior deal-level
  work (arXiv:2404.07298). Event definition is explicit: majority takeover, >20% of target shares acquired,
  >50% held post-transaction, deal value >USD 1m, excluding block purchases, creeping acquisitions and
  privatisations.
- **Milestone-gated real options decomposes an opaque growth assumption into auditable pieces.** Firm value
  splits as $V_0=V_{\text{DCF}}+V_{\text{AI}}$, and each AI milestone's conditional value into five
  components (arXiv:2609.24181). In the single demonstrated case (an anonymised Swiss AI-native energy-SaaS
  firm, "E12", CHF 100m pre-money), the AI overlay supplies CHF 95m of the CHF 100m total, and **M4 — the
  24-month reproducible-go-to-market option — drives >60% of the CHF 77–123m scenario band** (|δw| = 11.7 of
  a 46m range); deleting M4 alone collapses $V_{\text{AI}}$ from 95m to ≈50m.
- **The real-options paper is a protocol, not a validation.** Its own words: "a single-firm demonstration of
  protocol coherence, not empirical validation", with multi-case testing against realised post-exit
  valuations left to future work (arXiv:2609.24181). The CHF 100m base case matches the firm's disclosed
  pre-money *by construction* (inputs were taken from the masterplan).
- **IPO due diligence is a document-length problem as much as a reasoning problem.** The Finance Agent v2
  harness "basically failed to deliver any output" on the SpaceX S-1 because of filing length; replacing naive
  chunk retrieval with contextual retrieval (document-aware chunk prefixes before embedding) was the enabling
  change (arXiv:2606.23032). Best evaluated model GLM-5.2 scores **79.8%** on 70 public SPCX questions; the
  cost-efficient point MiMo-2.5 Pro scores 77.2% at **$0.05/query**, versus the FABv2 leaderboard ceiling of
  57.9% at $2.51/query. Governance slices are thin ($n=4$; n=5 for investment banking/ECM) and EBITDA-grade
  claims are unsupported below that sample size.
- **The LLM benchmark's weakest domain is valuation.** Valuation and underwriting is the lowest-scoring domain
  for four of six models (55.9–75.4%), and the authors attribute the high overall scores to harness quality
  rather than easier questions, explicitly flagging that the contextual-retrieval ablation was not run
  (arXiv:2606.23032). Scores also carry a same-family evaluator bias: the top model and the GLM-5.1 evaluator
  share a model family.
- **Post-merger financial ratios move only on profitability, and the test is under-powered.** Six Indian bank
  mergers, two years pre versus two post, paired t-test: ROE 0.0724→0.0779 (t=2.5272, p=0.0263), ROA
  0.0037→0.0043 (t=2.2509, p=0.0370), NIM 0.0641→0.0472 (p=0.4998, not significant), debt/equity
  0.6868→0.5608 (p=0.4999, ns), capital ratio 0.1268→0.1232 (p=0.4999, ns) (arXiv:2308.16054). The paper's
  own table reports EPS means falling (23.34→19.95) while the text calls the change "a significant
  improvement" — an internal inconsistency that is itself the lesson: do not trust a stated direction when
  the table contradicts it.
- **M&A volume is asserted to be quasi-periodic and polynomially approximable.** The diffusion-type paper
  claims the average of a sum of random numbers in an M&A-count time series produces quasi-periodic
  systematic oscillations "finely approximated by polynomial numbers", with ideal/linear/quadratic/exponential
  nonlinearities studied in MATLAB; it reports the 2006 worldwide record of USD 3.79tn, +38% over 2005
  (arXiv:1502.02537). No dataset, sample size, period estimate or fit statistic is given — this is a claim to
  test, not a result to deploy.
- **CSR–governance evidence is deliberately reported as mixed.** A review of >200 CSP–CFP studies finds
  positive, negative and null results, with endogeneity in SEM/regression specified as the main reason for the
  ambiguity (arXiv:2102.09218). Representative descriptive anchors it cites: French SBF120 boards 2003–2016
  (937 firm-years) have mean board size 12.89 (SD 3.53), 52.5% independence, 33.6% CEO duality, 22.2% female
  directors; a CSR committee exists in 63% of 4,013 firm-year observations across 13 European countries
  (2002–2016), and at least three female directors are associated with higher environmental-strength scores.
- **Off-topic notes.** None of the six is filed under a wholly different subject, but three are
  off-topic *for trading*: arXiv:2102.09218 (no estimator, no data — retained as a governance-factor
  rationale), arXiv:1502.02537 (no reproducible numerical result — retained as the category's only
  cycle-timing hypothesis), and arXiv:2308.16054 (six events, non-US, no returns — retained only because it
  is the corpus's canonical pre/post M&A ratio test). arXiv:2606.23032 sits in `cs.AI` rather than `q-fin.GN`
  in the metadata but is a finance-domain benchmark and is retained.

## 2. Implementable formulas & algorithms

### 2.1 Temporal Dynamic Industry Network (deal-level M&A prediction)
**Purpose.** Predict *when* a frequent acquirer makes its next acquisition and *which* firm it acquires,
as a per-acquirer, per-target hazard rate, without resampling or ad-hoc time binning.

**Formula.** Decompose the per-target intensity into timing × choice:
$$\lambda_d(t,v\mid H_t)=\lambda_d(t\mid H_t)\,P_d(v\mid t),\qquad \sum_{v\in V^t}P_d(v\mid t)=1 .$$
The timing intensity uses an additive base rate plus a decaying shift,
$$\lambda_d(t)=f_\lambda\!\big(w_e^\top e^{td}+w_c^\top c^{td}+\omega(t-t_d^-)\big),\qquad
\omega=w_{o1}e^{-w_{o2}\Delta t},$$
where $e^{td}$ is the intrinsic embedding (accounting variables through an FCN, concatenated with FinBERT
embeddings of the 10-K Item 1 text) and $c^{td}$ the extrinsic peer-effect embedding (event time-difference,
event type 0=self / 1=peer, and acquirer–target TNIC similarity) passed through an RNN over messages on the
dynamic top-ten TNIC peer graph. The choice module runs two rounds of aggregate/combine message passing,
$$a_j^{l}=f^l_{\text{agg}}(\{h_u^{l-1}:u\in N(j)\}),\qquad h_j^{l}=f^l_{\text{comb}}(h_j^{l-1},a_j^{l}),$$
and scores targets with a bilinear softmax:
$$P_d(v\mid t)=\frac{\exp\!\big(z_d^{2,t\top}\Phi\,z_v^{2,t}\big)}{\sum_{u\in V^t}\exp\!\big(z_d^{2,t\top}\Phi\,z_u^{2,t}\big)} .$$
Training loss separates timing NLL from choice cross-entropy,
$$\mathcal L=\sum_{d,n}\Big[\log\lambda_d(t_n^d)-\int_0^{t_n^d}\lambda_d(\tau)\,d\tau\Big]
+\sum_{d,n}\frac{-1}{|V^{t^d_n}|}\sum_{v\in V^{t^d_n}}\big[y_{vn}\log \hat y_{vn}+(1-y_{vn})\log(1-\hat y_{vn})\big].$$

**Required inputs.** A dated acquirer→target event table; per-firm accounting variables (assets, leverage,
operating condition, R&D); 10-K Item 1 text per firm-year; a time-varying peer graph (TNIC top-ten + absolute
similarity threshold); firm listing dates to define the active target universe $V^t$.

**Parameters & defaults.** Frequent-acquirer cutoff ≥4 deals; top-ten TNIC peers with an added similarity
threshold; FinBERT for text embeddings; RNN parameters shared across acquirers; training 1997–2019. Convert the
continuous time prediction to the annual label by $\hat t_d^+=E[t\mid H_t]=\int_t^\infty t\,p_d(t)\,dt$ and
marking "1" if it falls in the next year.

**Observed effect sizes.** AUC 0.5819 vs 0.5451 (Palepu) = +6.6% relative; component ablations as listed in
§1 (network −5.62%, GNN −4.78%, peer effect −4.50%, text −3.71%, RNN −2.30%).

**Failure modes.** Cold start: firms with no prior deal history cannot be scored, which is why 385 frequent
acquirers are the entire population; the model is only as good as SDC/Compustat coverage and interpolates
missing accounting (previous year, else cross-sectional mean), which leaks if done naively; AUC near 0.58 means
ranking is weak, so use it as a candidate generator, not a probability of return. See also
[`../qfin-st/ml-price-prediction.md`](../qfin-st/ml-price-prediction.md) for the general sequence/point-process
toolkit this specialises.

### 2.2 Milestone-gated real-options overlay with AHP success probabilities
**Purpose.** Replace a single opaque DCF growth assumption for an AI-transforming firm with per-milestone
options whose probabilities can be varied individually, producing a valuation band whose bounds trace to named
assumptions.

**Formula.** Total value and overlay:
$$V_0=V_{\text{DCF}}+V_{\text{AI}},\qquad
V_{\text{AI}}=\sum_{s=1}^{n}\frac{p_s\,V_s}{(1+r_s)^{T_s}}-I_0,$$
with the five-component conditional value
$$V_s=V_{b,s}+\Delta V_{o,s}+V_{c,s}-C_{r,s}-C_{e,s}$$
(baseline, operating uplift, continuation option, regulatory cost, execution cost). Each $p_s$ is an AHP
priority score (the Success Readiness Index) over five criteria — technical feasibility, regulatory compliance,
organisational readiness, market impact, data access/governance — calibrated to depth-specific base rates, with
inter-rater aggregation by geometric mean and conflict-weighted rater weights
$$w_i^{\text{eff}}\propto w_i^{\text{comp}}\,(1-\lambda b_i),\qquad \lambda\in[0,1].$$
Milestone clearing migrates value into the baseline: $V_{\text{firm},t}=V_{\text{DCF},t}+V_{\text{AI},t}$, with
$V_{\text{AI},t}$ contracting as options are exercised. Buyer-vs-seller M&A synergy is the difference of option
sets, $\Delta V_{\text{synergy}}=V_{\text{AI}}^{\text{buyer}}-V_{\text{AI}}^{\text{seller}}$.

**Required inputs.** A dated milestone register with gate pass/fail conditions; per-milestone probability $p_s$,
time $T_s$, discount rate $r_s$; a small expert panel scored on domain knowledge and conflict of interest; a
classification of the firm as AI Integrator (IDL 0–3) or AI Provider (Wrapper/Native).

**Parameters & defaults.** Case-E12 values (CHF m): $p=(0.82,0.67,0.52,0.38)$, $r=(15,20,25,30)\%$,
$T=(0.25,0.5,1,2)$ yr, $V=(13.9,34.9,79.3,198.5)$; $I_0=15$, $V_{\text{DCF}}=5$; scenario band from a uniform
$\pm0.10$ shift in all $p_s$. AHP consistency ratio threshold 0.10; IDL 0–1 contribute zero option overlay by
construction.

**Observed effect sizes.** Base case CHF 100m; band CHF 77–123m; M4 contributes |δw| = 11.7m of the 46m range
(>60%); removing M4 cuts $V_{\text{AI}}$ from 95m to ≈50m.

**Failure modes.** Probabilities are illustrative priors, not estimated base rates — the paper says so; the
option set is analyst-chosen, so the band bounds are conditional on a subjective list; overlapping options
double-count value unless attributed (Shapley is computationally prohibitive at $n=10$: 1,024 coalitions);
single-firm case gives no out-of-sample discipline. Treat it as a *documentation* framework for a diligence
note, not a return forecast.

### 2.3 Paired pre/post ratio test for an M&A event study
**Purpose.** Test whether a completed merger changed a firm's profitability and capital-structure ratios, with
an explicit direction and significance check per ratio.

**Formula.** For each ratio $X$ and each event firm, take the mean over the $w$ years before and after the
deal and test $H_0:\mu_{\text{pre}}=\mu_{\text{post}}$ with the paired statistic
$$t=\frac{\bar d}{s_d/\sqrt{n}},\qquad d_i=X_i^{\text{post}}-X_i^{\text{pre}},$$
reporting the two-sided $p$ per ratio and an overall pass/fail.

**Required inputs.** As-reported annual financial statements for each acquirer, aligned to event date; the
ratio set ROE, ROA, NIM, EPS, interest-expense/interest-income, cash-to-total-assets, total-liabilities-to-
assets, debt/equity, capital ratio.

**Parameters & defaults.** Window $w=2$ years pre and post (longer windows are contaminated by other macro
shocks, per the paper); sample = 6 merges (PNB, Canara, Union, Bank of Baroda, Indian Bank, SBI), event dates
2017–2020.

**Observed effect sizes.** ROE +0.0055 (p=0.0263), ROA +0.0006 (p=0.0370); NIM −0.0169 (p=0.4998), DER
−0.126 (p=0.4999), capital ratio −0.0036 (p=0.4999) — all non-significant.

**Failure modes.** $n=6$ under a per-ratio t-test gives almost no power; the paper reports p=0.4999 for several
ratios (a suspicious repeated value), and its EPS narrative contradicts its own table; two-year windows mix the
deal with concurrent macro shocks. With a US, as-reported dataset the same test becomes usable only if
fundamentals are point-in-time (see §3 gap) — using current restated statements is look-ahead.

### 2.4 M&A-wave cycle feature (quasi-periodic count model)
**Purpose.** Provide a slow, regime-style feature for corporate-action timing: is aggregate M&A volume in an
expansion or contraction phase of its oscillation?

**Formula.** Model the aggregate deal count $N_t$ over a rolling window as a sum of $n$ quasi-periodic
components and approximate its running mean by a low-order polynomial,
$$N_t\approx\sum_{i=1}^{k}\big[a_i\cos(2\pi t/P_i)+b_i\sin(2\pi t/P_i)\big]+p_d(t),\qquad
p_d(t)=\sum_{j=0}^{d}c_j t^j,$$
with nonlinearity family chosen from {ideal, linear, quadratic, exponential}. The paper's usable claim is only
the coarse one: the series carries systematic quasi-periodic oscillations that a polynomial tracks well.

**Required inputs.** A long dated series of M&A transaction counts (or values) by industry and region;
sufficient length for several merger waves (decades).

**Parameters & defaults.** None are published — the paper reports that MATLAB fits used ideal/linear/quadratic/
exponential forms but gives no period $P_i$, order $d$, or fit statistic. Fit $k$ and $P_i$ by periodogram on a
sufficiently long series; cap $d$ at 2–3 to avoid overfitting.

**Observed effect sizes.** Only context: worldwide M&A value USD 3.79tn in 2006, +38% over 2005
(arXiv:1502.02537). No model output is reported.

**Failure modes.** The source is non-reproducible (no data, no parameters, no validation) — never cite it as
evidence a cycle exists; M&A counts are driven by macro/rate regimes, not a stationary oscillator. Use it at
most as a design idea for a regime label built from your own data.

### 2.5 IPO-diligence LLM pipeline with evaluator-optimizer rubric generation
**Purpose.** Extract and grade the facts an analyst would pull from a first-time S-1 registration statement —
segment economics, KPI quality, governance, common-control recast accounting, capital intensity, execution
risk, valuation — where naive chunk retrieval fails on long, cross-referential filings.

**Formula.** Retrieval: index each chunk with a document-aware context prefix before embedding (contextual
retrieval), replacing fixed-size unenriched chunks. Rubric construction is an evaluator-optimizer loop:
$$\text{facts}\to\text{consolidate}\to\text{induce rubric}\to\text{quality score}\to
\{\text{stop},\ \text{repair},\ \text{enrich}\}\to\text{dedup}\to\text{human review},$$
where Stage 2 keeps only facts agreed by ≥2 models *from different labs*, and Stage 4 recommends repair
(structural, scoped: no new facts) or enrich (targeted re-extraction) with a numeric-payload-preservation check
during repair. A model answer is scored as the continuous per-question rubric-weighted mean in $[0,1]$.

**Required inputs.** Full S-1 filing text (EDGAR), a search/EDGAR tool harness, a multi-model answer ensemble
for fact extraction, an agreement threshold, and an expert review pass.

**Parameters & defaults.** Agreement threshold = 2 cross-lab models; question taxonomy of 7 IPO domains and 6
professional workflows; public set $n=70$ (SPCX), private remainder of the 1,000-question dataset; ensemble
GLM-5.1 / GLM-5.2 / Qwen 3.7 Max / Kimi K2.6 / MiMo-2.5 Pro (Nemotron 3 Ultra excluded for excessive
failures).

**Observed effect sizes.** GLM-5.2 79.8%, Qwen 3.7 Max 78.9% @$0.30, MiMo-2.5 Pro 77.2% @$0.05, Kimi K2.6
68.0%, Nemotron 3 Ultra 45.5%; FABv2 ceiling 57.9% @$2.51. Valuation/underwriting is the weakest domain for
most models (55.9–75.4%).

**Failure modes.** Metric mismatch: this is a continuous rubric average, FABv2 is dealbreaker-gated partial
credit, so the 19-point gap is not like-for-like; same-family evaluator bias (GLM-5.1 grading GLM-5.2); no
retrieval ablation was run; benchmark contamination is guarded only by withholding questions. Output is an
analysis artifact, not alpha. Related LLM-text machinery:
[`../qfin-st/news-sentiment-nlp.md`](../qfin-st/news-sentiment-nlp.md).

### 2.6 Governance/CSR cognitive scorecard (cross-sectional feature only)
**Purpose.** Build a comparable governance attribute vector for a public firm, to test whether board structure
or compensation/CSR-committee design co-moves with performance — explicitly not a causal claim.

**Formula.** For firm $i$ and year $t$, assemble
$$\text{Gov}_{it}=\big[\text{size}_{it},\ \text{indep}_{it},\ \text{dual}_{it},\
\text{gender}_{it},\ \text{foreign}_{it},\ \text{edu}_{it},\ \text{multiple}_{it},\
\mathbb 1[\text{CSRC}]\big],$$
and, if testing the CSP–CFP link, run a panel regression of operating performance on $\text{Gov}$ with
firm and year fixed effects, reporting endogeneity diagnostics rather than a single coefficient.

**Required inputs.** Board size, independence percentage, CEO duality flag, gender/foreign/education/multiple-
directorship percentages, presence and independence of a CSR/sustainability committee.

**Parameters & defaults.** Descriptive anchors from the review: European/US mean board size ≈9; French SBF120
mean 12.89 (SD 3.53), independence 52.5%, duality 33.6%, gender 22.2%; CSRC present in 63% of European
firm-years; the review cites 80% CSRC independence as a governance benchmark and ≥3 female directors as the
environmental-strength threshold.

**Observed effect sizes.** None causal: the review reports >200 studies with positive, negative and null
CSP–CFP links and attributes the ambiguity to endogeneity, so any score-to-return effect you estimate yourself
must survive that critique.

**Failure modes.** Reverse causality (financial performance may change board composition); confounding by
firm size/industry/regulation; the source is a literature review with no dataset of its own, so all numbers
above are third-party and must be re-derived from a real governance feed (see §3 gap). Do not trade this.

## 3. Data requirements → available endpoints

Provider rows are real entries in `strategies/endpoints.json`; `moomoo` rows are served by the local OpenD
gateway over the SDK and were not live-probed over HTTP. **gap** means no current provider can supply the
input.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (event-study returns, ADV) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily/prev aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday bars (deal-announcement windows) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Tradable symbol universe / delisting universe | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Current quarterly/annual statements (as filed today) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| Current fundamentals via query params | `https://www.alphavantage.co/query` | `fundamental_data` | alpha_vantage | ok |
| News stream (event text, M&A announcements) | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| News stream (secondary) | `https://api.benzinga.com/api/v2/news` | `news_data` | benzinga | ok |
| News stream (secondary) | `https://api.stockdata.org/v1/news/all` | `news_data` | stockdata | ok |
| News stream (secondary) | `https://newsapi.org/v2/everything` | `news_data` | newsapi | ok |
| News sentiment scores | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | ok |
| News sentiment via query params | `https://www.alphavantage.co/query` | `news_sentiment` | alpha_vantage | ok |
| Analyst ratings calendar (peer/coverage effect) | `https://api.benzinga.com/api/v2.1/calendar/ratings` | `analyst_ratings` | benzinga | ok |
| Earnings calendar (timing alignment) | `https://api.benzinga.com/api/v2.1/calendar/earnings` | `earnings_calendar` | benzinga | ok |
| Offerings / IPO calendar | `https://api.benzinga.com/api/v2.1/calendar/offerings` | `offerings_calendar` | benzinga | ok |
| Dividends (capital-structure events) | `https://eodhd.com/api/div/AAPL` | `corporate_actions` | eodhd | ok |
| Dividends calendar | `https://api.benzinga.com/api/v2.2/calendar/dividends` | `corporate_actions` | benzinga | ok |
| Macro rates (discount-rate inputs for §2.2) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Risk-free curve (discount-rate inputs) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Institutional holders (governance feature) | `moomoo://get_shareholders_institutional` | `institution_data` | moomoo | gateway (not live-probed) |
| Insider trades (governance feature) | `moomoo://get_insider_trade_list` | `smart_money` | moomoo | gateway (not live-probed) |
| Analyst rating summary | `moomoo://get_research_rating_summary` | `analyst_ratings` | moomoo | gateway (not live-probed) |
| Revenue breakdown (segment economics) | `moomoo://get_financials_revenue_breakdown` | `revenue_breakdown` | moomoo | gateway (not live-probed) |
| Capital flow | `moomoo://get_capital_flow` | `capital_flow` | moomoo | gateway (not live-probed) |
| **Point-in-time as-reported fundamentals history** | — | — | — | **gap** |
| **Historical M&A deal database (acquirer/target/timestamps/value)** | — | — | — | **gap** |
| **10-K Item 1 / business-description text corpus + TNIC peer map** | — | — | — | **gap** |
| **S-1 / IPO prospectus corpus (EDGAR full text)** | — | — | — | **gap** |
| **CSR/ESG scores and board-composition / CSR-committee data** | — | — | — | **gap** |

**What each gap costs, quantified.** §2.1 needs the full SDC-Platinum-style event table over 1997–2020 with
385 frequent acquirers, Compustat accounting variables, 10-K Item 1 text, and the Hoberg–Phillips TNIC map —
none of the 49 catalog rows carries a deal-level or text-corpus source, so TDIN can be trained only on a
self-assembled scrape (news-derived event dates plus current-statement proxies), which reproduces the model's
AUC≈0.58 regime at best. §2.3 needs **as-reported** annual statements aligned to event dates; the catalog's
`fundamental_data` rows (tiingo `statements`, alpha_vantage `query`) return *current* statements, so a
pre/post test on them silently uses restated numbers — a look-ahead bias whose size is exactly the cumulative
restatement history, which is why the Indian paper's two-year window and p≈0.50 values are not transferable.
§2.5 needs full S-1 text; the catalog has news and filings-adjacent feeds but no EDGAR full-text archive, so
the pipeline can be run only on filings fetched ad hoc. §2.2 needs discount rates (fred, treasury — available)
and a milestone register (private, no provider). §2.6 needs CSR scores and board data (Vigeo-Eiris/Bloomberg
class); the closest catalog rows are institutional-holder and insider feeds via the `moomoo` gateway, which
give ownership but not board composition or committee membership.

## 4. Pitfalls, validation and measurement

- **Look-ahead via restated fundamentals.** Every M&A performance test here (arXiv:2308.16054, and any
  replication of arXiv:2404.07298's accounting inputs) presumes as-reported point-in-time statements. The
  catalog's fundamentals are current; using them in a pre/post or hazard model leaks future restatements. If
  PIT data is unavailable, restrict claims to price-based tests (CAR around announcement) and state the
  limitation.
- **Modest discrimination and metric inflation.** TDIN's AUC 0.5819 vs the 0.5451 logistic baseline is a 6.6%
  relative lift that neither paper tests for statistical significance; report AUC with a bootstrap CI and a
  precision@k / lift curve, not the raw delta (arXiv:2404.07298).
- **Resampling-induced bias.** The paper's stated methodological novelty is avoiding oversampling for sparse
  positive pairs; if you rebalance to train a comparable logistic model, you bias exactly the comparison you
  are trying to make (arXiv:2404.07298).
- **Rubric-metric mismatch and judge bias.** IPO Finance Agent scores a continuous rubric average while
  Finance Agent v2 is dealbreaker-gated partial credit; the 19-point cross-benchmark gap is therefore not
  like-for-like, and the leading score comes from an evaluator in the same model family as the leader
  (arXiv:2606.23032). Hold a private question split and treat any single model's score as a floor.
- **Protocol is not validation.** The real-options paper's base case reproduces the disclosed pre-money by
  construction and is explicitly described as a "single-firm demonstration of protocol coherence"
  (arXiv:2609.24181). Do not present a valuation band as an out-of-sample accuracy claim; the band bounds are
  $p_s$-conditional and the option list is analyst-chosen.
- **Option overlap double-counting.** If two milestones claim the same revenue uplift, summing $V_s$
  double-counts; the paper recommends attribution-by-assignment plus an $n\times n$ interaction matrix, with
  Shapley deferred as impractical (arXiv:2609.24181).
- **Endogeneity in governance/CSP work.** The CSR review identifies endogeneity in regression/SEM designs as
  the primary cause of sign flips across >200 studies; any governance factor you build must use lagged
  regressors, firm fixed effects, and an explicit instrument or natural-experiment test (arXiv:2102.09218).
- **Non-reproducible cycle claim.** The quasi-periodicity result gives no data, period estimate, polynomial
  order or fit statistic; do not treat it as evidence of a tradable M&A wave cycle (arXiv:1502.02537).
- **Sample-size honesty.** The S-1 benchmark's governance domain has $n=4$ and investment-banking/ECM $n=5$;
  the bank study has $n=6$ with repeated p=0.4999 values. Both are too small for their quoted significance
  (arXiv:2606.23032, arXiv:2308.16054).
- **Split and regime discipline.** Follow the papers' own splits where they exist: train 1997–2019 / test
  beyond for TDIN, public 70 / private remainder for the benchmark; for any pre/post ratio test, match
  non-merging peers over the same window to absorb rate and macro regimes.

## 5. Recommended first implementation in FinRobot

Ranked by value-per-effort against what the data layer can fetch today.

1. **Announcement-window event study for M&A and corporate actions.** *What:* CAR around deal/earnings
   announcement dates, using news-derived event timestamps and daily bars. *Data:* eodhd `news`, benzinga
   `news`, eodhd `eod` / tiingo `prices`. *Pass:* a reproducible CAR table with a matched-peer benchmark and a
   bootstrap CI per window. *Effort:* S.
2. **Deal-level M&A candidate generator (TDIN-lite).** *What:* the timing + choice intensity from §2.1 on
   whatever dated event table can be assembled, with the TNIC-style peer graph replaced by sector/similarity
   peers. *Data:* news-derived event dates + current fundamentals + symbol universe. *Pass:* ranks the next
   acquirer–target pairs with an AUC lift over a logistic baseline on a time-based holdout, reported with a CI.
   *Effort:* L. Related general toolkit: [`../qfin-st/ml-price-prediction.md`](../qfin-st/ml-price-prediction.md).
3. **Pre/post capital-structure ratio test with an explicit PIT guard.** *What:* the paired test of §2.3,
   gated to refuse claims when fundamentals are not as-reported. *Data:* tiingo/alpha_vantage fundamentals
   (with the guard) plus event dates. *Pass:* a per-ratio table whose direction is consistent with its own
   means, emitted only when the PIT flag is set. *Effort:* S.
4. **Milestone-gated valuation worksheet for AI-exposed names.** *What:* an interactive $V_0=V_{\text{DCF}}
   +V_{\text{AI}}$ sheet with the $V_s$ five-way decomposition and AHP-style $p_s$ inputs. *Data:* fred/treasury
   for $r_s$; the milestone register is user-supplied. *Pass:* a scenario band whose bounds report which
   milestone dominates and by how much. *Effort:* M.
5. **IPO/S-1 diligence pipeline with contextual retrieval.** *What:* the retrieval + rubric loop of §2.5 over
   any S-1 fetched from EDGAR, scored with a private held-out split. *Data:* ad-hoc EDGAR text (no catalog
   source). *Pass:* domain-level scores with the valuation-domain floor reported and a same-family-evaluator
   caveat. *Effort:* L. Overlaps [`../qfin-st/news-sentiment-nlp.md`](../qfin-st/news-sentiment-nlp.md).
6. **Governance/CSR scorecard as a diagnostic, not a factor.** *What:* the $\text{Gov}$ vector from §2.6 using
   institutional-holder/insider proxies, computed but not traded. *Data:* `moomoo` gateway rows
   (`get_shareholders_institutional`, `get_insider_trade_list`). *Pass:* a lagged, fixed-effects regression
   whose endogeneity diagnostics are printed, with no causal claim. *Effort:* M.
7. **Acquire point-in-time fundamentals.** *What:* add a restatement-aware, as-reported fundamentals feed
   (Compustat-style) so items 3 and 4 can make historical claims. *Data:* the feed itself. *Pass:* the pre/post
   and hazard tests run on PIT data with a documented vintage date per record. *Effort:* L.
8. **Add an M&A deal-event archive.** *What:* a dated acquirer→target event table (deal value, status,
   timestamps) to train §2.1 properly. *Data:* the archive. *Pass:* the TDIN-lite holdout AUC is measured on
   real deal events rather than news proxies. *Effort:* L.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2308.16054v1 | Capital Structure Dynamics and Financial Performance in Indian Banks (An Analysis of Mergers and Acquisitions) | 2023 |
| 2102.09218v1 | Corporate Social Responsibility and Corporate Governance: A cognitive approach | 2021 |
| 2606.23032v3 | IPO Finance Agent: Benchmark of LLM Financial Analysts Beyond Finance Agent v2, with Automated Rubric Generation, on the SpaceX (SPCX) IPO | 2026 |
| 2404.07298v3 | A Deep Learning Method for Predicting Mergers and Acquisitions: Temporal Dynamic Industry Networks | 2024 |
| 1502.02537v1 | Mergers and acquisitions transactions strategies in diffusion-type financial systems in highly volatile global capital markets with nonlinearities | 2015 |
| 2609.24181v2 | Firm Valuation When AI Shapes the Business Model: A Milestone-Based Real-Options Framework for the AI Valuation Uncertainty Problem | 2026 |