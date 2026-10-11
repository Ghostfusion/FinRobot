---
id: price-impact-adverse-selection
name: Price Impact Law and Adverse Selection
version: 1.0.0
author: finrobot
domain: market-microstructure
description: Estimate the square-root price-impact law — exponent delta, prefactor c, Kyle lambda depth, and trade-sign long memory — from reconstructed metaorders. Use when measuring price impact, adverse selection, or market depth.
triggers:
- price impact
- square root law
- adverse selection
- kyle lambda
- kyle model
- market depth
- metaorder
- order flow
- impact exponent
- sign long memory
- price impact law
- liquidity
requires_data:
- input: Daily OHLCV ($V_D$, $\sigma_D$ Parkinson, ADV)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Daily OHLCV (secondary)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Daily OHLCV (tertiary)
  provider: stockdata
  category: core_stock_apis
  status: ok
- input: Previous-day aggregate bars
  provider: massive
  category: core_stock_apis
  status: ok
- input: Intraday bars (coarse impact reconstruction)
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Technical indicators / bars
  provider: alpha_vantage
  category: technical_indicators
  status: ok
- input: Intraday K-line via local OpenD gateway
  provider: moomoo
  category: technical_indicators
  status: gateway
- input: Top-of-book snapshot (best bid/ask only)
  provider: moomoo
  category: core_stock_apis
  status: gateway
- input: Tradable universe / tick sizes
  provider: eodhd
  category: exchange_symbols
  status: ok
- input: Option chain (implied vols, option imbalance)
  provider: moomoo
  category: options_data
  status: gateway
- input: Underlying/expected-move overview (straddle IV)
  provider: moomoo
  category: expected_move
  status: gateway
- input: Option surface, delayed quotes (IV)
  provider: cboe
  category: options_surface
  status: ok
- input: Risk-free curve (option pricing)
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: '**Signed trade tape with aggressor flag**'
  provider: ''
  category: ''
  status: gap
- input: '**Broker/member-tagged parent (meta)orders**'
  provider: ''
  category: ''
  status: gap
- input: '**L2/L3 book depth (slope $L$, imbalance)**'
  provider: ''
  category: ''
  status: gap
- input: '**Per-account order lifecycle (TSE/JVP equivalent)**'
  provider: ''
  category: ''
  status: gap
- input: '**Event-time child-order stream + waiting times**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Price Impact Law and Adverse Selection

You are an expert market-microstructure researcher specializing in price impact and adverse selection. You consume daily OHLCV (volume V_D, Parkinson range sigma_D), intraday volume profiles, reconstructed metaorders, signed trade tapes and option/implied-vol series from the available endpoints, and turn them into cross-sectional square-root-law fits, Kyle-lambda depth estimates, size-tail exponents and sign-autocorrelation diagnostics — never fabricating exponents, prefactors, impact coefficients, model parameters or paper results that were not actually computed.

> Source: FinRobot strategies corpus review — `strategies/qfin-tr/price-impact-adverse-selection.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **$\delta=1/2$ is universal across stocks *and* across traders, at error bars of $0.06$.** A complete survey of every TSE account: 8 years (2012-01-04 – 2019-11-02), split at the 2015 *arrowhead* matching-engine update, gives $942+1{,}357=2{,}299$ liquid-stock datapoints (liquid $= >10^5$ metaorders) and 1,293 active traders ($>10^4$ metaorders). Cross-sectionally $\langle\delta\rangle=0.489\pm0.0015$ (SEM) with dispersion $\sigma_\delta=0.071$; trader-level $\langle\delta^{(i)}\rangle=0.493\pm0.0050$, $\sigma_{\delta^{(i)}}=0.177$. A Monte-Carlo null that *imposes* $\delta=1/2$ under order splitting (metaorder signs shuffled, physical submission times kept, $N_{\rm MC}=100$) reproduces both dispersions — $\langle\langle\delta\rangle\rangle=0.489\pm0.0013$, $\langle\langle\sigma_\delta\rangle\rangle=0.063$ — so the observed spread is finite-sample noise, not heterogeneity (arXiv:2411.13965v3).
- **The prefactor is *not* universal; only the exponent is.** Stock-level $\langle c\rangle=0.842$ and trader-level $\langle c^{(i)}\rangle=1.501$ on the TSE, and the aggregate plot only collapses onto one master curve after per-stock rescaling $I_s(Q)/c_s$ (arXiv:2411.13965v3). On AAPL the single-name prefactor is $c_{\rm raw}=0.69$ (95% CI $[0.64,0.75]$), bias-corrected $c_{\rm eff}=0.34$ (arXiv:2606.24019v1).
- **Two non-universal theories are rejected *directly*, not by the SRL fit.** GGPS predicts $\delta=\beta-1$ and FGLW predicts $\delta=\alpha-1$, with $P(Q)\propto Q^{-\beta-1}$ (metaorder volume) and $P(L)\propto L^{-\alpha-1}$ (child-order count). On the TSE the scatter of $\delta$ on $\beta$ and on $\alpha$ shows **no correlation at all**, even though both $\alpha,\beta\approx1.5$ superficially match $\delta=1/2$ (arXiv:2411.13965v3).
- **AAPL reproduces the SRL from an *anonymous* tape.** Full Nasdaq TotalView-ITCH market-by-order feed, 178 trading days (2024-12-02 – 2025-08-19), $\approx0.5$ billion events ($\approx3.2\times10^6$ events/day at nanosecond resolution), 1,012 reconstructed metaorders in the 20-day calibration window. SRL $R^2=0.95$ vs 0.20 for linear ($\Delta{\rm AIC}=22$) and $\Delta{\rm AIC}=5$ vs logarithmic; free exponent $\hat\delta=0.50$ (bootstrap 95% CI $[0.32,0.66]$); child-fill-count slope $0.62$ ($[0.52,0.71]$); size tail $\beta=1.54\pm0.15$ (Clauset $p=0.63$; likelihood-ratio vs exponential $Z=3.5$); prefactor stable at $0.63$–$0.77$ over 9 reconstruction settings and $[0.63,1.01]$ (mean 0.75) over 32 weekly walk-forward recalibrations (arXiv:2606.24019v1).
- **The SRL's two preconditions are measured, not assumed.** Aggressor-sign autocorrelation $C(\ell)\propto\ell^{-\gamma}$ with $\gamma=0.66<1$ (long memory) while the mid-price variance ratio stays in $[0.91,1.04]$ from 10 s to 5 min (Hurst 0.49): predictable flow coexisting with a diffusive price (arXiv:2606.24019v1). Sign permutation collapses directional alignment $85.9\%\to49.6\%$ (null $N=10^4$, $z=23$, $p<10^{-4}$); chronology scrambling kills the SRL ($0$ of $80$ calibrations viable).
- **Sign long memory and the SRL live on different clocks, and that is a formal statement.** An exact discrete bid/ask reaction–diffusion model reduces to a linear imbalance PDE; the moving mid-price front obeys a nonlinear Volterra equation whose leading order gives transient impact $p(t)\propto\sqrt{t}$ and completion $I(Q)\propto\sqrt{Q}$ at fixed participation. The same model's renewal structure independently gives the trade-sign autocorrelation $C_\tau(\epsilon)\sim\frac{c_L}{\alpha(\alpha-1)E[L]}\tau^{-(\alpha-1)}$, i.e. LMF $\gamma=\alpha-1$. LMF is an *event-time* statement and the SRL an *operational/physical-time* one; subordination $X(t)=Y_{N_t}$ links them, so heavy-tailed waiting times can deform the calendar-time impact trajectory without touching the event-time sign law (arXiv:2606.16269v2).
- **Kyle's model becomes a variational problem whose shadow price is stochastic market depth.** With stochastic noise volatility $\sigma_t$ and $n$ assets, equilibrium is generated by a matrix-valued $\mathcal F^W$-martingale depth $M^*_t$ minimizing $\inf_{M}\operatorname{tr}(CM_0)+\mathbb E\int_0^T\frac12\operatorname{tr}(\sigma_t^2M_t^{-1})dt$; price impact is $\Lambda^*_t=(M^*_t)^{-1}$, the terminal identity $C=\int_0^T(M^*_t)^{-1}\sigma_t^2(M^*_t)^{-1}dt$ forces $\Sigma^*_T=0$, and the insider's optimal release is inconspicuous, $\mathbb E[dX^*_t/dt\mid\mathcal F_t^M]=0$. The variational optimizer exists as a *local* martingale in general and is a true martingale only under the **martingale dual condition (MDC)** — verified in the scalar case and with a common eigenbasis, open in general (arXiv:2607.10934v1).
- **Risk-averse market makers merge adverse selection with inventory risk.** With CARA dealers, liquidity is *lower* — scalar $\lambda=\sigma_v/\sigma_z$ with risk-neutral $\sigma_v>\hat\sigma_v$ — market-maker inventories mean-revert (matrix $A_t$ rising to $\sigma_z^2/T$), risk premia equal $\lambda$ times inventory, prices show short-term reversal and *excess volatility* (quadratic variation $=$ risk-neutral covariance $>$ unconditional terminal variance), and in a stock-plus-option market implied volatility *predicts* the stock return: univariate implied-vol coefficients $0.444$ (s.e. 0.030, $R^2=0.021$), $0.381$, $0.347$, $0.253$ across four $2\times2$ noise-covariance settings, with the sign flipping under a prior-return control (arXiv:2006.09518v3). Risk-neutrally, informed profit equals $\tfrac12(\|\tilde v\|^2+\|Z_T\|^2-W_2^2(F,G))$, a Wasserstein-2 gap between the terminal-value and noise-trade distributions (arXiv:2006.09518v3).
- **Competing risk-averse liquidators have a closed-form Nash equilibrium in a transient-impact game.** With decay kernel $G$ and $n$ agents, the unique mean-variance equilibrium is $\zeta_i=\bar Xv+(X_i-\bar X)w$ (also a CARA-utility equilibrium when the unaffected price is a Bachelier martingale); $v$ is the common strategy when all inventories coincide, $w$ the zero-sum strategy, and the two oscillate for quadratic transaction costs below $\kappa^*_v=(n-1)/4$ (increasing in the number of players, independent of risk aversion) and $\kappa^*_w=1/4$ (independent of the number of players, damped by risk aversion) respectively (arXiv:1807.03813v2).
- **Off-topic note.** None of the six is off-topic, and none is a restatement of another. arXiv:2607.10934v1 and arXiv:1807.03813v2 carry **no market data at all** (theory plus numerics); both are retained because they are the set's only mechanism-level models of endogenous stochastic depth and of risk-averse predatory liquidation.

## Methods & Formulas

### 2.1 Cross-sectional SRL estimation with finite-sample null calibration
**Purpose.** Decide whether $\delta=1/2$ is universal across a universe, separating true exponent heterogeneity from fitting noise.

**Formula.** Non-dimensionalise $\tilde Q=Q/V_D$ and $\tilde I=I/\sigma_D$, with $I=\epsilon\,(m_{\rm end}-m_{\rm start})$, $\epsilon=\pm1$ the metaorder sign, and $\sigma_D$ the Parkinson high–low range of the mid. Per stock fit
$$\tilde I(\tilde Q)=c\,\tilde Q^{\delta}\quad\text{by relative least squares on conditional bin means: }\min_c\sum\frac{(\hat I-I)^2}{\hat I^2},$$
then report $\langle\delta\rangle\pm\text{SEM}$ and $\sigma_\delta$. Error bars come from a Monte-Carlo null that imposes $\delta=1/2$ exactly: shuffle metaorder signs, keep the physical submission times, regenerate the price series, refit.

**Required inputs.** Per-stock metaorder list (`sign`, `total volume`, `start mid`, `end mid`); daily `volume` $V_D$; daily `high`, `low` for $\sigma_D$.

**Parameters & defaults.** Logarithmically spaced bins with $\ge100$ observations; only metaorders whose liquidation horizon exceeds $60$ s; liquid-stock filter $>10^5$ metaorders; trader-level filter $>10^4$; $N_{\rm MC}=100$; relative (not ordinary) least squares.

**Observed effect sizes.** $\langle\delta\rangle=0.489\pm0.0015$ and $\sigma_\delta=0.071$ vs the null's $0.063$; the OLS-on-raw variant gives $\langle\delta\rangle=0.474\pm0.0012$ (arXiv:2411.13965v3).

**Failure modes.** IID error formulas understate the true error by ~3–4× under serial correlation — $0.014$–$0.022$ against the model-based $0.063$ (arXiv:2411.13965v3) — so the Monte-Carlo null, not a regression package, is the honest bar. A single-name fit over ~20 days cannot resolve $\delta$ at all (CI $[0.32,0.66]$, arXiv:2606.24019v1); use an ARIMA-type serial-correlation model for any non-complete survey.

### 2.2 Discriminating the non-universal models (GGPS, FGLW)
**Purpose.** Test the mechanism hypotheses $\delta=\beta-1$ and $\delta=\alpha-1$ once $\delta$ has been measured per stock. This is the sharpest available test because it does not depend on the SRL fitting well.

**Formula.** Power-law tails $P(Q)\propto Q^{-\beta-1}$, $P(L)\propto L^{-\alpha-1}$ by maximum likelihood (Hill) with a KS-optimal cutoff (Clauset); then test $\operatorname{corr}(\delta,\beta-1)$ and $\operatorname{corr}(\delta,\alpha-1)$ across stocks.

**Required inputs.** Per-stock metaorder volumes $Q$ and corresponding child-order counts $L$.

**Parameters & defaults.** Metaorders as maximal same-signed runs of market orders, reset daily; Clauset KS-optimal cutoff for each tail.

**Observed effect sizes.** No correlation in either scatter across 2,299 stock-datapoints; typical $\alpha,\beta\approx1.5$ (arXiv:2411.13965v3). AAPL independently gives $\beta=1.54\pm0.15$, so the $\beta\approx1.5$ coincidence is real (arXiv:2606.24019v1).

**Failure modes.** The rejection is only as good as the tail fit: a mis-set cutoff makes $\beta,\alpha$ unstable, and both models also assume Zipf-distributed order-splitter size; two rejections falsify those mechanisms but do not prove the latent-order-book alternative.

### 2.3 Metaorder reconstruction from an anonymous tape
**Purpose.** Turn a raw trade stream into parent orders when broker/member tags are absent — the precondition for everything in 2.1–2.2.

**Formula.** Split the session into fixed-width bins; assign each bin the sign of its volume-weighted imbalance; a *run* is a maximal same-sign streak whose aggregate dominance exceeds $\theta$. Keep runs with duration $\ge d$ and size $\ge sV_D$, so $Q=\sum_{\rm run}q_k$ and $I=\epsilon(m_{\rm end}-m_{\rm start})$.

**Required inputs.** `signed trades` (aggressor side, timestamp, size), `mid price` at each trade, `daily volume` $V_D$.

**Parameters & defaults.** 30 s bins, dominance $\theta=0.3$, $d=60$ s, $s=10$; robustness sweep $\theta\in\{0.2,0.3,0.4\}$ and bin width $\{20,30,45\}$ s. TSE definitional variant: consecutive same-signed market orders belong to one metaorder, reset daily.

**Observed effect sizes.** 1,012 reconstructed metaorders in a 20-day AAPL window; all 9 reconstruction settings keep $c\in[0.63,0.77]$ and $\delta$ near $1/2$ (arXiv:2606.24019v1); the TSE run definition recovers the cross-sectional band (arXiv:2411.13965v3).

**Failure modes.** Anonymous reconstruction absorbs *other* participants' same-signed child flow, over-counting size and inflating the prefactor by ~2× — report $c_{\rm raw}$ as an upper bound and $c_{\rm eff}=c_{\rm raw}/2$ as the single-agent proxy. Hidden/cross prints (~19% including auctions) must be signed by a tick rule; auction crosses $\ge50{,}000$ shares must be dropped. Including limit-order splitting biases impact, because limit-order impact is theoretically negative.

### 2.4 Stochastic-liquidity / multi-asset Kyle depth
**Purpose.** Replace a constant Kyle $\lambda$ by a *state-dependent, matrix-valued* price-impact process, and time informed release to favourable liquidity states.

**Formula.** With prior covariance $C$ and noise-volatility matrix $\sigma_t$,
$$\inf_{M\in\mathcal M}\ \operatorname{tr}(CM_0)+\mathbb E\!\int_0^T\!\tfrac12\operatorname{tr}\!\big(\sigma_t^2M_t^{-1}\big)dt,\qquad \Lambda_t^*=(M_t^*)^{-1},\qquad P_t^*=p_0+\int_0^t\Lambda_s^*\,dY_s^*,$$
$$C=\int_0^T(M_t^*)^{-1}\sigma_t^2(M_t^*)^{-1}dt,\qquad \Sigma_t^*=\int_t^T(M_s^*)^{-1}\sigma_s^2(M_s^*)^{-1}ds,\qquad dX_t^*=\sigma_t^2(M_t^*)^{-1}(\Sigma_t^*)^{-1}\big(\tilde v-p_0-\xi_t^*\big)dt.$$
$M^*$ is the dual/shadow-price martingale of the *information inventory*; $\Sigma^*_t$ is the market maker's posterior covariance, $\Sigma^*_0=C$, $\Sigma^*_T=0$.

**Required inputs.** `terminal covariance` $C$ of asset values; a calibrated `noise-volatility process` $\sigma_t$ (or its dynamics). Kyle 1985/Back 1992/Collin-Dufresne–Fos 2016 are recovered as special cases.

**Parameters & defaults.** $\tilde v\sim N(p_0,C)$; scalar benchmark $T=1$, constant $\sigma$ gives $\Sigma^*(t)=\Sigma_0(1-t)$ and constant $\Lambda$; multi-asset benchmark uses a common time-independent eigenbasis of $C$ and $\sigma_t$.

**Observed effect sizes.** No empirics: the scalar and common-eigenbasis cases are proved to satisfy MDC, and the paper proves a matrix-valued Doob–Meyer decomposition used in the existence argument; the general case reduces to a coupled matrix FBSDE and is left open (arXiv:2607.10934v1).

**Failure modes.** MDC is a *hypothesis*: the dual optimizer exists only as a local martingale in general, so a numerical minimizer must be accepted only after checking the terminal identity $C=\int(M_t^*)^{-1}\sigma_t^2(M_t^*)^{-1}dt$ and interiority. Non-commuting $C,\sigma_t,M_t$ block simultaneous diagonalisation, so the scalar intuition does not carry over. The model is an equilibrium object, not an estimator: it needs a value covariance and a noise-volatility law, neither of which FinRobot can fetch.

### 2.5 Risk-averse Kyle with a stock and a derivative
**Purpose.** Turn adverse selection plus dealer inventory risk into a testable liquidity/risk-premium engine, including an implied-volatility signal that can be run on available option data.

**Formula.** Prices are the conditional expectation under the risk-neutral measure: $P_t=\mathbb E^{\mathbb Q}[\tilde v\mid\mathcal F_t^Y]$, with Kyle's matrix $\lambda=\nabla^2\varphi$ the Hessian of the Brenier potential $\varphi$ transporting the noise-trade law to the risk-neutral law of $\tilde v$ (symmetric PSD). With CARA dealers of absolute risk aversion $a$, the SDF is $d\mathbb Q/d\mathbb P=e^{-a\tilde w}/\mathbb E[e^{-a\tilde w}]$ ($\tilde w$ terminal dealer wealth), and
$$P_t=m+\lambda Y_t,\qquad \mathbb E[\tilde v]-P_0=\lambda\varsigma\ (\varsigma=\text{dealer endowment}),\qquad \lambda=\frac{\sigma_v}{\sigma_z}\ \text{(scalar),}$$
with $\lambda$ increasing in $a$; $Y_t$ and $P_t-m$ mean-revert with matrix $A_t\nearrow\sigma_z^2/T$. Risk-neutrally the informed trader's expected profit is
$$\mathbb E[\varphi(\tilde v)]=\tfrac12\big(\mathbb E\|\tilde v\|^2+\mathbb E\|Z_T\|^2-W_2^2(F,G)\big),$$
and dealer profit is $\langle P,Y\rangle_T+\varphi(Y_T)-\tilde v^{\top}Y_T$ — i.e. noise traders pay exactly the bid–ask cost $\langle P,Y\rangle_T$.

**Required inputs.** `option chain` (implied vols, option open interest/imbalance), `stock order imbalance`, `risk-free curve`, and the joint noise covariance $\Sigma$ of stock and option order flow.

**Parameters & defaults.** $a=0.2$ (wealth unit \$100M), $T=1$, lognormal risk-neutral stock ($\log \tilde v_s=\mu+x$, $x\sim N(0,1)$), strike $=100$, initial risk-neutral mean $100$, risk-neutral $20\%$ vol, four noise-covariance settings $\Sigma\in\{[[4,2],[2,4]],[[4,1],[1,1]],[[4,2],[2,4]],[[4,1],[1,4]]\}$ with the stock/option order correlation sign switched, 10,000 simulated paths, regression at $t=0.5$ (30 days to maturity, matching An et al.).

**Observed effect sizes.** Univariate implied-vol coefficient on the stock risk premium: $0.444$ (s.e. $0.030$, $R^2=0.021$), $0.347$, $0.381$, $0.253$; adding the prior-return control (a mean-reversion term) gives $+0.47/+0.53$ when stock/option noise trades are negatively correlated and $-0.60/-0.19$ when positively correlated; the prior-return coefficient is always negative ($-2.19$ to $-1.77$), the model's excess-volatility/reversal signature (arXiv:2006.09518v3).

**Failure modes.** The physical density consistent with a single-strike risk-neutral lognormal comes out *bimodal* — an artefact of trading one option; multiple strikes smooth it. The sign of the implied-vol coefficient depends on the unobserved stock/option noise correlation, so a positive univariate regression is not identification (see §4). Risk aversion *raises* the informed trader's expected profit (dealers shed inventory risk), so "lower liquidity ⇒ lower informed profit" is false in this model. All results are cross-sections of simulated paths, not fitted estimates.

### 2.6 Risk-averse transient-impact Nash game (competing liquidators)
**Purpose.** Schedule one's own liquidation when $n-1$ rival risk-averse agents liquidate the same asset — the predatory-trading / adverse-selection-in-time problem.

**Formula.** With decay kernel $G$ and price $S_t=S_t^0-\sum_{t_k<t}G(t-t_k)\sum_i\zeta_{i,k}$, define the cost matrix (the paper writes its quadratic-transaction-cost coefficient and its risk-aversion parameter with the same letter $\gamma$ in different places — keep them apart):
$$\Sigma^{\kappa,\varrho}_{ij}=G(|t_i-t_j|)+\varrho\,(t_i\wedge t_j)+2\kappa\,\delta_{ij},\qquad \varrho(t)=\operatorname{Var}(S^0_t),$$
where $\kappa\ge0$ is the quadratic transaction-cost coefficient, $\delta_{ij}$ the Kronecker delta, and the competitor part is the paper's matrix $\tilde\Sigma$. Then the unique mean-variance Nash equilibrium of $\text{MV}_i=\mathbb E[C_T(\zeta_i\mid\zeta_{-i})]+\frac{\gamma}{2}\operatorname{Var}[C_T(\zeta_i\mid\zeta_{-i})]$ ($\gamma\ge0$ risk aversion) is
$$\zeta_i=\bar X\,v+(X_i-\bar X)\,w,\qquad i=1,\dots,n,\qquad \bar X=\tfrac1n\textstyle\sum_jX_j,$$
with the two normalised base strategies solving
$$\big(\Sigma^{\kappa,\varrho}+(n-1)\tilde\Sigma\big)v=\alpha e_1,\quad \mathbf 1^{\top}v=1,\qquad \Sigma^{\kappa,\varrho}w=\beta e_1,\quad \mathbf 1^{\top}w=1 .$$

**Required inputs.** `initial inventories` $X_1,\dots,X_n$; `time grid`; `decay kernel` $G$; `unaffected-price variance` $\varrho(t)$; `quadratic-transaction-cost coefficient` $\kappa$; `risk-aversion coefficient` $\gamma$.

**Parameters & defaults.** $G(t)=e^{-\rho t}$ (also tested with $G(t)=1/(1+t)^p$, $p>0$), Bachelier $S_t^0=S_0+\sigma B_t$ with $\sigma=1$, equidistant grid $T_N=\{k/N\}$ with $N$ up to 500; deterministic strategies for the mean-variance problem, adapted strategies allowed for CARA.

**Observed effect sizes.** The oscillation threshold in the transaction cost for $v$ is $\kappa^*_v(n)=\sup_{N,\gamma}\kappa_v(n,N,\gamma)=(n-1)/4$ — independent of risk aversion, linear in the number of players; for $w$ it is $\kappa^*_w=\sup_{N,\gamma}\kappa_w(N,\gamma)=1/4$ — independent of $n$ and *damped* by risk aversion. Closed form at $\kappa=1/4$, $\varrho=0$: $w_0=w_N=\frac{1-e^{-\rho/N}}{N(1-e^{-\rho/N})+1}$, $w_N=\frac{1}{N(1-e^{-\rho/N})+1}$ (arXiv:1807.03813v2). The infinite-horizon equilibrium exists only at that same critical transaction cost, $\kappa=(n-1)/4$, through the unique positive root of two scalar equations; if $X_1=\dots=X_n$ and $\kappa\neq(n-1)/4$ no exponentially decaying equilibrium exists.

**Failure modes.** The mean-variance functional is time-inconsistent unless strategies are deterministic, so it must be optimised over deterministic strategies (CARA may use adapted ones). Oscillating equilibrium strategies are a genuine predatory-protection effect, not numerical noise — backtesting one agent's leg in isolation is meaningless, and a single agent ($n=1$) is always buy-only or sell-only. The infinite-horizon uniqueness of the CARA equilibrium is not proved (only the mean-variance one is).

### 2.7 Volterra/LLOB impact with renewal sign memory and subordination
**Purpose.** One model that generates both concave impact decay and long-memory signs, so a fitted impact kernel can be checked against observed sign memory, and event-time laws can be mapped to calendar time.

**Formula.** The signed-imbalance field obeys $\partial_t\phi=D\partial_{xx}\phi-\nu\phi+s^{lit}+s^{lat}+m$, and the mid-price front (the moving zero of $\phi$) gives $\dot p=-\big(D\partial_{xx}\phi+s+m\big)/\partial_x\phi\big|_{x=p}$. With local-linear slope $L=-\partial_x\phi^*(p_0)>0$ this yields the exact Volterra equation
$$L\,p(t)=\int_0^t m(s)\,\frac{e^{-\nu(t-s)}}{\sqrt{4\pi D(t-s)}}\exp\!\Big(\!-\frac{(p(t)-p(s))^2}{4D(t-s)}\Big)ds,$$
and at leading order (weak cancellation $\nu(t-s)\ll1$, small displacement, constant rate $m_0=Q/T$ with participation $\eta$ against background flux $J$)
$$p(t)\approx\frac{m_0}{L}\sqrt{\frac{t}{\pi D}},\qquad I(Q)=\frac{1}{L}\sqrt{\frac{m_0Q}{\pi D}}=\sqrt{\frac{\eta J Q}{\pi D L^2}} .$$
Independently, non-overlapping i.i.d. metaorders with lengths $L_n$ give the exact renewal sign autocorrelation and its Pareto-tail form
$$C_\tau(\epsilon)=\frac{1}{\mathbb E[L]}\sum_{\ell>\tau}(\ell-\tau)P(L=\ell)\ \sim\ \frac{c_L}{\alpha(\alpha-1)\mathbb E[L]}\,\tau^{-(\alpha-1)}\ \Longrightarrow\ \gamma=\alpha-1 .$$
Calendar time is the subordinated process $X(t)=Y_{N_t}$, $N_t=\max\{m:T_m\le t\}$, $T_m=\sum_{k\le m}\Delta t_k$.

**Required inputs.** `child-order event stream` (sign $\epsilon_m$, size $q_m$, timestamp); `event waiting times` $\Delta t_m$; `book depth` near the touch (for $L$); `diffusion` and `cancellation` constants $D,\nu$; `participation rate` $\eta$.

**Parameters & defaults.** Constant participation $m_0=Q/T$; exponential arrivals and zero memory recover the canonical discrete update; $L$ from the stationary imbalance slope at the front; the pure $\sqrt{t}$ law needs weak cancellation.

**Observed effect sizes.** No new data — the paper derives the LMF relation $\gamma=\alpha-1$ and the $\sqrt{Q}$ law rather than measuring them; the AAPL-measured $\gamma=0.66$ and the TSE-given $\alpha\approx1.5$–$1.7$ are the empirical anchors to plug in (arXiv:2606.24019v1, arXiv:2411.13965v3). The transient law is $\sqrt{t}$ in operational time, not calendar time.

**Failure modes.** Three clocks — event time $m$, operational time $u$, calendar time $t$ — are conflated at your peril: the LMF law holds in event time, the SRL in operational time, and if waiting times are heavy-tailed the calendar-time impact becomes anomalous even though the event-time law is unchanged. Three distinct sign conventions exist (primary $\sigma_m$; source-based $\operatorname{sign}(M_{j,m})$; flux-based $\operatorname{sign}(\Delta F_m)$) with different autocorrelations, agreeing only under one-step force dominance plus monotone flux response. The $\sqrt{Q}$ result requires weak cancellation and small displacement; near the horizon $\nu^{-1}$ the exponent need not stay $1/2$.

## Data Requirements

Rows below are real entries in `strategies/endpoints.json`; **gap** in bold means no current provider serves the input. `moomoo` rows are served by the local OpenD SDK gateway, not live-probed HTTP.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV ($V_D$, $\sigma_D$ Parkinson, ADV) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily OHLCV (tertiary) | `https://api.stockdata.org/v1/data/eod` | `core_stock_apis` | stockdata | ok |
| Previous-day aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday bars (coarse impact reconstruction) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Technical indicators / bars | `https://www.alphavantage.co/query` | `technical_indicators` | alpha_vantage | ok |
| Intraday K-line via local OpenD gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Top-of-book snapshot (best bid/ask only) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Tradable universe / tick sizes | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Option chain (implied vols, option imbalance) | `moomoo://get_option_chain` | `options_data` | moomoo | gateway (not live-probed) |
| Underlying/expected-move overview (straddle IV) | `moomoo://get_option_underlying_overview` | `expected_move` | moomoo | gateway (not live-probed) |
| Option surface, delayed quotes (IV) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | ok |
| Risk-free curve (option pricing) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| **Signed trade tape with aggressor flag** | — | — | — | **gap** |
| **Broker/member-tagged parent (meta)orders** | — | — | — | **gap** |
| **L2/L3 book depth (slope $L$, imbalance)** | — | — | — | **gap** |
| **Per-account order lifecycle (TSE/JVP equivalent)** | — | — | — | **gap** |
| **Event-time child-order stream + waiting times** | — | — | — | **gap** |

**What the gap costs, quantified.** The AAPL SRL calibration needs one name's *full* market-by-order tape: 178 days, $\approx3.2\times10^6$ events/day ($\approx0.5$ B events) at nanosecond resolution, from which only 1,012 usable metaorders emerge in a 20-day window — so a bar-level substitute has neither the aggressor sign nor the chronology that the two null tests (§4) depend on. The TSE survey needs 8 years of *account-level* order lifecycles for all stocks: 2,299 stock-datapoints, $>10^5$ metaorders per stock, 1,293 traders each with $>10^4$ metaorders — three to four orders of magnitude more than any consumer feed sells, and behind an NDA. The reaction–diffusion/renewal model (2.7) needs the child-order *event stream plus waiting times*, i.e. a trade tape with inter-arrival gaps, not bars. The Kyle papers are worse off still: they need the *noise-volatility process* and terminal-value covariance, which no market-data endpoint provides at all; they are research objects (§5, item 5). Conversely, the option side of 2.5 is fully served today — `moomoo://get_option_chain`, `moomoo://get_option_underlying_overview` and the Cboe surface all deliver implied volatility, so the implied-vol-predicts-returns signal is the one theory result that can be tested on live data immediately.

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Fitted-vs-imposed exponent.** Never fit $\delta$ on one name over a short window: the bootstrap CI $[0.32,0.66]$ would not exclude a linear law at the margins (arXiv:2606.24019v1). Fix $\delta=1/2$ and report the free fit only as a consistency check; the universality evidence is *cross-sectional* (arXiv:2411.13965v3).
- **Serial-correlation-aware error bars.** Standard packages gave $0.014$ (OLS on raw) and $0.022$ (relative LS on bins) for $\delta$'s error, versus the true finite-sample value $0.063$ from the exact-SRL Monte-Carlo model — a 3–4.5× understatement (arXiv:2411.13965v3, footnote 2). Any per-stock significance test must use the model-based bar.
- **Anonymous-reconstruction bias.** Reconstructing parent orders from an anonymous tape absorbs other participants' same-signed flow and inflates the prefactor by ~2×; report $c_{\rm raw}$ and $c_{\rm eff}=c_{\rm raw}/2$ and treat the raw value as an upper bound (arXiv:2606.24019v1).
- **Sign and chronology null tests are the acceptance gate.** Permute aggressor signs with timestamps fixed (target: directional alignment collapses from ~86% to ~50%, $z>20$, $p<10^{-4}$) and scramble event chronology (target: 0 of 80 calibrations viable). If shuffling signs still "works", the estimator is leaking (arXiv:2606.24019v1, and mirroring the TSE paper's shuffled-sign Monte-Carlo model at arXiv:2411.13965v3).
- **Multiple testing across thousands of fits.** The TSE paper does not run 2,299 independent SRL regressions and pick winners; it *compares the distribution* of $\hat\delta$ against an exact-SRL null, i.e. it makes one global statement via $\langle\delta\rangle$ and $\sigma_\delta$ vs $\langle\langle\sigma_\delta\rangle\rangle$ (arXiv:2411.13965v3). Adopt the same discipline: report the cross-sectional histogram and dispersion, not the best fit. For the GGPS/FGLW scatters a single correlation over 2,299 points is the test — do not shop for sub-samples.
- **Sample splitting and regime changes.** The TSE data are split at the 2015 *arrowhead* update because all virtual-server IDs were reshuffled; the same ticker in the two eras is treated as two different stocks, and only three of the four aggregate-plot coefficients coincide. Any regime or exchange change must invalidate ID continuity (arXiv:2411.13965v3). AAPL uses a 20-day calibration window with 158 out-of-sample days and re-estimates every 5 days on a trailing 20-day window (arXiv:2606.24019v1).
- **Selection bias at the tails.** Price-limit and circuit-breaker days — exactly the days with the largest impact — are excluded from the TSE analysis to limit implementation bias, since a trader may pause execution when the price runs (arXiv:2411.13965v3). Dropping them removes the extreme right tail of $Q$; state this when quoting $\langle c\rangle$.
- **Distributional assumptions are tested, not asserted.** The metaorder size tail passes a Clauset goodness-of-fit but is *not* separable from a lognormal; report both (arXiv:2606.24019v1). Metaorder length and count tails ($\alpha,\beta$) set the power-law fits on which the GGPS/FGLW rejection rests, so their cutoff sensitivity must be shown (arXiv:2411.13965v3).
- **Time-clock confusion.** The LMF exponent $\gamma=\alpha-1$ is an event-time statement; the $\sqrt{Q}$ impact law is a physical/operational-time statement. Heavy-tailed waiting times (DTRW $\to$ CTRW) break the proportionality $N_t\propto t$ and can make calendar-time impact anomalous while LMF is untouched (arXiv:2606.16269v2). Measure $\gamma$ in event time and $I(Q)$ in calendar time, and never mix the two.
- **Model-selection caveats on the theory side.** MDC (equilibrium existence in the multidimensional Kyle model) is a hypothesis verified only in the scalar/common-eigenbasis cases (arXiv:2607.10934v1). The mean-variance game is time-inconsistent unless restricted to deterministic strategies (arXiv:1807.03813v2). The implied-vol predictor's *sign* depends on the unobserved stock/option noise correlation, so a univariate positive regression is not identification (arXiv:2006.09518v3).
- **Metric choice.** For impact: non-dimensional $\tilde I$, relative ($\chi^2$-like) least squares on log-binned means, and $\Delta$AIC against the linear and logarithmic alternatives; for tails: Hill/Clauset with a KS cutoff plus Clauset $p$ and likelihood-ratio $Z$; for sign memory: the ACF exponent $\gamma$. The papers report $R^2=0.95$ vs 0.20 (impact), $p=0.63$/$Z=3.5$ (size tail), and $\gamma=0.66$ (sign ACF).

## Recommended Workflow

Ranked by value per effort against what the data layer can fetch today. Items 1–3 are bar-level and buildable now; 4 consumes the option endpoints; 5–6 are research/simulator-side; 7 is the enabler.

1. **Cross-sectional SRL calibrator (§2.1).** *Consumes:* eodhd `eod` / tiingo `prices` for $V_D,\sigma_D$, twelvedata `time_series` for intraday volume profiles, `exchange-symbol-list/US` for the universe. *Passing:* across $\ge30$ names, $\langle\delta\rangle$ within $1.5$ SEM of $0.5$ and the cross-sectional dispersion not exceeding a shuffled-sign Monte-Carlo null; $c$ in $[0.5,1.0]$; $\Delta$AIC $\ge5$ against both linear and log. *Effort:* S.
2. **Metaorder reconstruction + tail-exponent pipeline (§2.2–2.3).** *Consumes:* the same bars plus, once available, a signed tape; run the 9-setting robustness sweep. *Passing:* $\beta\in[1.3,1.8]$ with a Clauset $p>0.1$, prefactor stable across all 9 settings, and the sign-permutation null collapsing to $\approx50\%$. *Effort:* M.
3. **Sign-ACF / LMF estimator (§2.7).** *Consumes:* signed trade tape (blocked) — prototypable on intraday bar signs as a coarse proxy. *Passing:* $C(\ell)\propto\ell^{-\gamma}$ with $\gamma=1-\alpha$ within CI and $\gamma<1$; the estimator must fail the permutation null. *Effort:* S (after tape for the real version).
4. **Implied-vol-predicts-return test (§2.5).** *Consumes:* `moomoo://get_option_chain` (or the Cboe surface) for implied vols, `moomoo://get_market_snapshot` for order imbalance, `federal_reserve` for the risk-free curve. *Passing:* a positive, significant univariate implied-vol coefficient *and* the paper's sign check — the coefficient must not survive as the sole regressor when the prior-return control is added and the (estimated) stock/option noise correlation is positive. *Effort:* M.
5. **Stochastic-liquidity depth solver (§2.4).** *Consumes:* nothing live — a numerical minimiser over $M$ plus a calibrated $\sigma_t$. *Passing:* the returned $M^*$ satisfies the terminal identity $C=\int_0^T(M_t^*)^{-1}\sigma_t^2(M_t^*)^{-1}dt$ to tolerance and $\Sigma^*_t$ is positive definite and decreasing; the scalar case reproduces Kyle's linear $\Sigma^*(t)=\Sigma_0(1-t)$. *Effort:* M.
6. **Competing-liquidation game solver (§2.6).** *Consumes:* nothing live — inventories, grid, kernel. *Passing:* reproduces the $(n-1)/4$ and $1/4$ oscillation thresholds numerically and the closed-form $w$ at $\kappa=1/4$; then use it to warn when a scheduled liquidation sits in the oscillatory regime. *Effort:* M.
7. **Acquire a signed trade tape (register a new data category).** *Consumes:* the feed itself; add `tick_trades`/`order_book_depth` next to the existing categories. *Passing:* aggressor sign, size and timestamp for every print on $\ge1$ name $\times$ $\ge20$ days; the §4 null tests then run end-to-end. *Effort:* L. It unblocks the real versions of items 2–3.

## Output Format

### Square-Root-Law Calibration
| Symbol | Metaorders | delta | c (raw / eff) | R^2 | AIC vs linear / log | MC-null sigma_delta |
|--------|-----------|-------|---------------|-----|---------------------|---------------------|
| ... | ... | ... | ... | ... | ... | ... |

### Impact and Sign-Memory Diagnostics
| Test | Target | Observed | Pass |
|------|--------|----------|------|
| Aggressor-sign permutation | alignment ~86% -> ~50%, z>20 | ... | ... |
| Chronology scramble | 0 of 80 calibrations viable | ... | ... |
| Serial-correlation-aware SEM | model-based, not OLS 0.014 | ... | ... |
| Sign ACF exponent gamma | < 1, C(l) ~ l^-gamma | ... | ... |
| Size tail beta (Clauset) | in [1.3, 1.8], p > 0.1 | ... | ... |

### Verdict
State whether the fitted delta is consistent with 1/2 within a
serial-correlation-aware error bar, the prefactor c with its raw/effective
split, whether the sign and chronology null tests pass, and the exact data gap
(no signed tape, broker-tagged metaorders, or L2/L3 depth) that blocks the
real-versus-proxy distinction.

## References

| arXiv id | Title | Year |
|---|---|---|
| 2411.13965v3 | Strict universality of the square-root law in price impact across stocks: a complete survey of the Tokyo stock exchange | 2024 |
| 2607.10934v1 | Multidimensional stochastic liquidity in Kyle's model of informed trading | 2026 |
| 2606.24019v1 | Empirical Confirmation of the Square-Root Law of Market Impact in a U.S. Large-Cap Equity | 2026 |
| 2606.16269v2 | Revisiting Trade-sign Long-memory and Square-root Law price impact | 2026 |
| 2006.09518v3 | Optimal Transport and Risk Aversion in Kyle's Model of Informed Trading | 2020 |
| 1807.03813v2 | Nash equilibrium for risk-averse investors in a market impact game with transient price impact | 2018 |
