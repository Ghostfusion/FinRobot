# Numerical Pricing Methods — learnings from the q-fin.PR corpus
`394` of 2274 corpus papers matched this category (`392` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **MC cost is set by the discretisation rate; the multilevel decomposition converts a nested estimator from $O(\varepsilon^{-4})$ to $O(\varepsilon^{-2})$.** In rough Bergomi the squared VIX, $(\mathrm{VIX}_T)^2=\frac1\Delta\int_T^{T+\Delta}e^{X_T^u}du$, is a one-dimensional integral of the exponential of a non-Markovian Gaussian process and cannot be sampled exactly. A plain MC estimator on a right-point rectangle rule costs $O(\varepsilon^{-4})$ at MSE $\le\varepsilon^2$; the *same* rule under MLMC costs $O(\ln^2\varepsilon\,\varepsilon^{-2})$; a trapezoidal rule under MLMC reaches $O(\varepsilon^{-2})$ (arXiv:2105.05356v3).
- **Strong and weak rates are scheme-dependent, and the MLMC sample allocation follows from them.** Rectangle strong error is $O(1/n)$ *independently of* the Hurst index $H$; trapezoidal is $O(n^{-(1+H)})$; for market-typical $H\approx0.1$ the two are numerically close (arXiv:2105.05356v3).
- **Control variates built from the lognormal functional of the discretisation have closed-form (Black–Scholes) prices.** Taking the CV as the exponential of the arithmetic mean of the discretised state makes it lognormal with explicit $\mu_n,\sigma_n$, so its expectation is a Black–Scholes call/put (arXiv:2105.05356v3).
- **Deterministic quadrature can beat MC decisively — but only after the integrand is smoothed.** A root-finding plus one-dimensional preintegration *numerical smoothing* step makes the residual integrand $C^\infty$; ASGQ then needs $O(\mathrm{TOL}^{-1})$ work against MC's $O(\mathrm{TOL}^{-3})$ (arXiv:2111.01874v2). This is the corpus' central disagreement with the MC-first view: quadrature wins on complexity only once the payoff kink/jump is removed, otherwise its convergence is regularity-limited.
- **Smoothing is provably anisotropic, and that is what makes high dimension tractable.** The $p$-th derivative of the residual function in the Haar/Brownian-bridge coefficients decays as $O\!\left(2^{-\sum_j n_j/2}\right)$ (arXiv:2111.01874v2).
- **A continuously differentiable Heston characteristic function removes branch-cut instability and yields closed-form error bounds.** The $\zeta$-based form is stable at large frequency; truncation error $\propto e^{-\pi DL/N}$, discretisation error $O(N^{-m})$ with $m\ge2$ — the first explicit bound of its kind for an FFT convolution method in Heston (arXiv:2512.05326v1).
- **Working on the log-stock domain (convolution) instead of log-strike (Carr–Madan) removes damping-parameter tuning and boundary artifacts.** CFFT-II priced three strikes in 0.124 ms at N=2000 against 0.155 ms, errors $5.9\times10^{-5}$, $2.6\times10^{-4}$, $1.4\times10^{-4}$ shrinking to $4.6\times10^{-6}$, $1.6\times10^{-5}$, $4.7\times10^{-6}$ at N=8000 (arXiv:2512.05326v1).
- **The COS method's $N^d$ coefficient tensor can be compressed by a tensor-train (TT) approximation of the sampled characteristic function.** COS–TT–CHF compresses $\varphi_X$ by TT-cross and maps cores to COS coefficients, so contraction costs $O(dNr^2)$ instead of $O(N^d)$. The gain is dimensional, not universal: *slower* than direct COS at $d=2$, faster from $d=4$, tested to $d=30$ (GBM) and $d=20$ (VG, NIG, common-Heston) (arXiv:2608.17636v1).
- **LSMC improves when the asset direction is resolved by a conditional PDE/FFT step and only the variance state is regressed.** Bermudan puts under the Gatheral double mean-reverting model: relative errors 0.019–7.459 % (hybrid) against 0.344–8.645 % (plain LSMC) at 20 000 paths, the gap widest at the at-the-money strike and low path counts (arXiv:2606.11237v1).
- **Explicit finite differences with ghost (fictitious) points at an off-grid barrier are unstable, and no time step saves them.** The ghost interpolation replaces the intended Dirichlet condition and its stability threshold tightens without bound as the node approaches the barrier; L-stable TR-BDF2 damps the oscillation, A-stable Crank–Nicolson leaves a localised one (arXiv:2308.04629v2).
- **Data-honest cross-check.** Every mechanism above is a *pricing kernel*, not a strategy: the corpus supplies no credit/CDS feed, no swap or swaption data, no bond prices, no futures/commodity and no intraday/order-book feed, so credit- and rates-flavoured PDE work is out of reach of the current data layer; the implementable core is equity/volatility pricing from spot, rates, dividends and an option surface.

## 2. Implementable formulas & algorithms

The runtime target is pure NumPy: `numpy.fft` for every transform below, `numpy.linalg.cholesky` for correlated sampling, `numpy.polynomial.legendre.leggauss`/`laggauss` for quadrature, and `numpy.random` for normals and the randomisations QMC needs. Two paper ingredients are *not* in NumPy and must be re-implemented or dropped: the hypergeometric covariance evaluation `scipy.special.hyp2f1` used for the rough-Bergomi grid (arXiv:2105.05356v3), and a Sobol' generator (scipy's `qmc`), which the QMC references in arXiv:2608.17636v1 rely on.

### 2.1 Multilevel Monte Carlo (Giles) for a discretised path functional
**Purpose.** Estimate $\mathbb{E}[\phi(\text{VIX}^2_T)]$ (or any discretised functional) to MSE $\le\varepsilon^2$ at optimal cost by telescoping over refinement levels.

Telescoping identity and estimator, with $n_\ell=n_0 2^\ell$ and independent samples per level:
$$\mathbb{E}[P_L]=\mathbb{E}[P_0]+\sum_{\ell=1}^{L}\mathbb{E}\!\left[P_\ell-P_{\ell-1}\right],
\qquad
\hat P=\frac1{M_0}\sum_{m=1}^{M_0}P_0^{(0,m)}+\sum_{\ell=1}^{L}\frac1{M_\ell}\sum_{m=1}^{M_\ell}\!\left(P_\ell^{(\ell,m)}-P_{\ell-1}^{(\ell,m)}\right)$$
with variance $\operatorname{Var}\hat P=\sum_\ell V_\ell/M_\ell$, $V_\ell=\operatorname{Var}(P_\ell-P_{\ell-1})$, and cost $C_\ell=O(n_\ell^2)$. The optimal allocation $M_\ell\propto\sqrt{V_\ell/C_\ell}$ specialises, for the two schemes, to
$$M_{\ell,R}=M_{0,R}\,2^{-2\ell}\quad(\text{rectangle}),\qquad
M_{\ell,T}=M_{0,T}\,2^{-(2+H)\ell}\quad(\text{trapezoidal}).$$
Resulting costs for MSE $\le\varepsilon^2$: plain MC rectangle $O(\varepsilon^{-4})$, plain MC trapezoidal $O(\varepsilon^{-2(1+1/(1+H))})$, MLMC rectangle $O(\ln^2(\varepsilon)\,\varepsilon^{-2})$, MLMC trapezoidal $O(\varepsilon^{-2})$ (arXiv:2105.05356v3).

**Inputs.** A discretisable SDE plus a payoff; Gaussian draws; a Cholesky factor of the level covariance.
**Parameters.** $n_0$ (coarsest steps), $L$ levels, $M_0$ base sample size; $H$ (via $V_\ell$); window $\Delta$. Reference settings used: $n_0=6$ (rectangle) / $n_0=3$ (trapezoidal), $H=0.1$, $\eta=0.5$, $T=0.5$, $X_0=\ln 0.235^2$.
**Observed effects.** Measured slopes: $-\tfrac12$ (MC rectangle), $-1$ (both MLMC variants); reference VIX call $0.0298840\pm3\times10^{-7}$ for $\Delta=\tfrac1{12}$ and $0.0196369\pm4\times10^{-7}$ for $\Delta=1$ (arXiv:2105.05356v3).
**Failure modes.** The $O(n^2)$ Cholesky of a non-stationary correlated vector dominates per-sample cost and circulant embedding does not apply (the increment process is not stationary); a small $H$ makes the trapezoidal weak rate $n^{-(1+H)}$ slow, so $L$ grows; MLMC needs a *known* strong-error exponent to set the ladder.

### 2.2 Least-squares Monte Carlo with a conditional Fourier/PDE step (Bermudan)
**Purpose.** Price early-exercise options under a multi-factor stochastic-volatility model by conditioning on the simulated variance path, reducing the asset problem to one dimension, and regressing only the residual variance dependence.

Bermudan recursion $C_n(s,v,w)=e^{-r\Delta t_n}\mathbb{E}\!\left[U_{n+1}\right]$, $U_n=\max(h_n,C_n)$. After conditioning, the one-step continuation has the Gaussian representation
$$u(t,y)=\mathbb{E}_\xi\!\left[G\!\left(y+Z_n+I_n(t)+\sqrt{B_n(t)}\,\xi,\;v_{t_{n+1}},v'_{t_{n+1}}\right)\right],\quad \xi\sim\mathcal N(0,1),$$
with $I_n(t)=\int_t^{t_{n+1}}\!\!\left(r-\tfrac12 v_s\right)ds$ and $B_n(t)=\int_t^{t_{n+1}}\!\!\sigma_\perp^2 v_s\,ds$. The asset Brownian driver is projected onto the two variance drivers,
$$dW^{(1)}=\beta_2\,dW^{(2)}+\beta_3\,dW^{(3)}+\sigma_\perp\,dB^\perp,\quad
\beta_2=\frac{\rho_{12}-\rho_{13}\rho_{23}}{1-\rho_{23}^2},\;\;
\beta_3=\frac{\rho_{13}-\rho_{12}\rho_{23}}{1-\rho_{23}^2},\;\;
\sigma_\perp^2=\frac{1-\rho_{12}^2-\rho_{13}^2-\rho_{23}^2+2\rho_{12}\rho_{13}\rho_{23}}{1-\rho_{23}^2}.$$
The conditional step is propagated by FFT on the log-price grid,
$$\mathcal F u^{j,n}(\omega)=\mathcal F g^j_{n+1}(\omega)\exp\!\left(i\omega Z_n^j+i\omega I_n^j-\tfrac12\omega^2 B_n^j\right),$$
and the outer regression solves $a_n^N(s_i)=\left[A_n^N\right]_R^{-1}b_n^N(s_i)$ on a *volatility-only* basis, with the truncated inverse $\left[A\right]_R^{-1}=A^{-1}$ if $\|A^{-1}\|\le R$ and $0$ otherwise (arXiv:2606.11237v1).

**Inputs.** Simulated variance paths ($v,v'$), a uniform log-price grid, a bounded volatility basis.
**Parameters.** GDMR test set: $\kappa_1=5.5$, $\kappa_2=0.1$, $\theta=0.078$, $\xi_1=2.689$, $\xi_2=0.502$, $\delta_1=\delta_2=0.94$, $\rho_{12}=-0.982$, $\rho_{13}=-0.727$, $\rho_{23}=0.590$; $N_S=301$ grid points, 12 exercise dates, volatility truncation quantile $q_v=0.999$, cubic volatility basis, $\mathrm{CEV}$ exponents $\delta\in[\tfrac12,1]$.
**Observed effects.** 20 000 paths: relative errors 0.344–8.645 % (LSMC) vs 0.019–7.459 % (hybrid); ATM at 48 Euler steps: 1.105–25.948 % vs 0.088–11.118 % (arXiv:2606.11237v1).
**Failure modes.** Requires the one-way coupling (variance dynamics must not depend on $S$) and a bounded, invertible Gram matrix — hence the truncated inverse; extension to the general case must not pre-shift the terminal grid *and* keep $i\omega Z_n$ in the multiplier (double-counting the shift).

### 2.3 Characteristic-function pricing by convolution-FFT
**Purpose.** Price many European strikes quickly from a closed-form characteristic function, with *analytical* error control and no damping parameter to tune.

Differentiable Heston joint characteristic function and its increment kernel:
$$\phi_i(p,q)=\exp\!\Big(ip(x+r\tau)+iq(v+a\tau)+\tfrac{\gamma+\lambda}{\sigma^2}(1-\zeta)v-\tfrac{\gamma-\lambda}{\sigma^2}a\tau+\tfrac{2a}{\sigma^2}\ln\zeta\Big),$$
$$\gamma=\sqrt{\sigma^2(p^2-2ic_ip)+(b_i-i\sigma\rho p)^2},\quad
\lambda=b_i-i\sigma\rho p-i\sigma^2 q,\quad
\zeta=\frac{2\gamma}{\gamma+\lambda+(\gamma-\lambda)e^{-\gamma\tau}} .$$
With $\psi_i(p)=\mathcal F[\varphi_i(-y)](p)$ the probabilities are recovered by Fourier inversion and the price by
$$P_i(x)=\mathcal F^{-1}\!\left[\mathcal F[\delta(x)](p)\,\psi_i(p)\right],\qquad
C(S,K,v,t)=S\,P_1-Ke^{-r\tau}P_2 .$$
The convolution-FFT error bound is
$$|E-\tilde E|\le \epsilon_1 e^{-\pi D\,L N}+\epsilon_2 N^{-m},\qquad m\ge 2,\qquad D=\tfrac{2a}{\sigma^2}(v+a\tau)>0,$$
i.e. exponential truncation decay and at least second-order discretisation; boundary error is controlled by damping (exponent $\alpha<0$ in CFFT-II) plus a linear or exponential shift $h(x)=Ax+B$ / $Ae^{x}+B$ (arXiv:2512.05326v1).

**Inputs.** Model parameters and a terminal characteristic function; a log-price grid; a strike (or strike vector).
**Parameters.** Test set $r=0.03$, $v=0.1$, $\Lambda=1$, $\rho=-0.8$, $\kappa=3$, $\theta=0.1$, $\sigma=0.25$, $T=1$; grid $L=10$, $N=2000$–$8000$, damping $\alpha=-2$; Feller $2\kappa\theta\ge\sigma^2$ keeps $V_t>0$.
**Observed effects.** CFFT-II 0.124 ms vs FFT 0.155 ms at $N=2000$; errors $\sim10^{-4}$ falling to $\sim10^{-5}$ at $N=8000$ (arXiv:2512.05326v1).
**Failure modes.** The classical Heston $\log g$ form suffers branch-cut/grazing-phase discontinuities that destroy the integrand; damping requires the $(\alpha+1)$-th moment of $S_t$ to be finite; shifting by a linear function kinks the call payoff at the money (hence the exponential shift for CFFT-II).

### 2.4 COS density expansion with a tensor-train coefficient tensor
**Purpose.** Recover the density from the characteristic function and price many strikes from one coefficient set; compress the multi-asset coefficient tensor so cost is no longer $O(N^d)$.

One-dimensional COS reconstruction of the basket density on $[a_H,b_H]$:
$$u_n=\frac{n\pi}{b_H-a_H},\qquad
F_n=\frac{2}{b_H-a_H}\operatorname{Re}\!\left[\varphi_H(u_n)e^{-iu_na_H}\right],\qquad
f_H(h)\approx \sum_{n=0}^{N_H-1}\!{}'\,F_n\cos\!\left(n\pi\frac{h-a_H}{b_H-a_H}\right),$$
with prime halving the $n=0$ term. Prefix integrals $L_0(K)=\int_{a_H}^{K}\!f_H$, $L_1(K)=\int_{a_H}^{K}\!hf_H$, $T_0=L_0(b_H)$, $T_1=L_1(b_H)$ give $C(K)\approx e^{-rT}[(T_1-L_1(K))-K(T_0-L_0(K))]$ and $P(K)\approx e^{-rT}[KL_0(K)-L_1(K)]$. The truncation box is cumulant based, $a_m=\mu_m-L_{tr}\sqrt{\Sigma_{mm}}$, $b_m=\mu_m+L_{tr}\sqrt{\Sigma_{mm}}$. Low-rank format and contraction:
$$A[i_1,\dots,i_d]=G_1(i_1)G_2(i_2)\cdots G_d(i_d),\qquad
B_m(k)=\sum_{j=1}^{M_m}G_m(j)M_m[j,k],$$
$$Q^{>}_{\min,D}(y)\approx\prod_{m=1}^{d}\left(\sum_{k_m=0}^{N_m-1}R_m(y;k_m)B_m(k_m)\right),\qquad
C_{\min}(K)=e^{-rT}\!\int_K^{\infty}\!Q^{>}_{\min}(y)\,dy,$$
so a rectangle probability contracts in $O(dNr^2)$ instead of $O(N^d)$ (arXiv:2608.17636v1).

**Inputs.** A pointwise-evaluable joint characteristic function $\varphi_X(\omega)=\mathbb{E}[e^{i\omega^\top X_T}]$; a frequency tensor grid.
**Parameters.** TT-cross tolerance and rank cap (16 in the reported tests); frequency half-widths $W_m$ and quadrature sizes $M_m$; $N_m$ COS orders; reported families GBM, VG, NIG, common-Heston.
**Observed effects.** Crossover against direct COS at $d=4$ (slower at $d=2$); faster than the QMC common-Heston reference from $d=2$; tests to $d=30$ (GBM) and $d=20$ (VG/NIG/Heston); component Delta leaves TT ranks unchanged, component Vega needs rounding (arXiv:2608.17636v1).
**Failure modes.** Inadequate frequency resolution prevents an accurate TT approximation of the characteristic-function tensor; inexact tt-cross recovery breaks put–call parity and the recovered mass; the "min" payoff is non-separable until rewritten as a tail integral.

### 2.5 Explicit finite differences: CFL stability and ghost-point barriers
**Purpose.** Solve the low-dimensional pricing PDE (Black–Scholes, local vol, Heston) for path-dependent contracts such as one-touch/barrier options.

Black–Scholes PDE $\partial_tV+\tfrac12\sigma^2S^2\partial_{SS}V+(r-q)S\partial_SV-rV=0$, discretised by the explicit Euler step
$$V_i^{k+1}=A_{i,i-1}V_{i-1}^k+(1+A_{i,i})V_i^k+A_{i,i+1}V_{i+1}^k,$$
with the standard condition $\delta t\!\left(r_k+\dfrac{2\sigma_k^2S_i^2}{\delta S^2}\right)\le1$. Enforcing an off-grid barrier $L^+$ with a fictitious point via linear interpolation yields the tightened bound
$$\delta t\;\le\;\frac{4\,\delta S^2}{\sigma^2 S_{u-1}^2\left(3+\dfrac{\delta S}{L^+-S_{u-1}}\right)} .$$
**Inputs.** A PDE on a uniform grid, boundary/terminal conditions, off-grid barrier level.
**Parameters.** $M$ space steps, $\delta S$, $\delta t$; $r,q,\sigma$; barrier $L^+$; scheme (explicit, Crank–Nicolson, TR-BDF2).
**Observed effects.** With the barrier at $L^+$ (on-grid) the usual CFL threshold holds; with the ghost point the divergence threshold tracks the formula above and grows as $S_{u-1}\to L^+$ (e.g. for $S_{\max}=13782$, theoretical 3370 vs actual 3322 time steps). TR-BDF2 removes the oscillation; Crank–Nicolson leaves a narrow one (arXiv:2308.04629v2).
**Failure modes.** As $\varepsilon=L^+-S_{u-1}\to0$ the explicit scheme is unstable for *any* $\delta t$; placing the barrier exactly on the grid is *worse* (time-step restriction in $\varepsilon^2$ rather than $\varepsilon$); smooth grid deformation can produce near-coincident nodes that degrade accuracy.

### 2.6 Numerical smoothing + adaptive sparse-grid / randomised QMC
**Purpose.** Make a non-smooth payoff (digital, barrier, early-exercise) integrable enough that deterministic quadrature converges spectrally.

Choose a smoothing direction $v\in\mathbb R^d$, $\|v\|=1$, solving $\min_v\operatorname{Var}\!\left[\mathbb{E}[H_v(Z_v,w)\mid w]\right]$; project the coarsest Brownian factors $Y=AZ_1$, locate the discontinuity $y_{1\ast}$ by Newton on $P(y_{1\ast})=\phi(X^{\Delta t}(T))=0$, then preintegrate one dimension (Laguerre quadrature). The resulting integrand is smooth with anisotropy $\partial^{p}H_N/\partial z_{n_1,k_1}\cdots\partial z_{n_p,k_p}=O\!\left(2^{-\sum_j n_j/2}\right)$, and the error splits as
$$E_{\text{total}}=\underbrace{O(\Delta t)}_{\text{weak}}+\underbrace{O(M_{\mathrm{Lag}}^{-s/2})+O(\mathrm{TOL}_{\mathrm{Newton}})}_{\text{smoothing}}+\underbrace{O(M_{\mathrm{ASGQ}}^{-p/2})}_{\text{quadrature}},$$
with rQMC error $O\!\left(M_{\mathrm{rQMC}}^{-1/2+\delta}(\log M_{\mathrm{rQMC}})^{dN-1}\right)$ and ASGQ work $O(\mathrm{TOL}^{-1})$ when $p,s\gg1$; MLMC with the same smoothing recovers $O(\mathrm{TOL}^{-2}(\log\mathrm{TOL})^2)$ (arXiv:2111.01874v2).

**Inputs.** A discretised SDE; a payoff with a kink/jump; a hierarchical (Brownian-bridge) or Haar path construction.
**Parameters.** $\mathrm{TOL}_{\mathrm{Newton}}$, Laguerre nodes $M_{\mathrm{Lag}}$, ASGQ point count $M_{\mathrm{ASGQ}}$, Richardson extrapolation order; a rate $\Delta t^{-1}\times M_{\mathrm{ASGQ}}\times M_{\mathrm{Lag}}$ minimisation.
**Observed effects.** Reference prices: digital GBM $0.42074$ ($\sigma=0.4$, $T=1$, $S_0=K=100$); digital Heston $0.5146$; call GBM $15.8519$; call Heston $6.33254$; four-asset basket call GBM $11.04$ ($\rho=0.3$) (arXiv:2111.01874v2).
**Failure modes.** Optimal performance collapses if $p$ or $s$ is too small, or if the dimension $dN$ erodes the rate — the reason the paper adds Richardson extrapolation to keep $N$ small; the optimal direction $v$ is heuristic and problem-dependent.

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Spot + daily OHLCV (initial price $S_0$, return/vol seed) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily OHLCV (alt source) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Interval bars (candidate path input) | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok — `interval` param; intraday availability not separately probed, verify |
| Risk-free discount curve $r(t)$ | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Dividend yield $q$ / discrete dividends | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| SPX option chain quotes (calibration, implied-vol / VIX proxy) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Single-name option chain (exercise-style data) | `moomoo://get_option_chain` | options_data | moomoo | gateway — local OpenD SDK |
| Implied expected move | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway — local OpenD SDK |
| Realised/technical volatility indicators | `https://www.alphavantage.co/query` | technical_indicators | alpha_vantage | ok |
| Macro state (yields, spreads) for scenario/rate paths | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| VIX index level series ($\mathrm{VIX}_T$ itself) | — | — | — | gap |
| VIX futures term structure | — | — | — | gap |
| Forward-variance / variance-swap quotes (rough-Bergomi $X_0$) | — | — | — | gap |
| Certified 5-minute intraday bars (realised variance, path inputs) | — | — | — | gap |

## 4. Pitfalls, validation and measurement

- **Report bias and variance separately.** MC error decomposes as $\text{MSE}=\big(\mathbb{E}\phi(\text{VIX}^2_T)-\phi(\text{VIX}^{2,D_n}_T)\big)^2+\frac1M\operatorname{Var}\phi(\text{VIX}^{2,D_n}_T)$ — discretisation (weak) error plus sampling error. Tuning only the sample count hides a discretisation bias, and vice versa (arXiv:2105.05356v3).
- **Scheme rates are not universal.** The same underlying admits $O(1/n)$ (rectangle) and $O(n^{-(1+H)})$ (trapezoidal) strong error; a rate measured for one scheme does not transfer, and a claimed slope needs a declared fit window and independent randomisations — a single log-log fit is not evidence (arXiv:2105.05356v3, arXiv:2111.01874v2).
- **Fourier methods fail silently through the characteristic function, not the payoff.** The classical Heston $\log g$ form has branch-cut discontinuities and grazing-phase rotation at large frequency, producing a spurious discontinuity in the integrand; the $\zeta$-form is branch-free. Damping without a shift leaves right-boundary error, shifting without damping leaves left (arXiv:2512.05326v1).
- **Truncation intervals and TT tolerances are model risk.** COS assumes mass lies in $[a_m,b_m]$; a too-narrow box silently breaks put–call parity. For the TT variant, insufficient frequency resolution prevents an accurate approximation of the sampled characteristic-function tensor, and the rank cap changes the reported Vega (arXiv:2608.17636v1).
- **Explicit finite differences can be structurally — not marginally — unstable.** Ghost points at an off-grid barrier replace the Dirichlet condition and shrink the stability region without bound as the node approaches the barrier; grid deformation or an L-stable implicit scheme (TR-BDF2, not Crank–Nicolson alone) is the remedy (arXiv:2308.04629v2).
- **Regression Monte Carlo carries in-sample bias.** LSMC regressions are fitted and evaluated on the same paths unless deliberately separated; the hybrid method additionally needs a *bounded* basis and a truncated Gram inverse, or conditioning contaminates the continuation surface (arXiv:2606.11237v1).
- **Validation protocol.** (i) cross-check independent kernels — MC vs FFT/COS vs a high-resolution reference (the corpus does this: MC against a Premia PDE, hybrid LSMC against large-simulation LSMC); (ii) check structural identities — put–call parity, recovered COS mass, first moment, monotonicity across strikes; (iii) fit convergence slopes over a declared window with a confidence interval over randomisations (the half-widths in arXiv:2608.17636v1 come from 32 scrambled Sobol sets); (iv) report Monte Carlo standard errors and 95 % intervals on every price (arXiv:2606.11237v1).
- **Look-ahead and leakage.** Calibrate and price on *separate* paths/grids; use common random numbers across bumped parameters (the QMC Vega reference reuses the same Sobol normals up and down) so finite-difference Greeks measure the parameter, not sampling noise; re-draw any Sobol randomisation before use so the error estimate is unbiased (arXiv:2608.17636v1, arXiv:2111.01874v2).
- **Numerical-smoothing budgets are real error sources.** Newton tolerance and Laguerre node count each contribute an $O(\cdot)$ term; Richardson extrapolation keeps the time-step count (hence the integration dimension $dN$) small enough that the quadrature rate $p$ does not degrade (arXiv:2111.01874v2).

## 5. Recommended first implementation in FinRobot

1. **(S) Pure-NumPy characteristic-function convolver for European options.** Implement the $\zeta$-form Heston CHF (§2.3) on top of `numpy.fft`, with damping + exponential shift and the closed-form error bound as a self-test. Data: `risk_free_curve` (r) + OHLCV (`core_stock_apis`) + `cboe` `options_surface` for calibration. Value: the most self-contained kernel in the corpus — no data gap, no SciPy, explicit accuracy targets; it unblocks every other pricing routine. Risk: branch-cut regression if the classical $g$-form creeps back in; damping needs the $(\alpha+1)$-th moment finite. (arXiv:2512.05326v1)
2. **(S) Cumulant-based COS engine for many strikes.** Reuse the same CHF to build one COS coefficient set and price a whole strike grid by prefix integrals (§2.4). Data: none beyond item 1. Value: near-instant strike sweeps for the calibration loop; the natural place to add put–call-parity and mass diagnostics. Risk: truncation-box selection is model risk — guard with the parity check. (arXiv:2512.05326v1, arXiv:2608.17636v1)
3. **(S) Variance-reduction primitives.** Lognormal/exponential control variates plus antithetic sampling and Brownian-bridge path construction, all in `numpy`. Data: none. Value: cuts the sampling error of every simulation below at near-zero cost and is a prerequisite for items 4–5. Risk: a mis-specified CV *increases* variance; always report the empirical variance ratio. (arXiv:2105.05356v3, arXiv:2111.01874v2)
4. **(M) Multilevel MC wrapper with an empirically fitted ladder.** Implement §2.1 with geometric levels $n_\ell=n_0 2^\ell$ and per-level sample counts from measured $\hat V_\ell$; validate on a GBM/Asian-style functional before exotic models. Data: item 1 inputs (path simulation only). Value: turns a $\varepsilon^{-4}$ estimator into $\varepsilon^{-2}$ for path-dependent payoffs. Risk: needs a defensible strong-error exponent and a non-trivial Cholesky per level; skip if $n^2$ dominates. (arXiv:2105.05356v3)
5. **(M) Bermudan engine: LSMC with a conditional FFT step.** Implement the hybrid recursion of §2.2 (Brownian projection, volatility-only bounded basis, truncated Gram inverse) and fall back to plain LSMC as a cross-check. Data: OHLCV + `risk_free_curve`; no option-exercise data needed (openD `options_data` is a gateway dependency for a live variant). Value: early-exercise pricing at low path counts, where the corpus measures the largest gains. Risk: regression conditioning and the one-way-coupling requirement; needs its own reference (large-simulation LSMC). (arXiv:2606.11237v1)
6. **(M) Explicit finite-difference barrier solver with barrier-on-grid / TR-BDF2.** Implement §2.5 for one-touch/barrier payoffs, placing the barrier on the grid (or using TR-BDF2) and never ghost points; assert the CFL condition explicitly. Data: none (pure PDE). Value: a third independent kernel for diffusions, so MC and Fourier results are triangulated. Risk: stability traps documented above are easy to reintroduce. (arXiv:2308.04629v2)
7. **(L) Adaptive sparse-grid / rQMC with numerical smoothing.** Implement §2.6 for digitals and barriers once items 1–6 are measured; this is where the corpus' largest complexity win lies but it needs a Newton root-finder, Laguerre quadrature and hierarchical path generation. Data: item 1 inputs. Value: $O(\mathrm{TOL}^{-1})$ work versus MC's $O(\mathrm{TOL}^{-3})$. Risk: the rate collapses without sufficient smoothness; a Sobol generator must be hand-rolled because NumPy has none. (arXiv:2111.01874v2)
8. **(L) Tensor-train COS for multi-asset baskets.** Implement §2.4's TT-cross compression for arithmetic baskets and min/max options; only worth building once single-asset COS is trusted. Data: multi-asset OHLCV + correlation; no option data required. Value: polynomial-in-$d$ scaling where direct COS is exponential. Risk: slower than direct COS below $d=4$; frequency-resolution and rank-cap choices are model risk. (arXiv:2608.17636v1)

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2608.17636v1 | COS–TT–CHF: A Tensor-Train Characteristic-Function COS Method for Multi-Asset Option Pricing | 2026 |
| 2606.11237v1 | A Hybrid LSMC–PDE Method for Bermudan Option Pricing under the Gatheral Double Mean-Reverting Model | 2026 |
| 2512.05326v1 | Convolution-FFT for option pricing in the Heston model | 2025 |
| 2308.04629v2 | Instabilities of explicit finite difference schemes with ghost points on the diffusion equation | 2023 |
| 2111.01874v2 | Numerical Smoothing with Hierarchical Adaptive Sparse Grids and Quasi-Monte Carlo Methods for Efficient Option Pricing | 2021 |
| 2105.05356v3 | Multilevel Monte Carlo simulation for VIX options in the rough Bergomi model | 2021 |
