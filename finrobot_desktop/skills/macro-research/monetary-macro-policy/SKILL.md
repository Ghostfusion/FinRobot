---
id: monetary-macro-policy
name: Monetary Policy Transmission and Macro Uncertainty
version: 1.0.0
author: finrobot
domain: macro-research
description: Measure monetary-policy transmission with FOMC event-window rate shocks, UC-SV inflation-uncertainty estimation, and the QE yield-to-wealth-to-GDP channel ladder. Use when quantifying a policy shock, dating a transmission lag, or testing inflation-uncertainty and price-level relations.
triggers:
- monetary policy
- fomc
- policy shock
- inflation uncertainty
- transmission
- quantitative easing
- central bank
- uc-sv
- interest rate
requires_data:
- input: US CPI inflation, industrial production, money supply, Fed balance sheet, WTI oil (monthly/quarterly)
  provider: fred
  category: macro_data
  status: ok
- input: Long-term government yield curve (daily 10Y etc.)
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Policy rate target (fed funds / FOMC target range)
  provider: moomoo
  category: fed_watch
  status: gateway
- input: FOMC / macro announcement dates and times
  provider: moomoo
  category: economic_calendar
  status: gateway
- input: Non-US macro indicator lists (Eastern Europe CPI/IP)
  provider: moomoo
  category: macro_data
  status: gateway
- input: DJ sector / equity index prices (monthly log levels)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Equity index prices (secondary)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Equity index prices (tertiary)
  provider: massive
  category: core_stock_apis
  status: ok
- input: Equity/index OHLCV (fourth source)
  provider: stockdata
  category: core_stock_apis
  status: ok
- input: News text for a news-based uncertainty index
  provider: eodhd
  category: news_data
  status: ok
- input: News sentiment (uncertainty proxy)
  provider: eodhd
  category: news_sentiment
  status: ok
- input: News sentiment (alternative)
  provider: alpha_vantage
  category: news_sentiment
  status: ok
- input: Global news doc stream (uncertainty text)
  provider: gdelt
  category: news_sentiment
  status: fail
- input: Macro/policy prediction-market contracts
  provider: polymarket
  category: prediction_markets
  status: ok
- input: '**Bitcoin spot price (monthly and hourly)**'
  provider: ''
  category: ''
  status: gap
- input: '**Monetary Policy Uncertainty index (Baker–Bloom–Davis)**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Monetary Policy Transmission and Macro Uncertainty

You are an expert monetary-macroeconomics researcher specialising in policy-shock measurement and central-bank transmission. You consume FRED macro series (CPI, industrial production, money, balance sheet, oil), the Treasury yield-curve row, the fed_watch policy-rate target, and FOMC announcement timestamps from the economic calendar, and you interpret them into event-window responses, inflation-uncertainty series, and transmission-ladder verdicts — never fabricating EGARCH asymmetry parameters, Granger F-statistics, cointegration coefficients, or published QE effect sizes that were not actually estimated here.

> Source: FinRobot strategies corpus review — `strategies/qfin-gn/monetary-macro-policy.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **Inflation uncertainty and output-growth uncertainty are estimated jointly as conditional variances, and
  their interaction is regime-dependent.** A bivariate AR(12)-EGARCH(1,1) on monthly CPI inflation and
  industrial-production growth for six Eastern European economies, 2000-01 to 2011-07 (~139 monthly
  observations each, IFS), finds the EGARCH asymmetry parameter $\gamma$ positive and significant for
  Bulgaria (0.615) and the Czech Republic (0.523) — positive inflation shocks raise uncertainty more than
  negative ones, i.e. the Friedman–Ball effect — but *negative* for Estonia (−0.17, n.s.) and Poland
  (−0.081, n.s.), the two most credible regimes (arXiv:1303.6192).
- **Currency-board economies show higher nominal and real volatility than inflation-targeting economies in
  the same window.** Annualised monthly inflation SD (mean, %): Bulgaria 3.34 (5.73), Estonia 2.85 (4.14),
  Lithuania 3.33 (3.01) versus Czech 1.83 (2.46), Poland 1.58 (2.85), Romania 7.71 (11.21); IP-growth SD
  9.92/14.08/11.23 versus 8.98/6.75/5.82. Inflation-equation $R^2$ 0.11–0.39, growth-equation $R^2$
  0.08–0.73 (arXiv:1303.6192).
- **Granger causality runs inflation → inflation uncertainty in 3 of 6 countries, with the credible board as
  the exception.** Inflation Granger-causes inflation uncertainty with a positive sum of lagged coefficients
  for Romania, Bulgaria and Lithuania (F up to 29.41 at 4 lags) and with a negative sum for Estonia
  (F = 43.62 at 4 lags); inflation does *not* Granger-cause output-growth uncertainty in any country
  (arXiv:1303.6192).
- **The regime comparison is itself a null.** The paper's own conclusion is that the results "do not allow
  us to judge which monetary regime is more appropriate", attributing the convergence to EU-accession
  anchoring; regime labels carry no information for this nexus over 2000–2011 (arXiv:1303.6192).
- **Stock prices, inflation and inflation uncertainty are cointegrated in the long run for 8 of 10 US Dow
  Jones sector indexes, with the sign opposite to the Fisher effect.** Gregory–Hansen cointegration with one
  endogenous break on monthly 2002M7–2015M10 data (~160 obs; CPI/IP from FRED, DJ sectors from
  Investing.com). Long-run coefficients of the log index level on CPI inflation $I$ and inflation uncertainty
  $U$: consumer services $I=-0.098$, $U=-0.394$; financials $I=-0.067$, $U=-0.265$; basic materials
  $I=-0.013$ (n.s.), $U=-0.383$; industrials $U=-0.071$; all 1% significant unless noted (arXiv:1603.01231).
- **The structural break kills the long-run effect.** Breaks are dated 2008M7–2010M2; the dummy interactions
  roughly cancel the pre-break coefficients (consumer goods $U=-0.235$, $\text{Dum}\times U=+0.234$; basic
  materials $U=-0.383$, $\text{Dum}\times U=+0.307$), and a Wald test cannot reject that inflation and its
  uncertainty have no long-run effect after the crisis (arXiv:1603.01231).
- **In the short run only uncertainty matters.** Error-correction terms are negative and significant in all
  8 cointegrated indexes (−0.059 to −0.297); $\Delta U$ coefficients are −0.072 to −0.230 (all significant)
  while $\Delta I$ is insignificant for every index except consumer services and telecom; ECM $R^2$
  0.106–0.259. Two sectors — health care (DJUSHC) and energy (DJUSEN) — show *no* cointegration and no
  short-run relation (arXiv:1603.01231).
- **Inflation uncertainty is measured as the stochastic-volatility inflation gap, not as a GARCH variance.**
  Stock–Watson (2007) UC-SV model: $\pi_t=\tau_t+\eta_t$, $\tau_t=\tau_{t-1}+\varepsilon_t$, with
  $\ln\sigma^2_{\eta,t}$ and $\ln\sigma^2_{\varepsilon,t}$ as random walks and smoothness $\gamma=0.04$
  (arXiv:1603.01231).
- **Bitcoin returns split into two volatility regimes and monetary-policy uncertainty (MPU) is negative in
  both.** MSM(2)-VAR(1) on monthly BTC (CoinDesk) and the Baker–Bloom–Davis MPU index, 2010M7–2023M8
  (158 obs, 157 returns): regime 1 $\sigma=0.242$ (low volatility), regime 2 $\sigma=0.513$ (high); the MPU
  coefficient on the BTC return is −0.028 (regime 1) and −0.44 (regime 2), with $P_{11}=0.895$,
  $P_{22}=0.97$ ($P_{21}=0.03$). The regime-specific MPU coefficients are *not* individually significant
  (p = 0.492, 0.143) and BTC and MPU are *not* cointegrated (Johansen trace 11.98 < 17.95 critical at 5%)
  (arXiv:2311.10739).
- **An FOMC rate change moves Bitcoin with a one-lag response of roughly −2 per 1 pp.** Hourly BTC
  (Jan 2017–Aug 2023) around 55 FOMC meetings (18 hikes, 5 cuts, 32 holds):
  $\widehat{BTC\_ret}_t = 0.0506 - 1.968\,FOMC_{t-1} + 0.189\,BTC\_ret_{t-1}$, the FOMC coefficient
  negative and significant; impulse responses are negative for two periods (arXiv:2311.10739).
- **QE transmission channels get an econophysics framing and no calibrated threshold.** arXiv:1305.5656
  proposes that capital flows in QE transmission and transaction-network channels are characterised by a
  Reynolds number, that laminar→turbulent transitions proceed through a Landau–Hopf bifurcation cascade into
  "nonlinear dynamic chaos", and that QE can stabilise *or* destabilise depending on the liquidity level. No
  fitted Reynolds threshold is reported and the NDSGET+hydrodynamics simulation is not reproducible (no
  parameter values). Its usable content is the channel taxonomy plus the *cited* macro effect sizes:
  100 bp gilt-yield shock → peak GDP +0.75–2.5% and CPI +0.75–1.25%; household net financial wealth +16%;
  liquidity effects on 10Y UST of −46 to −85 bp per +2.5 pp-of-GDP reserve expansion (arXiv:1305.5656).
- **Two papers are a single theoretical line on interest rates and inflation, with no data.** arXiv:1104.2344
  derives $d(\ln y)/dt = I(t-t_0)$ with $y=i_L-i_S$ from a two-component manufacturer/banker model (delay
  $t_0\approx$ 6–12 months) and shows constant inflation forces an exponential spread $i_L-i_S=i_0e^{It}$
  (1970s US inflation ≈13.5%, then ≈3%). arXiv:1603.08311 keeps the proportionality, eliminates $I$ with
  Fisher's relation $I=i^{(n)}-i^{(a)}$, and obtains the delay-logistic (Hutchinson) equation
  $dx/dt=(A-w)x(t)-x(t)x(t-t_0)$ with oscillation onset at $(i_L^{(n)}-i_S^{(a)})t_0>1/e$ and sustained
  oscillations above $\approx1.5706$ (Wright's constant, $=\pi/2$). Neither estimates its parameters.
  **Explicit comparison:** arXiv:1104.2344 supplies the inflation↔spread identity; arXiv:1603.08311 converts
  it into a dynamical stability criterion for the real long rate under a zero short rate ($i_S^{(a)}=0$) and
  generalises to a non-zero constant short rate. They are the same model at two stages and must not be
  double-counted as independent corroboration.
- **Off-topic / weak-fit note.** None of the six is wholly off-topic. arXiv:1305.5656 is the weakest fit: a
  narrative econophysics review whose only original quantitative claim (Reynolds-number turbulence) is
  uncalibrated; it is retained solely for the transmission-channel taxonomy and the effect-size priors it
  quotes. arXiv:1104.2344 and arXiv:1603.08311 are pure derivations with illustrative, not fitted, numbers.
  The three data-based papers (arXiv:1303.6192, arXiv:1603.01231, arXiv:2311.10739) carry all the estimable
  content.

## Methods & Formulas

### 2.1 Bivariate AR(p)–EGARCH(1,1) uncertainty and Granger direction

**Purpose.** Produce monthly inflation-uncertainty and output-growth-uncertainty series from CPI and
industrial production alone, then test the *direction* of the inflation↔uncertainty link before using either
as a feature.

**Formula.** Let $e_t=(e_{pt},e_{yt})'$ be the residuals of a bivariate VAR(p):
$$p_t = a_0 + \sum_{i=1}^{p} a_i p_{t-i} + \sum_{i=1}^{p} r_i y_{t-i} + \eta\, i_{t-1} + \tau\,\text{Oil}_{t-1} + e_{pt},$$
$$y_t = b_0 + \sum_{i=1}^{p} b_i y_{t-i} + \sum_{i=1}^{p} d_i p_{t-i} + \lambda\, y^{EU}_{t-1} + e_{yt}.$$
Uncertainty is the conditional log-variance from EGARCH(1,1):
$$\ln h_{pt} = \alpha_0 + \alpha\ln h_{p,t-1} + \beta\frac{e_{t-1}}{\sqrt{h_{t-1}}} + \gamma\!\left(\frac{|e_{t-1}|}{\sqrt{h_{t-1}}}-\sqrt{2/\pi}\right),$$
and analogously for $\ln h_{yt}$; $\gamma>0$ is the Friedman–Ball asymmetry (positive inflation shocks raise
uncertainty more than negative ones).

**Required inputs.** Monthly CPI level; monthly industrial-production index; a policy rate (ECB rate for
currency boards, own rate for inflation targeters); a crude-oil price series; an EU industrial-production
index. All monthly.

**Parameters & defaults.** AR(12) for the residual pre-tests (AIC/SIC minimum), EGARCH(1,1) for the variance;
$p_t=\ln(CPI_t/CPI_{t-1})\times1200$ and $y_t=\ln(IPI_t/IPI_{t-1})\times1200$ (annualised monthly
log-differences); first differences (levels are I(1)); Granger tests at 4/8/12 lags with the optimal lag from
AIC/SIC.

**Observed effect sizes.** $\gamma$: Bulgaria 0.615 (1%), Czech 0.523 (1%), Romania 0.116 (5%), Estonia
−0.17 (n.s.), Poland −0.081 (n.s.); inflation eq. $R^2$ 0.11–0.39, growth eq. 0.08–0.73; inflation →
inflation-uncertainty Granger F up to 29.41 (Bulgaria, 4 lags) and 43.62 (Estonia, 4 lags, negative sum).

**Failure modes.** Jarque–Bera rejects normality for almost every series (inflation JB up to 53.13, growth up
to 83.08), so asymptotic Granger inference is fragile at ~139 observations; squared-residual ARCH is *absent*
for Estonian and Lithuanian inflation, so EGARCH is unidentified there; the sign of $\gamma$ flips with
regime credibility, so a pooled panel is misspecified; growth-equation diagnostics are poor for Estonia
($R^2=0.08$, F = 0.87). The GARCH/EGARCH volatility machinery itself is derived in
[`../qfin-st/volatility-modeling.md`](../qfin-st/volatility-modeling.md).

### 2.2 Gregory–Hansen cointegration with one break + UC-SV uncertainty + ECM

**Purpose.** Test and estimate the long-run relation between a price level (equity index, FX, commodity) and
inflation and inflation uncertainty when that relation may shift once, then separate it from short-run
dynamics.

**Formula.** Inflation uncertainty (UC-SV): $\pi_t=\tau_t+\eta_t$ with $\eta_t=\sigma_{\eta,t}\zeta_{\eta,t}$,
$\tau_t=\tau_{t-1}+\varepsilon_t$ with $\varepsilon_t=\sigma_{\varepsilon,t}\zeta_{\varepsilon,t}$,
$\ln\sigma^2_{\eta,t}=\ln\sigma^2_{\eta,t-1}+\nu_{\eta,t}$,
$\ln\sigma^2_{\varepsilon,t}=\ln\sigma^2_{\varepsilon,t-1}+\nu_{\varepsilon,t}$, smoothness $\gamma=0.04$.
The level equation $DJ=c+\alpha_1 I+\alpha_2 U+\varepsilon_t$ becomes, under a one-time regime shift at
fraction $\tau$, the GH-RST model
$$DJ=c_1+c_2\varphi_{t\tau}+\beta_1 t+\beta_1 t\varphi_{t\tau}+\alpha_1 I+\alpha_2 I\varphi_{t\tau}+\alpha_3 U+\alpha_4 U\varphi_{t\tau}+\varepsilon_t,
\qquad \varphi_{t\tau}=\mathbf 1\{t>n\tau\},$$
with $Z_\alpha=n(\rho^*-1)$, $Z_t=(\rho^*-1)/s_\tau$ and $ADF_\tau=t\text{-stat}(\varepsilon_{t-1,\tau})$,
the break chosen to minimise the statistic. Short run: ECM with the lagged residual $\widehat{ECM}_{t-1}$.

**Required inputs.** Monthly log price level of the target asset; monthly CPI inflation; and, for the
robustness variant, monthly industrial-production growth.

**Parameters & defaults.** Break timing unknown and scanned over all candidate dates; a long-run relation is
declared when 2 of 3 statistics (ADF, $Z_t$, $Z_\alpha$) reject at 10%; four models (GH-LS, GH-LST, GH-RS,
GH-RST) — GH-LST retained for 4 indexes and GH-RST for 3; Engle–Granger OLS for coefficients; ECM with the
retained model's residuals; VAR(2) in differences where cointegration is absent; CUSUM/CUSUM-squares for
stability.

**Observed effect sizes.** 8/10 sectors cointegrated; long-run $U$ coefficients −0.071 to −0.394; break dates
2008M7–2010M2; ECM terms −0.059 to −0.297 (all significant), $\Delta U$ −0.072 to −0.230, ECM $R^2$
0.106–0.259; adding IP leaves the picture unchanged and gives a positive output coefficient.

**Failure modes.** Only 1 of 4 GH models rejects for 5 of the 8 "cointegrated" indexes, so the long-run claim
is model-dependent; the break date is ambiguous across statistics (ADF and $Z_t$ often differ by months); the
post-break effect is statistically zero, so pre-break coefficients must not be carried forward; the UC-SV
uncertainty series uses full-sample (smoothed) stochastic volatility and therefore leaks future information
into any rule built on it; DJUSHC/DJUSEN show no relation, so a composite-index result must not be assumed
sector by sector. Cointegration/ECM and forecast-evaluation machinery is derived in
[`../qfin-st/econometrics-forecasting.md`](../qfin-st/econometrics-forecasting.md).

### 2.3 Markov-switching means VAR for macro-uncertainty sensitivity

**Purpose.** Let an asset's sensitivity to a macro-uncertainty index differ across volatility regimes,
instead of fitting a single linear slope.

**Formula.** MSM(r)-VAR(q):
$$x_t=\alpha_{s_t}+\sum_{i=1}^{q}\beta_{i,s_t}x_{t-i}+\sigma_{s_t}^{1/2}u_t,\qquad u_t\mid s_t\sim NID(0,I_k),$$
$$P(S_t=i\mid S_{t-1}=j)=p_{ji},\qquad \sum_j p_{ji}=1,$$
with $x_t=(R^{BTC}_t,R^{MPU}_t)'$. MSM lets the intercept/mean switch while lag coefficients are common;
use the **filtered** probabilities $P(S_t=i\mid X_t)$, not the smoothed ones.

**Required inputs.** A monthly asset return (log) and a monthly macro-uncertainty index; for the event
extension, an hourly asset return and the central-bank policy-rate change with announcement timestamps.

**Parameters & defaults.** $r=2$ regimes, $q=1$ (AIC minimum; a VAR lag-order search selects lag 1); Johansen
cointegration pretest first; MSM-VAR by EM/Kim filter; event study as a VAR on hourly returns with the lagged
policy change.

**Observed effect sizes.** Return $\sigma$: 0.242 (regime 1) vs 0.513 (regime 2); MPU→BTC −0.028 / −0.44;
$P_{11}=0.895$, $P_{22}=0.97$; with the MPU effect, $P_{11}=0.717$, $P_{21}=0.083$; FOMC coefficient −1.968
(1 pp → ≈ −1.97% next-hour BTC return).

**Failure modes.** The regime-specific MPU coefficients are individually insignificant (p 0.49 / 0.14) — the
two-regime structure is supported by the volatility split, not by the slope; BTC and MPU are not cointegrated,
so the VAR must be run in returns, not levels (avoid spurious regression); 158 monthly / 55 event observations
leave very little power; filtered and smoothed probabilities give very different regime dates, and using
smoothed probabilities in a backtest is look-ahead; the regime labels (bull/bear) are inferred, not exogenous.
Markov-switching state inference is derived in
[`../qfin-st/regime-switching.md`](../qfin-st/regime-switching.md); crypto asset behaviour in
[`../qfin-st/crypto-assets.md`](../qfin-st/crypto-assets.md).

### 2.4 Delay-logistic interest-rate/inflation stability criterion

**Purpose.** A monitoring inequality: decide whether the observed long/short rate spread and the policy
transmission delay put the inflation process into a damped or a sustained-oscillation regime.

**Formula.** Principle of Proportionality (arXiv:1104.2344): $\dfrac{d(\ln y)}{dt}=I(t-t_0)$, $y=i_L-i_S$,
and for constant $I$ the spread grows as $i_L-i_S=i_0e^{It}$. Eliminating $I$ with Fisher,
$I=i^{(n)}-i^{(a)}$ (arXiv:1603.08311), and setting $x=i_L^{(a)}-i_S^{(a)}$, $A=i_L^{(n)}$, $w=i_S^{(a)}$:
$$\frac{dx(t)}{dt}=(A-w)\,x(t)-x(t)\,x(t-t_0).$$
The behaviour depends only on $a'=(A-w)t_0$: asymptotic (no oscillation) for $0<a'\le 1/e$; damped
oscillation for $1/e<a'\le 1.5706$; sustained oscillation for $a'>1.5706$. The stability prescription is
$$(i_L^{(n)}-i_S^{(a)})\,t_0\le \frac{1}{e}.$$

**Required inputs.** Long-term nominal interest rate $i_L^{(n)}$; short-term actual rate $i_S^{(a)}$; a
transmission delay $t_0$ in the same time unit (months).

**Parameters & defaults.** $t_0$ default 6–12 months (arXiv:1104.2344); worked examples $A=0.08$ (8%/yr) and
$A=0.12$ with $w=0.01/0.02$; canonical transformation $t'=t\,t_0$, $A=a/t_0$, delay set to 1.

**Observed effect sizes.** For $i_L^{(n)}=0.08$: damped oscillations for $1.05<t_0<44.8$ months; for
$i_L^{(n)}=0.12$: sustained oscillations for $t_0>13.09$ months; a non-zero $w$ raises inflation and, in the
tested cases, restores stability ($A=0.12$, $w=0.02$: stable after $t>1113$ months). The simulation matched
an exact solution to 3 significant figures.

**Failure modes.** No parameter is estimated from data — $t_0$ is an assumed input and the illustrative rates
are not fitted; the Hopf threshold is an asymptotic result and the $\pi/2$ bound is a conjecture (best
numerical estimate 1.5706); the model has two agents and no money/credit detail, so it is a stability
heuristic, not a forecast; the $1/e$ rule is a guide, not a validated policy rule.

### 2.5 QE transmission-channel taxonomy and effect-size priors

**Purpose.** Structure a QE/liquidity event study around a transmission ladder and borrow published effect
sizes as priors, because the corpus paper itself supplies no calibrated estimator.

**Formula.** Reynolds number for a channel of characteristic dimension $d$ and capital-flow velocity
$\upsilon$ with kinematic viscosity $\nu$:
$$Re=\frac{\upsilon d}{\nu};$$
laminar→turbulent transition at a critical $Re$, then a Landau–Hopf bifurcation cascade to "nonlinear dynamic
chaos". The transmission ladder (compiled from the paper's sources) is: asset purchases → long-yield fall →
broader asset-price rise → household net wealth → demand → GDP and CPI.

**Required inputs.** Central-bank balance sheet/reserves; 10Y (and corporate) yields; equity index; GDP; CPI —
monthly/quarterly around QE announcements.

**Parameters & defaults.** No calibrated $Re$ threshold is given; use the cited elasticities as priors rather
than estimates.

**Observed effect sizes** (as reported/compiled in arXiv:1305.5656). 100 bp gilt-yield shock → peak GDP
+0.75–2.5% and CPI +0.75–1.25% (SVAR ≈ +1.5% / +0.75 pp; multi-model ≈ +1.5% / +1.25 pp; monetary ≈ +2% /
+1%); household net financial wealth +16%; liquidity effects on 10Y UST of −46 to −85 bp per +2.5 pp-of-GDP
reserve expansion; QE1 $600bn MBS (2008–10), QE2 $600bn Treasuries (2010–11), QE3 $40bn MBS/month (from Sep
2012); Fed assets $915bn → $2,316bn (end-2007 → end-2008); BoE £375bn by 2011–12; BoJ ¥55tn.

**Failure modes.** The paper's own contribution (Reynolds-number turbulence, NDSGET simulation) reports no
fitted parameters and cannot be reproduced; the effect sizes are second-hand and heterogeneous across
methods; "nonlinear dynamic chaos" and "laminar–turbulent transition" are analogies, not testable statements;
the claim that QE may stabilise or destabilise depending on liquidity level is unfalsifiable without a
threshold. News-based uncertainty construction overlaps
[`../qfin-st/news-sentiment-nlp.md`](../qfin-st/news-sentiment-nlp.md).

## Data Requirements

Provider rows below are real entries in `strategies/endpoints.json`; **gap** means no current provider can
supply the input.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| US CPI inflation, industrial production, money supply, Fed balance sheet, WTI oil (monthly/quarterly) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Long-term government yield curve (daily 10Y etc.) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Policy rate target (fed funds / FOMC target range) | `moomoo://get_fed_watch_target_rate` | `fed_watch` | moomoo | gateway (not live-probed) |
| FOMC / macro announcement dates and times | `moomoo://get_economic_calendar` | `economic_calendar` | moomoo | gateway (not live-probed) |
| Non-US macro indicator lists (Eastern Europe CPI/IP) | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| DJ sector / equity index prices (monthly log levels) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Equity index prices (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Equity index prices (tertiary) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Equity/index OHLCV (fourth source) | `https://api.stockdata.org/v1/data/eod` | `core_stock_apis` | stockdata | ok |
| News text for a news-based uncertainty index | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| News sentiment (uncertainty proxy) | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | ok |
| News sentiment (alternative) | `https://www.alphavantage.co/query` | `news_sentiment` | alpha_vantage | ok |
| Global news doc stream (uncertainty text) | `https://api.gdeltproject.org/api/v2/doc/doc` | `news_sentiment` | gdelt | rate_limited (HTTP 429) |
| Macro/policy prediction-market contracts | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | ok |
| **Bitcoin spot price (monthly and hourly)** | — | — | — | **gap** |
| **Monetary Policy Uncertainty index (Baker–Bloom–Davis)** | — | — | — | **gap** |

**What the gaps cost, quantified.** The crypto paper needed 158 monthly BTC observations (2010M7–2023M8) for
the regime model and 55 hourly FOMC windows (2017–2023) for the event study; with no crypto provider in the
catalog, §2.3 can only be exercised on equities and the MPU→BTC regime result is untestable as published. The
MPU index is a text-derived monthly series (Baker–Bloom–Davis, four keyword criteria over US newspapers); it
is not a FRED series, so the `fred` row cannot substitute, and without it §2.3 loses its regressor entirely —
rebuilding it needs a news archive (the `eodhd`/`benzinga` news rows) plus the keyword filter, i.e. a
separate text-processing project, not a data pull. Everything else in §2 maps to a real row: the three
uncertainty/cointegration techniques need only `fred` (CPI, IP, oil, money, balance sheet) plus an equity
price row, and the delay-logistic monitor needs only the Treasury curve row and the `fed_watch` gateway.

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Look-ahead via smoothed state/uncertainty estimates.** The MSM-VAR regime probabilities must be
  *filtered*; the UC-SV inflation-uncertainty series is estimated with full-sample stochastic volatility
  (arXiv:1603.01231) and the GH break point is chosen on the full sample — both leak future information into
  any historical rule. Re-estimate recursively for backtests.
- **Model-dependent cointegration claims and multiple testing.** 8 of 10 sector indexes are called
  cointegrated, but for 5 of them only 1 of 4 GH models rejects; declare a relation only when 2 of 3
  statistics agree, and treat the 10-index family as a multiple-testing problem (arXiv:1603.01231).
- **Regime dependence and sign flips.** The EGARCH asymmetry flips sign between credible and non-credible
  regimes (Estonia/Poland vs Bulgaria/Czech) (arXiv:1303.6192); the stock–inflation effect vanishes after the
  2008–2010 break (arXiv:1603.01231). Any fixed coefficient is a regime average, not an invariant.
- **Metric choice: long-run vs short-run, level vs uncertainty.** In the long run both inflation and its
  uncertainty matter; in the short run only uncertainty does (inflation is insignificant for 8/10 indexes)
  (arXiv:1603.01231). Do not use the long-run coefficient as a short-horizon signal.
- **Null and diagnostic tests before inference.** Unit-root tests (ADF/PP/KPSS) and a Johansen pretest are
  mandatory before any levels VAR (arXiv:2311.10739); the EGARCH papers must first show autocorrelation-free
  residuals with present ARCH, and they fail normality (JB up to 83.08) (arXiv:1303.6192).
- **Statistical vs economic significance.** The regime MPU coefficients are individually insignificant
  (p 0.49/0.14) even though the two-regime volatility split is strong (arXiv:2311.10739); report the
  volatility split and the slope separately.
- **Sample length and structural breaks.** Samples are short and break-ridden: ~139 monthly obs
  (arXiv:1303.6192), ~160 (arXiv:1603.01231), 158 and 55 (arXiv:2311.10739); the two regime papers are a
  single model line and are not two independent samples.
- **Cost assumptions are absent everywhere.** None of the six papers includes transaction costs, slippage or
  implementation lag; the cointegration relation is a long-horizon level relation and is not by itself a
  tradable signal. Backtest discipline is in
  [`../qfin-st/backtest-methodology.md`](../qfin-st/backtest-methodology.md).
- **Unreproducible simulations must not be treated as results.** arXiv:1305.5656 reports no simulation
  parameters; its effect sizes are second-hand from other studies. arXiv:1104.2344 and arXiv:1603.08311 give
  illustrative (not fitted) rate values, and their Hopf threshold is asymptotic.
- **Unit hygiene.** Inflation and growth are annualised monthly log-differences ($\times1200$); mixing
  monthly and annual rates, or levels and returns, silently changes every coefficient.

## Recommended Workflow

Ranked by value per effort against what the data layer can fetch today.

1. **FRED macro puller + UC-SV inflation-uncertainty estimator.** *What:* pull CPI, industrial production,
   oil and money series; estimate the Stock–Watson UC-SV inflation gap ($\gamma=0.04$) as the uncertainty
   feature. *Data:* `fred` `macro_data` row. *Passing:* the uncertainty series is reproduced and the
   GH-LST/GH-RST cointegration on the eight DJ sectors flags 8/10 cointegrated with break dates inside
   2008M7–2010M2. *Effort:* S.
2. **Gregory–Hansen cointegration + ECM module for price-level relations.** *What:* the four-model GH test
   with endogenous break, 2-of-3 acceptance rule, then ECM. *Data:* equity/index price row (`eodhd`, with
   `tiingo`/`massive` fallback) + `fred` CPI. *Passing:* ECM error-correction terms negative and significant
   (−0.059 to −0.297 range), CUSUM-stable, and the post-break null reproduced. *Effort:* M.
3. **Bivariate EGARCH uncertainty + Granger panel.** *What:* §2.1 on a small country panel (monthly CPI/IP).
   *Data:* `fred` plus `moomoo` `get_macro_indicator_list` for non-US series. *Passing:* positive
   inflation→inflation-uncertainty Granger in ≥3 countries and the $\gamma$ sign split reproduced.
   *Effort:* M.
4. **Markov-switching means VAR wrapper (equity proxy first).** *What:* MSM(2)-VAR(1) with filtered
   probabilities, applied to an equity return vs an uncertainty proxy until a crypto feed exists. *Data:*
   `fred` + equity row. *Passing:* two regimes with a volatility ratio near 2 and a negative
   uncertainty→return coefficient. *Effort:* M.
5. **Delay-logistic stability monitor.** *What:* compute $a'=(i_L^{(n)}-i_S^{(a)})t_0$ and compare to $1/e$
   and 1.5706; flag damped vs sustained oscillation. *Data:* `federal_reserve` `risk_free_curve` (long rate)
   + `moomoo` `get_fed_watch_target_rate` (short rate). *Passing:* the monitor emits a regime label per
   month and is stable under $t_0\in[6,12]$ months. *Effort:* S.
6. **QE event-study template with the yield→wealth→GDP ladder.** *What:* impulse responses around QE
   announcements, benchmarked to the +0.75–2.5% GDP / +0.75–1.25% CPI priors. *Data:* `fred` + Treasury
   curve row. *Passing:* a 100 bp yield shock maps inside the published band. *Effort:* M.
7. **Close the two data gaps (crypto price, MPU index).** *What:* register a crypto price source and build
   or licence the Baker–Bloom–Davis MPU series (news rows + keyword filter). *Data:* new provider rows;
   `eodhd`/`benzinga` news for reconstruction. *Passing:* BTC monthly 2010–2023 and an MPU series load, and
   the §2.3 regime result is reproducible. *Effort:* L.
8. **Sector inflation-hedge screen.** *What:* rank DJ sectors by the long-run $|U|$ coefficient and exclude
   health care and energy (no cointegration). *Data:* `eodhd` sector prices + `fred` CPI. *Passing:* the
   ranking is stable across the pre-break subsample. *Effort:* S.

## Output Format

### Policy-Shock Event Window
| Event | Shock (bp / pp) | Window | Target asset | Response | IRF sign (periods) | Significant |
|---|---|---|---|---|---|---|
| FOMC date | ... | t-1 / t / t+k | ... | ... | ... | Yes / No |

### Transmission & Uncertainty Validation
| Step | Method | Estimate | Break date / regime | Acceptance rule | Verdict |
|---|---|---|---|---|---|
| Inflation uncertainty | UC-SV gap (gamma=0.04) | ... | — | series reproduced | Pass / Fail |
| Price-level relation | Gregory–Hansen (4 models) | long-run I, U | 2008M7–2010M2 | 2 of 3 stats | Cointegrated / Not |
| Short-run | ECM term | ... | — | negative & significant | Pass / Fail |
| Regime sensitivity | MSM(2)-VAR(1) filtered | slope per regime | vol split | filtered probabilities | Reported |

### Stability Monitor & Verdict
Compute a' = (i_L^(n) - i_S^(a)) * t0 and compare to 1/e and 1.5706.
| Long rate | Short rate | t0 (months) | a' | Regime | vs 1/e |
|---|---|---|---|---|---|
| ... | ... | 6–12 | ... | Damped / Sustained | Above / Below |

State the transmission lag and the arm it lands on, the sign and significance of the
policy-shock coefficient, whether the long-run relation survives the dated break, and
the main failure mode (look-ahead in smoothed estimates, sign-flipping regime
dependence, or missing crypto/MPU data).

## References

| arXiv id | Title | Year |
|---|---|---|
| 1303.6192v1 | Inflation Uncertainty, Output Growth Uncertainty and Macroeconomic Performance: Comparing Alternative Exchange Rate Regimes in Eastern Europe | 2013 |
| 1305.5656v2 | To the problem of turbulence in quantitative easing transmission channels and transactions network channels at quantitative easing policy implementation by central banks | 2013 |
| 1603.08311v1 | Interest Rates and Inflation | 2016 |
| 1603.01231v1 | Stock prices, inflation and inflation uncertainty in the U.S.: Testing the long-run relationship considering Dow Jones sector indexes | 2016 |
| 1104.2344v1 | Interest Rates and Inflation | 2011 |
| 2311.10739v1 | Examining the Effect of Monetary Policy and Monetary Policy Uncertainty on Cryptocurrencies Market | 2023 |
