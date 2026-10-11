# Real Estate & Housing — learnings from the q-fin.GN corpus

`104` of 3095 corpus papers matched this category (104 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category yields exactly one quantitative, price-based estimator that FinRobot can
compute from data it can actually fetch** — the mortgage-rate-adjusted "effective price" and its
neutral home price index (arXiv:2207.02896), which need only a monthly home price index and a
mortgage-rate series (both available from `fred`). Everything else in the assigned set is
decision-analytic (a multi-criteria real-options screen, a county scoring rubric), behavioural
(a survey of metaverse-land buyers), theoretical (broker disintermediation conditions), or
simulation-only (a self-organised urban rent model). None of those four is a tradable signal, and
all four need property-, transaction- or ward-level data that **no endpoint in
`strategies/endpoints.json` serves**. The document therefore spends its depth on the mortgage
adjustment (§2.1–2.2), states the others plainly as context (§2.3–2.5), and marks every
property-level input as **gap** in §3 instead of implying it can be fetched.

## 1. What the corpus actually offers

- **A mortgage-rate price adjuster with a closed form (arXiv:2207.02896).** Two compatible houses
  financed with identical term $T$ and down-payment rate $\alpha$ but rates $r_A,r_B$ have an
  *effective* price $P_B^{A}=\gamma(r_A,r_B;T,\alpha)\,P_B$ with
  $\gamma=(1-\alpha)\beta_A/\beta_B+\alpha$, where $\beta(r;T)=\big((1+r)^T-1\big)/\big(r(1+r)^T\big)$.
  $\gamma$ is always positive and is $>1$ exactly when $r_B>r_A$: a higher future rate makes the same
  nominal price *effectively* more expensive. The paper's motivation data: **87%** of 2021 US home
  buyers financed with a mortgage, and among them first-time buyers financed **93%** and repeat buyers
  **83%** of the price (NAR, cited in arXiv:2207.02896).
- **The effective-price slope is large — roughly 9–10% of price per 100 bp of rate, near baseline.**
  On the paper's worked grid ($r_A=4.5\%$, $T=360$ months, $\alpha=20\%$, holding nominal growth
  $g=0$): a move to $r_B=3.5\%$ gives effective growth $-9.1\%$, to $5.0\%$ gives $+4.8\%$, to
  $6.0\%$ gives $+14.7\%$ and to $7.0\%$ gives $+25.0\%$ (arXiv:2207.02896, Table 1). Off-baseline
  rows confirm the multiplicative structure: $g=-10\%$ at $r_B=6.5\%$ still yields $+7.8\%$ effective
  growth.
- **A neutrality line separating "buy now" from "wait" (arXiv:2207.02896).** Setting effective
  growth to zero gives $g^{*}=\big(1-\gamma\big)/\gamma=(1-\alpha)(\beta_B-\beta_A)/
  \big(\alpha\beta_B+(1-\alpha)\beta_A\big)$. With $g=0$ as the horizontal axis and $r$ as the
  vertical, the $(r,g)$ plane splits into six regions: in A/B/C the future purchase is
  *effectively more expensive* (buy now); in D/E/F it is *cheaper* (wait). The paper uses this as a
  filtering device, not a price forecast.
- **Mortgage rates explain a material share of long-run US home-price growth, but not the pandemic
  surge (arXiv:2207.02896, Tables 3–4).** Neutralising the 30-year fixed rate (two-month lag,
  FRED Case-Shiller HPI), the share of nominal growth attributable to rates, $C=(A-B)/(1+A)$, is:
  **1987–2021** nominal $A=337.3\%$ vs adjusted $B=238.5\%$ → **22.6%** ($\alpha=20\%$; $25.4\%$ at
  $\alpha=10\%$, $24.0\%$ at $\alpha=15\%$); **2000–2021** $178.7\%$ vs $124.1\%$ → **19.6%**;
  **2010–2021** $92.2\%$ vs $73.0\%$ → **10.0%**; **2019–2021** $36.5\%$ vs $19.1\%$ → **12.7%**.
  During the pandemic (2020-03→2021-12) $A=29.5\%$ vs $B=24.4\%$ → only **3.9%**, and for calendar
  2021 alone the impact is **$-3.0\%$** ($A=17.8\%$, $B=21.4\%$) — i.e. neutralising rates would leave
  2021 prices *higher*, so rates were not the driver of the COVID run-up.
- **A county investment screen whose own validation failed (arXiv:2503.15532).** The Koedds tool
  fuses Redfin monthly county metrics (median sale price, homes sold; MoM and YoY averages, data from
  2012, ~1 GB, processed on a 10-node Spark cluster; **3,143** US counties) with the CDC/ATSDR Social
  Vulnerability Index (16 social factors, pre-normalised to $[0,1]$) into a weighted score. The paper
  reports the correlation between SVI and average annual price growth as **0.126** — below the 0.2
  significance convention, so the central hypothesis ("more resilient counties grow more") is
  rejected. Its headline finding is instead that growth is near-universal (only a handful of counties
  had negative average YoY change) and that Iowa/Ohio counties scored highest.
- **A real-options-aware MCDA screen with no empirical calibration (arXiv:2601.22166).** A five-level
  decision architecture (context → plausible uses → indicators → comparative matrix → decision/
  exclusion) over six indicators — expected NPV; market risk; operational risk; technical complexity;
  managerial complexity; time-to-income — scored on a relative **1–5** scale and aggregated into an
  *attractiveness index* whose structure is deliberately **subtractive** (risk and complexity penalise
  value rather than being traded off additively). Weights are declared to be *decision-profile
  parameters, not estimated coefficients*; the paper's evidence is illustrative cases, not a dataset.
- **A behavioural profile of metaverse landowners, not of housing (arXiv:2308.10309).** Survey
  distributed via CoinGecko (2022-12-15→2023-01-19): 2,892 clicks, **438** completions, **343** NFT
  owners, **164** metaverse-land owners. PCA (varimax, loading threshold 0.4, KMO 0.915, Bartlett
  $p<0.000$) gives four factors accounting for **78.3%** of variance: Aesthetics & Identity 26.1%,
  Social & Community 24.5%, Speculation & Investment 15.7%, Innovation & Technology 12.0%. A logistic
  model of land ownership ($N=343$, pseudo-$R^2=0.10$) finds negative association with age
  (OR 0.808, $p<0.05$) and positive with number of NFTs owned (OR 1.192) and earlier first NFT
  purchase (OR 1.230); average Decentraland land floor price **\$1,203** and Sandbox **\$1,675**
  (Dec 2022–Jan 2023). Digital land is not tradable US housing; retained only as context on the
  speculation channel.
- **A theory of when to bypass the broker (arXiv:2005.01710).** US residential brokerage revenue is
  put at **>$60 billion/yr**; the contribution is a set of derivative inequalities (information
  $I_i$ vs $I_p$, search costs $y_b$ vs $y_{bi}$, contract states $E_s/E_p/E_m$, social capital
  $SC_b,SC_s$) under which buyer or seller optimally dis-intermediates. No data, no estimation, no
  calibration — context only.
- **A self-organised urban rent simulator reproducing only the top of the ward ranking
  (arXiv:1406.6100).** Gauvin-model extension on an $L\times L$ lattice ($L=100$) with $K=10$ willingness-
  to-pay ranks, a Gaussian-mixture intrinsic attractiveness centred on Sapporo's 10 ward offices, and
  ward weights $\delta_l$ proportional to flat counts. It matches the top two wards' order (simulated
  Chuo ¥50,823 / Shiraishi ¥43,550 vs market ¥54,200 / ¥51,100) but not the full ordering. Empirical
  2DK rents range from ¥19,000 (Chuo low) to ¥120,000 (Chuo high); annual in-migration 63,021 vs
  out-migration 57,587; the derived minimum time step is $\tau=\Gamma\cdot365/C = 1000\cdot365/63021
  = 5.79$ days.
- **Scope notes.** No assigned paper is fully off-topic, but three are weak fits retained for defined
  roles: arXiv:2308.10309 (virtual land, not housing — the only retail-behaviour evidence in the set),
  arXiv:2005.01710 (pure theory, no numbers), and arXiv:1406.6100 (primary category `physics.soc-ph`,
  cross-listed `q-fin.GN`; the only generative model of a housing market in the set).

## 2. Implementable formulas & algorithms

### 2.1 Mortgage-rate-adjusted effective price and the neutrality line
**Purpose.** Turn a nominal home price into the price a buyer *effectively* pays given an expected
mortgage-rate change, and classify "buy now vs wait" scenarios without forecasting prices. This is
also the per-property building block of the index neutralisation in §2.2.

**Formula.** The monthly payment on price $P$ with down-payment rate $\alpha$ and rate $r$ over
$T$ months is $X=(1-\alpha)\,P\,r(1+r)^T/\big((1+r)^T-1\big)$, so that
$P=\beta(r;T)X+\alpha P$ with the annuity factor
$$\beta(r;T)=\frac{(1+r)^T-1}{r\,(1+r)^T}.$$
For two purchases one period apart the effective price of the later one, valued at the earlier rate,
is
$$P_B^{A}=\gamma(r_A,r_B;T,\alpha)\,P_B,\qquad
\gamma=(1-\alpha)\frac{\beta_A}{\beta_B}+\alpha .$$
The effective (mortgage-adjusted) growth rate of a nominal growth $g=(P_B-P_A)/P_A$ is
$$g^{*}=\gamma\,(1+g)-1 .$$
The **price–mortgage-rate neutrality line** ($g^{*}=0$) is
$$g^{*}_{\text{zero}}=\frac{1-\gamma}{\gamma}
=\frac{(1-\alpha)(\beta_B-\beta_A)}{\alpha\beta_B+(1-\alpha)\beta_A}.$$

**Required inputs.** A mortgage-rate series $r_t$ (30-year fixed is the paper's default); a home price
level series $P_t$ (monthly HPI); the term $T$; the down-payment rate $\alpha$; optionally an
assumed rate lag. For the buyer-level grid: baseline rate $r_A$ and candidate $(r_B,g)$ scenarios.

**Parameters & defaults.** $T=360$ months (30-year fixed); $\alpha$ reported at 0.10/0.15/0.20, base
case **0.20**; baseline $r_A=4.5\%$ in the worked example; **two-month lag** applied when
neutralising the HPI. The paper's own data pull: FRED Case-Shiller HPI and FRED 30-year fixed
mortgage rate, retrieved 2022-04-18.

**Observed effect sizes.** Near baseline, holding $g=0$: $\partial g^{*}/\partial r\approx
+9$–$10$ percentage points of effective price per 100 bp. Neutralisation removes **22.6%** of
1987–2021 nominal growth ($\alpha=20\%$), **19.6%** of 2000–2021, **10.0%** of 2010–2021, **12.7%**
of 2019–2021, but only **3.9%** across the pandemic and **$-3.0\%$** for 2021 alone
(arXiv:2207.02896).

**Failure modes.** Mortgage rates are *endogenous* — they are a monetary-policy transmission channel,
so the price–rate relation is partly circular (the paper cites this directly), and $\gamma$ is a
sensitivity device, not a causal estimate. The two-month lag is an assumption; changing it shifts the
timing of the adjustment. $\gamma$ is a *one-period relative* measure, so it should not be chained
naively across long gaps and ignores the forgone return on a delayed down payment. Cash purchases and
variable-rate/15-year mortgages are excluded, though the paper argues the 30-year fixed covers "80+%"
of activity. It does not predict future prices.

### 2.2 Mortgage-rate-neutral home price index
**Purpose.** Produce a version of an HPI in which mortgage-rate swings are removed, so that the
"true" housing-market movement can be read off independently of the rate regime.

**Formula / algorithm.** Given $H=\{h_1,\dots,h_N\}$ and rates $R=\{r_1,\dots,r_N\}$:
1. $G=\{g_1=0,\;g_n=(h_n-h_{n-1})/h_{n-1}\}$.
2. $\Gamma=\{\gamma_1=1,\;\gamma_n \text{ from §2.1 with } (r_{n-1},r_n)\}$ (lag if desired).
3. $G^{*}=\{g_1^{*}=0,\;g_n^{*}=\gamma_n(1+g_n)-1\}$.
4. $K=\{k_1=0,\;k_n=h_{n-1}g_n^{*}\}$.
5. $H^{*}=\{h_1^{*}=h_1,\;h_n^{*}=h_1+\sum_{i\le n}k_i\}$, with the closed form the paper prints,
   $$h_n^{*}=h_n+\sum_{i=1}^{n}(\gamma_i-1)\,h_i .$$

**Required inputs.** Monthly HPI, monthly mortgage rate, $T$, $\alpha$, lag choice.

**Parameters & defaults.** Same as §2.1 ($T=360$, $\alpha\in\{0.10,0.15,0.20\}$, two-month lag).

**Observed effect sizes.** The neutral series is ~24% lower than nominal cumulatively over
1987–2021 at $\alpha=20\%$; the $C=(A-B)/(1+A)$ attribution is reproduced in §1. For the chained-index
arithmetic itself see [`../qfin-st/econometrics-forecasting.md`](../qfin-st/econometrics-forecasting.md);
this corpus adds only the rate-neutralisation step.

**Failure modes.** In a low-rate, rising-price regime the neutral index can* exceed* the nominal one
(2021: $B=21.4\%>A=17.8\%$), which surprises users expecting "adjustment = haircut"; document the
sign convention. The result is sensitive to $\alpha$ only marginally (22.6%→25.4% as $\alpha$ goes
0.20→0.10) but sensitive to lag and to which mortgage product is used. Do not present the neutral
index as a forecast.

### 2.3 Real-options-aware multi-criteria redevelopment screen (context)
**Purpose.** Ex-ante selection/exclusion of the *intended use* of a redevelopment asset before capital
is committed, integrating option-value preservation (avoid premature irreversibility) with
multi-criteria trade-offs.

**Algorithm.** Six indicators map to three dimensions: *value* $V$ = expected NPV (comparative,
conservative, relative); *risk* $R$ = market risk combined with operational risk; *complexity* $C$ =
technical + managerial complexity, with time-to-income treated as a penaliser. Each alternative
(asset $\times$ use) is scored on a relative **1–5** scale across alternatives; NPVs are normalised.
Aggregation is **subtractive**:
$$A_{i}=w_V\,\tilde V_i-w_R\,\tilde R_i-w_C\,\tilde C_i,$$
where $\tilde{\cdot}$ denotes the normalised score. The primary output is an **exclusion** decision
(ex-ante elimination of structurally incoherent options); ranking is secondary.

**Required inputs.** The set of plausible uses for a given asset; comparative NPV estimates under
conservative rent/occupancy/cost assumptions; qualitative risk and complexity gradings; investor
profile (capital scale, capabilities, horizon).

**Parameters & defaults.** Weights $w_V,w_R,w_C$ are **decision-profile parameters, not estimated
coefficients** — the paper explicitly declines to fit them. Standard configuration tilts weight to
$V$ while preventing high $V$ from offsetting unsustainable $R$ or $C$. No numeric defaults are
published.

**Observed effect sizes.** None — illustrative cases only; no dataset, no backtest, no $R^2$. This is
a rubric, not an estimator.

**Failure modes.** Scores are relative positions, not absolute measures, so they are not comparable
across assets or studies. The paper warns explicitly that a high NPV built on aggressive assumptions
is itself a red flag, that ROI alone is inadequate (no time dimension, no risk decomposition), and
that the matrix does not replace due diligence or a business plan.

### 2.4 County investment screen with social vulnerability (context, validation failed)
**Purpose.** Rank US counties by *upside potential* (price growth) net of community vulnerability.

**Algorithm.** (i) From a Redfin-style monthly panel keep period, region, property type, homes-sold
and median-sale-price MoM/YoY, drop incomplete records; (ii) average MoM and YoY per region;
(iii) min–max normalise each average to $[0,1]$; (iv) the SVI is already in $[0,1]$, and because
*low* SVI is good while *high* price growth is good, normalise the price score as $1-\text{SVI}$;
(v) join on county (name + FIPS) and form a weighted score. The paper reports no explicit weight
vector — the model is a normalised weighted average.

**Required inputs.** County-level home price growth (monthly), homes-sold, CDC/ATSDR SVI (16 factors).

**Parameters & defaults.** Data from 2012 onward; 3,143 counties; SVI combined (not sub-index) score;
Spark 10-node cluster for the ~1 GB panel.

**Observed effect sizes.** Correlation of SVI with average annual price growth = **0.126** — no
significant relation. The screen's top-ranked region was the Midwest (Iowa/Ohio), contrary to the
authors' prior, and no forward benchmark was run.

**Failure modes.** No out-of-sample test (the authors say so); the correlation null means the score
is not a validated predictor; growth was positive almost everywhere so the ranking carries little
cross-sectional information; the SVI mixes factors that may not move property markets. Treat as an
unvalidated feature prototype.

### 2.5 Mean-field housing-market flow simulator (offline / synthetic-only)
**Purpose.** Generate the spatial rent distribution of a multi-centre city and study the emergence of
income-segregated communities; usable as a stylised housing-market simulator.

**Formula.** On an $L\times L$ lattice with centre $\mathbf O=(L/2,L/2)$, attractiveness for
category $k$ at location $\mathbf X$ updates as
$$A_k(\mathbf X,t{+}1)=A_k(\mathbf X,t)+\omega\big(A^{0}(\mathbf X)-A_k(\mathbf X,t)\big)
+\varepsilon\!\!\sum_{k'\ge k}\!v_{k'}(\mathbf X,t),$$
with intrinsic $A^{0}$ a Gaussian (single centre) or Gaussian mixture over ward offices,
$A^{0}(\mathbf X)=\sum_l \frac{\delta_l}{2\pi R_l}\exp\!\big(-\tfrac{\|\mathbf X-\mathbf B_l\|^2}{2R_l^2}\big)$,
$\sum_l\delta_l=1$. Buyers visit location $\mathbf X$ with probability
$\pi_k(\mathbf X,t)=\dfrac{1-e^{-\lambda A_k(\mathbf X,t)}}{\sum_{\mathbf X'}\big(1-e^{-\lambda A_k(\mathbf X',t)}\big)}$
(→ $\operatorname{argmax}$ as $\lambda\to\infty$, $\propto A_k$ as $\lambda\ll1$). Sellers of category
$k$ post $P^o_k(\mathbf X)=P^{0}+[1-e^{-\xi \bar A(\mathbf X,t)}]P_k$ with
$\bar A=\frac1K\sum_k A_k$; a transaction is approved iff the buyer's willingness-to-pay exceeds the
offer, $P_{k'}>P^o_k$; the transaction price is the interior division
$P_{\text{tr}}=(1-\beta)P_{k'}^{o}(\mathbf X)+\beta P_k$. A rank-$k$ agent's effective time step is
$\tau=\Gamma\cdot365/C$ days.

**Required inputs.** Lattice size $L$; number of ranks $K$; willingness-to-pay bounds $P_0,\Delta$;
basic rent $P^0$, cap $P^1$; flow rate $\Gamma$; and, for a real city, ward centroids, flat counts
(weights $\delta_l$) and office counts.

**Parameters & defaults.** $L=100$, $K=10$, $P_0=15{,}000$, $\Delta+P_0=120{,}000$ ($\Delta=105{,}000$),
$\omega=1/15$, $R=10$, $\varepsilon=0.0022$, $\lambda=0.01$, $\xi=0.1$, $P^0=9{,}000$, $P^1=200{,}000$,
$\beta=0.1$, $\Gamma=L^2/K=1000$, $T=100$ updates. Multi-centre $R_l=5$; Sapporo ward weights from
flat counts (Chuo $\propto1.0$ down to Kiyota $\propto0.1$).

**Observed effect sizes.** Reproduces the top-two ward rent ordering (Chuo, Shiraishi) and rough
levels (§1); lowest-rank agents are "swept away" from attractive regions into low-rent communities.
It does not reproduce the full ward ordering.

**Failure modes.** Calibration is partly arbitrary (office-location bias $\eta\sim U(-1,1)\cdot\delta$,
etc.); only 2 of 10 ward positions are recovered; spatial resolution is coarse and the authors flag
this. Simulation-only: it consumes no market feed and produces no tradeable signal.

## 3. Data requirements → available endpoints

Provider rows below are real entries in `strategies/endpoints.json` (`moomoo` rows are `gateway`,
served by the local OpenD SDK, not live-probed HTTP); "gap" means **no current provider can supply it.**

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Mortgage rate series (30-yr fixed) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Home price index (Case-Shiller-type) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Macro indicators (rates, CPI, housing) | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| Economic calendar (FOMC/housing releases) | `moomoo://get_economic_calendar` | `economic_calendar` | moomoo | gateway (not live-probed) |
| Fed target-rate expectations | `moomoo://get_fed_watch_target_rate` | `fed_watch` | moomoo | gateway (not live-probed) |
| Treasury yield curve (rate scenario input) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Listed homebuilders / REITs OHLCV (proxy beta) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Listed homebuilders / REITs OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Listed homebuilders / REITs OHLCV (secondary) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Housing-market news flow | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| Housing-market news flow (secondary) | `https://newsapi.org/v2/everything` | `news_data` | newsapi | ok |
| Housing-market news flow (secondary) | `https://api.benzinga.com/api/v2/news` | `news_data` | benzinga | ok |
| Prediction-market housing/macro contracts | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | ok |
| **County/ZIP median sale price, listings, inventory panel** | — | — | — | **gap** |
| **Transaction-level sale records (deed / MLS)** | — | — | — | **gap** |
| **Rent distribution by ward / neighbourhood** | — | — | — | **gap** |
| **Property attributes (beds/baths/condition) at unit level** | — | — | — | **gap** |
| **CDC/ATSDR Social Vulnerability Index (county)** | — | — | — | **gap** |
| **Metaverse land floor prices / NFT sale comps** | — | — | — | **gap** |

**What the gap costs, quantified.** The one implementable estimator (§2.1–2.2) needs only monthly
granularity and is *not* gapped: FRED supplies the HPI and the 30-year rate. The gapped items are what
the *context* papers used. Koedds required a county-level monthly panel covering **3,143** counties
from **2012** onward (Redfin ~1 GB) plus the 16-factor SVI — neither is an endpoint, so §2.4 cannot be
run as-is. The Sapporo simulator needed per-ward flats and office counts and annual in/out-migration
(**63,021** in / **57,587** out) to fix $\delta_l$ and the time step — property-registry data, gapped.
The metaverse study needed NFT land transaction and floor-price data — a crypto/NFT feed, which the
catalog does **not** contain at all. Absent these, the whole category reduces to the mortgage
adjustment plus, at best, an offline simulator and a manual-CSV prototype.

## 4. Pitfalls, validation and measurement

- **Endogeneity / circularity.** Mortgage rates are a monetary-policy transmission channel into
  housing demand, so price and rate are jointly determined; the effective-price relation is a
  sensitivity identity, not a causal estimate (arXiv:2207.02896). Report it as scenario arithmetic.
- **Chained-index sign surprises.** A rate-neutral HPI can *rise* relative to nominal in a
  low-rate boom (2021: $A=17.8\%$ vs $B=21.4\%$, impact $-3.0\%$) — the adjustment is not a haircut.
  Fix and document the sign convention (arXiv:2207.02896).
- **Lag, term and down-payment choices.** The two-month lag is assumed; $T=360$ and a single
  fixed-rate product exclude cash and variable-rate buyers. $\alpha$ moves the magnitude only mildly
  (25.4%→22.6% over $\alpha=0.10\to0.20$) but the lag and product choice are not robustness-tested by
  the paper. Sweep them before publishing a number.
- **No forecast, by construction.** The framework explicitly does not predict prices; it filters
  current price/rate combinations (arXiv:2207.02896). A backtest of "sell signal" from the neutrality
  line would be a different, unsupported claim.
- **A null result must be reported as a null.** Koedds' own correlation between SVI and growth is
  **0.126** (below the 0.2 convention) and it ran no forward benchmark; the authors concede the model
  was not validated (arXiv:2503.15532). Do not turn its Midwest ranking into a recommendation.
- **Relative scores are not levels.** MCDA matrix entries are relative positions on a 1–5 scale and
  its weights are preference parameters, not fitted coefficients — results are not comparable across
  assets, and a high NPV on aggressive assumptions is itself a warning (arXiv:2601.22166).
- **Survey scope and representativeness.** The metaverse sample is 164 land owners from a CoinGecko
  audience (male-skewed, young, educated) — self-selected and cross-sectional; treat factor loadings
  as descriptive, not population estimates (arXiv:2308.10309).
- **Simulator calibration is weak.** Only 2 of 10 ward positions are recovered and several parameters
  are chosen by convention; the authors flag the omitted spatial resolution (arXiv:1406.6100). Any
  rent forecast from it is illustrative.
- **Theory without data.** The disintermediation result is a family of derivative inequalities with
  no empirical magnitudes (arXiv:2005.01710); it can structure a narrative but cannot be estimated.

## 5. Recommended first implementation in FinRobot

Ranked by value per unit of effort against what the data layer can fetch today.

1. **Mortgage-rate-adjusted effective price + neutrality line (build first).** *What:* implement
   $\beta,\gamma,g^{*}$ and the $(r,g)$ region classifier from §2.1. *Data:* `fred` `series/observations`
   for the 30-year fixed rate and the HPI; `federal_reserve` treasury CSV as a rate-scenario input.
   *Passing:* reproduces the order of magnitude of Table 3 (≈19–25% of 1987/2000–2021 growth at
   $\alpha=0.20$) and the near-zero pandemic impact (≈3.9%, and $-3.0\%$ for 2021).
2. **Mortgage-rate-neutral HPI series builder.** *What:* the five-step chained neutralisation of
   §2.2, exposed as a derived series. *Data:* same FRED pulls. *Passing:* neutral series ~24% below
   nominal cumulatively over 1987–2021 at $\alpha=0.20$, and *above* nominal for 2021.
3. **Buyer scenario grid generator.** *What:* the $r$-by-$g$ effective-growth table (Baseline rate,
   $T$, $\alpha$ as inputs) for purchase-timing discussions. *Data:* none beyond the rate input.
   *Passing:* matches the published grid (e.g. $g=0,r=6\%\Rightarrow+14.7\%$; $r=3.5\%\Rightarrow-9.1\%$).
4. **Redevelopment MCDA exclusion rubric (no data pipeline).** *What:* six-indicator → three-dimension
   subtractive attractiveness screen from §2.3, with exclusion flags. *Data:* user-supplied asset
   parameters. *Passing:* emits a normalised matrix and at least one documented ex-ante exclusion; do
   **not** label output as a return forecast.
5. **County screen prototype — blocked on data.** *What:* §2.4 scoring against a *manually loaded*
   Redfin/SVI CSV. *Data:* **gap** (county panel, SVI). *Passing:* reproduces the ~0.126 correlation
   null and refuses to publish county rankings as recommendations.
6. **Urban rent simulator — offline only.** *What:* §2.5 on a small lattice; useful for stylised
   segregation studies. *Data:* self-contained (synthetic). *Passing:* reproduces the Sapporo
   top-two ward rent ordering. *Effort:* L, low priority.
7. **Do not build:** a metaverse-land motivation model or a broker-disintermediation decision engine —
   neither has a data feed nor a tradable output (arXiv:2308.10309, arXiv:2005.01710).

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2207.02896v1 | Mortgage-Rate-Adjusted Home Prices | 2022 |
| 2601.22166v1 | A Real-Options-Aware Multi-Criteria Framework for Ex-Ante Real Estate Redevelopment Use Selection | 2026 |
| 2503.15532v1 | Koedds: A National Real Estate Investment Analysis | 2025 |
| 2308.10309v1 | Digital Real Estate in the Metaverse: An Empirical Analysis of Retail Investor Motivations | 2023 |
| 2005.01710v1 | Issues In Disintermediation In The Real Estate Brokerage Sector | 2020 |
| 1406.6100v1 | Probabilistic flows of inhabitants in urban areas and self-organization in housing markets | 2014 |
