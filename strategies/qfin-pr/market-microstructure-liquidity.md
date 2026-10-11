# Market Microstructure & Liquidity — learnings from the q-fin.PR corpus
`160` of 2274 corpus papers matched this category (`159` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **Microstructure noise can be folded into a *complete* market as an extra, correlated volatility term.** Modelling the observed price as its efficient part plus a noise term driven by the *same* Brownian sign process, $dS_t=\mu_tS_tdt+\sigma_tS_tdB_t+\epsilon_tS_tdH_t$ with $H_t=\int_0^t\operatorname{sgn}(B_s)\,dB_s=|B_t|-L_t$ (local-time representation), keeps the market complete and yields the familiar BSM option price with $\sigma$ replaced by the noise-augmented volatility $\sigma+\epsilon$ and market price of risk $\theta=(\mu-r)/(\sigma+\epsilon)$. Using an *independent* second Brownian motion instead would make the market incomplete and break perfect hedging (arXiv:2511.00308v1).
- **The implied-noise surface on SPX options is large and sign-unstable, and its dominant empirical source is stale quotes.** Computing an implied $\epsilon(T,K)$ surface by matching the noise-augmented BSM to the 21-Apr-2025 SPX call chain gives $\hat\sigma^{(hist)}=0.0112$ vs $\hat\sigma^{(AG)}=0.0292$ (an ARMA(3,3)–GARCH(1,1) fit); the calibrated noise volatility is $\hat\sigma^{(n)}=0.0028$ for short maturities (25% of the observable $\sigma^{(o)}$) and $8.42\times10^{-4}$ for long ones (7.5%). Implied $\epsilon$ tracks the BSM smile and turns strongly negative out of the money; the authors attribute this mainly to asynchronous trading and stale *last-price* prints, not to a physical diffusion (arXiv:2511.00308v1).
- **Pool depth mechanically sets the volatility structure of a constant-product AMM, so option prices there obey a CEV law, not GBM.** When net flow into a pool of invariant $x^wy^{1-w}=K$ is a Brownian diffusion, the token price follows $dP=\mu(P)dt+\delta P^\beta dW$ with $\beta=w$ exactly; for $w=\tfrac12$ the exponent is $\tfrac12$ and instantaneous return volatility is $\sigma_{ret}(P)=\delta P^{-1/2}$, an *endogenous* leverage effect (arXiv:2603.29763v1).
- **The CEV correction is a pure skew effect that is depth-invariant when normalised.** Black–Scholes underprices 20%-out-of-the-money puts by roughly 6% in implied-volatility terms at *every* pool depth, while the absolute pricing discrepancy vanishes as $O(k^{-1})$ and the ATM prices are visually identical; the normalised implied-vol skew depends only on $\beta$, not on $\delta$ or $k$ (arXiv:2603.29763v1).
- **The predicted variance elasticity survives a cross-section.** Realised return variance should scale as $P^{2(\beta-1)}=P^{-1}$ for a constant-product pool; across 90 Bittensor subnets the median elasticity is $-0.86$ (IQR $[-0.98,-0.71]$), decisively rejecting the GBM null of zero ($p<0.0001$), and a delta-hedged backtest over 82 subnets shows near-identical ATM hedging errors — differences concentrate in the wings (arXiv:2603.29763v1).
- **Derivative liquidity forecasting is a replication problem, not an expectation problem.** Undiscounted expectations under different numeraires $\mathbb{Q}^N$ disagree; netting a long and a short payoff in different measures leaves a residual $(T_2-T_1)\mathbb{E}^{\mathbb{Q}^{P(T_2)}}(L^2)$ that, for a Black-type lognormal forward, becomes $(T_2-T_1)L_0^2e^{\sigma_L^2T_1}$ — exponentially increasing in variance and horizon. Funding *sensitivities* (hedge ratios w.r.t. the funding curve) are replication-consistent where static expected cash-flows are not (arXiv:2605.00862v1).
- **Stochastic payment times break the additivity of risk-neutral bucket values.** For a unit cash-flow paid at a stopping time $\tau$, the risk-neutral per-bucket values $E_i$ satisfy $\sum_i E_i=1$ only if $\tau$ is independent of the discounting numeraire; otherwise it can differ, with a relative inconsistency that grows toward 100% as the payment-time difference widens (arXiv:2605.00862v1).
- **Under transient price impact the super-replication cost is a convex risk measure with a liquidity-weighted $L^2$ penalty, and buy-and-hold is optimal for calls.** The half-spread follows $d\zeta_t^X=\tfrac{1}{\delta_t}(dX_t^\uparrow+dX_t^\downarrow)-r_t\zeta_t^Xdt$ (market depth $\delta$, resilience $r$) on top of permanent impact $\iota X_t$; transaction costs grow *quadratically* when a strategy is scaled, so no admissibility notion is needed and the dual is convex, not coherent (arXiv:1808.09807v2).
- **Indifference pricing with real bid-ask quotes produces sparse, practical static hedges.** Using finite quantities at the best bid/ask for ~400 SPX options, forwards and cash, the optimal static hedge of a call, digital, quadratic forward or log-forward has nonzero positions in fewer than 10 of the quoted strikes; removing the bid-ask spread makes the optimal portfolio dense and takes maximal allowed size at many strikes. The indifference selling/buying band is much narrower than the super-/subhedging band (call: 51.73/51.74 vs 53.05/51.23) (arXiv:1803.02486v1).
- **A market maker's inventory problem with stochastic price impact reduces to three BSDEs.** With uncertain customer orders and both a continuous-trading venue (linear stochastic impact) and an uncertain-timing dark pool, the value function is quadratic, $V(t,x)=V_2(t)x^2+2V_1(t)x+V_0(t)$, and gives an adapted (not deterministic) optimal policy from one non-linear and two linear BSDEs (arXiv:1503.07007v2).

## 2. Implementable formulas & algorithms

### 2.1 Noise-augmented Black–Scholes and the implied-$\epsilon$ surface
**Purpose.** Price European options when the traded price carries microstructure noise, preserving market completeness so that a single effective volatility applies.

Price dynamics and noise process:
$$ dS_t=\mu_tS_t\,dt+\sigma_tS_t\,dB_t+\epsilon_tS_t\,dH_t,\qquad H_t=\int_0^t\operatorname{sgn}(B_s)\,dB_s=|B_t|-L_t, $$
where $L_t$ is the local time of $B$ at zero. The replicating-portfolio PDE is
$$ \frac{\partial f}{\partial t}+r x\frac{\partial f}{\partial x}+\tfrac12\big[\sigma+\epsilon\big]^2x^2\frac{\partial^2 f}{\partial x^2}-rf=0,\qquad f(x,T)=g(x), $$
and the constant-coefficient call is the BSM formula with $\sigma\mapsto\sigma+\epsilon$:
$$ C=S_t\Phi(u^+)-e^{-r(T-t)}K\Phi(u^-),\quad u^\pm=\frac{\ln\!\big(S_t/K\big)+\big(r\pm\tfrac{(\sigma+\epsilon)^2}{2}\big)(T-t)}{(\sigma+\epsilon)\sqrt{T-t}}. $$
The implied noise is the minimiser of a relative-error fit,
$$ \epsilon^{(imp)}(t;T,K)=\arg\min_{\epsilon}\frac{\big[C^{(th)}(S_t,T,K;r,\sigma,\epsilon)-C^{(emp)}(S_t,T,K)\big]^2}{C^{(emp)}(S_t,T,K)} .$$
**Inputs.** European (cash-settled, e.g. SPX) call chain indexed by $(T,K)$; risk-free rate $r$; return history for $\sigma$.
**Parameters.** $\epsilon$ implied per $(T,K)$; $\sigma$ either historical over a window $(t-W,t]$ ($W=1008$ days) or the conditional volatility from an ARMA(3,3)–GARCH(1,1) with $t$-innovations.
**Observed effects.** $\hat\sigma^{(hist)}=0.0112$, $\hat\sigma^{(AG)}=0.0292$; $\hat\sigma^{(n)}=0.0028$ (short) and $8.42\times10^{-4}$ (long); implied $\epsilon$ reproduces the smile, is mixture-sensitive between short-term (daily) and long-term (monthly/quarterly) maturities, and is predominantly stale-quote noise (arXiv:2511.00308v1).
**Failure modes.** An independent noise Brownian motion destroys completeness and exact hedging. Historical and GARCH volatility are non-interchangeable (they shift the $\epsilon$ contour directly). Pooling short- and long-dated chains mixes contracts driven by different pricing (arXiv:2511.00308v1).

### 2.2 CEV / pool-depth liquidity-adjusted option pricing
**Purpose.** Price options on an asset whose price is set by a depth-limited mechanism (constant-product or weighted AMM), and expose depth as a hedgeable risk factor.

Risk-neutral dynamics and a closed-form CEV call:
$$ dP=rP\,dt+\delta P^\beta dW^{\mathbb Q},\qquad \beta=w, $$
$$ C(P,K,T)=P\big[1-\chi^2(a;b+2,c)\big]-Ke^{-rT}\chi^2(c;b,a),\qquad b=\frac{1}{1-\beta}, $$
$$ \kappa=\frac{2r}{\delta^2(1-\beta)\big(e^{2r(1-\beta)T}-1\big)},\quad c=\kappa P^{2(1-\beta)}e^{2r(1-\beta)T},\quad a=\kappa K^{2(1-\beta)}, $$
with $\chi^2(\cdot\,;n,\lambda)$ the non-central chi-squared CDF. For $w=\tfrac12$: $b=2$, $\delta=\dfrac{2\sigma_F}{\sqrt k}$, $c=\kappa Pe^{rT}$, $a=\kappa K$, $\kappa=\dfrac{4r}{\delta^2(e^{rT}-1)}$. Option Greeks decompose as
$$ \Delta_{CEV}=\frac{\partial C}{\partial P},\quad \Gamma_{CEV}=\frac{\partial^2C}{\partial P^2},\quad \Lambda=\frac{\partial C}{\partial k}=\frac{\partial C}{\partial\delta}\frac{\partial\delta}{\partial k}<0, $$
and the delta-hedging friction of trading through the pool is bounded by the replication premium
$$ R\le\frac{\delta^2P^{2\beta}}{2k}\;\mathbb E^{\mathbb Q}\!\int_0^T\Gamma_{CEV}^2(t)P(t)^2\,dt,\qquad R\to0 \text{ as } k\to\infty. $$
Deterministic emissions replacing $\delta^2T$ by an integrated variance:
$$ \bar v^2=\frac{4\sigma_F^2}{\dot k}\ln\!\Big(1+\frac{\dot k\,T}{k_0}\Big),\qquad \delta(t)=\frac{2\sigma_F}{\sqrt{k_0+\dot k t}}. $$
**Inputs.** Spot price $P$ (or reserves $x,y$); pool invariant $k$ (or $K$); net-flow volatility $\sigma_F$; $r$; emission rate $\dot k$ if applicable.
**Parameters.** $\beta=w$ (fixed by the invariant, not estimated); $\delta$; $\Theta$ (a flow-aggregation slope entering the drift).
**Observed effects.** Black–Scholes underprices 20%-OTM puts by ~6% IV at all depths; normalised skew depends only on $\beta$; variance elasticity median $-0.86$ $p<0.0001$; shallow-pool Monte Carlo exceeds the closed form by 1–3% of spot (Euler discretisation when $\sigma_F/x_0$ is large), deep-pool error $<0.5\%$ (arXiv:2603.29763v1).
**Failure modes.** The Brownian-flow assumption is violated in practice — Shapiro–Wilk rejects normality of daily reserves for all 98 subnets, median excess kurtosis $10.7$ (range $[0.6,189.6]$), median skewness $-0.62$; for very shallow pools the $k^{-2}$ replication premium can dominate and CEV prices should be treated as fair-value, not arbitrage-free (arXiv:2603.29763v1). Liquidity depth is unobserved from served data (§3).

### 2.3 Indifference pricing with bid-ask spreads and finite quantities
**Purpose.** Compute the band of prices a dealer will quote for an exotic, using real option quotes (with bid/ask and finite size) as static hedge instruments under convex optimisation.

Position cost and the agent's portfolio problem:
$$ S_0^j(x^j)=\begin{cases}s_a^j\,x^j,&x^j\ge0\\ s_b^j\,x^j,&x^j<0\end{cases},\qquad \min_{x\in D}\ \mathbb E\Big[v\Big(c-\sum_{j\in J}P^j(x^j)\Big)\Big]\ \ \text{s.t.}\ \ \sum_{j\in J}S_0^j(x^j)\le w, $$
with $D=\prod_j[q_b^j,q_a^j]$ the feasible-quantity box and $v(c)=e^{\gamma c/w}$ exponential-utility loss. Indifference prices bracket the agency value function $\Phi$:
$$ \pi_s(w,c;\tilde c)=\inf\{\Delta w:\Phi(w+\Delta w,c+\tilde c)\le\Phi(w,c)\},\qquad \pi_b(w,c;\tilde c)=\sup\{\Delta w:\Phi(w-\Delta w,c-\tilde c)\le\Phi(w,c)\}, $$
and satisfy $\pi_b\le\pi_s$ with equality of the spread narrowing well inside the super-/subhedging bounds.
**Inputs.** Call/put/forward/cash quotes with bid, ask and available quantity at each strike; a probabilistic model of $X_T$; the agent's initial wealth and liability.
**Parameters.** Risk aversion $\gamma$; $t$-distribution scale and degrees of freedom ($\hat\nu=4.84$, $\hat\sigma=0.0554$ fitted to 25 years of daily data); quantity caps.
**Observed effects.** 884 variables / 1769 constraints solved by an interior-point solver in ~4.3 s; optimal portfolios are sparse (<10 of 400 strikes); adding a 10% transaction cost barely changes sparsity while removing the spread produces a dense, mostly max-size portfolio; call buying/selling prices 51.73/51.74 vs sub/super 51.23/53.05; higher risk aversion widens the band, and the selling price is more sensitive (arXiv:1803.02486v1).
**Failure modes.** Prices depend on views, risk preferences and the agent's position, so they are subjective; results depend on the numerics actually reached; the quantity constraints bind and degrade the price per unit as $M$ grows (arXiv:1803.02486v1).

### 2.4 Transient price impact and super-replication duality
**Purpose.** Bound the cost of hedging/super-replicating a claim when trades move bid and ask prices and the spread relaxes with market resilience.

Spread dynamics and impacted price:
$$ d\zeta_t^X=\frac{1}{\delta_t}\big(dX_t^\uparrow+dX_t^\downarrow\big)-r_t\zeta_t^Xdt,\qquad P_t^X=P_t+\iota X_t,\qquad \xi_T^X=\xi_0-\!\int_{[0,T]}\!P_t^X\circ dX_t-\!\int_{[0,T]}\!\zeta_t^X\circ d(X_t^\uparrow+X_t^\downarrow). $$
Dual representation of super-replication costs:
$$ \pi(H)=\sup_{(Q,M,\alpha)}\Big\{\mathbb E_Q[H]-\tfrac12\|\alpha-\zeta_0\|^2_{L^2(Q\otimes\mu)}-M_0x_0-\tfrac12\iota x_0^2\Big\},\qquad \mu(dt)=\mathbb 1_{(0,T)}(t)\,|d\kappa_t|+\kappa_T\,\delta_T(dt),\ \ \kappa_t=\frac{\delta_t}{\rho_t^2}, $$
over measures $Q\ll P$, $Q$-square-integrable martingales $M$ and optional $\alpha\in L^2(Q\otimes\mu)$ with $\frac{\rho_t}{\delta_t}|P_t-M_t|\le \mathbb E_Q[\int_{[t,T]}\alpha_u\,\mu(du)\mid\mathcal F_t]$.
**Inputs.** Unaffected price $P$; market depth $\delta$ and resilience $r$; permanent impact $\iota$; initial half-spread $\zeta_0$.
**Parameters.** $\delta,\ r,\ \iota$; the friction from the strategy-dependent spread enters through $\kappa=\delta/\rho^2$.
**Observed effects.** Buy-and-hold ($X^\uparrow=(1-x_0)\mathbb 1_{[0,T]},X^\downarrow=\mathbb 1_{\{T\}}$) attains the super-replication cost of a call under deterministic liquidity coefficients and conditional full support; cost is a convex, not coherent, risk measure; scaling any strategy is self-defeating because costs grow super-linearly (arXiv:1808.09807v2).
**Failure modes.** Requires continuous filtration (no jumps) and $\delta/\rho^2$ strictly decreasing (relative depth changes dominated by resilience); the payoff must not be manipulable by the large investor (arXiv:1808.09807v2).

### 2.5 Replication-consistent funding sensitivities and settlement-lag LVA
**Purpose.** Forecast liquidity-relevant cash movements of a derivative book consistently with its self-financing replication rather than from static expected cash-flows.

Hedge ratios and rebalancing increments:
$$ \phi_A[V](t)=\frac{\partial V(t)}{\partial A(t)},\qquad \delta_A[V](t_i)=\phi_A[V](t_i)-\phi_A[V](t_{i-1}),\qquad r_i=\big(\delta_A[V](t_i)\big)_{A\in\mathcal A_i}. $$
Net settled funding increment and the funding-sensitivity/expected-cash-flow identity:
$$ \kappa_i=\phi_{P^f(t_i)}[V](t_{i-1})-\sum_{j=i+1}^{n}\delta_{P^f(t_j)}[V](t_i)\,P^f(t_j;t_i), $$
$$ -\frac{\partial}{\partial\Lambda_k}\Big|_{\Lambda=0}N(0)\,\mathbb E^{\mathbb Q}\!\Big[\sum_i X_i\exp(-\Lambda_i)/N(t_i)\Big]=P(t_k;t_0)\,\mathbb E^{\mathbb Q^{P(t_k)}}[X_k], $$
valid when the cash-flow does not depend on the spread $\lambda$. The replication PV identity with a frozen one-step hedge $H_i$ is
$$ N(0)\,\mathbb E^{\mathbb Q}\!\Big[\sum_{i=1}^{n}\frac{\kappa_i}{N(t_i)}\Big]=V(0)+N(0)\,\mathbb E^{\mathbb Q}\!\Big[\sum_{i=1}^{n-1}\frac{\varepsilon^\kappa_i}{N(t_i)}\Big],\quad \varepsilon^\kappa_i=V(t_i)-H_i(t_i)-\kappa_i. $$
**Inputs.** A valuation-model hedge-ratio profile across funding-instrument maturities (AAD outputs $\phi$ and $\delta$); funding/OIS curves; collateral accounts.
**Parameters.** Funding spread curve $\lambda(\cdot;t)$, cumulative $\Lambda(t,T)=\int_t^T\lambda(u;t)du$.
**Observed effects.** Measure mixing across numeraires yields an artificial residual that grows exponentially in variance/horizon; static expected cash-flows ignore the roll trading implied by replication and show non-zero expectations even for a self-financing, cash-matched position; discounting sensitivities equal discounted expected cash-flows and so are the consistent liquidity measure (arXiv:2605.00862v1).
**Failure modes.** The sensitivity/expected-cash-flow relation breaks if the payoff depends on $\lambda$; the paper's "LVA" is an operational settlement-lag adjustment, deliberately narrower than the bilateral LVA inside a full XVA/TVA decomposition (arXiv:2605.00862v1).

### 2.6 Market-maker inventory control with stochastic price impact
**Purpose.** Manage a market maker's inventory under uncertain customer orders, exchange trading with linear stochastic impact, and uncertain-timing block trades.

Impacted price, quadratic value function and optimal controls:
$$ \tilde S_s^{\pi,\delta}=S_s+M_s\pi_s-\beta_sX_s^{\pi,\delta},\qquad V(t,x)=V_2(t)x^2+2V_1(t)x+V_0(t), $$
$$ \pi_u^*=-\frac{1}{M_u}\Big(V_2(u)X_{u-}+V_1(u)+\tfrac12\big(S_u+M_u\Theta_u\big)\Big),\qquad \delta_u^*=-\frac{V_2(u)X_{u-}+V_1(u)+\tfrac12S_u}{V_2(u)+\eta_u}, $$
where $(V_2,Z_2)$ solves a non-linear BSDE and $(V_1,Z_1),(V_0,Z_0)$ two linear BSDEs.
**Inputs.** Security price $S$; stochastic impact factor $M$; inventory-reaction coefficient $\beta$; dark-pool execution intensity $\lambda$; repo/lending rate $l$.
**Parameters.** Customer-order moments $\Phi,\Psi,\Phi_2$; block penalty $\eta$; bid/offer spread $b$; terminal inventory penalty $\xi$.
**Observed effects.** The optimal policy is fully adapted to the market filtration (not deterministic); the multiple-security case is a backward stochastic Riccati equation bounded by Bismut's results, and a perturbative expansion needs only linear ODEs per order (arXiv:1503.07007v2).
**Failure modes.** No order-size-dependent intensity and no partial execution; the reduced form approximates a limit order book (arXiv:1503.07007v2).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| SPX option chain (delayed bid/ask, strike, maturity) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Risk-free / Treasury daily curve | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Daily OHLCV (return history for $\sigma$, ARMA–GARCH) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily OHLCV (alt source) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Technical indicators (volatility/price proxies) | `https://www.alphavantage.co/query` | technical_indicators | alpha_vantage | ok |
| Options chain via local gateway | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Expected move from option chain | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Macro state: term spread, rates, credit spread | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Corporate actions / dividends | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| News (attention / stale-print controls) | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| Global news tone | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | fail — HTTP 429 rate_limited |
| Best-quote sizes (finite liquidity quantities) | **gap** — no probed endpoint returns bid/ask *quantities* at the best quote | — | — | gap |
| Order-book depth $\delta$ and resilience $r$ | **gap** — no level-2/order-book feed | — | — | gap |
| Signed / trade-level order flow | **gap** — no trade-print or signed-flow provider | — | — | gap |
| Intraday quote or high-frequency series | **gap** — no certified intraday feed (twelvedata `interval`/massive aggregates are unverified candidates) | — | — | gap |
| Swap / swaption / cap-floor quotes | **gap** — no rates-derivatives provider | — | — | gap |
| CDS / credit-spread feed | **gap** — no credit feed (needed for defaultable-bond liquidity spreads) | — | — | gap |
| Futures / commodity / carbon prices | **gap** — no futures or commodity provider | — | — | gap |
| AMM pool reserves and on-chain flow | **gap** — no DeFi pool/flow provider | — | — | gap |

## 4. Pitfalls, validation and measurement

- **Noise contaminates the volatility you calibrate with.** Estimating $\sigma$ from observed close-to-close prints embeds bid-ask bounce and asynchronous trading; on SPX the calibrated noise component is negative in the OTM region and the implied-$\epsilon$ surface is dominated by stale last prices (arXiv:2511.00308v1). Never treat a single $\sigma$ estimate as the efficient-price volatility.
- **Measure mixing silently creates fake cash-flows.** Undiscounted expected cash-flows depend on the numeraire; aggregating legs valued in different numeraires leaves residuals that grow exponentially in variance and horizon, and stochastic payment times break additivity ($\sum_iE_i\ne1$) when timing indicators correlate with discounting (arXiv:2605.00862v1). Forecast liquidity from replication hedge ratios instead.
- **Diffusion/brownian assumptions fail on real flow.** Daily pool reserves are heavy-tailed and left-skewed (median excess kurtosis 10.7, skewness $-0.62$, normality rejected for all 98 subnets), so a single GBM/BSM calibration understates tail risk (arXiv:2603.29763v1).
- **Indifference and replication-based prices are subjective, not market prices.** Indifference prices move with the agent's views, risk aversion and current position, and even with how well the optimiser converges (arXiv:1803.02486v1); super-replication costs require the continuous-filtration and monotone-depth conditions (arXiv:1808.09807v2).
- **Non-robust scaling.** In transient-impact models transaction costs grow quadratically when a strategy is scaled, so naive amplification of a "profitable" hedge is self-defeating and there is no admissible-strategy shortcut (arXiv:1808.09807v2).
- **Validation protocol.** (i) Calibrate on a trailing window and price/hedge out of sample — e.g. a 1008-day window for historical $\sigma$ and the ARMA(3,3)–GARCH(1,1) fitted only on $(t-W,t]$ (arXiv:2511.00308v1); (ii) run a delta-hedged backtest and report hedging error per moneyness, as the 82-subnet ATM backtest does (arXiv:2603.29763v1); (iii) compare against the super-/subhedging bounds before trusting an indifference band (arXiv:1803.02486v1); (iv) validate the underlying price dynamics itself, e.g. a cross-sectional variance-elasticity regression testing $P^{2(\beta-1)}$ and rejecting GBM (arXiv:2603.29763v1).
- **Statistical tests.** Use Newey–West-adjusted regressions for the cross-section (the variance-elasticity test), Shapiro–Wilk for the flow-normality assumption, and report coefficient $p$-values for the volatility model (ARMA(3,3)–GARCH(1,1) coefficients are significant except the GARCH constant) (arXiv:2511.00308v1, arXiv:2603.29763v1).
- **Look-ahead / in-sample leakage.** Snapshot the option chain and the risk-free curve at the *same* timestamp before computing implied quantities (arXiv:2511.00308v1 used a 21-Apr-2025 Cboe chain and US Treasury 10-year par yield at one instant); do not use realised outcome windows as calibration inputs; separate short-dated from long-dated chains when the processes differ (arXiv:2511.00308v1).

## 5. Recommended first implementation in FinRobot

1. **SPX/Treasury option-pricing harness (S).** Pull the delayed SPX chain from `cboe` `options_surface` and the daily curve from `federal_reserve` `risk_free_curve`; compute mid prices and Black–Scholes implied vols per $(T,K)$. Data: cboe + federal_reserve (`ok`). Value: the substrate every option-pricing model below needs and the only served derivatives input. Risk: delayed quotes and no sizes, so mid prices are approximate (arXiv:2511.00308v1, arXiv:1803.02486v1).
2. **Noise-augmented BSM and implied-$\epsilon$ surface (S).** Fit the $\sigma+\epsilon$ BSM to the chain with $\sigma$ from daily OHLCV (`eodhd` `core_stock_apis`) via an ARMA(3,3)–GARCH(1,1), and plot the implied-$\epsilon$ surface. Data: cboe chain + eodhd OHLCV (`ok`). Value: first microstructure-adjusted option price, and it exposes stale-quote distortion of the smile. Risk: $\epsilon$ conflates many noise sources and is sign-unstable (arXiv:2511.00308v1).
3. **Bid-ask-aware indifference pricing of a vanilla/static hedge (M).** Solve the convex program over the quoted call/put/forward strikes with quoted bid/ask as costs and quantity caps; report the buying/selling band against super-/subhedging bounds. Data: cboe chain (`ok`) with generous caps; true quoted sizes are a `gap`, so substitute conservative caps. Value: a dealer price band for exotics and genuinely sparse hedges. Risk: subjective to preferences and to solver convergence (arXiv:1803.02486v1).
4. **Depth-adjusted Greeks and replication premium (M).** Implement the CEV/call price with $\beta=\tfrac12$, the liquidity Greek $\partial C/\partial k$ and the $k^{-2}$ replication premium, using exchange open-interest/volume as a depth proxy since true pool depth is unserved. Data: cboe chain + `moomoo` `options_data`/`expected_move` (`gateway`); real depth is a `gap`. Value: depth sensitivity of option value and a hedging-friction estimate. Risk: proxy depth is not pool depth; heavy-tailed flows break the diffusion assumption (arXiv:2603.29763v1).
5. **Replication-consistent funding-sensitivity reporting with settlement-lag LVA (M).** From a valuation model with AAD, output the funding hedge-ratio profile $\phi$, the rebalancing increments $\delta_A$, the net settled increment $\kappa_i$, and a settlement-lag LVA. Data: Treasury curve (`ok`) as funding proxy, plus hedge ratios. Value: removes measure-mixing artefacts from liquidity forecasts of derivative books. Risk: needs adjoint/hedge-ratio machinery and a funding-curve model (arXiv:2605.00862v1).
6. **Market-maker inventory policy solver (L).** Implement the quadratic-value-function/BSDE system with a perturbative expansion for the multiple-security BSRDE; support stochastic impact factor and dark-pool intensity. Data: impact factor $M$ and order-flow moments require trade-level/flow data that are a `gap`; seed with proxy values. Value: adapted inventory policy when hedging a derivative book. Risk: heavy numerics and unserved calibration inputs (arXiv:1503.07007v2).
7. **Transient-impact super-replication bounds (L).** Compute the buy-and-hold call cost and the dual penalty with calibrated $\delta,r,\iota$. Data: $\delta,r$ need order-book calibration (`gap`); fall back to proxies from spread dynamics. Value: conservative upper bound on hedge cost under finite liquidity. Risk: continuous-filtration and monotone-depth conditions, plus a data `gap` (arXiv:1808.09807v2).

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2603.29763v1 | Option Pricing on Automated Market Maker Tokens | 2026 |
| 2605.00862v1 | Replication-Consistent Liquidity Forecasting for Derivatives — Forward Funding Sensitivities and a Liquidity Valuation Adjustment for Settlement Lags | 2026 |
| 2511.00308v1 | Asset Pricing in the Presence of Market Microstructure Noise | 2025 |
| 1808.09807v2 | Continuous-time Duality for Super-replication with Transient Price Impact | 2018 |
| 1803.02486v1 | Pricing index options by static hedging under finite liquidity | 2018 |
| 1503.07007v2 | Optimal Position Management for a Market Maker with Stochastic Price Impacts | 2015 |
