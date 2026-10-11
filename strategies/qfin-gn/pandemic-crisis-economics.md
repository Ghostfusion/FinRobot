# Pandemic & Crisis Economics — learnings from the q-fin.GN corpus

`57` of 3095 corpus papers matched this category (55 with PDFs); this doc is based on a close reading of `6`.

Headline: **crisis economics is the thinnest, least tradable slice of `q-fin.GN`.** Of the six papers,
three yield a reusable *crisis/regime method* — a higher-moment tail monitor, a visibility-graph
regime detector, and a cointegration-stability gate — and one is a concrete, checkable *application
error* (the crisis risk-free rate). The remaining two (an e-commerce evolutionary game and a
lockdown-policy SEIR/NSGA-II optimiser) are **economic context, not construction advice**: neither is
expressed over a price series FinRobot can fetch. The bigger constraint is data: the corpus's crisis
findings live in crypto and in Chinese/global *futures*, and `strategies/endpoints.json` serves
neither asset class — so §3 is mostly **gap**. This doc therefore separates (a) what can be estimated
from what FinRobot can actually fetch today and (b) what stays offline until a crypto and a futures
feed exist.

## 1. What the corpus actually offers

- **In the 50 largest cryptocurrencies (≈95% of market cap), the skewness–kurtosis relation is
  quadratic and the pandemic *raises* it.** Panel of 23,499 day-crypto observations, daily
  Apr 1 2019 – Sep 30 2020, split at 31 Dec 2019 into 9 pre / 9 post months; weekly skewness $S$ and
  kurtosis $K$ give 3,423 observations (arXiv:2410.12801v2). Random-effects estimate of
  $K=\beta_0 S^2+\dots$ gives $\beta_0=0.880$ (eq. 7), $0.883$ (eq. 8), $0.855$ (eq. 9),
  $0.893$ (eq. 11), all $p<0.01$; the $S^2\times$COVID interaction is $+0.0464$ ($p<0.01$) and the
  COVID dummy $+0.111$ ($p<0.01$), i.e. the pandemic shifts the *level* of kurtosis, not the
  $S^2$ slope. OLS reproduces the same signs (arXiv:2410.12801v2).
- **Descriptives bound the raw moments:** $S\in[-2.041,2.041]$ (mean 0.082, sd 0.734),
  $K\in[1,5.405]$ (mean **2.473**, sd 0.780). Median of the validity factor is 2.868 and its 75th
  percentile is 10.26; **more than 25% of observations sit in the "extremes dominate" region
  ($\ln\Delta>2.3$) and under 25% in the normality region ($\ln\Delta<0$)** (arXiv:2410.12801v2).
- **The Klaassen bound $K\ge S^2+186/125$ is the binding edge of the crypto scatter; the Cristelli
  universal power law $K=N^{1/3}S^{4/3}$ is rejected** — an important negative result: the
  Skewness–Kurtosis plane in crypto is *not* the one-size-fits-all relation claimed for physics data
  (arXiv:2410.12801v2).
- **Visibility graphs turn crude-oil futures prices into a network whose tail exponent collapses in
  crises.** WTI, Brent and Shanghai (SC) front-month continuous closes, daily plus 5/15/30-min,
  Mar 26 2018 – Jul 20 2023; daily whole-sample $N=1{,}293$ (SC 5-min whole sample 63,034 points)
  (arXiv:2310.18903v3). In the calm sub-sample (Sub1, Mar 2018 – Dec 2019) the degree exponent is
  **exactly $\alpha=3.5$ for all three markets**; post-COVID (Sub2) all $\alpha$ fall, and over the
  whole sample **all $\alpha<3$**, meaning extreme price points become more probable
  (arXiv:2310.18903v3).
- **Global clustering is high and stable (≈0.7):** $C$ ranges $0.6649$–$0.7442$ across markets,
  frequencies and sub-samples, and every VG satisfies the small-world law $L(N)\propto\ln N$
  (arXiv:2310.18903v3).
- **The 5-minute assortativity coefficient $r$ is the single best crisis sentinel in the paper.**
  SC daily $r$ near zero during Sub2 (SC-SP 0.0205, SC-CP 0.0611); WTI/Brent achieve their lowest
  daily $r$ in Sub3 (Russia–Ukraine); the **5-minute $r$ captures the onset of both shocks for all
  three markets**, with SC's mean clustering spiking in Dec 2019 / Jan 2020
  (arXiv:2310.18903v3). WTI settled at **−\$37.63/bbl on 20 Apr 2020**, the anchor for the demand
  shock (arXiv:2310.18903v3).
- **Across all 32 liquid Chinese commodity futures, the pandemic shifted moments and broke
  cointegration.** Most-active contracts, 4 Jan 2016 – 31 Dec 2020, 1,218 trading days
  (arXiv:2106.09250v1). Post-COVID mean daily returns jump for soybean ($0.0001\to0.0017$), corn
  ($0.0000\to0.0015$), corn starch ($0.0001\to0.0012$) and iron ore ($0.0007\to0.0017$); volatility
  rises most for silver (sd $0.0113\to0.0267$), petroleum asphalt ($0.019\to0.027$) and egg
  ($0.0203\to0.0348$); corn skewness flips $−2.61\to0.88$ and its kurtosis collapses
  $71.61\to6.55$, egg kurtosis $76.24\to26.07$, coal kurtosis $9.37\to22.89$ (arXiv:2106.09250v1).
  An Engle–Granger sweep over all pairs reports **176 pairs that lost significant cointegration
  versus 82 that gained it** — a net *contraction* of the pairs-trading universe; gold, petroleum
  asphalt, PTA, sugar and methyl alcohol end un-cointegrated with every other commodity
  (arXiv:2106.09250v1).
- **In crisis, the empirical risk-free rate fell in 22 of ~mainly-developed countries (2021 vs 2020),
  34 countries (2020 vs 2019) and 25 (2019 vs 2018), while rising in 26 (2018 vs 2015)**; the within-
  country spread is extreme (Argentina 5.5%–47.8%) (arXiv:2111.07075v1, citing Fernández et al. 2021).
  The paper's claim is that this is *backwards*: crisis should raise $r_f$, because arbitrage
  opportunities (the sixth of six sources it enumerates) multiply and dominate the weighting
  (arXiv:2111.07075v1).
- **Context, not construction — two papers carry no usable price signal.** The e-commerce study is a
  bounded-rationality replicator-dynamics model: with negative operating markup the retail game has
  *closed orbits and no equilibrium*, with positive markup e-commerce is *bistable* between
  "everyone fast/eager" and "everyone slow/patient" depending on initial shares
  (arXiv:2105.06833v1). Its empirical anchors — Brazil e-commerce +68% in 2020, marketplaces 78% of
  the sector, Amazon Brazil searches +63% Feb 20–Mar 21, complaints +53.5% in 2020Q2, and 6 May 2021
  YTD bank returns (Bradesco −0.29%, Itaú −11.65%, Santander −12.41%, Banco do Brasil −22.29% vs
  Inter +117.05%, BTG +21.62%) (arXiv:2105.06833v1) — are *narrative validation*, not an estimator.
  The lockdown paper (arXiv:2005.08273v1) fits a multi-state SEIR model for nine Indian states and
  optimises a 10-week binary lockdown matrix with NSGA-II (100 generations, population 50) against
  economic cost and average infections; the authors state explicitly they model **no real state** and
  do not forecast. Both are retained only as regime *narrative* and are excluded from §2's tradable
  core.
- **Off-topic check:** none of the six is off-topic for a crisis/pandemic category, but
  arXiv:2105.06833v1 and arXiv:2005.08273v1 are off-topic for *FinRobot's data layer* — they are
  labelled context above and not adjusted into placeholder strategies.

## 2. Implementable formulas & algorithms

### 2.1 Skewness–Kurtosis (S–K) tail monitor
**Purpose.** A cheap, model-free tail-risk / regime gauge for any return panel (crypto, equity,
commodity): track how the higher moments co-move and whether extremes, not the body, dominate the
distribution.

**Formula.** With $S$ and $K$ the (weekly or rolling-window) skewness and kurtosis of daily returns
$r$,
$$S=\frac{1}{N\sigma^3}\sum_{i=1}^N (r_i-\mu)^3,\qquad K=\frac{1}{N\sigma^4}\sum_{i=1}^N (r_i-\mu)^4,$$
$$K_{i,t}=\beta_0 S_{i,t}+\beta_1 S_{i,t}^2+\beta_2 S_{i,t}^2 D_t+\beta_3 D_t+\epsilon_{i,t},$$
and the theoretical bounds $K\ge S^2+1$ and $K\ge S^2+186/125$. A validity ratio for the "extremes
dominate" regime is the paper's $\Delta$ (built after Cristelli et al.), reported on $\ln\Delta$ with
thresholds: normality if $\ln\Delta<0$, intermediate if $0<\ln\Delta<2.3$, extremes if
$\ln\Delta>2.3$. The tested hypothesis is $H_0:\beta_2=0$ (the pandemic does not alter the S–K
interaction).

**Required inputs.** A panel of per-asset daily returns; window for moment estimation; a crisis dummy
$D_t$.

**Parameters & defaults.** The paper computes $S,K$ weekly from daily data and splits 9/9 months at
the WHO outbreak date; panel estimator is random effects, with OLS as a robustness check.

**Observed effect sizes.** $\beta_0(S^2)\approx0.88$ ($p<0.01$) across all four specifications;
$\beta_1(S)\approx-0.021$ ($p<0.05$); interaction $\hat\beta_2=0.0464$ ($p<0.01$); COVID level
shift $\hat\beta_3=0.111$ ($p<0.01$). Post-announcement scatter gains dense clusters at both flanks
with $K>4$ (arXiv:2410.12801v2).

**Failure modes.** In this very sample the *mean weekly kurtosis is 2.473, below the Gaussian value
3* — weekly aggregation and a bounded crypto panel can make the "fat tail" narrative look the
opposite way; do not report $K$ without the window definition and the bound. The regression is
purely in-sample (the COVID dummy is estimated on the same window used to claim the effect) and has
no out-of-sample predictive test. $S,K$ are extremely noisy at weekly frequency; use robust or
quantile-based versions and cross-check. See [`../qfin-st/volatility-modeling.md`](../qfin-st/volatility-modeling.md)
and [`../qfin-st/risk-management-tails.md`](../qfin-st/risk-management-tails.md) for the variance/tail
machinery this monitor should be layered on, and [`../qfin-st/crypto-assets.md`](../qfin-st/crypto-assets.md)
for the crypto data contract.

### 2.2 Visibility-graph regime detector
**Purpose.** Map a price series to an undirected graph and read *regime* off three scalars: the
degree power-law exponent $\alpha$ (tail/extremity intensity), the global clustering $C$ (local
tightness), and Newman's assortativity $r$ (whether extreme points connect to extreme points). It is
a crisis *detector*, not a direction signal.

**Formula.** For price series $\{(t_i,p_i)\}$, nodes $i,j$ are linked iff for all $k$ with
$t_i<t_k<t_j$
$$p_k < p_j+(p_i-p_j)\frac{t_j-t_k}{t_j-t_i}.$$
Degree distribution $p(k)=Ck^{-\alpha}$ (fit $\alpha$ by Clauset MLE; the CCDF exponent is
$\beta=\alpha-1$). Node and global clustering
$$c_i=\frac{2E_i}{k_i(k_i-1)},\qquad C=\langle c_i\rangle=\frac1N\sum_i c_i,$$
small-world check $L(N)\propto\ln N$, and Newman's degree assortativity
$$r=\frac{M^{-1}\sum_i j_i k_i-\big[M^{-1}\sum_i \tfrac12(j_i+k_i)\big]^2}{M^{-1}\sum_i \tfrac12(j_i^2+k_i^2)-\big[M^{-1}\sum_i \tfrac12(j_i+k_i)\big]^2}.$$

**Required inputs.** A price series at a chosen frequency — daily for slow regimes, **5-minute for
crisis onset**. Log or raw prices work (the VG is scale-invariant to affine transforms of $p$).

**Parameters & defaults.** Monthly or sub-sample windows; the paper's cut points are a calm window
(Sub1, 432 daily obs), a COVID window (Sub2, 519 obs), a war window (Sub3, 210 obs) and a
post-overlap window (Sub4, 132 obs), plus monthly M1–M5 windows at 5/15/30-min.

**Observed effect sizes.** $\alpha=3.5$ calm $\to$ $<3$ stressed; $\alpha\in[2,3.5]$ overall;
$C\in[0.6649,0.7442]$; 5-min $r$ rises into both COVID and war onsets for WTI/Brent/SC; SC 5-min
clustering jumps in Dec 2019 / Jan 2020 (arXiv:2310.18903v3).

**Failure modes.** $\alpha$ needs long windows (a 30-day window is too short for a stable Clauset
fit); the VG inherits the series' sampling gaps (the paper's SC high-frequency data has two
multi-month holes); $C$ and $\langle k_{nn}\mid k\rangle$ show *non-monotone* assortative mixing, so
do not read pure disassortativity; WTI/Brent are near-duplicates (their paths coincide), so treat
them as one signal. See [`../qfin-st/correlation-networks-econophysics.md`](../qfin-st/correlation-networks-econophysics.md)
for the broader network-metric toolkit — do not re-derive distance/correlation network theory here.

### 2.3 Cointegration-breakdown gate for pairs trading
**Purpose.** Mid-crisis, the cointegrating set of a commodity/equity universe *contracts*; a pairs
strategy must re-test cointegration on a post-shock window before trusting any pair. Use this as a
universe-selection gate, not as a signal generator.

**Formula.** Engle–Granger: regress $\log P^B_t=a+b\log P^A_t+e_t$ and test the ADF statistic of
$\hat e_t$ against the no-cointegration null ($H_0$: no cointegration). Record, per pair, whether
cointegration exists pre- and post-event, at the 90% / 95% levels.

**Required inputs.** Continuous or most-active log price series per instrument; a split date.

**Parameters & defaults.** The paper uses most-active contracts for the 32 most liquid Chinese
commodity futures, 4 Jan 2016 – 31 Dec 2020 (1,218 days), split at the COVID onset.

**Observed effect sizes.** 176 pairs lost significance, 82 gained; 496 candidate pairs
($\binom{32}{2}$); five commodities end un-cointegrated with everything (arXiv:2106.09250v1).

**Failure modes.** The pre/post split is chosen at the known crisis date — fine for a descriptive
study, **look-ahead if used live**; real-time use requires a rolling ADF with a lag chosen without
peeking. Testing 496 pairs with no multiplicity correction reports ~5% false pairs per level; apply
Benjamini–Hochberg FDR. Most-active splicing creates artificial jumps at contract rolls. See
[`../qfin-st/mean-reversion-pairs.md`](../qfin-st/mean-reversion-pairs.md) for the trading layer.

### 2.4 Crisis risk-free-rate adjustment (an application-error checklist)
**Purpose.** Correct the discount rate fed into CAPM, DCF, Black–Scholes and portfolio optimisation
when markets are stressed. The paper's core claim is directional and *checkable*: traders undercut
$r_f$ in a crisis when the paper argues it should rise.

**Formula.**
$$r_0=W_1 r_1+W_2 r_2+W_3 r_3+W_4 r_4+W_5 r_5+W_6 r_6,$$
with $(r_i)$ = government-bond YTM, bank-deposit rate, interbank (IBL) rate, an expert "constructor"
component, zero-beta-equity return and arbitrage-deal return; $(W_i)$ are the shares of funds the
actor deploys in each segment. The paper's mechanism is that in crisis $W_6$ (and the return on
arbitrage) rises sharply and all other weights become secondary, so $r_0$ should **increase**.

**Required inputs.** A sovereign curve (short and long tenor), deposit/IBL rates, and an internal
measure of arbitrage/zero-beta return. Only the sovereign curve is externally observable.

**Parameters & defaults.** None are given operationally — the paper supplies only relative
significance rankings (bonds high→low, deposits average→low, IBL low→minimum, expert average→minimum,
zero-beta and arbitrage minimum→high across normal→crisis).

**Observed effect sizes.** Direction of empirical $r_f$ moves: 22 countries down (2021/2020),
34 down (2020/2019), 25 down (2019/2018), 26 up (2018/2015); Argentina band 5.5%–47.8%
(arXiv:2111.07075v1).

**Failure modes.** $W_4,W_5,W_6$ are unobservable and the "constructor" weight is explicitly
expert-set — the formula is **not estimable from market data alone** and should not be hard-coded as a
pricing input. Treat it as a *sanity check*: assert that any crisis regime flag either raises or
leaves $r_f$ flat, never silently lowers it. The paper contains no empirics of its own (it is an
opinion/errors piece over a 30-paper SSRN survey), so it earns a checklist role, not a model role.
Pricing/portfolio consumers: [`../qfin-st/derivatives-options.md`](../qfin-st/derivatives-options.md),
[`../qfin-st/portfolio-optimization.md`](../qfin-st/portfolio-optimization.md).

### 2.5 Evolutionary-game sector-regime model (context; conditional on data)
**Purpose.** Model the *share* of consumers/producers adopting a behaviour (fast vs slow) under two
competing strategies — the paper uses it for e-commerce vs traditional retail during lockdowns. It is
the only *generic* two-population regime model in the set.

**Formula.** Replicator dynamics with shares $x$ (eager consumers) and $y$ (fast sellers):
$$\dot x=x(1-x)\big[(U_1-U_3+U_2-U_4)y+(U_4-U_2)\big],\qquad \dot y=y(1-y)\big[(\mu+2\psi)x-\psi\big],$$
interior point $x^\*=\psi/(\mu+2\psi)$, $y^\*=(U_2-U_4)/(U_1-U_3+U_2-U_4)$, Jacobian
$\Omega^\*$ as in eq. (4) of the paper; the sign of the operating markup $\psi$ decides the topology:
$\psi<0$ gives pure-imaginary eigenvalues and **closed orbits (no equilibrium)**, $\psi>0$ gives
**two stable corners**.

**Required inputs.** Strategy shares $x,y$ and utility/markup orderings — no price series directly;
use sector index returns or an adoption proxy.

**Parameters & defaults.** Simulation set $U_1=8,U_2=5,U_3=2,U_4=1$; retail $\psi=-10,\mu=2$;
e-commerce $\psi=10,\mu=2$.

**Observed effect sizes.** Retail: perpetual oscillations from $(x_0,y_0)=(0.4,0.3)$. E-commerce:
bistable; $(0.35,0.60)\to(1,1)$, $(0.65,0.15)\to(0,0)$ (arXiv:2105.06833v1).

**Failure modes.** Parameters are chosen to tell a pandemic story, not estimated; the model has no
stochastic terms (deterministic orbits are fragile); the payoffs are ordinal only. Use only if a
sector-share time series becomes available.

### 2.6 SEIR + NSGA-II lockdown optimizer (context; not market data)
**Purpose.** Balance infection control against economic cost via a multi-objective policy search.
Not a trading strategy; documented so the category is not over-sold.

**Formula.** Multi-state SEIR with interstate travel, hospital-strain fatality
$f_i=0.04\,\frac{0.03}{1+h_i^{0.01}}$ with $h_i=C_i/H_i$; social-distancing transmission factor
$\beta_i=f(I_i)$ following a Granovetter threshold curve; costs
$$C_{\rm med}=c_t I+c_{sp} I,\quad C_{\rm abs}=p_{\rm inc} I,\quad C_{\rm sd}^{\rm sec}=p_{\rm inc}^{\rm sec} P^{\rm sec}\, sd^{\rm sec}.$$
NSGA-II minimises (total cost, average infections) over a binary lockdown matrix of size
states × weeks.

**Required inputs.** State populations, sector income shares, hospital capacity, epidemiological
parameters.

**Parameters & defaults.** 9 Indian states, 10 weeks, 70-day horizon extended to 300 days for cost;
transmission 2.2 (no lockdown) → 1 (lockdown); incubation 5 d, progression 14 d; 20% asymptomatic,
20% serious; hospital capacity 1–2% of population; NSGA-II 100 generations, population 50.

**Observed effect sizes.** Optimal partial lockdown has cost **below** both no-lockdown and full
lockdown while infections sit between the extremes; gradual threshold-curve-I yields lower
infections and slightly higher cost than the step curve-II (arXiv:2005.08273v1).

**Failure modes.** Authors disclaim: no real state is modelled, no forecast intended, aggregate data
only. Keep offline.

## 3. Data requirements → available endpoints

Provider rows are copied from `strategies/endpoints.json`; **gap** means no current provider serves
the input.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily equity/ETF OHLCV (crisis proxies, retail/e-commerce baskets) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Intraday minute bars (5-min VG surrogate) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local OpenD gateway (China/HK names) | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Tradable symbol universe / tick sizes | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Options-implied surface for stress regime | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | ok |
| Sovereign curve for $r_f$ (crisis adjustment) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Policy-rate expectations gauge | `moomoo://get_fed_watch_target_rate` | `fed_watch` | moomoo | gateway (not live-probed) |
| Macro series (inflation, output) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Macro indicator catalogue | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| News sentiment (crisis tone) | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | ok |
| News sentiment (secondary) | `https://www.alphavantage.co/query` | `news_sentiment` | alpha_vantage | ok |
| Global news tone | `https://api.gdeltproject.org/api/v2/doc/doc` | `news_sentiment` | gdelt | rate_limited (HTTP 429) |
| Event contracts (lockdown/policy outcomes) | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | ok |
| **Crypto daily OHLCV (S–K panel, 50 coins)** | — | — | — | **gap** |
| **Crude-oil futures WTI/Brent/SC prices** | — | — | — | **gap** |
| **Chinese commodity futures (most-active contracts)** | — | — | — | **gap** |
| **Retail vs e-commerce sector share / footfall** | — | — | — | **gap** |

**What each gap costs, quantified.** The S–K monitor needs a *crypto* panel: 50 assets × ~18 months,
23,499 day-asset observations at weekly moment granularity (arXiv:2410.12801v2) — no crypto row
exists in the catalogue, so the technique is codeable-but-idle until a crypto feed is registered.
The VG detector needs *intraday futures*: 63,034 (SC) to ~126,000 (WTI) 5-minute points per market
plus daily series of 432–1,293 points (arXiv:2310.18903v3); `moomoo://get_cur_kline` is the only
plausible route but the catalogue does not attest futures coverage, so the SC/WTI/Brent series are a
gap and the detector can run only on equities/ETFs today. The cointegration gate needs 32 most-active
contracts × 1,218 days (arXiv:2106.09250v1): a Chinese futures gap; on US equities the same test runs
on `eodhd` / `tiingo` daily. The risk-free-rate checklist is the one item fully served — the Treasury
CSV gives the sovereign curve; only the internal zero-beta/arbitrage and deposit/IBL terms remain
unobservable by construction.

## 4. Pitfalls, validation and measurement

- **Fixed crisis dates are look-ahead for trading.** Every paper splits at a known event date
  (arXiv:2410.12801v2 at 31 Dec 2019; arXiv:2106.09250v1 at the COVID onset;
  arXiv:2310.18903v3 at 31 Dec 2019 and 24 Feb 2022). That is legitimate for description but must not
  become a live regime label. For a tradable regime detector, use a rolling/online split and score
  the detector on *unseen* onsets — see [`../qfin-st/regime-switching.md`](../qfin-st/regime-switching.md)
  and [`../qfin-st/backtest-methodology.md`](../qfin-st/backtest-methodology.md).
- **Multiple testing dominates the pairs result.** 32 commodities give 496 pairs and the paper
  reports raw 90%/95% counts (176 lost, 82 gained) with no correction (arXiv:2106.09250v1). At 5%,
  ≈25 false cointegrations are expected per sweep. Always apply FDR before acting on any pair.
- **Metric choice changes the story.** Weekly kurtosis in the crypto panel averages 2.473 < 3
  (arXiv:2410.12801v2): a "fat-tailed" claim is window- and frequency-dependent. Report moment
  estimates only with the window length and the $K\ge S^2+186/125$ bound overlaid.
- **In-sample inference, no out-of-sample test.** The S–K regression estimates and tests the COVID
  interaction on the same 18 months (arXiv:2410.12801v2); the VG study reports $C$ and $r$ as time
  series without a formal break test (arXiv:2310.18903v3). Treat both as *diagnostics*, and only
  promote them to signals after a rolling out-of-sample evaluation.
- **Regime dependence is the point, not a nuisance.** The whole category is about non-stationarity:
  cointegration breaks, VG topology shifts, $r_f$ conventions move. Any calibrations (S–K coefficients,
  VG baselines, cointegration lags) must be re-estimated per regime, not pooled across it.
- **Weak/opinion sources must be labelled.** arXiv:2111.07075v1 has no data and no estimation — it is
  an errors essay over a 30-paper survey; use it only as a checklist and cite it as such.
  arXiv:2005.08273v1 self-declares it models no real state, and arXiv:2105.06833v1 sets payoffs to fit
  a narrative; neither should be presented in FinRobot as an empirical result.
- **Cost assumptions are absent everywhere in this set.** No paper includes transaction costs,
  slippage, or borrow costs; none of the signals above is cost-adjusted. Layer any use of §2 on the
  execution/cost machinery in [`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md)
  before trusting a P&L.

## 5. Recommended first implementation in FinRobot

Ranked by value-per-effort against what the data layer can fetch today. Items 1–3 are buildable now
on equities/ETFs; items 4–5 are the honest crypto/futures extensions.

1. **S–K tail monitor as a diagnostic module.** *What:* compute rolling $S,K$, fit the quadratic
   $K=\beta_0 S+\beta_1 S^2\,(+\beta_2 S^2 D)$, and flag regimes via the $K\ge S^2+1$ bound and the
   $\ln\Delta$ bands. *Data:* any return panel (equities via `eodhd`/`tiingo` now; crypto needs a new
   feed). *Passes* when it reproduces $\beta_1(S^2)>0$ with a positive crisis-interaction sign on a
   known stress window without look-ahead. *Effort:* S.
2. **Visibility-graph regime detector.** *What:* build the VG from 5-minute closes and emit monthly
   $\alpha$, $C$, $r$; alert when $\alpha$ drops below its calm baseline and 5-min $r$ rises.
   *Data:* `twelvedata` 1-min (resampled to 5-min) or `moomoo://get_cur_kline`. *Passes* when the
   detector fires on the Feb–Mar 2020 and Feb 2022 windows in an equity/ETF universe. *Effort:* M.
3. **Cointegration-stability gate for the pairs universe.** *What:* rolling Engle–Granger ADF over a
   candidate universe, BH-FDR corrected, that *removes* pairs whose cointegration dies in the latest
   window before the pairs engine trades them. *Data:* `eodhd`/`tiingo` daily. *Passes* when the
   retained pair count contracts around a stress window and out-of-sample pairs' half-life stays
   stable. *Effort:* S–M. Trader in [`../qfin-st/mean-reversion-pairs.md`](../qfin-st/mean-reversion-pairs.md).
4. **Crisis $r_f$ guardrail for pricing and optimisation.** *What:* a single function returning the
   sovereign-curve $r_f$ (from the Treasury CSV) plus a regime flag that *never* lowers $r_f$ when
   stress is on; wire into CAPM/option/portfolio calls. *Data:* `federal_reserve` curve;
   `moomoo://get_fed_watch_target_rate` as a secondary view. *Passes* when every pricing path is
   unit-tested to raise-or-hold $r_f$ under stress. *Effort:* S.
5. **Crypto panel feed for the S–K monitor.** *What:* register a crypto OHLCV category so item 1
   runs on the 50-coin universe the paper uses. *Data:* the feed itself — currently a **gap**.
   *Passes* when the monitor reproduces the paper's crypto-panel moment ranges. *Effort:* M
   (integration).
6. **News-tone regime overlay.** *What:* a crisis-intensity index from `eodhd sentiments` /
   `alpha_vantage news_sentiment` used only to gate the regime detectors of items 2–3. *Data:* those
   endpoints (GDELT currently rate-limited). *Passes* when sentiment spikes coincide with the
   detector windows. *Effort:* M.
7. **(Optional) Sector-regime replicator model** for retail vs e-commerce shares using equity/ETF
   proxies. Only worth it if a sector-share series is added; the model's payoffs are not estimable
   from prices. *Effort:* M.
8. **Lockdown SEIR/NSGA-II optimiser** — explicitly **out of scope** for the trading layer; keep as
   an offline policy notebook only. *Effort:* L, no market payoff.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2410.12801v2 | Exploring the Interplay of Skewness and Kurtosis: Dynamics in Cryptocurrency Markets Amid the COVID-19 Pandemic | 2024 |
| 2310.18903v3 | Visibility graph analysis of crude oil futures markets: Insights from the COVID-19 pandemic and Russia-Ukraine conflict | 2023 |
| 2111.07075v1 | Risk-Free Rate in the Covid-19 Pandemic: Application Mistakes and Conclusions for Traders | 2021 |
| 2106.09250v1 | Effects of Covid-19 Pandemic on Chinese Commodity Futures Markets | 2021 |
| 2105.06833v1 | Trends in the E-commerce and in the Traditional Retail Sectors During the Covid-19 Pandemic: an Evolutionary Game Approach | 2021 |
| 2005.08273v1 | Sustaining the economy under partial lockdown: A pandemic centric approach | 2020 |
