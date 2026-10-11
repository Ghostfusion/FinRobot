---
id: prediction-markets-betting
name: Prediction Market Contract Calibration
version: 1.0.0
author: finrobot
domain: prediction-markets
description: 'Prediction-market event contracts: ingest Polymarket metadata into typed 0/1 tables, calibrate threshold probabilities against option-implied Φ(d2), and stress leveraged payoffs and settlement finality. Use when analyzing prediction markets, event contracts, or betting odds calibration.'
triggers:
- prediction market
- polymarket
- event contract
- kalshi
- betting market
- probability calibration
- binary contract
- settlement finality
- option-implied probability
- event market
- threshold contract
requires_data:
- input: Event-market metadata, current YES/NO quotes, volume
  provider: polymarket
  category: prediction_markets
  status: ok
- input: Event-contract category listing (local gateway)
  provider: moomoo
  category: prediction_markets
  status: gateway
- input: Macro/event outcome series (CPI, policy rates)
  provider: fred
  category: macro_data
  status: ok
- input: Event evidence (news around a source programme)
  provider: eodhd
  category: news_data
  status: ok
- input: Scheduled economic releases
  provider: moomoo
  category: economic_calendar
  status: gateway
- input: Earnings date/outcome for equity-event contracts
  provider: benzinga
  category: earnings_calendar
  status: ok
- input: Listed equity/ETF option chain (benchmark leg)
  provider: moomoo
  category: options_data
  status: gateway
- input: Index option quotes/surface (benchmark leg)
  provider: cboe
  category: options_surface
  status: ok
- input: Underlying options overview / expected move
  provider: moomoo
  category: expected_move
  status: gateway
- input: Risk-free discount curve for `e^{-r\tau}`
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Daily OHLCV of an underlying (spot reference)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Intraday bars of an underlying (`interval=1min`)
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: '**Crypto spot reference (BTC/ETH hourly bars)**'
  provider: ''
  category: ''
  status: gap
- input: '**Listed crypto option chain (Binance/Deribit, hourly bid–ask)**'
  provider: ''
  category: ''
  status: gap
- input: '**Event-contract L2 order book / tick event feed**'
  provider: ''
  category: ''
  status: gap
- input: '**Authoritative on-chain trade tape with aggressor sign**'
  provider: ''
  category: ''
  status: gap
- input: '**On-chain protocol events (Preparation / Resolution / PayoutRedemption)**'
  provider: ''
  category: ''
  status: gap
- input: '**Kalshi REST + WebSocket market / MVE API**'
  provider: ''
  category: ''
  status: gap
- input: '**Versioned venue rule objects and official source-release archives**'
  provider: ''
  category: ''
  status: gap
- input: '**Per-market depth time series and maker-level inventory**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Prediction Market Contract Calibration

You are an expert prediction-market and event-contract researcher specializing in binary-claim pricing, probability calibration and settlement mechanics. You consume Polymarket gamma metadata, event-contract category listings, option chains and surfaces, macro/event calendars and, where present, on-chain fill and protocol logs, and interpret them into typed contract tables, option-implied Φ(d2) benchmark wedges with HAC and block-bootstrap intervals, and terminal-payoff leverage statements — never fabricating quotes, paper results, significance levels, or an on-chain aggressor sign that was not actually computed.

> Source: FinRobot strategies corpus review — `strategies/qfin-tr/prediction-markets-betting.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **Trade direction inferred from Polymarket's own off-chain feed is noise-dominated, and the error
  flips whole measures.** Across a pre-registered 600-market panel, feed sign matches on-chain ground
  truth on `~59%` of matched buckets: panel mean `0.615` (market-clustered bootstrap 95% CI
  `[0.579, 0.653]`), volume-weighted `0.592` (CI `[0.542, 0.659]`), median `0.591` (IQR
  `[0.526, 0.681]`) — against a `50%` chance baseline and `~81%` for Lee–Ready on Nasdaq. The feed's
  `change_side` marks which book side moved, not who initiated. Swapping feed for on-chain direction,
  effective half-spread changes sign on `67%` of markets (`16/24`, Wilson CI `[0.47, 0.82]`) in window
  A and `50%` (`15/30`) in non-overlapping window B; Kyle's `\lambda` on `60%` (`15/25`, CI
  `[0.41, 0.77]`) and `43%` (`13/30`); volume weighting *raises* the spread flip rate to `86%` (CI
  `[0.32, 0.99]`). Feed inference also under-counts trades by a median factor `0.23` (range
  `0.004`–`3.62`) with no correctable scaling (arXiv:2604.24366).
- **A longshot quoted-spread premium, an order of magnitude wider than the racetrack literature.** By
  mid-price decile, median quoted half-spread is `~400` bps in `[0.4, 0.6]` and `650`–`900` bps in the
  lowest decile (decile 0 median `1,818` bps, p75 `4,000`; decile 9 median `53.5` bps), versus a few
  percent of stake on IEM/TradeSports (arXiv:2604.24366).
- **Depth is layered, not top-heavy, and its cross-section is not about time-to-close.** Over 547
  markets with non-null depth, level 1 holds a median `0.136` of cumulative top-10 depth vs a `0.10`
  uniform null, flat at `~0.08` from `L_4` to `L_10`; median KL divergence from uniform is `0.087`
  (IQR `[0.024,0.474]`), only `9%` of markets are strongly top-heavy (`L_1>0.5`) and `57%` sit within
  a factor two of uniform. Log depth on log seconds-to-close has slope `+0.818` (HC3 SE `0.113`,
  `R^2=0.129`, `n=322`) bivariately but `+0.008` (SE `0.102`, `t=0.08`, `R^2=0.570`, `n=313`) once log
  duration (`+0.222`, SE `0.073`), log `p(1-p)` (`-1.02`, SE `0.180`) and log volume (`+0.41`, SE
  `0.046`) enter (arXiv:2604.24366).
- **Maker liquidity is decentralised; wash is low under a direct-detection floor.** Volume-weighted
  maker HHI median `0.031` (`~32` effective makers), p90 `0.119` (`~8`), max `0.40` (`~3`), over 600
  markets and 6.4M trades. Self-counterparty wash share median `0.97%`, p90 `4.5%`, p99 `10.6%`, max
  `22.2%` — a *lower bound*, versus Cong et al.'s `25–70%` on unregulated token exchanges, which the
  paper rejects as a different incentive environment (arXiv:2604.24366).
- **Prediction-market prices sit systematically above option-implied risk-neutral values, and the wedge
  is structural.** The Sep-2023 `BTC > $27,000` contract vs Binance `BTC-230929-27000-C`: mean gap
  `\bar D=0.0558` (`s_D=0.1264`, `t=6.46`, `p=6.9\times10^{-10}`, HAC 95% CI `[0.0228,0.089]`) over
  `214` hourly observations; pooled over three Binance-compatible thresholds `0.0633` over `287` obs
  (`t=8.24`, `p=6.3\times10^{-15}`). Persistent but mean-reverting: AR(1) `\hat\varphi=0.849\pm0.051`,
  half-life `4.2` h, ADF `-3.69` (`p=0.004`); median friction `0.0427` vs mean benchmark SE `0.0458`,
  `41.1%` of points outside the friction-adjusted band. It is not outlier noise (pooled median
  `0.0642`, 10%-trimmed mean `0.0576`, `68.6%` positive, sign test `p=2.45\times10^{-10}`) and grows
  at low option-implied probability (`-0.398`, SE `0.063`), with benchmark uncertainty (`+0.039`, SE
  `0.019`) and with time to expiry (`+0.0008`/h, `R^2=0.221`). Against Deribit the same contracts show
  `0.1105` pooled over `2,585` obs; Ethereum is mixed (`0.0129` pooled, one March contract `0.1899`)
  (arXiv:2606.19517).
- **Leverage on a binary claim is an account identity, not a path result.** A synthetic long of `x` at
  `p_0` with collateral `xp_0/L` has terminal equity `E_\tau=-xp_0(1-1/L)` whenever the claim pays
  `0`, independent of the pre-resolution mark, so every `L>1` leaves an adverse-outcome shortfall
  (`x=1{,}000`, `p_0=0.60`, `L=5` `\Rightarrow` `C_0=120`, `E_\tau=-480`); basis-only funding
  `f=c(q-I)` vanishes for a *fixed relative* error at the boundaries, and any finite transfer cap
  rules out uniform relative-basis pressure (arXiv:2605.10400).
- **The mechanical replay is negative evidence.** Over a 7-day Polymarket window (2026-04-21→27;
  13.69bn CLOB events, 110,828 market ids, 13,298 usable), boundary-depth median `1.72` (floor `1.5`)
  and terminal-jump median `0.50` (floor `0.10`) pass, but three of five pre-specified E2/E3 tests
  fail: dynamic margin is `~6%` *worse* on `L=5` liquidations (target `-30%`), pooled hypothetical
  drawdown falls `5.1%` (target `-50%`), and a staged halt cuts final-hour liquidations `80.4%` by
  construction while terminal account-shortfall incidence is `2.4%` *worse* (target `-75%`)
  (arXiv:2605.10400).
- **On-demand combinatorial markets explode in tickers while collapsing in breadth, and their two
  public surfaces disagree.** A registered 7-day Kalshi MVE interval yields `7,611,594` unique REST
  tickers (`1.087`M/day, `12.59`/s; hourly `4,640`–`237,403`, median `27,404`) from `5,262,526` event
  keys, `3` collection keys and `83,701` selected-leg primitives (`66,344,938` occurrences, mean
  `8.72`/object). One collection holds `94.82%`; collection HHI `0.9013` (`1.11` effective), primitive
  HHI `0.001388` (`~720` effective); only `35.38%` show positive current volume or open interest and
  24-hour volume is zero on every row. `1,487,330` WebSocket creation-notification tickers intersect
  REST in only `276,177` (`18.57%` of WS-created, `3.63%` of REST); exact endpoint evidence covers
  `7,357,576` objects (`96.66%`) but only `126,806` (`1.67%`) have an exact determination-to-endpoint
  pair (arXiv:2609.17610).
- **A decidability clock can be economically well defined yet retrospectively unobservable.** The
  historical Kalshi frame of `152,694` ordinary tickers, `11,530` event identities and `6,540`
  read-only official requests produced `0` historically eligible events and `0` eligible tickers; in
  the blind 25-market pilot `25/25` identities and blinding checks passed and current rule text was
  recovered `25/25`, but exact-or-bounded historical rule versions were `0/25` and official
  source-release objects `0/25` (arXiv:2609.16642).
- **Resolution is not settlement, and settlement is not realization.** Polymarket's CTF bridge links
  `108,638` conditions (from `185,550` adapter-questions, `76,912` unmatched): `99,283` protocol-final
  by block `90,114,204`, `92,158` with any redemption, `91,817` with positive payout, Kaplan–Meier
  medians `182` s and `200` s. Payout taxonomy: `53,847` `(0,1)`, `45,024` `(1,0)`, `410` fifty-fifty,
  `2` other valid, `9,355` unresolved; only `823` conditions have an interval-qualified terminal
  generation, `91,638` have none in the frozen evidence and `16,129` are censored (arXiv:2609.15373).
- **Off-topic note.** None of the six is off-topic; arXiv:2609.16642 is the weakest fit for a *trading*
  document (no price, clock or latency result) but supplies the only formal account of when a
  contract's outcome becomes determinate — the upstream risk the other five assume away.

## Methods & Formulas

### 2.1 Option-implied binary benchmark and cross-venue wedge
**Purpose.** Price a binary threshold claim off a listed vanilla option with the same underlying,
strike and maturity, and test whether the event market's YES price deviates beyond frictions.

**Formula.**
$$P^{\rm fair}_t=e^{-r\tau_t}\Phi(d_{2,t}),\qquad
d_2=\frac{\ln(S_t/K)+(r-\tfrac12\sigma^2)\tau}{\sigma\sqrt{\tau}},\qquad d_1=d_2+\sigma\sqrt{\tau}$$
$$\hat\sigma_t=\arg\min_\sigma\big|C_{\rm BS}(S_t,K,r,\tau^{(c)}_t,\sigma)-C_{{\rm mkt},t}\big|,\qquad
D_t=P^{\rm poly}_t-P^{\rm fair}_t$$
$$\mathrm{Var}(P^{\rm fair}_t)\approx\frac{g'(\hat\sigma_t)^2\varsigma^2_{C,t}}{V_t^2},\qquad
g'(\sigma)=-e^{-r\tau}\phi(d_2)\frac{d_1}{\sigma},\qquad V_t=S_t\phi(d_1)\sqrt{\tau}$$
$$\mathrm{TF}_t=(f_B+f_P)+\tfrac12(s_{B,t}+s_P),\qquad
\mathrm{CI}_{{\rm adj},t}=P^{\rm fair}_t\pm1.96\,\mathrm{SE}\pm\mathrm{TF}_t,\qquad
\mathrm{Var}(D_t)\approx\mathrm{Var}(P^{\rm fair}_t)+\tfrac{\Delta_P^2}{12}$$
with `D_t=a+\varphi D_{t-1}+u_t`, `h_{1/2}=\ln(0.5)/\ln\varphi`, and
`\varsigma_{C,t}=\max\{(\text{high}_t-\text{low}_t)/2,\ 0.01|C_{{\rm mkt},t}|,\ 10^{-10}\}`.

**Required inputs.** Event YES series (or `1-p` for a NO trade); listed option mid at the same
strike/maturity; spot reference; risk-free rate; relative spreads `s_B,s_P`; fees `f_B,f_P`; tick size
`\Delta_P`.

**Parameters & defaults.** 365-day convention; one-sample `t`-test plus Newey–West HAC CI and circular
block bootstrap (blocks `\lfloor n^{1/3}\rfloor`); hourly alignment (event quote merged backward to
the last quote at or before the option timestamp); near-maturity points excluded for inversion
stability. Backtest entry when `|D_t|>\mathrm{SE}(P^{\rm fair}_t)+\mathrm{TF}_t`, exit on mean
reversion or expiry; hedge `q_0=V^D_{t_0}/V^C_{t_0}`, spot `x_{t_0}=\Delta^D_{t_0}-q_0\Delta^C_{t_0}`,
rebalanced hourly.

**Observed effect sizes.** `\bar D=0.0558`, `t=6.46` (main); `0.0633`, `t=8.24` (pooled); HAC CIs
`[0.023,0.089]` / `[0.033,0.094]`; `41.1%` / `36.2%` outside `\mathrm{CI}_{\rm adj}`; Deribit pooled
`0.1105`. Proxy backtest: 16 trades, gross `1.649`, net `1.113`, win rate `69%`, median hold `3.5` h,
net alpha `0.067` (`t=2.10`, `p=0.053`, HAC CI `[-0.008,0.143]`).

**Failure modes.** Black–Scholes is not a description of BTC dynamics; a stochastic-volatility
correction widens the gap, so BS is conservative for the sign only, not a bound. Contract mapping is
close but not exact (oracle feed vs exchange convention). Alignment lag injects spurious wedge and a
coarse grid sets a hard noise floor via `\Delta_P^2/12` — do not run the test below it.

### 2.2 Prediction-market spread and depth-shape stylized facts
**Purpose.** Characterise the cost of holding an informational position and the liquidity shape
without an on-chain join.

**Formula.** Quoted half-spread in bps of mid,
$$\mathrm{hs}^{\rm q}_t=10^4\frac{\text{ask}_t-\text{bid}_t}{2\,\text{mid}_t},\qquad
\text{mid}_t=\tfrac12(\text{bid}_t+\text{ask}_t)$$
Depth shape `w_k=\bar d_k/\sum_{j\le K}\bar d_j`,
`\bar d_k=\overline{(\text{cum}_k-\text{cum}_{k-1})_{\rm bid+ask}}`, uniform null `w_k=1/K`,
top-of-book null `w_1=1`, and `\mathrm{KL}(w\,\|\,\text{unif})=\sum_k w_k\ln(Kw_k)\in[0,\ln K]`.
Effective makers from `H_m=\sum_a(v_a/\sum_b v_b)^2`, `\hat n_{\rm eff}=1/H_m`.

**Required inputs.** L2 book snapshots/deltas (`bid`, `ask`, per-level sizes) at tick resolution;
resolution horizon; on-chain maker addresses and volume (HHI); category labels.

**Parameters & defaults.** `K=10`; mid-price deciles; eligibility floor `\ge100` on-chain trades;
sample step `60` s with `{1,10,60,300}` s sensitivity; block-clock test `\pm100` ms around a `2000` ms
grid.

**Observed effect sizes.** Half-spread `400` bps central, `650`–`900` bps lowest decile; `L_1` share
`0.136`; median KL `0.087`; HHI `0.031`; block alignment `0.102`; ingestion latency p50 `41.5` ms
(p25–p75 `39`–`47`, p90 `166`, p99 `6,108`).

**Failure modes.** The longshot premium is *quoted*, not decomposed — separating inventory risk from
misperception needs maker inventory and time-on-book, absent here. Millions of events per market make
exact null tests reject mechanically (`58.5%`, 351/600, at `\alpha=0.05`). The latency statistic is
collector-side; never call it exchange latency.

### 2.3 On-chain trade-direction gate and sign-flip audit
**Purpose.** Decide whether a direction-dependent measure on an event venue is admissible, and how far
it moves if the sign source is wrong.

**Formula.**
$$a=\frac{\#\{t:\mathrm{sign}^{\rm feed}_t=\mathrm{sign}^{\rm chain}_t\}}{\#\{t\}},\qquad
\mathrm{flip}(M)=\frac{\#\{m:\mathrm{sgn}\,M^{\rm feed}_m\neq\mathrm{sgn}\,M^{\rm chain}_m\}}{\#\{m\}}$$
Ground truth for a conditional-token exchange: aggressor `+1` when `takerAssetId=0` (taker posted
USDC, so buyer), `-1` when `makerAssetId=0`. Spread split `S^{1}_{\rm eff/2}=c+\varphi` with `c` the
realized half-spread at a 60-second lag.

**Required inputs.** Feed events (`change_price`, `change_side`, `change_size`, `book_snapshot`);
on-chain fills with both counterparties and asset ids; a `(condition_id, yes_token_id, no_token_id)`
bridge from CLOB REST (not the metadata API); matching at 5-second and exact-price granularity.

**Parameters & defaults.** Four disjoint 7-day windows; `\ge10` matched buckets per cell;
market-clustered bootstrap CIs; `128`-block roundtrip window for the wash filter; scrape blocks at
depth `\ge256`.

**Observed effect sizes.** `a=0.592` (volume-weighted) / `0.615` (panel mean); spread flips
`67%`/`50%`; `\lambda` flips `60%`/`43%`; count ratio median `0.23`. After injecting on-chain trades,
the top-100 median effective half-spread is essentially zero (`-0.0003` pp), transitory `0.00001`,
adverse selection `0.0`; the split converges on 97/100.

**Failure modes.** The flip rate is itself window-specific, so one window is not evidence, and volume
weighting can strengthen or weaken the headline. The on-chain record still contains MEV flow and the
60/40 seller/buyer asymmetry is unattributable without mempool capture. Only the top stratum has
enough signed trades.

### 2.4 Terminal payoff identity for a leveraged binary overlay
**Purpose.** Decide — before writing a margin engine — whether a synthetic leveraged position on a
0/1 claim can survive to resolution, and decompose margin into the three jobs it must do.

**Formula.** With `Y\in\{0,1\}`, size `x`, entry `p_0`, leverage `L`, collateral `C_0=xp_0/L`:
$$\Pi_\tau=x(Y-p_0),\qquad E_\tau=C_0+x(Y-p_0),\qquad S_\tau=[-E_\tau]^+$$
Mark-to-market telescopes: `E_{\tau^-}+x(Y-q_{\tau^-})=C_0+x(Y-p_0)=E_\tau`. Under open exposure with
no top-up, close, deleverage or conversion,
$$E_\tau=-xp_0\Big(1-\tfrac1L\Big),\qquad S_\tau=xp_0\Big(1-\tfrac1L\Big)\ \ (\text{when }Y=0)$$
so `E_\tau<0` for every `L>1`, independent of the mark path; the short side is `x(1-p_0)(1-1/L)` when
`Y=1`. Margin decomposition `M_t=M^{\rm path}_t+M^{\rm terminal}_t+M^{\rm execution}_t`.

**Required inputs.** None for the identity. For the replay: price paths, depth, timestamps, realised
outcomes, a position grid and a leverage grid.

**Parameters & defaults.** `L\in\{1,2,3,5,10\}`; configs `C_0` (static vol margin, basis-only funding,
fixed cap), `C_1` (jump-aware margin + compression), `C_2` (`C_1` + experimental funding + halt);
mechanics `M_0` forced expiry, `M_1` compression, `M_2` compression+funding, `M_3` full staged halt.
Floors: boundary-depth median `\ge1.5`; terminal-jump `\ge0.10`; `\ge30%` liquidation reduction at
`L=5`; `\ge50%` pooled drawdown reduction; `\ge50%` final-hour liquidation cut; `\ge75%` terminal-cut.

**Observed effect sizes.** Boundary-depth `1.72`, terminal-jump `0.50` (pass). Maintenance-path pass
rate falls with `L` (`C_0`: `33.5%\to27.3%`), and `C_2` is *worse* than `C_0` at every `L`. Pooled
drawdown `545.1`M`\to517.1`M (`-5.1%`); shortfall incidence `51.7%`(`M_0`,`L=2`)`\to57.9%`(`M_3`,`L=10`).

**Failure modes.** The replay is `Z_c=g_c(X^{\rm obs})` on *fixed* paths; it does not identify the
endogenous path after traders, arbitrageurs and market makers react, so it cannot support equilibrium
or deployment claims. Account shortfall is not exchange bad debt — that needs the full liquidation and
loss-sharing waterfall. An adverse position *can* be rescued by early liquidation, top-up, physical
conversion or an external backstop; state which channel you rely on.

### 2.5 Economically bounded boundary funding
**Purpose.** Penalise mark–index divergence near `0` and `1` without diverging when the index is a
normalised probability.

**Formula.**
$$f_t=\mathrm{clip}_{[-\bar f_t,\bar f_t]}\!\left(\alpha_t(q_t-I_t)
+\beta_t\mathbf 1_{B_t}\frac{q_t-I_t}{\max\{\epsilon,\min(I_t,1-I_t)\}}\right)$$
Trilemma: no rule with `|f(q,I)|\le\bar f<\infty` satisfies
`|f(q,I)|\ge\kappa|q-I|/\min\{I,1-I\}` for all `q\in[0,1]`, `I\in(0,1)` and fixed `\kappa>0`; and
basis-only `f=c(q-I)` vanishes for fixed relative deviation as `I\to0` or `I\to1`.

**Required inputs.** Reference index `I_t` (composite of midpoint, depth-weighted midpoint and recent
executed prices), mark `q_t`, per-payer equity, collateral limits, boundary indicator `\mathbf 1_{B_t}`.

**Parameters & defaults.** Floor `\epsilon` and cap `\bar f_t` free; optionally require the interval
transfer not to exceed a stated fraction of payer equity. The replay used an *uncapped* correction;
the capped family here is untested.

**Observed effect sizes.** Uncapped funding had no incremental effect (`M_1` and `M_2` final-hour
liquidation incidence identical at every `L`: `0.128%` at `L=2`, `0.115%` at `L=5`), and `M_2`
terminal shortfall is `2.5`–`1.1` pp *worse* than `M_1`.

**Failure modes.** Never present a clamped rule as "restoring boundary control" — the clip is exactly
what destroys uniform relative-basis pressure. Pair it with boundary-specific leverage/listing
restrictions or reduce-only states.

### 2.6 Event-sourced finality clocks and redemption survival
**Purpose.** Separate oracle finality, protocol finality and holder realization, and measure how long
collateral stays unrealized after the payout rule exists.

**Formula.** Canonical order key and clocks:
$$\kappa(e)=(b_e,\ i^{tx}_e,\ i^{\log}_e),\qquad
L^{OP}_c=t_{\rm protocol\text{-}final}-t_{\rm oracle\text{-}final},\quad
L^{PR}_c=t_{\rm first\text{-}redeem}-t_{\rm protocol\text{-}final}$$
Raw integer numerators `Y_c`, `D_c=\sum_k Y_{ck}`, `\pi_c=Y_c/D_c`; and
$$A_c(u)=\sum_{j\in R_c}a_{cj}\mathbf 1[0\le t_{cj}-t_{\rm protocol\text{-}final}\le u],\qquad
\Gamma_c(u)=\frac{A_c(u)}{W_c}$$
`\Gamma_c(u)` is **not identified** from redemption events alone: two balance histories can give the
same `A_c(u)` with different winning entitlement `W_c`. Survival is Kaplan–Meier on
`t_{\rm first\text{-}redeem}` with right-censoring at the fixed snapshot; a zero-payout redemption
ends the *any* endpoint but not the *positive* endpoint.

**Required inputs.** ABI-pinned `ConditionPreparation` / `ConditionResolution` / `PayoutRedemption`
with full ordered topics and exact log indices; a zero-gap block-range coverage ledger; an exact
question→condition bridge (protocol identifiers only); payout numerators and paid collateral.

**Parameters & defaults.** Clock grades `E` (exact), `I` (interval), `S` (snapshot), `Prx` (proxy),
`U` (unmeasured), `X` (conflicting); duration tables use compatible grades only. Nested universes:
cohort → prepared → protocol-final → redemption risk set → positive risk set → value-qualified. Report
medians, quantiles, numbers at risk and restricted means, not means of a zero-inflated heavy tail.

**Observed effect sizes.** `108,638` linked conditions; `99,283` protocol-final; first-any redemption
`92,158` events (`7,125` censored, median `182` s, p25 `52`, p75 `544`); first-positive `91,817`
events (`7,466` censored, median `200` s, p25 `58`, p75 `720`); zero-only `341` (`0.31%`);
resolved-no-redemption `7,125` (`6.56%`); redemption-without-resolution `3,669` (`3.38%`).

**Failure modes.** Same-transaction events have zero wall-clock separation but non-degenerate log
order, so no scalar "resolution timestamp" identifies the path. Provider duplication must not inflate
event counts; a contract-wide count is never a cohort denominator. A missing log index blocks
ordering; a missing transaction index does not. Censoring is an observation boundary, not a state.

### 2.7 Hierarchical breadth audit and contractual decidability clocks
**Purpose.** (a) Measure economic breadth of an on-demand combinatorial venue instead of trusting
ticker counts; (b) clock a contract's determinate outcome *upstream* of venue action.

**Formula.** Breadth: with incidence `B_{pm}=\mathbf 1[p\in\ell(m)]`, degree `d_p=\sum_m B_{pm}`,
`w_p=d_p/\sum_q d_q`,
$$H_P=\sum_p w_p^2,\qquad \widehat{|P|}_{\rm eff}=1/H_P,\qquad
H_c=\sum_c\big(M_c/|M|\big)^2,\qquad R_{\rm dup}=1-\frac{U}{|M|},\qquad
B_A=\frac{1}{\sum_i\tilde a_i^2},\quad Q_A=\frac{B_A}{N_{\rm created}}$$
with `U` the unique exact production signatures and `\tilde a_i=a_i/\sum_j a_j`. Decidability: with
rule graph `\Gamma_i(t)`, evidence `E_i(t)`, settlement set `Y_i`,
`\Psi_i(t)=\Psi_i(\Gamma_i(t),E_i(t))\subseteq Y_i`,
$$t^{\rm first}_{{\rm decide},i}=\inf\{t:|\Psi_i(t)|=1,\ \text{no contract-required future condition}\},\qquad
t^{\rm stable}_{{\rm decide},i}=\inf\{t:\Psi_i(s)=\{y_{i^*}\}\ \forall s\in[t,t_{{\rm final},i}]\}$$
$$L^{FD}_i=t_{{\rm det},i}-t^{\rm first}_{{\rm decide},i},\quad V_i=t^{\rm stable}-t^{\rm first},\quad
Q_i=\frac{t_{{\rm det},i}-\max(t_{{\rm close},i},t^{\rm first}_{{\rm decide},i})}{t_{{\rm det},i}-t_{{\rm close},i}}\in[0,1]$$
Interval evidence gives bounds only: `t_{\rm decide}\in[a_i,b_i]` with exact `t_{\rm det}` yields
`t_{\rm det}-t_{\rm decide}\in[t_{\rm det}-b_i,\ t_{\rm det}-a_i]`; `Q_i` replaces an unbounded ratio.

**Required inputs.** (a) Per object: exact event key, collection key, ordered selected-leg tuple
`(event ticker, market ticker, side)`; creation timestamps; current volume/open interest. (b)
Prospectively archived versioned rule objects, official source-release objects, receipts and revision
graphs; market form, source class, expected horizon.

**Parameters & defaults.** Signatures exclude output ticker, timestamps, title, rules and activity,
with legs sorted as a multiset retaining duplicates; uncertainty by collection-level block bootstrap
(creation-day blocks for burstiness); tickers inside one collection are not independent. Criterion:
**no determination-defined decidability** — venue outcome must not enter the blind clock; grades are
exact/interval, source-found-rule-ambiguous, rule-found-source-unavailable, multiple-plausible,
conflicting, unmeasured; support dispositions set before outcome inspection are full `n^*=500` (needs
`\ge500` markets, `100` clusters, `10` rule/series families, `3` source classes, `80%`
exact-or-bounded support), reduced `150`, exploratory `50`, else no-go.

**Observed effect sizes.** `|M|=7,611,594`, `|P|=83,701`, `H_P=0.001388` (`~720` effective), `H_c=0.9013`
(`1.11` effective collections), `R_{\rm dup}=0`, activity-eligible `35.38%`. Decidability: `0` eligible
events / `0` eligible tickers from `152,694`; pilot rule-version recovery `0/25`, source-release `0/25`,
current rule text `25/25`; shakedown `260,568` s (`72` h `22` m `48` s), `3` source programmes, `25`
markets, `781,266` lifecycle frames, `22` closed lower-bounded reconnect receipts, no unresolved gap.
At `n^*=500` the worst-case 95% margin of error for a proportion is `\approx0.044`.

**Failure modes.** Zero signature collisions do not mean substitutability — the event key is inside the
signature and primitives are heavily reused; creation is endogenous to user requests, and current
snapshot activity has no timestamp. Substituting the venue determination for a missing clock forces the
latency toward zero; `L^{SD}<0` is a conflict class, not a negative delay; `t^{\rm stable}` is a
robustness clock, never a real-time information set.

## Data Requirements

Rows below are exact entries in `strategies/endpoints.json`; "**gap**" means **no current provider can
supply it.**

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Event-market metadata, current YES/NO quotes, volume | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | ok |
| Event-contract category listing (local gateway) | `moomoo://get_event_contract_category` | `prediction_markets` | moomoo | gateway |
| Macro/event outcome series (CPI, policy rates) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Event evidence (news around a source programme) | `https://eodhd.com/api/news` | `news_data` | eodhd | ok |
| Scheduled economic releases | `moomoo://get_economic_calendar` | `economic_calendar` | moomoo | gateway |
| Earnings date/outcome for equity-event contracts | `https://api.benzinga.com/api/v2.1/calendar/earnings` | `earnings_calendar` | benzinga | ok |
| Listed equity/ETF option chain (benchmark leg) | `moomoo://get_option_chain` | `options_data` | moomoo | gateway |
| Index option quotes/surface (benchmark leg) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | ok |
| Underlying options overview / expected move | `moomoo://get_option_underlying_overview` | `expected_move` | moomoo | gateway |
| Risk-free discount curve for `e^{-r\tau}` | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Daily OHLCV of an underlying (spot reference) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Intraday bars of an underlying (`interval=1min`) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| **Crypto spot reference (BTC/ETH hourly bars)** | — | — | — | **gap** |
| **Listed crypto option chain (Binance/Deribit, hourly bid–ask)** | — | — | — | **gap** |
| **Event-contract L2 order book / tick event feed** | — | — | — | **gap** |
| **Authoritative on-chain trade tape with aggressor sign** | — | — | — | **gap** |
| **On-chain protocol events (Preparation / Resolution / PayoutRedemption)** | — | — | — | **gap** |
| **Kalshi REST + WebSocket market / MVE API** | — | — | — | **gap** |
| **Versioned venue rule objects and official source-release archives** | — | — | — | **gap** |
| **Per-market depth time series and maker-level inventory** | — | — | — | **gap** |

**What the `polymarket` row does and does not expose.** `https://gamma-api.polymarket.com/markets`
(probe `ok`) returns market metadata and current quotes — question text, outcome set, end date, last
price, cumulative volume. It does **not** expose order-book state (`price_change` / `book_snapshot`
deltas), per-trade aggressor sign, or on-chain events; and it is itself incomplete for joining, since
Gamma indexed only `34,764` markets while the venue's CLOB REST resolved all `385,198` archive ids
(arXiv:2604.24366). Any direction-dependent measure built on this row alone is invalid by construction
(feed direction agrees with on-chain truth on only `~59%`).

**What the gap costs, quantified.** Polymarket microstructure needed a `30.29`bn-event tick archive
over `52` days (`623.8` GB, `385,198` markets) plus a `28`-day scrape of `255,425,405` `OrderFilled`
events (arXiv:2604.24366); the option benchmark needs hourly listed-option mids and spot on the *same*
strike/maturity (`214` aligned hours main, `287` pooled, `2,585` for Deribit), so with no crypto option
feed no cross-venue wedge is computable (arXiv:2606.19517); the breadth audit needs Kalshi MVE
REST+WS at `7,611,594` objects and `1.087`M/day with hourly bursts to `237,403`, a rate no snapshot
API reconstructs after the fact (arXiv:2609.17610); the finality study needs three ABI-pinned event
families with zero-gap coverage over `108,638` conditions, and a metadata API returns state, never
transition history (arXiv:2609.15373); the decidability programme needed `6,540` official requests and
prospectively frozen rule versions and *still* recovered `0` eligible tickers (arXiv:2609.16642); and
the leverage stress test needed `13.69`bn CLOB events over `168` hours to reach `13,298` usable
markets, since a coarser feed cannot reproduce the boundary half-spreads (`0.0055` low region vs
`0.2700` mid region) the terminal-jump diagnostic depends on (arXiv:2605.10400).

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Never infer aggressor sign from an event venue's own book feed.** `~59%` agreement barely clears
  chance; it flips the sign of effective spread on `67%`/`50%` of markets and of Kyle's `\lambda` on
  `60%`/`43%` across two non-overlapping windows, with no repair for the under-count (median ratio
  `0.23`, range `0.004`–`3.62`) (arXiv:2604.24366). Source direction from on-chain fills or mark the
  measure inadmissible.
- **Estimator fragility is not uniform, and cross-sectional slopes can be pure mediation.** Kyle's
  `\lambda` varies by orders of magnitude across sample steps `{1,10,60,300}` s and is the most fragile
  measure at any step, while Roll is invariant by construction and effective spread / Amihud are stable
  to `~10–20%` at `60` s vs `1` s. A log-depth/log-time-to-close slope of `+0.818` collapses to
  `+0.008` once duration and `p(1-p)` are conditioned on — the omitted variables were the whole effect.
  A `650`–`900` bps longshot half-spread is consistent with inventory risk *and* misperception, so
  report it as quoted, not as a bias, absent maker inventory and time-on-book (arXiv:2604.24366).
- **Huge `n` makes point nulls meaningless, and a collector statistic is not a venue statistic.** An
  exact block-clock null is rejected in `58.5%` of markets while the panel median sits at `0.102` vs a
  `0.10` null — prefer effect sizes and equivalence thresholds — and the `41.5` ms median (p99
  `6,108` ms) is archive-ingestion latency, tight across markets (`39`–`47` ms), not exchange or
  trader latency (arXiv:2604.24366).
- **Declare the benchmark's direction of bias and respect the tick floor.** Black–Scholes is
  conservative for the *sign* of the prediction-market premium because stochastic-vol corrections
  widen the gap — it is not a bound; exact underlying/strike/maturity matching is a prerequisite; and
  the uniform grid adds `\Delta_P^2/12` to `\mathrm{Var}(D_t)`. Report HAC *and* block-bootstrap
  intervals and treat outlier-robust summaries (median, trimmed mean, sign test) as co-primary
  (arXiv:2606.19517).
- **Label marginal significance marginal.** Net alpha `0.067` at `t=2.10`, `p=0.053` with HAC CI
  `[-0.008,0.143]` contains zero, and costs are the swing variable; see
  [`../qfin-st/backtest-methodology.md`](../qfin-st/backtest-methodology.md) for the general
  cost/deflated-Sharpe discipline.
- **Fixed-path replay is not equilibrium identification, and account shortfall is not bad debt.**
  `Z_c=g_c(X^{\rm obs})` keeps prices, depth, open interest and behaviour fixed; adding an adaptive
  simulation *after* seeing the negative result would be an ex-post repair. Likewise, never label a
  clipped funding rule as boundary control — any finite cap breaks uniform relative-basis pressure
  (arXiv:2605.10400).
- **Denominator discipline, censoring and ordered endpoints.** Nest universes explicitly (questions →
  prepared → protocol-final → redemption risk set → positive risk set → value-qualified); never divide
  a lower-stage numerator by a higher-stage denominator, and never let contract-wide counts masquerade
  as cohort rates. A zero-payout redemption ends "any redemption" but not "positive redemption"; take
  medians from Kaplan–Meier on the correct risk set and run the creation-time placebo to show the bias
  from a wrong risk-set origin (arXiv:2609.15373, arXiv:2609.17610).
- **No hindsight in the adjudication clock, and cluster dependence matters.** A determination-defined
  clock forces latency toward zero; forbid it, grade clocks exact/interval, and read `L^{SD}<0` as a
  conflict class. With five registered questions and many strata, bootstrap at the *collection* or
  *source-release* level — millions of related child tickers are pseudoreplicates — and apply
  multiplicity correction or shrinkage. The evidence→outcome extraction is the same problem as
  news-based event detection in
  [`../qfin-st/news-sentiment-nlp.md`](../qfin-st/news-sentiment-nlp.md) (arXiv:2609.16642,
  arXiv:2609.17610).
- **Regime dependence, and ship the negative controls.** The leverage replay is one 7-day, sports-heavy
  window (`51.1%` sports of the usable sample, `77.9%` of the three named classes) excluding the 2024
  election cycle, and the wedge study is three 2023 BTC contracts plus a mixed ETH exercise, so report
  window-specific dispersion rather than a venue-wide parameter (arXiv:2605.10400, arXiv:2606.19517).
  Negative controls are part of the result: shuffled intra-block order, a forbidden title-similarity
  relation that must never enter the canonical mapping, source-observation vs canonical-event counts,
  and the signature-collision count (arXiv:2609.15373, arXiv:2609.17610).

## Recommended Workflow

Ordered by value-per-effort against what the layer can fetch today. Items 1–3 are buildable now.

1. **Prediction-market ingestion and probability panel.** Normalise
   `https://gamma-api.polymarket.com/markets` into a typed event-contract table (question, outcome
   set, end date, current YES/NO, volume), add `moomoo://get_event_contract_category`, and register a
   `prediction_markets` category in `finrobot/engine/data/categories.py`. *Pass:* a reproducible
   snapshot with market count, category mix and end-date distribution, flagged as metadata-level
   quotes only. *Effort:* S.
2. **Option-implied binary benchmark engine** (§2.1): IV inversion, `P^{\rm fair}`, delta-method SE,
   friction band, `D_t` with HAC + block bootstrap, AR(1) half-life. *Data:*
   `moomoo://get_option_chain`, `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json`,
   `moomoo://get_option_underlying_overview`, the Treasury curve row, `https://eodhd.com/api/eod/AAPL`.
   *Pass:* reproduces `\Phi(d_2)` against a hand-checked Black–Scholes call and returns a signed wedge
   whose CI widens with `\Delta_P`. *Risk:* cannot price a crypto-threshold contract until a listed
   crypto option feed exists. *Effort:* M.
3. **Leverage and terminal-payoff stress harness (data-free)** (§2.4): the account identity, the
   `L\in\{1,2,3,5,10\}` grid, the margin decomposition, and a replay interface `g_c(X^{\rm obs})` that
   refuses equilibrium claims. *Pass:* `E_\tau=-xp_0(1-1/L)` reproduced exactly on a synthetic grid,
   and an `M_0` vs `M_3` comparison reporting both the `80.4%` liquidation reduction and the
   *worsened* terminal shortfall so the two channels are never aggregated. *Effort:* S.
4. **On-chain trade-direction gate** (§2.3): refuse direction-dependent measures (effective/realized
   spread, Kyle's `\lambda`, Amihud, Roll, Abdi–Ranaldo, Glosten–Harris) unless a fill-level sign
   source is present, plus the sign-agreement audit. *Data:* on-chain or exchange-signed tape —
   **blocked**; ship the hard fail so no silent bad number is produced. *Pass:* the gate aborts a
   feed-sign-only run and reports the flip rate on any joined sample. *Effort:* S.
5. **Spread/depth stylized-facts monitor** (§2.2): quoted half-spread deciles, per-level depth shares
   with uniform-null KL, maker HHI, block-alignment null, ingestion-latency percentiles. *Data:* the
   Polymarket order-book feed — **blocked**; only quoted deciles are partly derivable from a quote
   snapshot. *Pass:* reproduces `400` bps central / `650`–`900` bps lowest decile and labels latency
   as collector-side. *Effort:* M (after feed).
6. **Finality-clock and redemption-survival estimator** (§2.6): ABI-derived event registry, zero-gap
   coverage ledger, exact question→condition bridge, grades, KM survival, and the entitlement boundary
   that blocks `\Gamma_c(u)` without a balance-complete denominator. *Data:* Polygon CTF logs —
   **blocked**; its interface is worth building because it encodes the
   resolution/redeemability/realization separation. *Pass:* on a fixture log produces `A_c(u)` and
   censored medians and refuses an entitlement-completion rate. *Effort:* M (after feed).
7. **Breadth audit and decidability capture** (§2.7): collection/primitive HHI, effective counts,
   signature duplication and `Q_A`, plus forward capture of versioned rule objects, official releases
   and receipts with blind-packet adjudication and interval-bounded clocks. *Data:* Kalshi MVE
   REST+WS and a rule archive — **blocked**. *Pass:* reproduces `H_c=0.9013`, `H_P=0.001388`,
   `R_{\rm dup}=0` on a fixture population, and a gap-free capture with a documented
   release-object→predicate map (this cannot be backfilled: `0/152,694`). *Effort:* L.

Cross-corpus: option-implied probability generalises the option-pricing machinery in
[`../qfin-st/derivatives-options.md`](../qfin-st/derivatives-options.md); venue microstructure and
spread decomposition follow [`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md);
crypto-venue comparison sits beside [`../qfin-st/crypto-assets.md`](../qfin-st/crypto-assets.md); and
the collateral/tail questions in §2.4–2.5 connect to
[`../qfin-st/risk-management-tails.md`](../qfin-st/risk-management-tails.md).

## Output Format

### Event-Contract Probability Panel
| Market id | Question | Outcome set | End date | YES | NO | Volume | Category | Level |
|-----------|----------|-------------|----------|-----|----|--------|----------|-------|
| ... | ... | ... | ... | ... | ... | ... | ... | metadata-only quote |

### Option-Implied Binary Calibration (Φ(d2))
| Contract | Option leg (K, τ) | P_fair | SE / ΔP floor | Friction band | D_t | HAC 95% CI | AR(1) φ / half-life |
|----------|-------------------|--------|---------------|---------------|-----|------------|---------------------|
| ... | ... | ... | ... | ... | ... | ... | ... |

### Admissibility & Leverage Verdict
- Direction-dependent measures (effective/realized spread, Kyle's λ, Amihud, Roll,
  Glosten–Harris): BLOCKED unless a fill-level sign source is present; report the
  feed-vs-on-chain sign-agreement rate (~59% here) on any joined sample.
- Leverage stress: E_τ = -x·p0·(1 − 1/L) for Y=0 on L ∈ {1,2,3,5,10}; report the M0 vs
  M3 comparison with BOTH the liquidation reduction and the worsened terminal shortfall,
  never aggregated.
- Verdict: state the signed wedge and its interval, whether the tick floor
  (ΔP²/12) is respected, and the calibration recommendation with its failure mode
  (BS sign-only conservatism, window-specific dispersion, or unresolved feed sign).

## References

| arXiv id | Title | Year |
|---|---|---|
| 2604.24366v2 | The Anatomy of a Decentralized Prediction Market: Microstructure Evidence from the Polymarket Order Book | 2026 |
| 2605.10400v2 | Resolution-Aware Perpetual Futures on Binary Prediction Markets: Failure Modes and Mechanical Stress Tests Using Polymarket Data | 2026 |
| 2606.19517v1 | Do Prediction Markets Match Option Prices? Bitcoin Threshold Evidence from Binance and Polymarket | 2026 |
| 2609.15373v1 | Resolution Is Not Settlement, Part II: Protocol Finality and Observed Redemption on Polymarket | 2026 |
| 2609.16642v1 | From Public Evidence to Contractual Outcome: First and Stable Decidability on Kalshi | 2026 |
| 2609.17610v1 | On-Demand Combinatorial Event Markets on Kalshi: Instantiation, Concentration, and Effective Market Breadth | 2026 |
