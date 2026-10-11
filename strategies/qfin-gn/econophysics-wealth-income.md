# Wealth & Income Distribution — learnings from the q-fin.GN corpus

`309` of 3095 corpus papers matched this category (308 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category yields no tradable signal and no FinRobot-available micro-data.** It yields a
small, well-specified set of *distributional estimators* — Gini from grouped/tabulated data, Pareto
tail exponents, a four-parameter κ-deformed Generalized Gamma density, and a mobility (liquidity)
diagnostic — plus two proof-carrying simulation results (unbiased binary exchange ⇒ condensation;
income tax cannot stop it, wealth tax can). What it does **not** yield is an observable input FinRobot
can fetch today: every empirical result below is calibrated on household income/wealth micro-data
(IPUMS/CPS, World Bank PovcalNet, national accounts) or on simulation. That micro-data is the gap, and
it is marked **gap** in §3. The estimable content here is therefore *methodological*: how to compute and
validate an inequality statistic once a distributional series exists, and what an agent-based wealth
process does under a given tax rule. Cross-links: `risk-management-tails.md` already derives the Hill
Pareto exponent estimator, and `correlation-networks-econophysics.md` already derives the two-class
exponential/Pareto wealth structure; this doc does not re-derive either.

## 1. What the corpus actually offers

- **A closed-form map from a "graduation" exponent to the Gini index.** If the `n` ranked income
  levels of a population follow `x_i = Const·i^m` (`i=1` poorest, `i=n` richest, `m>0`), then the
  Gini index converges to a pure function of the exponent, `G'_m(n) → m/(m+2)` as `n→∞` (arXiv:1309.3771).
  For integer `m=1..10` this gives `G' = 1/3, 1/2, 3/5, 2/3, 5/7, 3/4, 7/9, 4/5, 9/11, 5/6`. Inverting,
  `m = 2G'/(1-G')`. Worked readings: Norway (2008, `G'=0.25`) → `m=0.667`; France (2008, `0.327`) →
  `m≈1`; Russia (2008, `0.423`) → `1<m<2`; USA (2007, `0.45`) `m≈1.5`; Mexico (2000, `0.482`) →
  `m≈2`; Haiti (2001, `0.538`) → `2<m<3`; Sierra Leone (1989, `0.629`) → `3<m<4`; South Africa
  (2005, `0.65`) → `m≈4`; Namibia (2003, `0.707–0.75`) → `5<m<6`; Moscow 2009 (`0.521`) → `m=2.742`
  (arXiv:1309.3771). No sample sizes are given — the inputs are published country Gini values (CIA /
  World Bank lists), not micro-data.
- **Rawls-fair general equilibrium pins the *fair* income distribution to the exponential and the
  alarming Gini to 0.5, not 0.4.** Embedding Rawls' equal-opportunity axiom in an Arrow–Debreu economy
  with heterogeneous agents, the highest-probability equilibrium income distribution is the
  Boltzmann–Gibbs form `a_k = 1/e^{α+βε_k}` (`α≤0`), whose Gini is `G_B = 1/(2(1-α)) ∈ [0, 0.5]`,
  whereas the "rich get richer" Pareto form `a_k = ε_k^{-γ-1}` gives `G_P = 1/(2γ-1) ∈ [0, 1]`
  (arXiv:1409.3979). Empirically, on World Bank PovcalNet cross-country Gini (1990 `N=130`, 1995
  `N=137`, 2000 `N=139`, 2005 `N=140`), 1990 fails a Jarque–Bera normal test (JB `=6.03`, `p=0.049`;
  skew 0.436, kurtosis 2.405) while 1995/2000/2005 pass (JB `=4.04/2.74/4.47`, `p=0.13/0.25/0.11`;
  means `0.3941/0.3929/0.3898`, SD `0.0978/0.0903/0.0852`); the two-sigma alarming levels are
  **0.5797 (1995), 0.5734 (2000), 0.5603 (2005)** — all above 0.5, none near 0.4 (arXiv:1409.3979).
- **Any unbiased binary wealth exchange is provably doomed to perfect inequality.** For any pairwise,
  wealth-conserving exchange with zero expected gain to both agents (`E[Δ_i]=E[Δ_j]=0`), the Gini
  index is monotone non-decreasing (`dG/dt≥0`, a Lyapunov functional) and the stationary density is
  absolute oligarchy `f_c(x)=δ(x)+lim_{N→∞}δ(x-⟨x⟩N)/N`, so `lim_{t→∞}G(t)=1` and liquidity
  `L(t)→0` (arXiv:2012.00206). The theorem covers the yard-sale rule `Δ_i=ηλ min(x_i,x_j)`, the
  modified loser rule `Δ_i=ε λ x_j-(1-ε)λ x_i`, and the Iglesias–Almeida rule
  `Δ_i=η x_i x_j/(x_i+x_j)`; the mobility of an agent at wealth `x` is bounded by `l(x,t)≤2⟨x⟩`.
  Motivation is real: US top-1% wealth share rose from 22% (1980) to 37% (2015) (arXiv:2012.00206).
- **In an asymmetric artificial-chemistry exchange model, income tax is nearly powerless and a wealth
  tax is ~two orders of magnitude more effective.** Baseline asymmetric rule `m = p·min(m_i,m_j)`
  (no debt), 1,000 agents: equilibrium Gini → 1, versus the symmetric Dragoescu–Yakovenko kinetic
  exchange whose Gini fluctuates around `1/2` (arXiv:2007.02934). A 30% flat income tax applied every
  10 iterations to the 10-period wealth increment, fully redistributed, leaves the distribution nearly
  as unequal as untaxed; even a 60% flat or a 75% progressive marginal rate leaves the top 1% with
  ~10% of assets and the bottom half at ~8% after 100,000 iterations. A 30% wealth tax on the *whole*
  stock (applied at 1/10 the frequency) stabilizes quantile shares in a narrow band within a short
  relaxation period; a **1% wealth tax has roughly the distributional effect of a 60% income tax**
  (arXiv:2007.02934). A Gini below 0.25 is the paper's high-equality reference.
- **A four-parameter κ-deformed Generalized Gamma (κ-GG) density fits the whole wealth range,
  including the power-law tail.** Derived from maximum entropy with the Kaniadakis κ-exponential
  `exp_κ(x)=(√(1+κ²x²)+κx)^{1/κ}`, it nests the κ-Generalized (Clementi), Generalized Gamma, Gamma,
  Weibull and exponential densities as κ→0 or by parameter restrictions, and its tail exponent is
  `a = 1/θ₁ - 1` (arXiv:1805.06929). Fitted to heterogeneous-saving kinetic exchange with `N=10^3`
  agents (`M/N=10^3`, `10^9` iterations, averaged over `10^3` realizations): `κ=1.3320`, `σ=1.1240`,
  `θ₁=221.3150`, `θ₂=0.7868`, Pareto `a=1.2193`; at `N=10^5`: `κ=1.7127`, `σ=1.3710`, `θ₁=342.7610`,
  `θ₂=0.9088`, `a=1.1670` — both inside the observational `1<a<2` band (arXiv:1805.06929).
- **A one-driver microeconomic model reproduces U.S. personal-income distributions across
  race/gender.** Individual income obeys `dM/dt = σ(t) - α M(t)/Λ(t)`, with closed form
  `M(t)=ΛΣ[1-exp(-αt/Λ)]`, where capability `Σ` and work instrument `Λ` both scale as the square root
  of real GDP per capita; relative capability and instrument are discrete uniforms on `{2,…,30}`
  giving `29×29=841` histories (arXiv:2007.06530). Calibrated on IPUMS/March-CPS individual incomes
  1962–2014 (one-year age cells), the Pareto threshold is `M^P(τ₀)=0.43` (male, evolving ∝ rGDPpc) and
  `0.29→0.39` (female, 1960→2014), with a female instrument factor `FL(t)` rising 0.45→0.65. In
  1962 the peak-age cell held 40,000 women vs 150,000 men above threshold — a ~100× female deficit —
  and the white-male rich share later falls toward ~20% (2014) from ~30% (1967, ages 40–50) while
  black-female share rises above 5% (ages 40–55) only by 2001 (arXiv:2007.06530).
- **Off-topic note.** None of the six is off-topic; all six address wealth/income distribution directly.
  But only arXiv:1805.06929, arXiv:1309.3771 and arXiv:1409.3979 contain *executable* estimators;
  arXiv:2012.00206 and arXiv:2007.02934 are theorems/simulations about a closed artificial economy,
  and arXiv:2007.06530 is a calibrated macro-micro model whose only FinRobot-usable input (real GDP
  per capita) is a macro series, not a wealth series. That imbalance is the reason §1 is explicit about
  which findings are estimators and which are economic context.

## 2. Implementable formulas & algorithms

### 2.1 Gini from grouped data and the "graduation" inverse map
**Purpose.** Compute a Gini index when only tabulated/decile income shares (not micro-data) are
available, and express it as an interpretable polynomial-degree `m`.

**Formula.** For ordered incomes `x_1≤…≤x_n`,
$$G(n)=\frac{1}{n(n-1)\bar x}\sum_{i,j=1}^{n}\lvert x_i-x_j\rvert
      =\frac{2}{n(n-1)\bar x}\sum_{i=1}^{n}\bigl(i-\tfrac{n+1}{2}\bigr)x_{(i)}$$
Under the graduation model `x_i = Const·i^m`, `G'_m(n) → m/(m+2)` as `n→∞`, and the inverse read is
$$m=\frac{2G'}{1-G'} .$$
Sum-of-powers form with Bernoulli numbers: `S_m(n)=Σ_{k=0}^{n-1}k^m = (1/(m+1))Σ_k C(m+1,k) B_k n^{m+1-k}`;
the finite-`n` estimator is `G'_m(n)=\frac{n}{n-1}·\frac{S_{m+1}(n)-(n+1)/2·S_m(n)}{S_m(n)}`.

**Required inputs.** Either individual sorted incomes, or a grouped table of `k` income brackets with
counts/shares; or a published headline Gini to convert via `m=2G'/(1-G')`.

**Parameters & defaults.** `m` is an integer or fraction; the paper treats `m∈{1,…,10}` as
"linear … hexal" and reports table values `m/(m+2)`. No free parameters beyond the bracket structure.

**Observed effect sizes.** The map is exact in the limit; finite-`n` correction is `O(1/n)`. Published
values reproduced: Norway 0.25→`m=0.667`, France 0.327→`m≈1`, Russia 0.423→`1<m<2`, Mexico
0.482→`m≈2`, Namibia 0.71–0.75→`5<m<6` (arXiv:1309.3771).

**Failure modes.** The graduation model is a *stylization*: it forces a single power relation onto the
ranking and will mis-fit bimodal (two-class) distributions. Grouped-data Gini estimates are biased
downward when the top bracket is open-ended and no Pareto extrapolation is applied (the paper cites
Gastwirth 1972 / Modorres–Gastwirth 2006 on standard-error caution). Do not read `m` as a behavioural
parameter.

### 2.2 Benchmark-tail Gini and the Rawlsian alarming-level test
**Purpose.** Given a cross-country (or cross-region) panel of Gini values, test whether the panel is
stable and compute an *empirically derived* alarming level instead of adopting the folk 0.4.

**Formula.** For exponential `f_B(ε)=βe^{-β(ε+α/β)}` and Pareto `f_P(ε)=γa^γ ε^{-γ-1}` incomes,
$$G_B=\frac{1}{2(1-\alpha)}\in[0,0.5],\qquad G_P=\frac{1}{2\gamma-1}\in[0,1].$$
Normality gate (Jarque–Bera):
$$JB=\frac{n}{6}\Bigl(S^2+\tfrac14 (K-3)^2\Bigr)\ \sim\ \chi^2_2\ \text{under }H_0,$$
then the two-sigma critical value `X^*=μ+2σ` (right tail probability `0.0228`) is the alarming level.

**Required inputs.** A panel of Gini coefficients `{G_i}` with observation counts per period; nothing
finer. For the theoretical leg, only the sign of `α` (exponential support shift) or Pareto `γ`.

**Parameters & defaults.** Use **two-sigma** (not three-sigma) because the object of interest is the
right tail; the paper rejects the 0.4 folk level and reports 0.5 as the *minimum* alarming level from
theory. Normality is tested at the 5% level before computing any threshold.

**Observed effect sizes.** 1990 panel rejected normality (`JB=6.03`, `p=0.049`) — no threshold
computed; 1995/2000/2005 thresholds `0.5797/0.5734/0.5603` (arXiv:1409.3979). The declining sequence
is read as slowly rising global instability.

**Failure modes.** `G_B≤0.5` holds only if income truly follows the Rawls-optimal exponential; a
Pareto upper class voids it (`G_P→1` as `γ→1`). The normal-panel assumption fails exactly in turbulent
years (1990), so a rejected `JB` must *suppress* the threshold rather than be ignored. Cross-country
Gini series are not a random sample — mixing survey years and methodologies inflates `σ`.

### 2.3 Kinetic-exchange / artificial-chemistry simulator with tax rules
**Purpose.** Reproduce the two central simulation results — unbiased exchange condenses to Gini→1,
and only a wealth (stock) tax stabilizes the distribution — as a self-contained FinRobot module with
no market data.

**Formula.** Pairwise exchange of conserved wealth `x_i,x_j`:
$$x_i'=x_i+\Delta_i,\quad x_j'=x_j+\Delta_j,\quad \Delta_j=-\Delta_i,\quad \mathbb E[\Delta_i]=0\ \text{(unbiased)}.$$
Yard-sale `Δ_i=ηλ min(x_i,x_j)`, `η=±1`, `𝔼[η]=0`; asymmetric AC rule `m=p\,min(m_i,m_j)` (only the
poorer agent's wealth caps the flow, no debt). Tax updates, applied every `τ` iterations to the
period increment `m_i(t)-m_i(t-τ)` (income tax, rate `r`, only if positive) or to the whole stock
(wealth tax):
$$m_i \leftarrow m_i - r\,[m_i(t)-m_i(t-\tau)],\qquad
m_i \leftarrow m_i + \frac{T(t)}{N}\ \text{(redistribute to all) or}\ \frac{T(t)}{\lvert N_n\rvert}\ \text{(redistribute to losers)}.$$
Gini and liquidity as in §2.1/§2.4.

**Required inputs.** None external. Initial wealth vector (equal or arbitrary), agent count `N`,
exchange rule, tax type/rate/frequency, redistribution rule.

**Parameters & defaults.** Paper defaults: `N=1000` agents; baseline `p` random percentage of the
smaller wealth; `10` bins; tax every `10` iterations; income-tax rates `{5%,30%,60%}` flat and
`15%→45%`, `15%→60%`, `15%→75%` progressive (break-even `$150`, topping at `$850/$1200/$1550`);
wealth-tax rates `{5%,30%,60%}` applied at `1/10` frequency; `100,000` iterations; compare against
the symmetric kinetic model `m=p(m_i+m_j)/2` (arXiv:2007.02934).

**Observed effect sizes.** Baseline AC Gini → 1; symmetric kinetic Gini ≈ 1/2. Income tax at 30%
(both redistribution modes) barely changes the outcome; 60% flat / 75% progressive still leaves top-1%
≈10%, bottom-half ≈8%. 30% wealth tax keeps the middle class dominant and quantile shares in a band;
1% wealth tax ≈ 60% income tax (arXiv:2007.02934). Unbiased exchange (any rule): `G(t)→1`,
`L(t)→0`, `l(x,t)≤2⟨x⟩` (arXiv:2012.00206).

**Failure modes.** These are closed, conservative, production-free economies — results are about
*relative* distribution, not absolute wealth. The AC asymmetry (`min`-capped flow) is what makes
income tax weak; a symmetric exchange is more benign, so the 1%-vs-60% gap is model-dependent. Finite
`N` does not reach the condensation equilibrium within any practical run (relaxation is long), so a
non-rising Gini in a short run is not a refutation. Never present simulator output as an empirical
inequality forecast.

### 2.4 Mobility / liquidity diagnostic for simulated wealth
**Purpose.** Detect the "thermal death of the market": when exchange ceases, mobility collapses before
the Gini saturates, so it is an early warning.

**Formula.** Agent-level mobility and system liquidity:
$$l(x,t)=\int_0^\infty\!\!\int_{-x}^{x'} d\Delta\ \lvert\Delta\rvert\,\omega_{[x,x']\to[x+\Delta,x'-\Delta]}\,f(x',t),\qquad
L(t)=\frac{1}{2\langle x\rangle}\int_0^\infty l(x,t)\,f(x,t)\,dx\in[0,1].$$
Absorbing state: `l(x,t)=0` wherever `f(x,t)>0`. Bound `l(x,t)≤2⟨x⟩`.

**Required inputs.** Simulated (or real) wealth panel with pairwise transfer records, or an
exchange rule plus wealth vector to compute `ω` weights.

**Parameters & defaults.** Factor `1/2` cancels double counting; `L=1` = all wealth exchanged per
unit time, `L=0` = frozen economy.

**Observed effect sizes.** Under any unbiased binary exchange `lim_{t→∞}L(t)=0` and `G→1`
(arXiv:2012.00206). This is the quantitative statement behind the tax results: a rule that keeps
`L(t)` bounded away from 0 keeps `G` below 1 (arXiv:2007.02934).

**Failure modes.** `L` requires the pairwise rate `ω`, which is unobservable in real wealth data —
usable only inside a simulator or when an exchange rule is assumed. Definitional factor `1/2` is easy
to mis-apply.

### 2.5 κ-deformed Generalized Gamma fit to a wealth/income size distribution
**Purpose.** Fit the entire empirical wealth size distribution — bulk plus heavy tail — with one
four-parameter density, and read off Pareto exponent, Gini, and Lorenz orderings.

**Formula.** Kaniadakis functions `exp_κ(x)=(√(1+κ²x²)+κx)^{1/κ}`, `ln_κ(x)=(x^κ-x^{-κ})/(2κ)`. The
κ-GG density maximizes Shannon entropy under three constraints:
$$f(x\mid\kappa,\sigma,\theta_1,\theta_2)=\frac{1}{\sigma\,r_\kappa(\theta_1)}
\Bigl(\tfrac{x}{\sigma}\Bigr)^{\!\theta_1-1}\exp_\kappa\!\Bigl[-\tfrac1{\theta_2}\bigl(\tfrac{x}{\sigma}\bigr)^{\theta_2}\Bigr]
\sqrt{1+\tfrac{\kappa^2}{\theta_2^2}\bigl(\tfrac{x}{\sigma}\bigr)^{2\theta_2}}.$$
Small-`x` behavior `f ∼ x^{θ_1-1}`; large-`x` power law `f → a x_0^a / x^{a+1}` with
$$a=\frac{1}{\theta_1}-1,\qquad
x_0=\bigl(\tfrac{1}{\theta_2}\Gamma_\kappa(\cdot)\bigr)^{1/\theta_2}.$$
Gini from the Lorenz curve `L(u)=1/m ∫_0^x t f(t)dt`; generalized entropy `GE(ε)=(1/(ε(ε-1)))(𝔼[(X/m)^{ε+1}]-1)`
with MLD (`ε→0`) and Theil (`ε→1`) as limits.

**Required inputs.** A positive wealth/income vector `x` (individuals or brackets); or the pair of
simulated histograms on which to refit.

**Parameters & defaults.** Four parameters `κ∈[0,1]` (deformation), `σ>0` (scale), `θ_1,θ_2>0`
(shape). κ=0 recovers the three-parameter Generalized Gamma; `θ_1=θ_2` gives the κ-Generalized
(Clementi). Fit by maximum likelihood on the body + darker tail bins (the paper refits excluding the
`N=10^5` discreteness cutoff).

**Observed effect sizes.** `N=10^3`: `κ=1.3320, σ=1.1240, θ₁=221.3150, θ₂=0.7868, a=1.2193`;
`N=10^5`: `κ=1.7127, σ=1.3710, θ₁=342.7610, θ₂=0.9088, a=1.1670` (arXiv:1805.06929). Lorenz
ordering condition (`X⋞_L Y`) is `σ_x≤σ_y` and `θ₁(θ₂)≤θ₁(θ₂)_y`; distributions violating it are not
comparable.

**Failure modes.** `a<2` implies infinite theoretical variance, so moment-based Gini/GE are delicate
near the tail. The `N=10^5` fit shows an artificial cutoff from discrete saving propensities — do not
fit across it. `κ` affects only the tail, so it is weakly identified unless the tail is well sampled;
small samples cannot separate κ-GG from lognormal/Pareto mixtures (`risk-management-tails.md` covers
the Hill cross-check).

### 2.6 GDP-driven personal-income-distribution model with a Pareto threshold
**Purpose.** Project a full age×race×gender income distribution (and its Pareto-rich share) from a
single macro driver — usable only as a scenario engine.

**Formula.** `dM(τ₀,t)/dt = α{Σ(τ₀,t) - M(τ₀,t)/Λ(τ₀,t)}` with closed form
`M(t)=ΛΣ[1-exp(-αt/Λ)]`; capability and instrument grow as
`Σ(τ,t)=Σ(τ₀)[Y(τ)/Y(τ₀)]^{1/2}`, `Λ(τ,t)=Λ(τ₀)[Y(τ)/Y(τ₀)]^{1/2}`. Above critical time `T_c`,
`M(t)=M(T_c)exp[-(α/Λ)(t-T_c)]`, with `T_c(τ)=T_c(τ₀)[Y(τ)/Y(τ₀)]^{1/2}`. Exchange simulation uses
distributed saving `λ_i`; the Pareto threshold evolves as `M^P(τ)=M^P(τ₀)Y(τ)/Y(τ₀)`.

**Required inputs.** Real GDP per capita `Y(τ)` (working-age deflated); relative capability/instrument
supports; female instrument factor `FL(t)`; critical-age constants `T_c, T_S, T_A` and decay
constants `A,B`.

**Parameters & defaults.** `M^P(τ₀)=0.43` male / `0.29→0.39` female; `S_k,L_j∈{2,…,30}` discrete
uniform (`29×29=841`); `FL: 0.45 (1962)→0.65 (2014)`; `T_c` and the rich share both scale as
`√rGDPpc`.

**Observed effect sizes.** 1962 peak-age Pareto cell: 40,000 women vs 150,000 men; white-male rich
share ~30% (1967) → ~20% (2014); black-female share >5% only after 2001 (arXiv:2007.06530). The
model's contribution is a *decomposition*: gender/race gaps persist because of smaller work
instruments, not capability.

**Failure modes.** Single exogenous driver (`rGDPpc`) — no monetary, tax or portfolio channel.
Calibrated only on 1962–2014 US; race categories are not time-compatible (paper restricts to
black/white). Peak-income and critical-age estimates are noisy when cell counts are small.

## 3. Data requirements → available endpoints

Provider rows below are real entries in `strategies/endpoints.json`; **gap** means no current provider
can supply it.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Country/aggregate inequality & income-share series (by series id) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Real GDP per capita (driver for §2.6) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Macro indicator list via local gateway | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| Firm-level income/capital aggregates (corporate proxy) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| Fundamental data (secondary) | `https://www.alphavantage.co/query` | `fundamental_data` | alpha_vantage | ok |
| Daily equity prices (asset-wealth proxy, weak) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Institutional / large-shareholder holdings | `moomoo://get_shareholders_institutional` | `institution_data` | moomoo | gateway (not live-probed) |
| **Household income/wealth micro-data (IPUMS/CPS, WID, Fed DFA)** | — | — | — | **gap** |
| **Cross-country Gini / income-decile micro-data (PovcalNet, LIS)** | — | — | — | **gap** |
| **Personal/corporate tax rates and transfer schedules (policy panel)** | — | — | — | **gap** |
| **Intra-population wealth-change panel (panel survey with mobility)** | — | — | — | **gap** |

**What the gap costs, quantified.** Every empirical result above is calibrated on micro-data FinRobot
cannot fetch. arXiv:2007.06530 needs IPUMS/March-CPS individual records in one-year age cells across
`1962–2014` (≈51 annual cross-sections × 2 races × 2 genders), with the paper explicitly discarding
non-white/black races because the series are not time-compatible. arXiv:1409.3979 needs a
cross-country Gini panel (`N=130/137/139/140` for 1990/1995/2000/2005) from PovcalNet; without the
panel, only the theoretical alarming level (0.5) survives and the empirical two-sigma test cannot run.
arXiv:2012.00206 and arXiv:2007.02934 are *self-contained* — they need `N=10^3–10^5` simulated agents,
`10^9` iterations and `10^3` realizations, which is compute, not data — so §2.3–§2.4 are the only
buildable-now items. The corporate proxy (`tiingo`/`alpha_vantage` fundamentals, `moomoo` shareholder
lists) serves only the ownership-concentration side, and is a *firms-as-agents* stand-in for a
household wealth panel; it cannot reproduce a Gini.

## 4. Pitfalls, validation and measurement

- **Metric choice is not neutral.** Gini is one scalar; Lorenz ordering is partial (arXiv:1805.06929).
  Two distributions with equal Gini can have opposite tail risk once `a<2`. Report Gini **and** a tail
  exponent **and** a top-share, because the exponential/Rawls benchmark caps `G` at 0.5 while a Pareto
  upper class has no such cap (arXiv:1409.3979).
- **Normality is a pre-condition, not a formality.** The 1990 cross-country panel rejects Jarque–Bera
  (`p=0.049`) and the papers then *refuse* to compute a threshold; computing one anyway produces a
  meaningless "alarming level" (arXiv:1409.3979). Any threshold detector must gate on the normality
  test and suppress output on failure.
- **Two-sigma vs three-sigma is a choice with a stated cost.** The papers use two-sigma (right-tail
  `0.0228`) precisely because they want an early, actionable level; using three-sigma would push every
  threshold above the observed maximum. State which rule and why (arXiv:1409.3979).
- **Race/gender/age categories drift.** Census race definitions were revised repeatedly over the
  50-year window, so long series are not comparable; the reference paper restricts to black and white
  exactly to avoid this. Any re-estimation must reconcile category vintages or fall back to a shorter
  window (arXiv:2007.06530).
- **Unit of analysis.** Individual vs household vs family income changes the Gini materially;
  arXiv:2007.06530 explicitly uses *individual* incomes and argues household aggregates inherit
  fluctuating composition rules that add noise. Fix the unit before comparing to published Ginis.
- **Closed-system conservation is a modelling choice, not a law.** The kinetic/AC models conserve
  wealth (`Δ_j=-Δ_i`), which the paper itself notes is criticized (production is absent); results hold
  for *relative* distribution only. Do not read "condensation is inevitable" as a claim about a growing
  economy (arXiv:2012.00206, arXiv:2007.02934).
- **Tax results are model-dependent.** The 1%-wealth-tax ≈ 60%-income-tax equivalence depends on the
  asymmetric `min`-capped flow; a symmetric exchange would shrink the gap. Treat the ordering (stock
  tax ≫ flow tax) as robust, the ratio as not (arXiv:2007.02934).
- **Tail-fitting discipline.** Choose the Pareto cutoff on a Hill plot's stable region, never by IQR
  filtering (which deletes the very tail being estimated). κ is tail-only and weakly identified; report
  a lognormal/Pareto-mixture alternative whenever the tail has few points (arXiv:1805.06929;
  `risk-management-tails.md`).
- **Simulation-only status must be labelled.** §2.3–§2.4 produce distributions from assumed micro-rules
  with no market data; any P&L, forecast or policy ranking drawn from them is a scenario, not an
  estimate. Label every output accordingly (arXiv:2007.02934, arXiv:2012.00206).

## 5. Recommended first implementation in FinRobot

Ranked by value-per-effort against what the data layer can fetch today.

1. **Inequality statistic library (grouped-data Gini + graduation inverse).** *What:* `gini_from_brackets`,
   the order-statistic and sum-of-powers Gini estimators, and `m = 2G'/(1-G')`. *Data:* any decile/share
   table or a single headline Gini; optionally FRED `series/observations` for a panel. *Value:* makes
   FinRobot able to quantify an inequality series instead of echoing a headline number. *Pass:*
   reproduces the paper's `m` readings (Norway 0.667, Mexico ≈2, Namibia 5–6) from published Ginis.
   *Effort:* S.
2. **Alarming-level detector (JB gate + two-sigma).** *What:* a small routine that tests normality of a
   Gini panel and returns `μ+2σ` only when JB passes. *Data:* FRED Gini/income-share series by id.
   *Value:* turns the "0.4" folk rule into a testable, sample-specific threshold. *Pass:* on a
   1995/2000/2005-style panel, returns ≈0.58/0.57/0.56 and suppresses output on a 1990-style
   non-normal panel. *Effort:* S.
3. **Kinetic-exchange / artificial-chemistry simulator with tax rules.** *What:* port the pairwise
   exchange rules (yard-sale, asymmetric `min`), Gini and liquidity trackers, and the flat/progressive
   income-tax + wealth-tax + redistribution rules from §2.3. *Data:* none — self-contained.
   *Value:* the only place FinRobot can study distributional policy effects, and a sandbox for §4
   pitfalls. *Pass:* unbiased rules drive `G→1`, `L→0`; a ~30% wealth tax stabilizes quantile shares
   while a 30% income tax does not. *Effort:* M.
4. **κ-GG density fitter with Hill cross-check.** *What:* MLE of the four κ-GG parameters, tail
   exponent `a=1/θ₁-1`, Gini/GE readouts, Lorenz-order check. *Data:* any positive wealth/income vector
   (simulated, or a fetched distributional series). *Value:* a single density covering body and tail,
   with a defensible tail exponent. *Pass:* recovers `a≈1.17–1.22` on the paper's `N=10^3/10^5`
   simulations and agrees with a Hill estimate on the same tail (`risk-management-tails.md`).
   *Effort:* M.
5. **Mobility/liquidity diagnostic.** *What:* compute `l(x,t)` and `L(t)` from a simulator's transfer
   log; expose as an early-warning feature alongside Gini. *Data:* simulator only. *Value:* detects
   exchange freeze before Gini saturates. *Pass:* `L(t)→0` monotonically for unbiased rules and stays
   bounded under a wealth tax. *Effort:* S (after item 3).
6. **GDP-driven PID scenario engine (Kitov model).** *What:* the `Σ,Λ`-growth ODE, age profile, Pareto
   threshold evolution, and race/gender decomposition. *Data:* FRED real GDP per capita. *Value:* a
   macro-linked income-distribution projection and a documented capability-vs-instrument attribution.
   *Pass:* reproduces the qualitative 1962 vs 2014 convergence and the rich-share trend on US
   parameters. *Effort:* L.

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 1309.3771v1 | New models of income distribution, graduation as the explanation of Gini coefficient | 2013 |
| 1409.3979v1 | Rawls' Fairness, Income Distribution and Alarming Level of Gini Coefficient | 2014 |
| 2012.00206v2 | Wealth concentration in systems with unbiased binary exchanges | 2020 |
| 2007.06530v1 | Race and gender income inequality in the USA: black women vs. white men | 2020 |
| 2007.02934v1 | The Effects of Taxes on Wealth Inequality in Artificial Chemistry Models of Economic Activity | 2020 |
| 1805.06929v1 | A new κ-deformed parametric model for the size distribution of wealth | 2018 |
