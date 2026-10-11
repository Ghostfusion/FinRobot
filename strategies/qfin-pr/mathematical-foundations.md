# Mathematical Foundations — learnings from the q-fin.PR corpus
`197` of 2274 corpus papers matched this category (`193` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **The backward SDE / Feynman–Kac reformulation is the shared workhorse.** A pricing problem with terminal payoff $g$ is written as a BSDE whose solution satisfies $Y_t=V(t,X_t)$ and $Z_t=\sigma(t,X_t)^\top\nabla_x V(t,X_t)$, so the second component *is* the delta. Under the risk-neutral measure a Black–Scholes-type price uses the linear driver $f(t,x,y,z)=-ry$; a European put is the canonical instance (arXiv:2601.18634v2). Every "nonlinear" price in this literature is then a different driver over the same forward SDE $dX_t=\mu\,dt+\sigma\,dW_t$.
- **Exponential (CARA) utility is what forces quadratic-growth drivers.** The individual optimum in a mean-field market is characterised by a BSDE whose driver grows quadratically in both the stochastic integrands *and their conditional expectations*; well-posedness is proved in $H^2_{\mathrm{BMO}}$-type spaces after a change of measure, not by a global Lipschitz condition (arXiv:2607.17502v1). Market clearing then gives a mean-field BSDE for the risk premium, with the premium decomposing into a Brownian-hedging part (inherited from the diffusive model) and a default-risk part.
- **Under CARA utility the frictionless hedge is exactly additive, and frictions turn it into a band.** The optimal share holding is $y^*=\Delta_{\mathrm{BS}}(t,S)+\frac{\mu-r}{\sigma^2\gamma S e^{r(T-t)}}$ — a pure delta hedge plus a Merton speculative position that is independent of wealth. With proportional transaction cost $\lambda$, optimal rebalancing is a *no-transaction band* around $\Delta_{\mathrm{BS}}$ whose half-width scales as $O(\lambda^{1/3})$ (Wallace–Wilmott); report the band and the trade frequency, not only the price (arXiv:2603.29994v1).
- **Malliavin calculus converts Greeks into weighted expectations.** For a jump-diffusion with CIR stochastic intensity, the delta is $\Delta=\mathbb E\!\left[f(S_T)\,Z_T/S_0\right]$ with a Wiener weight $Z_T=\delta^W(h(\cdot))$, and there is a second, Poisson-space weight; because the price depends on the intensity, the intensity's Malliavin derivative must be folded into the weight. In their experiments the Malliavin estimator is an order of magnitude more accurate than central finite differences (MSE $3\times10^{-4}$–$4\times10^{-4}$ vs $0.0190$–$0.0254$) (arXiv:2405.00473v2).
- **Robust pricing over a book of quoted options is an optimal-transport problem, and bid–ask spreads do not wash out.** Enforcing the model marginal to lie between calibrated bid and ask marginals in convex order ($\mu_b\preceq_c\mu^Q_T\preceq_c\mu_a$) yields superhedging prices that can sit far above the mid-price marginal; for one SPX digital the paper reports a superhedging value 46.84 against a mid-price value 37.14, a 9.70 premium (arXiv:2603.24605v2). The market practice of pricing exotics off the mid marginal "can substantially underestimate" the robust bound.
- **Free-boundary/viscosity theory is alive but thinly algorithmic in this slice.** The perpetual American price is the unique viscosity solution of the variational inequality $\min\{-LV,\ V-\psi\}=0$ with the Black–Scholes ODE operator $L$; an explicit difference scheme converges to it and the exercise boundary has a closed-form discrete location, but the paper is an existence/uniqueness/convergence study rather than a calibrated pricer (arXiv:1903.05189v1).
- **Where the reading disagrees, and what the shortlist lacks.** Deep-learning solvers claim accuracy on problems (high-dimensional Bermudan, $M$-fold compound options) where lattice/regression methods are costly, but the convergence of backward deep BSDE for early-exercise options was an *open problem* prior to the compound-BSDE proof (arXiv:2601.18634v2); on frictions the stochastic-control and deep-hedging writer prices diverge sharply at high cost (0.11750 vs 0.08878 at $\lambda=5\%$), a gap the authors attribute to discretisation vs. rare-scenario pricing (arXiv:2603.29994v1). Across the 26 highest-ranked members the machinery clusters on BSDEs, mean-field games and Malliavin/OT duality; rough-path calculus and a dedicated Girsanov paper are absent from that shortlist.

## 2. Implementable formulas & algorithms

### 2.1 Forward Monte-Carlo BSDE solver (Feynman–Kac backbone)
**Purpose.** Price a European/compound/Bermudan claim and recover its delta by simulating the *whole* BSDE forward, with no backward induction and no nested least-squares — the structure that makes it usable in a pure-NumPy stack.

Discretise on a uniform grid of step $h$ and simulate forward,
$$
\begin{aligned}
X^\pi_{t_{i+1}} &= X^\pi_{t_i} + b(t_i,X^\pi_{t_i})\,h + \sigma(t_i,X^\pi_{t_i})\,\Delta W_{t_i},\\
Y^\pi_{t_{i+1}} &= Y^\pi_{t_i} - f(t_i,X^\pi_{t_i},Y^\pi_{t_i},Z^\pi_{t_i})\,h + Z^\pi_{t_i}\,\Delta W_{t_i},
\end{aligned}
$$
where $Y^\pi_{t_0}$ and the $Z^\pi_{t_i}$ are the unknowns. For an $M$-fold compound problem the coupling is imposed by minimising
$$
\inf_{\{Y^\pi_{j,T_{j-1}}\},\{Z^\pi_{j,t_i}\}}\ \sum_{j=1}^{M-1}\mathbb E\big\|g_j(X^\pi_{T_j},Y^\pi_{j+1,T_j})-Y^\pi_{j,T_j}\big\|^2+\mathbb E\big\|g_M(X^\pi_{T_M})-Y^\pi_{M,T_M}\big\|^2 .
$$
The three bankable compounding conditions are: $g_j(x,y)=y$ (collapses to a plain BSDE), $g_j(x,y)=(y-K_j)^+$ (compound/chooser options), and $g_j(x,y)=\max\{y,(x-K_j)^+\}$ (Bermudan exercise, a discretely reflected BSDE). The a posteriori estimate that supports it is
$$
\sup_{t}\mathbb E\|X_t-X^\pi_{\pi(t)}\|^2+\sum_{j=1}^{M}\!\Big(\sup_{t\in[T_{j-1},T_j]}\!\mathbb E\|Y_{j,t}-Y^\pi_{j,\pi(t)}\|^2+\!\int_{T_{j-1}}^{T_j}\!\mathbb E\|Z_{j,t}-Z^\pi_{j,\pi(t)}\|^2 dt\Big)\ \le\ C\Big(h+\textstyle\sum_j \text{objective term}_j\Big).
$$
In NumPy the neural $Z^\pi_{t_i}$ can be replaced by a per-step linear/regression readout (the deep BSDE loss reduces to the least-squares Monte-Carlo variance objective), keeping the forward recursion exactly as above.

- **Inputs:** underlying price paths from the forward SDE; the risk-free rate for $f=-ry$; the payoff(s).
- **Parameters:** time step $h$; number of Monte-Carlo paths; for Bermudan, the exercise-time grid $\{T_j\}$.
- **Observed effects:** relative MSE $3.8\times10^{-7}$ to $1.0\times10^{-3}$ on the four plain compound options and stable to $M=5$; error decreases approximately at first order in $h$ (a factor $\approx5$ from $N=10$ to $N=50$) and the empirical error tracks the theoretical bound, up to $d_1=50$ for a Bermudan geometric basket put (arXiv:2601.18634v2).
- **Failure modes:** the a posteriori constant is only finite when the driver's Lipschitz constants are small; putting the $Z$ process inside $g_j$ needs extra regularity of the decoupling field and is left open; high-variance Monte-Carlo estimates need many paths for the small-$h$ regime (arXiv:2601.18634v2).

### 2.2 HJBQVI no-transaction band and the Whalley–Wilmott prior
**Purpose.** Price and hedge a short option under proportional costs with CARA utility: recover the utility-indifference price *and* the trading policy (a band), not just a number.

The value function $U(t,S,y,X)$ satisfies the quasi-variational inequality
$$
\max\{A,B,C\}=0,\quad
A=U_y-(1+\lambda)SU_X,\quad
B=-U_y+(1-\lambda)SU_X,\quad
C=-U_t-\mu SU_S-\tfrac12\sigma^2S^2U_{SS}-rXU_X .
$$
The no-transaction region is exactly $\{(1-\lambda)S\le U_y/U_X\le(1+\lambda)S\}$. Under CARA, $U(t,S,y,X)=1-e^{-\gamma X/\delta(t,T)}Q(t,y,S)$ with $\delta=e^{-r(T-t)}$ eliminates the cash dimension, and the writer's indifference price is
$$
p_w(t,y,S)=\frac{\delta(t,T)}{\gamma}\Big[\log Q^{\text{without}}(t,y,S)-\log Q^{\text{with,writer}}(t,y,S)\Big].
$$
The band half-width around $\Delta_{\mathrm{BS}}$ is, to leading order in small $\lambda$,
$$
h_{\mathrm{WW}}(t,S)=\left(\frac{3\lambda\,\delta(t,T)\,S\,\Gamma_{\mathrm{BS}}(t,S)^2}{2\gamma}\right)^{1/3}.
$$

- **Inputs:** stock paths and $\sigma$ (from realised vol or a chain), $r$, the transaction-cost rate $\lambda$, risk aversion $\gamma$, payoff $\varphi$.
- **Parameters:** binomial tree $N=400$ steps with $u=e^{\sigma\sqrt{\Delta t}},d=e^{-\sigma\sqrt{\Delta t}}$; holding grid $y_k=k\Delta y$, $\Delta y=\sigma\Delta t$, $M=\mathrm{int}(0.8\lfloor N/2\rfloor)$; run the scheme twice (with/without the option) to get $p_w$; a soft clamp $\ell+\frac{u-\ell}{2}+\frac{u-\ell}{2}\tanh\!\big(\beta\frac{x-(\ell+u)/2}{(u-\ell)/2}\big)$ with $\beta=10$ replaces hard clamping in the learning variants.
- **Observed effects:** frictionless price recovers $\mathrm{BS}=0.07966$; the writer price rises monotonically in $\lambda$ and a bid–ask spread in indifference prices opens (0.00068 at $\lambda=0$ up to 0.07621 at $\lambda=5\%$ for the dynamic-programming solution); the Whalley–Wilmott prior matches the control solution's band more closely than learning the band from scratch and converges to a lower entropic loss (arXiv:2603.29994v1).
- **Failure modes:** the dynamic-programming scheme can only trade $\pm\Delta y$ per step, biasing trade frequency and mechanically scaling the spread; the Whalley–Wilmott formula "underestimates the true band width" for large $\lambda$; stochastic-control and deep prices diverge at high frictions and the split of blame is unresolved (arXiv:2603.29994v1).

### 2.3 Mean-field quadratic-growth BSDE for the equilibrium risk premium
**Purpose.** Give an *endogenous* risk premium that clears a large heterogeneous population, including a single-default jump — the object a real-options or factor-price model would need.

Each agent maximises exponential utility subject to an unspanned terminal liability; market clearing $\mathbb E[\pi^{1,*}_t]=0$ yields the candidate premium
$$
\theta^{\mathrm{mfg}}_s=-\hat\gamma\,\mathbb E[Z^{1,0}_s]^{\top}-\hat\gamma\,\lambda_s\eta_s\psi^*_s,\qquad
\psi^*_s=\mathbb E\!\left[e^{-q^{1,*}_s/\gamma_1}\right],\qquad \hat\gamma=\mathbb E[1/\gamma_1]^{-1},
$$
where the representative agent's $(Y^1,Z^{1,0},Z^1,U^1)$ solves a mean-field BSDE with driver
$$
f^{1,\mathrm{mfg}}(s,Z^{1,0}_s,Z^1_s,U^1_s)=\hat\gamma Z^{1,0\parallel}_s(M^1_s)^\top-\tfrac{\hat\gamma^2}{2\gamma_1}|M^1_s|^2+\tfrac{\gamma_1}{2}\big(|Z^{1,0\perp}_s|^2+|Z^1_s|^2\big)-\lambda_sU^1_s+\lambda_s\Phi^1_s-\tfrac{\lambda_s}{\gamma_1+\gamma_1\lambda_s^2|\eta_s|^2/2}(\Phi^1_s)^2,
$$
and the default-jump exposure is recovered from the root of a scalar fixed-point equation
$$
q^{1,*}_s-\lambda_s|\eta_s|^2e^{-q^{1,*}_s}=\gamma_1\big(Z^{1,0\parallel}_s\eta_s-U^1_s\big)-\hat\gamma\big(\mathbb E[Z^{1,0\parallel}_s]\eta_s+\lambda_s|\eta_s|^2\psi^*_s\big).
$$

- **Inputs:** default intensity $\lambda$, jump size $\eta$, the cross-sectional distribution of $(\gamma_i,$ liabilities$)$; a Markovian factor model for solvability.
- **Parameters:** $\hat\gamma$, the horizon $T$.
- **Observed effects:** short-time existence of the mean-field BSDE for $T\le T_0$ via a fixed-point argument on a coupled semilinear PDE system; the premium provably clears the finite-agent market as $N\to\infty$ (arXiv:2607.17502v1).
- **Failure modes:** no closed form for the default-jump exposure — the equilibrium is a *pair* of a mean-field BSDE and a scalar root problem, not a single BSDE; the driver depends on conditional expectations, so naive nested Monte Carlo is high-variance; the default intensity is not observable from FinRobot's data (see §3) (arXiv:2607.17502v1).

### 2.4 Malliavin-weight Greeks under jump-diffusion with CIR intensity
**Purpose.** Compute the delta of a European option on an asset whose jumps arrive with CIR stochastic intensity, where finite differences are noisy and discontinuous payoffs break pathwise differentiation.

Model (independent $W,W^S$, $N$):
$$
dS_t=\mu S_t\,dt+\sigma_1S_t\,dW^S_t+\int_{\mathbb R_0}(e^{J_{t,z}}-1)S_t\,\tilde N(dt,dz),\qquad
d\lambda_t=\kappa(\Theta-\lambda_t)\,dt+\sigma_2\sqrt{\lambda_t}\,dW_t .
$$
The price and delta representations are
$$
\mathbb E[f(S_T)]=\mathbb E\!\left[\frac{F(S_T)}{S_T}(1+Z_T)\right]=\mathbb E\!\left[G(X_T)Z_T\right],\qquad
\Delta^W=\frac{\partial}{\partial S_0}\mathbb E[f(S_T)]=\mathbb E\!\left[\frac{f(S_T)\,Z_T}{S_0}\right],
$$
with $Z_T=\delta^W(h(\cdot)/B_T)$ the Wiener–Malliavin weight and a second weight $\Delta^N$ obtained from the Poisson-space derivative (jump-size derivative $\partial_z h$); the average $(\Delta^W+\Delta^N)/2$ is the recommended estimator.

- **Inputs:** $r=\mu$, volatility $\sigma_1$, jump law (e.g. Gaussian $\mu_J,\sigma_J$ or Kou $\eta_1,\eta_2,p_{\text{up}}$), and CIR parameters $\kappa,\Theta,\sigma_2,\lambda_0$.
- **Parameters:** Feller condition $2\kappa\Theta>\sigma_2^2$; Euler step $h$; payoff of at most polynomial growth (locally Riemann integrable, first-kind discontinuities allowed).
- **Observed effects:** exact delta 0.0481509 is recovered with MSE 0.0004 (Wiener weight), 0.0023 (Poisson weight), 0.0003 (average) in the first approach and 0.0003/0.0021/0.0002 in the second, versus 0.0254/0.0190 for symmetric finite differences; the Euler scheme converges in log2 error roughly linearly in the refinement (arXiv:2405.00473v2).
- **Failure modes:** the method needs bounded moments of the Malliavin weights and of $S_T$; the Feller condition can fail under calibration; if the payoff is too irregular the weight's moments blow up and variance dominates (arXiv:2405.00473v2).

### 2.5 Bid–ask martingale optimal transport: primal, dual, closed-form digital
**Purpose.** Turn a quoted option chain (with spreads) into honest robust price *bounds* for an illiquid claim, avoiding the mid-marginal bias.

Primal and dual:
$$
\sup_{Q\in\mathcal Q(\mu_b,\mu_a)}\mathbb E^Q[H],\quad
\mathcal Q(\mu_b,\mu_a)=\{\text{martingale }Q:\ \mu_b\preceq_c\mu^Q_T\preceq_c\mu_a\},
\qquad
\inf_{\psi^{b,a}\in\Psi^{b,a}(H)}\ \mu_a(\psi_a)-\mu_b(\psi_b),
$$
with strong duality $\sup=\inf$ for upper-semicontinuous $H$ of at most linear growth. Bid/ask marginals are calibrated as log-normal mixtures $\mu=\sum_j w_j\,\mathrm{LN}(\cdot)$ with shared means/weights and component volatilities ordered to preserve convex order. The one-sided digital has a closed form: with $\bar b_a(L)=\int_L^\infty(x-K)\mu_a(dx)$ and $L^\star$ the root of $\bar b_a(L)=0$,
$$
P(h)=\sup_{\mu\preceq_c\mu_a}\mu([K,\infty))=\frac{c_a(L^\star,T)}{K-L^\star}=\mu_a([L^\star,\infty)).
$$

- **Inputs:** bid and ask call prices per strike at one or more maturities, the forward $x_0$; a calibratable family (log-normal mixture, $J=4$).
- **Parameters:** mixture component count and the spread envelope; in the one-sided case only the ask marginal.
- **Observed effects:** the mid-price practice underestimates the robust digital superhedging price by a wide margin — SPX digital (2025-02-27 quotes, 2025-07-18 maturity) computed at 46.84 vs a mid-marginal 37.14, a 9.70 premium, with optimal call-spread strikes $L^\star=6032$, $K=6154.05$; convergence to classical MOT is linear in the bid–ask distance for difference-of-convex payoffs and square-root for general upper-semicontinuous payoffs (arXiv:2603.24605v2).
- **Failure modes:** the calibrated bid/ask pair must stay in convex order (the authors report small feasibility residuals, min signed potentials $-0.1136$ and $-0.3529$, interpreted as discretisation); a dual optimizer for the undiscretised problem need not exist; the resulting bound is deliberately wide (arXiv:2603.24605v2).

### 2.6 Explicit difference scheme for the perpetual-American variational inequality
**Purpose.** A one-dimensional free-boundary/viscosity baseline: the cheapest correct implementation of an optimal-stopping problem with a genuine exercise boundary.

$$
\min\left\{-\tfrac{\sigma^2}{2}S^2\frac{d^2V}{dS^2}-(r-q)S\frac{dV}{dS}+rV,\ V-\psi\right\}=0,\qquad \psi=(E-S)^+\ \text{(put)} .
$$
Under $u(x)=V(S),\ S=e^x$ the explicit scheme is
$$
u_j=\max\left\{\frac{1}{\rho}\big[(1-w)u_j+w(au_{j+1}+(1-a)u_{j-1})\big],\ \varphi_j\right\},\qquad
w=\frac{\sigma^2\Delta t}{\Delta x^2},\quad a=\frac12+\frac{(r-q-\sigma^2/2)\Delta x}{2\sigma^2},\quad \rho=1+r\Delta t .
$$
The characteristic equation $wa\,\xi^2-(\rho+w-1)\xi+w(1-a)=0$ has roots $\xi_1<1<\xi_2$, so the continuation solution is $u_j=c_1\xi_1^{\,j}$ and the optimal exercise boundary has the closed form $j^\star=\lfloor\frac1{\Delta x}\log(\cdot)\rfloor$ from an explicit logarithmic expression in $w,a,\rho,\xi_1,E,c$; the solution is $u_j=(E-e^{j\Delta x+c})\xi_1^{\,j-j^\star}$ for $j>j^\star$ and $\varphi_j$ otherwise.

- **Inputs:** $\sigma$, $r$, $q$, strike $E$.
- **Parameters:** step sizes with $0<w\le1$ and $\big|\frac{(r-q-\sigma^2/2)\Delta x}{\sigma^2}\big|\le1$; the grid must be fine enough for the discrete maximum principle.
- **Observed effects:** the scheme has a unique solution, the optimal exercise boundary exists and satisfies $S_0\le\min\{rE/q^+,\,E\}$; the interpolated solution converges to the viscosity solution as $\Delta x\to0$; the price limits of the variational-inequality and binomial-tree models are time-independent as maturity $\to\infty$ (arXiv:1903.05189v1).
- **Failure modes:** perpetual/constant-coefficient only; if $r=0$ the exercise region is empty and no boundary exists; the payoff singularity at $S=E$ and the free boundary require the grid conditions above or monotonicity/convergence can fail (arXiv:1903.05189v1).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Underlying equity OHLCV (forward SDE $X$, dynamic hedge) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Equity OHLCV (alt) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Daily/interval bars (alt) | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok |
| Local snapshot OHLCV (gateway) | `moomoo://get_market_snapshot` | core_stock_apis | moomoo | gateway |
| Risk-free discount curve $r$ ($-ry$ driver, BSOD operator) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Dividend yield $q$ / carry | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Listed option chain with bid/ask quotes (OT bid/ask marginals) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Option chain (local gateway) | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Expected move / implied-vol snapshot ($\sigma$ input) | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Macro factors (rates, credit-spread proxies for the risk premium) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Default intensity / CDS or credit spreads (mean-field default, CIR intensity) | — | — | — | gap — no credit/CDS/spread feed in the inventory |
| Recovery rates / corporate bond prices | — | — | — | gap — no bond-price provider |
| Swap / swaption rates (term-structure foundations) | — | — | — | gap — no swap/swaption feed |
| Intraday/tick quotes for jump-intensity and quadratic-variation estimation | — | — | — | gap — no certified intraday series |
| Order-book depth / underlying bid–ask (proportional cost $\lambda$) | — | — | — | gap — no order-book or quote feed |
| Futures / forward prices (carry, MOT forward $x_0$) | — | — | — | gap — inferable only from spot + curve |

Row tally: **16 rows — `ok` 7, `gateway` 3, `fail` 0, `gap` 6.**

## 4. Pitfalls, validation and measurement

- **Quadratic-growth BSDEs need BMO machinery, not Lipschitz checks.** Existence for the mean-field, exponential-utility driver is proved only for *short* horizons ($T\le T_0$) after a change of measure, and the driver contains conditional expectations — the practical estimator (nested Monte Carlo) is the dominant variance source, not the path simulator (arXiv:2607.17502v1).
- **A posteriori error constants are not checkable in practice.** The compound-BSDE bound requires the driver's Lipschitz constants $K_y,K_z$ to be "sufficiently small"; treat the bound as a *shape* argument (error $\sim$ objective $+\,h$) and validate empirically by refining $h$ (arXiv:2601.18634v2).
- **Discretisation, not economics, can create "findings".** The control dynamic-programming scheme is restricted to $\pm\Delta y$ trades, which inflates trade frequency and mechanically widens the indifference spread; the stochastic-control and deep-hedging writer prices differ by 0.0287 at $\lambda=5\%$ for exactly this reason (arXiv:2603.29994v1). Report the discretisation and re-run at finer grids before interpreting any friction result.
- **Malliavin weights are heavy-tailed.** The Greek estimators are unbiased but require bounded moments of $Z_T$ and $S_T$; verify them by comparing against closed-form deltas on log-normal sub-cases and by reporting Monte-Carlo standard errors, not single point estimates (arXiv:2405.00473v2).
- **The mid marginal is a biased estimator under spreads.** Pricing off $\mu=(\mu_a+\mu_b)/2$ "can substantially underestimate" the robust superhedging price (46.84 vs 37.14 here); always report both the mid-marginal price and the bid–ask robust bound, and check that the calibrated pair is in convex order before trusting either (arXiv:2603.24605v2).
- **Free-boundary schemes have grid conditions that silently break monotonicity.** The maximum principle for the discrete Black–Scholes operator holds only for small $\Delta x$ with $0<w\le1$ and $\big|\frac{(r-q-\sigma^2/2)\Delta x}{\sigma^2}\big|\le1$; violating them invalidates the convergence-to-viscosity-solution argument (arXiv:1903.05189v1).
- **Validation protocol.** (i) Feynman–Kac cross-check against analytic benchmarks — Black–Scholes for the plain case, the bivariate-normal compound formulas for call-on-call/put-on-put (arXiv:2601.18634v2), the frictionless price at $\lambda=0$ for the band solver (arXiv:2603.29994v1); (ii) Richardson extrapolation in $h$ or $\Delta x$ plus Monte-Carlo standard errors; (iii) for robust bounds, a feasibility check on the potential functions $U_\mu(x)=\int|x-y|\mu(dy)$; (iv) for Greeks, a finite-difference agreement test only on smooth payoffs, where it is valid (arXiv:2405.00473v2).
- **Leakage.** MOT marginals are calibrated to the *same* quote date they are priced against, so any out-of-sample claim needs later chains; state-variable-driven drivers (macro, intensity) must be lagged to the decision date. Grid-boundary and in-sample mixture-fitting residuals are a look-ahead vector in disguise (arXiv:2603.24605v2, arXiv:2607.17502v1).

## 5. Recommended first implementation in FinRobot

1. **Forward Monte-Carlo BSDE/Feynman–Kac core (S).** Implement the forward Euler recursion of §2.1 with driver $f=-ry$ and a per-step regression readout for $Z$ (NumPy least squares, no `torch`). Data: equity OHLCV (`core_stock_apis`) + the Treasury curve (`risk_free_curve`). Value: it is the single shared engine underneath every pricing method in this category and unblocks compound/Bermudan payoffs with delta for free. Risk: Monte-Carlo variance and regression bias at low path counts (arXiv:2601.18634v2).
2. **Perpetual-American variational-inequality solver (S).** Port the explicit difference scheme of §2.6 with the closed-form boundary $j^\star$; a few dozen lines of NumPy. Data: OHLCV + `risk_free_curve` + dividends (`corporate_actions`). Value: a free-boundary/viscosity validation baseline in 1D that is trivial to check and that exercises the Greek machinery. Risk: perpetual/constant-coefficient scope; grid conditions must be enforced (arXiv:1903.05189v1).
3. **HJBQVI no-transaction band + Whalley–Wilmott (S→M).** Implement Algorithm 1 of §2.2 on a binomial tree with the holding grid and the Whalley–Wilmott half-width as the analytic prior; pure NumPy. Data: OHLCV + $\sigma$ (realised or `cboe`/`moomoo` implied) + `risk_free_curve`, $\lambda$ and $\gamma$ as inputs. Value: gives both the utility-indifference price and an implementable trading policy — the piece the corpus most directly converts to action. Risk: $\pm\Delta y$ trade restriction biases frequency; Whalley–Wilmott understates the band at large $\lambda$ (arXiv:2603.29994v1).
4. **Malliavin-weight Greeks (M).** Implement $\Delta^W=\mathbb E[f(S_T)Z_T/S_0]$ on a Merton-style jump-diffusion with constant intensity first, then add the CIR intensity term of §2.4. Data: OHLCV + `risk_free_curve`; jump parameters calibrated from historical returns (the CIR-intensity calibration is blocked, see row "default intensity"). Value: pathwise Greeks on discontinuous payoffs where finite differences lose an order of magnitude (MSE $3\times10^{-4}$ vs $0.02$). Risk: heavy-tailed weights; needs the Feller condition (arXiv:2405.00473v2).
5. **Robust bid–ask price bounds from the listed chain (M).** Calibrate log-normal-mixture bid/ask marginals to the SPX chain and solve the single-maturity primal/dual (LP on a strike grid) with the closed-form digital as a unit test. Data: `cboe` `options_surface` (delayed bid/ask) + `risk_free_curve`; `moomoo` `options_data` (gateway) as the live alternative. Value: honest price bounds for illiquid claims instead of a mid-price point estimate, and it is the only method here that consumes the option chain directly. Risk: mixture calibration and convex-order feasibility; the bound is wide by construction (arXiv:2603.24605v2).
6. **Mean-field equilibrium risk-premium solver (L, theory-first).** Build the coupled semilinear PDE system / fixed point of §2.3 in a Markovian factor model, but gate it behind the credit-intensity row of §3. Data: `fred` macro factors + OHLCV; the required default intensity/jump law is a **gap**. Value: an endogenous premium decomposition (Brownian vs default component) that no reduced-form model gives. Risk: short-horizon existence only, no closed form, and the discriminating input is unserved — treat as research until a credit feed exists (arXiv:2607.17502v1).
7. **Deep BSDE / deep hedging variants — out of scope for now (—).** The composite, no-transaction-band-network and free-boundary DNN variants all depend on `torch`, which the runtime dependency red line excludes; the classical forward-BSDE, difference-scheme and regression formulations above already cover the same pricing/stopping problems at these problem sizes (arXiv:2601.18634v2, arXiv:2603.29994v1). Revisit only if the runtime dependency policy changes.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2607.17502v1 | Mean-field equilibrium price formation under single-default risk | 2026 |
| 2603.29994v1 | Bridging Stochastic Control and Deep Hedging: Structural Priors for No-Transaction Band Networks | 2026 |
| 2603.24605v2 | Bid–Ask Martingale Optimal Transport | 2026 |
| 2601.18634v2 | The Compound BSDE Method: A Fully Forward Method for Option Pricing and Optimal Stopping Problems in Finance | 2026 |
| 2405.00473v2 | Pricing and delta computation in jump-diffusion models with stochastic intensity by Malliavin calculus | 2024 |
| 1903.05189v1 | Variational inequality for perpetual American option price and convergence to the solution of the difference equation | 2019 |
