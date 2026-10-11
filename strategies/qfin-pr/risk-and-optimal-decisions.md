# Risk Measures, Capital & Optimal Decisions — learnings from the q-fin.PR corpus
`197` of 2274 corpus papers matched this category (`195` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **VaR is a quantile and therefore not sub-additive; ES is the corpus' preferred rectification.** The counterparty dialogue states it directly — VaR "does not always acknowledge the benefits of diversification, in that in some paradoxical situations the risk of a total portfolio can be larger than the sum of the risks in the single positions", while expected shortfall (tail VaR, conditional VaR) is "a better measure from that point of view" (arXiv:1111.1331v3). The optimisation paper uses this pair and restricts to $0<\alpha\le 1/2$ (arXiv:1002.2487v1).
- **A VaR limit applied *only at maturity* can increase risk; a *uniform* (throughout-horizon) bound does not.** The paper cites Basak–Shapiro for the maturity-only pathology, then shows that with power (HARA) utility and a bound valid for all $t$, the optimum at sufficiently small risk level $\zeta$ is riskless — "not allowed to invest anything into risky assets at all, but consume everything". This resolves a genuine disagreement by horizon scope (arXiv:1002.2487v1).
- **The constrained optimum may not need the market coefficients.** For the VaR and ES problems the optimal controls "do not depend on the coefficients $(\mu_t)$ and $(\sigma_t)$ of the stock price"; those enter only the feasibility conditions, so "an upper bound for $\lVert\theta\rVert_T$ suffices" (arXiv:1002.2487v1).
- **Solvency II's capital requirement is a one-year 99.5% VaR of basic own funds, computable exactly as quantile hedging**: minimal $V_0$ with $E_P[\mathbf 1_{\{V_1\ge D\}}]=0.995$, i.e. maximise the *probability* of solvency rather than an expectation, handling market and non-market (insurance) risk jointly — something "usually neglected by insurance companies although this neglectance opposes widely accepted Black–Scholes approach" (arXiv:1405.1212v1).
- **Quantile hedging prices capital far below superhedging.** For a put on a non-tradable asset hedged with a *correlated* tradable asset, the success factor approaches the complete-market case as $\rho\to1$; at $\rho=1$ the strategy recovers the Black–Scholes cost 0.119235 ($K=1$, $T=1$, $\sigma=0.3$, zero rate), while lower $\rho$ cuts capital and lowers the success factor (arXiv:1405.1212v1).
- **Credit VaR and CVA use different measures inside one simulation.** Defaults and market variables are simulated under $P$ to the risk horizon; the residual portfolio beyond it is priced under $Q$. $Q$-measure default probabilities, implied from CDS or bonds, are "typically larger than those under the measure $P$". Credit VaR is the 99.9th percentile over a year; the exposure measures (CE, PFE, EE, EPE, EAD, MPFE) involve *no* default simulation, whereas Credit VaR does (arXiv:1111.1331v3).
- **Two-thirds of crisis counterparty losses came from CVA mark-to-market, not defaults.** Basel III: "roughly two-thirds of losses attributed to counterparty credit risk were due to CVA losses and only about one-third were due to actual defaults", which is why capital is charged against CVA volatility and not only default (arXiv:1111.1331v3).
- **Wrong-way-risk multipliers are not a robust capital tool.** "Depending on the specific dynamics of the underlying financial variables, on volatilities and correlations, and on the chosen models, the multipliers vary a lot … The multipliers are very volatile and fixing them is not a good idea" (arXiv:1111.1331v3).
- **Utility indifference prices *are* risk measures, and their computation reduces to information quantities.** The buyer's price $p^{bT}$ and minus the seller's price $-p^{sT}$ satisfy risk-measure properties; for HARA utilities the maximal expected utility is expressed through the relative entropy $I(P^u_T\Vert Q^{u,*}_T)$, the reverse entropy $I(Q^{u,*}_T\Vert P^u_T)$ and Hellinger-type integrals $H^{(q),*}_T$, and for exponential Lévy models the information processes are *deterministic*, which makes indifference prices tractable (arXiv:1303.1134v1).
- **Merton's problem extends to stochastic coefficients, and its hedging term reappears.** With an external diffusion factor $Y$ the optimal fraction is the Merton term plus a factor-hedging term in $D_yh$; the decomposition collapses to Merton exactly when the factor is independent of the traded Brownian motion ($\rho=1$) (arXiv:1102.1186v2).
- **Best-in-class American value comes from forward-learning the exercise rule, not finer backward recursion.** LSMC's discretisation error and its error back-propagation "directly conflict"; Bermudan solvers are conventionally kept below $N<100$ steps and the Bermudan–American gap is $O(N^{-1})$. A forward-RL solver learning a joint space–time boundary (CARLOS) captures more than 90% of the gap on a 2-d max-call at 3–10× the speed of a fine-grid neural comparator (arXiv:2606.17545v1).
- **The exercise-frequency trade-off is two-sided.** For a fixed solver grid the highest rewards occur at an *intermediate* exercise frequency; "making $\Delta t^{ex}$ extremely small may lead to lower rewards", and infrequent stopping "leaves money on the table". Classical max-call benchmarks use as few as 9 exercise dates over 3 years, an "extreme example of Bermudization" (arXiv:2606.17545v1).

## 2. Implementable formulas & algorithms

### 2.1 Uniform VaR/ES-constrained Merton problem (explicit feedback form)
**Purpose.** Maximise expected power utility of consumption plus terminal wealth under a *uniform* VaR or ES budget, with the optimum in closed feedback form.

With $y_t=\sigma_t'\pi_t$, $\theta_t=\sigma_t^{-1}(\mu_t-r_t\mathbf 1)$:
$$dX_t = X_t\big(r_t+y_t'\theta_t\big)dt - c_t\,dt + X_t y_t'\,dW_t,\qquad X_0=x,$$
$$\mathrm{VaR}_t(x,\varsigma,\alpha)=xe^{R_t}-\lambda_t,\quad
\lambda_t=x\exp\!\Big(R_t-V_t+(y,\theta)_t-\tfrac12\lVert y\rVert_t^2-|z_\alpha|\,\lVert y\rVert_t\Big),$$
$$m_t(x,\varsigma,\alpha)=xF_\alpha\!\big(|z_\alpha|+\lVert y\rVert_t\big)e^{R_t+(y,\theta)_t-V_t},\quad
\mathrm{ES}_t=xe^{R_t}-m_t,\quad
F_\alpha(z)=\frac{\int_z^\infty t\,e^{-t^2/2}dt}{\int_{|z_\alpha|}^\infty e^{-t^2/2}dt},$$
where $z_\alpha$ is the normal $\alpha$-quantile, $R_t=\int_0^t r_u du$, $V_t=\int_0^t v_u du$, $(y,\theta)_t=\int_0^t y_u'\theta_u\,du$. The *level risk function* is $\zeta_t(x)=\zeta\,xe^{R_t}$; the admissible set is $\sup_t \mathrm{VaR}_t/\zeta_t\le1$ (resp. ES). For $\gamma_1=\gamma_2=1$ the VaR-optimal control is Merton scaled by a risk budget,
$$\rho^\ast_{\mathrm{VaR}}=\sqrt{(|z_\alpha|-\lVert\theta\rVert_T)^2-2\ln(1-\zeta)}-\big(|z_\alpha|-\lVert\theta\rVert_T\big),\qquad
y_t^\ast=\rho^\ast_{\mathrm{VaR}}\frac{\theta_t}{\lVert\theta\rVert_T},\ v_t^\ast=0,$$
feasible for $\max\!\big(0,1-e^{z_\alpha^2/2-|z_\alpha|\lVert\theta\rVert_T}\big)<\zeta<1$. For ES the same form holds with $\rho^\ast_{\mathrm{ES}}=\sup\{\rho>0:\psi(\rho,1)\ge\ln(1-\zeta)\}$, $\psi(\rho,u)=\lVert\theta\rVert_T\rho u^2+\ln F_\alpha(|z_\alpha|+\rho u)$.

- **Inputs:** daily return panel; a risk-free curve for $r_t$; an estimate or upper bound for $\lVert\theta\rVert_T$.
- **Parameters:** curvature $0<\gamma_i\le1$; investor risk level $\zeta\in(0,1)$; regulator confidence $\alpha\in(0,1/2]$; horizon $T$.
- **Observed effects:** for $0<\gamma_1<1$, $\gamma_2\le1$ and small $\zeta$ the optimum collapses to $y_t^\ast=0$, $v_t^\ast=\zeta\,\hat g_1^{q}(t)/\big(\lVert\hat g_1\rVert^q_{q,T}-\zeta\lVert\hat g_1\rVert^q_{q,t}\big)$ and $X_t^\ast=x\,e^{R_t}\big(\lVert\hat g_1\rVert^q_{q,T}-\zeta\lVert\hat g_1\rVert^q_{q,t}\big)/\lVert\hat g_1\rVert^q_{q,T}$ — deterministic, no risky investment; linear utility instead goes all-in and consumes nothing (arXiv:1002.2487v1).
- **Failure modes:** maturity-only VaR bounds raise risk, so the constraint must hold for all $t$; near-unit $\lVert\theta\rVert_T$ makes $\rho^\ast$ fragile; closed forms assume deterministic (càdlàg) coefficients, not stochastic volatility (arXiv:1002.2487v1).

### 2.2 Quantile hedging for Solvency II capital
**Purpose.** Find the minimal capital $V_0$ (and its strategy) such that the probability of covering a liability $D$ meets a set level.

In an incomplete market with $F=F_T$ possibly enlarged by non-market information, and $dW_Y=\rho\,dW_X+\sqrt{1-\rho^2}\,dW$, with $\mathcal A=\{(V_0,\pi):V_0\le\tilde V_0\}$:
$$\text{find }(V_0^\ast,\pi^\ast)\ \text{maximising}\quad E_P\!\Big[g\big(V_T/D\big)\Big],\quad g\in\big\{v\mapsto\mathbf 1_{\{v\ge d\}},\ v\mapsto \mathbf 1_{\{v\ge d\}}+\tfrac{v}{d}\mathbf 1_{\{v<d\}}\big\},$$
where $g$ is the *success factor*. The optimal claim is the Neyman–Pearson truncated claim: for a chosen $Q\in\mathcal P$,
$$G_Q(x)=E_Q\!\Big[\tfrac{dP}{dQ}\,D\,\mathbf 1_{\{D\le x\}}\Big],\qquad
\bar g^m=\min\{x:g(x)=\hat g^m(x)\},$$
with $\hat g^m$ the highest line of slope $m$ touching $g$ from above; $m$ is the capital price, tracing the frontier. Solvency II special case: $T=1$, $D$ the undertaking's total liabilities, success factor $\mathbf 1_{\{V_T\ge D\}}$, target $E[\mathbf 1_{\{V_1\ge D\}}]=0.995$. Monte Carlo: draw $w_1,\dots,w_{N_W}\sim N(0,T)$, for each $i$ solve the pathwise $\max_x$ and set
$$V_0(m)\approx \tfrac1{N_W}\sum_i \exp\!\Big(\tfrac{|w_i|^2}{2T}\Big)x^{\max}(i).$$

- **Inputs:** tradable price series (plus the non-tradable proxy); implied/estimated volatilities; correlation $\rho$.
- **Parameters:** $\rho\in[0,1]$; multiplier $m\ge0$ (capital budget); grid $N_x$, path count $N_W$; reference strike and maturity.
- **Observed effects:** at $\rho=1$ the hedge reduces to Black–Scholes and costs 0.119235 ($K=1$, $T=1$, $\sigma=0.3$, zero rate); lower $\rho$ reduces capital but lowers the success factor; the Solvency II application fixes success at 0.995 and reads off minimal $V_0$ (arXiv:1405.1212v1).
- **Failure modes:** $m$ must be found numerically; the construction depends on $\rho$ and on the unobservable growth/volatility of the non-traded asset; without a liquid CDS/bond for the underlying the $Q$-dynamics are unavailable (arXiv:1405.1212v1, arXiv:1111.1331v3).

### 2.3 Credit VaR, exposure and CVA
**Purpose.** Measure capital against counterparty default and price the counterparty-risk charge on OTC books.

$$E(t)=\max(V(t),0),\quad \mathrm{EE}(t)=E_P[E(t)],\quad
\mathrm{EPE}=\tfrac1T\!\int_0^T\!\!\mathrm{EE}(t)\,dt,\quad
\mathrm{PFE}_{95}(t)=q_{0.95}(E(t)),$$
with $\mathrm{MPFE}=\max_t \mathrm{PFE}(t)$ and $\mathrm{EAD}=E(\tau)$ at the random default time $\tau$. Credit VaR is the 99.9% (one-year) loss quantile obtained by simulating market variables *and* defaults under $P$ to the horizon and pricing the residual under $Q$. CVA is a call option on residual value with random maturity $\tau$:
$$\mathrm{CVA}=(1-R)\,E_Q\!\Big[\int_0^T D(0,t)\,\mathrm{EE}(t)\,dP_D(t)\Big],$$
with recovery $R$, discount $D(0,t)$ and $Q$-default probability $P_D$. Bilateral adjustment uses first-to-default: $\mathrm{BVA}=\mathrm{DVA}-\mathrm{CVA}$, where the survivor's term activates and the other vanishes at $\min(\tau_{\text{bank}},\tau_{\text{cpty}})$. Basel III additionally requires VaR *of CVA*: simulate under $P$ to the horizon, re-price residual CVA under $Q$ per scenario, take the loss quantile.

- **Inputs:** portfolio and market factors; per-counterparty $P$ and $Q$ default probabilities; recoveries; collateral/margin schedules; netting sets.
- **Parameters:** horizon (1 year); confidence 99.9% (Credit VaR) / 95% (PFE); recovery (industry default 0.4); closeout convention (risk-free vs replacement); margining frequency; credit–underlying correlation (WWR).
- **Observed effects:** netting lowers unilateral CVA ("an option on a sum is smaller than the sum of options"); risk-free closeout can make a net debtor's liability *jump up* at a creditor default while replacement closeout can under-recover for creditors; $+1$M and $-1$M swaps net to zero loss, without netting the bank loses $(1-R)\cdot1\text{M}=0.6$M at $R=0.4$ (arXiv:1111.1331v3).
- **Failure modes:** model dependence — pricing an option on a swap book needs a rate-option model even if the book was model-independent; single-firm $P$ default probability is not directly observable; $P$–$Q$ gaps; WWR multipliers are unstable; funding makes the price a recursive (BSDE/backward-induction) problem, not RISK-FREE $+$ DVA $-$ CVA $+$ FVA (arXiv:1111.1331v3).

### 2.4 Utility indifference pricing and HARA information quantities
**Purpose.** Price a non-traded claim from the investor's own utility in a semimartingale model with a random factor, computing it from information quantities rather than by optimising controls.

$$V_T(x;g)=\sup_{\pi}E_P\!\Big[U\Big(x+\int_0^T\pi_s\,dS_s+g\Big)\Big],\qquad
V_T(x;0)=\sup_{\pi}E_P\!\Big[U\Big(x+\int_0^T\pi_s\,dS_s\Big)\Big],$$
with buyer/seller prices solving
$$V_T\big(x-p^{bT};g\big)=V_T(x),\qquad V_T\big(x+p^{sT};g\big)=V_T(x).$$
For HARA utilities the value *without* the claim is
$$V_T(x;0)=\int\big[\ln x+I(P^u_T\Vert Q^{u,*}_T)\big]\,\mu(du)\quad(\text{log case}),$$
the power case is written through the Hellinger-type integral $H^{(q),*}_T(u)=E_{P^u}\big[(\tilde Z_T(u))^{q}\big]$ with $q=\tfrac{p}{p-1}$, and the exponential case through the reverse entropy $I(Q^{u,*}_T\Vert P^u_T)$; replacing $x\mapsto x+g(u)$ gives $V_T(x;g)$. Information processes are the predictable integrands, e.g. for the log case
$$I_t(u)=\tfrac12\int_0^t(\varsigma_{su})^2\,dC_s-\int_0^t\!\!\int_{\mathbb R}\big(\ln(Y_{su}(x))-Y_{su}(x)+1\big)\,\nu^u(ds,dx),\quad I(P^u_T\Vert Q^{u,*}_T)=E_{P^u}I_T(u).$$

- **Inputs:** tradable price series and the factor (joint law); the claim payoff $g$; utility parameters.
- **Parameters:** HARA family (log / power $p<1$ / exponential $\gamma>0$); the $f$-divergence minimal martingale measure $Q^{u,*}$ (parameter $q=p/(p-1)$).
- **Observed effects:** $p^{bT}(g)$ and $-p^{sT}(g)$ behave as risk measures (monotone, translation-invariant, convex under HARA); for exponential Lévy models the information processes are deterministic, so the entropy integrals are closed-form (arXiv:1303.1134v1).
- **Failure modes:** the price depends on the utility choice and the agent's information level (non-informed / perfectly informed); Assumptions 1–4 (absolute continuity of conditional laws, existence of the $f$-divergence minimal measure) can fail; closed-form values are proven only for HARA (arXiv:1303.1134v1).

### 2.5 Consumption–investment with stochastic coefficients (CRRA, HJB + Feynman–Kac)
**Purpose.** Solve the Merton consumption/investment problem when $r,\mu,\sigma$ depend on an external diffusion factor, with a provably convergent fixed-point scheme.

$$dX_t=X_t\big(r(t,Y_t)+\pi_t'\theta(t,Y_t)-c_t\big)dt+X_t\pi_t'\,dW_t,\quad
dY_t=F(t,Y_t)dt+\beta\,dU_t,\quad U_t=\rho V_t+\sqrt{1-\rho^2}\,\sigma_*W_t,$$
$$\theta(t,y)=\sigma^{-1}(t,y)\big(\mu(t,y)-r(t,y)\mathbf 1_d\big),\qquad
\max_{\vartheta\in V}E_{x,y}\!\Big[\int_0^T c_t^\gamma (X_t^\vartheta)^\gamma dt+(X_T^\vartheta)^\gamma\Big].$$
With the distortion $z(t,\varsigma)=x^\gamma h^{\varepsilon}(t,y)$, $\varepsilon=\tfrac{1-\gamma}{1-\rho^2\gamma}$, $h$ solves the quasilinear PDE
$$h_t+Q(t,y)h+\alpha(t,y)'D_yh+\tfrac{\beta^2}{2}\operatorname{tr}D_{y,y}h+q_*\big(\tfrac1h\big)^{q_*-1}=0,\quad h(T,y)=1,$$
and the Feynman–Kac map $L_f(t,y)=E\big[G(t,T,y)+\tfrac1{q_*}\int_t^T H_f(t,s,y)ds\big]$ is a contraction with $\lambda=\tfrac{1+mL_*}{\zeta+1+mL_*}$. The optimal strategy is explicit in $h$:
$$\pi^\ast(t,y)=\frac{\theta(t,y)}{1-\gamma}+\frac{\varepsilon\sqrt{1-\rho^2}\,\beta\,\sigma_*D_yh(t,y)}{(1-\gamma)h(t,y)},\qquad
c^\ast(t,y)=h(t,y)^{-q_*},\qquad \max J=x^\gamma h(0,y)^{\varepsilon}.$$

- **Inputs:** factor and price histories (to fit $r,\mu,\sigma,F,\beta,\rho$); initial endowment and horizon.
- **Parameters:** CRRA $\gamma\in(0,1)$; $\rho\in[0,1]$; $\sigma_*$ with $\sigma_*\sigma_*'=I_m$.
- **Observed effects:** $\rho=1$ recovers Merton; $\rho<1$ adds a factor-hedging term in $D_yh$; the iteration $h_0\equiv1$, $h_n=L_{h_{n-1}}$ converges *super-geometrically*, $U_n^\ast=O(n^{-\delta n})$; numerically with $\gamma=0.75$ the error is $\delta_5\simeq10^{-4}$, $\delta_8\simeq10^{-8}$, $\delta_{14}\simeq10^{-16}$ and identically zero for $n\ge15$ (arXiv:1102.1186v2).
- **Failure modes:** the bound is proven only for power utility $x^\gamma$, $0<\gamma<1$; the nonlinear second-order PDE requires coefficient regularity ($A_1$–$A_3$); the factor $Y$ must be observable, which in stochastic-volatility applications it is not directly (arXiv:1102.1186v2).

### 2.6 Continuous-time optimal stopping by aggregate-network RL (CARLOS)
**Purpose.** Learn the American-style exercise boundary at arbitrarily fine time resolution, sidestepping LSMC backward-recursion error and the Bermudan–American gap.

$$V^{(N)}(t_n,x)=\sup_{\tau\in\mathcal T_n}E\big[e^{-r(\tau-t_n)}h(X_\tau)\,\big|\,X_{t_n}=x\big],\qquad
V(t,x)=\sup_{\tau\in\mathcal T_t}E\big[e^{-r(\tau-t)}h(X_\tau)\,\big|\,X_t=x\big],$$
with $V^{(N)}\uparrow V$ and gap $O(N^{-1})$. The timing value $T(t,x)=\tilde q(t,x)-h(x)$ gives the Snell rule $\tau_n^\star=\min\{t_k:\ T(t_k,X_{t_k})\le0\}$ and $\phi(t,x)=\mathbf 1_{\{\hat T(t,x)\le 0,\ h(x)\ge0\}\ \text{or}\ t=T\}}$. CARLOS alternates (1a) a coarse LSMC pass, (1b) training an aggregate DNN $R^\Theta:\mathbb R^{d+1}\to\mathbb R$ on $(t,x)$ jointly, and (2) about a dozen RL loops over 3–6 nested grids, halving $\Delta t^{tr}$ once validation reward differences $D^{[\ell]}=\Upsilon^{[\ell]}-\Upsilon^{[\ell-1]}$ become statistically insignificant, with learning rate $\eta^{[b+1]}=\alpha_{dec}\eta^{[b]}$, $\eta^{[0]}=10^{-4}$, $\alpha_{dec}=0.7$. Delayed stopping and boundary-concentrated sampling counter concept drift and the shrinking stopping region.

- **Inputs:** a parametric $X$ (Black–Scholes / Monte-Carlo generator), payoff $h$, discount $r$; market history is not strictly required (model-based RL).
- **Parameters:** grid ladder $\Delta t^{tr,0}\!\to\!\Delta t^{tr,B}$ (e.g. $1/6\to1/96$); per-loop training size; RL loops; learning rate/decay; validation path set.
- **Observed effects:** B1 put ($X_0=36,K=40,T=1,r=0.05,\sigma=0.2$): CARLOS 4.592 vs PDE 4.601; M2 max-call ($d=2$, $X_0=100,K=100,T=3,r=0.05,\sigma=0.2,\delta=(0.1,0.1)$): CARLOS 14.171 vs PDE 14.214 vs Bermudan ($\Delta t=1/3$) 13.901 — capturing >90% of a >30-cent (2%+) gap; speed-ups 3–5× (up to 10× on M3); 1.6M Monte-Carlo paths for pricing (arXiv:2606.17545v1).
- **Failure modes:** non-monotone training (a loop can overshoot near maturity and recover at the next grid); both too-coarse and too-fine exercise grids reduce reward; as $\Delta t\to0$ the smooth-fit condition makes near-boundary classification delicate; benchmarked in $d\le5$, not truly high dimensions (arXiv:2606.17545v1).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Equity daily OHLCV (returns, portfolio, VaR/ES series) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok — alternates: tiingo/twelvedata/stockdata/massive/finnhub/fmp |
| Dividend / corporate-action calendar (dividend yield $\delta$) | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Risk-free discount curve ($r_t$, discount factors) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok — ~17s fetch, 45s adapter timeout |
| Macro state (credit spread, term spread, rates) for stress | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Implied vol surface / risk-neutral inputs (SPX options) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Listed option chain (early-exercise premium) | `moomoo://get_option_chain` | options_data | moomoo | gateway — local OpenD SDK |
| Expected move / implied one-sigma | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway — local OpenD SDK |
| Issuer fundamentals (credit-quality proxies) | `https://financialmodelingprep.com/stable/income-statement` | fundamental_data | fmp | ok |
| Filings (counterparty disclosure) | `https://data.sec.gov/submissions/CIK0000320193.json` | sec_filings | sec_edgar | ok — filings only, no agency ratings |
| Analyst ratings (credit/sentiment proxy) | `https://api.benzinga.com/api/v2.1/calendar/ratings` | analyst_ratings | benzinga | ok |
| News / systemic-risk state for stress overlays | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| Event contracts (macro outcome probabilities, optional) | `https://gamma-api.polymarket.com/markets` | prediction_markets | polymarket | ok |
| CDS / corporate-bond spreads and counterparty default probabilities ($P$ and $Q$) — Credit VaR and CVA inputs | **gap** — no credit/credit-spread feed | — | — | gap |
| Recovery rates (LGD) / credit-spread volatility | **gap** — no source | — | — | gap |
| Credit–underlying correlation (wrong-way risk) | **gap** — no credit/underlying joint series | — | — | gap |
| Collateral, margin, netting-set and closeout terms | **gap** — contract/legal data, not a market feed | — | — | gap |
| Swap / swaption / interest-rate volatility (CVA model dependence) | **gap** — no swaption or rates-vol feed | — | — | gap |
| Mortality / longevity rates (Solvency II insurance risk) | **gap** — no mortality feed | — | — | gap |
| Intraday ticks / sub-daily paths (gap risk, continuous exercise) | **gap** — no certified intraday or order-book feed | — | — | gap |

Row count: 19 — `ok` = 10, `gateway` = 2, `fail` = 0, `gap` = 7. (Affiliate equity-OHLCV providers are folded into one row; the prediction-markets row is optional.)

## 4. Pitfalls, validation and measurement

- **VaR is not coherent.** It fails sub-additivity, so desk-level VaR cannot be summed and portfolio VaR can exceed the sum of constituent VaRs; report ES alongside (arXiv:1111.1331v3). ES is not elicitable alone, so validate the VaR/ES *pair* jointly rather than ES in isolation.
- **Measure inconsistency is the classic credit leakage.** Simulating defaults under $P$ but pricing the residual under $Q$ is correct only if the stages stay separate; using $Q$ default probabilities in the $P$ simulation, or mixing horizons, biases Credit VaR. $Q$ probabilities "are typically larger than those under the measure $P$" (arXiv:1111.1331v3).
- **Single-firm default probabilities cannot be estimated from history.** "Default of a single firm occurs only once, so determining the $P$ probability through direct historical observation is not possible"; the paper falls back to rating-aggregated defaults with acknowledged agency problems. A flat 0.4 recovery is a modelling choice, not data (arXiv:1111.1331v3).
- **Wrong-way risk is not a multiplier problem.** Computing CVA under independence and scaling by a standard WWR factor is invalid: the multipliers "vary a lot" with dynamics, volatilities, correlations and model choice and this "could lead to bitter surprises in situations of systemic risk" (arXiv:1111.1331v3). Calibrate WWR in-model and stress it.
- **Model and payoff risk in CVA.** Model-independent books become model-dependent once CVA is added (it is an option on residual value with random maturity); different closeout, collateral, re-hypothecation and first-to-default conventions give materially different numbers, so a CVA figure is comparable only with an explicit convention attached (arXiv:1111.1331v3).
- **Horizon scope changes a risk limit's effect.** A maturity-only VaR bound can raise risk; the uniform bound does not, and with power utility and small $\zeta$ the optimum becomes risk-free. Any risk-limit implementation must state and enforce the monitoring frequency and test whether the limit is active (arXiv:1002.2487v1).
- **Dependence risk dominates quantile hedging.** The success factor is driven by $\rho$, the correlation between the hedging asset and the non-tradable underlying; a mis-estimated $\rho$ mis-states both capital and success probability (arXiv:1405.1212v1). Validate with a sensitivity sweep, not a point estimate.
- **Indifference prices are utility- and information-dependent.** Buyer/seller prices, the $f$-divergence minimal measure and the agent's information level all enter; closed forms hold for HARA and (deterministically) exponential Lévy models, and the §2.5 convergence bound is proven for power utility only (arXiv:1303.1134v1, arXiv:1102.1186v2 Remark 3.3).
- **Iterative schemes must report their error bound.** For the HJB fixed-point scheme, log the per-iteration $\delta_n=\sup_{t,y}|h_n-h_{n-1}|$ and the optimal bound $U_n^\ast$; convergence is super-geometric, so a fixed iteration count (machine precision by $n=14$–15 in the paper's example) must be justified against the fitted coefficients (arXiv:1102.1186v2).
- **Optimal-stopping solvers have two discretisations.** The solver grid $\Delta t^{tr}$ and the forward exercise grid $\Delta t^{ex}$ are distinct; keeping them equal while refining both is expensive and eventually counter-productive, and reward differences between successive configurations should be tested for significance before claiming an improvement. Final prices need an independent forward Monte-Carlo re-evaluation — never reuse the training reward as the price (arXiv:2606.17545v1).
- **Look-ahead and in-sample leakage.** In RL/LSMC stopping, the rule is trained on simulated paths and evaluated on fresh ones, and the grid-refinement decision is driven by *validation*-path reward differences (arXiv:2606.17545v1). In VaR/ES backtests use rolling windows and out-of-sample quantiles; in quantile hedging and Credit VaR align the simulation horizon, the pricing horizon and the $P/Q$ switch, and never let calibration overlap evaluation.
- **Comparators.** Use a model confidence set or Diebold–Mariano-type test rather than a single point estimate: CARLOS benchmarks are means over five seeds with standard deviations and adjacent-grid differences flagged at the 5% and 1% levels (arXiv:2606.17545v1). For solvency/capital, report the capital–success frontier (vary $m$) rather than one number (arXiv:1405.1212v1).

## 5. Recommended first implementation in FinRobot

1. **Risk-factor and risk-measure layer (S).** Pull the equity panel (`https://eodhd.com/api/eod/AAPL` with tiingo/twelvedata fallbacks) plus the Treasury curve (`risk_free_curve`) and the FRED macro block (`macro_data`); compute historical and parametric VaR/ES at 95/99% on 1-day and 1-year horizons. Data: core_stock_apis + risk_free_curve + macro_data (all `ok`). Value: every later risk/capital module consumes this and it needs no derivatives contract. Risk: quantile estimates are noisy in the tails — report ES alongside VaR with rolling windows (arXiv:1111.1331v3, arXiv:1002.2487v1).
2. **Uniform VaR/ES-constrained consumption–investment solver (S/M).** Implement §2.1's closed forms: the quantile/ES formulas, the level-risk function, activation conditions and the explicit optimal control for linear and HARA cases. Data: the panel from item 1 + the risk-free curve. Value: the corpus' core risk-constrained optimisation, with the "go riskless when $\zeta$ is small" result as a built-in sanity check. Risk: needs an upper bound on $\lVert\theta\rVert_T$; the closed form assumes deterministic coefficients (arXiv:1002.2487v1).
3. **American-exercise engine on served equity + options data (M).** Implement LSMC plus the CARLOS refinement (aggregate DNN over $(t,x)$ with grid halving and significance-gated refinement), priced off `core_stock_apis` returns, `corporate_actions` dividend yields and `risk_free_curve`; validate against the chain from `moomoo://get_option_chain` (gateway) where available. Data: core_stock_apis + corporate_actions + risk_free_curve (`ok`), options_data (`gateway`). Value: exercise-timing optionality is directly testable against `cboe` SPX and `moomoo` quotes. Risk: needs an options-enabled environment for validation; keep the final price on an independent forward pass (arXiv:2606.17545v1).
4. **Solvency-II / quantile-hedging capital module (M).** Implement §2.2: the success-factor objective, the Neyman–Pearson multiplier, the Monte-Carlo capital/success frontier and the 0.995 one-year calibration; feed volatilities and correlations from `cboe`/`options_surface` and the curve from `risk_free_curve`. Data: options_surface + risk_free_curve (`ok`) + the panel. Value: a regulator-shaped capital number with an explicit trade-off, reusing the option surface already available. Risk: the non-traded underlying and its correlation $\rho$ are unobservable — sweep, do not assume (arXiv:1405.1212v1).
5. **Utility-indifference pricing module (M).** Implement §2.4 for HARA utilities through the entropy/Hellinger information quantities, with the exponential-Lévy special case where information processes are deterministic. Data: the equity panel + factor series + the curve. Value: bid/ask-style price bounds consistent with risk preferences and risk-measure outputs, complementing items 1–2. Risk: results are utility-dependent; test the minimal-measure existence assumptions before use (arXiv:1303.1134v1).
6. **Credit-VaR / CVA prototype behind a synthetic-credit adapter (L).** Implement §2.3 (exposure statistics, $P$-sim→$Q$-price Credit VaR, CVA/BVA with first-to-default, CVA-VaR) driven by user-supplied or synthetic default probabilities and recoveries, because the inventory has *no* credit/CDS/spread feed. Data: portfolio factors from `core_stock_apis` + `options_surface`; credit inputs are `gap`. Value: builds the full engine so it runs the moment a credit source is added, and pins the exposure/CVA distinction. Risk: unservable today — every credit input must be injected and WWR cannot be calibrated from inventory data (arXiv:1111.1331v3).
7. **Defer funding/FVA, closeout-convention and margin-lending structures (—).** Funding makes pricing a recursive BSDE/backward-induction problem (not the additive RISK-FREE + DVA − CVA + FVA), closeout choice determines whether contagion hits borrowers or lenders, and margin lending needs a global valuation framework; none is supported by served data. Mark out of scope until the credit layer exists (arXiv:1111.1331v3).

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2606.17545v1 | Continuous-time Optimal Stopping through Deep Reinforcement Learning | 2026 |
| 1405.1212v1 | Market risk modelling in Solvency II regime and hedging options not using underlying | 2014 |
| 1303.1134v1 | Utility maximisation and utility indifference price for exponential semi-martingale models with random factor | 2013 |
| 1102.1186v2 | Optimal consumption and investment for markets with random coefficients | 2011 |
| 1111.1331v3 | Counterparty Risk FAQ: Credit VaR, PFE, CVA, DVA, Closeout, Netting, Collateral, Re-hypothecation, WWR, Basel, Funding, CCDS and Margin Lending | 2011 |
| 1002.2487v1 | Optimal consumption and investment with bounded downside risk for power utility functions | 2010 |
