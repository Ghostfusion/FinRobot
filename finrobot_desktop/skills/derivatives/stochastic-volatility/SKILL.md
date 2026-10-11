---
id: stochastic-volatility
name: Stochastic Volatility Pricing and Calibration
version: 1.0.0
author: finrobot
domain: derivatives
description: 'Heston and rough-volatility pricing engines: semi-analytic European and VIX-future prices, VVIX estimators, multi-factor Markovian and Volterra-Heston Asian pricers, moment-explosion guards. Use when pricing or calibrating stochastic-volatility models, not fitting a raw volatility surface.'
triggers:
- heston
- rough volatility
- stochastic vol calibration
- vix futures
- volterra heston
- vvix
- vol-of-vol
- asian option pricing
- moment explosion
- riccati volterra
- fourier contour
requires_data:
- input: Underlying daily OHLCV (returns, realized-variance proxy, $H$ calibration)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Daily bars, alternative vendor
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Interval bars (simulation grid / MC step calibration)
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Index/ETF spot quote ($S_0$, forward estimate)
  provider: finnhub
  category: core_stock_apis
  status: ok
- input: Spot snapshot via local gateway
  provider: moomoo
  category: core_stock_apis
  status: gateway
- input: SPX option quotes (VIX/VVIX replication, benchmark implied vols)
  provider: cboe
  category: options_surface
  status: ok
- input: Option chain with greeks (single-name Heston/rough-vol benchmark)
  provider: moomoo
  category: options_data
  status: gateway
- input: Expected move / model-free ATM implied input
  provider: moomoo
  category: expected_move
  status: gateway
- input: Risk-free discount curve $r(t)$
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Dividend / forward inputs $q(t)$
  provider: eodhd
  category: corporate_actions
  status: ok
- input: Macro state series (rates, stress flags for the scenario generator)
  provider: fred
  category: macro_data
  status: ok
- input: OHLCV-derived technical/realized-volatility proxies
  provider: alpha_vantage
  category: technical_indicators
  status: ok
- input: VIX index level ($v_0$ proxy; VIX future and VVIX equations)
  provider: ''
  category: ''
  status: gap
- input: VVIX index level (vol-of-vol anchor)
  provider: ''
  category: ''
  status: gap
- input: VIX / VVIX option quotes (double-replication VVIX, joint $\sigma$–VVIX fit)
  provider: ''
  category: ''
  status: gap
- input: Forward variance curve / variance-swap quotes (Volterra–Heston transform, GKW hedge)
  provider: ''
  category: ''
  status: gap
- input: Intraday (5-minute) returns for realized variance and empirical $H$
  provider: ''
  category: ''
  status: gap
- input: Exotic (Asian / barrier / cliquet) reference prices for validation
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Stochastic Volatility Pricing and Calibration

You are an expert stochastic-volatility quant working under the risk-neutral measure. You consume SPX/index option chains, risk-free and dividend curves, spot quotes, and VIX/VVIX levels, together with the calibrated Heston or rough-Heston parameter sets exposed by the available endpoints. You produce Heston semi-analytic European and VIX-future prices, four-way VVIX estimator dispersion, multi-factor rough-Heston and Volterra-Heston discretely-monitored Asian prices, and Fourier-strip / moment-explosion guards — never fabricating calibrated parameters, paper benchmark numbers, or any price, hedge or residual you did not actually compute.

> Source: FinRobot strategies corpus review — `strategies/qfin-pr/stochastic-volatility.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **The Heston vol-of-vol $\sigma$ is not the VVIX level, and $\mathrm{VVIX}(\sigma)$ is not monotone.** Starting from the CIR transition density, $\mathrm{VIX}^2_H(v(t),T-t)=\tfrac{1-e^{-\kappa(T-t)}}{\kappa(T-t)}\theta+\tfrac{1-e^{-\kappa(T-t)}}{\kappa(T-t)}v(t)$, the VIX future $F_{\mathrm{VIX}}=\int_0^\infty\sqrt{\mathrm{VIX}_H^2(C_1z,\Delta)}\,\varphi_{t,T}(z)\,dz$ and the log-contract $\mathrm{VVIX}^2\approx\tfrac{2}{T-t}\mathbb{E}[\ln F_{\mathrm{VIX}}(T,T)-\ln F_{\mathrm{VIX}}(t,T)]$ are one-dimensional integrals. A vol-of-vol of 30% can correspond to a VVIX near 100%, and the mapping depends on $\kappa$: with a small $\kappa$ the same VVIX band is reached at $\sigma>70\%$, with a $\kappa$ ten times larger only above $\sigma>125\%$ (arXiv:2512.19611v1).
- **Replicating VVIX from SPX options alone (no VIX options) is feasible via the Heston PDE, and truncation bias is measurable.** Solving the 2-D Heston PDE for $n$ calls and $n$ puts, then applying the VIX replication at $t=T$ and a second replication at $t=0$, gives VVIX directly out of SPX500 quotes. Cutting the VIX-option strike grid at $K_1^V=10$ instead of 5 inflates the estimate by 5.1% and 11.5% for two of the calibrated parameter sets, so the discrete lowest strike matters when VVIX is large (arXiv:2512.19611v1).
- **Volterra (rough) Heston admits a measure-valued affine Fourier–Laplace transform, which is what makes discretely monitored Asian options tractable.** With $X_t=(\log S_t,\nu_t)$, $\mathbb{E}[\exp\langle X_{T-s},\mu(ds)\rangle\mid\mathcal F_t]=\exp(\langle\mathbb{E}[X_{T-s}\mid\mathcal F_t],\mu(ds)\rangle+\tfrac12\int_0^{T-t}\psi(s)A^2\psi(s)^\top ds)$ where $\psi$ solves the Riccati–Volterra equation with $\mu$ as input; discretely monitored geometric Asians are the special case $\mu=(\sum_j\delta_{t_j},0)$ (arXiv:2609.07169v1).
- **The single quadratic governing non-linearity is $R(x_1,x_2)=\tfrac12(x_1^2-x_1)-\kappa x_2+\tfrac12\sigma^2x_2^2+\rho\sigma x_1x_2$.** In the Markovian Heston benchmark it collapses into a classical ODE (solved by RK4 on a grid aligned with the fixing dates); in the Volterra case it becomes a generalised Riccati–Volterra equation whose solution is $W^{\eta,2}$-regular for $\eta<\gamma/2$ (arXiv:2609.07169v1).
- **Discrete monitoring is a controlled approximation to continuous averaging, with rate $\Delta_N$.** Under $\mathbb{E}[S_T^{2q}]<\infty$ for some $q>1$, $\mathbb{E}[\sup_{t\le T}|H^N_{t,h}-H^c_{t,h}|^q]\le\Lambda_{q,h}(T)\Delta_N^q$. For the fractional kernel $K(t)=t^{\alpha-1}/\Gamma(\alpha)$ the integrability condition is an explicit moment bound on $v$, and it is exactly the fluctuation/explosion condition (arXiv:2609.07169v1).
- **Rough volatility is non-Markovian and non-semimartingale, but the fractional kernel is a Laplace transform of a positive measure, so a Markovian multi-factor approximation exists and converges.** $K(t)=\tfrac{t^{H-1/2}}{\Gamma(H+1/2)}=\int_0^\infty e^{-xt}\mu(dx)$ with $\mu(dx)=\tfrac{x^{-H-1/2}}{\Gamma(1/2-H)}dx$; discretising $\mu$ as weights $c_i^n$ at mean-reversions $\xi_i^n$ gives an $n$-factor Markovian variance $V^n_t=g^n(t)+\sum_i c_i^n V^{n,i}_t$ that converges in law (uniform topology) to the rough variance, with kernel error $\|K^n-K\|_{2,T}\le C_H n^{-4H/5}$ for a suitable auxiliary reversion grid, $C_H$ depending only on $H$ (arXiv:1801.10359v3).
- **The multi-factor lift turns the fractional Riccati equation into $n$ classical Riccati ODEs, with an explicit error.** $\psi^n(t,z)=\sum_i c_i^n\psi^{n,i}(t,z)$, $\partial_t\psi^{n,i}=-\xi_i\psi^{n,i}+F(z,\psi^n)$, and $\sup_t|\psi^n(t,z)-\psi(t,z)|\le C(1+b^4)\int_0^T|K^n(s)-K(s)|ds$; the scheme costs $O(n\,n_t)$ against the Adams scheme's $O(n_t^2)$, $n\approx20$ factors already track the rough-Heston implied-vol curve (tightest near the money), and at $n=500$ the relative Riccati error is about 1% (arXiv:1801.10359v3).
- **Rough Volterra simulation has three interchangeable schemes and one unreliable accelerator.** Cholesky (exact, $O(n^3)$), the Hybrid scheme ($O(n\log n)$, kernel split into a power function near zero and a step function elsewhere, with MSE-optimal $b_k^*=\tfrac{k^{H+1/2}-(k-1)^{H+1/2}}{H+1/2}$) and the rDonsker scheme ($O(n\log n)$) produce sample absolute moments statistically indistinguishable from exact. Turbocharging (the mixed estimator $\tilde C=\tfrac1M\sum(X_i+\hat\omega Y_i)-\hat\omega\mathbb{E}[Y]$) cut variance by factors 65, 27, 10, 5, 3, 3, 11, 9 for strikes 80…150 in an SPX-like setting but *raised* variance and biased deep-OTM prices when $\rho>0$; the authors recommend it only for $\rho<0$, and $\ge100{,}000$ paths for rough models versus ~10,000 for classical SV (arXiv:2108.01999v2).
- **Moment explosion in rough Heston is exactly as restrictive as in classical Heston.** $T(u)<\infty$ iff $u$ falls in cases (A) or (B) ($c_1(u)>0$ with $e_0(u)\ge0$, or $c_1>0,e_0<0,e_1<0$), which is equivalent to the classical Heston explosion time being finite; $T(u)$ is the blow-up time of a fractional power series whose coefficients obey a convolution recurrence, and critical moments are finite for all maturities — the mgf's analyticity strip is therefore finite (arXiv:1801.09458v3).
- **Short-maturity Asian options in local-stochastic volatility models have a large-deviations rate function, not a closed form.** $\lim_{T\to0}T\log C(T)=-I_\rho(S_0,V_0,K)$ with $I_\rho$ the infimum of $\Lambda_\rho[g,h]$ over absolutely continuous paths subject to $\int_0^1 e^{g(t)}dt=K$, and the ATM price scales as $\sqrt T$: $\lim_{T\to0}C(T)/\sqrt T=S_0\eta(S_0)\sqrt{V_0/(6\pi)}$. Expanding the rate function in log-moneyness $x=\log(K/S_0)$ yields ATM level, skew and convexity in closed form (arXiv:2409.08377v2).

## Methods & Formulas

### 2.1 Heston semi-analytic pricing, VIX futures and the four VVIX estimators
**Purpose.** Price European options and both levels/options of the volatility-of-volatility complex under classical Heston; recover a defensible vol-of-vol from the VVIX quote instead of from the smile.

Expected 30-day variance (exact under Heston):
$$\mathrm{VIX}_H^2(v(t),T-t)=\frac{1-e^{-\kappa(T-t)}}{\kappa(T-t)}\theta+\frac{1-e^{-\kappa(T-t)}}{\kappa(T-t)}v(t).$$
CIR transition (noncentral chi-square, the engine of every VVIX formula below):
$$v(t)\mid v(u)\ \stackrel{d}{=}\ \frac{\sigma^2(1-e^{-\kappa(t-u)})}{4\kappa}\,\chi'^2_d\!\left(\frac{4\kappa e^{-\kappa(t-u)}}{\sigma^2(1-e^{-\kappa(t-u)})}v(u)\right),\qquad d=\frac{4\kappa\theta}{\sigma^2}.$$
Log-contract VVIX and the VIX future:
$$\mathrm{VVIX}^2(t,T)\approx\frac{2}{T-t}\int_0^\infty\!\Big(\ln\mathrm{VIX}_H(C_1z,\Delta)-\ln F_{\mathrm{VIX}}(t,T)\Big)^2\varphi_{t,T}(z)\,dz,\qquad F_{\mathrm{VIX}}=\int_0^\infty\!\sqrt{\mathrm{VIX}_H^2(C_1z,\Delta)}\,\varphi_{t,T}(z)\,dz.$$
Simple no-integral approximation, obtained by a second-order Taylor expansion of $\sqrt{\mathrm{VIX}_H^2}$ around its conditional mean and using the closed-form first two conditional moments of $v(T)$, $\mathbb{E}[v(T)\mid t]=(v(t)-\theta)e^{-\kappa(T-t)}+\theta$ and $\mathbb{E}[v^2(T)\mid t]$ (equations A2–A4 of the paper):
$$\mathrm{VVIX}_A=\sqrt{\ln\!\Big(1+\frac{\mathrm{Var}[\mathrm{VIX}_H(v(T),\Delta)]}{\mathbb{E}[\mathrm{VIX}_H^2(v(T),\Delta)\mid t]}\Big)\Big/\Delta}.$$
Fourth estimator: a 2-D Heston PDE in $(x,v)$, $f_t=\tfrac{vx^2}{2}f_{xx}+\rho\sigma xv f_{xv}+\tfrac{\sigma^2v}{2}f_{vv}+(r-q)xf_x+\kappa(\theta-v)f_v-r_Cf$, initialised with call/put payoffs at $t=T+\Delta$, with the call–put-parity regression $H^\top H\beta=H^\top G$ to recover the forward, then VIX and VIX-option payoffs imposed at $t=T$ (arXiv:2512.19611v1).

- **Inputs:** SPX option quotes (or the calibrated $v_0,\kappa,\theta,\rho,\sigma$), the VIX level, 30-day $\Delta$.
- **Parameters:** $\kappa,\theta,\sigma,\rho,v_0$; replication strike range; $\Delta=30$ days (ACT/365).
- **Observed effects:** four estimates agree to <1% on the log contract when $K^V_1=5$; vol-of-vol 30% ↔ VVIX ~100%; strategy (b) (solve $\sigma$ by Newton from a VVIX quote) cut calibration time 50% versus strategy (a) and reduced the spread between weighting choices for VVIX < 150.
- **Failure modes:** the replication-based VVIX is not invertible (non-monotone in $\sigma$); strategy (a) can drive $\sigma\to3.09$ and $\kappa\to7.17$ against a plausible $\sigma=0.71$; the simple approximation degrades above $\sigma\approx50\%$ (arXiv:2512.19611v1).

### 2.2 Volterra–Heston pricing of discretely monitored Asian options
**Purpose.** Semi-closed prices of geometric Asian options (fixed and floating strike) with discrete fixings, plus a control variate for the arithmetic variant.

Riccati–Volterra equation with quadratic $R$ from §1:
$$\psi_1(t,\mu)=\mu_1([0,t]),\qquad \psi_2(t,\mu)=\int_{[0,t]}K(t-s)\mu_2(ds)+\int_0^t K(t-s)\,R(\psi(s,\mu))\,ds.$$
Conditional joint transform ($A^g_t=\int_{[0,t]}\log S_y\,g(dy)$, $\xi_t(x)=\mathbb{E}[\nu_x\mid\mathcal F_t]$, $\psi_1^{s,w}(u)=w+s\,g([T-u,T])$, $\psi_{1,-}^{s,w}(u)=w+s\,g((T-u,T])$):
$$\Psi_t(s,w)=H_t(s,w)/G_t^{s}=\exp\!\Big(sA^g_t+\psi_{1,-}^{s,w}(T-t)\log S_t-\tfrac12\int_t^T\!\psi_{1,-}^{s,w}(T-x)\,\xi_t(x)\,dx+\tfrac12\int_t^T\!\big((\psi_1^{s,w})^2+2\rho\sigma\psi_1^{s,w}\psi_2^{s,w}+\sigma^2(\psi_2^{s,w})^2\big)\xi_t(y)\,dy\Big),$$
and the price of any payoff $h$ admitting $h(x,y)=a+bx+cy+\int_{S_R}x^z\zeta_0(dz)+\int_{S_R}x^zy^{1-z}\zeta_1(dz)$ (the four standard geometric-Asian payoffs are instances with $\zeta_K(dz)=\tfrac{K^{1-z}}{2\pi z(z-1)}\lambda_R(dz)$) is
$$H^h_t=e^{-r(T-t)}a+e^{-r(T-t)}bG_t\Psi_t(1,0)+cS_t+e^{-r(T-t)}\int_{S_R}G_t^z\Psi_t(z,0)\zeta_0(dz)+e^{-r(T-t)}\int_{S_R}G_t^z\Psi_t(z,1-z)\zeta_1(dz).$$
- **Inputs:** strike/monitoring grid, $S_0$, $r$, and either the full forward-variance curve $\xi_0$ or the $n$-factor lift.
- **Parameters:** $(\kappa,\theta,\sigma,\rho)$, kernel $K$ (fractional, Gamma, $\alpha$-log, hyperbolic, or multi-exponential), contour line $R\in(0,1)$.
- **Observed effects:** in the Heston benchmark ($\kappa=1,\theta=v_0=0.04,\sigma=0.3,\rho=-0.7,S_0=K=100,T=1$, 21 fixings) the transform price lies inside every Monte-Carlo confidence interval; constant-variance price/delta match analytic values to $4.6\times10^{-11}$/$3.0\times10^{-13}$; the GKW hedge matches centred finite differences and the gap shrinks 4× when the step halves.
- **Failure modes:** the transform needs the forward-variance curve (an infinite-dimensional state); the $N$-factor lift is not accurate enough for pathwise hedge claims under singular fractional kernels; the moment conditions can fail for large $q$ (arXiv:2609.07169v1).

### 2.3 Multi-factor Markovian approximation and the $n$-dimensional Riccati scheme
**Purpose.** Replace a non-Markovian rough model with a Markovian $(n{+}1)$-dimensional one that a pure-NumPy engine can price and simulate, with an error guarantee.

Kernel approximation and the lift:
$$K(t)=\int_0^\infty\!e^{-xt}\mu(dx),\qquad K^n(t)=\sum_{i=1}^n c_i^n e^{-\xi_i^n t},\qquad V^n_t=g^n(t)+\sum_{i=1}^n c_i^n V^{n,i}_t,\qquad dV^{n,i}_t=(-\xi_i^n V^{n,i}_t-V^n_t)\,dt+\varphi(V^n_t)\,dB_t.$$
Weights from the auxiliary reversion grid ($0=\xi_0^n<\dots<\xi_n^n$): $c_i^n=\int_{\xi^n_{i-1}}^{\xi^n_i}\mu(dx)$, $\xi^n_i=\int_{\xi^n_{i-1}}^{\xi^n_i}x\,\mu(dx)/c_i^n$. Characteristic function and the $n$-dimensional ODE:
$$\log L^n(t,z)=\int_0^t F\!\big(z,\psi^n(t-s,z)\big)g^n(s)\,ds,\qquad \partial_t\psi^{n,i}=-\xi_i^n\psi^{n,i}+F(z,\psi^n),\quad \psi^{n,i}(0)=0.$$
- **Inputs:** Hurst $H$, horizon $T$, mean-reversion target $\varphi$, number of factors $n$; nothing market-side beyond a calibrated parameter set.
- **Parameters:** $n$ (≈20 useful, 500 for ~1% Riccati error), $\xi_n$ from the closed-form optimum, $n_t$ ODE steps.
- **Observed effects:** implied-vol error is smallest around the money and grows in the wings; the factor expansion also gives a fallback when no Riccati solver is available, since the $n$-dim ODE system is a standard initial-value problem.
- **Failure modes:** the approximation is a *lift*, not a reparameterisation — its forward-variance curve $g^n$ differs from the rough model's unless generated consistently; accuracy in the wings at small $n$ is poor (arXiv:1801.10359v3).

### 2.4 Rough Volterra Monte-Carlo: Cholesky / Hybrid / rDonsker, and turbocharging
**Purpose.** Generate $\alpha$RFSV / rough-Bergomi paths for vanilla and exotic pricing and for scenario analysis.

Model (exponential Volterra volatility) and the $\alpha$RFSV specialization:
$$\sigma_t=\sigma_0\exp\!\big(\xi Y_t-\tfrac12\alpha\xi^2r(t)\big),\qquad \sigma_t^{\alpha\mathrm{RFSV}}=\sigma_0\exp\!\big(\xi B^H_t-\tfrac12\alpha\xi^2t^{2H}\big),\qquad B^H_t=\sqrt{2H}\int_0^t(t-s)^{H-1/2}dW_s.$$
Hybrid scheme ($\kappa=1$, optimal step coefficient, second term is a discrete convolution computed by FFT):
$$Y_i=\sqrt{2H}\,W_{\max\{i-1,0\},1}+\sum_{k=2}^{i}\Big(\frac{b^*_k}{n}\Big)^{H-1/2}W_{i-k,2},\qquad b^*_k=\frac{k^{H+1/2}-(k-1)^{H+1/2}}{H+1/2}.$$
Turbocharged mixed estimator and its regression constants:
$$\tilde C=\frac1M\sum_{i=1}^M(X_i+\hat\omega Y_i)-\hat\omega\mathbb{E}[Y],\qquad \hat\omega=-\frac{\sum(X_i-\bar X)(Y_i-\bar Y)}{\sum(Y_i-\bar Y)^2},\qquad \hat Q=\max_i\Big\{\int_0^t\sigma_u\,du\Big\}.$$
Moment check for calibration $H$: $\mathbb{E}[(B^H_t)^q]=\tfrac{2^{q/2}}{\sqrt\pi}\Gamma\!\big(\tfrac{q+1}{2}\big)t^{qH}$ and $\mathbb{E}[\sigma_t^q]=\sigma_0^q e^{\frac12\xi^2q(q-\alpha)t^{2H}}$.
- **Inputs:** daily OHLCV (to calibrate $H,\xi,\rho,\sigma_0$ by the moment check or a fit to a benchmark surface), spot, $r$.
- **Parameters:** $H$ (empirical ≈0.05–0.15), $\xi\approx1.9$, $\rho\approx-0.9$, $\alpha\in[0,1]$, $n=4\times252$ steps/year typical, $P$.
- **Observed effects:** Hybrid and rDonsker are as accurate as exact Cholesky for absolute moments; runtime crossover is at $P\approx2500$ (beyond it Cholesky is fastest because it vectorises); turbocharging reduced variance 5–65× for strikes 80–150 with $\rho=-0.9$ but failed for $\rho>0$.
- **Failure modes:** turbocharging is biased through the non-linearity of the Black–Scholes map and is unstable for $\rho\approx0$ or $\xi>1$; sample-size demands are ~10× classical SV; the Deep-OTM region is where all schemes misbehave (arXiv:2108.01999v2).

### 2.5 Short-maturity Asian-option asymptotics (SABR / Heston / LSV)
**Purpose.** Price or sanity-check Asian options with zero Monte-Carlo cost at short maturity, and supply a control variate for longer maturities.

Rate function and its log-moneyness expansion:
$$\lim_{T\to0}T\log C(T)=-I_\rho(S_0,V_0,K),\qquad I_\rho=\inf_{\int_0^1e^{g(t)}dt=K}\Lambda_\rho[g,h],\qquad \Lambda_\rho[g,h]=\frac{1}{2(1-\rho^2)}\int_0^1\Big(\frac{g'(t)}{\eta(e^{g(t)})e^{h(t)/2}}-\frac{\rho h'(t)}{\sigma(e^{h(t)})}\Big)^2dt+\frac{1}{2}\int_0^1\frac{h'(t)^2}{\sigma(e^{h(t)})^2}dt,$$
$$I_\rho(S_0,V_0,S_0e^x)=\frac{x^2}{2\eta_0V_0}-\frac{3}{10\eta_0^{3/2}V_0}\big(3\rho\sigma_0+(\eta_0+6\eta_1)\sqrt{V_0}\big)x^3+\frac{\beta_0V_0+\beta_1\sigma_0+\beta_2\sigma_0^2}{1400\eta_0V_0}x^4+O(x^5),$$
with $\beta_0=109\eta_0^2+2664\eta_1^2+36\eta_0(13\eta_1-60\eta_2)$, $\beta_1=18\rho(-30\rho\sigma_1+(13\eta_0+18\eta_1)\sqrt{V_0})$, $\beta_2=9(-25+99\rho^2)$. The equivalent log-normal Asian volatility follows from $\lim_{T\to0}\Sigma_A(K,T)=|{\log(K/S_0)}|/\sqrt{2I_\rho(S_0,V_0,K)}$; the quadratic approximation $\Sigma_A(x)=\Sigma_{ATM}+s_Ax+\kappa_Ax^2$ is what gets quoted in practice. Heston is the special case $\sigma(v)=\xi v^{-1/2}$ ($\sigma_0=\xi/\sqrt{V_0}$, $\sigma_1=-\xi/(2\sqrt{V_0})$), SABR the case $\eta\equiv1,\sigma\equiv\mathrm{const}$.
ATM scaling: $\lim_{T\to0}C(T)/\sqrt T=\lim_{T\to0}P(T)/\sqrt T=S_0\eta(S_0)\sqrt{V_0/(6\pi)}$.
- **Inputs:** spot $S_0$, strike $K$, maturity $T$, and local-vol/vol-of-vol expansions $\eta_0,\eta_1,\eta_2,\sigma_0,\sigma_1,\sigma_2$.
- **Parameters:** correlation $\rho$; for Heston $(\kappa,\theta,\xi,V_0)$; for SABR $\sigma,V_0$.
- **Observed effects:** for $T=1/52$ the quadratic approximation matches 100k-path MC within reading accuracy for $|x|\lesssim0.05$ in SABR ($\sigma=2,V_0=0.1$) and Heston ($\kappa=2,\theta=0.09,\xi=0.2,V_0=0.04$); the $\mathcal{O}(x)$ term reproduces Alòs et al.'s ATM skew and the $\mathcal{O}(x^2)$ term reduces to the Black–Scholes Asian convexity as $\sigma\to0$.
- **Failure modes:** strictly an asymptotic as $T\to0$ — use only for short maturities and near-ATM strikes; the variational problem is only expanded around ATM (no global uniqueness proof for arbitrary $K$) (arXiv:2409.08377v2).

### 2.6 Moment-explosion time and critical moments (rough Heston)
**Purpose.** Decide whether a Fourier price is finite, bound the admissible damping contour, and compute the critical exponent that drives the wing asymptotics.

Fractional Riccati initial-value problem and its coefficients:
$$D_t^\alpha\psi(u,t)=R(u,\psi(u,t)),\quad I_t^{1-\alpha}\psi(u,0)=0,\qquad R(u,w)=c_1(u)+c_2(u)w+c_3w^2,$$
$$c_1(u)=\tfrac12\sigma^2u(u-1),\quad c_2(u)=-\kappa u,\quad c_3=\tfrac12\sigma^2>0,\qquad e_0=\tfrac12c_2,\quad e_1=e_0^2-c_3c_1.$$
Fractional power-series expansion of the solution and the resulting convolution recurrence for its coefficients ($d_1=c_1c_3$, $d_2=c_2$, $v_n$ increasing):
$$a_1(u)=\frac{d_1(u)}{v_1},\qquad a_{n+1}(u)=\frac{1}{v_{n+1}}\Big(d_2(u)\,a_n(u)+\sum_{k=1}^{n-1}a_k(u)\,a_{n-k}(u)\Big),\qquad v_n=\frac{\Gamma(n+1)}{\Gamma(\alpha n+1)},\quad \alpha\in(1/2,1).$$
Pringsheim's theorem makes the radius of convergence of $\sum_n a_n(u)z^n$ a genuine singularity, and Theorem 7.4 shows it coincides with the explosion time; Algorithm 7.5 therefore evaluates $a_1,\dots,a_{n_{\max}}$ ($n_{\max}=100$ is enough in the paper's tests) and inverts the Roberts–Olmstead blow-up asymptotic $f(t)\sim(T(u)-t)^{-\alpha}$, whose subexponential coefficient correction provably improves on the plain Cauchy–Hadamard rate. In case (B) the $a_n$ change sign, Pringsheim does not apply, and only the lower bound (7.11) is available. Theorem 4.1 supplies a lower bound that is sharp as $\alpha\to1$ — it degenerates to the classical Heston moment-explosion integral of (2.12) — and Theorem 4.2 a matching upper bound involving $\int_0^\infty w^{1/\alpha}dw/G'(u;w)$ scaled by $4(\alpha+1)^{-1}$, with $G(u,w)=(w+e_0)^2-e_1$.
Classical Heston reference time (Andersen–Piterbarg, eq. (2.13)): $T_1(u)$ has a closed form — an $\arctan$ expression when $e_1<0$, a logarithmic expression when $e_1>0$ and $e_0>0$, and $T_1(u)=\infty$ otherwise — and the rough-Heston explosion time is finite exactly when $T_1(u)<\infty$.
- **Inputs:** model parameters only; no market data.
- **Parameters:** $\alpha\in(1/2,1)$ (equivalently $H=\alpha-1/2$), $\kappa,\sigma,\rho$; $n_{\max}$.
- **Observed effects:** $T(u)<\infty$ exactly when $T_1(u)<\infty$; critical moments are finite for every maturity; for $\rho<0$ the lower critical moment (left wing) is what the algorithm returns, matching Lee's moment formula for the strike asymptotics.
- **Failure modes:** case (B) yields only a lower bound (the coefficients $a_n$ change sign, so Pringsheim does not apply); the refined asymptotic $a_n\sim R^{-n}n^{\alpha-1}/\Gamma(\alpha)$ is derived heuristically; the algorithm is limited to maturities that are not too large (arXiv:1801.09458v3).

### 2.7 Variance-optimal (GKW) hedging of Asian options under Volterra–Heston
**Purpose.** Produce a mean-variance hedge of a discretely monitored Asian payoff when volatility risk cannot be traded, with a computable residual error.

Galtchouk–Kunita–Watanabe representation $H^h_t=H^h_0+(\vartheta^{*,h}\cdot S)_t+L^h_t$ with $\langle L^h,S\rangle\equiv0$, $\vartheta^{*,h}_t=d\langle H^h,S\rangle_t/d\langle S\rangle_t$, and
$$\vartheta^{*,h}_t=c+\frac{H_t(1,0)}{S_t}\beta_t(1,0)+\int_{S_R}\frac{H_t(z,0)}{S_t}\beta_t(z,0)\zeta_0(dz)+\int_{S_R}\frac{H_t(z,1-z)}{S_t}\beta_t(z,1-z)\zeta_1(dz),\qquad \beta_t(s,w)=w+sg((t,T])+\rho\sigma\psi_2^{s,w}(T-t),$$
$$\epsilon_h=(1-\rho^2)\sigma^2\int_0^T\mathbb{E}\big[\nu_t\,|Q^h_t|^2\big]dt,\qquad Q^h_t=bH_t(1,0)\psi_2^{1,0}(T-t)+\int_{S_R}H_t(z,0)\psi_2^{z,0}(T-t)\zeta_0(dz)+\int_{S_R}H_t(z,1-z)\psi_2^{z,1-z}(T-t)\zeta_1(dz).$$
The $n$-factor lift replaces each $\psi_2$ by $\psi_2^{n}$ and each $H_t$ by $H^n_t$, and the hedge converges to the Volterra hedge under $\int_0^T\mathbb{E}[|\nu^n_t-\nu_t|]dt\to0$ plus a uniform $(2+\delta)$-moment bound.
- **Inputs:** $S_t$, the forward-variance curve $\xi_t(\cdot)$ (or the $n$-factor state $Y^{n,i}_t$), the payoff's countable representation $(a,b,c,\zeta_0,\zeta_1)$.
- **Parameters:** the same $(\kappa,\theta,\sigma,\rho,K)$ as pricing; rebalancing frequency; number of factors $n$.
- **Observed effects:** in the Heston benchmark the semi-analytic geometric hedge stabilises regression-based arithmetic-Asian hedging; hedge differences shrink as $2^{-2}$ with finite-difference steps, consistent with second-order accuracy.
- **Failure modes:** $(1-\rho^2)$ multiplies the whole residual, so a near-perfect correlation hides a badly estimated vol-of-vol; for singular kernels the factor lift is not accurate enough to support pathwise hedge claims, and the authors report none (arXiv:2609.07169v1).

## Data Requirements

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Underlying daily OHLCV (returns, realized-variance proxy, $H$ calibration) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily bars, alternative vendor | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Interval bars (simulation grid / MC step calibration) | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok |
| Index/ETF spot quote ($S_0$, forward estimate) | `https://finnhub.io/api/v1/quote` | core_stock_apis | finnhub | ok |
| Spot snapshot via local gateway | `moomoo://get_market_snapshot` | core_stock_apis | moomoo | gateway |
| SPX option quotes (VIX/VVIX replication, benchmark implied vols) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Option chain with greeks (single-name Heston/rough-vol benchmark) | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Expected move / model-free ATM implied input | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Risk-free discount curve $r(t)$ | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Dividend / forward inputs $q(t)$ | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Macro state series (rates, stress flags for the scenario generator) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| OHLCV-derived technical/realized-volatility proxies | `https://www.alphavantage.co/query` | technical_indicators | alpha_vantage | ok |
| VIX index level ($v_0$ proxy; VIX future and VVIX equations) | — | — | — | gap — no probed endpoint returns `^VIX` |
| VVIX index level (vol-of-vol anchor) | — | — | — | gap |
| VIX / VVIX option quotes (double-replication VVIX, joint $\sigma$–VVIX fit) | — | — | — | gap |
| Forward variance curve / variance-swap quotes (Volterra–Heston transform, GKW hedge) | — | — | — | gap |
| Intraday (5-minute) returns for realized variance and empirical $H$ | — | — | — | gap — twelvedata `interval` and massive aggregates are unverified candidates |
| Exotic (Asian / barrier / cliquet) reference prices for validation | — | — | — | gap |

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **The Fourier strip is finite and model-dependent.** Rough Heston critical moments are finite for all maturities, so any contour $R$ must lie strictly inside the analyticity strip; the lower critical moment ($\rho<0$, left wing) is the binding constraint, and it must be computed from the fractional power series rather than assumed (arXiv:1801.09458v3). The Volterra–Heston implementation in arXiv:2609.07169v1 confirms this empirically: shifting $R\in\{0.25,0.5,0.75\}$ moves the price by $<2\times10^{-6}$ and the initial hedge by $<1.2\times10^{-6}$, but that stability is only observed once the strip is respected.
- **Vol-of-vol is weakly identified from the smile, and the VVIX anchor is non-monotone.** Six parameter sets calibrated to the *same* SPX chain (equal weights vs inverse-Vega with a Vega floor of $10^{-2}$, $\kappa$ free or pinned at 0.75) produce VVIX estimates from 98 to 382 for the same market day (arXiv:2512.19611v1). Never report a single Heston fit as *the* vol-of-vol; report the objective-function sensitivity, and prefer solving $\sigma$ from a VVIX level over adding a VVIX penalty term.
- **Approximation error is not uniform in strike.** The multi-factor lift is most accurate around the money and degrades in the wings even at $n=20$ (arXiv:1801.10359v3); the log-moneyness expansion is an asymptotic in $x$ and in $T$ (arXiv:2409.08377v2). Report errors as a function of moneyness and maturity, never as a single number.
- **Simulation bias hides behind variance reduction.** Turbocharging's mixed estimator is biased by the non-linearity of the Black–Scholes map, and the bias is material exactly where it is least visible — deep OTM and $\rho>0$ (arXiv:2108.01999v2). Guard any accelerated estimator with the three admissibility tests from that paper (values non-negative, price below spot, prices monotone decreasing in strike) and fall back to the uncorrected estimator when they fail.
- **Separate discretization, sampling and solver error.** Calibrate the time grid independently of the path count; in the reported runtime study the exact Cholesky method overtakes the faster asymptotics for $P>2500$ because it vectorises, while rDonsker wins for few paths (arXiv:2108.01999v2). On the transform side, budget the quadrature nodes (384–1,000 Gauss–Legendre nodes on $|\mathrm{Im}\,z|\le60$–80) separately from the ODE steps (500–1,400), and report the sensitivity to each (arXiv:2609.07169v1).
- **Leakage points to watch.** The forward-variance state $\xi_t(x)=\mathbb{E}[\nu_x\mid\mathcal F_t]$ must be conditioned on the information set at $t$ only — in a discrete-monitoring implementation the monitoring coefficient on each interval must be the *left* value, not the value at the fixing (arXiv:2609.07169v1). When a VIX/VVIX level is used as an anchor, use the level observed at the valuation instant, not a smoothed or full-sample average, and align the option-snapshot date to the OHLCV date in the same time zone.
- **Validation protocol (in order).** (i) Degenerate check — set $V_0$ constant and confirm the transform reproduces discrete geometric-Asian Black–Scholes price and delta to machine precision (reported $4.6\times10^{-11}$ / $3.0\times10^{-13}$) (arXiv:2609.07169v1). (ii) Contour invariance — recompute across two or three $R$ lines and quadrature resolutions. (iii) Exact-CIR Monte Carlo — sample the variance transition from its noncentral-$\chi^2$ law, freeze seeds, and require the transform price to sit inside the 95% CI (200,000 paths gives half-width ≈0.025 in the reported benchmark). (iv) Factor convergence — recompute the price and hedge as $n$, $2n$, $4n$; the reported price differences fall 4× per doubling of the factor count in the regular-kernel case. (v) Hedge check — compare the GKW hedge with centred finite differences of $C_0$ in $S_0$ and $\nu_0$; halving the step must shrink the gap ~4× (second-order). (vi) fBm sample check — verify $\widehat{\mathbb{E}}|B^H_t|^q$ against $\tfrac{2^{q/2}}{\sqrt\pi}\Gamma(\tfrac{q+1}{2})t^{qH}$ for $q=1,\dots,6$ before trusting any rough-volatility path (arXiv:2108.01999v2). (vii) Equivalence test — compare hedge MSE across step sizes with a prespecified margin (the reported two-one-sided test used a 2% margin giving a 90% ratio interval $[0.99968,1.00758]$).
- **Report prices, hedges and residuals separately.** A matching price with a wrong hedge is not a validation: the mean-variance residual has its own closed form, $\epsilon_h=(1-\rho^2)\sigma^2\int_0^T\mathbb{E}[\nu_t|Q^h_t|^2]dt$, which is zero in the degenerate perfectly-hedgeable limit and must be reported alongside the hedge (arXiv:2609.07169v1). Likewise, an Asian price match at one maturity proves nothing about the wings (arXiv:2409.08377v2).

## Recommended Workflow

1. **Heston semi-analytic engine: European prices, VIX futures, VVIX estimators (S).** Data: `cboe` `options_surface` chain, `federal_reserve` `risk_free_curve`, `eodhd` `corporate_actions` for $q$; `finnhub` quote for $S_0$. Value: unblocks every stochastic-variance workflow in the corpus — it is the benchmark against which rough models are measured, and the four VVIX estimators give an independent handle on $\sigma$. Risk: $\mathrm{VVIX}(\sigma)$ non-monotone and objective-function sensitive, so report the weight-set dispersion rather than one fit (arXiv:2512.19611v1).
2. **Multi-factor Markovian rough-Heston pricer (S–M).** Data: none beyond a calibrated $(\kappa,\theta,\sigma,\rho,H)$; the Cauchy problem is self-contained. Value: a pure-NumPy rough-volatility pricer — fractional Riccati replaced by an $n$-dimensional ODE system with an explicit error bound and $O(n\,n_t)$ cost — needs only `numpy`, satisfying the runtime red line. Risk: wings at small $n$; use $n\ge20$ and cross-check $n$, $2n$, $4n$ (arXiv:1801.10359v3).
3. **Moment-explosion / Fourier-strip guard (S).** Data: model parameters only. Value: computes the explosion time and the lower critical moment that delimit the valid Fourier contour, preventing silently wrong prices in the wing, and directly validates the truncation window used by item 1. Risk: case (B) gives only a lower bound, so treat it as a conservative guard rather than an equality (arXiv:1801.09458v3).
4. **Rough-Volterra simulation harness: Cholesky / Hybrid / rDonsker (M).** Data: `eodhd` OHLCV to calibrate $\xi,\rho,H,\sigma_0$. Value: scenario paths and an fBm moment-quality harness; the Hybrid and rDonsker convolutions are FFT-only and stay in NumPy. Risk: ~10× the path count of classical SV (use $\ge100{,}000$); do not apply turbocharging when $\rho>0$ and always run the three admissibility guards (arXiv:2108.01999v2).
5. **Volterra–Heston Asian pricer via the Riccati–Volterra transform (M).** Data: `cboe` SPX chain to build the forward-variance input (see the `gap` row — no certified variance-swap feed) plus the `risk_free_curve`. Value: discretely monitored geometric Asian prices with no Monte Carlo, and a control variate that cuts the variance of arithmetic-Asian estimates. Risk: needs the forward-variance curve or the $n$-factor lift; rebalancing-frequency sensitivity must be measured, not assumed (arXiv:2609.07169v1).
6. **Short-maturity Asian approximation for LSV / SABR / Heston (S–M).** Data: OHLCV plus `cboe` quotes for the vol-of-vol expansion coefficients. Value: near-zero-cost Asian prices at short $T$ and near ATM, useful as a fast desking/consistency check on items 1 and 5. Risk: asymptotic only — gate it to small $T$ and $|x|$ and never extrapolate to long maturities (arXiv:2409.08377v2).
7. **GKW variance-optimal Asian hedge under the finite-factor Volterra–Heston lift (L).** Data: `cboe` surface (forward variance / $\xi_0$), OHLCV for $S_t$. Value: explicit hedge ratios with a closed-form residual error $(1-\rho^2)\sigma^2\int_0^T\mathbb{E}[\nu_t|Q^h_t|^2]dt$, and a stability test for regression-based hedging. Risk: the largest build here; under singular fractional kernels the factor accuracy does not justify pathwise hedge claims — report no pathwise claim, only the mean-variance residual (arXiv:2609.07169v1).

## Output Format

### Stochastic-Vol Pricing Table
| Instrument | Engine / estimator | Price | MC 95% CI or analytic ref | Moneyness band |
|------------|-------------------|-------|---------------------------|----------------|
| European call | Heston semi-analytic (exact CIR) | ... | ... | ... |
| VIX future F_VIX | CIR transition integral | ... | ... | ... |
| VVIX (log contract) | integral / Taylor / PDE / Newton-in-sigma | ... | ... | ... |
| Asian (discrete) | Volterra-Heston Riccati-Volterra transform | ... | ... | ... |

### Fourier-Strip & Moment Guard
| Parameter set | Lower critical moment (rho<0) | Explosion time T(u) | Valid contour R | Price shift across R |
|---------------|-------------------------------|---------------------|-----------------|----------------------|
| ... | ... | ... | ... | ... |

Report the flag when only the case-(B) lower bound is available, and state the
quadrature nodes vs ODE steps used.

### Validation & Verdict
In order: (i) constant-variance degenerate check against discrete geometric-Asian
Black-Scholes price and delta to machine precision; (ii) contour invariance across
two or three R lines; (iii) exact-CIR Monte Carlo, seeds frozen, transform price
inside the 95% CI; (iv) factor convergence at n, 2n, 4n; (v) turbocharging
admissibility guards when rho>0. Then state the VVIX-vs-smile vol-of-vol dispersion,
the binding lower critical moment, price/hedge errors as a function of moneyness and
maturity, and the mean-variance hedging residual separately from the price.

## References

| arXiv id | title | year |
|---|---|---|
| 2609.07169v1 | Pricing and Hedging of Discretely Monitored Asian Options in the Volterra–Heston Model | 2026 |
| 2512.19611v1 | Heston vol-of-vol and the VVIX | 2025 |
| 2409.08377v2 | Asian options for local-stochastic volatility models in the short-maturity regime | 2024 |
| 2108.01999v2 | On simulation of rough Volterra stochastic volatility models | 2021 |
| 1801.10359v3 | Multi-factor approximation of rough volatility models | 2018 |
| 1801.09458v3 | Moment Explosions in the Rough Heston Model | 2018 |
