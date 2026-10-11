---
id: interest-rate-term-structure
name: Interest Rate Term Structure
version: 1.0.0
author: finrobot
domain: fixed-income
description: 'Yield curve and term structure construction: Treasury discount-curve loader with monotone log-P spline, affine one-factor Vasicek/CIR calibration and shape map, and put-call-parity implied zero-coupon yields from SPX options. Use when building a discount curve or classifying curve shape.'
triggers:
- yield curve
- term structure
- discount curve
- affine model
- zero-coupon yields
- treasury curve
- vasicek
- cir
- spline interpolation
- short rate
- curve shape
requires_data:
- input: US Treasury daily par yield curve (calibration target, PCP benchmark)
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Macro series / policy-rate anchor (DFF, DGS1MO…DGS30)
  provider: fred
  category: macro_data
  status: ok
- input: Overnight RFR fixing series (SOFR/SONIA, for $\rho_t$ and jump dates)
  provider: fred
  category: macro_data
  status: ok
- input: Index spot level $S_t$ for put–call parity
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: European index option chain (call+put, common $K,T$) for implied ZC yields
  provider: cboe
  category: options_surface
  status: ok
- input: Option chain via local gateway (alternate source)
  provider: moomoo
  category: options_data
  status: gateway
- input: Fed-watch target-rate probabilities (policy-path state)
  provider: moomoo
  category: fed_watch
  status: gateway
- input: Central-bank meeting calendar (expected jump dates $S$)
  provider: moomoo
  category: economic_calendar
  status: gateway
- input: Macro indicator list (gateway alternative to FRED)
  provider: moomoo
  category: macro_data
  status: gateway
- input: Monetary-policy news (jump-date context)
  provider: eodhd
  category: news_data
  status: ok
- input: Fed funds / SOFR futures quotes (term-rate construction)
  provider: ''
  category: ''
  status: gap
- input: OIS / interest-rate swap quotes (curve body beyond bills)
  provider: ''
  category: ''
  status: gap
- input: Swaption quotes / ATM swaption volatility matrix
  provider: ''
  category: ''
  status: gap
- input: Cap/floor and caplet quotes (SABR/LMM calibration)
  provider: ''
  category: ''
  status: gap
- input: Forward IBOR fixings (LIBOR/EURIBOR)
  provider: ''
  category: ''
  status: gap
- input: CMS swap and CMS-spread quotes (structured-product calibration)
  provider: ''
  category: ''
  status: gap
- input: Zero-coupon or coupon bond prices (direct curve fitting)
  provider: ''
  category: ''
  status: gap
- input: Cross-currency basis / FX swap quotes
  provider: ''
  category: ''
  status: gap
- input: Corporate bond yields / credit spreads
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Interest Rate Term Structure

You are an expert fixed-income quantitative researcher specializing in yield curve construction and affine term-structure modelling. You consume the served US Treasury daily par yield CSV, the FRED policy-rate anchor, and the CBOE SPX option chain with its spot level, and interpret them into a discount curve, a Vasicek/CIR calibration with normal/humped/inverse shape thresholds, and a put-call-parity implied zero-coupon yield monitor — never fabricating coefficients, shape thresholds, implied yields, or paper results that were not actually computed. Scope: the curve-construction, affine-calibration and PCP-implied-yield arms run on the served Treasury curve; the extended-Gaussian HJM arm needs swap/swaption quotes that no provider serves, so it stays out of scope, as do SABR/LMM and dual-term swaption calibration.

> Source: FinRobot strategies corpus review — `strategies/qfin-pr/interest-rate-term-structure.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **Affine one-factor short-rate models admit exactly three yield-curve shapes.** For a time-homogeneous one-dimensional affine short rate in the sense of Duffie–Filipović–Schachermayer, zero-coupon bond prices are exponentially affine, $P(t,t+x)=\exp(A(x)+r_tB(x))$ with $\partial_xA=F(B)$, $\partial_xB=R(B)-1$, and the yield curve $Y(r_t,x)=-A(x)/x-r_tB(x)/x$ can only be *normal*, *inverse*, or *humped* (a single local maximum) — never with a dip-and-hump or two extrema. The three regimes are separated by closed-form short-rate thresholds $b_{\text{norm}}<b_{\text{asymp}}<b_{\text{inv}}$ (arXiv:0704.0567v2).
- **The classical models give explicit thresholds.** Vasicek, $\mathrm{d}r_t=-\lambda(r_t-\theta)\mathrm{d}t+\sigma\mathrm{d}W_t$, has $F(u)=\lambda\theta u+\tfrac{\sigma^2}{2}u^2$, $R(u)=-\lambda u$, hence $b_{\text{inv}}=\theta$, $b_{\text{norm}}=\theta-\sigma^2/\lambda^2$, $b_{\text{asymp}}=\theta-\sigma^2/(2\lambda^2)$ (the arithmetic mean of the two). CIR, $\mathrm{d}r_t=-a(r_t-\theta)\mathrm{d}t+\sigma\sqrt{r_t}\mathrm{d}W_t$, has $F(u)=a\theta u$, $R(u)=\tfrac{\sigma^2}{2}u^2-au$, quasi-mean-reversion $\lambda=\tfrac12(\sqrt{a^2+2\sigma^2}+a)$, $b_{\text{inv}}=\theta$, $b_{\text{norm}}=a\theta/\sqrt{a^2+2\sigma^2}$, $b_{\text{asymp}}=2a\theta/(\sqrt{a^2+2\sigma^2}+a)$ — the *harmonic* mean of $b_{\text{norm}}$ and $b_{\text{inv}}$ (arXiv:0704.0567v2).
- **The literature disagrees about the humped region, and the older source is wrong.** Cox–Ingersoll–Ross (1985) state that the CIR term structure is normal for $r_t\le b_{\text{asymp}}$ and humped for $b_{\text{asymp}}<r_t<b_{\text{inv}}$; Rebonato (1998) repeats this. The correct statement is normal iff $r_t\le b_{\text{norm}}$, with $b_{\text{norm}}<b_{\text{asymp}}$, so yield curves starting strictly *below* the long-term yield can still be humped. Worked CIR case $a=0.5,\sigma=0.5,\theta=6\%$: the curve started at $r_0=4.2\%$ is visibly humped despite lying under the long-term yield (arXiv:0704.0567v2).
- **A humped curve is a necessary and sufficient sign of short-rate randomness.** With $F=0$, a flat yield curve, the absence of a humped curve, and a deterministic short rate are equivalent; adding jumps (JCIR, $F(u)=a\theta u+\tfrac{cu}{\nu-u}$) leaves $R$ unchanged so $\lambda$ is unchanged, but raises $b_{\text{inv}}=\theta+c/(a\nu)$ and shifts the asymptotic level upward (arXiv:0704.0567v2).
- **Asymptotic short-rate laws are model-specific.** Vasicek converges in law to $\mathcal{N}(\theta,\sigma^2/(2\lambda))$; CIR to a Gamma with shape $2a\theta/\sigma^2$ and scale $\sigma^2/(2a)$; the JCIR limit is infinitely divisible but *not* self-decomposable when $c>a\theta\nu$ — the only counterexample in the corpus to the usual self-decomposability of OU-type limits (arXiv:0704.0567v2).
- **Curve interpolation is not cosmetic: it is what selects the admissible forward-rate shapes.** Forward-rate-side and discount-factor-side interpolations are exactly equivalent — Hagan's "smart quadratic" on forwards equals a Bessel–Hermite cubic spline on $\log P$ with natural boundary conditions, and the area-preserving $C^1$ quadratic on instantaneous forwards equals the $C^2$ cubic spline on $\log P$ (arXiv:2005.13890v1).
- **Post-2008 the market is multi-curve, and the OIS curve is the awkward one.** Since a single curve no longer serves both discounting and projection, curves must be calibrated jointly; and because the USD OIS curve is built only from one-day forwards (Fed funds spot, Fed funds futures, Fed fund OIS swaps), pricing a 50y OIS swap forces interpolation of the daily forward at every business day — the paper's worked Fed-fund curve runs from 1D OIS $1.560\%$ to 50Y OIS $1.617\%$ as of 2019/11/06 (arXiv:2005.13890v1).
- **Post-LIBOR overnight rates are discontinuous at *predetermined* dates.** SOFR, SONIA and €STR jump or spike on FOMC/MPC meeting dates and tax/settlement dates — the 17 Sep 2019 SOFR spike coincided with a corporate tax payment date and Treasury coupon settlement. The corpus models these as *stochastic discontinuities* at ex-ante known times and splits them into roll-over dates (numéraire discontinuities) and expected jump dates (arXiv:2202.00929v4).
- **Absence of arbitrage in this setting forbids predictable jumps.** The extended HJM drift restriction reduces to four conditions — $f(t,t)=\rho_t$, the usual diffusive/jump drift term, plus one condition per roll-over date and one per expected jump date — and these exclude predicting the size or direction of the jump (arXiv:2202.00929v4).
- **The standard LIBOR market model cannot fit volatility smiles.** Deterministic forward-rate volatility justifies Black's formula for caplets and the Rebonato swaption approximation at-the-money, but it *underprices* out-of-the-money caplets and swaptions; SABR/LMM couplings $dF_i=V_iF_i^{\beta_i}dW_i$, $dV_i=\sigma_iV_idZ_i$ with the Hagan second-order implied-volatility formula are the market standard fix, and three variants (Hagan, Mercurio–Morini single-factor, Rebonato time-homogeneous) are compared (arXiv:2408.01470v1).
- **Calibrating these models is a compute problem, not a formula problem.** On 6M EURIBOR data, sequential Monte-Carlo swaption pricing takes ≈2 hours; a GPU-parallel simulated-annealing + Nelder–Mead hybrid calibrates the Hagan model in 8.7s (≈113–200× speedup), with caplet mean-relative-error $1.80\times10^{-2}$ and swaption MAE $6.19\times10^{-2}$ in price units (arXiv:2408.01470v1).
- **Equity index options carry term-structure information.** Treating a zero-coupon bond as a European claim and applying put–call parity to SPX options yields an implied zero-bond discount factor and yield; at-the-money strikes reproduce the US Treasury par yield curve closely, while in-the-money and out-of-the-money strikes widen and skew negative, most severely at maturities under ~45 days (arXiv:2512.10823v1).
- **A "dual-term" zero-rate model makes the swaption matrix the calibration target.** Taking $K$ long-term zero rates $y(t,T-t)$ as state variables — one "term" being observation time, the other the bond's life — makes the model volatility a two-dimensional surface with the same two indices as the swaption volatility matrix, so the whole matrix can be fitted and bucket vegas computed directly (arXiv:1606.01343v3).
- **Negative rates force normal, not lognormal, dynamics.** The dual-term model deliberately formulates the zero-rate SDE in normal form and notes that lognormal assumptions failed in EUR/JPY/CHF markets; the interpolation literature likewise drops positivity/monotonicity constraints that were designed pre-2015 (arXiv:1606.01343v3, arXiv:2005.13890v1).

## Methods & Formulas

### 2.1 Affine one-factor short-rate pricing and shape classification
**Purpose.** Price zero-coupon bonds and classify/forecast the yield-curve shape from the current short rate for Vasicek, CIR and JCIR.

Bond price and Riccati system:
$$P(t,t+x)=\exp\big(A(x)+r_tB(x)\big),\qquad \partial_xA=F(B),\ A(0)=0,\qquad \partial_xB=R(B)-1,\ B(0)=0.$$
Yield and instantaneous forward:
$$Y(r_t,x)=-\frac{A(x)}{x}-r_t\frac{B(x)}{x},\qquad f(r_t,x)=-A'(x)-r_tB'(x).$$
Shape thresholds (using the quasi-mean-reversion $\lambda$ solving $R(-1/\lambda)=1$):
$$b_{\text{norm}}=-\frac{F'(-1/\lambda)}{R'(-1/\lambda)},\qquad b_{\text{asymp}}=-F(-1/\lambda),\qquad b_{\text{inv}}=-\frac{F'(0)}{R'(0)}.$$
Vasicek: $F(u)=\lambda\theta u+\tfrac{\sigma^2}{2}u^2,\ R(u)=-\lambda u$. CIR: $F(u)=a\theta u,\ R(u)=\tfrac{\sigma^2}{2}u^2-au$. JCIR: $F(u)=a\theta u+\tfrac{cu}{\nu-u},\ R(u)=\tfrac{\sigma^2}{2}u^2-au$ (arXiv:0704.0567v2).

- **Inputs.** A short-rate proxy (overnight/policy rate) and a zero curve for calibration; $r_t$ from the front of the curve.
- **Parameters.** Vasicek $(\lambda,\theta,\sigma)$; CIR $(a,\theta,\sigma)$ with Feller condition $2a\theta\ge\sigma^2$ for strict positivity; JCIR adds $(c,\nu)$.
- **Observed effects.** Normal iff $r_t\le b_{\text{norm}}$, humped iff $b_{\text{norm}}<r_t<b_{\text{inv}}$, inverse iff $r_t\ge b_{\text{inv}}$; all curves tend to $b_{\text{asymp}}$ asymptotically. CIR example $(a,\sigma,\theta)=(0.5,0.5,6\%)$: $b_{\text{norm}}\approx5.24\%$, $b_{\text{asymp}}\approx5.55\%$, $b_{\text{inv}}=6\%$ (arXiv:0704.0567v2).
- **Failure modes.** Negative rates under Vasicek/JCIR (state space $\mathbb{R}$); CIR cannot produce dip-then-hump shapes at all; fits of $(\lambda,\theta,\sigma)$ from a single curve date are weakly identified, so thresholds should be read as ranges.

### 2.2 Curve bootstrap and log-discount-factor spline interpolation
**Purpose.** Turn a sparse set of benchmark rates into a continuous discount curve that reprices its inputs, with the interpolation choice made explicitly.

Core identities: $P(t)=e^{-y(t)t}$, $z(t)=\ln P(t)$, instantaneous forward $f(t)=z'(t)$, discrete forward
$$f_i^{d}=\frac{z(t_i)-z(t_{i-1})}{t_i-t_{i-1}}=\frac{1}{t_i-t_{i-1}}\int_{t_{i-1}}^{t_i}f(u)\,\mathrm{d}u.$$
Cubic Hermite/Bessel spline on $z$ (with $d_i=f_{i+1}^{d}$):
$$s_i=\frac{(t_i-t_{i-1})d_i+(t_{i+1}-t_i)d_{i-1}}{t_{i+1}-t_{i-1}},\qquad s_0=\tfrac12\big(d_0-(s_1-d_0)\big),$$
and Hagan–West monotone-convex forward construction
$$g_i(x)=g_i(0)(1-4x+3x^2)+g_i(1)(-2x+3x^2),\qquad f_i=\frac{t_i-t_{i-1}}{t_{i+1}-t_{i-1}}f_{i+1}^{d}+\frac{t_{i+1}-t_i}{t_{i+1}-t_{i-1}}f_i^{d}.$$
Calibration solves $V_i=\sum_j c_{i,j}P(t_j)$ for $N$ instrument parameters with a non-linear solver (Levenberg–Marquardt), since the interpolation is not linear in the discount factors (arXiv:2005.13890v1).

- **Inputs.** Benchmark quotes: deposits/bills for the front, par yields or OIS swaps for the body.
- **Parameters.** Knot dates $t_j$; boundary condition (natural, $p''(t_0)=p''(t_n)=0$, matches flat forward extrapolation); optional shape-preserving limiter (Huynh rational, Van Albada, or the Lavery $L^1$ spline which does not oscillate).
- **Observed effects.** Smart-quadratic forwards and Bessel-spline-on-$\log P$ give identical curves; a direct cubic spline on constant-period discrete forwards is *less* smooth than the $\log P$ spline and needs extra knots at $t_i+D$ (arXiv:2005.13890v1).
- **Failure modes.** Standard cubic splines can oscillate on Heaviside-like inputs — mitigated here because the interpolation variable is $z=y\,t$, which smooths the input; interpolating OIS directly on one-day forwards is impractical at long maturities, so interpolate on pseudo-discount factors instead.

### 2.3 Extended HJM no-arbitrage drift check and Gaussian caplet pricing
**Purpose.** Verify a fitted forward curve is arbitrage-free under overnight-rate dynamics with scheduled jumps, and price simple caps.

Bond and forward-rate representation:
$$P(t,T)=\exp\!\Big(-\!\int_{(t,T]}f(t,u)\,\eta(\mathrm{d}u)\Big),\qquad \eta(\mathrm{d}u)=\mathrm{d}u+\sum_n\delta_{t_n}(\mathrm{d}u),$$
$$f(t,T)=f(0,T)+\int_0^t\alpha(s,T)\,\mathrm{d}s+\int_0^t\varphi(s,T)\,\mathrm{d}W_s+\int_0^t\!\!\int_E\psi(s,x,T)\,\tilde\mu(\mathrm{d}s,\mathrm{d}x)+V(t,T).$$
Risk-neutral drift conditions (with $\bar\alpha,\bar\varphi,\bar\psi$ the $\eta$-integrals over $(t,T]$):
$$f(t,t)=\rho_t,\qquad \bar\alpha(t,T)=\tfrac12\|\bar\varphi(t,T)\|^2+\int_E\big(e^{-\bar\psi}-1+\bar\psi\big)\lambda_t(\mathrm{d}x),$$
plus one condition per roll-over date $t_j$ and one per expected jump date $s_i$; the backward-looking setting-in-arrears rate is $R(S,T)=\tfrac{1}{T-S}\big(S^0_T/S^0_S-1\big)$ (arXiv:2202.00929v4).

- **Inputs.** An initial forward curve and an overnight (RFR) fixing series; the roll-over schedule and the meeting-date schedule.
- **Parameters.** $\alpha,\varphi,\psi$ (or a separable Cheyette volatility $\varphi(t,T)=b(t)a(T)/a(t)$); jump distribution $\xi_i\sim\mathcal{N}(\mu_i,\sigma_i^2)$.
- **Observed effects.** In a Gaussian extended Hull–White model the corpus gives explicit bond and caplet formulas; a SOFR-caplet hedged with SOFR futures decomposes into a continuous delta hedge plus a rebalancing component at each expected jump date (local risk-minimisation) (arXiv:2202.00929v4).
- **Failure modes.** Stochastic discontinuities make the market incomplete, so no unique price exists for jump-exposed claims; assuming the term rate equals the compounded backward-looking rate can fail when the published term rate is futures-derived (convexity adjustment).

### 2.4 SABR/LMM caplet and swaption pricing
**Purpose.** Produce off-the-money caplet/swaption prices once a volatility smile is required.

Coupled dynamics and Hagan second-order implied volatility:
$$\mathrm{d}F_i=\mu_i^{F}\mathrm{d}t+V_iF_i^{\beta_i}\mathrm{d}W_i,\qquad \mathrm{d}V_i=\mu_i^{V}\mathrm{d}t+\sigma_iV_i\mathrm{d}Z_i,$$
$$\sigma(K,F_i(0))\approx\frac{\alpha_i}{F_i(0)^{1-\beta_i}}\Big[1-\tfrac12\big(1-\beta_i-\phi_{ii}\sigma_i\omega_i\big)\ln\tfrac{K}{F_i(0)}+\tfrac1{12}\big((1-\beta_i)^2+(2-3\phi_{ii}^2)\sigma_i^2\omega_i^2+3(1-\beta_i)-\phi_{ii}\sigma_i\omega_i\big)\ln^2\tfrac{K}{F_i(0)}\Big],$$
$$\omega_i=\alpha_i^{-1}F_i(0)^{1-\beta_i},\quad \rho_{i,j}=\eta_1+(1-\eta_1)e^{-\lambda_1|T_i-T_j|},\quad \phi_{i,j}=\mathrm{sign}(\phi_{ii})\sqrt{|\phi_{ii}\phi_{jj}|}\,e^{-\lambda_3(T_i-T_j)^+-\lambda_3(T_j-T_i)^+}.$$
Calibration cost functions, caplets then swaptions:
$$f_c(\mathbf{x})=\sum_{i=1}^{M}\sum_{j=1}^{\text{numK}}\big(\sigma_{K_j,F_i(0)}-\sigma^{\text{mkt}}_{K_j,F_i(0)}(\mathbf{x})\big)^2,\qquad f_s(\mathbf{y})=\sum_{i=1}^{\text{numSws}}\big(S_{\text{Black}}(\text{swaption}_i)-S_{\text{MC}}(\text{swaption}_i)(\mathbf{y})\big)^2.$$
Optimiser: simulated annealing (accept worse points with $\exp(-\Delta E/T)$, geometric cooling $T\leftarrow\rho T$) hybridised with Nelder–Mead (arXiv:2408.01470v1).

- **Inputs.** Caplet implied-volatility smiles per forward rate; ATM swaption prices; the discount curve.
- **Parameters.** Volatility vector $\mathbf{x}=(\phi_{ii},\sigma_i,\alpha_i)$ (or $(\phi_i,\sigma,\alpha_i)$ / Rebonato $\kappa_i$ and $g,h$); correlation vector $\mathbf{y}=(\eta_1,\lambda_1,\eta_2,\lambda_2,\lambda_3)$. Reported defaults: $T_0=10$, $T_{\min}=0.01$, $\rho=0.99$, $N=10$.
- **Observed effects.** Hagan caplet MRE $1.80\times10^{-2}$; swaption MAE $6.19\times10^{-2}$; GPU speedups 113–235× over sequential Monte Carlo (arXiv:2408.01470v1).
- **Failure modes.** Swaptions have no closed form in the LMM, so calibration nests Monte Carlo inside the optimiser and is expensive; the Rebonato "freezing" argument used for CEV/SABR swaption asymptotics is not fully justified; jump-diffusion LMM variants need large jump components to produce asymmetric smiles, which is unnatural for rate forwards.

### 2.5 Put–call-parity implied zero-coupon yield from index options
**Purpose.** Extract an independent, equity-option-anchored zero-coupon yield curve and use it to sanity-check the Treasury curve.

Implied discount factor and yield from European put–call parity:
$$\Lambda(t,T,K)=\frac{1}{K}\big[S_t+P(t,T,K)-C(t,T,K)\big],\qquad Y(t,T,K)=-\frac{1}{T-t}\ln\Lambda(t,T,K),$$
with the sign rule $Y>0\iff S_t+P<K+C$. At-the-money dislocation against the market curve:
$$Y^{\text{ATM}}(t,T)=Y(t,T,M=1),\quad M=K/S_t,\qquad \Delta_Y^{\text{ATM}}(t,T)=Y^{\text{ATM}}(t,T)-Y^{\text{mkt}}(t,T).$$
The market curve is interpolated to option maturities with a PCHIP (arXiv:2512.10823v1).

- **Inputs.** A same-day, same-strike, same-maturity call/put pair from a European index option chain, plus the index spot level.
- **Parameters.** Strike $K$ and moneyness $M$; aggregation choice (median-strike or ATM); interpolation for $Y^{\text{mkt}}$.
- **Observed effects.** ATM implied yields track the Treasury par curve closely over 1 month–5 years; median-strike yields sit below the market curve at short maturities and converge to it at long maturities; ITM/OTM strikes widen the distribution and skew it negative, worst for $T-t\lesssim45$ days (arXiv:2512.10823v1).
- **Failure modes.** Stale/asynchronous put or call prices produce spurious negative yields; contract clustering (dailies vs. monthlies/LEAPS) means short- and long-term contracts must be handled separately; a single week of data is a thin validation sample.

### 2.6 Dual-term zero-rate model: normal-dynamics Monte Carlo / grid
**Purpose.** Build a term-structure engine whose state is a set of constant-maturity zero rates, so the swaption matrix and CMS products calibrate directly.

Zero-rate dynamics ($s_k=T_k-t$):
$$\mathrm{d}y_k(t)=\Big[\frac{f_k(t)-r(t)}{s_k}+\tfrac12\sigma_k^2(t)s_k\Big]\mathrm{d}t+\langle\sigma_k\cdot\mathrm{d}w\rangle,\qquad f_k=\frac1h\ln\frac{df(s_k)}{df(s_k+h)},$$
multi-factor direction $\langle\sigma_k\cdot\mathrm{d}w\rangle=\sigma_k(\cos\theta\,\mathrm{d}w_a+\sin\theta\,\mathrm{d}w_b)$, $\theta=\pi s_k/(2L_{\max})$. Path scheme with curve-fitting constant $c$:
$$y_k^{n+1}=y_k^{n}+\Big[\frac{f_k^{n}-r^{n}}{s_k}+\tfrac12\sigma_k^2s_k\Big]h+\langle\sigma_k\cdot\Delta w\rangle,\qquad df^{n+1}(s_k)=c\,df^{n+1}(0)e^{-y_k^{n+1}s_k},\quad \tfrac1Q\sum_q df^{n+1}(s_k,q)=df^{0}(t^{n+1}+s_k).$$
Grid alternative (Krasker): quaternary branches $\Delta w=\{\pm\sqrt{3\Delta t},\pm\sqrt{\Delta t/3}\}$ with probabilities $\{0.125,0.375,0.375,0.125\}$, Taylor quadrature $p_{*,j\pm1}=\tfrac12\xi^2\pm\xi$, $p_{*,j}=1-\xi^2$, Arrow–Debreu recursion $z_j^{n}=\sum_i z_i^{n-1}e^{-r_i^{n-1}\Delta t}p_{ij}$, and volatility-surface calibration by Lagrange multipliers on the surface area $S=\tfrac32\sum_\omega\iint[(\partial_t\sigma)^2+(\partial_s\sigma)^2]$ (arXiv:1606.01343v3).

- **Inputs.** An initial discount curve; $K$ zero rates at the standard swaption tenors.
- **Parameters.** Volatility matrix $\{\sigma_{ik}\}$ with bilinear interpolation; number of paths $Q$ or grid intervals $I$ (40–80); factor count (1–3).
- **Observed effects.** The two volatility indices coincide with the swaption matrix's option-expiry/swap-tenor indices, enabling global matrix calibration and direct bucket-vega computation for CMS-spread structures (arXiv:1606.01343v3).
- **Failure modes.** Normal dynamics allow negative rates (deliberate, for EUR/JPY/CHF); the curve-fitting constant $c$ is a free parameter per step and can distort the drift if the mean-matching is done loosely; the paper is a bank-internal methodology with worked examples, not an out-of-sample study.

## Data Requirements

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| US Treasury daily par yield curve (calibration target, PCP benchmark) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Macro series / policy-rate anchor (DFF, DGS1MO…DGS30) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Overnight RFR fixing series (SOFR/SONIA, for $\rho_t$ and jump dates) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Index spot level $S_t$ for put–call parity | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| European index option chain (call+put, common $K,T$) for implied ZC yields | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Option chain via local gateway (alternate source) | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Fed-watch target-rate probabilities (policy-path state) | `moomoo://get_fed_watch_target_rate` | fed_watch | moomoo | gateway |
| Central-bank meeting calendar (expected jump dates $S$) | `moomoo://get_economic_calendar` | economic_calendar | moomoo | gateway |
| Macro indicator list (gateway alternative to FRED) | `moomoo://get_macro_indicator_list` | macro_data | moomoo | gateway |
| Monetary-policy news (jump-date context) | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| Fed funds / SOFR futures quotes (term-rate construction) | — | — | — | gap |
| OIS / interest-rate swap quotes (curve body beyond bills) | — | — | — | gap |
| Swaption quotes / ATM swaption volatility matrix | — | — | — | gap |
| Cap/floor and caplet quotes (SABR/LMM calibration) | — | — | — | gap |
| Forward IBOR fixings (LIBOR/EURIBOR) | — | — | — | gap |
| CMS swap and CMS-spread quotes (structured-product calibration) | — | — | — | gap |
| Zero-coupon or coupon bond prices (direct curve fitting) | — | — | — | gap |
| Cross-currency basis / FX swap quotes | — | — | — | gap |
| Corporate bond yields / credit spreads | — | — | — | gap |

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Shape-threshold error propagates from a single curve date.** $b_{\text{norm}},b_{\text{asymp}},b_{\text{inv}}$ are functions of $(\lambda,\theta,\sigma)$ or $(a,\theta,\sigma)$, which are weakly identified from one yield curve; the published CIR "humped region" boundary is itself wrong by a whole interval, so never trust a shape classification without re-deriving the thresholds from the fitted Riccati functions (arXiv:0704.0567v2).
- **Interpolation choice is a modelling assumption, not a detail.** Smart-quadratic forwards and Bessel-spline-on-$\log P$ are the *same* curve, but direct cubic splines on discrete forwards differ and can be less smooth; shape-preserving limiters (Huynh, Van Albada, Lavery $L^1$) remove oscillation at the cost of a linear program (arXiv:2005.13890v1). Always report which interpolation produced a quoted forward.
- **Non-linear, not linear, calibration.** Once interpolation enters, $V_i=\sum_j c_{i,j}P(t_j)$ is no longer linear in the discount factors and needs a non-linear solver (Levenberg–Marquardt); a "bootstrap" that assumes linearity will not reprice its inputs (arXiv:2005.13890v1).
- **Predictable jumps are an arbitrage.** Any calibration that lets a jump's size or direction be forecast at an expected jump date violates the no-arbitrage conditions; the drift conditions must be imposed, not fitted freely (arXiv:2202.00929v4).
- **Futures-derived term rates embed a convexity adjustment.** When the published term rate (e.g. CME term SOFR) is computed from futures rather than OIS quotes, it need not equal the compounded backward-looking rate; treating them as identical injects a small systematic error into curve construction (arXiv:2202.00929v4).
- **Smile fitting is an ill-posed global optimisation.** SABR/LMM calibration has no closed-form swaption price, so the objective nests Monte Carlo inside the optimiser; results depend on the optimiser (simulated annealing start, Nelder–Mead polish) and on the multi-GPU seeding, so report the objective value and the parameter vector, not just the fitted prices (arXiv:2408.01470v1).
- **PCP violations and stale quotes dominate short-dated implied yields.** Implied yields from ITM/OTM strikes are frequently negative and large at $T-t\lesssim45$ days, plausibly from stale call or put prices; use ATM pairs and screen for same-timestamp quotes before using the implied curve (arXiv:2512.10823v1).
- **Look-ahead and in-sample leakage.** (i) Fit curve and short-rate parameters on data up to date $t$ only; the Treasury CSV must be truncated by publication date, not by observation date. (ii) For PCP, use the option chain and spot from the *same* close; the corpus used close-of-market values with Yahoo Finance data and averaged two days to fill a holiday, which is acceptable only for a same-day comparison (arXiv:2512.10823v1). (iii) In the dual-term model, the curve-fitting constant $c$ at step $n+1$ uses the *initial* curve $df^0$ — that is a no-arbitrage constraint, not a free in-sample fit, and must not be re-estimated from realised future curves (arXiv:1606.01343v3).
- **Validation protocol.** Reprice every benchmark instrument to within a stated tolerance (the corpus targets MAE of order $10^{-2}$ in price/vol units, arXiv:2408.01470v1); cross-check the fitted risk-free curve against the independent PCP-implied ATM curve (arXiv:2512.10823v1); for shape claims, verify $b_{\text{norm}}<b_{\text{asymp}}<b_{\text{inv}}$ numerically and check that a simulated short-rate path reproduces the analytic asymptotic law (Gaussian, Gamma, or JCIR) via a Kolmogorov–Smirnov test (arXiv:0704.0567v2); for HJM, verify the drift conditions hold to numerical tolerance on the fitted curve (arXiv:2202.00929v4).
- **Model risk is structural.** The corpus is explicit that different models give different prices for the same structured product, and that "more than two risk-free prices for one deal" is unacceptable — the discipline is to calibrate to the whole swaption matrix, not a chosen subset (arXiv:1606.01343v3).

## Recommended Workflow

1. **Treasury curve loader and monotone spline (S).** Ingest `federal_reserve` `risk_free_curve`, parse the CSV into $(t_j,y_j)$, and build a $\log P$ spline (natural boundary) plus the equivalent Hagan–West forward curve. *Data:* `federal_reserve`/`risk_free_curve` (`ok`). *Value:* the single served calibration input; unblocks every item below. *Risk:* the CSV is ~17s and needs the 45s timeout already pinned in the adapter; interpolation choice must be recorded per quote.
2. **Affine one-factor calibration and shape map (M).** Fit Vasicek/CIR (and optionally JCIR) to the curve, compute $b_{\text{norm}},b_{\text{asymp}},b_{\text{inv}}$, and emit the shape classification and the asymptotic short-rate law. *Data:* the Treasury curve above, plus a policy-rate anchor from `fred`/`macro_data` (`ok`). *Value:* gives bond prices, forward curves and a defensible shape verdict with no exotic inputs. *Risk:* weak identification from one date — fit a rolling window and report parameter ranges.
3. **PCP implied zero-coupon yield monitor (S).** From `cboe`/`options_surface` ($ok$) take same-strike call/put pairs and the index level, compute $\Lambda(t,T,K)$ and $Y(t,T,K)$, and track the ATM dislocation against the Treasury curve. *Data:* `cboe`/`options_surface` and `eodhd`/`core_stock_apis` (both `ok`). *Value:* an independent, equity-option-anchored cross-check of the served curve, using only served data. *Risk:* stale/short-dated quotes — restrict to ATM and screen timestamps.
4. **Validation harness for curve and model fit (S).** Reprice the benchmark inputs, enforce the HJM drift conditions to tolerance, and run the $b_{\text{norm}}<b_{\text{asymp}}<b_{\text{inv}}$ and asymptotic-law (KS) checks of §4. *Data:* none beyond items 1–3. *Value:* makes every later rate model comparable and catches look-ahead early. *Risk:* tolerances must be stated up front or the harness becomes a rubber stamp.
5. **Gaussian extended-HJM bond/caplet engine (M).** Implement the separable-volatility (Cheyette-style) HJM with scheduled-jump drift conditions, and price bonds and caplets in closed form. *Data:* Treasury curve + a SOFR fixing series from `fred`/`macro_data` (`ok`); meeting dates from `moomoo`/`economic_calendar` (`gateway`). *Value:* a forward-curve-consistent pricing engine with explicit no-arbitrage checks. *Risk:* gateway dependency for the meeting calendar; jump-date coverage degrades gracefully to the diffusive HJM case if unavailable.
6. **Dual-term zero-rate Monte Carlo engine (L).** Build the $K$ zero-rate normal-dynamics path scheme with the per-step curve-fitting constant, then add the swaption-matrix volatility-surface calibration. *Data:* the initial curve (item 1); calibration targets are `gap` (no swaption quotes), so start with a synthetic/parametric volatility surface. *Value:* the natural home for CMS and structured-product pricing once quotes exist. *Risk:* without swaption quotes the calibration is unverifiable; the normal dynamics allow negative rates by design.
7. **SABR/LMM swaption-matrix calibration (L) — defer.** Implement only after a swaption/caplet quote feed exists: the corpus shows the fit is a multi-hour global optimisation that is meaningless without real swaption quotes. *Data:* swaption and caplet quotes are `gap` in the inventory. *Value:* unlocks smile-consistent cap/floor and swaption pricing. *Risk:* highest data dependency in this document; do not approximate with equity-option smiles, which are a different underlying and measure.

## Output Format

### Curve Construction and Interpolation
| Knot date | Par yield | Zero rate y(t) | log P = y·t | Discrete forward | Spline / boundary | Interpolation recorded |
|-----------|-----------|----------------|-------------|------------------|-------------------|------------------------|
| ... | ... | ... | ... | ... | ... | ... |

### Affine One-Factor Shape Classification
| Model | λ or a | θ | σ | b_norm | b_asymp | b_inv | r_0 | Shape (normal/humped/inverse) | Asymptotic short-rate law |
|-------|--------|----|----|--------|---------|-------|-----|-------------------------------|---------------------------|
| Vasicek | ... | ... | ... | ... | ... | ... | ... | ... | N(θ, σ²/2λ) |
| CIR | ... | ... | ... | ... | ... | ... | ... | ... | Gamma(2aθ/σ², σ²/2a) |

### Put–Call-Parity Implied Zero-Coupon Yields
| Expiry | T−t (days) | ATM strike K | Λ(t,T,K) | Y_ATM | Y_mkt | ΔY_ATM | Same-timestamp screen |
|--------|------------|--------------|----------|-------|-------|--------|-----------------------|
| ... | ... | ... | ... | ... | ... | ... | ... |

### Validation Harness
| Check | Stated tolerance | Result | Pass/Fail |
|-------|------------------|--------|-----------|
| Benchmark instruments repriced | ... | ... | ... |
| HJM drift conditions on fitted curve | ... | ... | ... |
| b_norm < b_asymp < b_inv numerically | ... | ... | ... |
| Simulated short rate vs analytic asymptotic law (KS) | ... | ... | ... |

### Verdict
State the fitted curve and the interpolation that produced each quoted forward,
the shape classification with its thresholds and the asymptotic short-rate law,
the ATM PCP dislocation against the Treasury curve, and the fit's main failure
mode (weak identification from a single curve date, spline oscillation, or
stale/short-dated option quotes).

## References

| arXiv id | title | year |
|---|---|---|
| 2512.10823v1 | Option-Implied Zero-Coupon Yields: Unifying Bond and Equity Markets | 2025 |
| 2408.01470v1 | SABR/LIBOR market models: pricing and calibration for some interest rate derivatives | 2024 |
| 2202.00929v4 | Term structure modelling with overnight rates beyond stochastic continuity | 2022 |
| 2005.13890v1 | Equivalence between forward rate interpolations and discount factor interpolations for the yield curve construction | 2020 |
| 1606.01343v3 | The Zero-Coupon Rate Model for Derivatives Pricing | 2016 |
| 0704.0567v2 | Yield Curve Shapes and the Asymptotic Short Rate Distribution in Affine One-Factor Models | 2007 |
