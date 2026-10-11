---
id: systemic-risk-crises
name: Systemic Risk and Contagion Measurement
version: 1.0.0
author: finrobot
domain: risk-management
description: 'Systemic risk and contagion measures: build a market-value-weighted financial-sector system loss panel, copula Δ-CoVaR/Δ-CoES pairwise network estimates, and the implied power-law tail-index early-warning monitor. Use when measuring cross-institutional contagion or systemic-risk build-up.'
triggers:
- systemic risk
- contagion
- covar
- coes
- copula
- financial network
- debtrank
- interbank network
- default cascade
- crisis propagation
requires_data:
- input: Daily OHLCV of financial-sector equities (loss panel, $\Delta$-CoES)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Daily equity prices (secondary, for the panel)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Daily/prev aggregate bars
  provider: massive
  category: core_stock_apis
  status: ok
- input: Daily OHLCV (another source)
  provider: stockdata
  category: core_stock_apis
  status: ok
- input: Intraday bars (coarser than daily, for crisis windows)
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Intraday K-line via local gateway
  provider: moomoo
  category: technical_indicators
  status: gateway
- input: Bank/corporate financial statements (leverage proxy)
  provider: tiingo
  category: fundamental_data
  status: ok
- input: Fundamentals (secondary)
  provider: alpha_vantage
  category: fundamental_data
  status: ok
- input: Macro series (stress-regime conditioning)
  provider: fred
  category: macro_data
  status: ok
- input: Risk-free curve ($\Delta$ baselines, discounting)
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Index option surface (implied crash/tail overlay)
  provider: cboe
  category: options_surface
  status: ok
- input: Option chain via local gateway
  provider: moomoo
  category: options_data
  status: gateway
- input: Institutional holders (ownership overlay)
  provider: moomoo
  category: institution_data
  status: gateway
- input: '**Bilateral interbank exposures $A_{ij}$**'
  provider: ''
  category: ''
  status: gap
- input: '**CDS / credit-default index spreads**'
  provider: ''
  category: ''
  status: gap
- input: '**Money-market (e-MID/overnight) transaction records**'
  provider: ''
  category: ''
  status: gap
- input: '**Structured-credit deal tape (CPDO/CDO tranches, ratings, leverage)**'
  provider: ''
  category: ''
  status: gap
- input: '**Regulatory capital / reserve ratios and leverage per bank**'
  provider: ''
  category: ''
  status: gap
- input: '**Financial-sector classification (SIC 6000–6800 style)**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Systemic Risk and Contagion Measurement

You are an expert systemic-risk researcher specializing in interbank contagion, copula network measures, and financial-crisis propagation. You consume daily financial-sector equity panels, market-value weights, equity co-movement or exposure proxies, and macro stress-regime series from the available endpoints, and you refuse to fabricate bilateral interbank exposures, DebtRank cascade values, or any paper's effect size that no endpoint actually serves.

> Source: FinRobot strategies corpus review — `strategies/qfin-gn/systemic-risk-crises.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **A copula representation collapses all five systemic measures to a univariate quantile problem.**
  For losses $(X,Y)$ with copula $C$, $\mathrm{CoVaR}_{\alpha,\beta}(Y\mid X)=\mathrm{VaR}_{\omega}(Y)$
  and $\mathrm{CoES}_{\alpha,\beta}(Y\mid X)=\mathrm{ES}_{\omega}(Y)$, where $\omega=\omega(\alpha,\beta,C)$
  is the largest root of $\bar C(\alpha,\omega)=(1-\alpha)(1-\omega)$; MES is the special case $\beta=0$
  (arXiv:2206.02582). This turns conditional estimation into *fit a copula, solve one scalar equation,
  estimate a marginal quantile*.
- **A power-law tail exponent is recoverable from the ratio of the two contributions.**
  Under a GPD tail with index $\xi\in(0,1)$,
  $\Delta\text{-CoES}/\Delta\text{-CoVaR}=1/(1-\xi)$ (arXiv:2206.02582). The simulated truth
  ($\xi=0.3131$, Gumbel $\theta=2.22$, $t_3$ margins, $\alpha=\beta=0.95$) gives $\Delta\text{-CoVaR}=5.0718$,
  $\Delta\text{-CoES}=7.3833$, ratio $1.4557$, $\omega=0.9975$ — i.e. the estimator is exact to 4 decimals
  in-sample (arXiv:2206.02582).
- **The empirical tail is where theory says it should be.** On 73 large US financial institutions
  (CRSP daily equity, 31-12-1970–31-12-2020, SIC 6000–6800, 6,182,652 observations over 18,613 days,
  1,564 firms screened, 2,523 weeks), the unconditional power-law coefficient of the system and
  institution loss distributions lands in $[0.3297,0.3972]$, i.e. $\approx1/3$ (arXiv:2206.02582).
- **Daily vs weekly is a hard data constraint, not a preference.** At the 0.95 level the *median* number
  of tail observations used by the CoES estimator is 24 on daily data but only 5 on weekly data; weekly
  $\Delta$-CoVaR rises to mean 0.1012 / $\Delta$-CoES 0.1366 vs daily 0.0487 / 0.0594 (arXiv:2206.02582).
  Use daily.
- **In finite samples every estimator is biased *down*.**
  $\Delta$-CoVaR bias at $n=500$ is $-0.559$ vs $-0.011$ at $n=20{,}000$; $\Delta$-CoES bias is $-2.099$
  at $n=500$ vs $-0.045$ at $n=20{,}000$; reliable estimates need $\ge2000$ observations
  (arXiv:2206.02582, 10,000 Monte-Carlo datasets per size).
- **Sensitivity is the discriminator between the two measures.** The influence function of CoVaR is
  *piecewise constant* in the outlier size $l$; that of CoES is *piecewise linear* beyond
  $\mathrm{VaR}_\omega(Y)$ and can dip negative for intermediate losses — so a *falling* $\Delta$-CoES is
  an early-warning build-up, not an all-clear (arXiv:2206.02582). Lehman's $\Delta$-CoES spikes months
  before bankruptcy while JPM's is flat; the network estimate of $\Delta$-CoES has SD 0.0381 vs
  $\Delta$-CoVaR SD 0.0253 across the 73·72 = 5,256 ordered pairs (arXiv:2206.02582).
- **Scale-free interbank topology decides who is dangerous.** In Bollobás preferential-attachment
  networks of $N=1000$ banks with matched average connectivity $\langle k\rangle\approx2.65$, the
  aggregate Default Impact orders $\mathrm{GD}_0$ (debt-concentrated) $0.48>$ $\mathrm{S}_0$ (symmetric)
  $0.46>$ $\mathrm{GC}_0$ (credit-concentrated) $0.43$, and the aggregate Default Cascade orders
  $0.99>0.79>0.49$; the worst single bank cascades to ~6% of nodes in $\mathrm{GD}_0$ but <1% in
  $\mathrm{GC}_0$ (arXiv:1410.2549). More *connected* credit-concentrated networks are the *most*
  resilient.
- **Topological risk indices only explain losses in debt-concentrated networks.** Counterparty
  susceptibility $CS(i)$ and local network frailty $f(i)$ correlate clearly positively with
  $\mathrm{DI}_i$ for $\mathrm{GD}_0$; the correlation is *smaller* for the more resilient
  $\mathrm{GC}_0$ (arXiv:1410.2549). Asset concentration (Gini 0.83 for $\mathrm{GC}_0$, 0.80 for
  $\mathrm{GD}_0$, 0.78 for $\mathrm{S}_0$; largest bank 122× vs 55× the average) drives single-bank
  impact more than connectivity does.
- **Size and capital move contagion in opposite directions to intuition.** Doubling network size from
  $N=500$ to $N=10{,}000$ leaves aggregate $\mathrm{DI}$ and $\mathrm{DC}$ *unchanged* while shrinking
  every individual bank's impact; raising the capital/assets ratio $\lambda$ from 0.01 to 0.10 lowers
  contagion, with a larger effect on $\mathrm{DC}$ than on $\mathrm{DI}$ (arXiv:1410.2549).
- **A DebtRank cascade has a tractable aggregate measure and a tax that reduces it.**
  On e-MID overnight money-market networks (four one-month aggregates: Apr-2000, Oct-2004, Nov-2008,
  Sep-2009; $N=112$–$177$), a Pigouvian reserve-fund tax of $\alpha=0.01$ of balance-sheet reserves cuts
  expected DebtRank by up to **20%**, and a 1% tax is more effective than a 1% reserve-requirement hike;
  a tax of 2–4 bps of banks' balance is the paper's own proposal (arXiv:1406.5817).
- **Risk-adjusted return need not fall with the tax.** With $ROI^{int}=0.04$, $ROI^{ext}=0.07$,
  $ROI^E=0.03$, $ROI^F=0.02$, $p^O=0.001$, the risk-adjusted ROI is *monotonically increasing* in the
  reserve level $\eta$ despite the nominal ROI drag (arXiv:1406.5817). This is an economics result about
  a regulator's trade-off; it is **not** a tradable edge.
- **Protection evolves, and delay breaks the independence assumption.**
  In an Erdős–Rényi protection ABM ($n=10$, $p=0.9$), the same parameters give failure potentials
  0.527 (enough protection, coexistence), 0.953 (low protection, all-failure), 0.95, or 0.50 (high
  protection, absence of failure) purely through $p_{p,\max}, c_{p,1/2}$ (arXiv:1907.11622). With
  recovery time 1 the failure indicator is binomial (0.4 failure / 0.6 absence over 20 steps); with
  recovery delay 5 the trials become *dependent* and the binomial model fails (arXiv:1907.11622).
- **The CPDO blow-up is fully mechanical and was knowable in 2006.**
  In the ratings-agency coin-toss model (personal capital $\alpha=0.1$, per-toss bet fraction
  $\beta=0.01$, goal $2$), $\mathbb{E}[X_k]=0$ and $\mathrm{Var}(X_k)=(1+\beta^2)^k-1$ grows
  exponentially; the sequence is a martingale; Cash-In is *impossible* in finite time even with a
  two-headed coin; a two-tailed coin Cass-Outs in exactly 10 tosses; and with the modified Cash-In
  (net capital $\ge1$) the probability of Cash-Out is **at least 88.9%** (arXiv:1804.00764). Monte
  Carlo of 1,000 CPDOs × 50,000 tosses returns ≈89% (arXiv:1804.00764).
- **Off-topic/thin-fit note.** arXiv:1412.5452 is *not* a data-driven estimator: it is a measurement
  *design* (Fuzzy Cognitive Map + Choquet integral) whose inputs are expert-elicited causal weights and
  confidence levels — it is retained because §2.5 needs a principled way to aggregate heterogeneous
  vulnerability indicators when data is missing, which is exactly FinRobot's situation for networks.
  None of the six is off-topic; arXiv:1804.00764 is the loosest fit (q-fin.MF structured credit) but is
  kept as the corpus's only worked leverage/blow-up mechanism.

## Methods & Formulas

### 2.1 Copula representation of CoVaR / CoES / $\Delta$-CoES
**Purpose.** Compute a conditional tail measure between two institutions, or between an institution and
the system, without assuming a joint normal.

**Formula.** With losses $(X,Y)$, $X=-P_X$, $Y=-P_Y$, copula $C$ and margins $F_X,F_Y$ (Sklar):
$$F_{X,Y}(x,y)=C\big(F_X(x),F_Y(y)\big),\qquad \bar C(u,v)=1-u-v+C(u,v).$$
Let $\omega=\omega(\alpha,\beta,C)$ be the largest solution of $\bar C(\alpha,\omega)=(1-\alpha)(1-\omega)$.
Then
$$\mathrm{CoVaR}_{\alpha,\beta}(Y\mid X)=\mathrm{VaR}_\omega(Y),\qquad
\mathrm{CoES}_{\alpha,\beta}(Y\mid X)=\mathrm{ES}_\omega(Y),$$
$$\Delta\text{-CoVaR}=\mathrm{VaR}_\omega(Y)-\mathrm{VaR}_\beta(Y),\qquad
\Delta\text{-CoES}=\mathrm{ES}_\omega(Y)-\mathrm{ES}_\beta(Y),\qquad
\mathrm{MES}=\mathrm{CoES}_{\alpha,0}(Y\mid X).$$
Both $\Delta$ measures vanish iff $X,Y$ are independent and are maximal iff they are comonotonic;
$\omega$ rises from $\alpha$ (independence) to the comonotonic bound.

**Required inputs.** Daily (or higher-frequency) loss series for each institution $Y$ and each
conditioning institution $X$; a market-value weight per institution per date to build the system index
(see below).

**Parameters & defaults.** $\alpha=\beta=0.95$. Copula: Gumbel (logistic), $\theta=2.22$ (Kendall
$\tau=0.55$), which lies between independence and comonotonicity and is the natural extreme-value
copula for joint large losses (arXiv:2206.02582). Margins in simulation: standardized $t$ with
$\nu=3$ (so the true $\xi=1/\nu\approx1/3$). System loss definition:
$$X^t_{\rm sys}=\frac{\sum_{i=1}^N MV^{ti}X_{it}}{\sum_{i=1}^N MV^{ti}},$$
the market-value-weighted return (arXiv:2206.02582).

**Observed effect sizes.** Daily unconditional: $\Delta$-CoVaR mean 0.0487 (median 0.0532, SD 0.0111),
$\Delta$-CoES mean 0.0594 (SD 0.0110), ratio mean 1.236. Weekly: 0.1012 / 0.1366 / ratio 1.410. Network
(5,256 pairs): $\Delta$-CoVaR mean 0.0591 (SD 0.0253), $\Delta$-CoES mean 0.0792 (SD 0.0381), $\omega$
median 0.9961 (arXiv:2206.02582).

**Failure modes.** $\omega$ sits at 0.997 of the comonotonic upper bound 0.9975, so tiny estimation error
in $\omega$ explodes into $\Delta$-CoES error; at $n=500$ the bias is $-2.1$ on a true value of 7.4. The
measures are **not classically elicitable/identifiable** and cannot be backtested with VaR-style tests —
use joint-/multiple-objective elicitability tests (arXiv:2206.02582). Under market-value aggregation the
system measure loses cross-sectional heterogeneity (all pairs collapse toward the same band structure),
so network use needs the *pairwise* estimates, not the aggregate.

### 2.2 Power-law tail-index estimator from $\Delta$-CoES/$\Delta$-CoVaR
**Purpose.** A one-number, model-light tail-shape read-out usable as a systemic early-warning indicator.

**Formula.** Under a Generalized Pareto tail of $Y$ beyond $u=\mathrm{VaR}_\alpha(Y)$ with scale $\sigma$
and index $\xi\in(0,1)$,
$$\frac{\Delta\text{-CoES}}{\Delta\text{-CoVaR}}=\frac{1}{1-\xi}\quad(0<\xi<1,\ \omega>\alpha),
\qquad\Longrightarrow\qquad \hat\xi=1-\frac{\Delta\text{-CoVaR}}{\Delta\text{-CoES}}.$$
Equivalently the ratio of the empirical estimators
$\hat\xi = 1 - \widehat{\Delta\text{-CoVaR}}/\widehat{\Delta\text{-CoES}}$
(arXiv:2206.02582).

**Required inputs.** Rolling windows of paired loss series; the same copula fit and $\omega$ solve as 2.1.

**Parameters & defaults.** Rolling window of 2,000 daily observations, re-estimated daily. Compute both
$\Delta$ measures at $\alpha=\beta=0.95$; use the ratio, not either term alone.

**Observed effect sizes.** In simulation the estimator recovers $\xi=0.3131$ against a true $0.3333$;
across 73 institutions the implied $\xi$ has median 0.1637 / mean 0.1826 (daily) and 0.2573 / 0.2593
(weekly). In the crisis case study, $\hat\xi$ for Lehman spikes mid-March 2008, collapses June–early
September, and spikes again 5 days before bankruptcy (arXiv:2206.02582) — the *pattern*, not the level,
is the signal.

**Failure modes.** The hard bound is $\xi>0$; the estimator only exists where the GPD tail holds and
$\omega>\alpha$. Bivariate outliers inflate $\omega$ and deform $\hat\xi$ non-linearly. Negative
estimates occur when the true $\xi\approx0$ and intermediate losses push the ratio below 1
(arXiv:2206.02582) — treat any $\hat\xi<0$ as "tail too light to measure", not as a real negative index.

### 2.3 DebtRank cascade, cascade risk, and the Pigouvian tax
**Purpose.** Quantify the system-wide distress caused by an initial default, turn it into a probability
of being hit by a cascade, and price a rescue-fund tax.

**Formula.** Weighted directed network with exposures $A_{ij}$ (loans $i\to j$), default levels
$E_i=\eta B_i$, distress $\psi_i\in[0,1]$, and propagation
$$h_j(t)=\min\Big\{1,\; h_j(t-1)+W_{ij}\,h_i(t-1)\Big\},\qquad W_{ij}=\frac{A_{ij}}{E_j},$$
each link usable **once** ($l\in\{0,1\}$); the last run is when no unused link can propagate stress
(arXiv:1406.5817). DebtRank $DR_i$ is the fraction of total economic value under distress after shocking
node $i$. With exogenous default probability $p^O_i$ and $Q(i\mid j)$ the conditional cascade
probability,
$$p_i=p^O_i+p^S_i,\qquad p^S_i=\sum_{j\neq i}Q(i\mid j)\,p^O_j,\qquad
p^C_i=\frac{\sum_{j\neq i}Q(i\mid j)\,p^O_j}{\sum_{j\neq i}p^O_j}.$$
$p^C_i$ is scale-invariant in the exogenous probabilities. Under uniform $p^O$,
$p^C_i=\Delta_i/(N-1)$ and the system cascade risk is
$p^C=\sum_i\Delta_i/\big(N(N-1)\big)$ (arXiv:1406.5817). Rescue-fund design: $B_i=\beta\max(S_{iB},S_{iL})$,
$E_i=\eta B_i$, $F_i=\alpha E_i$, with the fund paid to the *counterparties* of the first defaulter
(never to the defaulter) to suppress moral hazard. Risk-adjusted return:
$$ROI^{RA}_i=ROI^N_i\,(1-p_i)-p_i.$$

**Required inputs.** The weighted directed exposure matrix $A_{ij}$; a balance-sheet scale $B_i$; the
reserve ratio $\eta$; the tax rate $\alpha$.

**Parameters & defaults.** $\beta=10$ (tested $\beta\in[4,20]$), $\eta\in[0,0.05]$, $\alpha\in[0,1]$;
$ROI^{int}=0.04$, $ROI^{ext}=0.07$, $ROI^E=0.03$, $ROI^F=0.02$, $p^O=0.001$; policy tax 2–4 bps of
balance (arXiv:1406.5817).

**Observed effect sizes.** $\alpha=0.01$ cuts expected DebtRank by up to 20%; cascade risk falls
sharply for $\eta\in[0.001,0.01]$; for a fixed $\eta$ a 1% tax beats a 1% reserve hike; networks from
2008–2009 show *lower* cascade risk than 2000–2004 networks (self-protective behaviour), with the
qualitative ordering identical across all four monthly networks (arXiv:1406.5817).

**Failure modes.** DebtRank is deterministic given initial conditions, so $Q(i\mid j)$ is modelled as a
binomial variable — an approximation, and the networks are tiny ($N=112$–177) and aggregated to four
single months. The definition excludes capital loss and real-economy impact; it measures only the
*probability* a given node is reached by a cascade. The ROI model assumes total loss on default.

### 2.4 Default Impact / Default Cascade on a synthesised scale-free interbank network
**Purpose.** Stress-test which bank is dangerous when only topology (degrees), not exposures, is observed.

**Formula.** Balance sheets built from connectivity alone:
$$BA_i=\sum_{j\in k^i_{\rm in}} w_{ji},\quad BL_i=\sum_{j\in k^i_{\rm out}} w_{ij},\quad
w_{ij}=\frac{k^i_{\rm out}\,k^j_{\rm in}}{k^{\max}_{\rm out}\,k^{\max}_{\rm in}},$$
$$NBA_i=\xi\,(BA_i+BL_i),\qquad E_i=\lambda_i\,(BA_i+NBA_i),$$
$$NBL_i=(1-\lambda_i)(1+\xi)\,BA_i+\big[(1-\lambda_i)\xi-1\big]BL_i.$$
Cascade from a single insolvent bank via the Eisenberg–Noe payment-vector clearing algorithm. Measures
(reduction in total system assets $A_0\to A_t$):
$$\mathrm{DI}_i=\frac{A_0-A_t}{A_0}\ (\text{contagion only}),\qquad
\mathrm{TI}_i=\mathrm{DI}_i+\frac{NBA_i}{A_0},\qquad
\mathrm{DC}_i=\frac{\#\{\text{banks insolvent due to }i\}}{N}.$$
Aggregates $\mathrm{DI}=\sum_i\mathrm{DI}_i$, $\mathrm{DC}=\sum_i\mathrm{DC}_i$. Local indices:
$$CS(i)=\max_{j\in E_j}\frac{w_{ij}}{E_j},\qquad f(i)=\text{same maximal exposure reweighted by }BL_j.$$

**Required inputs.** A directed degree sequence (in/out) per bank; a capital ratio $\lambda_i$; the
nonbank scale $\xi$.

**Parameters & defaults.** Bollobás preferential attachment with $\alpha+\gamma=0.75$,
$\delta_{\rm in}+\delta_{\rm out}=4$, and the exponent constraint
$X_{\rm out}=(X_{\rm in}+15)/(X_{\rm in}-1)$; target $X_{\rm in},X_{\rm out}\approx2$–$3$. Reference
triples: $\mathrm{GD}_0\,(8.43,3.15)$, $\mathrm{S}_0\,(5.00,5.00)$, $\mathrm{GC}_0\,(3.15,8.43)$.
$N=1000$ (also 500/5000/10000), 20 realizations per type, $\xi=2$, $\lambda\in\{0.01,0.05,0.10\}$
(use $\lambda=0.05$) drawn as $\lambda_i\sim N(\lambda,\sigma)$ truncated above the minimum.
Estimating power-law exponents: MLE for discrete power laws (Clauset et al.).

**Observed effect sizes.** $\langle k\rangle\approx2.65$; Gini(in-degree) 0.418 (GD0) / 0.578 (S0) /
0.748 (GC0). Aggregated DI/DC as in §1. Top-bank coefficient of variation ≈40% of its mean, so rank-1
estimates are noisy.

**Failure modes.** $N=1000$ is far from the asymptotic limit: realised exponents fall in 2.2–3.2 vs limit
values 3.15–8.43 (convergence from the left). Comparisons across network *types* confound connectivity
with concentration unless the type-1..4 variants are used to separate them. A smaller exponent means a
*more* concentrated distribution — do not read the exponent's sign naively. The weight rule is a
modelling choice, not an observation.

### 2.5 Choquet integral over a Fuzzy Cognitive Map
**Purpose.** Aggregate heterogeneous vulnerability indicators/decomposed segments into one systemic-risk
level while respecting their non-additive interdependence (used when bilateral data is absent).

**Formula.** A fuzzy measure on $N=\{1,\dots,n\}$ is a monotone set function
$\mu:\mathcal P(N)\to[0,1]$, $\mu(\varnothing)=0$, $\mu(N)=1$, $A\subseteq B\Rightarrow\mu(A)\le\mu(B)$.
The discrete Choquet integral of evaluations $x_1,\dots,x_n$:
$$C(x_1,\dots,x_n)=\sum_{i=1}^{n}\big(x_{(i)}-x_{(i-1)}\big)\,\mu\big(\{c_{(i)},\dots,c_{(n)}\}\big),
\qquad x_{(0)}=0,$$
with $x_{(1)}\le\dots\le x_{(n)}$ an ascending permutation. Expert weights are confidence-weighted:
$$w(S_l,S_m)=\frac{\sum_{i,j}r_{ij}(S_l,S_m)\,w_{ij}(S_l,S_m)}{\sum_{i,j}r_{ij}(S_l,S_m)}.$$
The map is a hierarchical directed graph $SR\to\{S_1,\dots,S_t\}\to\{s_{i,1},\dots,s_{i,p_i}\}$; edge
weights live in $[0,1]$ and are *not* symmetric, so $w(S_l,S_m)\ne w(S_m,S_l)$ (arXiv:1412.5452).

**Required inputs.** Per expert, per cell: an adjacency value and a confidence $r_{ij}$; a hierarchy of
segments (country → sector → sub-dimension). Optionally a normalisation of node values to $[0,1]$.

**Parameters & defaults.** Two applications: (i) pan-European systemic risk, SR → countries → sectors;
(ii) single-country, SR → the country → its sectors → sub-dimensions. Graph analysis uses standard
centrality (in/out strength, eigenvector) to label receiver (vulnerable) vs transmitter (contagious)
nodes (arXiv:1412.5452).

**Observed effect sizes.** The paper reports the framework and European applications qualitatively;
it is a design contribution with no out-of-sample statistics, so no effect size can be quoted.

**Failure modes.** Everything rests on elicitation; there is no objective loss function to validate
$\mu$ or the weights. Non-symmetric weights mean the aggregated map must be treated as a directed graph,
not a correlation matrix. This is an aggregation *protocol*, not a predictive model — do not report its
output as a return or risk forecast.

### 2.6 Evolving-protection agent-based contagion (simulation-only)
**Purpose.** Study how *adaptive* protection investment changes cascade size — relevant to regime
analysis and stress-scenario design, not to live signals.

**Formula.** Protection function and strategy:
$$p_p=\frac{p_{p,\max}}{1+c_{p,1/2}/(f_p\,c)},\qquad f_p=f_{p0}+f_{p1}\,C\ \text{truncated to }(0,1-f_m),$$
where $c$ is capital, $C\in(0,1)$ the (eigenvector) centrality of the node. Capital update
$c\mapsto 1+(1-f_m-f_p)c$. Failure potential originates at a node w.p. $p_n$, propagates along each link
w.p. $p_l$, and turns into failure w.p. $1-p_p$. Social learning: imitate a role model with probability
$$p_i=\frac{1}{1+e^{-s\,\Delta c}},$$
and explore with probability $p_e$ via a normal increment $N(0,\sigma_e)$ on $f_{p0}$ or $f_{p1}$.

**Required inputs.** None live — this is self-contained; calibrate $p_n,p_l,s,\sigma_e$ against an
observed default/loss frequency for realism.

**Parameters & defaults.** $n=10$ or $100$, $p=0.9$ / $0.1$; $f_{p0}=0.4$, $f_{p1}=0.5$, $f_m=0.1$,
$s=1$, $\mu=0$, $\sigma=0.1$, $p_n=0.1$, $p_l=0.3$, $t=10$–$1000$; $\alpha_{p,\max}\in\{0.1,1\}$,
$c_{p,1/2}\in\{0.1,0.5,1\}$ (arXiv:1907.11622).

**Observed effect sizes.** Identical networks tip between coexistence and total failure purely through
$p_{p,\max},c_{p,1/2}$ (failure potentials 0.527 vs 0.953 at fixed $f_p=0.9$); with recovery time 1 the
failure indicator is binomial 0.4/0.6, with recovery time 5 it is non-independent; strong connection
($p=0.9$) with strong imitation/exploration ($p_r=p_e=0.9$) yields a *symmetric* centrality–protection
relation, weak connection an asymmetric one (arXiv:1907.11622).

**Failure modes.** Parameters are artificial and the paper describes the implementation as "still needing
polishing against the real world." The binomial/independence assumption is provably violated by recovery
delay — do not apply binomial tail bounds to delayed-recovery paths. Simulation-only: no market data,
no return claim.

### 2.7 CPDO cash-out / martingale analytics (leverage validation)
**Purpose.** A closed-form validator for any leveraged "bet-more-after-a-loss" structure: prove up front
that it almost surely Cass-Outs, and size the leverage at which it does.

**Formula.** Stake $Y_k$, net capital $X_k=Y_k-1$, coin $C_k=\pm1$, bet fraction $\beta$:
$$Y_k=Y_k-1+\beta(2-Y_{k-1})C_k\quad\Longrightarrow\quad X_k=1-\prod_{j=1}^{k}(1-\beta C_j),$$
$$\mathbb{E}[X_k]=0,\qquad \mathrm{Var}(X_k)=(1+\beta^2)^k-1.$$
Cash-Out when $X_k\le-\alpha$ (personal capital $\alpha$); the two-tailed coin Cass-Outs at
$k=\ln(1+\alpha)/\ln(1+\beta)$; with $\alpha=0.1,\beta=0.01$ this is $9.58\to10$ tosses. With
Cash-In redefined as $X_k\ge1$, the Law of Total Probability on the martingale gives
$$\Pr(\text{Cash-Out})\ \ge\ 1-(\alpha+\beta+\alpha\beta)=0.889.$$

**Required inputs.** Personal-capital fraction $\alpha$, bet fraction $\beta$, leverage
($\alpha=0.0625$ at 15×), and the Cash-Out threshold — i.e. the term sheet, not an endpoint.

**Parameters & defaults.** $\alpha=0.1$, $\beta=0.01$ (1% of the distance to goal), goal $2$; at 15×
leverage $\alpha=0.0625$, borrowed $0.9375$ (arXiv:1804.00764).

**Observed effect sizes.** $\Pr(\text{Cash-Out})\ge0.889$; Monte Carlo 1,000 CPDOs × 50,000 tosses gives
≈0.89; 108,220 tosses (≈54,000 years at semi-annual steps) are needed for a 95% chance of $X_k\ge0.9$;
$\Pr(X_k<0)$ is exactly 0.5 for odd $k$ and $\approx0.5$ for even $k$ up to $k\approx200$
(arXiv:1804.00764).

**Failure modes.** The market analogue ignores the mean-reversion the strategy itself assumes — the
paper's central point is that the CPDO strategy bets *more* after a loss, the opposite of Kelly/Whitworth,
and in a subfair casino the probability of doubling is at most 50% under *any* strategy. Use it as an
accept/reject test for leverage proposals, never as a tradable strategy.

## Data Requirements

Rows are copied verbatim from `strategies/endpoints.json`; **gap** means no current provider serves it.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV of financial-sector equities (loss panel, $\Delta$-CoES) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily equity prices (secondary, for the panel) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily/prev aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Daily OHLCV (another source) | `https://api.stockdata.org/v1/data/eod` | `core_stock_apis` | stockdata | ok |
| Intraday bars (coarser than daily, for crisis windows) | `https://api.twelvedata.com/time_series` (`interval=1min`) | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Bank/corporate financial statements (leverage proxy) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| Fundamentals (secondary) | `https://www.alphavantage.co/query` | `fundamental_data` | alpha_vantage | ok |
| Macro series (stress-regime conditioning) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Risk-free curve ($\Delta$ baselines, discounting) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Index option surface (implied crash/tail overlay) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | ok |
| Option chain via local gateway | `moomoo://get_option_chain` | `options_data` | moomoo | gateway (not live-probed) |
| Institutional holders (ownership overlay) | `moomoo://get_shareholders_institutional` | `institution_data` | moomoo | gateway (not live-probed) |
| **Bilateral interbank exposures $A_{ij}$** | — | — | — | **gap** |
| **CDS / credit-default index spreads** | — | — | — | **gap** |
| **Money-market (e-MID/overnight) transaction records** | — | — | — | **gap** |
| **Structured-credit deal tape (CPDO/CDO tranches, ratings, leverage)** | — | — | — | **gap** |
| **Regulatory capital / reserve ratios and leverage per bank** | — | — | — | **gap** |
| **Financial-sector classification (SIC 6000–6800 style)** | — | — | — | **gap** |

**What the gaps cost, in the papers' own units.** The copula measures need $T\ge2000$ daily observations
*per institution pair*; the reference study used 73 institutions = 5,256 pairs over 18,613 days
(arXiv:2206.02582) — FinRobot can supply the equity side, so this half is **buildable today**. DebtRank
and cascade risk need the *entire* weighted directed exposure matrix; the reference networks had
$N=112$–177 nodes from four single-month aggregates of a single venue (arXiv:1406.5817) — without it,
$\Delta_i$ cannot be computed for any real system and the tax simulation stays synthetic. The Default
Impact study needs 20 realizations of $N=1000$ synthetic networks with full balance sheets
(arXiv:1410.2549); the topology can be simulated, but the calibration to real exposures cannot. A CDS
event study would additionally need 5-year CDS log-returns thresholded at each firm's own 99th
percentile. The CPDO validator needs no market data — only the deal term sheet — and is the one item
in §2 that is fully runnable offline.

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Systemic conditional measures are not backtestable the classical way.** CoVaR/CoES have multiple
  sources of variation (VaR model, copula, ES model), so they are not elicitable/identifiable in the
  sense of Gneiting; use joint elicitability or multiple-objective tests, and remember ES-style
  backtests check both the *number* and the *severity* of violations (arXiv:2206.02582).
- **Every historical estimate is biased down and needs $\ge2000$ observations.** At $n=500$ the
  $\Delta$-CoES bias is $-2.1$ (true 7.38); weekly aggregation leaves a median of 5 tail observations
  (arXiv:2206.02582). Never report a point estimate without the window length.
- **A falling $\Delta$-CoES is a warning, not an all-clear.** Intermediate losses push the sensitivity
  function negative before large losses pull it back up — sharply decreasing estimates signal risk
  build-up (arXiv:2206.02582).
- **Metric choice is directional.** MES is *unsuitable* for extreme risk (it is the special case
  $\beta=0$; it cannot satisfy $\xi>0$ and reacts to profits as well as losses); ES-based measures are
  more tail-sensitive and less robust, making them better for *network* risk, while $\Delta$-CoVaR is
  more stable and better for long-horizon build-up (arXiv:2206.02582).
- **Aggregation hides heterogeneity.** With market-value-weighted $Y$, the system-level $\Delta$ measures
  show little cross-sectional variation; only the pairwise network estimates recover it
  (arXiv:2206.02582).
- **Topology alone does not predict contagion; direction does.** Positive correlation between $CS(i)$,
  $f(i)$ and $\mathrm{DI}_i$ holds for debt-concentrated networks and weakens for resilient ones; and
  realisation at $N=1000$ is far from the asymptotic exponents (2.2–3.2 vs 3.15–8.43)
  (arXiv:1410.2549). Cross-network comparison is only legitimate with a fixed stress scenario, because
  the wording of "loss" depends on the assumed shock.
- **Sample split and regime dependence are first-order.** Cascade risk is *lower* for 2008–2009
  networks than 2000–2004, plausibly because banks self-protected during the crisis; any calibration
  must be re-estimated per regime (arXiv:1406.5817). In the ABM, recovery delay breaks trial
  independence and invalidates binomial confidence intervals (arXiv:1907.11622).
- **Assume dependence only where it exists.** The CPDO strategy depends on mean-reversion that in fact
  contradicts the martingale property $\mathbb{E}[X_{k+1}\mid X_k]=X_k$; the "heads is due" logic is
  gambler's fallacy (arXiv:1804.00764). Mirror this as a null test: any levered strategy must pass
  $\mathbb{E}[X_{k+1}\mid X_k]=X_k$ before it is attributed an edge.
- **Expert-elicited aggregates have no null.** The FCM/Choquet design provides no out-of-sample check;
  its validity rests entirely on elicitation discipline and per-cell confidence weights
  (arXiv:1412.5452).
- **Tax/regulation results are welfare statements, not returns.** The Pigouvian result (2–4 bps or
  $\alpha\approx1\%$ preferred over a 1% reserve hike) is about a regulator's stability–inefficiency
  trade-off and assumes total loss on default (arXiv:1406.5817); do not encode it as an alpha signal.

## Recommended Workflow

Ranked by value-per-effort against what the layer can fetch today. Items 1–3 are buildable now;
items 4–8 need inputs that are **gap**.

1. **Financial-sector equity panel + market-value-weighted system index.** *What:* fetch daily OHLCV for
   a list of financial names, compute $X^t_{\rm sys}=\sum MV_i X_i/\sum MV_i$. *Data:* eodhd `eod` /
   tiingo `prices` / stockdata `eod`. *Passing result:* reproducible daily system loss series and
   per-institution loss series with no gaps over $\ge2000$ trading days. *Effort:* S.
2. **Copula $\Delta$-CoVaR / $\Delta$-CoES network measure.** *What:* fit an empirical beta or Gumbel
   copula per pair, solve $\bar C(\alpha,\omega)=(1-\alpha)(1-\omega)$, return
   $\mathrm{VaR}_\omega-\mathrm{VaR}_\beta$ and $\mathrm{ES}_\omega-\mathrm{ES}_\beta$ per ordered pair at
   $\alpha=\beta=0.95$. *Data:* item 1. *Passing result:* on the 73-name reference the network
   $\Delta$-CoES SD exceeds $\Delta$-CoVaR SD (target ≈0.038 vs 0.025), and the two failed institutions
   (LEH, BSC) rank high when they are the conditioned $Y$ (arXiv:2206.02582). *Effort:* M.
3. **Tail-index early-warning estimator + rolling monitor.** *What:* compute
   $\hat\xi=1-\Delta\text{-CoVaR}/\Delta\text{-CoES}$ on a 2,000-observation rolling window, daily.
   *Data:* item 2. *Passing result:* $\hat\xi$ recovers $\approx1/3$ on $t_3$-heavy synthetic data and
   flags the Lehman pre-bankruptcy spike pattern out-of-sample. *Effort:* S (given item 2).
4. **DebtRank cascade module on a synthesised exposure proxy.** *What:* port $h_j(t)=\min\{1,h_j(t-1)+
   W_{ij}h_i(t-1)\}$ (links used once) and $p^C_i=\Delta_i/(N-1)$, fed by an aggregate interbank proxy
   or correlation network. *Data:* requires $A_{ij}$ — **blocked**; can be prototyped on the equity
   correlation network as a documented substitute. *Passing result:* reproduces the paper's ordering
   (debt-concentrated > symmetric > credit-concentrated) on synthetic Bollobás networks. *Effort:* M.
5. **Scale-free interbank generator + Default Impact/Cascade stress test.** *What:* Bollobás
   preferential attachment with the exponent constraint
   $X_{\rm out}=(X_{\rm in}+15)/(X_{\rm in}-1)$, balance-sheet synthesis, Eisenberg–Noe clearing, output
   $\mathrm{DI}_i,\mathrm{DC}_i$ and $CS(i),f(i)$. *Data:* synthetic; calibrate against item 4. *Passing
   result:* aggregate $\mathrm{DI}/\mathrm{DC}$ order GD0 > S0 > GC0 with the published values
   (0.48/0.46/0.43 and 0.99/0.79/0.49). *Effort:* L.
6. **Pigouvian rescue-fund tax scenario simulator.** *What:* add $F_i=\alpha E_i$ to the item-5 network,
   compute $p^C(\alpha,\eta)$ and $ROI^{RA}_i(\alpha)$. *Data:* synthetic exposure matrix — **blocked**
   without real interbank data. *Passing result:* reproduces the sign pattern ($\alpha=0.01$ cuts DR by
   up to 20%; 1% tax dominates a 1% reserve hike). *Effort:* M (after item 5).
7. **CPDO / leverage accept–reject validator.** *What:* given a term sheet ($\alpha,\beta$, goal,
   Cash-Out rule), evaluate the recurrence, $\mathrm{Var}(X_k)=(1+\beta^2)^k-1$, the two-tailed
   Cass-Out toss count, and the $\Pr(\text{Cash-Out})\ge1-(\alpha+\beta+\alpha\beta)$ bound. *Data:*
   none. *Passing result:* flags a 15× ($\alpha=0.0625$) structure as $\ge88.9\%$ Cash-Out. *Effort:* S.
8. **FCM + Choquet expert-aggregation dashboard.** *What:* only if FinRobot acquires a supervisory
   panel; encode the hierarchy, per-cell confidences, and the Choquet integral over a fuzzy measure.
   *Data:* expert input — **gap**. *Passing result:* monotone aggregation ($A\subseteq B\Rightarrow
   \mu(A)\le\mu(B)$) and reproducible receiver/transmitter rankings. *Effort:* M.

Statistical tail machinery (Hill/Pareto estimators, GARCH-EVT, reverse stress testing, a multiplex
Hawkes systemic-risk measure) is already derived in
[`../qfin-st/risk-management-tails.md`](../qfin-st/risk-management-tails.md); use it for the marginal
tails and keep this doc to network topology, contagion dynamics and measure design. Equity co-movement
networks as an exposure proxy are covered in
[`../qfin-st/correlation-networks-econophysics.md`](../qfin-st/correlation-networks-econophysics.md),
and the agent-based simulator in
[`../qfin-st/market-simulation-agent-models.md`](../qfin-st/market-simulation-agent-models.md).

## Output Format

### Pairwise Network Measures
| Ordered pair (Y | X) | Δ-CoVaR | Δ-CoES | ω | implied ξ̂ | window n |
|----------------------|---------|--------|-----|-----------|----------|
| ... | ... | ... | ... | ... | ... |

### System Index and Monitor
| Date | X_sys (MV-weighted) | rolling ξ̂ | Δ-CoVaR SD | Δ-CoES SD | flag |
|------|---------------------|-----------|------------|-----------|------|
| ... | ... | ... | ... | ... | ... |

### Verdict
State the buildable half (equity panel -> system index -> copula pair measures ->
tail-index monitor) with its window length and the ≥2000-observation bias caveat;
label the DebtRank / Default-Impact / Pigouvian-tax / FCM-Choquet arms as **gap**
(bilateral interbank exposures, CDS spreads, money-market records, expert weights),
report the CPDO validator as offline-only leverage accept/reject, and never present
a welfare or regulation result as a return signal.

## References

| arXiv id | Title | Year |
|---|---|---|
| 1410.2549v1 | Propagation of Systemic Risk in Interbank Networks | 2014 |
| 2206.02582v2 | Making heads or tails of systemic risk measures | 2022 |
| 1907.11622v1 | Network and Agent Dynamics with Evolving Protection against Systemic Risk | 2019 |
| 1804.00764v1 | Constant Proportion Debt Obligations, Zeno's Paradox, and the Spectacular Financial Crisis of 2008 | 2018 |
| 1412.5452v2 | Aggregation operators for the measurement of systemic risk | 2014 |
| 1406.5817v1 | Reduction of systemic risk by means of Pigouvian taxation | 2014 |
