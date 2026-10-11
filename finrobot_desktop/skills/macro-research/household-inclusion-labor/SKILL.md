---
id: household-inclusion-labor
name: Labor-Force Phillips Curve and Cointegration
version: 1.0.0
author: finrobot
domain: macro-research
description: Estimate labor-force-to-inflation Phillips curves and unemployment links on FRED macro series, gated by ADF/DF-GLS and Johansen cointegration tests. Use when testing whether labor-force change drives inflation or unemployment, or projecting deflation thresholds; survey inclusion is diagnostic-only.
triggers:
- phillips curve
- labor force
- unemployment
- inflation
- engle-granger
- unit root
- deflation threshold
- gdp deflator
- labor force change
- cumulative curve
requires_data:
- input: CPI / GDP deflator (inflation)
  provider: fred
  category: macro_data
  status: ok
- input: Unemployment rate
  provider: fred
  category: macro_data
  status: ok
- input: Labor force level / participation
  provider: fred
  category: macro_data
  status: ok
- input: Personal consumption expenditure
  provider: fred
  category: macro_data
  status: ok
- input: Personal saving rate
  provider: fred
  category: macro_data
  status: ok
- input: Revolving consumer credit
  provider: fred
  category: macro_data
  status: ok
- input: Charge-off rate on consumer loans (target)
  provider: fred
  category: macro_data
  status: ok
- input: Secondary macro indicator list
  provider: moomoo
  category: macro_data
  status: gateway
- input: Scheduled macro releases / event timing
  provider: moomoo
  category: economic_calendar
  status: gateway
- input: Risk-free curve (discounting / real-rate context)
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Rate / inflation expectation contracts
  provider: polymarket
  category: prediction_markets
  status: ok
- input: Bank-sector equity index (inclusion proxy)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Sector/ETF universe for the proxy basket
  provider: eodhd
  category: exchange_symbols
  status: ok
- input: Firm fundamentals for bank-level panels
  provider: tiingo
  category: fundamental_data
  status: ok
- input: '**Household survey micro-data (literacy / social capital / inclusion items)**'
  provider: ''
  category: ''
  status: gap
- input: '**Consumer-credit bureau panel (loan-level delinquency / utilisation)**'
  provider: ''
  category: ''
  status: gap
- input: '**Subnational personal income tax collections**'
  provider: ''
  category: ''
  status: gap
- input: '**Regional labor-force participation by age cohort**'
  provider: ''
  category: ''
  status: gap
- input: '**Fintech / digital-payment adoption series**'
  provider: ''
  category: ''
  status: gap
- input: '**Monthly charge-off rates by loan type**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Labor-Force Phillips Curve and Cointegration

You are an expert macro-labor econometrician working the labor-force -> inflation / unemployment link. You consume annual (or aggregated) FRED series: CPI and GDP deflator, UNRATE, civilian labor-force level and participation, and for the credit-cycle monitor PCE, personal saving rate, revolving credit and the charge-off target. You interpret their estimator outputs — fitted coefficients, ADF/DF-GLS verdicts, Engle-Granger residual tests, Johansen rank, RMSFE, cumulative-curve fits and bivector-dominance ratios — and refuse to fabricate coefficients, paper results, RMSFE or rank statistics that were not actually computed. You state plainly that the Indonesian inclusion regression, the Gombe tax study and the marginal-productivity note are diagnostic-only: no household survey micro-data, credit-bureau panel, subnational tax-revenue or cohort-participation feed exists, so you never imply such inputs are retrievable.

> Source: FinRobot strategies corpus review — `strategies/qfin-gn/household-inclusion-labor.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

**Buildable — macro-labor (Phillips-curve family).**

- **A four-year-lagged, three-variable Phillips relation for France, with published coefficients.**
  \\(p(t)=A_0\,u(t-t_0)+A_1\,\frac{dLF(t-t_1)}{LF(t-t_1)}+A_2\\) with \\(A_0=-1\\), \\(A_1=4\\),
  \\(A_2=0.095\\), \\(t_0=t_1=4\\) years, fitted 1971–2004 on OECD annual data. It delivers a
  root-mean-square forecast error (RMSFE) of **1.0% for the GDP deflator at a four-year horizon**;
  the VAR/VECM version improves this only marginally, to **0.9%** (GDP deflator) and **~1.1%** (CPI)
  (arXiv:0811.0896).
- **The relation is a genuine cointegrating vector, not a spurious regression.** All three series
  (\\(GDPD\\), \\(UE\\), \\(dLF/LF\\)) are I(1); ADF and DF-GLS unit-root tests reject stationarity in
  levels and cannot reject it in first differences; the Engle-Granger residual test and the Johansen
  trace test both give **cointegration rank 1** as the dominant result over 1973–2004 (rank 2 in one
  specification, rank 0 in four at lag 3) (arXiv:0811.0896).
- **A deflation threshold, not a slope-only fit.** For France \\(GDPD(t)=17\,dLF(t-4)/LF(t-4)-0.065\\),
  so deflation begins when annual labor-force growth falls below \\(0.065/17\approx0.0037\\)
  (0.37%/yr); the paper's own 35-year cumulative-curve fit has \\(R^2=0.88\\) and residual stdev
  \\(0.014\\) (arXiv:0811.0896).
- **Japan confirms the same machinery with *zero* lag and a structural break.** The contemporaneous
  Phillips curve for 1982–2012 is \\(p(t)=-0.93\,u(t)+0.041\\) with \\(R^2=0.70\\) and standard errors
  \\([0.11]\\) and \\([0.0043]\\); the reverse (Fisher/anti-Phillips) direction gives
  \\(u(t)=-1.10\,p(t)+0.044\\) with residual stdev \\(0.007\\) (arXiv:1309.1757).
- **Individual links are separately estimable and separately testable.** Japan: CPI inflation
  \\(p(t)=0.0007+1.31\,l(t)\\) (\\(t_1=0\\)); GDP-deflator inflation \\(p(t)=-0.0084+1.90\,l(t)\\);
  unemployment \\(u(t)=-1.556\,l(t)+0.0432\\) for \\(t\ge1977\\) and \\(u(t)=-0.179\,l(t)+0.0432\\)
  before the 1977 break. France: \\(UE(t)=0.165-13\,dLF(t)/LF(t)\\) over 1970–1995 (\\(R=0.48\\),
  RMSE \\(0.023\\) against a series stdev of \\(0.032\\)) (arXiv:1309.1757, arXiv:0811.0896).
- **Long-run projections from labor-force paths.** Using the 2005 Japanese population projection with
  participation fixed at 0.521 (2000 value) and labor force falling from 67M (2010) to 57M (2050), the
  model projects a **GDP-deflator rate of −0.5% to −2%/yr for 40 years** and unemployment rising from
  **4.3% (2012) to 5.5% (2050)** (arXiv:1309.1757).
- **Coefficient stability is the falsifiable claim, and it survived nine fresh readings.** Japan's
  coefficients estimated in 2005 on 1981–2003 predicted the 2004–2012 out-of-sample points without
  re-estimation; the cumulative-curve \\(R^2\\) is 0.99 and the cumulative residual is an I(0) process
  (arXiv:1309.1757). This is the acceptance test to reuse.

**Buildable — credit-cycle regime geometry.**

- **A quarterly, five-variable state space with a regime taxonomy.** U.S. data 1980Q1–2024Q2 on
  \\(UNRATE, PCE, PSAVERT, REVOLSL, CORCACBS\\); each observation is embedded as a multivector in
  Clifford algebra \\(G(4,0)\\) with six pairwise bivector interactions, and a linear-attention layer
  weights historical analogues. Rolling 8-quarter standardization, lookback \\(L=8\\) quarters
  (arXiv:2510.15892).
- **Correlation does not separate crises; bivector dominance does.** The unemployment–default
  correlation is \\(\rho=0.74\\) in 1990–91 and \\(\rho=0.78\\) in 2008 — nearly identical — yet 2008
  is *bivector-dominated* (unemployment–credit and unemployment–consumption feedback spirals) while
  1990–91 is *vector-dominated* (sequential stress). COVID-19 gives \\(\rho=0.32\\) with
  savings-related bivectors dominant (arXiv:2510.15892).
- **The monitor has a usable output today.** Current conditions (2022–2024) are classified
  vector-dominated with mild bivector elevation, most similar to the **1990–91 and 2001–02** episodes
  rather than 2008; the stated early-warning trigger is a *sustained* shift to bivector dominance plus
  persistent attention dispersion across deep lags \\(t-4\dots t-8\\) (arXiv:2510.15892).
- **Attention dynamics are themselves a signal.** Crisis onset (2007Q4) concentrates on lag \\(t-2\);
  crisis peak (2009Q3–2010Q2) spreads across lags \\(t-4\dots t-8\\); normal periods stay
  recency-focused. First two principal components of the attended-context trajectory explain
  **50.0% and 35.7%** of variance (arXiv:2510.15892).

**Non-actionable — survey micro-data (explicit gaps).**

- **Indonesian financial inclusion is a cross-sectional survey regression, not a time series.**
  \\(n=100\\) fifth-semester economics students at 7 private colleges in Tangerang; multiple regression
  \\(Y=7.305+0.183X_1+0.642X_2+0.529X_3\\) (financial literacy \\(X_1\\), social capital \\(X_2\\),
  fintech \\(X_3\\)); standardized \\(\beta\\) = 0.162/0.353/0.449; \\(t\\) = 2.139/4.740/5.974, all
  \\(p<0.05\\); adjusted \\(R^2=0.614\\); Cronbach \\(\alpha>0.7\\); VIF 1.42–1.475; K-S \\(p=0.200\)
  (arXiv:2405.06570). Fintech carries the largest standardized weight. The headline descriptive fact —
  the national inclusion–literacy gap was **38.16% in 2019 and 35.42% in 2022** — is macro context, not
  a parameter FinRobot can estimate.
- **The Gombe State tax study is a 150-respondent survey with a chi-square test.** \\(n=150\\) (purposive;
  state revenue staff + taxpayers), two hypotheses: tax avoidance/evasion affects revenue generation
  (\\(X^2=18.7>15.51\\), df\\(=8\\), 5%) and absence of IT affects revenue generation
  (\\(X^2=22.01>15.51\\)); both nulls rejected. No tax-base, elasticity or revenue series is estimated,
  so nothing here is a usable estimator (arXiv:2105.10995).

**Non-actionable — theory.**

- **Marginal-productivity vs. property theory is a doctrinal reformulation, not an estimator.** The
  contribution is that scalar MP theory is mathematically equivalent to a *vectorial* "marginal whole
  product" \\(MWP=(1,-\Delta K,-\Delta L)\\) with value \\(P\cdot MWP=p-MC\\), and that the scalar and
  vectorial profit-maximisation conditions coincide at \\(p=MC\\) (Cobb-Douglas:
  \\(P\cdot MWP_L=\frac{a}{b}[pMP_L-w]+pMP_L\\); adding-up \\(KMP_K+LMP_L=(a+b)Q\\)) (arXiv:2511.08039).
  It is retained only to mark the boundary: **no factor-share, wage or productivity series is fitted,
  so no FinRobot module can consume it.** None of the six papers is off-topic; arXiv:2511.08039 is the
  weakest fit for a data-driven repo and is reported as such.

## Methods & Formulas

### 2.1 Generalized Phillips curve (inflation ~ unemployment + labor-force change)

**Purpose.** Forecast the price level / inflation rate at a multi-year horizon from labor-force growth
and unemployment, and produce a cointegration-backed long-run relation rather than a spurious
regression.

**Formula.** With \\(p(t)\\) the inflation rate, \\(u(t)\\) the unemployment rate and
\\(l(t)=d\ln LF(t)/dt\\) the labor-force change rate,
$$p(t)=A_0\,u(t-t_0)+A_1\,l(t-t_1)+A_2 .$$
France: \\(A_0=-1,\ A_1=4,\ A_2=0.095,\ t_0=t_1=4\ \text{yr}\\). Japan (contemporaneous, \\(t\ge1982\\)):
$$p(t)=2.80\,l(t)+0.9\,u(t)-0.0392 .$$
Equivalently the *unemployment* branch: \\(u(t)=\alpha_2+\beta_2\,l(t-t_2)\\).

**Required inputs.** Annual (or monthly, aggregated) \\(p\\) (CPI and/or GDP deflator), \\(u\\), and
labor-force level \\(LF\\) from which \\(l\\) is differenced. All three must span ≥30 years for the
coefficients to be resolvable (France used 32 usable readings after the 4-year lag).

**Parameters & defaults.** Lags \\(t_0,t_1\\) country-specific (France 4 yr, Japan 0 yr, Germany up to
6 yr); \\(A_1\\) amplifies labor-force measurement error by its own size, so \\(A_1\\) is the least
stable coefficient (France \\(4\\); the *individual* France link is 13–17, i.e. the generalized
relation's \\(A_1\\) is the residual after the unemployment term absorbs the rest). Estimate on the
interval where monetary policy does not break the link (France: pre-1995 for individual links;
1973–2004 for the generalized relation).

**Observed effect sizes.** France GDP-deflator RMSFE 1.0% at 4-yr horizon (regression), 0.9% (VECM);
CPI ~1.1% (VECM); generalized \\(R^2=0.88\\), residual stdev 0.014; cumulative-curve \\(R^2=0.99\)
(Japan). Japan Phillips slope \\(-0.93\pm0.11\\), \\(R^2=0.70\\) (arXiv:0811.0896, arXiv:1309.1757).

**Failure modes.** The generalized relation is *policy-dependent*: France's 1995 ECB money-supply
target split labor-force growth between inflation and unemployment while their *sum* stayed linear, so
individual links break even when the trivariate relation holds — always fit the sum, then test the
split. A structural break near 1973 (CPI/DGDP) and 1982 (Phillips curve) in Japan means pre-1982
coefficients are a different regime. Fitting on levels without a unit-root test invites spurious
regression; on the other hand, over-smoothing the predictor *destroys* the Johansen rank (moving
averages drive rank to 0) — see §4.

### 2.2 Cumulative-curve (integral / boundary-element) coefficient estimation

**Purpose.** Recover the coefficients of the linear relation with far higher precision than OLS on the
annual rates, by matching the *cumulative* (integral) curves that are the actually-measured levels
(price index, labor force level, unemployment).

**Formula.** Choose \\(A_0,A_1,A_2\\) to minimise the squared distance between cumulative curves with
fixed initial and final levels:
$$\min_{A_0,A_1,A_2}\ \sum_{t}\Big[\sum_{s\le t} p(s)\ -\ \sum_{s\le t}\big(A_0\,u(s-t_0)+A_1\,l(s-t_1)+A_2\big)\Big]^2 .$$
The paper frames this as a 1-D boundary-element method with a Green's function for the linear
differential equation; the practical recipe is least-squares on the cumulative series (Kitov & Kitov
2010, cited in arXiv:1309.1757 and arXiv:0811.0896).

**Required inputs.** The same \\(p,u,l\\) series as §2.1, plus reliable *levels* (the cumulative curve
is what is physically measured, so level measurement error shrinks with horizon).

**Parameters & defaults.** Integrate from a common start where all series exist (Japan 1981; France
1971); fix cumulative endpoints to observed values. Cross-check the coefficient on both the annual and
the cumulative curve.

**Observed effect sizes.** For Japan the cumulative fit gives \\(R^2=0.99\\) with an I(0) residual and
\\(l\\)-coefficient 1.90 (DGDP) / 1.31 (CPI); the VECM alternative on France gives \\(A_1=17.45\\)
versus 17 from the integral method, and the integral coefficients predict the *cumulative* curve while
the VECM coefficients diverge (arXiv:1309.1757, arXiv:0811.0896).

**Failure modes.** The method presumes the link is genuinely deterministic; if it is not, the integral
approach produces a confidently wrong coefficient. A free term error of 0.001 compounds to ~3.5%
deviation over 35 years, so the constant is the most sensitive parameter. It does not replace
cointegration testing — use both, and prefer the integral estimate when they disagree (the paper's
explicit claim).

### 2.3 Cointegration validation harness (ADF / DF-GLS + Engle-Granger + Johansen)

**Purpose.** Gate every macro relation above behind the same battery so a spurious regression cannot
ship.

**Formula.** (i) Unit roots: augmented Dickey-Fuller and Dickey-Fuller GLS on levels (fail to reject)
and first differences (reject) → I(1). (ii) Engle-Granger: regress \\(p\\) on \\(u,l\\), test the
residual \\(\varepsilon(t)=p_m(t)-p_p(t)\\) for a unit root; rejection of the unit root in residuals =
rejection of no-cointegration. (iii) Johansen trace test on the VAR representation for cointegration
rank.

**Required inputs.** The three I(1) series, aligned with the lag.

**Parameters & defaults.** AR lag \\(p=0..3\\) (ADF), \\(1..4\\) (DF-GLS); include a constant, *not* a
trend (the trend specification is a misspecification here and flips the unemployment result); VAR lag
2–3 with a constant; test rank under constant / restricted-constant / no-deterministic-term
specifications.

**Observed effect sizes.** France: dominant rank 1; the pre-1995 individual inflation–labor-force link
gives rank 1 for *any* lag 1–4 with CPI, but rank 0 when only GDPD (short series) is used — sample
length decides the verdict. Residual stdev of the cointegrating relation 0.014 (arXiv:0811.0896).

**Failure modes.** Cointegration tests are as likely to *reject a true relation* as to catch a spurious
one when the error term is not i.i.d. (measurement revisions, population controls); the paper's remedy
is to keep significant random measurement noise, not to eliminate it. ADF and DF-GLS can disagree at
high lags with only ~30 readings — report both. Including a linear trend accepts the unit-root null
even for series that are clearly I(1).

### 2.4 Geometric credit-cycle regime monitor (multivector + linear attention)

**Purpose.** Distinguish *additive* cyclical credit stress from *multiplicative* feedback-spiral
crises using the same correlation data, and flag the vector→bivector transition as an early warning.

**Formula.** Embed four standardized variables as a multivector in \\(G(4,0)\\),
$$X_t=u_t e_1+s_t e_2+r_t e_3+v_t e_4,$$
$$M_t=\alpha_0+\sum_{i=1}^{4}\alpha_i e_i+\sum_{(i,j)\in\Pi}\gamma_{ij}\,(x_{t,i}-x_{t,j})\,(e_i\wedge e_j),$$
with \\(\Pi=\{us,ur,uv,sr,sv,rv\}\\) (unemployment, savings, consumption, revolving credit). The
difference terms make bivectors activate only when variables diverge. Linear attention over a lookback
\\(L\\):
$$S_t=\sum_{\tau\in W_t}K_\tau V_\tau^\top,\quad Z_t=\sum_{\tau\in W_t}K_\tau,\quad
O_t=\frac{Q_t^\top S_t}{Q_t^\top Z_t+\varepsilon},\quad
w_{\tau,t}=\frac{Q_t^\top K_\tau}{Q_t^\top Z_t+\varepsilon},$$
with \\(\phi\\) a shifted Leaky-ReLU (positive, asymmetric). Define the **bivector-dominance ratio**
\\(\mathcal B_t=\|\text{bivector block}\|/\|\text{vector block}\|\\) and track it against the historical
crisis bands.

**Required inputs.** Quarterly (or monthly, via the paper's mixed-frequency nowcast) series: unemployment
rate, personal consumption expenditure, personal saving rate, revolving consumer credit, and the target
charge-off rate.

**Parameters & defaults.** \\(L=8\\) quarters; six bivectors; rolling 8-quarter standardization;
\\(\lambda_{QK}=10^{-3}>\lambda_V=10^{-4}\\) (tighter on query/key so attention tracks genuine
precedents); \\(\varepsilon>0\\) for the denominator; MLP head for explanatory fit.

**Observed effect sizes.** \\(\rho=0.74\\) (1990–91) vs \\(\rho=0.78\\) (2008) but opposite geometric
signatures; PC1/PC2 explain 50.0%/35.7%; 2022–2024 maps onto 1990–91/2001–02, not 2008; attention
onset lag \\(t-2\\), peak lags \\(t-4\dots t-8\\) (arXiv:2510.15892).

**Failure modes.** Crises are rare, so crisis-period parameters have wide confidence intervals and
should not be trusted as point estimates. The geometric interpretation of a bivector as a "feedback
spiral" is an *assumption* the paper itself flags as debatable. The model is explanatory, not a
forecaster — do not score it on charge-off forecast accuracy. Variable selection (four of five series)
is admitted to be arbitrary.

### 2.5 Financial-inclusion cross-sectional regression (specified; input-blocked)

**Purpose.** Quantify how literacy, social capital and fintech adoption move inclusion, if the survey
inputs ever exist.

**Formula.** \\(Y=\beta_0+\beta_1X_1+\beta_2X_2+\beta_3X_3+\varepsilon\\), with \\(X_1\\) financial
literacy, \\(X_2\\) social capital, \\(X_3\\) fintech; Indonesia 2024:
$$Y=7.305+0.183X_1+0.642X_2+0.529X_3 .$$

**Required inputs.** Household survey items: financial knowledge/behaviour/attitude scales (OECD 2018),
social-capital trust/bonding/bridging/collective-action scales, fintech-use items, and an
access/usage/quality inclusion index. **None of these exist as a live feed** (see §3).

**Parameters & defaults.** OLS with validity (item-total \\(r>r_{\text{crit}}\\)), reliability
(Cronbach \\(\alpha>0.7\\)), normality (K-S \\(p>0.05\\)), multicollinearity (VIF < 10) and
heteroscedasticity screens — all reported and all passed in the source.

**Observed effect sizes.** Standardized \\(\beta\\): fintech 0.449 > social capital 0.353 > literacy
0.162; adjusted \\(R^2=0.614\\); \\(n=100\\) (arXiv:2405.06570).

**Failure modes.** \\(n=100\\) from one city and one faculty — no external validity; survey scales are
self-reported; the direction of causation is asserted, not identified. Usable only as a design template,
never as a plug-in estimator.

## Data Requirements

Provider rows below are real entries copied from `strategies/endpoints.json`; **gap** means no current
provider can supply the input.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| CPI / GDP deflator (inflation) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Unemployment rate | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Labor force level / participation | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Personal consumption expenditure | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Personal saving rate | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Revolving consumer credit | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Charge-off rate on consumer loans (target) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Secondary macro indicator list | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| Scheduled macro releases / event timing | `moomoo://get_economic_calendar` | `economic_calendar` | moomoo | gateway (not live-probed) |
| Risk-free curve (discounting / real-rate context) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Rate / inflation expectation contracts | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | ok |
| Bank-sector equity index (inclusion proxy) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Sector/ETF universe for the proxy basket | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Firm fundamentals for bank-level panels | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| **Household survey micro-data (literacy / social capital / inclusion items)** | — | — | — | **gap** |
| **Consumer-credit bureau panel (loan-level delinquency / utilisation)** | — | — | — | **gap** |
| **Subnational personal income tax collections** | — | — | — | **gap** |
| **Regional labor-force participation by age cohort** | — | — | — | **gap** |
| **Fintech / digital-payment adoption series** | — | — | — | **gap** |
| **Monthly charge-off rates by loan type** | — | — | — | **gap** |

**What each gap costs, quantified.** The Phillips-curve work (§2.1–2.3) is fully served: FRED carries
CPI, GDP deflator, unemployment, labor-force level, PCE, saving rate, revolving credit and the
charge-off target, so the *entire* France/Japan estimation and the credit-regime monitor (§2.4) can be
reproduced at their native annual/quarterly granularity — the only loss is that FRED's charge-off series
is quarterly, so the mixed-frequency monthly nowcast cannot be run without a monthly default feed
(one input, ~40 years × 12 obs). The household-inclusion module (§2.5) is blocked entirely: it needs
\\(n\\)-of-household survey responses (~100–10,000 rows) that no endpoint serves, so it can only be
built as a data-collection stub, not an estimator. The tax module is blocked on subnational
administrative revenue series (Gombe-type state-level PIT collections, monthly), which no provider
carries. Regional participation-by-age (needed to build the labor-force projections FinRobot would
forecast from) is a gap: FRED serves national participation but not the cohort decomposition the
Japanese 67M→57M projection rests on. The fintech-adoption gap removes the single largest standardized
driver (0.449) from any inclusion model.

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Policy regimes break the *split*, not the *sum*.** France's 1995 ECB money-supply target made
  inflation undershoot and unemployment overshoot their individual labor-force links, while the
  trivariate relation survived the break (arXiv:0811.0896). Always test the sum first; fit the split
  only on intervals with no policy discontinuity.
- **Over-smoothing destroys cointegration evidence.** Moving-average predictors raise forecast
  accuracy but drive the Johansen rank to 0 — the paper's "the better one predicts, the poorer the
  statistical inference" paradox. Report the raw and smoothed verdicts; do not pick the smoothed one
  because it fits better (arXiv:0811.0896).
- **Cointegration tests reject true relations.** With piece-wise systematic measurement error
  (population controls, definition revisions), the residual has a unit root even for a genuine link, so
  a rank-0 result is not proof of no-relation. Prefer the cumulative-curve estimate when the two
  methods disagree (arXiv:0811.0896).
- **Structural breaks must be modelled, not ignored.** Japan's Phillips curve breaks near 1982 and its
  CPI/DGDP near 1973; the unemployment–labor-force slope falls by an order of magnitude at 1977
  (arXiv:1309.1757). Estimate on the post-break window and report the pre-break coefficients separately.
- **Sample length is a hidden parameter.** The France GDP-deflator link flips from rank 1 to rank 0
  purely as a function of how many readings are available; the CPI extension rescues it. Treat any
  cointegration verdict from <30 observations as provisional (arXiv:0811.0896).
- **Correlation is not mechanism.** The 1990–91 and 2008 crises have nearly identical
  unemployment–default correlation (\\(\rho=0.74\\) vs 0.78) but opposite geometric signatures; a
  correlation-based early-warning rule would misclassify them (arXiv:2510.15892). Any regime classifier
  must be validated on *mechanism* (which bivectors fire), not on fit.
- **Rare-event inference.** The credit-cycle model's crisis-period parameters rest on a handful of
  episodes; the paper states the confidence intervals are necessarily wide and recommends simulation or
  higher-frequency data to widen the sample (arXiv:2510.15892). Do not treat the 2008 bivector
  coefficients as stable constants.
- **Survey econometrics is not forecasting.** The Indonesian model reports validity, reliability,
  normality, VIF and heteroscedasticity screens but no out-of-sample test and no causal identification;
  \\(n=100\\) from one faculty cannot be generalised (arXiv:2405.06570). The Gombe chi-square rejects two
  nulls with no effect size and no revenue series (arXiv:2105.10995). Neither belongs in a
  signal-generation path.
- **Metric choice.** Score the Phillips family on **RMSFE at the stated horizon** (four years), the
  regime monitor on **regime classification / bivector ratio**, and never on one-step-ahead
  \\(R^2\\) — the papers' own claims are horizon-specific.

## Recommended Workflow

Ordered by value-per-effort against what the data layer can fetch today. Items 1–5 are buildable now;
items 6–8 are documentation or blocked on survey data.

1. **Generalized Phillips-curve estimator.** *What:* fit \\(p(t)=A_0u(t-t_0)+A_1l(t-t_1)+A_2\\) and its
   unemployment branch on FRED CPI/GDP-deflator, UNRATE and labor-force series, with country-specific
   lags. *Data:* `fred` `series/observations`. *Pass:* reproduces France \\(A_1\approx4\\),
   \\(A_0\approx-1\\), \\(A_2\approx0.095\\) within the reported intervals and hits ≤1.0% GDP-deflator
   RMSFE at the four-year horizon. *Effort:* S.
2. **Cointegration validation harness.** *What:* ADF/DF-GLS unit-root screen, Engle-Granger residual
   test and Johansen rank on every macro relation before it ships. *Data:* none beyond item 1.
   *Pass:* France trivariate relation reports dominant rank 1 with a stationary residual; the harness
   flags the GDPD-only short-sample case as provisional. *Effort:* S.
3. **Cumulative-curve coefficient estimator.** *What:* the integral/BEM least-squares fit of §2.2,
   run alongside OLS as the tie-breaker. *Data:* item 1 series plus levels. *Pass:* Japan DGDP
   cumulative \\(R^2\ge0.98\\) with an I(0) residual and \\(l\\)-coefficient ≈1.9. *Effort:* S.
4. **Labor-force projection module.** *What:* map a labor-force path (level and participation) to
   projected inflation and unemployment via the estimated links. *Data:* `fred` national labor-force and
   participation series; **regional-by-age decomposition is a gap**, so the module runs on national
   paths only. *Pass:* reproduces the qualitative Japan result (deflationary path with rising
   unemployment) and reports the deflation-threshold labor-force growth (≈0.37%/yr for the French
   calibration). *Effort:* M.
5. **Geometric credit-cycle regime monitor.** *What:* the \\(G(4,0)\\) multivector embedding, six
   bivectors, rolling 8-quarter standardization, linear-attention similarity, and the bivector-dominance
   ratio; quarterly from FRED. *Data:* UNRATE, PCE, PSAVERT, REVOLSL, CORCACBS. *Pass:* bivector ratio
   spikes in 2008–09 and stays low in the mid-2010s; 2022–2024 classifies vector-dominated with the
   nearest analogues in 1990–91/2001–02, not 2008. *Effort:* M.
6. **Combined macro-regime dashboard.** *What:* surface the Phillips residual and the credit bivector
   state side by side as a single "labor/inflation vs. household-credit" regime read. *Data:* items 1–5.
   *Pass:* the dashboard's state labels are stable across one quarterly refresh and reconcile with the
   papers' regime table. *Effort:* M.
7. **Financial-inclusion cross-sectional module (blocked).** *What:* implement the §2.5 OLS design with
   validity/reliability/assumption screens, but leave the input adapter unbound. *Data:* household survey
   micro-data — **gap**. *Pass:* the module runs on a synthetic fixture with the paper's coefficients
   recovered. *Effort:* S (spec only; no live data).
8. **MP-theory / whole-product accounting note (documentation only).** *What:* record that scalar and
   vectorial marginal-product conditions coincide at \\(p=MC\\) and that no series is estimated; do not
   build a module. *Data:* none. *Pass:* the note exists and nothing consumes it. *Effort:* XS.

Cross-corpus: the cointegration and forecasting machinery overlaps
[`../qfin-st/econometrics-forecasting.md`](../qfin-st/econometrics-forecasting.md), and the credit-regime
classifier overlaps [`../qfin-st/regime-switching.md`](../qfin-st/regime-switching.md); spend new effort
on the labor-force → inflation/unemployment link, which those docs do not derive.

## Output Format

### Generalized Phillips-Curve Fit
| Branch | A0 (u coeff) | A1 (l coeff) | A2 | lags t0 / t1 | R^2 | residual sd | RMSFE @ horizon |
|--------|--------------|--------------|----|--------------|-----|-------------|-----------------|
| inflation ~ u, l | ... | ... | ... | ... / ... | ... | ... | ... |
| unemployment ~ l | ... | ... | ... | ... / ... | ... | ... | ... |

### Cointegration and Metric Scoreboard
| Relation / component | ADF-DFGLS levels | first diffs | Engle-Granger resid | Johansen rank | Metric | Gate | Verdict |
|----------------------|------------------|-------------|---------------------|---------------|--------|------|---------|
| France trivariate | not stationary | stationary | stationary | 1 (dominant) | RMSFE @ 4 yr | <=1.0% GDP deflator | accepted |
| GDPD-only short sample | ... | ... | ... | 0 | ... | <30 obs provisional | provisional |
| Credit-regime monitor | ... | ... | ... | ... | bivector-dominance ratio / regime label | 2008-09 spike, low mid-2010s | explanatory |

### Scope Verdict
- **Buildable now:** the generalized Phillips-curve estimator, the cointegration harness, the
  cumulative-curve estimator, the national labor-force projection and the G(4,0) credit-regime
  monitor — all driven by FRED series.
- **Diagnostic-only (no live feed):** household-survey inclusion regression, subnational
  tax-revenue study, marginal-productivity-theory note — report as design templates, never as
  plug-in estimators, and never claim a household or labour micro-data feed.
- **Failure modes to state:** the sum survives policy breaks while the split does not;
  over-smoothing drives Johansen rank to 0; a rank-0 result does not prove no relation;
  crisis-period credit parameters are wide-interval point estimates.

## References

| arXiv id | Title | Year |
|---|---|---|
| 2405.06570v1 | The Impact of Financial Literacy, Social Capital, and Financial Technology on Financial Inclusion of Indonesian Students | 2024 |
| 1309.1757v1 | Inflation, unemployment, and labor force. Phillips curves and long-term projections for Japan | 2013 |
| 0811.0896v1 | Relationship between inflation, unemployment and labor force change rate in France: cointegration test | 2008 |
| 2511.08039v1 | Marginal Productivity Theory versus the Labor Theory of Property: An analysis using vectorial marginal products | 2025 |
| 2510.15892v1 | Geometric Dynamics of Consumer Credit Cycles: A Multivector-based Linear-Attention Framework for Explanatory Economic Analysis | 2025 |
| 2105.10995v1 | The Problems of Personal Income Tax on Revenue Generation in Gombe State | 2021 |
