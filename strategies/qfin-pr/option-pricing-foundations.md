# Option Pricing Foundations — learnings from the q-fin.PR corpus
`970` of 2274 corpus papers matched this category (`963` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **The BSM machinery is still the reference object, and it is being re-derived rather than replaced.** arXiv:2607.06355v1 builds Geometric Brownian motion (GBM) *from* a Maximum-Entropy principle: return symmetry selects $\ln S$ as the unique (up to affine) dynamical variable, a continuity constraint plus a directionality constraint then produce the GBM transition density $\ln(S'/S)\sim\mathcal N\big((\mu_c-\tfrac12\sigma^2)\Delta t,\ \sigma^2\Delta t\big)$, with $\sigma^2\Delta t$ identified as an "entropic clock". The same machinery, given one more constraint, gives Merton's jump-diffusion. This reframes BSM as the no-jump limit rather than the starting postulate.
- **Contingent-claim valuation is a portfolio-replication statement.** arXiv:2308.13717v3 shows that a positive $C^{2,1}$ function $V$ of asset prices generates a portfolio whose value replicates $V$ if and only if $V$ solves a *general Black–Scholes PDE* (Corollary 5.3, eq. 5.3/5.4). Homogeneity of degree 1 — Merton's economic requirement on option-pricing functions — is exactly the condition that removes the riskless asset from the replicating portfolio. The paper is explicit that its replicability concept is decoupled from arbitrage: arbitrage *can* exist in the setting (arbitrage-free markets are not assumed).
- **The pricing kernel is the object of empirical work, not the martingale measure alone.** arXiv:2112.05308v2 estimates a *state-dependent* kernel inside a Realized GARCH model and finds volatility-risk aversion is time-varying: on average the variance risk premium is negative, but during low-volatility regimes (1993–1995, 2004–2007, 2014–2017) investors show a slight appetite for variance risk. This is presented as an explanation of the empirical *pricing-kernel puzzle* (a U-shaped, or sometimes inverted, kernel against market return).
- **Discrete hedging is where the theory leaks.** arXiv:2405.02919v1 gives closed-form asymptotics for delta-hedge error under discrete rebalancing: the expected error is $\mathcal O(\Delta t^2)$ but its second moment is $\mathcal O(\Delta t^2)$ with leading terms driven by the option gamma $C_{XX}$ interacting with systematic/idiosyncratic factor loadings $\varphi_i,\sigma_i$. Continuous-time BSM hedging is exact; the *implemented* hedge is not.
- **Solver technology is a live alternative to closed forms.** arXiv:2405.05780v1 substitutes the BSM PDE by its heat-equation form and fits an MLP (2-32-32-1, tanh, Adam) to option price series of Petrobras/Vale call options; the network tracks market prices closer than the analytic BSM solution through most of the option's life, with MSE as low as 1.295 BRL (PETRA332, $K=24.76$) and $R^2$-like ARV 0.003 for PETRA391.
- **Structural extensions price things the classical model cannot.** arXiv:2509.18099v1 embeds a market-index path dependence and an ESG-affinity parameter $\gamma^{\text{ESG}}$ into a unified Bachelier–BMS model; the ESG term moves option prices monotonically *and symmetrically* in $|\gamma^{\text{ESG}}|$ (eq. 34) with the sign fixed by whether the stock's relative ESG rating $Z^{(X;M)}_t$ exceeds the index's. arXiv:2607.06355v1 shows that in an incomplete jump market, no-arbitrage admits infinitely many martingale measures and the Esscher transform is the one selected by imposing the no-arbitrage condition through the *mean log-return* — a modelling choice, not a theorem.

## 2. Implementable formulas & algorithms

### 2.1 BSM closed form, PDE and heat reduction
**Purpose.** The baseline European pricer and the canonical valuation PDE in terms of which every extension below is stated and validated.

BSM PDE (arXiv:2405.05780v1 eq. 2.2; arXiv:2405.02919v1 eq. 1):
$$\frac{\partial c}{\partial t} + rS\frac{\partial c}{\partial S} + \tfrac12\sigma^2 S^2 \frac{\partial^2 c}{\partial S^2} = rc.$$
Closed form (arXiv:2405.05780v1 eqs. 2.3–2.5):
$$c = S_0 N(d_1) - Ke^{-rT}N(d_2),\qquad p = Ke^{-rT}N(-d_2)-S_0N(-d_1),$$
$$d_1 = \frac{\ln(S_0/K)+(r+\tfrac12\sigma^2)T}{\sigma\sqrt T},\qquad d_2 = d_1-\sigma\sqrt T.$$
Heat reduction used by the NN paper (eqs. 2.7–2.12): with $x=\ln(S/K)$, $\tau=\tfrac12\sigma^2(T-t)$, $c=Ku(x,\tau)e^{-\frac12(k-1)x-\frac14(k+1)^2\tau}$, $k=2r/\sigma^2$, the PDE becomes $\partial_\tau u=\partial_{xx}u$.

- **Inputs:** $S_0$, $K$, $T$, $r$, $\sigma$; terminal payoff $\max(S_T-K,0)$.
- **Parameters:** $r$ (Brazilian SELIC was held constant at 13.75%/yr in that study); $\sigma$ constant.
- **Observed effects:** the analytic solution converges to the spot price far from maturity and to the market option value near expiry (arXiv:2405.05780v1).
- **Failure modes:** constant-$\sigma$, no dividends, GBM tails; European-only (no analytic American price).

### 2.2 Merton jump-diffusion: entropic derivation, density and forward equation
**Purpose.** Add discontinuous moves and fat tails to the GBM baseline; obtain the implied-volatility smile from a Poisson mixture of lognormals.

Transition density on a finite horizon (arXiv:2607.06355v1 eqs. 33–35), i.e. Merton's jump-diffusion:
$$P_{JD}(\ln S'\,|\,\ln S)=\sum_{n=0}^{\infty}P(n)\,\big(P_c * P_J^{*n}\big)(\ln S'-\ln S),\qquad P(n)=e^{-\lambda\Delta t}\frac{(\lambda\Delta t)^n}{n!},$$
$$P_J(Y)=\frac{1}{\sqrt{2\pi\delta^2}}\exp\!\Big(-\frac{(Y-\kappa)^2}{2\delta^2}\Big),\quad \delta^2=\nu-\kappa^2,$$
with $\langle n\rangle=\lambda\Delta t$, mean log-jump $\kappa$, second moment $\nu$. Short-step form (eq. 34): $P_{JD}=(1-\lambda\Delta t)P_c+\lambda\Delta t\,(P_c*P_J)$.

Dynamics (eq. 36–37): $\Delta\ln S=(\mu_c-\tfrac12\sigma^2)\Delta t+\Delta W+Y\Delta N$, or $\frac{\Delta S}{S}=\mu_c\Delta t+\Delta W+(e^{Y}-1)\Delta N$.

Forward equation (Kolmogorov–Feller, eq. 39):
$$\partial_t p = -(\mu_c-\tfrac12\sigma^2)\,\partial_{\ln S}p + \tfrac12\sigma^2\,\partial^2_{\ln S}p + \lambda\int dy\,\big[p(\ln S-y,t)-p(\ln S,t)\big]P_J(y).$$
The Fokker–Planck equation is the $\lambda\to0$ limit; the pure compound-Poisson master equation is the $\sigma\to0$ limit.

- **Inputs:** $S_0$, $K$, $T$, $r$; jump intensity $\lambda$, jump-size mean $\kappa$ and dispersion $\delta$.
- **Parameters:** risk-neutralization via the Esscher transform, selected by imposing no-arbitrage through the mean log-return (arXiv:2607.06355v1 §3.1). The Merton PIDE for the premium is the backward Kolmogorov–Feller equation under the risk-neutral measure $P_{rn}$; the BSM PDE is its $\lambda_{rn}=0$ limit.
- **Observed effects:** the Poisson-weighted mixture of lognormals generates the implied-volatility smile/smirk; the market is incomplete for $\lambda>0$ so the martingale measure is a choice among an infinite family (eq. 40: $E_{rn}[S'/S]=e^{r\Delta t}$ is one scalar condition on an infinite-dimensional set).
- **Failure modes:** calibration of $(\lambda,\kappa,\delta)$ is weakly identified from short-dated option panels; the Esscher selection depends on which observable carries the no-arbitrage constraint — a different controlled observable selects a different measure.

### 2.3 Contingent-claim replicability and the generalized BSM PDE
**Purpose.** Decide whether a portfolio-generating function $V$ (a candidate option value) is exactly replicable, and extract its weights and drift.

Generating-function weights (arXiv:2308.13717v3 Theorem 3.4, eqs. 3.7–3.9):
$$\pi_i(t)=\frac{X_i(t)\,D_iV(X(t),t)}{V(X(t),t)},\qquad \pi_0=1-\sum_i\pi_i(t),$$
$$d\Phi_V(t)=-\tfrac12\sum_{i,j}\sigma_{ij}\frac{X_iX_jD_{ij}V}{V}dt-\frac{D_tV}{V}dt+\gamma_0\Big(1-\sum_i\frac{X_iD_iV}{V}\Big)dt.$$
Replicability holds iff $\Phi_V\equiv0$ (Prop. 5.2), giving the general BSM equation (Cor. 5.3):
$$\tfrac12\sum_{i,j}\sigma_{ij}X_iX_jD_{ij}V + D_tV + \gamma_0\sum_i X_iD_iV - V = 0,$$
which for $\gamma_0=r$ is the generalized Black–Scholes equation. For a *contingent claim function* (homogeneous of degree 1) the $\gamma_0$ term vanishes (Cor. 5.4):
$$\tfrac12\sum_{i,j}\sigma_{ij}X_iX_jD_{ij}V + D_tV = 0.$$

- **Inputs:** asset price processes $X_i$ with growth rates $\gamma_i$ and covariance processes $\sigma_{ij}$; the candidate $V(x,t)$; $\gamma_0$ the interest-rate process.
- **Parameters:** homogeneity degree (degree 1 needed to drop the riskless asset); $V$ must be positive $C^{2,1}$ (put/call terminal values dropping to 0 require the Section-7 workaround).
- **Observed effects:** the geometric mean $x_1^{p_1}\cdots x_n^{p_n}$, $\sum p_i=1$, is replicable only for constant covariance processes; the Gibbs–Shannon entropy $S(x)=-\sum x_i\log x_i$ extends to a contingent claim function $\hat S$ generating the same portfolio $-\mu_i\log\mu_i/S(\mu)$ (Ex. 4.8).
- **Failure modes:** replicability is a property of the *price processes as much as the function*; assuming zero drift is a modelling error, and the concept carries no arbitrage guarantee in this framework.

### 2.4 State-dependent pricing kernel + Markov-switching Realized GARCH pricer
**Purpose.** Price European options with a variance risk premium that varies with a latent market regime, and a time-varying volatility risk aversion $\chi_{s_t}$.

Realized GARCH under $P$ (arXiv:2112.05308v2 eqs. 1–3, with state-dependent intercept 3'):
$$R_{t+1}=r+\lambda\sqrt{h_{t+1}}-\tfrac12 h_{t+1}+\sqrt{h_{t+1}}z_{t+1},\quad \log h_{t+1}=\omega+\beta\log h_t+\gamma\log x_t+\tau_1z_t+\tau_2(z_t^2-1),$$
$$\log x_t=\xi_{s_t}+\varphi\log h_t+\delta_1z_t+\delta_2(z_t^2-1)+\sigma u_t.$$
State-dependent exponentially affine kernel (eq. 4):
$$M_{t+1,t}(s_{t+1})=\frac{\exp(\psi z_{t+1}+\chi_{s_{t+1}}u_{t+1})}{E_t^P\!\left[\exp(\psi z_{t+1}+\chi_{s_{t+1}}u_{t+1})\mid s_{t+1}\right]},\qquad \psi=-\lambda\ \text{(no-arbitrage)}.$$
Risk-neutral dynamics (Theorem 1): $z^*_{t+1}=z_{t+1}+\lambda$, $u^*_{t+1}=u_{t+1}-\chi_{s_{t+1}}$, with $\omega^*=\omega-\tau_1\lambda+\tau_2\lambda^2$, $\tau_{1*}=\tau_1-2\tau_2\lambda$, $\delta_{1*}=\delta_1-2\delta_2\lambda$, $\xi^*_{s_t}=\xi_{s_t}-\delta_1\lambda+\delta_2\lambda^2+\sigma\chi_{s_t}$.
Variance risk premium (eq. 5): $E^Q_t(\log h_{t+2})-E^P_t(\log h_{t+2})=-(\tau_1+\gamma\delta_1)\lambda+(\tau_2+\gamma\delta_2)\lambda^2+\gamma\sigma E^P_t(\chi_{s_{t+1}})$.
Option price (Edgeworth expansion, eqs. 11–12):
$$\tilde g(z)\approx\Big[1-\tfrac{\kappa_3}{6}H_3(z)+\tfrac{\kappa_4-3}{24}H_4(z)+\tfrac{\kappa_3^2}{72}H_6(z)\Big]\varphi(z),\qquad C_t(s_t)\approx A_0+\tfrac{\kappa_3}{6}A_3+\tfrac{\kappa_4-3}{24}A_4+\tfrac{\kappa_3^2}{72}A_6,$$
with $A_0=S_te^{\delta_\sigma}\Phi(d)-Ke^{-r(T-t)}\Phi(d-\sigma)$ and higher terms from the Hermite polynomials $H_3,H_4,H_6$.

- **Inputs:** close-to-close returns $R_t$, a realized volatility measure $x_t$ (realized kernel), and an option-price panel for joint estimation; latent states inferred from $(R_t,x_t)$.
- **Parameters:** $N=2$ states; $\lambda$ equity premium, $\chi_{s_t}$ state-dependent variance-aversion (large $\chi\Rightarrow$ high variance risk premium); estimated by quasi-ML on $(R_t,x_t)$ plus a Vega-weighted option quasi-likelihood.
- **Observed effects:** on S&P 500 / SPX options 1990–2019 (7,559 trading days; 32,024 OTM options), return std 17.437% vs average implied vol 19.147% (negative variance risk premium); the framework reduces in- and out-of-sample option-pricing errors by ≥15% vs benchmarks.
- **Failure modes:** the MGF of cumulative return has no closed form, so prices are *approximations* — Edgeworth truncation error grows with skewness/kurtosis; the latent state is only identified through realized measures, so a bad RV proxy corrupts the kernel.

### 2.5 Discrete-hedging error asymptotics (finite difference / Monte Carlo)
**Purpose.** Quantify and reduce the hedging error of a delta-hedged book when rebalancing is discrete.

Option sensitivity via finite differences (arXiv:2405.02919v1): $f'(x_i)\approx\frac{f(x_{i+1})-f(x_i)}{h}$ with leading error $\mathcal O(\Delta x)$ from $\frac{\Delta x}{2!}f''(x)$.
Hedge error (eq. 14): $\Delta H=C_X\big[X(t+\Delta t)-X(t)\big]+\mathcal P[e^{r\Delta t}-1]-\big[C(X(t+\Delta t),t+\Delta t)-C(X(t),t)\big]$, with cash position $\mathcal P=\frac1n\sum_i\big(C(X_i,t)-C_X(X_i,t)X_i\big)$ (eq. 13).
Theorem 1: $E[\Delta H]=\mathcal O(\Delta t^2)$ and
$$E\big[(\Delta H)^2\big]=\frac{1}{2n^2}\Big[\sum_i C_{X_iX_i}\varphi_i\Big]^2\Delta t^2+\frac{1}{2n^2}\sum_i\big(C_{X_iX_i}\big)^2(\tilde\sigma_i^4-\varphi_i^4)\Delta t^2+\mathcal O(\Delta t^2),$$
where $\tilde\sigma_i^2=\sigma_i^2+\varphi_i^2$ and $\varphi_i$ is the systematic (single-factor) loading, $\sigma_i$ the idiosyncratic one.

- **Inputs:** multi-asset price series; $\Sigma=\varphi\varphi'+\Sigma_{\text{idio}}$ one-factor covariance; Monte Carlo samples for variance reduction (importance sampling, control/antithetic variates, Cholesky eigen-decomposition).
- **Parameters:** rebalancing interval $\Delta t$; number of names $n$.
- **Observed effects:** higher-order exposure to the *systematic* factor reduces discrete-time hedge-error variance; a static hedge can be made exact in finite time only by letting the portfolio size grow without bound.
- **Failure modes:** the expansion is asymptotic in small $\Delta t$ and assumes the BS model is the true dynamics; transaction costs and jumps are outside its scope.

### 2.6 Neural-network (physics-informed) BSM solver
**Purpose.** Solve the BSM heat equation from real option-price boundary data without an analytic formula, useful where the PDE is non-standard or externally perturbed.

Residual objective (arXiv:2405.05780v1 eqs. 3.1–3.4): for differential operator $D$ and forcing $F$, minimize $R(\hat u)=D(\hat u)-F$; hard-constrain initial/boundary data with $\tilde u(x,t)=A(x,t;x_b,t_0)\hat u(x,t)$. Heat form $\partial_\tau u=\partial_{xx}u$ with $\tau=\tfrac12\sigma^2(T-t)$, $x=\ln(S/K)$, recovered price $c(s,t)=Ku(x,\tau)\exp\big(-\tfrac12(k-1)x-\tfrac14(k+1)^2\tau\big)$, $k=2r/\sigma^2$.

- **Inputs:** a real option call-price time series mapped through the same transforms; strike $K$; constant $r$.
- **Parameters:** MLP 2-32-32-1, tanh, Adam, 30,000 epochs (Neurodiffeq + Torch); evaluation by MAE, MSE, MAPE, POCID, ARV.
- **Observed effects:** the NN solution is closer to the market price than the analytic BSM curve for most of the option's life; best-case MSE 1.295 (PETRA332), MAPE 0.528 / ARV 0.003 (PETRA391); POCID 46–84%.
- **Failure modes:** fit is per-series; only call series had sufficient volume (Brazilian puts lacked liquidity); no dividend, no early exercise; NN extrapolation beyond the trained $x,\tau$ range is unchecked.

### 2.7 Path-dependent, ESG-valued BBSM binary-tree pricing
**Purpose.** Price European calls where the stock's increments are driven by a market index's *path* (via the Cherny–Shiryaev–Yor invariance principle) and an ESG-affinity parameter scales the risky value.

Unified BBSM dynamics (arXiv:2509.18099v1 eq. 1): $dA_t=\varphi_tdt+\psi_tdB_t$ with $\varphi_t=a_t+\mu_tA_t$, $\psi_t=v_t+\sigma_tA_t$; the 3D subspace $a_t=v_t=\rho_t=0$ is BSM, the disjoint subspace $\mu_t=\sigma_t=r_t=0$ is the modernized Bachelier model. ESG-adjusted price $A^{(X)}_t=S^{(X)}_t\big(1+\gamma^{\text{ESG}}Z^{(X;M)}_t\big)$, $Z^{(X;M)}_t=\big(Z^{(X)}_t-Z^{(M)}_t\big)/Z^{(M)}_t$; regression residual (eq. 26) fitted by constrained least squares subject to $\tilde v+\tilde\sigma A^{(M)}_{t_{n,k}}+\tilde\gamma h(X_{k/n})\ge0$.

- **Inputs:** stock prices, index/ETF prices (QQQ proxy used), ESG ratings per component, 3M T-bill daily curve.
- **Parameters:** $a,\mu,v,\sigma,\gamma$ per stock (constant over the sample); $\gamma^{\text{ESG}}\in\{-1,0,1\}$; reparameterizations $a/A_0,v/A_0,\gamma/A_0$; riskless fit $\rho=-0.00139,\ r=0.00140$, adj. $R^2=0.418$.
- **Observed effects:** binary-tree call prices up to 26 days match published quotes reasonably (BBSM overestimates in-the-money calls); $\gamma^{\text{ESG}}$ moves prices monotonically with $|K_T(C,-1)-K_T(C,0)|\approx|K_T(C,1)-K_T(C,0)|$ (eq. 34), sign set by $\operatorname{sign} Z^{(X;M)}_t$ (AMD positive, AMZN negative).
- **Failure modes:** tree cost is $O(\sum_t 2^t)$ vs $O(\sum_t(t+1))$ for a binomial tree — only $\Delta=1$ day / $T\le26$ days was feasible; adjusted $R^2$ only 17–38% because a single index path is a poor Brownian approximation; the model cannot reproduce the heavy tails of empirical price changes.

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Risk-free discount curve ($r$, $\gamma_0$) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Underlying spot & daily OHLCV | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| SPX option quotes / implied vol surface | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Equity option chain / Greeks (local gateway) | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Implied expected move | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Dividends / corporate actions | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Trailing technical indicators (e.g. realized vol proxy) | `https://www.alphavantage.co/query` | technical_indicators | alpha_vantage | ok |
| Macro state (rates, term spread, HY spread) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| News / event features for jump arrivals | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| High-frequency realized measure (realized kernel / RV) | **gap** — the Realized-GARCH and RHARG models need intraday returns; no probed endpoint exposes a certified intraday or Oxford-Man RV series | — | — | gap |
| VIX index quote series | **gap** — no probed endpoint returns `^VIX`; `cboe` options_surface is the nearest served proxy | — | — | gap |
| Long-history SPX option panel (1990–2019, OptionMetrics/Optsum) | **gap** — served option data is delayed snapshot only | — | — | gap |
| ESG ratings $Z^{(X)}_t,Z^{(M)}_t$ | **gap** — no provider in the inventory exposes ESG scores | — | — | gap |
| Credit / CDS spread feed | **gap** — required for counterparty/credit extensions; unserved | — | — | gap |
| Swap / swaption quotes | **gap** — no rates-derivative endpoint | — | — | gap |
| Bond prices | **gap** — no fixed-income price endpoint | — | — | gap |
| Futures / commodity prices | **gap** — no futures endpoint (GBM jump extension to commodities unserved) | — | — | gap |
| Crypto prices | **gap** — no crypto endpoint | — | — | gap |
| Intraday quote / order-book feed | **gap** — no L1/L2 book endpoint; only delayed aggregates | — | — | gap |

## 4. Pitfalls, validation and measurement

- **Discrete hedging is not riskless.** The BSM self-financing hedge is exact only in continuous time; under discrete rebalancing the expected error is $\mathcal O(\Delta t^2)$ while its *second moment* is $\mathcal O(\Delta t^2)$ with gamma-weighted systematic and idiosyncratic terms — judge an implementation by the *distribution* of $\Delta H$, not its mean (arXiv:2405.02919v1).
- **Martingale-measure non-uniqueness is a choice, not an oversight.** Once jumps ($\lambda>0$) enter, the market is incomplete and infinitely many equivalent martingale measures satisfy $E_{rn}[S'/S]=e^{r\Delta t}$; the Esscher transform reported in arXiv:2607.06355v1 is selected by the specific no-arbitrage observable (mean log-return) and maximizing relative entropy — swapping the observable swaps the measure. Document the selection rule with the model.
- **Constant parameters are the largest model risk.** Both the BSM baseline (constant $\sigma$) and the BBSM fit (constant $a,\mu,v,\sigma,\gamma$ over 2,012 days) are static; the pricing-kernel paper finds risk aversion itself is regime-dependent (arXiv:2112.05308v2). Report regime-conditioned errors and re-estimate by walk-forward windows.
- **The pricing kernel is not monotone in wealth.** Empirically the kernel is U-shaped (sometimes hump- or inverted-U-shaped); a model that imposes monotone risk aversion is misspecified against the data and will misprice deep OTM puts (arXiv:2112.05308v2).
- **Calibration must be loss-weighted and out-of-sample.** The Realized-GARCH literature estimates the kernel jointly with a **Vega-weighted** option quasi-likelihood (units of implied-vol), scaled to balance the option count against the return count (arXiv:2112.05308v2). Never calibrate and evaluate on the same option panel; split in- versus out-of-sample and report both.
- **Approximation error is not model error.** Edgeworth-truncated prices (arXiv:2112.05308v2) and NN/PDE surrogates (arXiv:2405.05780v1) carry truncation/interpolation error separate from the underlying model; validate the approximation against the exact solution on a controlled case (e.g. the BSM limit) before trusting it in the tails.
- **Data-quality leakage.** The path-dependent BBSM fit achieved adjusted $R^2$ of only 17–38% because one historical index path is a poor proxy for the limiting Brownian motion — do not read high in-sample fits as model quality (arXiv:2509.18099v1). Assign annual ESG scores to fiscal-year-end and *lag* release dates to avoid look-ahead.
- **Strike-monotonicity and arbitrage checks.** Any interpolated or model-generated surface must satisfy call monotonicity/decreasing in $K$, convexity, and put-call parity; the ESG construction's symmetry $|K_T(C,-1)-K_T(C,0)|\approx|K_T(C,1)-K_T(C,0)|$ (eq. 34) is a testable invariant, not a guarantee.
- **Replicability is conditional on the price processes.** A candidate value function that solves the generalized BSM PDE is only replicable for the *actual* covariance processes $\sigma_{ij}$; a function replicable under constant covariance is not automatically so under stochastic covariance (arXiv:2308.13717v3).

## 5. Recommended first implementation in FinRobot

1. **Discount-curve loader + BSM/Greeks pricer (S).** Pull the daily Treasury curve from `federal_reserve` `risk_free_curve`, interpolate a zero curve, and implement the §2.1 call/put formulas plus delta/gamma/vega/theta. Data: `risk_free_curve` (ok) + `core_stock_apis` spot (ok). Value: the reference pricer every extension is validated against; no exotic inputs needed. Risk: constant-$\sigma$ misspecification on far-dated strikes.
2. **Implied-volatility extraction from the served SPX surface (S).** Invert §2.1 on `cboe` `options_surface` quotes to build a moneyness/term IV grid with monotonicity and parity sanity checks. Data: `options_surface` (ok). Value: turns the single served option feed into the $\sigma$ input the whole category consumes. Risk: delayed quotes and sparse strikes need robust filtering.
3. **Merton jump-diffusion / Esscher pricer (M).** Implement the §2.2 Poisson-mixture density and calibrate $(\lambda,\kappa,\delta)$ to the §2.1 IV smile, using the Esscher no-arbitrage constraint through the mean log-return. Data: the served IV grid (ok) — no new feed required. Value: reproduces the smile/smirk the BSM baseline cannot, and demonstrates the incomplete-market measure choice. Risk: weak identification of three jump parameters from short-dated quotes.
4. **Discrete-hedging-error simulator (M).** Reproduce §2.5: run a delta-hedged option book with finite-difference Greeks, measure the empirical distribution of $\Delta H$ across rebalancing frequencies, and apply variance reduction (antithetic/control variates). Data: `core_stock_apis` price paths (ok). Value: quantifies the gap between textbook BSM and an implementable hedge. Risk: MC cost grows with path count and names.
5. **Contingent-claim replicability checker (S).** Given a candidate $V(x,t)$ and fitted $\sigma_{ij},\gamma_0$, evaluate the generalized BSM PDE residual (eq. 5.3/5.4) and the generating weights $\pi_i$ from §2.3. Data: `core_stock_apis` + `risk_free_curve` (ok). Value: a cheap gate that certifies whether a proposed product is static-replicable before it is built. Risk: needs a stationary covariance estimate.
6. **State-dependent pricing-kernel pricer (L).** Build the §2.4 Markov-switching Realized GARCH model with the state-dependent kernel, estimate by quasi-ML on returns plus Vega-weighted option errors, and price calls with the Edgeworth approximation. Data: `core_stock_apis` returns + a realized measure (**gap** — must be proxied from daily OHLCV via `alpha_vantage` technical indicators until an intraday feed exists) + the `cboe` IV panel (ok). Value: ≥15% pricing-error reduction reported on SPX; the only corpus model that prices a *time-varying* variance risk premium. Risk: the realized-measure gap caps fidelity; Edgeworth truncation in the tails.
7. **NN/PDE heat-equation solver (M).** Reproduce the §2.6 MLP pipeline on a liquid call series, hard-constraining boundary data, as a surrogate where the analytic form is unavailable. Data: `core_stock_apis` + `options_surface` (ok). Value: a solver template for PDEs the closed forms cannot handle. Risk: per-series retraining; no extrapolation guarantees.
8. **Defer ESG-valued / path-dependent and multi-asset trees (—).** The BBSM/ESG model needs ESG ratings (**gap**) and index-component histories, and its binary tree is $O(\sum_t 2^t)$ limited to ~26-day maturities (arXiv:2509.18099v1). Mark out of scope until (a) an ESG feed exists and (b) the served data layer can support longer tenors; state this explicitly rather than shipping a stub.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2607.06355v1 | Entropic Dynamics of Jump-Diffusion Option Pricing | 2026 |
| 2509.18099v1 | Path-dependent, ESG-valued, option pricing in the Bachelier-Black-Scholes-Merton model | 2025 |
| 2405.05780v1 | Neural Network Learning of Black-Scholes Equation for Option Pricing | 2024 |
| 2405.02919v1 | Hedge Error Analysis In Black Scholes Option Pricing Model: An Asymptotic Approach Towards Finite Difference | 2024 |
| 2308.13717v3 | Portfolios Generated by Contingent Claim Functions, with Applications to Option Pricing | 2023 |
| 2112.05308v2 | Option Pricing with State-dependent Pricing Kernel | 2021 |
