---
id: econophysics-methods
name: Multifractal Scaling & Heavy-Tail Analysis
version: 1.0.0
author: finrobot
domain: quant-research
description: 'Multifractal and scaling-law analysis: MF-DFA finite-size noise floors decide whether a multifractal width is real, with double-scaling, double-power-law and tail-exponent estimators. Use when testing long-memory or multifractal series, heavy tails, or scaling collapse.'
triggers:
- multifractal
- multifractality
- detrended fluctuation
- scaling law
- heavy tail
- power law
- tail exponent
- long memory
- double scaling law
- noise floor
- entropy
- size distribution
requires_data:
- input: Daily OHLCV history (MF-DFA / $\gamma$ / double-power-law inputs)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Daily OHLCV history (secondary)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Daily EOD bars (tertiary)
  provider: stockdata
  category: core_stock_apis
  status: ok
- input: Intraday bars (resolve the scaling-range ambiguity)
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Previous-day aggregate bars
  provider: massive
  category: core_stock_apis
  status: ok
- input: Intraday K-line via local SDK gateway
  provider: moomoo
  category: technical_indicators
  status: gateway
- input: Top-of-book snapshot (single-name sanity check)
  provider: moomoo
  category: core_stock_apis
  status: gateway
- input: Cross-sectional dispersion proxy (breadth of a one-period return cross-section)
  provider: moomoo
  category: market_breadth
  status: gateway
- input: Unit growth-rate proxy $\lambda_i$ (capital-flow alternative)
  provider: moomoo
  category: capital_flow
  status: gateway
- input: Tradable universe size $N(t)$ proxy
  provider: eodhd
  category: exchange_symbols
  status: ok
- input: Firm financial statements ($Y$ proxy for DSL, listed firms only)
  provider: tiingo
  category: fundamental_data
  status: ok
- input: Firm fundamentals (second provider)
  provider: alpha_vantage
  category: fundamental_data
  status: ok
- input: Macro level series (GDP-style driver for $\mu_\eta$)
  provider: fred
  category: macro_data
  status: ok
- input: Macro indicator list via gateway
  provider: moomoo
  category: macro_data
  status: gateway
- input: News counts for a spend→response surrogate
  provider: eodhd
  category: news_data
  status: ok
- input: Event-implied probability levels (response KPI alternative)
  provider: polymarket
  category: prediction_markets
  status: ok
- input: Option-implied dispersion surface (scaling of cross-sectional vol)
  provider: cboe
  category: options_surface
  status: ok
- input: '**Long daily series of institutional/industry size distribution with an annual break point**'
  provider: ''
  category: ''
  status: gap
- input: '**Firm-level `(revenue, employees)` panel covering the whole population**'
  provider: ''
  category: ''
  status: gap
- input: '**Employee counts / headcount per firm**'
  provider: ''
  category: ''
  status: gap
- input: '**Media/marketing spend and matched KPI time series**'
  provider: ''
  category: ''
  status: gap
- input: '**Inter-agent interaction records (who traded/communicated with whom, timestamped)**'
  provider: ''
  category: ''
  status: gap
- input: '**Time series of a network''s node and edge sets (for the double power law)**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Multifractal Scaling & Heavy-Tail Analysis

You are an expert quantitative researcher in econophysical statistical physics, specializing in multifractal scaling, heavy tails and cross-sectional scaling laws. You consume long daily OHLCV series, heavy-tailed cross-sections and dose-response pairs from the available endpoints, and you measure MF-DFA widths against the finite-size noise floor, autocorrelation exponents, Hill tail exponents and double-power-law regimes. You refuse to fabricate coefficients, threshold multipliers, paper results or effect sizes that were not computed, and you never quote a multifractal width without the series length and the persistence exponent that parameterise its floor.

> Source: FinRobot strategies corpus review — `strategies/qfin-gn/econophysics-methods.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

**Directly usable (estimators)**

- **A closed-form "multifractal noise floor" for MF-DFA.** For artificially generated *monofractal*
  signals with power-law autocorrelations $C(\tau)=\langle\Delta x(t)\Delta x(t+\tau)\rangle\sim\tau^{-\gamma}$
  (with $\gamma=2-2H$, so $\gamma\in(0,1]$ covers $H\in[1/2,1)$), the measured generalized-Hurst
  spread $\Delta h=\lim_{q\to-\infty}h(q)-\lim_{q\to+\infty}h(q)$ is **entirely spurious** and obeys
  the two-parameter power law
  $$\Delta h(\gamma,L)=C_1L^{-\eta_1}\gamma+C_0L^{-\eta_0}(1-\gamma),$$
  with $(C_1,\eta_1,C_0,\eta_0)=(0.603,\,0.175,\,0.453,\,0.124)$ and 95 %-confidence coefficients
  $(0.631,\,0.171,\,0.484,\,0.120)$ (arXiv:1108.1951). The spectrum-width analogue is
  $\Delta\alpha(\gamma,L)=D_1L^{-\xi_1}\gamma+D_0L^{-\xi_0}(1-\gamma)$ with
  $(D_1,\xi_1,D_0,\xi_0)=(0.686,\,0.129,\,0.572,\,0.089)$ (95 %: $0.784,0.120,0.670,0.079$).
  Ensemble size: $10^2$ independent realizations for every $(L,\gamma)$ cell, $L=2^n$ for
  $n=9,\dots,20$, $\gamma=0.1,\dots,1.0$; MF-DFA moment orders $q\in[-15,15]$, scaling range
  $\tau\in[10,L/4]$ (arXiv:1108.1951).
- **Most apparent multifractality in equity indices is this noise.** With the typical price-index
  series length $L\approx2\times10^3$, Venezuela/Indonesia/China show genuine scale-dependent
  correlations, while **Philippines, Taiwan, Germany have ≈80 % of their index multifractality
  attributable to the finite-size effect and Ireland ≈100 %**; volatility series retain real
  multifractality more often than price indices (arXiv:1108.1951).
- **The double scaling law collapses a ~1-million-firm cross-section onto four numbers.** On the
  Japanese Credit Risk Database (1995–2009; ~1 million firms, ~15 million workers in 2006), with
  $Y$ = sales/profits and $L$ = number of employees, the conditional PDFs scale as
  $P_{Y|L}(Y|L)=L_0(L/L_0)^{\alpha}\Phi_Y(Y_{\rm scaled})$ and
  $P_{L|Y}(L|Y)=Y_0(Y/Y_0)^{\beta}\Phi_L(L_{\rm scaled})$. Fitted on the 2006 cross-section:
  $\alpha=1.037(0.003)$ from $E[\ln Y|L]=\alpha\ell+\text{const}$, $\beta=0.655(0.002)$ from
  $E[\ln L|Y]=\beta y+\text{const}$, joint lognormal shape parameter $p=0.698(0.025)$, and a
  **labor-productivity exponent $\zeta=0.456(0.017)$** with $E[L|C]\propto(C/C_0)^{\zeta}$
  (arXiv:1003.2321). Nonparametric and linear fits agree to 0.01 pp ($R^2=44.04\%$ vs $44.03\%$ for
  $10^{0.7}<L<10^{2.5}$; $47.18\%$ vs $47.09\%$ for $10^{4.5}<Y<10^{7.0}$) — i.e. the log-linear law is
  a *local* description, not a global one (arXiv:1003.2321).
- **Double power laws are generated, not assumed, and their two exponents have different drivers.**
  With fitness $\eta_i\sim\mathcal N(\mu_\eta,\sigma_\eta^2)$ and exponential growth
  $dk_i/dt=\eta_ik_i$, $\;N(t)\propto e^{c_nt}$, the **lower-tail exponent is
  $\gamma_1=c_n/\mu_\eta$, independent of $\sigma_\eta$**, while the **upper-tail exponent scales as
  $\gamma_2\sim1/\sigma_\eta$** (so $\sigma_\eta\to0$ degenerates the tail to a hard cutoff
  $k_c=e^{\mu_\eta t_c}$); the break point drifts as $k_c\sim e^{\mu_\eta t_c}$ with a transition at
  $\sigma_{\rm tr}\approx\mu_\eta$ (arXiv:1103.2001). Empirical confirmation on the Chinese airline
  network 1999–2008: $N(t)\propto e^{0.088t}$, $M(t)\propto e^{0.154t}$, degree distribution with
  $\gamma_1=0.46,0.51,0.52,0.51,0.51,0.51$ and $\gamma_2=2.2,2.1,2.5,2.3,2.7,2.7$ across
  1999/2000/2001/2002/2003/2008, break $k_c=18,18,20,21,22,30$ (arXiv:1103.2001).
- **A spend→response law with an explicit saturation *and* tipping point.** Fitting
  $y=Cx^{\alpha}(1-e^{\beta x})^{-\gamma}$ to media-spend/KPI curves, the proposed form beats
  Michaelis–Menten and Hill on one synthetic dataset (average $r^2$: 0.535 vs 0.456 vs 0.444) and
  *loses* on another (0.903 vs 0.945 vs 0.939) — a genuine negative result reported by the author;
  regression-through-the-origin (RTO) gives significant coefficients at $p<0.01$ in all channels
  whereas OLS-with-intercept often does not (e.g. a channel with coefficient $-0.02$, SE $0.125$,
  $p=0.874$) (arXiv:2404.02175v5). All three validation datasets are **dummy/synthetic**.
- **An information-diffusion process with a closed-form mixing rate.** For $N$ interacting
  components with symmetric $m$-ary interaction kernel $Q$ and Poisson intensities, the law of a
  component up to time $t$ is the "extended Wild sum"
  $\mu_t=\sum_{n\ge0}p_n(t)\frac{1}{\#_m(n)}\sum_{A_n\in\mathcal A_n}\mu\circ_m A_n$ with tree count
  $\#_m(n)=\prod_{k=1}^{n}\bigl((m-1)(k-1)+1\bigr)$; for the wealth-redistribution kernel
  $S_m(\mu)=\mathcal L(H_1X_1+\dots+H_mX_m)$ with $\mathbb E[\sum H_i]=1$ and $\mathbb E[\sum H_i^2]<1$
  convergence to the fixed point $\gamma$ is **exponential at rate $\eta=1-\mathbb E[\sum_i H_i^2]$**,
  $|\langle\mu_t,f\rangle-\langle\gamma,f\rangle|\le ce^{-\eta t}$ ($m=2$ recovers Kac's classical
  Wild sum of kinetic gas theory) (arXiv:1202.5251). No market data is used; this is a simulation
  primitive (§2.7).

**Contextual only — retained, not actionable**

- `1409.0789v1` is **historical**: it traces Ettore Majorana's 1936/1942 manuscript "The value of
  statistical laws in physics and social sciences" (requested by his uncle Giuseppe, a Catania
  economics professor; mailed 4 Mar 1936) and the founding meetings — Budapest 21–27 July 1997 (26
  talks, 60 participants), Rome 12–13 March 1998 (16 talks, 32), Palermo 28–30 Sept 1998 (32 talks,
  53, the first with published proceedings) — plus the 1999 Palermo "Observatory of Complex Systems".
  It contains no estimator, dataset or statistic computable on FinRobot data.
- `1202.5251v1` is **theory**: a limit theorem plus the mixture law above. It certifies *why* an
  $m$-ary aggregation process mixes fast; it does not supply a quantity estimable from market data.

The corpus therefore has **no tradable construction** in this category. What it has is a way to keep
scaling claims honest, plus two cross-sectional decomposition estimators (DSL, double power law) and
one response-curve fitter.

---

## Methods & Formulas

### 2.1 MF-DFA with the finite-size multifractal-noise floor
**Purpose.** Decide whether an observed generalized-Hurst spread $\Delta h$ (or spectrum width
$\Delta\alpha$) in a return, volatility or volume series is *real* multifractality or the unavoidable
artefact of a finite sample of a monofractal long-memory signal. This is a **gate**, not a signal.

**Formula.** For a series $x(t)$, compute $q$-deformed fluctuation $F_q(\tau)$ by MF-DFA
(order-1 detrending suffices here) and fit $F_q(\tau)\sim\tau^{h(q)}$. Then
$$\Delta h=\lim_{q\to-\infty}h(q)-\lim_{q\to+\infty}h(q)\;\approx\;h(-15)-h(+15),$$
$$\Delta\alpha=\alpha_{\max}-\alpha_{\min},\qquad \alpha=h(q)+qh'(q),\qquad f(\alpha)=q\bigl(\alpha-h(q)\bigr)+1 .$$
The monofractal noise floor is
$$\boxed{\;\Delta h_{\rm thr}(\gamma,L)=C_1L^{-\eta_1}\gamma+C_0L^{-\eta_0}(1-\gamma)\;}$$
$$\Delta\alpha_{\rm thr}(\gamma,L)=D_1L^{-\xi_1}\gamma+D_0L^{-\xi_0}(1-\gamma),$$
with the 95 %-level multipliers obtained by inflating the coefficients as
$\Delta h^{95\%}(L)=C\,e^{\,f(\sigma_C+S)}\,L^{-\eta}$, $f=1.65$, where $\sigma_C,\sigma_\eta$ are the
fit uncertainties and $S$ the ensemble standard deviation (arXiv:1108.1951). Declare *true*
multifractality only when the measured $\Delta h$ lies above the 95 % curve.

**Required inputs.** One long series of prices or returns (long enough that $L\ge10^3$; the paper's
finance example uses $L\approx2\times10^3$ daily observations) and, as input to the threshold, an
estimate of $\gamma$ (from 2.2).

**Parameters & defaults.** $q\in[-15,15]$ (uniformly spaced); scaling range $\tau\in[10,\,L/4]$;
MF-DFA detrending order 1; ensembles of $10^2$ realizations to reproduce the coefficients; threshold
coefficients $(C_1,\eta_1,C_0,\eta_0)=(0.603,0.175,0.453,0.124)$ and
$(D_1,\xi_1,D_0,\xi_0)=(0.686,0.129,0.572,0.089)$ (arXiv:1108.1951).

**Observed effect sizes.** Residual $\Delta h$ decays as $L^{-\eta}$ with $\eta_1=0.175$ (weak
persistence, $\gamma=1$) and $\eta_0=0.124$ (strong persistence, $\gamma=0$); it grows *linearly* in
$\gamma$ at fixed $L$. Shuffling the series removes the $\gamma$ dependence but leaves the $L$
dependence — the finite-size term is irreducible (arXiv:1108.1951). In finance, 80–100 % of index
multifractality is attributable to it (India/Ireland examples above).

**Failure modes.** (i) The coefficients are calibrated on FFM-generated *monofractal* series: they are
the right null, not the right model, so they must be re-derived if a different long-memory generator
is assumed. (ii) $q=\pm15$ is a numerical truncation of $q\to\pm\infty$; results are sensitive to it.
(iii) The scaling range must be re-verified per series — plotting $\log F_q$ vs $\log\tau$ outside
$[10,L/4]$ breaks the power law. (iv) A $\Delta h$ that passes the threshold is *consistent* with true
multifractality; it does not prove it (fat tails alone generate apparent multifractality too). (v)
$\gamma$ is assumed constant across scales; the paper's whole point is that when it is *not* constant
the residual is real.

### 2.2 Autocorrelation exponent / Hurst estimator feeding the noise floor
**Purpose.** Supply the $\gamma$ (equivalently $H$) that parameterises the noise-floor threshold, and
classify a series as long-memory ($H>1/2$) versus diffusive.

**Formula.** With increments $\Delta x(t)=x(t+1)-x(t)$,
$$C(\tau)=\langle\Delta x(t)\Delta x(t+\tau)\rangle\sim\tau^{-\gamma},\qquad \gamma=2-2H\;\Longleftrightarrow\;H=1-\gamma/2 .$$
Fit the log-log slope of $C(\tau)$ over $1\le\tau\le L/10$ (the paper fits to large lags and reports
$\gamma_{\rm out}=0.203(\pm0.009),\;0.498(\pm0.012),\;0.782(\pm0.054)$ for inputs $0.2,0.5,0.8$ —
i.e. the estimator is accurate to $\pm0.01$–$0.05$ over the range $L=2^{20}$) (arXiv:1108.1951).

**Required inputs.** The same series as 2.1, differenced once.

**Parameters & defaults.** $\gamma\in(0,1]$ only (the monofractal family spanned); average over all
overlapping lags; fit in log-log space; the scaling range $\tau\in[10,L/4]$ is shared with 2.1.

**Observed effect sizes.** In-sample recovery error grows with $\gamma$: $0.2\to0.203$,
$0.5\to0.498$, $0.8\to0.782$ (arXiv:1108.1951). In finance, the crossing $\gamma<1$ is exactly the
long-memory condition used by the noise-floor boundary.

**Failure modes.** (i) The estimator is *in-sample by construction* — with $L\approx2\times10^3$ and
$\gamma\ge0.8$ the fit degrades; report the CI, not the point. (ii) A series may have $\gamma$ that
drifts with scale; then $H$ is not a single number and the noise-floor comparison is invalid (this is
the definition of "true" multifractality). (iii) Microstructure noise dominates at intraday
frequencies; estimate on daily or coarser series, or high-frequency-filter first.

### 2.3 Multifractal spectrum, its width, and the entropy reading
**Purpose.** Present the same multifractal content in Hölder language and obtain a thermodynamically
interpretable "entropy of singularities", together with a single scalar width for screening.

**Formula.** Legendre transform of the mass exponent $\tau(q)=qh(q)-1$:
$$\alpha=\frac{d\tau}{dq}=h(q)+qh'(q),\qquad f(\alpha)=q\alpha-\tau(q)=q\bigl(\alpha-h(q)\bigr)+1 .$$
$f(\alpha)$ is a large-deviation rate function — the entropy of the set of points whose local Hölder
exponent is $\alpha$ — so the intercept $f(\alpha^\*)=1$ and the width $\Delta\alpha$ measure how many
distinct scaling regimes coexist. Report the pair $(\Delta h,\Delta\alpha)$; the two are monotonically
related but not identical, and 2.1 gives a separate threshold for each (arXiv:1108.1951). For the DSL
lognormal (2.4), the differential entropy of the fitted joint PDF is available in closed form as the
Gaussian entropy $\tfrac12\ln\!\bigl((2\pi e)^2\det\Sigma\bigr)$ with $\Sigma=\Sigma(\alpha,\beta,p)$,
usable as a one-number summary of the cross-section's dispersion.

**Required inputs.** The $h(q)$ table from 2.1.

**Parameters & defaults.** $\alpha_{\min}$/$\alpha_{\max}$ read at $q=+15$/$q=-15$ respectively (the
paper's convention); no additional parameters.

**Observed effect sizes.** Shuffling a monofractal series removes the $\gamma$ dependence of both
$\alpha_{\min}$ and $\alpha_{\max}$ but preserves the length dependence (arXiv:1108.1951). For
finance, the width alone is unreliable — §2.1 is the deciding tool.

**Failure modes.** (i) Numerical differentiation $h'(q)$ amplifies noise; fit a smooth $h(q)$
(quadratic in $q$ is adequate near $q=0$) before transforming. (ii) $\Delta\alpha$ and $\Delta h$
diverge in interpretation when $f(\alpha)$ is not concave — check convexity of $\tau(q)$. (iii) The
spectrum is only defined inside the verified scaling range; extrapolating $\alpha$ beyond $q=\pm15$
is meaningless.

### 2.4 Double scaling law (DSL) estimator for a joint (output, labour) cross-section
**Purpose.** Reduce a large firm-level cross-section of two heavy-tailed variables to a small set of
indices that reconstruct the joint, marginal and productivity distributions — the "micro→macro"
aggregation map.

**Formula.** Define $y=\ln(Y/Y_0)$, $\ell=\ln(L/L_0)$ and the two scaling *invariant functions*
$\Phi_Y,\Phi_L$ by the double scaling law
$$P_{Y|L}(Y|L)=L_0\Bigl(\frac{L}{L_0}\Bigr)^{\alpha}\Phi_Y(Y_{\rm scaled}),\quad Y_{\rm scaled}=\Bigl(\frac{L}{L_0}\Bigr)^{\alpha}Y,$$
$$P_{L|Y}(L|Y)=Y_0\Bigl(\frac{Y}{Y_0}\Bigr)^{\beta}\Phi_L(L_{\rm scaled}),\quad L_{\rm scaled}=\Bigl(\frac{Y}{Y_0}\Bigr)^{\beta}L .$$
Equivalently $E[\ln Y|L]=\alpha\,\ell+\text{const}$ and $E[\ln L|Y]=\beta\,y+\text{const}$. When the
invariant functions are lognormal, so is the joint PDF, and the productivity $C=Y/L$ has marginal
$P_C(C)\propto C^{-1}e^{-\cdot}$ with exponent $\zeta$, i.e. $E[L|C]\propto(C/C_0)^{\zeta}$.

**Required inputs.** A cross-section of pairs `(revenue_Y, employees_L)` with **unbounded support** —
i.e. the whole firm population, not listed firms only (the paper is explicit that a listed-only
database is insufficient to resolve the distributions).

**Parameters & defaults.** Nonparametric (kernel) regression of $E[\ln Y|L]$, $E[\ln L|Y]$ on the log
variables, compared against linear regression; conditioning values of $L$ at equal log spacing.
Fitted values: $\alpha=1.037(0.003)$, $\beta=0.655(0.002)$, $p=0.698(0.025)$,
$\zeta=0.456(0.017)$; validity ranges $10^{0.7}<L<10^{2.5}$ and $10^{4.5}<Y<10^{7.0}$
(arXiv:1003.2321).

**Observed effect sizes.** $\alpha>1$ means sales scale *super-linearly* in employees, so the
conditional median output per worker *rises* with firm size over the valid range (≈1.7 % per doubling
of $L$ implied by $\alpha-1=0.037$); nonparametric and linear fits differ by $\le0.01$ pp in $R^2$,
so the log-linear local law is essentially non-parametric-driven; the lognormal fitted to the scaled
conditional PDF is visually and numerically accepted (arXiv:1003.2321).

**Failure modes.** (i) The law holds only in a *local* window of the $(Y,L)$ plane; extrapolating the
lognormal to all scales is explicitly wrong. (ii) Estimators are conditional means — they are
log-mean, not mean, relations, and must not be composed multiplicatively. (iii) Using listed
companies only truncates the support and biases both exponents toward 1. (iv) The exponent-relation
identity linking $(\alpha,\beta,p)$ to $\zeta$ (paper Eqs. 22–25) holds only under the lognormal
assumption; verify it numerically rather than trusting it.

### 2.5 Double power-law fit and the fitness+noise generator
**Purpose.** Fit a two-regime Pareto distribution to any heavy-tailed cross-section (degrees, sizes,
incomes, volumes) with an explicit break point, and diagnose whether the second regime is real or an
artefact of heterogeneity.

**Formula.** Cumulative form
$$P(K>k)\;=\;\begin{cases}k^{-\gamma_1}, & k<k_c\\[2pt] k_c^{\gamma_2-\gamma_1}\,k^{-\gamma_2}, & k\ge k_c,\end{cases}$$
with the generative predictions
$$\gamma_1=\frac{c_n}{\mu_\eta},\qquad \gamma_2\sim\frac{1}{\sigma_\eta},\qquad k_c\sim e^{\mu_\eta t_c},$$
for exponentially growing variables ($dk_i/dt=\eta_ik_i$, $\eta_i\sim\mathcal N(\mu_\eta,\sigma_\eta^2)$)
whose population grows as $N(t)\propto e^{c_nt}$, and generally
$$dk_i=\rho\,\eta_ik_i\,dt+(1-\rho)\bigl(\mu_\eta\,dt+\sigma\,dw\bigr)k_i,\qquad \rho\in[0,1],$$
where noise leaves $\gamma_1$ unchanged but *reduces* $\gamma_2$ (arXiv:1103.2001).

**Required inputs.** A heavy-tailed empirical cross-section plus, to exploit the exponents, a time
series of the population size $N(t)$ and of a per-unit growth-rate proxy (GDP, market cap) for the
same units.

**Parameters & defaults.** Fit the two slopes by Hill on the sub-samples $k<k_c$ and $k\ge k_c$, with
$k_c$ chosen by minimising the KS distance between empirical and fitted CDFs; the paper reads $\gamma_1$
off the plateau of successive annual fits. Simulation defaults: $\mu_\eta=0.15$, $\sigma_\eta=0.02$,
$N(t)=50\,e^{0.088t}$, $t_c=30$ steps, 50 realizations averaged (arXiv:1103.2001).

**Observed effect sizes.** Chinese airline network: $\gamma_1$ is *stable* across years
(0.46–0.52) while $\gamma_2$ fluctuates 2.1–2.7 — the model predicts $(\gamma_1$ stable, $\gamma_2$
fluctuation-sensitive$)$ exactly; the calibrated stochastic model reproduces
$\gamma_1=0.61$, $\gamma_2=2.84$ against data 0.51/2.7 (arXiv:1103.2001). Null test: replacing the
normal fitness by exponential, uniform, power-law, Poisson, Rayleigh or Weibull fitness destroys the
double power law in **all six** cases (arXiv:1103.2001).

**Failure modes.** (i) Two regimes are easy to over-fit; without the null distribution test
(`λ_i`, $d\varepsilon$) the second exponent is unfalsified. (ii) $\sigma_\eta\approx\mu_\eta$ kills the
second regime — if the fitted $\sigma_\eta$ is not well below $\mu_\eta$ the double law is not
identified. (iii) The mechanism requires an exponentially growing population; a static cross-section
cannot validate it. (iv) The fitness interpretation is a modelling choice, not a measurement — do not
report $\mu_\eta,\sigma_\eta$ as observed quantities.

### 2.6 Advertising/S-response curve fit with tipping point
**Purpose.** Fit a spend→response curve that can express both saturation and a threshold, extract
three interpretable sensitivities, and locate the spend level beyond which extra spend is wasted.

**Formula.**
$$y=C\,x^{\alpha}\bigl(1-e^{\beta x}\bigr)^{-\gamma},\qquad \alpha\in[0,1],\ \gamma\in[0,1],$$
$$\frac{dy}{dx}=C\alpha x^{\alpha-1}(1-e^{\beta x})^{-\gamma}+\gamma\beta e^{\beta x}(1-e^{\beta x})^{-\gamma-1}\;=\;0 \;\;\text{(tipping point)} .$$
The form is **not** scale invariant: the factor $(1-e^{\beta x})^{-\gamma}$ breaks $f(ax)=a^{\alpha}f(x)$
(arXiv:2404.02175v5).

**Required inputs.** A spend series $x$ and a KPI/response series $y$ (media spend vs sales/KPI, or any
dose–response pair); the model was fitted on MMM-attributed channel impact.

**Parameters & defaults.** Fit by Levenberg–Marquardt/L-BFGS-B with $\text{maxiter}=10^6$,
$\text{tol}=10^{-6}$; use **regression through the origin** ($y=0$ when $x=0$); benchmark against
Michaelis–Menten $y=V_{\max}x/(K+x)$ and Hill $y=x^n/(K_d+x^n)$. Interpretation bands: $\alpha>0.5$
"complex mechanisms", $<0.2$ "focused"; $\beta>0.8$ rapid saturation; $\gamma>0.8$ strong network
effects / unified audience (arXiv:2404.02175v5).

**Observed effect sizes.** Average $r^2$ (RTO): dataset 1 **0.535 (proposed) vs 0.456 (Hill) vs 0.444
(MM)**; dataset 2 **0.903 vs 0.945 vs 0.939** (proposed loses); dataset 3 **0.348 vs 0.334 vs 0.347**
(arXiv:2404.02175v5). Fitted ranges across 24 channel-datasets: $\alpha\in[0.018,0.686]$,
$\beta\in[-1.000,0.984]$, $\gamma\in[0,0.935]$. RTO coefficients are significant at $p<0.01$ in every
channel; OLS-with-intercept fails significance in a majority.

**Failure modes.** (i) **All validation data are dummy** — the paper's own limitation statement; treat
the coefficients as priors, not estimates. (ii) The proposed equation wins on 2 of 3 datasets only;
choose per-dataset by adjusted $r^2$, never by prior. (iii) $C$ and $\alpha$ are not mutually
identified across channels — only their product tracks attribution influence. (iv) With $\beta>0$ the
curve does not saturate, so the "saturation point" claim is conditional on the fitted sign. (v)
Fitting on attributed MMM output propagates the attribution model's error into $C$.

### 2.7 Information percolation / m-ary Wild-sum aggregation (simulator)
**Purpose.** Model how an initial state (a price-relevant information set, or a wealth distribution)
is mixed through repeated $m$-agent interactions — for scenario generation and for computing how fast
a population forgets its initial condition.

**Formula.** With $\#_m(n)=\prod_{k=1}^{n}\bigl((m-1)(k-1)+1\bigr)$,
$$\mu_t=\sum_{n\ge0}p_n(t)\frac{1}{\#_m(n)}\sum_{A_n\in\mathcal A_n}\mu\circ_m A_n,\qquad
\frac{dp_t(0)}{dt}=-p_t(0),\quad \frac{dp_t(n)}{dt}=\bigl((m-1)(n-1)+1\bigr)p_t(n-1)-\bigl((m-1)n+1\bigr)p_t(n),$$
and for the redistribution kernel $S_m(\mu)=\mathcal L(H_1X_1+\dots+H_mX_m)$ the mixing rate is
$$\eta=1-\mathbb E\bigl[\textstyle\sum_{i=1}^m H_i^2\bigr],\qquad
\bigl|\langle\mu_t,f\rangle-\langle\gamma,f\rangle\bigr|\le c\,e^{-\eta t},$$
valid whenever $H_i\in[0,1]$, $\mathbb E[\sum H_i]=1$, the $H_i$ are non-Bernoulli and
$\mathbb E[\sum H_i^2]<1$ (arXiv:1202.5251).

**Required inputs.** None from the data layer. Choices only: $m$ (group size), the kernel $Q$
(hence $H$), and an initial $\mu_0$.

**Parameters & defaults.** $m\ge2$ ($m=2$ is Kac's Wild sum); the paper proves the $N\to\infty$
asymptotic tree approximation is valid with an $O(1/N)$ redundant-edge rate.

**Observed effect sizes.** The whole content is analytic: the convergence constant is $1-\mathbb E[\sum H_i^2]$
and the branch-count intensities are $(m-1)n+1$. No fitted numbers are reported.

**Failure modes.** (i) It is a *simulator*: no market data, no calibration target, therefore no
tradable output. (ii) The tree approximation fails for small $N$ — the multiply-interacting term is
$O(1/N)$ but $N$ must be genuinely large. (iii) The Bernoulli-$H$ case is excluded (an assumption,
not a theorem). (iv) Its only defensible FinRobot use is as a diffusion toy model for signal
propagation across a trader network.

---

## Data Requirements

Provider rows below are real entries in `strategies/endpoints.json`; "gap" means **no current provider
can supply it.**

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV history (MF-DFA / $\gamma$ / double-power-law inputs) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV history (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily EOD bars (tertiary) | `https://api.stockdata.org/v1/data/eod` | `core_stock_apis` | stockdata | ok |
| Intraday bars (resolve the scaling-range ambiguity) | `https://api.twelvedata.com/time_series` (`interval=1min`) | `core_stock_apis` | twelvedata | ok |
| Previous-day aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday K-line via local SDK gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Top-of-book snapshot (single-name sanity check) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Cross-sectional dispersion proxy (breadth of a one-period return cross-section) | `moomoo://get_rise_fall_distribution` | `market_breadth` | moomoo | gateway (not live-probed) |
| Unit growth-rate proxy $\lambda_i$ (capital-flow alternative) | `moomoo://get_capital_flow` | `capital_flow` | moomoo | gateway (not live-probed) |
| Tradable universe size $N(t)$ proxy | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Firm financial statements ($Y$ proxy for DSL, listed firms only) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| Firm fundamentals (second provider) | `https://www.alphavantage.co/query` | `fundamental_data` | alpha_vantage | ok |
| Macro level series (GDP-style driver for $\mu_\eta$) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Macro indicator list via gateway | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| News counts for a spend→response surrogate | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| Event-implied probability levels (response KPI alternative) | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | ok |
| Option-implied dispersion surface (scaling of cross-sectional vol) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | ok |
| **Long daily series of institutional/industry size distribution with an annual break point** | — | — | — | **gap** |
| **Firm-level `(revenue, employees)` panel covering the whole population** | — | — | — | **gap** |
| **Employee counts / headcount per firm** | — | — | — | **gap** |
| **Media/marketing spend and matched KPI time series** | — | — | — | **gap** |
| **Inter-agent interaction records (who traded/communicated with whom, timestamped)** | — | — | — | **gap** |
| **Time series of a network's node and edge sets (for the double power law)** | — | — | — | **gap** |

**What each gap costs, quantified.**

- *Long index series for MF-DFA/$\gamma$.* **No gap** — daily OHLCV from `eodhd`/`tiingo` supplies the
  $L\approx2\times10^3$ observations the paper used as its finance example, and `twelvedata` 1-minute
  bars allow the required scaling-range check ($\tau\in[10,L/4]$). This is the one estimator that is
  fully buildable today.
- *Firm panel for DSL.* The paper's exponents ($\alpha=1.037$, $\beta=0.655$, $p=0.698$,
  $\zeta=0.456$) come from **~1 million firms and ~15 million workers** in a purpose-built credit
  database. The best available substitute (`tiingo`/`alpha_vantage` fundamentals) is a listed-firm
  sample of order $10^3$–$10^4$ units with **no employee counts**, i.e. both truncation and a missing
  variable: the DSL is under-identified by three orders of magnitude in sample size.
- *Double power law.* The generating mechanism needs an *annual* record of $N(t)$ and $M(t)$ and of a
  per-unit growth proxy; the retail data layer offers no network edge set at all, so only the fitting
  half (§2.5's Hill-on-two-regimes) is usable — on any heavy-tailed series the layer does expose, e.g.
  daily cross-sectional breadth or capital-flow magnitudes.
- *Response curve.* The media-spend/KPI pairs used by arXiv:2404.02175v5 are dummy; nothing in the
  catalog serves marketing spend, so §2.6 is currently a curve-fitting utility in search of an input.
  A defensible surrogate is `news_data` count → next-day volume or `prediction_markets` level change
  → realized move.
- *Information percolation.* Needs no data; it is therefore free but also valueless as a signal until
  it is attached to an observed interaction graph (`gap`).

---

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **"Multifractality" is mostly finite-sample noise until proven otherwise.** The corpus's central
  warning: for price indices, ≈80 % (Philippines, Taiwan, Germany) to ≈100 % (Ireland) of the
  measured multifractal width is reproduced by monofractal long-memory series of the same length
  (arXiv:1108.1951). Always run the shuffling control (it removes $\gamma$ dependence) and report
  $\Delta h$ against the 95 % floor, never against zero.
- **$L$ and $\gamma$ must be reported with any $\Delta h$.** The floor scales as $L^{-\eta}$ with
  $\eta\in[0.124,0.175]$; a width of 0.05 is significant at $L=2^{20}$ and pure noise at $L=2^{9}$
  (arXiv:1108.1951). Quoting a width without its sample length is uninterpretable.
- **Scaling laws are local.** DSL fits hold only for $10^{0.7}<L<10^{2.5}$ and $10^{4.5}<Y<10^{7.0}$;
  outside these windows the lognormal-everywhere derivation does not apply (arXiv:1003.2321). Fit the
  valid window first, then the law.
- **Commit to a regression convention before looking at $r^2$.** For a curve that must pass through
  the origin, RTO is the right default: it makes the predictor significant in *every* channel
  ($p<0.01$) where OLS-with-intercept fails in many (arXiv:2404.02175v5). Choosing the convention per
  channel inflates the apparent win rate of the proposed equation.
- **Report the losing datasets.** The proposed response curve wins on 2 of 3 synthetic datasets and
  loses on the second (0.903 vs 0.945) (arXiv:2404.02175v5). A model-selection report that omits the
  counterexample is a red flag.
- **Null-test every second exponent.** The double power law's $\gamma_2$ is *designed* to be sensitive
  to heterogeneity, so a two-slope fit alone is not evidence. The paper's own null test — six
  alternative fitness distributions all failing to generate the double law (arXiv:1103.2001) — is the
  standard to match; substitute shuffle/bootstrap resamplings of the cross-section.
- **Separate the two drivers before interpreting exponents.** $\gamma_1=c_n/\mu_\eta$ is noise-
  independent; $\gamma_2$ is noise-driven. Reading a shift in $\gamma_1$ as "more inequality" (or
  $\gamma_2$ as "more competition") confuses the two regimes (arXiv:1103.2001).
- **Do not compose conditional means.** DSL exponents are relations for $\mathbb E[\ln Y|L]$ and
  $\mathbb E[\ln L|Y]$; multiplying them to obtain a mean-mean elasticity introduces a Jensen term of
  the order of the fitted $\sigma^2$ (arXiv:1003.2321).
- **Sample-split discipline in the corpus.** Multifractal coefficients come from $10^2$ realizations
  per cell; the double-power-law model from 50 realizations, with the empirical side split by year
  (1999–2003 for fitting, 2008 for corroboration); the CAN mechanism was corroborated on six
  consecutive years (arXiv:1103.2001). Any FinRobot re-derivation should match or exceed these
  replication counts, and must hold out at least one period.
- **Regime dependence is explicit in the DSL and the double law** (validity windows, transition
  $\sigma_{\rm tr}\approx\mu_\eta$), and absent from the percolation theorem (which is an
  unconditioned limit) — do not import the theorem's stationarity into a market application
  (arXiv:1003.2321, arXiv:1103.2001, arXiv:1202.5251).
- **Look-ahead.** All three estimators are fitted on the series they describe; for any forward use,
  re-estimate on a trailing window and score on the next, non-overlapping window. The response-curve
  paper's validation is in-sample throughout and its own limitation section says so
  (arXiv:2404.02175v5).

---

## Recommended Workflow

Ordered by value-per-effort against what the data layer can fetch today. Items 1–3 are buildable now;
items 4–6 are blocked on inputs the catalog does not serve.

1. **`MultifractalNoiseGate` (daily/index-level).** *What:* MF-DFA $\Delta h$ and $\Delta\alpha$ plus
   the finite-size floor $\Delta h_{\rm thr}(\gamma,L)$ from §2.1, with $\gamma$ from §2.2. *Consumes:*
   daily OHLCV (`eodhd` `eod`, `tiingo` `prices`, `stockdata` `eod`). *Passing result:* the gate
   reproduces the paper's finance ordering — volatility series pass the 95 % floor more often than
   price indices — and flags $\ge70\%$ of index-level widths as noise at $L\approx2\times10^3$.
   *Risk:* the floor is calibrated on FFM monofractals; document that it is a null, not a model.
   *Effort:* M.
2. **`ScalingExponentSuite` (Hurst + tail + double power law).** *What:* one module exposing $\gamma$
   from $C(\tau)$ (§2.2), the Hill/power-law exponent, and the two-regime fit with break $k_c$.
   *Consumes:* the same daily bars plus cross-sectional series the layer does hold (breadth, capital
   flow via the `moomoo` gateway, or single-name volume). *Passing result:* on 20 randomly chosen
   daily series, the $\gamma$ estimator recovers an injected $\gamma\in\{0.2,0.5,0.8\}$ to within
   $\pm0.06$, and the two-regime fit reports a stable $\gamma_1$ with an unstable $\gamma_2$ across
   annual re-estimations (the paper's own signature). *Risk:* single-name Hill fits are dominated by
   the tail cutoff choice. *Effort:* M.
3. **`ResponseCurveFitter` (generic dose→response).** *What:* the §2.6 fit with RTO convention, the
   analytic tipping point solved by Newton's method, and Michaelis–Menten/Hill as mandatory
   benchmarks. *Consumes:* any available ordered pair — `news_data` count → next-day volume, or
   `prediction_markets` level → realized move. *Passing result:* the fitter selects the correct model
   by adjusted $r^2$ on held-out doses, and on the paper's synthetic reproductions recovers
   $(C,\alpha,\beta,\gamma)$ within the reported standard errors. *Risk:* no true spend data exists;
   label every output "dose→response surrogate". *Effort:* S.
4. **`FirmSizeDistributionPanel` (DSL, blocked).** *What:* §2.4 on an unbounded `(revenue, employees)`
   population. *Consumes:* **gap** — `tiingo`/`alpha_vantage` `fundamental_data` give listed-firm
   statements with no headcount; `exchange_symbols` gives $N$ but not the joint pair. *Passing
   result:* reproduce $\alpha\approx1.04$, $\beta\approx0.66$ on a full population; currently
   unimplementable, keep as specification only. *Effort:* L.
5. **`DoublePowerLawGenerator` (simulation).** *What:* the §2.5 stochastic generator, used to
   pre-compute the mapping $(\mu_\eta,\sigma_\eta,c_n)\mapsto(\gamma_1,\gamma_2,k_c)$ and to test the
   six-distribution null battery. *Consumes:* nothing live. *Passing result:* the simulated
   $\gamma_2\sim1/\sigma_\eta$ relation is linear with $R^2>0.9$ and no non-normal fitness reproduces
   the double law. *Value:* lets the team falsify any future double-power-law claim on FinRobot data.
   *Effort:* M.
6. **`PercolationDiffusion` (simulation, informational only).** *What:* §2.7's $m$-ary Wild-sum
   process with the closed-form rate $\eta=1-\mathbb E[\sum H_i^2]$, exposed purely as a scenario
   generator for how fast a shared information set mixes across $N$ agents. *Consumes:* nothing.
   *Passing result:* the simulated convergence matches $ce^{-\eta t}$ and the empirical tree has the
   predicted $O(1/N)$ redundancy. *Value:* low until an interaction graph exists. *Effort:* S–M.
7. **Skip** the Majorana history (`1409.0789v1`) and, for estimator purposes, the percolation theorem
   (`1202.5251v1`). Neither yields a quantity computable on FinRobot data.

---

## Output Format

### Multifractal Noise Gate
| Series | L | gamma | Delta-h | Delta-h 95% floor | Delta-alpha | Pass / noise |
|--------|-----|-------|---------|-------------------|-------------|--------------|
| ... | ... | ... | ... | ... | ... | ... |

### Scaling-Law Fit
| Estimator | Exponent | SE | Valid window | Shuffle / null test | Verdict |
|-----------|----------|----|--------------|---------------------|---------|
| gamma from C(tau) | ... | ... | tau in [10, L/4] | ... | ... |
| Hill / power law | ... | ... | tail cutoff | ... | ... |
| Double power law | gamma1 / gamma2 | ... | k < kc / k >= kc | six-distribution null | ... |
| Double scaling law | alpha / beta / p / zeta | ... | local (Y,L) window | nonparametric vs linear | ... |

### Verdict
State whether the measured width clears the 95% finite-size floor (and at what L and
gamma), the fitted exponents with their standard errors and valid windows, the
result of the shuffle or null battery for every second exponent, the fitter's
RTO-vs-OLS convention and held-out r2, and which items are blocked on inputs the
catalog does not serve (full-population firm panel, media-spend/KPI pairs,
interaction records). Report any counterexample where the proposed model lost.

## References

| arXiv id | Title | Year |
|---|---|---|
| 2404.02175v5 | Symmetries, Scaling Laws and Phase Transitions in Consumer Advertising Response | 2024 |
| 1202.5251v1 | Information Percolation: Some General Cases with an Application to Econophysics | 2012 |
| 1108.1951v2 | How much multifractality is included in monofractal signals? | 2011 |
| 1409.0789v1 | Sicily and the development of Econophysics: the pioneering work of Ettore Majorana and the Econophysics Workshop in Palermo | 2014 |
| 1103.2001v1 | Emergence of double scaling law in complex system | 2011 |
| 1003.2321v1 | Micro-Macro Relation of Production — The Double Scaling Law for Statistical Physics of Economy | 2010 |
