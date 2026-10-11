---
id: equilibrium-and-corporate-valuation
name: Equilibrium Valuation and Discount Rates
version: 1.0.0
author: finrobot
domain: equity-research
description: 'Cost-of-equity and discount-rate estimation for valuation: CAPM betas with causal aggregator diagnostics, stochastic dividend-discount valuation duration and implied cost of capital. Use when setting or challenging a discount rate, reading valuation duration, or testing whether a beta is causal.'
triggers:
- cost of equity
- capm beta
- discount rate
- cost of capital
- valuation duration
- implied cost of capital
- beta
- dividend discount
- stochastic ddm
- momentum
- valuation
- aggregator contradiction
requires_data:
- input: Equity / index / sector-ETF OHLCV (returns, volume, VWAP)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Equity OHLCV alt (returns, betas)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Market / ETF quote bars alt
  provider: fmp
  category: core_stock_apis
  status: ok
- input: Interval bars (candidate for ETF/index series)
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Local-gateway snapshots / klines
  provider: moomoo
  category: core_stock_apis
  status: gateway
- input: Per-share dividend history (DDM states, duration)
  provider: eodhd
  category: corporate_actions
  status: ok
- input: Dividend calendar alt
  provider: benzinga
  category: corporate_actions
  status: ok
- input: Treasury yield / zero curve ($R_f$, discount rates)
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: 'Macro state: consumption (PCE), CPI, population, credit spread'
  provider: fred
  category: macro_data
  status: ok
- input: Macro indicators alt
  provider: moomoo
  category: macro_data
  status: gateway
- input: Option surface / model-free implied vol (risk-premium state)
  provider: cboe
  category: options_surface
  status: ok
- input: Earnings, book value, market cap (valuation inputs)
  provider: fmp
  category: fundamental_data
  status: ok
- input: Fundamentals alt (valuation inputs)
  provider: alpha_vantage
  category: fundamental_data
  status: ok
- input: Corporate filings (dividends, capital structure)
  provider: sec_edgar
  category: sec_filings
  status: ok
- input: News / sentiment (belief and attention proxies)
  provider: eodhd
  category: news_data
  status: ok
- input: Analyst consensus / research ratings (cash-flow expectations)
  provider: moomoo
  category: analyst_ratings
  status: gateway
- input: Short interest / institutional holdings (belief & friction proxies)
  provider: moomoo
  category: short_interest
  status: gateway
- input: Economic calendar (CPI release / shock days)
  provider: moomoo
  category: economic_calendar
  status: gateway
- input: VIX index level series (driver $Z$)
  provider: ''
  category: ''
  status: gap
- input: Index futures prices (dividend-strip construction)
  provider: ''
  category: ''
  status: gap
- input: S&P 500 dividend strip / dividend futures prices
  provider: ''
  category: ''
  status: gap
- input: FX / DXY log return (driver $Z$)
  provider: ''
  category: ''
  status: gap
- input: Intraday quote / order-book data (microstructure, sub-daily timing)
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Equilibrium Valuation and Discount Rates

You are an expert equity-valuation researcher specializing in discount-rate and cost-of-capital estimation. You consume equity, index and sector-ETF OHLCV, per-share dividend histories, treasury zero curves, FRED macro series and consumption data from the available endpoints, and turn them into environment-conditional CAPM betas with causal diagnostics, stochastic-DDM expected values, variances and cross-covariances with an existence check, valuation-duration state variables, and belief-driven momentum/reversal measures — never fabricating betas, discount rates, dividend-growth states or regression R-squared that were not actually estimated.

> Source: FinRobot strategies corpus review — `strategies/qfin-pr/equilibrium-and-corporate-valuation.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **Dividend-discount valuation collapses to a two-state-variable model, and the slope of the valuation term structure — not its level — is the return predictor.** Li & Wang define *valuation duration* as $dr_t \equiv \ln(P_t/P_{t1})$, the log ratio of total market capitalisation to the price of the next-year dividend strip, and show that the equity state space is two-dimensional: the first two principal components of $\{dr,\,pd,\,s^{0.5},\,s^{1},\,s^{1+}\}$ explain 96.3% of total variance, and $\{dr,\,pd\}$ span it (arXiv:2310.07110v1).
- **$dr$ forecasts annual market returns on its own while the price-dividend ratio does not.** In-sample $R^2 = 25\%$ and out-of-sample $R^2 = 15\%$ for annual S&P 500 returns; the OOS $R^2$ from $pd$ is "almost zero". A market-timing strategy that reduces exposure when duration rises delivers Sharpe 0.58, a 55% improvement over buy-and-hold (arXiv:2310.07110v1).
- **Duration is discount-rate-driven because cash-flow expectations lack persistence.** The necessary and sufficient condition for the conditional expected return to be a univariate function of $dr$ is that the market holds no information about cash-flow growth beyond the next year — i.e. a zero AR(1) coefficient of expected dividend growth. Empirically, the near-year earnings-growth forecast has $R^2 = 73\%$, but only 8% for growth from year 1 to 2 and 7% for year 2 to 3 (arXiv:2310.07110v1).
- **Stochastic dividend discount models (SDDM) admit closed-form mean, variance and covariance.** With a finite-state random growth rate $\tilde g$ (mean $\bar g$, variance $\mathrm{Var}[\tilde g]$) the expected price is $\bar P_0 = d_0(1+\bar g)/(k-\bar g)$; its variance is monotone in $\mathrm{Var}[\tilde g]$ and finite iff $\mathrm{Var}[\tilde g] < (1+k)^2-(1+\bar g)^2$; the cross-stock covariance is monotone in $\mathrm{Cov}[\tilde g_A,\tilde g_B]$ and is zero exactly when growth rates are uncorrelated (arXiv:1609.03029v2).
- **That covariance formula feeds directly into mean-variance portfolio choice.** Applied to E.ON and Saint-Gobain (dividends 1989–2016, Eurostoxx 50, CAPM discount rates $k_A=6.631\%$, $k_B=7.943\%$, weekly-return betas $\beta_A=0.9571$, $\beta_B=1.1621$): $\bar P_{A0}=11.01$, $\bar P_{B0}=22.65$, $\mathrm{Var}[\tilde P_{A0}]=44.60$, $\mathrm{Var}[\tilde P_{B0}]=79.86$, and $\mathrm{Cov}[\tilde P_{A0},\tilde P_{B0}]=1.11872$ (geometric-mean growth states) or $0.93951$ (median states); the minimum-variance portfolio is $[29.85\%,70.15\%]$ (arXiv:1609.03029v2).
- **Consumption-based pricing hides price and payoff autocorrelations in its averaging convention.** Re-averaging the investor's utility over the *same* interval $\Delta$ at date $t$ and at date $T$ replaces $p=\beta E[mx]$ by $E[u'(c_t)p]=\beta E[u'(c_T)x]$; the linear Taylor approximation then makes the mean price depend on price volatility $\sigma_p^2(t)$, payoff volatility $\sigma_x^2(T)$, and — for a second purchase — on the price autocorrelation $\mathrm{corr}\{p(t_1)p(t_2)\}$ (arXiv:2204.07506v2).
- **Heterogeneous beliefs about a noisy signal generate momentum and reversal endogenously.** In a four-period model where informed agents *overestimate* supply variance, the signal impact satisfies $b_1<b_2$ (initial under-reaction, later over-reaction); the momentum measure $\gamma_m=(b_2-b_1)b_1\sigma_s^2-b_1^2c_1^2\sigma_\theta^2$ is positive when $\pi b_2^2\sigma_s^2(b_2-b_2^*)-b_1c_1^2>0$, and the reversal measure $\gamma_r=-b_2(b_2-b_1)\sigma_s^2-b_2^2c_2^2\sigma_\theta^2$ is always negative (arXiv:2406.08448v1).
- **Momentum strengthens with more informed traders and more belief heterogeneity; reversal strengthens with noisier supply and signal.** $\partial\gamma_m/\partial\pi>0$, $\partial\gamma_m/\partial\Delta\sigma_\theta^2>0$, $\partial\gamma_r/\partial\sigma_\theta^2>0$, $\partial\gamma_r/\partial\sigma_s^2>0$; the multi-asset extension yields cross-sectional momentum/reversal plus co-movement and lead-lag (arXiv:2406.08448v1).
- **A contemporaneous CAPM beta cannot be a causal effect on realised returns — the "aggregator contradiction".** Because $R_{m,t}=\sum_j w_{j,t-1}R_{j,t}$ is itself a value-weighted aggregate, a same-period arrow $R_{m,t}\to R_{i,t}$ forces $\beta=0$ unless the index is leave-one-out, lagged, or degenerate. The plausible baseline is a *fork* $Z\to\{R_m,R_i\}$ in which the OLS slope is an attenuated proxy ratio $\beta_{fork}=(b/a)\lambda$ with $\lambda=a^2\sigma_Z^2/(a^2\sigma_Z^2+\sigma_X^2)\in(0,1)$ (arXiv:2509.05760v3).
- **Beta-neutral hedging does not remove the common driver.** In the fork the post-hedge residual still loads on $Z$ with coefficient $b-a\beta_{fork}=b\sigma_X^2/(a^2\sigma_Z^2+\sigma_X^2)$. Empirically, on CPI-release days adding $\{\Delta VIX,\Delta DGS10,DXY,\text{sector ETF}\}$ collapses the pooled market slope from $\approx 0.9$ to $\approx 0.03$, betas vary systematically by volatility/rate/FX regime, and beta-hedged residuals still load on $\Delta VIX$ and sector returns (arXiv:2509.05760v3).
- **Bubbles are a summability property of dividends relative to resources, and they are logically distinct from Pareto optimality.** With $F_t=\sum_{s\ge1}D_{t+s}/(R_{t+1}\cdots R_{t+s})$ and $B_t=q_t-F_t$, a bubble exists iff $\sum_t D_t/q_t<\infty$; every equilibrium is bubbly iff dividends are summable relative to $G_n^t e_t^y$; in the stationary low-interest-rate case the maximal equilibrium is asymptotically bubbly and Pareto optimal while the bubbleless equilibrium is Pareto dominated (arXiv:2508.03230v4).
- **The three classical Tirole regimes reappear under time-varying primitives.** A bubbleless equilibrium exists when discounted dividends at the benchmark rate are finite; bubbly and bubbleless equilibria coexist when dividend growth sits below a low interest rate that is itself below population growth ($D_{t+1}/D_t<\gamma\le R^*_{t+1}<G_n$); a bubble requires a low interest rate ($R^*\le G_n$) together with low dividend growth ($G_d<G_n$) (arXiv:2508.03230v4).
- **Where this corpus is thin: real options, irreversible investment and capital structure.** The 26 highest-ranked members of the `equilibrium-and-corporate-valuation` shortlist contain **no** real-option, investment-timing or capital-structure paper. Corporate-finance content is limited to dividend-discount valuation and its merger/portfolio applications (arXiv:1609.03029v2) and to the OLG bubble welfare analysis (arXiv:2508.03230v4). FinRobot should treat real-option modules as *uncovered* by this corpus rather than as supported by it.

## Methods & Formulas

### 2.1 Valuation duration and the two-variable state space
**Purpose.** Build a real-time discount-rate state variable from the relative valuation of near- vs. long-dated dividends, and use it to forecast annual market returns and to span the equity state space.

Price-dividend ratios of dividend strips are exponential-affine in the latent state $X_t$ (arXiv:2310.07110v1 eqs. 1–11):
$$X_{t+1}=\Pi X_t+\sigma_X\epsilon_{t+1},\qquad s_{tn}\equiv\ln\!\frac{P_{tn}}{D_t}=A(n)+B(n)^\top X_t,$$
$$P_{tn}=\mathbb E_t\!\left[M_{t+1}P_{t,n+1}\right],\qquad M_{t+1}=\exp\!\left(-r_f-\tfrac12\lambda_t^\top\Sigma\lambda_t-\lambda_t^\top\epsilon_{t+1}\right),\qquad \lambda_t=\lambda+\theta^\top X_t .$$
Duration and the level are then linear combinations of the same state:
$$pd_t=\ln(P_t/D_t)=A+B^\top X_t,\qquad dr_t\equiv\ln(P_t/P_{t1})=pd_t-s_{t1}=A-A(1)+\big(B-B(1)\big)^\top X_t .$$
Strips are backed out of index futures and zero-coupon bonds, $P_{tn+}=e^{-nr_f}\mathbb E^{RN}_t[S_{t+n}]=ZCB^n_t\,F_{tn}$, and $P_{t1}=P_t-P_{t1+}$.

- **Inputs:** index level / total market cap $P_t$; realised dividends $D_t$; one-year dividend-strip price $P_{t1}$ (hence index futures $F_{t1}$ and ZCB prices); risk-free rate $r_f$.
- **Parameters:** the $(A(n),B(n))$ recursions from the affine model; two state variables; the AR(1) persistence of expected dividend growth (set to zero under the limited-information condition).
- **Observed effects:** $dr$ has mean 4.027 (≈56 years), std 0.494, monthly autocorrelation 0.919; min 2.952 (19 years, Nov 1988), max 6.632 (759 years, Nov 2000); March 2000 duration 175 years (0.57% of value from next-year dividends), March 2009 duration 46 years (>2.2%). Predictor $dr$: in-sample $R^2$ 25%, OOS $R^2$ 15%, Sharpe 0.58 for the timing rule (arXiv:2310.07110v1).
- **Failure modes:** requires strip/futures prices and a ZCB curve that FinRobot does not have (see §3); the futures curve needs interpolation to constant maturity; the return signal is negative-loading (a timing strategy, not a static factor); the whole construction assumes limited cash-flow information beyond one year.

### 2.2 Stochastic DDM: expected value, variance and covariance
**Purpose.** Closed-form mean, variance and cross-covariance of stock prices when dividend growth is a finite-state random variable; the inputs to mean-variance portfolio choice and to exchange-ratio/merger analysis.

Gordon baseline and finite-state extension (arXiv:1609.03029v2 eqs. 1–2.4):
$$P_0=\frac{d_0(1+g)}{k-g},\qquad \tilde g=\begin{cases}g_1,\dots,g_n\\ p_1,\dots,p_n\end{cases},\quad \bar P_0=\frac{d_0(1+\bar g)}{k-\bar g},$$
$$\mathrm{Var}[\tilde P_0]=\frac{\mathrm{Var}[\tilde g]\,(1+k)^2}{(1+k)^2-(1+\bar g)^2-\mathrm{Var}[\tilde g]}\times\frac{\bar P_0^2}{(1+\bar g)^2},\qquad \mathrm{Var}[\tilde g]<(1+k)^2-(1+\bar g)^2 .$$
Cross-covariance with risk-adjusted growth $G_m=\bar g_m+\mathrm{Cov}[\tilde g_m,\tilde g_l]/(1+\bar g_l)$:
$$\mathrm{Cov}[\tilde P_{A0},\tilde P_{B0}]=\frac{\mathrm{Cov}[\tilde g_A,\tilde g_B]}{(1+k_A)(1+k_B)-(1+\bar g_A)(1+\bar g_B)-\mathrm{Cov}[\tilde g_A,\tilde g_B]}\times\prod_{m=A,B}\frac{1+k_m}{1+\bar g_m}\,\bar P_{m0},$$
valid when $\big|\prod_m(1+\bar g_m)+\mathrm{Cov}[\tilde g_A,\tilde g_B]\big|<\prod_m(1+k_m)$. With A=B this recovers the variance formula.

- **Inputs:** per-share dividend history (to estimate states and probabilities); discount rate $k$ via CAPM, $k_i=R_F+\beta_i(R_M-R_F)$; return series for the beta regression.
- **Parameters:** $n$ growth states and their joint probabilities $\pi_{cd}$; $k>\bar g$; the variance-existence bound above.
- **Observed effects:** E.ON/Saint-Gobain, geometric-mean states give $\mathrm{Cov}[\tilde g_A,\tilde g_B]=0.043\%$ (corr 18.23%) and $\mathrm{Cov}[\tilde P_{A0},\tilde P_{B0}]=1.11872$; median states give 0.036% (corr 12.18%) and $0.93951$; $x_{\min}=[29.85\%,70.15\%]$ (arXiv:1609.03029v2).
- **Failure modes:** variance/divergence when $\mathrm{Var}[\tilde g]$ approaches the bound; a two-state abstraction is imposed when dividend histories are short; the discount rate is estimated on a short window (five years here); near-zero covariance can create diversification even when one asset mean-variance dominates the other.

### 2.3 Consumption-based pricing with price and payoff autocorrelation
**Purpose.** Extend the consumption-based basic pricing equation to a multi-period, multi-trade setting in which price volatility, payoff volatility and price/payoff autocorrelations enter explicitly — a diagnostic for whether an estimated mean price is consistent with the assumed averaging interval.

Modified basic equation and linear Taylor approximation (arXiv:2204.07506v2 eqs. 2.7–3.5):
$$E[u'(c_t)p]=\beta E[u'(c_T)x],$$
$$p_0(t)=\beta\frac{u'(c_{T;0})}{u'(c_{t;0})}x_0(T)+\beta\xi\frac{u''(c_{T;0})}{u'(c_{t;0})}\sigma_x^2(T)+\xi\frac{u''(c_{t;0})}{u'(c_{t;0})}\sigma_p^2(t).$$
Second purchase at $t_2$ (eq. 4.12):
$$p_0(t_2)=\beta\frac{u'(c_{T;0})}{u'(c_{t2;0})}x_{2;0}+\beta\frac{u''(c_{T;0})}{u'(c_{t2;0})}\big[\xi(t_1)+\xi(t_2)\big]\sigma_{x2}^2(T)+\frac{u''(c_{t2;0})}{u'(c_{t2;0})}\big[\xi(t_1)\mathrm{corr}\{p(t_1)p(t_2)\}+\xi(t_2)\sigma_p^2(t_2)\big],$$
with $\mathrm{corr}\{p(t_1)p(t_2)\}=E[\delta p_1\delta p_2]$ and, for $k$ purchases, dependence on all $\mathrm{corr}\{p(t_i)p(t_j)\}$.

- **Inputs:** consumption path $(e_t,e_T)$; price series $p$; payoff series $x$ (price + dividend); trade volumes (the paper's VWAP-based market average).
- **Parameters:** subjective discount factor $\beta$; the utility $u$ (its first two derivatives); the averaging interval $\Delta$; the asset amount $\xi$.
- **Observed effects:** no empirical calibration in the paper. It establishes structurally that the mean price depends on *both* price and payoff volatility (with $u''<0$ the volatilities must be small relative to $p_0$), and that using VWAP makes the price–volume correlation zero while price–volume² and price²–volume² correlations are non-zero (arXiv:2204.07506v2).
- **Failure modes:** theory-only, no parameter values; requires specifying a utility function and $\xi$ (which the author flags as a hard problem); linear Taylor truncation discards higher moments; the "averaging interval" choice is not operationally pinned down.

### 2.4 Heterogeneous-belief momentum and reversal
**Purpose.** Generate and decompose the equilibrium price autocorrelation into a momentum (belief-heterogeneity) component and a reversal (stationarity) component, for both a single asset and the cross-section.

Affine equilibrium price and autocorrelation measures (arXiv:2406.08448v1 Props. 1–5):
$$S_t=a_t+b_t(s-\bar D+c_t\theta_t),\qquad b_2=\frac{\pi\beta_\xi(\sigma_s^2+c_2^2\sigma_\theta^2)\beta_s+(1-\pi)\beta_s\sigma_s^2\beta_\xi}{\pi\beta_\xi(\sigma_s^2+c_2^2\sigma_\theta^2)+(1-\pi)\beta_s\sigma_s^2},$$
$$\gamma_m=\mathrm{Cov}(S_2-S_1,S_1-S_0)=(b_2-b_1)b_1\sigma_s^2-b_1^2c_1^2\sigma_\theta^2>0\ \text{iff}\ \pi b_2^2\sigma_s^2(b_2-b_2^*)-b_1c_1^2>0,$$
$$\gamma_r=\mathrm{Cov}(D-S_2,S_2-S_1)=-b_2(b_2-b_1)\sigma_s^2-b_2^2c_2^2\sigma_\theta^2<0 .$$
Cross-sectional (matrix) version: $\Gamma_m=(B_2-B_1)\Sigma_sB_1^\top-B_1C_1\Sigma_\theta C_1^\top B_1^\top$ (PSD ⇒ momentum) and $\Gamma_r=-(B_2-B_1)\Sigma_sB_2^\top-B_2C_2\Sigma_\theta(B_2C_2)^\top$ (always NSD).

- **Inputs:** price/return series (for the autocorrelation measures); a supply proxy (volume, short interest); a signal proxy (news/forecast surprises).
- **Parameters:** $\pi$ (proportion informed), belief heterogeneity $\Delta\sigma_\theta^2=\sigma_{\theta,1}^2-\sigma_{\theta,2}^2>0$, risk aversion $\alpha$, signal precision $\sigma_s^2$.
- **Observed effects:** comparative statics $\partial\gamma_m/\partial\pi>0$, $\partial\gamma_m/\partial\Delta\sigma_\theta^2>0$, $\partial\gamma_r/\partial\sigma_\theta^2>0$, $\partial\gamma_r/\partial\sigma_s^2>0$; momentum is larger for high-volume and high-volatility assets; reversal is unconditional in the model (arXiv:2406.08448v1).
- **Failure modes:** a four-period toy model with dogmatic agents and no calibration; the momentum condition involves too many parameters to be "precise"; the paper works with price levels rather than returns and does not make the distinction; no testable empirical bound is supplied.

### 2.5 Causal CAPM diagnostics and the aggregator contradiction
**Purpose.** Decide whether an estimated beta is a causal transmission or a proxy for a common driver, and hedge accordingly; formalise when a contemporaneous CAPM regression is even admissible.

Structural model and population slopes (arXiv:2509.05760v3 eqs. 1–12):
$$\beta_{OLS}=\frac{\mathrm{Cov}(R_m,R_i)}{\mathrm{Var}(R_m)},\qquad \beta_{causal}=E\!\left[\frac{\partial}{\partial r}R_i\,\middle|\,do(R_m=r)\right],\qquad R_{m,t}=\sum_j w_{j,t-1}R_{j,t},$$
$$\text{fork: }\beta_{fork}=\frac{b}{a}\cdot\underbrace{\frac{a^2\sigma_Z^2}{a^2\sigma_Z^2+\sigma_X^2}}_{\lambda\in(0,1)},\qquad \text{post-hedge loading } b-a\beta_{fork}=\frac{b\,\sigma_X^2}{a^2\sigma_Z^2+\sigma_X^2};\qquad \text{chain: }\beta_{chain}=c .$$
Aggregator contradiction: if $\sum_j w_{j,t-1}=1$, $w_{i,t-1}>0$, some other $w_{j,t-1}>0$, and $Y_{i,t}:=\beta X_t+Z_t$ with $Z_t$ not depending on $Y_{i,t}$, then acyclicity forces $\beta=0$ (else leave-one-out, a lagged index, or a degenerate single-asset market).

- **Inputs:** stock and market return series; driver proxies $Z$ = {$\Delta VIX$, $\Delta DGS10$, DXY return, sector ETF return}; CPI release dates for shock days.
- **Parameters:** measurement noise $\sigma_X$; lag horizon $\Delta$; rolling estimation window (the paper cites 36–60 monthly or multi-year daily conventions).
- **Observed effects:** on CPI days the pooled market slope falls from $\approx 0.9$ to $\approx 0.03$ once $Z$ proxies are added; environment-specific slopes are larger in COVID-shock, rates-down and USD-up states and smaller in hiking and USD-down states; lagged slopes ($k\ge1$) are small, sign-alternating and mostly insignificant; beta-hedged residuals still load on $\Delta VIX$ and sector (arXiv:2509.05760v3).
- **Failure modes:** the paper filters admissible graphs but does not identify the DAG from prices; $Z$ proxies are noisy; the result is a caution against causal beta reading, not a causal beta estimator; results are at daily frequency and ignore intraday microstructure arrows.

### 2.6 OLG bubble regimes and valuation monitoring
**Purpose.** Classify an asset's equilibrium as bubbleless, co-existing, or necessarily bubbly from exogenous primitives, and flag the welfare (Pareto) status separately from the bubble status.

Pricing recursion, fundamental value and bubble component (arXiv:2508.03230v4 eqs. 2–4, Lem. 2):
$$q_t=\frac{q_{t+1}+D_{t+1}}{R_{t+1}},\qquad F_t=\sum_{s\ge1}\frac{D_{t+s}}{R_{t+1}\cdots R_{t+s}},\qquad B_t=q_t-F_t=\lim_{T\to\infty}\frac{q_T}{R_{t+1}\cdots R_T}.$$
Bubble iff (with $D_t>0$) $\sum_t D_t/q_t<\infty$, equivalently $\lim_t Q_tq_t>0$ with $Q_t=1/(R_1\cdots R_t)$. With a benchmark interest rate $R^*_t$ (the no-asset rate), population growth $G_n$ and young endowments $e_t^y$: every equilibrium is bubbly iff
$$\sum_{t=1}^{\infty}\frac{D_t}{G_n^{\,t}e_t^{y}}<\infty,$$
and every equilibrium is bubbleless if that series diverges. A bubble requires low interest rate ($R^*\le G_n$) and low dividend growth ($G_d<G_n$); a bubbleless equilibrium exists if $\sum_{t\ge1}D_t/(R_1^*\cdots R_t^*)<\infty$.

- **Inputs:** dividend stream $D_t$; interest rates $R_t$ (and the benchmark $R_t^*$); population growth $G_n$; young/old endowments (resource growth).
- **Parameters:** $G_n$; $R^*$; dividend growth $G_d$; the summability index $\alpha$ in the boundary case $D_te_t^y/G_n^t\sim t^{-1/\alpha}$.
- **Observed effects:** recovers Tirole's three regimes; in the stationary low-interest-rate case the maximal equilibrium is asymptotically bubbly and Pareto optimal, every other equilibrium (including the bubbleless one) is Pareto dominated; larger initial asset value strictly Pareto dominates smaller; bubble and Pareto optimality are distinct properties (arXiv:2508.03230v4).
- **Failure modes:** pure-exchange OLG with no capital accumulation; exogenous primitives; welfare conclusions require regularity conditions and a converse is only partial; the classification is aggregate-market, not single-stock, and dividends must be modelled as a long-lived tree's cash flow.

## Data Requirements

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Equity / index / sector-ETF OHLCV (returns, volume, VWAP) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Equity OHLCV alt (returns, betas) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Market / ETF quote bars alt | `https://financialmodelingprep.com/stable/quote` | core_stock_apis | fmp | ok |
| Interval bars (candidate for ETF/index series) | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok |
| Local-gateway snapshots / klines | `moomoo://get_market_snapshot` | core_stock_apis | moomoo | gateway |
| Per-share dividend history (DDM states, duration) | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Dividend calendar alt | `https://api.benzinga.com/api/v2.2/calendar/dividends` | corporate_actions | benzinga | ok |
| Treasury yield / zero curve ($R_f$, discount rates) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Macro state: consumption (PCE), CPI, population, credit spread | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Macro indicators alt | `moomoo://get_macro_indicator_list` | macro_data | moomoo | gateway |
| Option surface / model-free implied vol (risk-premium state) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Earnings, book value, market cap (valuation inputs) | `https://financialmodelingprep.com/stable/income-statement` | fundamental_data | fmp | ok |
| Fundamentals alt (valuation inputs) | `https://www.alphavantage.co/query` | fundamental_data | alpha_vantage | ok |
| Corporate filings (dividends, capital structure) | `https://data.sec.gov/submissions/CIK0000320193.json` | sec_filings | sec_edgar | ok |
| News / sentiment (belief and attention proxies) | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| Analyst consensus / research ratings (cash-flow expectations) | `moomoo://get_research_rating_summary` | analyst_ratings | moomoo | gateway — rating summary only, not a forecast series |
| Short interest / institutional holdings (belief & friction proxies) | `moomoo://get_short_interest` | short_interest | moomoo | gateway |
| Economic calendar (CPI release / shock days) | `moomoo://get_economic_calendar` | economic_calendar | moomoo | gateway |
| VIX index level series (driver $Z$) | **gap** — no probed endpoint returns `^VIX`; cboe serves SPX option quotes only | — | — | gap |
| Index futures prices (dividend-strip construction) | **gap** — no futures/commodity feed in the inventory | — | — | gap |
| S&P 500 dividend strip / dividend futures prices | **gap** — no endpoint; the closest is index options on cboe | — | — | gap |
| FX / DXY log return (driver $Z$) | **gap** — no probed FX endpoint; eodhd `core_stock_apis` is the only untested candidate | — | — | gap |
| Intraday quote / order-book data (microstructure, sub-daily timing) | **gap** — no intraday quote or order-book feed | — | — | gap |

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Beta is an attenuated proxy, not a mechanism.** Under the fork the population OLS slope is $\beta_{fork}=(b/a)\lambda$ with $\lambda<1$ and shrinks as market measurement noise $\sigma_X$ rises; adding driver proxies collapses it (≈0.9 → ≈0.03 on CPI days), and a beta-neutral residual still loads on $Z$. Report betas as associational and test lag/leave-one-out alternatives before any hedging claim (arXiv:2509.05760v3).
- **State dependence defeats any single-window beta.** Slopes differ systematically across volatility terciles, rate trends, FX trends and structural episodes; a fixed 36–60-month beta is a misspecification. Estimate environment-conditional slopes and report them (arXiv:2509.05760v3).
- **Predictive-regression bias and overlapping horizons.** $dr$ is autocorrelated (0.919 monthly), so return-predictor standard errors must be corrected — the paper uses the Hodrick (1992) adjustment, the Stambaugh (1999) small-sample bias correction, and encompassing (ENC) and Clark–West (CW) tests, reporting in-sample 25% and OOS 15% $R^2$ (arXiv:2310.07110v1). Do not compare predictors on in-sample $R^2$ alone; the $pd$ OOS $R^2$ is near zero.
- **Look-ahead and in-sample leakage.** $dr$ is promoted precisely because it is "measured in real time and directly from market prices", whereas latent-state filters require full-sample estimation. Any dividend-strip reconstruction must use only information available at $t$; futures-curve interpolation (piecewise cubic or linear) is a modelling choice, not data (arXiv:2310.07110v1). In the SDDM the discount rate must be estimated on a window that does not include the valuation date (the paper uses a shorter five-year window for $k$ than for dividends, arXiv:1609.03029v2).
- **Variance and covariance can blow up or vanish.** The SDDM variance is finite only under $\mathrm{Var}[\tilde g]<(1+k)^2-(1+\bar g)^2$ and diverges as that bound is approached; the cross-covariance changes sign with $\mathrm{Cov}[\tilde g_A,\tilde g_B]$ and is zero when growth rates are uncorrelated. Always check the existence condition before reporting a portfolio variance (arXiv:1609.03029v2).
- **Momentum/reversal conditions are not sharp.** The model's momentum condition $\pi b_2^2\sigma_s^2(b_2-b_2^*)-b_1c_1^2>0$ depends on many uncalibrated parameters; reversal is the model's only unconditional prediction. Treat the momentum sign as an empirical question to be tested out-of-sample, not a guaranteed signal (arXiv:2406.08448v1).
- **Bubble ≠ inefficiency.** Bubbly equilibria can be Pareto optimal and bubbleless equilibria Pareto dominated; when several equilibria coexist they are ranked by initial asset value, with larger values dominating. Do not infer welfare from the presence of a bubble (arXiv:2508.03230v4).
- **Calibration targets worth pinning.** $dr$: mean 4.027, std 0.494, autocorr 0.919; first two PCs of valuation ratios explain 96.3% of variance; SDDM empirical inputs: $k_A=6.631\%$, $k_B=7.943\%$, $\mathrm{Var}[\tilde g_A]=0.02431$, $\mathrm{Var}[\tilde g_B]=0.01447$ (arXiv:2310.07110v1, arXiv:1609.03029v2).

## Recommended Workflow

1. **CAPM beta + causal-diagnostics module (S).** Estimate rolling betas from equity OHLCV and a market/ETF proxy, then run the three diagnostics: lead–lag regressions, leave-one-out index, and shock-day attenuation with $Z$ proxies. Data: `core_stock_apis` (eodhd/tiingo/fmp) for stock, market and sector-ETF series; `macro_data` (fred) for rate/credit series; CPI dates from `economic_calendar` (moomoo). Value: the cheapest unblocking step — a baseline risk exposure plus the corpus' central warning that beta is associational (arXiv:2509.05760v3). Risk: VIX and DXY are gaps, so $Z$ starts with $\Delta DGS10$ and sector returns only.
2. **Dividend-discount / stochastic-DDM valuation engine (S).** Pull per-share dividends, build two growth states (geometric-mean and median splits) with joint probabilities, estimate $k$ by CAPM, and output $\bar P_0$, $\mathrm{Var}[\tilde P_0]$ and pairwise $\mathrm{Cov}[\tilde P_{A0},\tilde P_{B0}]$ with the existence check. Data: `corporate_actions` (eodhd/benzinga) + `risk_free_curve` + `core_stock_apis`. Value: fundamental value, dispersion and a mean-variance covariance matrix with no exotic data (arXiv:1609.03029v2). Risk: short dividend histories force a two-state abstraction; the variance bound can bind.
3. **Valuation-duration proxy monitor (M).** Build $dr_t=pd_t-s_{t1}$ where the near strip is approximated by the realised-dividend ratio (since dividend strips and index futures are gaps), and use it as a discount-rate state variable alongside $pd$. Data: index level + dividends + `risk_free_curve`. Value: a return predictor the corpus shows reaches OOS $R^2$ 15% and Sharpe 0.58 in its true form (arXiv:2310.07110v1). Risk: the proxy is not the true strip price; expect materially weaker OOS power until a strip/futures feed exists.
4. **Consumption-based pricing diagnostic (M).** Use FRED consumption (PCE) and returns to evaluate the modified basic equation $E[u'(c_t)p]=\beta E[u'(c_T)x]$ and its volatility/autocorrelation decomposition for a candidate utility. Data: `macro_data` (fred) + `core_stock_apis`. Value: an SDF-consistency check on any pricing model FinRobot builds (arXiv:2204.07506v2). Risk: theory-only; requires an explicit utility function and the asset amount $\xi$.
5. **Heterogeneous-belief momentum/reversal signal (M).** Compute the empirical $\gamma_m$ and $\gamma_r$ autocorrelation measures and condition them on volume, short interest and sentiment. Data: `core_stock_apis` + `short_interest`/`institution_data` (moomoo) + `news_data`/`news_sentiment`. Value: a single signal family that unifies momentum and reversal and links them to belief heterogeneity (arXiv:2406.08448v1). Risk: parameters are uncalibrated; the momentum sign must be validated out-of-sample.
6. **OLG bubble-regime and welfare monitor (L).** Estimate a long-run dividend-growth rate, benchmark interest rate and population/resource growth, then classify the market as bubbleless, co-existing or bubbly via the summability test, and flag that welfare is a separate question. Data: `corporate_actions` (index dividends), `risk_free_curve`, `macro_data` (fred: population, output). Value: a regime label and a guard against equating bubbles with inefficiency (arXiv:2508.03230v4). Risk: pure-exchange abstraction; aggregate-market only; requires a long, clean dividend/rate history.
7. **Risk-premium and discount-rate state inputs (S).** Assemble term spread, credit spread and implied-vol state variables from FRED and the cboe SPX surface for use by items 1–4. Data: `macro_data` (fred) + `options_surface` (cboe). Value: supplies the $Z$ and discount-rate inputs the equilibrium models need (arXiv:2509.05760v3, arXiv:2310.07110v1). Risk: the raw VIX series is a gap and must be approximated from the SPX surface.

## Output Format

### Discount-Rate and Beta Diagnostics
| Beta estimate | Window / conditioning set | Value | Reading |
|---------------|---------------------------|-------|---------|
| OLS vs market | rolling window | ... | associational proxy, not causal |
| Leave-one-out index | ... | ... | aggregator-contradiction check |
| Lagged (k >= 1) | ... | ... | sign-alternating / insignificant |
| Shock-day + Z (ΔDGS10, sector ETF) | CPI dates | ... | attenuation (baseline ~0.9 -> ~0.03) |
| Post-hedge residual loading on Z | ... | ... | beta-neutral hedge leaves common driver |
Note which driver proxies are gaps (VIX, DXY) and what was substituted.

### Stochastic-DDM Valuation
| Stock | d0 | Growth states (g, p) | k (CAPM) | Expected P0 | Var[P0] | Existence bound satisfied |
|-------|----|----------------------|----------|-------------|---------|---------------------------|
Pairwise Cov[P_A0, P_B0] from the risk-adjusted growth covariance, and the
resulting minimum-variance weights; flag any case where Var[g] approaches
(1+k)^2 - (1+bar g)^2 and the variance diverges.

### Valuation-Duration State
| Date | pd | s_t1 (near-strip proxy) | dr = pd - s_t1 | Context (mean 4.027, std 0.494, autocorr 0.919) |
|------|----|-------------------------|----------------|------------------------------------------------|

### Verdict
State the discount rate used and how it was estimated, whether the beta is
reported as associational or causal, whether the SDDM existence condition
holds, and whether the momentum sign survives out-of-sample validation rather
than being asserted from the model condition.

## References

| arXiv id | title | year |
|---|---|---|
| 2509.05760v3 | Rethinking Beta: A Causal Take on CAPM | 2025 |
| 2508.03230v4 | To Bubble or Not to Bubble: Asset Price Dynamics and Optimality in OLG Economies | 2025 |
| 2406.08448v1 | Heterogeneous Beliefs Model of Stock Market Predictability | 2024 |
| 2310.07110v1 | Valuation Duration of the Stock Market | 2023 |
| 2204.07506v2 | Price and Payoff Autocorrelations in a Multi-Period Consumption-Based Asset Pricing Model | 2022 |
| 1609.03029v2 | Covariance of random stock prices in the Stochastic Dividend Discount Model | 2016 |
