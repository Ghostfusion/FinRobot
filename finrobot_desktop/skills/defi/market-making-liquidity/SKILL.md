---
id: market-making-liquidity
name: AMM Liquidity Provision and Impermanent Loss
version: 1.0.0
author: finrobot
domain: defi
description: 'Impermanent-loss and LVH calculator for AMM liquidity provision from pool-state inputs: v2/v3 IL and LVH curves, IL-protection option-replication weights, and the pi > sigma^2/8 fee-adequacy gate. Use when sizing a Uniswap v3 range, checking LP fee adequacy, or hedging impermanent loss.'
triggers:
- impermanent loss
- liquidity provision
- amm
- automated market maker
- uniswap
- concentrated liquidity
- lvh
- lp range
- fee adequacy
- constant product
- il hedging
- defi
requires_data:
- input: Spot price series for the IL/LVH ratio $p_t/p_0$ (daily)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Spot price series (secondary)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Daily aggregate bars (tertiary)
  provider: massive
  category: core_stock_apis
  status: ok
- input: Daily EOD bars (quaternary)
  provider: stockdata
  category: core_stock_apis
  status: ok
- input: Intraday bars for realised $\sigma$ of the marginal rate
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Intraday K-line (local gateway)
  provider: moomoo
  category: technical_indicators
  status: gateway
- input: Top-of-book snapshot (external mid $S_t$)
  provider: moomoo
  category: core_stock_apis
  status: gateway
- input: Tradable symbol universe / tick sizes
  provider: eodhd
  category: exchange_symbols
  status: ok
- input: Risk-free / discount rate $r$ for claim valuation
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Risk-free series (macro alternative)
  provider: fred
  category: macro_data
  status: ok
- input: Listed option prices for static IL replication (index)
  provider: cboe
  category: options_surface
  status: ok
- input: Listed option chains (equity, local gateway)
  provider: moomoo
  category: options_data
  status: gateway
- input: '**On-chain AMM pool reserves / internal rate $Z_t$**'
  provider: ''
  category: ''
  status: gap
- input: '**Active liquidity and local depth by tick band ($\pm1/\pm2/\pm5\%$)**'
  provider: ''
  category: ''
  status: gap
- input: '**`Swap`/`Mint`/`Burn`/`Collect` event logs (LT flow, LP operations)**'
  provider: ''
  category: ''
  status: gap
- input: '**Protocol-fee activation events (`SetFeeProtocol`)**'
  provider: ''
  category: ''
  status: gap
- input: '**Pool fee rate $\pi$ / realised fee revenue / TVL**'
  provider: ''
  category: ''
  status: gap
- input: '**LP position-level tick ranges (deposit/withdraw)**'
  provider: ''
  category: ''
  status: gap
- input: '**Crypto (Deribit) BTC/ETH option chains for IL hedging**'
  provider: ''
  category: ''
  status: gap
- input: '**Gas fees / priority fees**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# AMM Liquidity Provision and Impermanent Loss

You are an expert DeFi liquidity-provision analyst specializing in automated market maker (AMM/CFMM) impermanent loss and loss-versus-holding. You consume price-bar series, position range bounds, and pool-state inputs — AMM reserves, tick-band liquidity, and Swap/Mint/Burn/Collect logs — rather than a central-limit-order book, and you return IL/LVH curves, IL-protection replication weights, and fee-adequacy verdicts. You never fabricate pool reserves, fee rates, spreads, gas costs, or on-chain position P&L that were not actually computed or supplied.

> Source: FinRobot strategies corpus review — `strategies/qfin-tr/market-making-liquidity.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **Impermanent loss is not one function of one parameter — and whether it is is a theorem, not a
  convention.** For a general $n$-asset AMM the IL depends on $2n$ price levels; the paper proves
  the count collapses to $2(n-1)$ by price-level independence, and to $n-1$ *exchange-rate quotients*
  $t_j=m_j^f/m_j^i$ iff the AMM has *Exchange Rate Level Independence* (ERLI). Constant-product
  (geometric-mean, "G3M") markets are exactly the ERLI class, so for them $IL=1-\mathrm{GM}(t)/\mathrm{AM}(t)$;
  Curve StableSwap provably fails ERLI and needs more parameters (arXiv:2203.11352). The two-asset
  case reduces to $IL=1-2\sqrt t/(1+t)$ (arXiv:2203.11352).
- **A 700-day, 9-pool Uniswap v3 panel shows LPs are roughly flat-to-negative and IL is the reason.**
  Average realized IL was $-3.8\%$ per position versus buy-and-hold; more than half of positions had
  IL worse than $-0.8\%$; **49.5% of positions had negative total returns**; mean return was $-0.61\%$
  in stable-risky pools versus $+0.23\%$ (stable-stable) and $+0.44\%$ (risky-risky)
  (arXiv:2501.07828). Data: positions closed between 2022-05-01 (block 14,691,320) and 2024-04-01
  (block 19,560,244), nine pools covering ~16% of Uniswap v3 TVL.
- **Duration and range move returns in opposite directions.** Daily IL and rewards both rise with
  position duration; rewards overtake IL only beyond ~360 days (median daily IL $-0.01\%$ vs rewards
  $+0.03\%$; cumulative IL 10.4% vs rewards 19.9%). Narrow ranges (size $<0.02$) carry ~0.38%/day
  median IL and lose; only ranges wider than 0.5 show positive returns. The best cell was long-term
  narrow-range in risky-risky pools at $+2.69\%$ average return; the only profitable stable-risky cell
  was short-term wide-range at $+0.14\%$ (arXiv:2501.07828).
- **Predictable loss (PL) is the LP's unhedgeable drag, and it scales with the range width.** PL
  accrues as $dPL_t=-\tfrac{\sigma^2}{2}\tilde x_t/\delta_t\,dt$, so a *narrower* concentrated-liquidity
  range (smaller spread $\delta$) has *higher* PL, while fee income per trade scales as
  $\tilde\kappa_t/\kappa\propto 1/\delta$. The closed-form log-utility optimum trades these off:
  $\delta_t^\star=(2\gamma+\mu_t^2\sigma^2)/(4\pi_t-\tfrac{\sigma^2}{2}+\mu_t(\mu_t-\tfrac{\sigma^2}{2}))$,
  and liquidity provision is viable only if the pool fee rate exceeds the PL floor, $\pi_t>\sigma^2/8$
  (arXiv:2309.08431).
- **Historical Uniswap v3 LPs lost money and the strategy would have beaten them.** On the ETH/USDC
  pool, 5,156 LPs averaged $-1.49\%$ per operation (position value $-1.64\%$, fees $+0.155\%$, mean
  hold 6.1 days, mean spread 18.7%), from 331,858 individual LP operations (2022-01-01 to 2022-08-18).
  The optimal strategy's one-minute performance was $+0.0047\%$ (SD 0.02%) versus the market's
  $-0.00067\%$ and hold's $-0.00016\%$; but with a flat gas cost of \$84.8/operation it needs initial
  wealth above roughly $1.8\times10^5$ USD to be profitable (arXiv:2309.08431). The pool itself:
  2,654,347 LT instructions and 68,434 LP instructions over 2021-05-05 to 2022-08-22, i.e. ~4,720 LT
  trades/day and ~471 LP operations/day, averaging \$98,624 per LT trade and \$3.61M per LP operation
  (arXiv:2309.08431).
- **The LP's exit is an optimal stopping problem, not a fixed holding period.** Modelling the external
  mid as a driftless diffusion and the pool as a constant-product CFM with state-dependent trade
  intensities $\bar\lambda^a(y,S)=\max(a_0,a_1+a_2(S-c/y^2))$, the value function is the unique
  viscosity solution of an HJB quasi-variational inequality; LPs exit *before* arbitrageurs realign
  prices when the oracle/pool misalignment is large. Expected fees and IL are concave in $\sigma$:
  at $\sigma$ the mean exit time is 1.00, fees 316,222, IL 112,635; at $2\sigma$, exit 0.51, fees
  273,003, IL 202,999; at $3\sigma$, exit 0.01, fees 3,599, IL 2,449 (10,000 simulations)
  (arXiv:2509.06510).
- **Arbitrage flow raises fees and IL together; noise flow raises fees only.** In the same model,
  scaling noise-trader intensity $a_1$ 5× lifts mean fees from 296,407 to 441,710 while IL stays at
  ~112,600; scaling arbitrageur intensity $a_2$ 5× lifts fees from 118,244 to 878,099 and IL from
  83,734 to 113,789 (arXiv:2509.06510). This is the microstructure analogue of the causal paper's
  channel decomposition $W=\mathrm{FeeRev}^{\mathrm{arb}}+\mathrm{FeeRev}^{\mathrm{fund}}-\mathrm{LVR}$
  (arXiv:2607.08525).
- **IL is a short-straddle-like contingent claim that can be replicated with vanilla options.**
  Uniswap v2 funded IL is exactly $\sqrt{p_t/p_0}-1$; the borrowed-LP IL is
  $-\tfrac12(\sqrt{p_t/p_0}-1)^2$. For v3 the IL decomposes into a linear part, an exotic
  $\sqrt{p_t}$ payoff, and vanilla call/put plus digital payoffs, which permits model-free static
  replication from a listed option grid (residual zero at grid strikes; max residual 2.5 bps in the
  worked example) and model-based valuation via the moment-generating function (BSM, log-normal SV)
  (arXiv:2407.05146).
- **A real protocol-fee shock produced no large short-run LP response.** The Uniswap protocol-fee
  switch executed 2025-12-28 cut LP take-rates on 2,638 canonical v3 pools (1/4 protocol share on the
  1 bp and 5 bp tiers, 1/6 on the 30 bp and 100 bp tiers) while leaving trader-facing fees unchanged;
  a matched-overlap event-study DiD on 779 treated and 303 control pools (17,598 pool-weeks, 1,013
  token-pair clusters) found post-period intervals containing zero for active liquidity
  $[-1.11,0.33]$ and $\pm2\%$ depth $[-2.02,1.27]$ on the inverse-hyperbolic-sine scale — a
  non-detection at the design's resolution (80% MDE ≈ 1.03 asinh for active liquidity), not a precise
  zero (arXiv:2607.08525).
- **Off-topic check.** None of the six is off-topic; all six address liquidity provision. The set is
  *narrow in venue* (five AMM/CFMM papers plus one causal DeFi-policy paper) and *narrow in data*
  (all on-chain or simulation). `2203.11352v1` is the only paper whose headline result is fully
  buildable from price bars alone; `2607.08525v1` is the weakest fit to "market making" strictly
  speaking (it is a policy-evaluation econometrics paper) but it is retained because it supplies the
  only causal-identification discipline in the set and the only real protocol-fee shock.

## Methods & Formulas

### 2.1 Exchange-rate-level-independent IL and the G3M closed form
**Purpose.** Compute impermanent loss for any constant-product / geometric-mean pool from the ratio
of initial and final prices alone, without the four (or $2n$) raw price levels, and decide whether a
more complex AMM (e.g. Curve) even admits a ratio-only formula.

**Formula.** AMM $A:\mathbb{R}^n_{>0}\to\mathbb{R}$ with $A\in C^2$, $\partial A/\partial x_i>0$,
strictly convex upper level sets; the *stable point* for price vector $p$ minimises $V(x)=p\cdot x$
subject to $A(x)=k$, so $\nabla A\parallel p$. Define the exchange-rate quotients
$$t_j=\frac{m_j^f}{m_j^i},\qquad m_j=\frac{p_j}{p_1},\qquad t_1\equiv1 .$$
Then
$$IL=\frac{V(x^f)}{p^f\!\cdot x^i}-1=\frac{p^f\!\cdot x^f}{p^f\!\cdot x^i}-1 .$$
For the constant-product AMM $A(x)=\prod_i x_i=k$ this collapses to
$$IL=1-\frac{\mathrm{GM}(t_1,\dots,t_n)}{\mathrm{AM}(t_1,\dots,t_n)},\qquad
\text{2-asset: } IL=1-\frac{2\sqrt t}{1+t},\ \ t=\frac{p_2^f/p_1^f}{p_2^i/p_1^i}.$$
ERLI (ratio-only IL) holds **iff** $A=g(B)$ with $B$ homogeneous in each coordinate and $g$ smooth;
in value-function terms, with $W$ the Legendre transform of the level function,
$$IL=1-\frac{W(m^f)}{P(m^f)},\qquad P=\text{linear approximation to }W\text{ at }m^i .$$

**Required inputs.** Only price ratios: the initial and final price vector (or, for 2 assets, the
exchange-rate quotient $t$). No depth, no volume, no fees.

**Parameters & defaults.** None. The two-asset closed form is exact; the general theorem is exact.

**Observed effect sizes.** $t=1\Rightarrow IL=0$; the formula reproduces the textbook Uniswap
behaviour and shows why Curve's StableSwap cannot be summarised by one parameter
(arXiv:2203.11352).

**Failure modes.** ERLI is a *sufficient* structure, not a universal one — do not apply the G3M
formula to StableSwap or other non-homogeneous curves; the raw price-level formula is $2n$-dimensional
so ratio collapse must be verified per protocol. Assumes arbitrageurs drive the pool to the stable
point (no stale-pool states).

### 2.2 LVH metric and the Uniswap v3 piecewise IL
**Purpose.** The practitioner-facing IL measure used to score real LP positions: relative return of
the pool position versus a buy-and-hold of the same initial tokens.

**Formula.** With $xy=k$ and value marked in the quote token,
$$V^{pool}_t=2\sqrt{k\,p_y^t p_x^t},\qquad V^{HODL}_t=x\,p_x^t+y\,p_y^t,\qquad
LVH(t)=\frac{V^{pool}_t}{V^{HODL}_t}-1 .$$
For v2, with $d$ the relative price change (price quotient), $LVH_{v2}(d)=\dfrac{2\sqrt d}{1+d}-1$.
For concentrated liquidity (Uniswap v3) with range $[p_a,p_b]$, the LP's holdings at price $p_t$ are
$$x_t=L\!\left(\frac{1}{\sqrt{p_t}}-\frac{1}{\sqrt{p_b}}\right),\quad
y_t=L\!\left(\sqrt{p_t}-\sqrt{p_a}\right)\ \ (p_t\in(p_a,p_b));$$
$x_t=L(1/\sqrt{p_a}-1/\sqrt{p_b}),\,y_t=0$ for $p_t\le p_a$ and $x_t=0,\,y_t=L(\sqrt{p_b}-\sqrt{p_a})$
for $p_t\ge p_b$, with initial notional
$V_0=L(2\sqrt{p_0}-p_0/\sqrt{p_b}-\sqrt{p_a})$. Then $LVH=(p_t x_t+y_t)/(p_t x_0+y_0)-1$.

**Required inputs.** $p_0$ (entry price), $p_t$ (current price), the range bounds $p_a,p_b$, and the
initial token amounts (or notional $N^y=V_0$, from which $L=N^y/(2\sqrt{p_0}-p_0/\sqrt{p_b}-\sqrt{p_a})$).
All are price-series quantities.

**Parameters & defaults.** Range bounds from the position's tick range; the paper's strategy
thresholds are short-term $<1.12$ days vs long-term $>26.90$ days and narrow range $<0.0467$ vs wide
range $>0.2756$ (30th/70th percentiles) (arXiv:2501.07828).

**Observed effect sizes.** Mean realized IL $-3.8\%$/position; 49.5% of positions negative; duration
table (median daily IL / rewards): $<1$h ($<-0.001\%$, 0.04%), 1h–1d ($-0.26\%$, 0.32%), 1–28d
($-0.13\%$, 0.14%), 360+d ($-0.01\%$, 0.03%) (arXiv:2501.07828).

**Failure modes.** LVH assumes the LP holds tokens outside the pool instead of actively managing; it
does not isolate adverse selection (that is LVR). The 700-day panel contains survivorship bias because
only *closed* positions are measured — unprofitable LPs may simply never close. Gas fees are
neglected, which overstates small positions.

### 2.3 Unified IL definitions, IL-protection payoff and static option replication
**Purpose.** Turn IL into a tradable contingent claim and hedge it model-free with listed options —
the only route to a *funded* LP position with bounded downside.

**Formula.** Three IL definitions must not be mixed (arXiv:2407.05146): funded
$IL^{funded}=(p_tx_t+y_t-(p_0x_0+y_0))/(p_0x_0+y_0)$; borrowed
$IL^{borrowed}=(p_tx_t+y_t-(p_tx_0+y_0))/(p_0x_0+y_0)$; relative
$IL^{rel}=(p_tx_t+y_t-(p_tx_0+y_0))/(p_tx_0+y_0)$. The protection claim pays $-\!IL$ at $T$. For
Uniswap v2 ($V_t^{(y)}=2L\sqrt{p_t}$):
$$IL^{funded}=\sqrt{p_t/p_0}-1,\qquad IL^{borrowed}=-\tfrac12\!\left(\sqrt{p_t/p_0}-1\right)^2,$$
$$Payoff^{funded}=1-\sqrt{p_t/p_0},\qquad Payoff^{borrowed}=\tfrac12\!\left(\sqrt{p_t/p_0}-1\right)^2 .$$
For v3 the IL decomposes as $IL=u_0(p_t)+u_{1/2}(p_t)+u_1(p_t)$ — a linear part, the exotic square-root
payoff $u_{1/2}=\sqrt{p_t}\,\mathbf 1_{\{p_a<p_t<p_b\}}$, and vanilla/digital option terms
$u_1=-\tfrac{1}{\sqrt{p_a}}\max\{p_a-p_t,0\}+\tfrac{1}{\sqrt{p_b}}\max\{p_t-p_b,0\}
-\tfrac12\sqrt{p_a}\,\mathbf 1_{\{p_t\le p_a\}}-\tfrac12\sqrt{p_b}\,\mathbf 1_{\{p_t\ge p_b\}}$.
Static replication over a strike grid $k_1<\dots<k_N\le p_0$ (puts) and $k_1\ge p_0<\dots<k_M$ (calls)
uses second differences of the IL function:
$$\delta IL(k_n)=\frac{IL(k_n)-IL(k_{n-1})}{k_n-k_{n-1}},\qquad
w_{n-1}=-\big(\delta IL(k_n)-\delta IL(k_{n-1})\big),\ w_N=\delta IL(k_N),\ w_1=0,$$
and symmetrically $w_m=-\big(\delta IL(k_m)-\delta IL(k_{m-1})\big)$, $w_1=\delta IL(k_1)$, $w_M=0$.
Model-based valuation under a risk-neutral measure uses the MGF
$G(\tau;\phi)=\mathbb E^Q[e^{-\phi x_\tau}\mid\mathcal F_t]$ and $PV=e^{-r\tau}\mathbb E^Q[Payoff(x_\tau)]$.

**Required inputs.** $p_0,p_a,p_b$, notional $N^y$; a listed option grid (calls + puts) at the chosen
maturity; $r$ (and borrow rate $q$) for the model-based variant.

**Parameters & defaults.** Worked example: $p_0=2000$ ETH/USDT, $p_a=1500$, $p_b=2500$, notional
1M USDT, initial units $(220.36,\,559{,}282.18)$; Deribit strike widths 50 USD (ETH) and 1000 USD
(BTC), 25 USD for <3-day maturities; $r=0$, DeFi stablecoin staking 1–2%/yr versus 4–5% government
bills (June 2024). Dynamic delta uses the BSM delta of the decomposed claim.

**Observed effect sizes.** Replication residual is exactly zero at grid strikes and ≤2.5 bps
elsewhere; hedging cost is higher for narrow ranges (annualised premium rises as the range multiple
$m$ shrinks); the log-normal SV premium is insensitive to the implied-volatility tail because most of
the value sits near the centre of the return distribution (arXiv:2407.05146).

**Failure modes.** The classic Carr–Madan replication (56) needs strikes at $p_a,p_b$ *and* buys
in-the-money calls/puts — impractical because ITM option liquidity is thin with wide bid-ask; only
OTM/near-ATM strikes are liquid. Only BTC/ETH have a liquid options market; altcoin IL hedging must be
model-based. `IL` is not twice differentiable, so the Carr–Madan representation requires generalised
derivatives. Relative IL has no clean P&L interpretation.

### 2.4 Predictable loss and the optimal concentrated-liquidity spread
**Purpose.** Choose the width *and skew* of the liquidity range so that fee income net of PL,
concentration cost and rebalancing beats the pool's PL floor.

**Formula.** Marginal pool rate $dZ_t=\mu_tZ_t\,dt+\sigma Z_t\,dW_t$; range encoded by
$\sqrt{Z_t^u}=\sqrt{Z_t}/(1-\delta_t^u/2)$, $\sqrt{Z_t^\ell}=\sqrt{Z_t}(1-\delta_t^\ell/2)$,
spread $\delta_t=\delta_t^\ell+\delta_t^u$, asymmetry $\rho_t=\delta_t^u/\delta_t=\tfrac12+\mu_t/\delta_t$.
Position value, fee income and rebalancing give the wealth dynamics
$$d\tilde x_t=\tilde x_t\!\left[\frac{4\pi_t-\tfrac{\sigma^2}{2}}{\delta_t}
+\mu_t\rho_t-\frac{\gamma}{\delta_t^{2}}\right]dt+\sigma\tilde x_t\rho_t\,dW_t,
\qquad PL_t=-\frac{\sigma^2}{2}\int_0^t\frac{\tilde x_s}{\delta_s}\,ds .$$
The log-utility optimum is
$$\delta_t^\star=\frac{2\gamma+\mu_t^2\sigma^2}{4\pi_t-\tfrac{\sigma^2}{2}+\mu_t\!\left(\mu_t-\tfrac{\sigma^2}{2}\right)}
\qquad\xrightarrow[\ \mu=0\ ]{}\qquad \delta_t^\star=\frac{4\gamma}{8\pi_t-\sigma^2},$$
with feasibility $\delta_t\in[2|\mu_t|,\,4-2|\mu_t|]$ and profitability gate $\pi_t>\sigma^2/8$.

**Required inputs.** $\sigma$ (std of the pool marginal rate, e.g. daily from 1-minute log returns
scaled by $\sqrt{1440}$); pool fee rate $\pi_t$ (daily fee income ÷ pool size $2\kappa Z_t^{1/2}$);
concentration-cost $\gamma$ from the regression $\delta^2\hat p_{\delta,m}=4\pi m\delta-\gamma m$;
drift $\mu_t$ (optional predictive signal); rebalancing cost $\zeta$.

**Parameters & defaults.** $\gamma=5\times10^{-7}$ used out-of-sample; regression estimates
$\gamma=2.51\times10^{-7}$ ($m=1$ min) and $1.27\times10^{-6}$ ($m=5$ min); discretisation
$t_{i+1}-t_i=1$ minute; in-sample window $[t_i-1\,\text{day},t_i]$, out-of-sample $[t_i,t_{i+1}]$.

**Observed effect sizes.** Optimal strategy one-minute total $+0.0047\%$ (SD 0.02%) versus market
$-0.00067\%$; position value $-0.015\%$ (0.0951%) offset by fees $+0.0197\%$ (0.005%); $\pi$ and $Z$
returns weakly correlated ($-2.1\%$ at 1 min, $-10.9\%$ at 1 day) (arXiv:2309.08431).

**Failure modes.** The model assumes continuous repositioning while Ethereum blocks land every ~13 s;
gas is flat here but stochastic in practice (\$84.8/operation ⇒ need $>1.8\times10^5$ USD initial
wealth); constant volatility; no market impact of provision on taking flow; the drift asymmetry is a
fixed functional form. $\pi$ and $\gamma$ both require on-chain data (see §3).

### 2.5 Optimal exit time for the LP (HJB quasi-variational inequality)
**Purpose.** Decide *when* to withdraw liquidity before a fixed horizon so that collected fees minus
realised IL is maximised, given that arbitrage realignment is not instantaneous.

**Formula.** External mid $S_t=S_0+\sigma W_t$; CFM $xy=c^2$ with internal rate $Z_t=X_t/Y_t=c/Y_t^2$;
trade intensities $\bar\lambda^a(y,S)=\max(a_0,a_1+a_2(S-c/y^2))$,
$\bar\lambda^b(y,S)=\max(a_0,a_1+a_2(c/y^2-S))$. With $\varphi_c(y)=c/y$, the per-trade P&L terms are
$$\beta^b(y,S)=\varphi_c(y+\xi)-\varphi_c(y)+\xi S+r(y),\qquad
\beta^a(y,S)=\varphi_c(y-\xi)-\varphi_c(y)-\xi S+r(y),$$
$$IL_t=-\big[(X_t-X_0)+S_t(Y_t-Y_0)\big],\qquad
v(t,y,S)=\sup_{\tau\in\mathcal T_{t,T}}\mathbb E\!\left[\int_t^\tau\!\big(\beta^b\lambda^b\mathbf 1
+\beta^a\lambda^a\mathbf 1\big)ds\right].$$
The value function solves the HJB QVI $\min\{-\partial_tv-\tfrac{\sigma^2}{2}\partial_{SS}v-\mathcal Lv,\;v\}=0$
on $[0,T)\times Q\times\mathbb R$ with $v(T,\cdot)=0$; the LP exits where $v=0$. Numerics: Euler
operator-splitting and a Longstaff–Schwartz regression (risk-averse variant uses exponential utility
with $\psi$, and $\psi\to0$ recovers the risk-neutral QVI).

**Required inputs.** Per-trade pool state $(Y_t,c)$, external mid $S_t$, trade size $\xi$, intensity
parameters $(a_0,a_1,a_2)$, fee function $r(\cdot)$, volatility $\sigma$, horizon $T$.

**Parameters & defaults.** Constant trade size $\xi$; $r$ with linear growth (linear $r(y)$ is a good
approximation to the optimal fee structure); 10,000 simulation paths per cell; normalised
$\sigma=1$, unstressed $r\sim10^4$.

**Observed effect sizes.** Concave $(\sigma\mapsto \mathbb E[R],\mathbb E[IL])$: $(\sigma,2\sigma,3\sigma)
\Rightarrow$ exit (1.00, 0.51, 0.01), fees (316,222; 273,003; 3,599), IL (112,635; 202,999; 2,449).
Noise scaling $a_1\times5$: fees 296,407→441,710, IL flat ~112,600. Arbitrage scaling $a_2\times5$:
fees 118,244→878,099, IL 83,734→113,789. Fee multiplier $r/2$: mean exit 0.96 versus 1.00 at $r$
(arXiv:2509.06510).

**Failure modes.** Representative-agent assumption (LP owns all pool liquidity); exit race ignores
priority fees (arbitrageurs may need to outbid the LP); bounds $\underline Y,\overline Y$ are risk
limits; the LP's own withdrawal is assumed not to move the pool.

### 2.6 Protocol-fee take-rate event study (matched-overlap DiD)
**Purpose.** Estimate the causal LP-supply response $K_L$ to a fee change that moves the LP take-rate
but *not* trader-facing execution prices — and be explicit about what public on-chain data cannot
identify.

**Formula.** With LP welfare $W=\mathrm{FeeRev}^{arb}+\mathrm{FeeRev}^{fund}-\mathrm{LVR}$, LP take-rate
$\rho_i=1-\kappa_i$, tier intensity $\kappa_i\in\{1/4,1/6\}$, and a pool-specific activation week
$t_{0i}$, the event study is
$$Y_{itm}=\alpha_{im}+\delta_{tm}+\sum_{k\ne-1}\beta^m_k\,\mathbf 1[t-t_{0i}=k]\,D_i
+\mathbf 1[t=\tau]X_{i0}'\theta^m_\tau+\varepsilon^m_{it},$$
and the finite-horizon matched-overlap ATT is
$\Delta^m_h=\mathbb E[Y^m_{i,t_{0i}+h}(\bar\rho^{sw})-Y^m_{i,t_{0i}+h}(\bar\rho^{no})\mid D_i=1,i\in M]$.
Matching: exact on fee tier and pair class, nearest neighbours ($k\le3$, caliper 0.5 log-points) on
the selection variable itself (pre-period realised fee revenue $S_i$); controls restricted to low
spillover exposure via a pre-treatment exposure matrix $E_i=\sum_j D_jA_{ij}$.

**Required inputs.** On-chain `SetFeeProtocol` activation events (treatment $D_i$, intensity
$\kappa_i$, event time $t_{0i}$); normalised `Swap`/`Mint`/`Burn`/`Collect` logs; time-weighted active
liquidity and local depth in $\pm1/\pm2/\pm5\%$ bands; LP participation/composition; at least one
competitor venue.

**Parameters & defaults.** Primary window $\pm8$ weeks (robustness $\pm6,\pm12$); reference bin
$k=-1$; caliper 0.5 (robustness 0.25/1.0); panel 2024-01 to 2026-06; inference clustered at token-pair
level with restricted wild cluster bootstrap; Honest-DiD bounds, placebo activation dates, entropy
balancing, and a channel-admissibility audit.

**Observed effect sizes.** 2,638 treated v3 pools → 868 with usable pre-period panel → 786 matched
(90.6%) → 779 treated + 303 controls, 17,598 pool-weeks, 1,013 clusters. Post-period active liquidity
$[-1.11,0.33]$ asinh (multiplicative ≈$[0.33,1.39]$, 80% MDE ≈1.03); $\pm2\%$ depth $[-2.02,1.27]$
(≈$[0.13,3.58]$, MDE ≈2.35); LP participation MDEs ≈0.1 asinh (±10%). Token-1 volume and native LP
fee income fail the parallel-trends gate and stay descriptive (arXiv:2607.08525).

**Failure modes.** Observational, not randomised: relies on dynamic parallel trends in untreated
increments. Non-detection ≠ zero — report the MDE. The coverage rule selects on pre-period fee revenue
(SMD only narrowed 1.19→0.84 after matching), so level balance is not achieved and identification rests
on conditional trends. Post-treatment volume/fee/depth must never enter the main specification as
controls (they absorb the response). Proposal-to-activation weeks are anticipation, not clean pre-period.

## Data Requirements

Provider rows are real entries in `strategies/endpoints.json` (the `Probe status` column is the
catalog's exact `code`); **gap** means no current provider serves the input. `moomoo` rows are served
by the local OpenD SDK gateway (`detail: "local gateway (SDK)"`), not by live-probed HTTP.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Spot price series for the IL/LVH ratio $p_t/p_0$ (daily) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Spot price series (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily aggregate bars (tertiary) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Daily EOD bars (quaternary) | `https://api.stockdata.org/v1/data/eod` | `core_stock_apis` | stockdata | ok |
| Intraday bars for realised $\sigma$ of the marginal rate | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday K-line (local gateway) | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway |
| Top-of-book snapshot (external mid $S_t$) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway |
| Tradable symbol universe / tick sizes | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Risk-free / discount rate $r$ for claim valuation | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Risk-free series (macro alternative) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Listed option prices for static IL replication (index) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | ok |
| Listed option chains (equity, local gateway) | `moomoo://get_option_chain` | `options_data` | moomoo | gateway |
| **On-chain AMM pool reserves / internal rate $Z_t$** | — | — | — | **gap** |
| **Active liquidity and local depth by tick band ($\pm1/\pm2/\pm5\%$)** | — | — | — | **gap** |
| **`Swap`/`Mint`/`Burn`/`Collect` event logs (LT flow, LP operations)** | — | — | — | **gap** |
| **Protocol-fee activation events (`SetFeeProtocol`)** | — | — | — | **gap** |
| **Pool fee rate $\pi$ / realised fee revenue / TVL** | — | — | — | **gap** |
| **LP position-level tick ranges (deposit/withdraw)** | — | — | — | **gap** |
| **Crypto (Deribit) BTC/ETH option chains for IL hedging** | — | — | — | **gap** |
| **Gas fees / priority fees** | — | — | — | **gap** |

**What the gap costs, quantified.** The pool-state layer is not a nicety — it is the whole sample.
arXiv:2309.08431 needed 2,654,347 LT instructions and 68,434 LP instructions over 473 days in a single
pool (≈4,720 LT/day, ≈471 LP ops/day) and derived its 331,858 LP operations from position-level
deposit/withdraw matching; without `Swap`/`Mint`/`Burn`/`Collect` logs and tick-band liquidity there is
no way to compute $\pi$, the concentration-cost $\gamma$, or the depth-weighted fee share
$\tilde\kappa/\kappa$. arXiv:2501.07828 needed 700 days × 9 pools (~16% of v3 TVL) with FIFO-matched
deposit/withdrawal events; without them the duration/range return table cannot be reproduced.
arXiv:2509.06510 needs per-trade pool state $(Y_t,c)$ at trade granularity plus the external mid — the
mid is available from bars, but the reserve grid is gap-bound. arXiv:2607.08525 needed a 2024-01–2026-06
panel spanning 2,638 treated pools (→779 treated + 303 controls, 17,598 pool-weeks, 1,013 clusters) plus
at least one competitor venue; without `SetFeeProtocol` events the treatment vector $D_i$, intensity
$\kappa_i$ and event time $t_{0i}$ do not exist, and the design is undefined. arXiv:2407.05146's static
replication needs a listed option grid at the position's strikes — available for SPX via the CBOE row
and equity chains via the `moomoo` gateway, but the crypto (Deribit) BTC/ETH chains that actually
correspond to AMM pairs are a gap. Conversely arXiv:2203.11352 needs nothing but price ratios, so its
formula and the §2.2 LVH curve are the only parts of this category that run on the present data layer.

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Freeze the design before looking at outcomes.** arXiv:2607.08525 reconstructs treatment, event
  time, unit roles and outcomes from raw logs into a *frozen, hash-checked panel* before any estimate
  (assumption A1, replayability). It also separates the economic object (LP welfare $W$) from the
  statistical object (reconstructed outcomes $Y$), and refuses to read $W$ causally because
  fee-revenue attribution, LVR and trader types are latent.
- **Event time ≠ governance date.** The switch is dated 2025-12-28 by convention but the on-chain
  `SetFeeProtocol` burst is 2025-12-27 20:51 UTC; the paper uses the pool-specific block timestamp.
  Mixing the two mis-times every event-study bin.
- **Anticipation contaminates the pre-period.** The proposal was public from November 2025; the clean
  pre-period must end at the proposal date, and proposal-to-activation weeks get their own bins and
  are never pooled into the pre-period (arXiv:2607.08525).
- **Pre-trends are the acceptance gate, not a diagnostic to be tuned away.** Token-1 volume and
  native LP fee income fail the parallel-trends gate and are reported descriptively — not re-specified
  until they pass (arXiv:2607.08525). Robustness must include Honest-DiD bounds, placebo activation
  dates, entropy balancing, and window/caliper sweeps; none of these may be used to *select* the
  specification.
- **Report the minimum detectable effect, not just the interval.** Active liquidity's 80% MDE is
  ≈1.03 asinh (multiplicative ≈[0.33,1.39]); calling that "no effect" without the MDE overstates the
  evidence (arXiv:2607.08525).
- **Definition discipline for IL.** Funded, borrowed and relative IL are three different numbers
  (arXiv:2407.05146); arXiv:2203.11352 shows the parameter count itself depends on ERLI (2n vs 2(n−1)
  vs n−1). Relative IL has no clean P&L interpretation and should not be used to size a hedge.
- **Metric choice: LVH vs LVR.** LVH compares to buy-and-hold (practical, what an LP actually faces)
  but mixes market risk with adverse selection; LVR isolates adverse selection but requires
  replicating *every* LP transaction and assumes continuous rebalancing (arXiv:2501.07828).
- **Sample selection and survivorship.** arXiv:2501.07828 measures only closed positions, so LPs
  waiting for reversion (unrealised IL) are excluded; arXiv:2607.08525's coverage rule is selection on
  observables at the list margin, and matching only narrowed the pre-period fee-revenue SMD from 1.19
  to 0.84.
- **Cost assumptions dominate the sign.** arXiv:2309.08431 shows the optimal strategy is positive
  *before* gas and requires initial wealth $>1.8\times10^5$ USD after \$84.8/operation; arXiv:2501.07828
  explicitly neglects gas, which flatters small positions; the pool execution cost is
  $yZ_t^{3/2}/\kappa$ per unit traded. Any IL strategy reported without gas and rebalancing cost is
  optimistic.
- **Regime dependence.** The 700-day panel spans the FTX collapse (Nov 2022) and the Ethereum Merge
  (Sep 2022); the ETH/USDC study spans 2021-05 to 2022-08, a single violent regime. Report the sample
  window alongside any effect size.
- **Model-assumption audit.** Continuous repositioning versus ~13 s Ethereum blocks; flat gas versus
  stochastic gas; constant volatility; and — critically — no market impact of provision on taking
  flow (arXiv:2309.08431, §6). Simulator-based fee-controller evaluations that freeze liquidity supply
  assume away exactly the $K_L$ margin arXiv:2607.08525 estimates.
- **Out-of-sample discipline.** arXiv:2309.08431 estimates $\sigma,\pi,\gamma$ on the trailing day and
  scores on the next minute, rolling forward over 331,858 operations; the two numerical schemes for the
  exit problem (Euler splitting vs Longstaff–Schwartz) should be cross-checked against each other
  (arXiv:2509.06510). Option-replication weights must be evaluated on strikes *off* the grid, where the
  residual is nonzero (arXiv:2407.05146).

## Recommended Workflow

Ordered by value-per-effort against what the data layer can fetch today. Items 1–5 are buildable now;
items 6–8 are blocked on an on-chain feed and should be built as simulator/analysis skeletons.

1. **IL / LVH calculator on price bars.** *What:* implement §2.2 — $LVH=2\sqrt d/(1+d)-1$ for v2 and
   the piecewise v3 value from the holdings formulas, for any pair and any range $[p_a,p_b]$.
   *Data:* eodhd `eod` / tiingo `prices` / twelvedata `time_series` (spot ratio) plus
   `exchange_symbols` for tick/range conventions. *Passing:* reproduces the v2 closed form to $<10^{-6}$
   and reports the price ratio at which $IL$ reaches $-1\%$, $-5\%$, $-10\%$. *Effort:* S.
2. **IL break-even / fee-adequacy screen.** *What:* the §2.4 profitability gate $\pi>\sigma^2/8$ and
   the $\delta^\star=4\gamma/(8\pi-\sigma^2)$ spread rule, with $\gamma,\pi$ supplied as scenario
   inputs. *Data:* intraday bars for $\sigma$; $\pi,\gamma$ as user parameters until an on-chain feed
   exists. *Passing:* flags a pool/range as non-viable when $\pi\le\sigma^2/8$, and returns a strictly
   wider range as $\sigma$ rises. *Effort:* S.
3. **IL-protection static replication weights.** *What:* §2.3 second-difference weights over a listed
   strike grid, with the residual reported off-grid. *Data:* `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json`
   (index surface) or `moomoo://get_option_chain` (equity chains). *Passing:* replication residual zero
   at grid strikes and ≤ a few bps off-grid, matching the paper's 2.5 bps worked example. *Effort:* M.
4. **BSM / MGF valuation of the IL protection claim.** *What:* §2.3 — closed-form v2 values plus the
   five-transform Fourier valuation for v3 (vanilla, digital, square-root, capped payoffs).
   *Data:* option grid + `risk_free_curve` (or `fred` macro series) for $r$. *Passing:* v2 closed forms
   reproduced exactly; v3 value monotone in range width with narrower ranges more expensive. *Effort:* M.
5. **LP exit-boundary prototype (synthetic pool).** *What:* §2.5 HJB QVI solved by Longstaff–Schwartz
   on a synthetic constant-product pool with external mid $S_t$ from bars. *Data:* bars for $S_t$;
   synthetic reserves until a real feed exists. *Passing:* the exit boundary contracts as $\sigma$
   rises and the LP exits early when $|S-c/Y^2|$ is large. *Effort:* M.
6. **Protocol-fee event-study harness (frozen panel).** *What:* §2.6 — build the reconstruction rules,
   treatment vector, matching on pre-period fee revenue, and the event-study estimator with the
   pre-trend gate and MDE reporting, so it runs the moment logs are ingested. *Data:* none live; the
   skeleton is self-contained. *Passing:* the pipeline emits a pre-trend $p$-value and an MDE per
   outcome, and labels any failing outcome descriptive. *Effort:* M.
7. **On-chain ingestion path for AMM pools.** *What:* register a new data category (e.g.
   `dex_pool_state` / `dex_event_logs`) in `finrobot/engine/data/categories.py` and ingest Uniswap v3
   `Swap`/`Mint`/`Burn`/`Collect` and `SetFeeProtocol` events plus tick-band liquidity.
   *Data:* the on-chain feed itself (subgraph or node logs). *Passing:* reconstructs $\pi$, $\gamma$
   and the §2.6 panel for one pool/venue. *Effort:* L.
8. **Crypto option-chain feed for IL hedging.** *What:* add Deribit BTC/ETH option quotes so §2.3 can
   be applied to actual AMM pairs rather than equity indices. *Data:* the crypto options venue.
   *Passing:* a replication portfolio with ≤ a few bps residual on a BTC/ETH range. *Effort:* M–L.

## Output Format

### IL / LVH Curve
| Price ratio p_t/p_0 | v2 IL = 2*sqrt(d)/(1+d)-1 | v3 LVH (range [p_a, p_b]) | Ratio where IL = -1% / -5% / -10% |
|---------------------|---------------------------|--------------------------|------------------------------------|
| ... | ... | ... | ... |

### Fee-Adequacy and Range Verdict
| Pool fee rate pi | Realised sigma (1-min, sqrt(1440)-scaled) | pi vs sigma^2/8 gate | Optimal spread delta* = 4*gamma/(8*pi - sigma^2) | Viable |
|------------------|-------------------------------------------|----------------------|--------------------------------------------------|--------|
| ... | ... | ... | ... | ... |
Verdict: flag non-viable when pi <= sigma^2/8; as sigma rises the optimal
range must widen. State whether the range is narrow (<0.0467) or wide
(>0.2756) and the sample window, since effects are regime-dependent.

### IL-Protection Replication Weights
| Strike k_n | Second-difference weight w_n | Residual at grid strike | Residual off-grid (bps) | v2 funded/borrowed IL check |
|------------|------------------------------|-------------------------|-------------------------|-----------------------------|
| ... | ... | 0 | ... | sqrt(p_t/p_0)-1 vs -0.5*(sqrt(p_t/p_0)-1)^2 |
State the IL definition used (funded, borrowed, or relative) and report the
off-grid residual, which is nonzero.

## References

| arXiv id | Title | Year |
|---|---|---|
| 2607.08525v1 | Causal Effects of Protocol-Fee Changes on Liquidity Provision in Automated Market Makers | 2026 |
| 2509.06510v2 | Optimal Exit Time for Liquidity Providers in Automated Market Makers | 2025 |
| 2501.07828v1 | Automated Market Makers: Toward More Profitable Liquidity Provisioning Strategies | 2025 |
| 2407.05146v1 | Unified Approach for Hedging Impermanent Loss of Liquidity Provision | 2024 |
| 2203.11352v1 | A General Framework for Impermanent Loss in Automated Market Makers | 2022 |
| 2309.08431v3 | Decentralised Finance and Automated Market Making: Predictable Loss and Optimal Liquidity Provision | 2023 |
