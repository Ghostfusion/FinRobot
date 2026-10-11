# Hedging & Incomplete Markets — learnings from the q-fin.PR corpus
`424` of 2274 corpus papers matched this category (`419` with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **A delta hedge is only approximately risk-free once rebalancing is discrete or costly.** The corpus treats replication as a *tracking control* problem: Leland (1985) shows proportional transaction costs change replication through an *effective* volatility, and Whalley–Wilmott (1997) derive a no-transaction band around the Black–Scholes delta — re-trading to close a small gap inside the band does not repay the spread (arXiv:2607.25258v1).
- **Liquidity cost of a delta-hedging programme is semi-analytic and scales quadratically in the trade size.** Using Çetin's supply curve $S(t,z)\approx S_t+\alpha S_t z$, the risk-neutral expected liquidity cost of hedging $N$ European options collapses to a single number $ \alpha N^2 S_0 I$, where the *unit liquidity cost* $I$ is an integration over European option prices; the authors report it is far faster than Monte Carlo and linear in the slope $\alpha$ (arXiv:2103.15302v1).
- **In a GARCH market the correct instantaneous hedge is delta *plus a vega correction*.** Local risk minimisation with respect to a pricing kernel gives $\xi_{t+1}\approx \Delta^Q_{t,S}+\mathrm{VM}^Q_{t+1}\Delta^Q_{t,\sigma^2}$, with $\mathrm{VM}^Q_{t+1}=\mathrm{Cov}^Q(S_{t+1}-S_t,\ \sigma^2_{t+2}-\sigma^2_{t+1}\mid F_t)/\mathrm{Var}^Q(S_{t+1}-S_t\mid F_t)$; Duan's (1995) static delta is the special case in which price and variance innovations are uncorrelated — which is *inconsistent* with GARCH (arXiv:1209.5976v4).
- **Non-Gaussian innovations improve hedging, not just pricing.** On S&P 500 European calls, hedges under Normal-Inverse-Gaussian GARCH systematically beat their Gaussian counterparts across moneyness and maturity, the gain being largest for out-of-the-money contracts (arXiv:1209.5976v4).
- **With basis risk the unhedgeable residual carries a $1-\rho^2$ signature.** In the cross-hedge model $dS_t=\sigma_S S_t(\lambda_S dt+dW^S_t)$, $dY_t=\sigma_Y Y_t(\lambda_Y dt+dW^Y_t)$, $W^Y=\rho W^S+\sqrt{1-\rho^2}W^\perp$, the residual-risk SDE has drift $\tfrac12\gamma(1-\rho^2)(\sigma_Y Y_t p_y)^2$ and diffusion $\sqrt{1-\rho^2}\,\sigma_Y Y_t p_y$; at a *high* correlation $\rho=0.98$ the orthogonal scale is still $\sqrt{1-\rho^2}\approx 20\%$ — a small change in $\rho$ near 1 swings the basis share sharply, but near $0$ barely moves it (arXiv:2101.00251v1).
- **Indifference price = marginal price + a risk correction.** To second order, $p(t,S_t,Y_t)=p_M+\tfrac12\gamma\big(\mathrm{Var}^{Q_M}[C(Y_T)\mid F_t]-\mathbb E^{Q_M}[\langle X_M\rangle_{t,T}\mid F_t]\big)+O(\gamma^2)$ for exponential forward utility with risk aversion $\gamma$ (arXiv:2101.00251v1).
- **Drift/market-price-of-risk uncertainty is practically unidentifiable, so filtering is mandatory.** Estimating $\lambda_S$ to within 5% at 95% confidence needs $t\approx1537$ years of data; the paper therefore places a Kalman–Bucy filter over the unknown drift, and the residual-risk and hedging objects are derived under partial information (arXiv:2101.00251v1).
- **Deep-hedging policies are not dominated by classical bands, and the ranking is liquidity- and budget-dependent.** Post-training robust hedging valuation adjustment (HVA) stresses tracking-cost CVaR95 over a KL ball; sparse learned execution wins only in *Low Liquidity* (a 4.2% reserve reduction, 95% interval $[-0.007066,-0.005290]$ over 20 test seeds), while tuned classical gamma-wide bands win in High/Middle Liquidity; an almost-unhedged policy looks cheapest by reserve alone yet has tracking CVaR $10.6/8.5/7.0\times$ the reference in the three environments (arXiv:2607.25258v1).
- **In heavy-execution products, indifference pricing measures *achievable* rather than fair value.** For Accelerated Share Repurchase, the fair discount $\delta_{fair}$ assumes perfect Greek replication while the indifference discount $\delta_{ind}$ (where $\rho(\mathrm{PnL})=0$ for a convex risk measure $\rho$) reflects actual execution and hedging; adding the hedge lifted $\delta_{ind}$ from 82.1 to 126.5 bp for the bang-bang policy and from 114.6 to 132.4 bp for the neural policy, narrowing the $\delta_{fair}-\delta_{ind}$ gap (arXiv:2601.18686v1).
- **A model-free delta exists that needs no volatility or drift estimate.** Replacing prices by their *trends* turns the risk-free replication equation into a degree-1 algebraic tracking law $\Delta=(V_{trend}-\Pi_{trend}(0)e^{\int_0^t r})/S_{trend}$, initialised by matching logarithmic derivatives — no Black–Scholes PDE and no final condition (arXiv:1005.0194v1).
- **Disagreement to note.** The corpus splits three ways on the right objective: *quadratic* (local risk-minimisation / minimum-variance, arXiv:1209.5976v4), *utility/indifference* (exponential forward utility, arXiv:2101.00251v1; OCE risk measures, arXiv:2601.18686v1), and *robust worst-case* (KL-stressed CVaR, arXiv:2607.25258v1). They agree that no single hedging rule dominates across liquidity regimes and contract types; the choice is a policy decision that must be reported together with the risk measure it optimises.

## 2. Implementable formulas & algorithms

### 2.1 No-transaction-band delta hedge under proportional costs
**Purpose.** Discretise a delta hedge so that small misalignments are tolerated rather than re-traded, cutting transaction-cost leakage; the standard benchmark for any hedging study.

Leland's effective-volatility adjustment for a replication interval $\Delta t$ and proportional cost $k$:
$$\tilde\sigma^2=\sigma^2\left(1+\sqrt{\tfrac{8}{\pi}}\,\frac{k}{\sigma\sqrt{\Delta t}}\right).$$
Whalley–Wilmott band: hold target delta $d_i$ and half-width $b_i$, and project the previous position onto the band,
$$q_i=\min\{\max(q_{i-1},\,d_i-b_i),\,d_i+b_i\},\qquad i=0,\dots,N-1,$$
with the gamma-aware widening $b_i=\min\{3b_0,\ b_0(1+e^{G_i})\}$, $e^{G_i}=\min\{|\Gamma_i|S_i\sigma\sqrt{\Delta t}/Q_{90},\,5\}$, where $Q_{90}$ is a 90th-percentile gamma-intensity scale (arXiv:2607.25258v1, following Leland 1985 and Whalley–Wilmott 1997).
- **Inputs:** underlying price path $S_i$; option value/gamma (analytic Merton/Black–Scholes); rebalancing grid.
- **Parameters:** base half-width $b_0\in\{0.05,\dots,0.20\}$; $\Gamma$; $Q_{90}$ fixed on an independent sample.
- **Observed effects:** in high and middle liquidity, tuning $b_0$ captures most of the achievable reserve reduction (gamma-wide $b_0=0.075$ changes total adjustment by $-0.1\%$/$-1.6\%$); wider bands reduce reserve further only as the risk budget loosens (arXiv:2607.25258v1).
- **Failure modes:** ignore $b_0$ tuning and the band can be dominated by sparse/deep rules in low liquidity; a no-hedge policy minimises reserve but leaves the largest tail (arXiv:2607.25258v1).

### 2.2 Expected liquidity cost of a delta-hedging programme
**Purpose.** Price the market-impact component of hedging *before* trading it, replacing a Monte Carlo loop with a quadrature over option prices.

Unit liquidity cost $I$ for one option with moneyness $M=K/S_0$,
$$I=-2\int_0^T\!\!\int_0^\infty e^{r(2T-t)}\frac{\partial f}{\partial t}\!\big(t,e^{r(T-t)}k;M,T\big)\,\varphi^{(t)}(1,k)\,dk\,dt+2e^{rT}\!\!\int_0^\infty f(T,k;M,T)\,\varphi^{(T)}(1,k)\,dk,$$
$$f(t,x;M,T)=e^{-3r(T-t)}x\Big(\tfrac{\partial\bar D}{\partial x}\big(t,e^{-r(T-t)}x;M,T\big)\Big)^2,$$
where $\varphi^{(t)}$ is the density of the underlying under the pricing measure and $\bar D$ the delta normalised by $S_0$. The total expected cost for $N$ options is
$$\mathbb E^Q\!\Big[\int_0^T\alpha S_t\,d[D]_t\Big]=\alpha N^2 S_0 I.$$
- **Inputs:** an option price/density surface $\varphi^{(t)}(1,k)$ at strikes $k$ and maturities $t$; the delta function of the hedge.
- **Parameters:** supply-curve slope $\alpha$ (linear approximation of the Çetin exponential curve); implied/realised volatility for $\varphi$.
- **Observed effects:** cost is linear in $\alpha$ and *quadratic* in the number of options $N$; the integration is a fast deterministic alternative to Monte Carlo (arXiv:2103.15302v1).
- **Failure modes:** linear supply curve is only a first-order fit (good for highly liquid names, jump-linear fits for illiquid ones); needs a smooth supply curve near $z=0$ (arXiv:2103.15302v1).

### 2.3 Local risk-minimisation / minimum-variance quadratic hedge (GARCH)
**Purpose.** Choose the one-step-ahead hedge that minimises realised squared hedging error when the market is incomplete — the directly implementable quadratic-hedging rule.

Backward recursion for a generalized strategy $(\xi^0,\xi)$ with $V_T=H$:
$$\xi^P_{t+1}=\frac{\mathrm{Cov}^P\big(\widetilde V_{t+1},\ \widetilde S_{t+1}-\widetilde S_t\mid F_t\big)}{\mathrm{Var}^P\big(\widetilde S_{t+1}-\widetilde S_t\mid F_t\big)},\qquad \widetilde V_t=\mathbb E^P[\widetilde V_{t+1}\mid F_t]-\xi_{t+1}\mathbb E^P[\widetilde S_{t+1}-\widetilde S_t\mid F_t].$$
Diffusion-limit approximation under a measure $Q$: $\xi^Q_{t+1}\approx\Delta^Q_{t,S}+\mathrm{VM}^Q_{t+1}\Delta^Q_{t,\sigma^2}$, $\mathrm{VM}^Q_{t+1}=\mathrm{Cov}^Q(S_{t+1}-S_t,\sigma^2_{t+2}-\sigma^2_{t+1}\mid F_t)/\mathrm{Var}^Q(S_{t+1}-S_t\mid F_t)$. Performance measured by the price-normalised hedging error
$$\mathrm{NHE}(\xi)=\frac{\big|H(S_T)-V_0-\sum_{i=0}^{K}\xi_{t_{i+1}}(S_{t_{i+1}}-S_{t_i})\big|}{V_0}.$$
- **Inputs:** historical log-returns to fit NGARCH(1,1) $\sigma^2_t=\alpha_0+\alpha_1\sigma^2_{t-1}\omega(\epsilon_{t-1})+\beta_1\sigma^2_{t-1}$ by MLE; option price and Greeks under the chosen $Q$ (Monte Carlo).
- **Parameters (S&P 500, 1992–2003 MLE):** Gaussian $\alpha_0=9.941\!\times\!10^{-7},\alpha_1=0.041,\beta_1=0.917,\gamma=0.863,\lambda=0.041$; NIG $\alpha_0=8.665\!\times\!10^{-7},\alpha_1=0.047,\beta_1=0.909,\gamma=0.860,\lambda=0.041$, invariant shape $k=1.322,a=-0.144$ (skew $-0.250$, kurtosis $4.839$).
- **Observed effects:** local risk-minimation beats the ad-hoc Black–Scholes benchmark; the vega-corrected delta $\Delta^{SV}$ is far better than plain delta when initialised at ad-hoc implied volatility (NHE $0.572\to0.204$ Gaussian, $0.553\to0.183$ NIG), and NIG hedges beat Gaussian hedges for every method and contract (arXiv:1209.5976v4).
- **Failure modes:** minimal-martingale measure is *signed* in GARCH, so local risk-minimisation against the physical measure may not be arbitrage-free; when $\Delta^Q_{t,\sigma^2}=0$ or price/variance innovations are uncorrelated the vega correction vanishes (the Duan case) (arXiv:1209.5976v4).

### 2.4 Indifference pricing with basis risk and partial information
**Purpose.** Value and hedge a claim on a *non-traded* asset using a correlated traded asset, when drift is unknown — the canonical incomplete-market pricing rule.

Forward (exponential) utility $U_t(x)=-e^{-\gamma x+\tfrac12\int_0^t(\widehat\lambda^S_u)^2du}$ with filter-implied Sharpe ratio $\widehat\lambda^S$. Indifference price $p$ solves
$$v^{C}\big(t,X_t+p(t,S_t,Y_t),S_t,Y_t\big)=v^{0}(t,X_t,S_t,Y_t),$$
i.e. the cash that makes the investor indifferent to holding the claim; $p$ is wealth-independent. Residual (basis) risk $\varrho_t=X_t-p(t,S_t,Y_t)$ evolves as
$$d\varrho_t=\tfrac12\gamma(1-\rho^2)\big(\sigma_Y Y_t\,p_y(t,S_t,Y_t)\big)^2dt-\sqrt{1-\rho^2}\,\sigma_Y Y_t\,p_y(t,S_t,Y_t)\,d\widehat W^\perp_t.$$
Asymptotic price: $p=p_M+\tfrac12\gamma(\mathrm{Var}^{Q_M}[C(Y_T)\mid F_t]-\mathbb E^{Q_M}[\langle X_M\rangle_{t,T}\mid F_t])+O(\gamma^2)$.
- **Inputs:** traded $S$ and basis $Y$ price paths; $\sigma_S,\sigma_Y,\rho$ (estimated from quadratic and co-variations).
- **Parameters:** risk aversion $\gamma$; Kalman–Bucy filter for the unknown market price of risk; the claim payoff $C(Y_T)$.
- **Observed effects:** $\varrho\equiv0$ only when $|\rho|=1$; at $\rho=0.98$ the diffusion scale is $\approx20\%$; correlations drift over time so the basis share is unstable (arXiv:2101.00251v1).
- **Failure modes:** $\lambda_S$ estimation is hopeless from history alone ($\approx1537$ years for a 5% band) so the answer is filter-dependent; non-traded $Y$ may have *no* price feed at all in FinRobot's inventory (see §3) (arXiv:2101.00251v1).

### 2.5 Robust HVA / CVaR reserve under KL stress
**Purpose.** Attach a single internally-consistent reserve to a *trained* hedge policy, and rank policies under a tracking-risk budget.

Pathwise friction cost $C^\pi=\sum_{i=0}^{N}D_iM_i\big(sX^\pi_i+\kappa(X^\pi_i)^2\big)$ with $X^\pi_i=S_i|\Delta q^\pi_i|$; robust HVA is the KL-constrained upper expectation with closed dual
$$\mathrm{RHVA}^\pi(\varepsilon)=\sup_{Q:D_{KL}(Q\|\widehat P_S)\le\varepsilon}\mathbb E_Q[C^\pi]=\inf_{\eta>0}\Big\{\eta\varepsilon+\eta\log\Big(\tfrac1{N_{sim}}\sum_{n=1}^{N_{sim}}e^{C^\pi_n/\eta}\Big)\Big\}.$$
Funding and margin add-ons are stressed under the *same* tilt $w^{\star,\pi}_n\propto e^{A^\pi_n/\eta^{\star,\pi}}$, $A^\pi=C^\pi+C^\pi_{fund}+C^\pi_{margin}$; ranking solves
$$\min_\pi\ \mathrm{RAdj}^\pi(\varepsilon)\quad\text{s.t.}\quad R^\pi=\mathrm{CVaR}_{95}[-\mathcal E^\pi_T]\le c\,R^{ref}.$$
- **Inputs:** simulated price paths (Merton jump-diffusion $\tfrac{dS_t}{S_{t-}}=\dots+\sigma dW_t+(J-1)dN_t$); a two-state liquidity Markov chain; the hedge policy.
- **Parameters:** half-spread $s$, impact $\kappa$, liquidity multiplier $m_s$, funding spread $s_f=1\%$, margin spread $s_m=0.5\%$, KL radius $\varepsilon\in\{0.005,0.006\}$, budget multiple $c\in\{1,1.2,1.5\}$.
- **Observed effects:** no policy dominates; validation-selected sparse 0.075 in Low Liquidity gives a 4.2% reserve cut with a paired 95% interval $[-0.007066,-0.005290]$; learned NTB lowers tracking CVaR but raises reserve (arXiv:2607.25258v1).
- **Failure modes:** ranking by reserve alone favours near-no-hedge (CVaR $10.6\times$ reference); the fixed KL radius does not preserve the benchmark-stress label across policies; validating on the same paths as selection overstates performance (arXiv:2607.25258v1).

### 2.6 OCE deep hedging and indifference discount
**Purpose.** Jointly learn execution and hedging of an illiquid, path-dependent product, and convert the residual risk into a tradable discount.

Optimized-certainty-equivalent risk measure with convex loss $l$:
$$\rho(Z)=\inf_{w\in\mathbb R}\{w+\mathbb E[l(-w-Z)]\},$$
with expected-shortfall choice $l(x)=\tfrac1{1-\alpha}\max(x,0)$ and mean-variance choice $l(x)=x+\tfrac12\gamma x^2$ (the latter is not convex-decreasing, so it is not an OCE in the formal sense). Optimal policy solves $\inf_{\theta,\phi,w}\{w+\mathbb E[l(-w-\mathrm{PnL}_\tau)]\}$. Discounts: fair discount $\delta_{fair}$ from $\mathbb E^Q[\mathrm{PnL}^{ASR}_\tau]=0$, i.e. $\delta_{fair}=1-\mathbb E^Q[W_{n^*}]/\mathbb E^Q[A_{n^*}Q_{n^*}]$; indifference discount $\delta_{ind}$ solves $\rho(\mathrm{PnL}_\tau)=0$.
- **Inputs:** simulated buyback/price paths; the contract state $S_n=(n,S_n,A_n,Q_{n-1},W_{n-1})$; risk measure.
- **Parameters:** two neural nets (4–6 layers, 128–150 units, ReLU, sigmoid/linear head); $\lambda=(W_{Min}+W_{Max})/(S_0(N_{Min}+N_{Max}))$ output scaling; $\alpha=0.75$ ES level.
- **Observed effects:** neural policy beats smooth bang-bang (ES $0.75$: $-136.8$ vs $-94.0$ bp) and sequential hedging lifts $\delta_{ind}$ by 32–44 bp while leaving $\delta_{fair}$ unchanged (arXiv:2601.18686v1).
- **Failure modes:** without $\lambda$ scaling, hedge-PnL gradients vanish and training collapses to execution-only; under Black–Scholes with $r=0$ the authors set $P=Q$; relies on neural training (a `torch` dependency — out of FinRobot's NumPy-only runtime; see §5) (arXiv:2601.18686v1).

### 2.7 Model-free delta from trends
**Purpose.** Hedge without a volatility or drift model, using only smoothed price trends.

Portfolio $\Pi=V-\Delta S$ held risk-free gives $\Pi_{trend}=\Pi_{trend}(0)e^{\int_0^t r}$; combining the two trend equations yields the tracking law
$$\Delta=\frac{V_{trend}-\Pi_{trend}(0)\,e^{\int_0^t r(\tau)d\tau}}{S_{trend}},$$
initialised by equating logarithmic derivatives,
$$\Delta(0)=\frac{\dot V_{trend}(0)-r(0)V_{trend}(0)}{\dot S_{trend}(0)-r(0)S_{trend}(0)},\qquad \Pi_{trend}(0)=V_{trend}(0)-\Delta(0)S_{trend}(0).$$
A carry variant replaces the denominator with $\dot S_{trend}-qS_{trend}$.
- **Inputs:** daily underlying and derivative price series; a trend/denoising filter (moving-average class).
- **Parameters:** trend-extraction window/denoising parameters only.
- **Observed effects:** no calibration and no terminal condition; demonstrated on CAC 40 put/call daily data with jump handling via unusual-fluctuation detection (arXiv:1005.0194v1).
- **Failure modes:** the paper is a conference note — no systematic comparison against Black–Scholes and no transaction-cost treatment; derivative price series are required per contract (arXiv:1005.0194v1).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Underlying equity OHLCV (delta, replication, return fitting) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Underlying daily bars (alt) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| SPX option quotes / chain for hedge instrument & implied vol | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | ok |
| Option chain (alt, local gateway) | `moomoo://get_option_chain` | options_data | moomoo | gateway |
| Expected move / implied inputs | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Risk-free discount curve (Leland/Whalley–Wilmott $r$) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | ok |
| Short-rate & funding proxies (FVA inputs) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Term spread / HY credit spread (funding & stress state) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Traded-asset trend input (model-free delta) | `moomoo://get_cur_kline` | technical_indicators | moomoo | gateway |
| Technical indicators (trend/vol filters, alt) | `https://www.alphavantage.co/query` | technical_indicators | alpha_vantage | ok |
| News/regime features (liquidity-stress state) | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| Corporate actions (adjusted returns) | `https://eodhd.com/api/div/AAPL` | corporate_actions | eodhd | ok |
| Realized correlation / covariance between two *traded* assets (cross-hedge) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Order-book / limit-order depth for the Çetin supply curve | **gap** — no provider exposes depth; only top-of-book option quotes via `cboe` | — | — | gap |
| Bid–ask spread / realized transaction-cost series | **gap** — spread must be proxied from the `cboe` option quotes; no standalone cost feed | — | — | gap |
| Non-traded / basis asset price series (weather, kerosene, credit index) | **gap** — the basis model's $Y$ has no feed | — | — | gap |
| Intraday (sub-daily) bars for high-frequency rebalancing & liquidity cost | **gap** — no certified intraday series in the inventory | — | — | gap |
| Funding / margin (FVA, MVA) spread term structure | **gap** — no swap/collateral curve; `fred` gives only proxy rates | — | — | gap |

## 4. Pitfalls, validation and measurement

- **Drift/Markov-price-of-risk uncertainty is the dominant estimation error.** Estimating a log-normal Sharpe ratio to within 5% at 95% confidence needs $t\approx1537$ years, so any hedging result built on a point estimate of $\lambda$ is fragile; the corpus' prescription is filtering (Kalman–Bucy) plus reporting sensitivity to the filter prior (arXiv:2101.00251v1).
- **Model non-robustness under jumps.** Black–Scholes's hedging rules are known to lack robustness once jumps are admitted; the model-free variant is proposed precisely to sidestep the BSM assumptions, and it flags abrupt changes as the hard case (arXiv:1005.0194v1). Test any hedge on a jump-diffusion path set, not only on a pure diffusion.
- **The objective function decides the ranking, so state it.** Local risk-minimisation, expected shortfall, mean-variance and robust CVaR select different "best" policies; a policy that minimises reserve can be nearly unhedged (tracking CVaR $10.6\times$ reference) (arXiv:2607.25258v1). Always report the risk measure alongside the hedge, and never rank on cost alone.
- **Selection/validation leakage.** Choosing the best candidate on the same simulated paths that report its performance overstates the result; the corpus uses disjoint validation (select) and test (report) path blocks with a *pass/fail* check that the tracking-CVaR budget still holds out of validation (arXiv:2607.25258v1, arXiv:2601.18686v1). Re-estimate GARCH parameters once in-sample and hold them fixed across all hedged contracts to avoid look-ahead (arXiv:1209.5976v4).
- **In-sample vs out-of-sample in cross-hedging.** The residual-risk process is driven by $1-\rho^2$ and correlations are non-stationary, so a backtest must re-estimate $\rho$ (and $\sigma_Y$) walk-forward rather than in-sample; near $\rho=1$ the basis share is hypersensitive to small estimation error (arXiv:2101.00251v1).
- **Signed / non-convex measures break arbitrage-freeness.** In GARCH the minimal martingale measure is signed, so local risk-minimisation against the physical measure may not yield arbitrage-free prices; use a genuine pricing kernel and verify no-arbitrage numerically (arXiv:1209.5976v4). Similarly, the mean-variance loss is not a formal OCE (arXiv:2601.18686v1).
- **Validation protocol / tests.** Report the price-normalised hedging error $\mathrm{NHE}$ (mean and dispersion) across moneyness $\times$ maturity bins (arXiv:1209.5976v4); compare policies with paired per-seed differences and a 95% interval rather than mean-only (arXiv:2607.25258v1); verify the reserve decomposition by checking $\mathrm{RHVA}+\mathrm{RFA}+\mathrm{RMA}\ge\mathrm{RAdj}$ (the componentwise worst cases need not coincide) (arXiv:2607.25258v1).
- **Cost-model calibration risk.** The liquidity-cost formula assumes a linear supply curve and a known slope $\alpha$; both are approximations (linear holds for highly liquid names, jump-linear for illiquid ones), so $\alpha$ must be treated as an uncertain parameter and the cost reported as a range (arXiv:2103.15302v1).

## 5. Recommended first implementation in FinRobot

1. **(S) Band-delta hedge evaluator on served SPX data.** Implement Black–Scholes/Merton delta and the no-transaction-band projection $q_i=\mathrm{clip}(q_{i-1},d_i\pm b_i)$, then score any rule with $\mathrm{NHE}$ across moneyness/maturity bins. `Data:` `cboe` `options_surface` (SPX chain) + `eodhd` `core_stock_apis`. `Value:` the benchmark every other hedging rule must beat, and the first end-to-end hedging artifact FinRobot can compute from *served* data. `Risk:` delayed quotes and discrete rebalancing; $b_0$ needs tuning on validation paths (arXiv:2607.25258v1).
2. **(S) GARCH local-risk-minimisation hedge with vega multiplier.** Fit NGARCH(1,1) by MLE on equity returns and build $\xi=\Delta_S+\mathrm{VM}\cdot\Delta_{\sigma^2}$. `Data:` `core_stock_apis` OHLCV only (no options needed for the diffusion-limit delta). `Value:` materially lower NHE than ad-hoc Black–Scholes; the tip of the corpus' quadratic-hedging theory with the least data. `Risk:` signed minimal-martingale measure; needs a chosen pricing kernel (arXiv:1209.5976v4).
3. **(S) Model-free trend delta.** Compute $V_{trend},S_{trend}$ with a moving-average/denoising filter and apply the degree-1 tracking law. `Data:` `core_stock_apis` + `technical_indicators`. `Value:` a no-calibration, jump-tolerant hedge; cheap cross-check on items 1–2. `Risk:` conference-note evidence only, no cost handling (arXiv:1005.0194v1).
4. **(M) Indifference-pricing layer with basis-risk residual.** Implement exponential-utility indifference price and the residual-risk SDE; drive the sharpe ratio with a Kalman–Bucy filter. `Data:` two correlated traded assets via `core_stock_apis` (true non-traded $Y$ is a `gap`). `Value:` an incomplete-market price with a risk correction and an explicit hedging-error process, i.e. the corpus' central PR result. `Risk:` the filter prior drives the answer; $\gamma$ is a policy input (arXiv:2101.00251v1).
5. **(M) Semi-analytic expected liquidity cost.** Implement the unit-liquidity-cost quadrature $\alpha N^2S_0I$ over the served SPX surface and report cost as an $\alpha$-range. `Data:` `cboe` `options_surface` (prices/densities) + assumed $\alpha$. `Value:` prices the impact of hedging programmes before trading, at the cost of a quadrature. `Risk:` supply-curve slope unobservable without depth (a `gap`) (arXiv:2103.15302v1).
6. **(M) Robust HVA / CVaR reserve and budget-constrained ranking.** Simulate Merton jump-diffusion paths, compute $\mathrm{RAdj}(\varepsilon)$ under the KL tilt and select policy by validation with an out-of-validation budget check. `Data:` simulated paths seeded from served OHLCV calibration. `Value:` turns "which hedge?" into a reproducible, reserve-aware decision. `Risk:` KL radius must be disclosed as a market-level assumption (arXiv:2607.25258v1).
7. **(L — deferred) Deep hedging with OCE and indifference discount.** The joint execution/hedging neural policy and $\delta_{ind}$. `Data:` simulated paths; `Risk:` requires a `torch` training stack, which is outside FinRobot's NumPy-only runtime red line — keep out of scope until the classical stack (items 1–6) is measured (arXiv:2601.18686v1, §2.6).

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2607.25258v1 | Robust Hedging Valuation Adjustment for Deep Hedging Policies under Market Frictions | 2026 |
| 2601.18686v1 | Optimal strategy and deep hedging for share repurchase programs | 2026 |
| 2103.15302v1 | Analytic formula for option margin with liquidity costs under dynamic delta hedging | 2021 |
| 2101.00251v1 | Forward indifference valuation and hedging of basis risk under partial information | 2021 |
| 1209.5976v4 | Quadratic hedging schemes for non-Gaussian GARCH models | 2013 |
| 1005.0194v1 | Delta Hedging in Financial Engineering: Towards a Model-Free Approach | 2010 |
