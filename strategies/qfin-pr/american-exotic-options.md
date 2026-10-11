# American & Exotic Options — learnings from the q-fin.PR corpus
`297` of 2274 corpus papers matched this category (`295` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **The free boundary is the whole problem, and it is a put problem.** Early exercise of an American call on a non-dividend-paying asset is never optimal when $r>0$, so the category's live case is the American put/Bermudan put and its exercise boundary; both modern simulation papers restrict their numerical work to puts for exactly this reason (arXiv:2601.00815v1, arXiv:2606.11237v1).
- **A near-exact variance sampler removes the discretization bias that dominates early-exercise simulation.** The Almost-Exact Simulation (AES) scheme samples the CIR variance from its exact non-central chi-square marginal and rewrites two of the four log-price stochastic integrals in terms of the sampled variance; Bermudan prices then converge with $M$ equal to the number of *exercise dates*, not the number of steps an Euler scheme would need. At 20 exercise dates the AES Bermudan put gives 9.966/3.195/0.917 for $S_0=90/100/110$ against reference 9.978/3.205/0.927, while the fair-comparison Euler run (40 steps) gives 9.956/3.189/0.927 (arXiv:2601.00815v1).
- **An American option is priced as a Bermudan with ~48+ exercise dates per year.** With $T=0.25$ the paper sets the minimal step count to $M=12$, and taking $M$ equal to the exercise-date count turns the American pricer into a Bermudan pricer directly — the price falls monotonically toward the American value as $M$ rises (1.986→1.999 for $S_0=8$) (arXiv:2601.00815v1).
- **Reference prices are themselves estimates, and the corpus admits it.** Under the Gatheral double mean-reverting model there is no closed-form Bermudan price, so the Hybrid LSMC–PDE paper benchmarks against a 1,200,000-path, 1,200-step plain LSMC run and reports its Monte Carlo standard errors alongside the "reference" (arXiv:2606.11237v1). Any accuracy claim here inherits that benchmark's error.
- **Reducing the regression dimension is the main numerical lever under multi-factor volatility.** Conditioning on the simulated variance path turns the one-step continuation value into a one-dimensional PDE in the log-price; the remaining variance dependence is a low-order regression, and the advantage over plain LSMC is largest at low and moderate path budgets (arXiv:2606.11237v1).
- **Short-maturity barrier pricing is model-free to leading order.** In the near-barrier regime the leading term is the Black–Scholes barrier price fitted to the forward variance curve; the first stochastic-volatility correction is $O(\theta^{H+1/2})$, where $H\in(0,\tfrac12]$ is the roughness of the relative volatility fluctuation — for regular models $H=\tfrac12$ and the coefficient is set by the short-dated at-the-money implied-volatility skew; for rough models $H<\tfrac12$ it collapses to a one-dimensional integral (arXiv:2610.00340v1).
- **The barrier correction works, but only in a limited regime.** For CEV ($\beta=0.5$) the mean absolute error falls from 0.09426 (Black–Scholes) to 0.01248 (difference correction); for lognormal SABR from 0.14937 to 0.07444; for rough Bergomi ($H=0.1$) from 0.27126 to 0.10319. The theorem itself is proved for the up-and-out put with $k\le b$; up-and-out calls and down-and-out puts hit a boundary layer, and the identity used to normalise the correction fails for $k>b$ (arXiv:2610.00340v1).
- **Path dependence is exactly representable by signatures for the common exotic payoffs.** European and Asian *polynomial* payoffs are exact signature payoffs (via the shuffle product), and the signature of the time-augmented price linearises an otherwise non-Markovian hedging problem into an infinite-dimensional Riccati system whose solution gives the frictionless hedge in feedback form (arXiv:2511.23295v1).
- **Frictions make the path-dependent problem easier, not harder.** With market impact, optimal trading is smoothed and low-truncation signature approximations become accurate and robust — the opposite of the frictionless case, which needs high truncation (arXiv:2511.23295v1).
- **Drawdown/occupation-time derivatives need a sticky process.** In Heston/Black–Scholes the time spent at the running maximum or minimum has measure zero, so streak-like "winning/losing streak" payoffs are degenerate; a time-changed sticky drawdown/drawup diffusion gives record highs and lows positive occupation time, at the cost of a 5-state, 9-parameter model that is solved by a neural PDE solver and beats Heston in- and out-of-sample on SPX 2021–2022 (arXiv:2503.14829v1).
- **Approximate dynamic programming error propagates backward with a contraction factor tied to $r$.** Decomposing error into regression, Monte Carlo and propagation terms gives a Bellman operator that is contractive with $c_P=e^{-2r}<1$ for a positive rate, so errors are damped; non-smooth option payoffs place you in a misspecified regime where the regression rate stays slow (arXiv:2509.20239v2).

## 2. Implementable formulas & algorithms

### 2.1 AES variance sampling + Longstaff–Schwartz Bermudan/American puts
**Purpose.** Price Bermudan and American puts under Heston with near-bias-free variance simulation and a cheap LSM exercise rule; the reference implementation of the category's central object.

Exact CIR marginal sampling (non-central chi-square):
$$\nu_{i+1} \approx \bar c(t_{i+1},t_i)\cdot\chi^2\!\big(\delta,\ \bar k(t_{i+1},t_i)\big),\quad \bar c=\frac{\gamma^2}{4\kappa}\big(1-e^{-\kappa\Delta t}\big),\ \ \bar k=\frac{4\kappa e^{-\kappa\Delta t}}{\gamma^2(1-e^{-\kappa\Delta t})}\nu_i,\ \ \delta=\frac{4\kappa\bar\nu}{\gamma^2}.$$

Log-price AES scheme (Heston):
$$x_{i+1}\approx x_i + c_0 + c_1\nu_i + c_2\nu_{i+1} + c_3\sqrt{\nu_i}\,Z_1,\qquad Z_1\sim N(0,1),$$
$$c_0=(r-\kappa\bar\nu)\Delta t,\quad c_1=\Big(\kappa-\tfrac{\rho\gamma}{2}\Big)\Delta t,\quad c_2=\tfrac{\rho}{\gamma},\quad c_3=\sqrt{1-\rho^2}\,\Delta t.$$

Dynamic-programming recursion solved by regression on in-the-money paths:
$$V_{t_k}=\max\{h_{t_k},\,C(t_k,Y_{t_k})\},\qquad C(t_k,Y_{t_k})=e^{-r\Delta t}\,\mathbb{E}^{\mathbb Q}_{t_k}\big[V(t_{k+1},Y_{t_{k+1}})\big].$$

- **Inputs:** spot $S_0$, variance $v_0$, $r$, strike $K$; no intraday data needed.
- **Parameters:** $\kappa,\bar\nu,\gamma,\rho$ (Heston); regression basis up to second order in $(S/K,\nu)$, fitted on in-the-money paths; $M=$ number of exercise dates.
- **Observed effects:** AES matches reference to $<0.1\%$ relative error in-the-money and $0.2$–$0.4\%$ at/out-of-the-money at 40 exercise dates; roughly halves Euler's step requirement and memory (arXiv:2601.00815v1).
- **Failure modes:** the scheme is only "almost" exact — two residual stochastic integrals are still Euler-approximated; out-of-the-money accuracy does not beat Euler; the Feller condition is needed for strict variance positivity (arXiv:2601.00815v1).

### 2.2 Error-bounded kernel-ridge dynamic programming (KRR-DP)
**Purpose.** Price American/Bermudan options by backward induction with an explicit, modular error budget rather than a single point estimate — useful as the accuracy harness around any other pricer.

Bellman recursion and its empirical surrogate:
$$V_t(x)=\max\big\{C_t(x),\,e^{-r}\mathcal Q_tV_{t+1}(x)\big\},\qquad \hat{\mathcal T}_t f(x)=\operatorname*{ess\,sup}_{u\in\{0,1\}}\big\{F_t(x,u)+\hat{\mathcal P}_{tu}f(x)\big\},$$
$$\hat{\mathcal P}_{tu}f(x)=\frac1{M_t}\sum_{i=1}^{M_t} f\big(\pi_t(x,u,z_i)\big).$$

Error decomposition (three independent terms):
$$E_t=\big\|\hat W_t^{\lambda_t}-V_t\big\|^2_{L^2_{\mu_t}}\lesssim \underbrace{\|\hat W_t^{\lambda_t}-\hat{\mathcal T}_t\hat W_{t+1}^{\lambda_{t+1}}\|^2}_{\text{regression}}+\underbrace{\|\hat{\mathcal T}_t\hat W_{t+1}-\mathcal T_t\hat W_{t+1}\|^2}_{\text{Monte Carlo}}+\underbrace{c_P\,E_{t+1}}_{\text{propagation}}.$$

Regression rate and propagation constant:
$$\big\|\hat W_t^{\lambda_t}-\mathcal T_t\hat W_{t+1}\big\|^2_{L^2_{\mu_t}}\lesssim n_t^{-\frac{\beta_t}{\beta_t+1}},\qquad c_P=e^{-2r}.$$

- **Inputs:** simulated $d$-dimensional GBM paths; payoff $C_t(X_t)$; kernel (RBF) and its RKHS.
- **Parameters:** KRR ridge $\lambda_t\sim n_t^{-\frac{1}{\beta_t+1}}$; Monte Carlo budget $M_t\sim n_t^{\frac{\beta_t+1}{\beta_t}}$; smoothness $\beta_t\in(0,1]$ ($\beta_t=1$ well-specified, $\beta_t<1$ misspecified).
- **Observed effects:** matches literature benchmarks for a geometric-basket put ($d=2$: 4.63 vs 4.62) and a max-call ($d=2$: 16.93 vs 16.86; $d=40$: 50.44 vs 50.70) with 2–118 s runtimes (arXiv:2509.20239v2).
- **Failure modes:** Monte Carlo data generation is the computational bottleneck as dimension rises; payoff non-smoothness drives $\beta_t$ down and stalls the rate; the recursion is contractive only because $r>0$ (arXiv:2509.20239v2).

### 2.3 Hybrid LSMC–PDE for Bermudan options under multi-factor stochastic volatility
**Purpose.** Price Bermudan puts when the variance has two factors (e.g. Gatheral double mean-reverting), avoiding a full three-dimensional PDE and a full-continuation regression.

Brownian projection of the asset driver onto the variance drivers:
$$\beta_2=\frac{\rho_{12}-\rho_{13}\rho_{23}}{1-\rho_{23}^2},\quad \beta_3=\frac{\rho_{13}-\rho_{12}\rho_{23}}{1-\rho_{23}^2},\quad \sigma_\perp^2=\frac{1-\rho_{12}^2-\rho_{13}^2-\rho_{23}^2+2\rho_{12}\rho_{13}\rho_{23}}{1-\rho_{23}^2},$$
$$dW^{(1)}_t=\beta_2\,dW^{(2)}_t+\beta_3\,dW^{(3)}_t+\sigma_\perp\,dB^\perp_t.$$

Conditional one-step Gaussian representation and its FFT propagation:
$$u(t,y)=\mathbb E_\xi\Big[G\big(y+Z_n+I_n(t)+\sqrt{B_n(t)}\,\xi,\ v_{t_{n+1}},v'_{t_{n+1}}\big)\Big],\qquad \xi\sim N(0,1),$$
$$\mathcal F u^{jn}(\omega)=\mathcal F g^j_{n+1}(\omega)\,\exp\!\Big(i\omega Z_n^j+i\omega I_n^j-\tfrac12\omega^2 B_n^j\Big),$$
$$Z_n^j=\sum_{\tau_\ell\in[t_n,t_{n+1})}\sqrt{\bar v_{\ell j}}\,\big(\beta_2\Delta W^{(2)}_{\ell,j}+\beta_3\Delta W^{(3)}_{\ell,j}\big),\quad I_n^j=\sum\big(r-\tfrac12\bar v_{\ell j}\big)\Delta\tau_\ell,\quad B_n^j=\sum\sigma_\perp^2\bar v_{\ell j}\Delta\tau_\ell.$$

Regression over the variance state with a truncated inverse $\;[A]_R^{-1}=A^{-1}$ if $\|A^{-1}\|\le R$ else $0$:
$$a^N_n(s_i)=[A^N_n]_R^{-1}\,b^N_n(s_i),\qquad A^N_n=\tfrac1N\sum_j\phi(V_{nj})\phi(V_{nj})^\top.$$

- **Inputs:** simulated variance paths (Euler/truncated-Euler) and a fixed asset-price grid; no market data required for the estimator itself.
- **Parameters:** exercise dates $N_{ex}$ (paper: 12); asset grid $NS=301$; volatility rectangle truncated at the 99.9% quantile; cubic volatility-only regression basis.
- **Observed effects:** at 48 Euler steps and 250→60,000 paths, the at-the-money ($K=100$) relative error ranges 0.088%–11.118% (Hybrid) versus 1.105%–25.948% (LSMC); reference prices $K\in\{70,\dots,110\}$ = 2.522851/4.298933/6.942119/10.682037/15.743520 (arXiv:2606.11237v1).
- **Failure modes:** not uniformly better at every step count; requires variance truncation and a bounded regression basis for the convergence theorem; benchmark is a large-simulation LSMC estimate, not truth (arXiv:2606.11237v1).

### 2.4 Short-maturity up-and-out barrier expansion with the ATM skew
**Purpose.** Fast, accuracy-controlled barrier pricing near the barrier for short maturities, driven by observable European information only.

Scaling and expansion ($\theta\downarrow0$, $b>\max\{k,0\}$):
$$B=S_0\big(1+\sqrt{v_0\theta}\,b\big),\qquad K=S_0\big(1+\sqrt{v_0\theta}\,k\big),\qquad T=\theta,$$
$$p^{\mathrm{UO}}=p^{\mathrm{UO}}_{\mathrm{BS}}\Big(S_0,\ \sqrt{\textstyle\int_0^\theta v(r)\,dr}\Big)+\alpha\,v_0S_0\,\theta^{H+1/2}+o\big(\theta^{H+1/2}\big).$$

Leading Bachelier term and first Black–Scholes correction:
$$P_0=(K-S_0)\Phi\!\Big(\tfrac{K-S_0}{S_0w(0)}\Big)+S_0w(0)\phi\!\Big(\tfrac{K-S_0}{S_0w(0)}\Big)-\big(K+S_0-2B\big)\Phi\!\Big(\tfrac{K+S_0-2B}{S_0w(0)}\Big)-S_0w(0)\phi\!\Big(\tfrac{K+S_0-2B}{S_0w(0)}\Big),$$
$$P_1=S_0v_0\theta\,\gamma(b,k),\qquad \gamma(b,k)=\tfrac{k}{2}\phi(k)-\phi(k-2b)-b(b-k)\Phi(k-2b).$$

Regular-model practical form (Corollary, $H=\tfrac12$), $A$ = at-the-money volatility skew:
$$p^{\mathrm UO}\approx P_0+\Big(1+\tfrac{2A}{\sqrt{v_0}}\Big)\big(p^{\mathrm{UO}}_{\mathrm{BS}}-P_0\big).$$

- **Inputs:** $S_0$, $B$, $K$, $\theta$; forward variance curve or ATM implied variance (both interchangeable to $o(\theta)$); ATM skew $A$ for the regular-model coefficient.
- **Parameters:** $H\in(0,\tfrac12]$ (roughness); $\rho,\nu$ and initial variance for SABR/rough-Bergomi instances; CEV exponent $\beta$.
- **Observed effects:** the single skew-driven correction cuts the CEV mean absolute error 7.5× (0.09426→0.01248) and the SABR error ~2× (0.14937→0.07444); rough Bergomi from 0.27126 to 0.10319 (arXiv:2610.00340v1).
- **Failure modes:** proved for the up-and-out put with $k\le b$; up-and-out call and down-and-out put develop $(1-u)^{-1}$ boundary layers; the skew-symmetry identity (and hence the correction) fails for $k>b$; jump and non-positive models are outside the assumptions (arXiv:2610.00340v1).

### 2.5 Signature pricing and hedging of path-dependent payoffs with frictions
**Purpose.** Represent Asian/barrier/lookback-type payoffs as signature payoffs, get a frictionless replication explicitly, and extend to a market-impact hedging problem solved by an infinite-dimensional Riccati system.

Signature payoff and frictionless replication (Fawcett formula):
$$H_T=\langle\xi,\hat{\mathbf S}_T\rangle,\qquad \xi_t:=\xi\big|_{\mathcal E_{T-t}},\qquad \mathcal E_t=\exp_\otimes\!\Big(1+\tfrac{\sigma^2}{2}\,t\,\mathbf{22}\Big),$$
$$V_0=\xi_0^{\varnothing},\qquad X_t=\big\langle \xi_t\big|_2,\ \hat{\mathbf S}_t\big\rangle.$$

Polynomial path-dependent payoffs are exact signature payoffs via the shuffle product, e.g.
$$H_T=\sum_{k=0}^{N}\alpha_k\Big(\tfrac1T\textstyle\int_0^T S_t\,dt-K\Big)^k=\Big\langle\sum_{k=0}^{N}\alpha_k\,\sqcup\!\sqcup^k\big(\tfrac12-\varnothing K\big),\ \hat{\mathbf S}_T\Big\rangle .$$

Frictional objective (mean-quadratic variation) and indifference price:
$$\sup_{\theta\in\mathcal A}\ \mathbb E\Big[R_T^\theta-\tfrac{\lambda}{2}[R^\theta,R^\theta]_T\Big],\qquad \pi=\xi_0^{\varnothing}-\sup_\theta \mathbb E\Big[\int(\mu+\nu\theta_t)\big\langle X_{t\theta}-\xi_t|_2,\hat{\mathbf P}^\theta_t\big\rangle dt-\int\eta\theta_t^2dt\Big]-\tfrac{\lambda\sigma^2}{2}\mathbb E\!\int\big\langle X_{t\theta}-\xi_t|_2,\hat{\mathbf P}^\theta_t\big\rangle^2dt .$$

- **Inputs:** the price path (one-dimensional Bachelier dynamics $dS_t=\mu dt+\sigma dW_t$); payoff coefficients $\alpha_k$ or the target forward curve.
- **Parameters:** temporary impact $\eta$, permanent impact $\nu$, risk aversion $\lambda$, signature truncation $M$; coefficients from the Riccati system (5.20) with time-dependent terms.
- **Observed effects:** market impact smooths the optimal strategy, so a low truncation order is accurate in the frictional market while the frictionless case needs high order; the indifference price exceeds the frictionless price when $\eta\ge0,\mu=0,\nu=0$ (arXiv:2511.23295v1).
- **Failure modes:** existence/uniqueness of the infinite-dimensional Riccati system is open in general; truncated-signature hedging is a universal-approximation argument, not exact; cost grows with order (arXiv:2511.23295v1).

### 2.6 Sticky drawdown/drawup stochastic-volatility model (occupation-time derivatives)
**Purpose.** Model and price derivatives whose value depends on the time spent at record highs/lows — drawdown/streak payoffs that Heston cannot represent.

Time-change and sticky dynamics:
$$R(t)=t+\xi L_t^1(D)+\eta L_t^1(U),\qquad D_t^{\pm}=D_{R^{-1}(t)},\quad U_t^{\pm}=U_{R^{-1}(t)},$$
$$dS_t^\pm=rS_t^\pm dt+\sqrt{V_t}S_t^\pm \mathbb 1_{\{S^\pm_t\ne\{M^\pm_t,M^{\pm}_t\}\}}dB_t^{\mathbb Q},\qquad dV_t=\kappa(\theta-V_t)dt+\sigma\sqrt{V_t}\,dW_t^{\mathbb Q}.$$

Pricing PDE (European call on the sticky extreme process) and boundary conditions:
$$P_t+\tfrac12vx^2P_{xx}+\rho\sigma vxP_{xv}+\tfrac12\sigma^2vP_{vv}+rxP_x+\kappa(\theta-v)P_v+ryP_y+rzP_z-rP=0,$$
$$P_y(t,y,y,z,v)=\big(\tfrac12vyP_{xx}+\rho\sigma vP_{xv}\big)\xi,\qquad P_z(t,z,y,z,v)=-\big(\tfrac12vzP_{xx}+\rho\sigma vP_{xv}\big)\eta,\qquad P(T,x,y,z,v)=(x-K)^+.$$

- **Inputs:** SPX spot and option quotes for calibration; simulated CTMC paths for pricing.
- **Parameters:** $\Phi=(K,r,\rho,\kappa,\theta,\sigma,\eta,T,\xi)$; neural network 4 hidden layers × 110 nodes, 1.6M training points, ADAM with piecewise-constant learning rate.
- **Observed effects:** network prices match Monte Carlo with average percentage error 0.3596% and average absolute error 0.02734 over 1,219 parameter sets; per-option pricing 0.018 s versus 1,241 s for 60,000-path Monte Carlo; calibration ≈164 ms and SVSDU/SVSD/SVSU beat Heston in- and out-of-sample on SPX 2021–2022 (arXiv:2503.14829v1).
- **Failure modes:** nine parameters plus a data-scaling factor make calibration delicate; the PDE is solved only on a bounded domain and accuracy degrades if inputs fall outside the training range; requires a neural solver (arXiv:2503.14829v1).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV for the underlying (calibration, LSMC/PDE paths) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Alternative daily OHLCV (multi-asset basket legs) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Interval bars for fine time-grid discretization checks | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok |
| SPX option chain + surface (BS/Bachelier calibration, ATM skew) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Single-name option chain (exercise-boundary fitting) | `moomoo://get_option_chain` | options_data | moomoo | gateway — local OpenD |
| Implied expected move (from option chain) | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway — local OpenD |
| Risk-free discount curve ($r$ in LSMC/PDE, Bermudan dates) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Dividend / corporate-action schedule (early-exercise calls) | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Realized-vol / technical indicators (SV calibration proxy) | `https://www.alphavantage.co/query` | technical_indicators | alpha_vantage | ok |
| Macro state: rates, term spread, credit (regime-aware exercise) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| News/sentiment features for ML pricing models | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| 5-minute intraday returns / realized quadratic variation over the stub | **gap** — no inventoried provider exposes a certified intraday series | — | — | gap |
| VIX / variance-swap strikes (variance swaps, vol-of-vol exotics) | **gap** — no probed endpoint returns the index or a swap strike series | — | — | gap |
| Futures / commodity / FX option quotes (commodity & FX exotics) | **gap** — no futures, commodity or FX feed in the inventory | — | — | gap |
| Swaption / cap-floor vol (Bermudan swaptions) | **gap** — no rates-volatility endpoint | — | — | gap |
| Bond / convertible prices (convertibles with reset & call provisions) | **gap** — no bond or convertible price feed | — | — | gap |
| Tick / order-book depth (market-impact hedges, signature frictions) | **gap** — no intraday quote or L2 feed | — | — | gap |

## 4. Pitfalls, validation and measurement

- **Discretization bias is the dominant simulation error, and it has two heads.** Truncated/reflected Euler on the CIR variance biases early-exercise prices; the AES scheme removes the variance bias but still Euler-approximates two log-price integrals (arXiv:2601.00815v1). Barrier crossings checked only at grid endpoints add a separate *monitoring* bias: on the same paths, moving from 12,500 to 25,000 monitoring dates changed the controlled estimates by up to 0.00477 — detectable even on a fine grid, and the paper states it is *not* a rigorous bound on the residual bias (arXiv:2610.00340v1).
- **In-sample regression leaks.** LSMC/KRR continuation values are fitted and then used on the same paths. Report an *out-of-sample* valuation and both a low-biased policy value and a high-biased dual/upper bound; never compare pricers only on the regression exercise rule (arXiv:2601.00815v1, arXiv:2509.20239v2).
- **Benchmarks are estimates.** Under GDMR there is no closed form, and the "reference price" is a 1,200,000-path LSMC run with its own standard error; relative errors are computed against that, not truth (arXiv:2606.11237v1). Always carry Monte Carlo confidence bands and treat small gaps (a few standard errors) as unresolved.
- **Accuracy claims are regime-limited.** The barrier correction is proved for $k\le b$ (up-and-out put); the up-and-out call and down-and-out put boundary layers are an open extension and $k>b$ breaks the correction outright (arXiv:2610.00340v1). The AES advantage disappears for deep out-of-the-money options (arXiv:2601.00815v1), and the Hybrid LSMC–PDE gain is not uniform across step counts (arXiv:2606.11237v1).
- **Model risk scales with parameters.** The sticky-model calibration fits nine parameters plus a data-scaling factor and warns that inputs outside the network's bounded training domain degrade accuracy (arXiv:2503.14829v1); multi-factor SV adds Feller-type boundary conditions and truncation choices that change prices (arXiv:2606.11237v1).
- **Error propagation must be reported, not assumed.** The RKHS analysis formalises the total error as regression + Monte Carlo + propagation, with propagation controlled by $c_P=e^{-2r}$; a positive rate damps errors, but with $r\to0$ the damping vanishes, and non-smooth payoffs keep the regression rate slow (arXiv:2509.20239v2). Validation protocol: report the three components separately, re-fit weights walk-forward, and check the truncation/variance-grid stability (each pricer in this corpus reports a refinement study).
- **Truncation order is a frictional choice.** For signature hedges, low order suffices under market impact but the frictionless case needs high order — validating a signature pricer only in one friction regime is misleading (arXiv:2511.23295v1).
- **Standard protocol across the corpus:** compare on a fixed parameter set from the literature (or a calibrated set), report the calibration routine's fit (not just price error), run at least two path/step budgets and at least two seeds, and use explicit reference prices or PDE benchmarks with CIs; paired monitoring-frequency comparisons isolate the discrete-monitoring effect (arXiv:2601.00815v1, arXiv:2606.11237v1, arXiv:2610.00340v1, arXiv:2509.20239v2).

## 5. Recommended first implementation in FinRobot

1. **Discounted LSMC Bermudan engine (S).** Longstaff–Schwartz on GBM (and optionally Heston) with a polynomial in-the-money basis, in-sample policy plus an out-of-sample revaluation and a crude dual upper bound. Data: `core_stock_apis` OHLCV + `risk_free_curve` for $r$. Value: the baseline early-exercise pricer every later method is measured against, and the exact object the corpus benchmarks (arXiv:2601.00815v1, arXiv:2606.11237v1, arXiv:2509.20239v2). Risk: in-sample bias if no held-out valuation is added.
2. **AES CIR variance sampler (S).** Swap the Euler variance update for exact non-central chi-square sampling; keep exercise dates equal to simulation steps. Data: same OHLCV + a Heston calibration from the `options_surface` chain. Value: removes the dominant discretization bias and roughly halves step/memory cost (arXiv:2601.00815v1). Risk: residual Euler error in two log-price integrals; OTM gain is thin.
3. **Short-maturity barrier pricer from the ATM skew (S→M).** Implement $P_0+P_1$ and the regular-model interpolation $P_0+(1+2A/\sqrt{v_0})(p^{\mathrm{UO}}_{\mathrm{BS}}-P_0)$, feeding $A$ and the level from the CBOE SPX surface. Data: `options_surface`. Value: near-barrier barrier prices at negligible cost and a validation target for the Monte Carlo pricer (arXiv:2610.00340v1). Risk: only the near-barrier, short-maturity, $k\le b$ regime applies.
4. **Accuracy-budget harness around the DP pricer (S→M).** Implement the regression/Monte Carlo/propagation split and report each term with a kernel-ridge fit on simulated paths. Data: OHLCV only. Value: turns "our price" into "our price ± this error", and exposes whether the payoff is in the misspecified regime (arXiv:2509.20239v2). Risk: Monte Carlo data generation is the runtime bottleneck.
5. **Hybrid LSMC–PDE Bermudan under a two-factor SV model (M).** Implement the Brownian projection, the conditional Gaussian step and the FFT propagation with the truncated-inverse regression; calibrate the two variance factors to the SPX surface. Data: `options_surface` + equity OHLCV. Value: better Bermudan prices at low path budgets and the paper's reference-price table for tests (arXiv:2606.11237v1). Risk: needs grid/truncation tuning; gain not uniform across step counts.
6. **Signature path-dependent pricer/hedger (L).** Represent Asian payoffs exactly as signature payoffs, implement the Fawcett replication and, for risk, the Riccati-based frictional hedge at low truncation order. Data: OHLCV; frictional variant needs quote/tick depth that is a recorded **gap**, so it can only be exercised on simulated impact parameters. Value: covers Asian/barrier path dependence in one formalism and matches the corpus' friction-smoothing result (arXiv:2511.23295v1). Risk: Riccati well-posedness is open; heavy compute.
7. **Sticky drawdown/drawup model (L, deferred).** The neural PDE solver and its training loop are outside FinRobot's pure-NumPy runtime; mark out of scope until a NumPy/CTMC simulation path is built from the paper's Meier-et-al. scheme. Value: the only route in this corpus to occupation-time/streak payoffs (arXiv:2503.14829v1). Risk: 9-parameter calibration and bounded-domain extrapolation.

**Recorded gaps that block whole sub-topics today:** variance swaps and vol-of-vol exotics (no VIX/swap-strike feed), Bermudan swaptions (no swaption vol), convertible-bond pricing (no bond feed), commodity/energy and FX exotics (no futures/FX feed), and market-impact-aware hedging (no tick/order-book feed). Each is a genuine **gap** row in §3, not a modelling choice.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2601.00815v1 | Almost-Exact Simulation Scheme for Heston-type Models: Bermudan and American Option Pricing | 2025 |
| 2606.11237v1 | A Hybrid LSMC–PDE Method for Bermudan Option Pricing under the Gatheral Double Mean-Reverting Model | 2026 |
| 2610.00340v1 | Short-term barrier option price expansion | 2026 |
| 2511.23295v1 | Signature approach for pricing and hedging path-dependent options with frictions | 2025 |
| 2503.14829v1 | Stochastic Volatility Model with Sticky Drawdown and Drawup Processes: A Deep Learning Approach | 2025 |
| 2509.20239v2 | Error Propagation in Dynamic Programming: From Stochastic Control to American Option Pricing | 2025 |