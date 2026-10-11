# Crypto Exchange Microstructure — learnings from the q-fin.TR corpus

`273` of 2370 corpus papers matched this category (273 with PDFs); this doc is based on a close reading of `6`.

Headline: **crypto venue mechanics are where the data layer is emptiest and the economics most legible.** All
six papers describe how a venue's *rules* — block interval, transaction ordering, pool fee tier, funding
schedule, cost profile — set the profit of an otherwise identical trade. None needs a conventional equity
tape; all need something FinRobot cannot fetch today: mempool arrivals, per-block transaction order, DEX swap
events, 8-hour funding rates, CEX tick prints. What survives today is the *accounting* layer —
execution-risk-aware entry rules, cost ladders, funding-aware thresholds, inclusion thresholds — which is
buildable as deterministic code and testable on bars.

Asset-class questions (crypto reversal, bar sampling, realised-volatility roughness) are handled in
[`../qfin-st/crypto-assets.md`](../qfin-st/crypto-assets.md); price-impact and execution cost in
[`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md); backtest-overfitting
diagnostics in [`../qfin-st/backtest-methodology.md`](../qfin-st/backtest-methodology.md). This doc stays
on venue mechanics: fees, ordering, latency, MEV, funding.

## 1. What the corpus actually offers

**CEX-DEX arbitrage is an execution-risk problem, and the risk is priced.**

- The arbitrageur's DEX leg lands only with probability $\alpha$, and pricing that risk changes behaviour more
  than the spread distribution does. With $\alpha=0.35$, moving Ethereum from 12-second slots to 1-second
  subslots raises the risk-averse agent's transaction count by **535%** (weighted over the 30/5/1 bp ETH-USDC
  pools, range 378–567%) and ETH volume by **203%** (159–243%); the mechanical "attempt everything" agent
  gets **+371%** transactions (356–412%) and **+168%** volume (148–211%). The mechanism is variance, not the
  mean: faster confirmation compresses the window in which a *failed* leg can move against the trader, so
  marginal opportunities clear the hurdle $E[\pi]-\lambda\sqrt{Var[\pi]}\ge\theta$. Gains concentrate in
  low-fee pools — the 1 bp pool supplies 63.2% of arbitrage transactions but only 21.1% of volume. Simulated
  on Binance + Uniswap v3 ETH-USDC at millisecond best bid/ask, July–September 2025 (arXiv:2601.00738).

**Transaction ordering is priced, and the price is measurable.**

- Ethereum's block builders do not preserve time priority: a transaction's **mempool position is not a
  statistically significant predictor** of its position in the finalized block, while gas fields and DEX/MEV
  address dummies are (ordered logit, October 2024) (arXiv:2508.04003).
- Shadow price of time priority: ≈**4,600 additional gas per transaction** (≈\$0.20–\$0.21) to guarantee
  first-quartile inclusion; over October 2024's **35,799,578 transactions** that is **164.8 bn gas ≈
  \$7.2 M per month** (arXiv:2508.04003).
- The **front-run leg of a sandwich raises first-quartile probability by 47.96%** (Oct 1, 2024; monthly
  average 0.4848) versus 14.64% for the back-run leg (monthly 8.26%) — the largest marginal effect in the
  model (arXiv:2508.04003).
- Sandwiches average **>4,400 per day** (Oct 2022–Sep 2024), **124,946 attacks in October 2024**. Back-run
  legs pay **0.0248 ETH** average gas versus **0.0025 ETH** for other legs (t = 137.9) — \$62.70 per
  back-run and **\$7.89 M of MEV gas in one month**, ≈**9.6%** of the average builder-to-validator payment
  (0.1554 ETH/block). Concentration: **91.1%** of blocks come from MEV agents, top-3 builders hold **85.9%**
  of blocks and **86.8%** of MEV (block-share HHI **3,186**, 2.5× pre-merge miners), and >98% of finalized
  transactions were seen in the public mempool (arXiv:2508.04003).

**DEX/aggregator efficiency is a few basis points, and the winner depends on chain gas.**

- DECS measured **534,540** Ethereum comparisons (6 months): 1inch Classic gave the better effective amount
  in **71%**, parity in 27%, loss in 3% — win/loss **27:1** — totalling **\$4,273,546** uplift, only
  **0.17%** of the \$2,530,926,769 analysed volume. Uplift scales with size while the win rate falls: median
  winning uplift **\$3.08 (≈3 bp)** under \$10k, **\$41.43** in \$10k–100k, **\$230.75 (≈23 bp)** above
  \$100k, with win rates 71% → 67% → 64% (arXiv:2411.01950).
- On non-Ethereum chains (Arbitrum, BSC, Polygon; 472,264 comparisons) parity dominates at **93%** and the
  win rate collapses to **7%** (11:1): cheap gas removes the aggregator's gas-efficiency edge
  (arXiv:2411.01950).
- 1inch's intent protocol crosses over its router at ≈\$10k: under \$1k Classic wins 66.24%, in \$10k–50k
  Classic wins 23.84% (Fusion 19.51%), above \$1 M Classic wins only **3.29%** (Fusion **51.64%**)
  (arXiv:2411.01950).

**Venue events move volatility more than the level, and the sign flips with horizon.**

- Around the CME/CBOE Bitcoin futures launch, bias-corrected realised volatility of 1-minute Bitcoin
  returns rose from **0.0502** to **0.0721** (Period 1, significant, |t|≈4.6), decayed to **0.0480**
  (Period 2, indistinguishable from pre-launch, t≈0.57) and **0.0295** (Period 3, significantly *below*
  pre-launch, |t|≈4.7) (arXiv:1906.03430).
- The spectral decomposition shows *all* bands rose then fell: Period-1/Period-0 amplitude ratios ≈1.35–1.67
  across the low (w: 1–240), medium (241–480) and high (481–720) bands, Period-3 ratios ≈0.42–0.67 — the
  aggregate move is not a single-frequency artefact. Difference-in-differences with Ethereum as control
  confirms the long-run effect only in Period 3, $\beta_3=-0.2872$ (t = −2.68) versus +0.0507 (t = 0.47)
  and −0.0242 (t = −0.26) for Periods 1–2, and a two-regime skewed-t GJR model switches to the
  low-volatility regime in early April 2018 (arXiv:1906.03430).

**Execution-constrained configuration selection moves results by more than most signals do.**

- On BTC/USDT 4h perpetuals with strict $t+1$ semantics, the same fixed strategy and trade sequence scores
  CAGR **2.726** (fees+slippage+funding), **4.308** (fees only) and **5.225** (zero-cost), annualised Sharpe
  2.049 / 2.506 / 2.711 (arXiv:2512.22476). Cost modelling alone is worth a doubling of headline return.
- Two-stage screening is a *drawdown/fragility* filter, not a return maximiser: on the BTC anchor it gives
  training monthly geometric return 0.145 (Sharpe 2.388, MaxDD 0.265) versus 0.222 (3.164, 0.283) for top-1
  one-stage tuning, and its validation-window advantage is **−0.016 with 95% moving-block-bootstrap CI
  [−0.040, 0.008]** — not distinguishable from zero (arXiv:2512.22476).
- The stable-candidate thresholds are design choices with visible consequences: across 27 policy variants
  the selected configuration toggles between three trial IDs (52/87/108), validation CAGR spans
  **0.332–1.058**, Sharpe **0.844–1.667**, MaxDD **0.209–0.386**. The failure mode being guarded against is
  real: the frozen Stage-I baseline loses **−24.09% CAGR** (MaxDD 0.9536, Sharpe −0.0738) over
  2019-09-08–2025-10-14 while earning **+16.59%** in training and **−56.43%** in validation
  (arXiv:2512.22476).

**On-chain flow age is the only "tape" UTXO chains expose.**

- Weighted Average Lifespan and Coin-Days-Destroyed separate store-of-value from medium-of-exchange
  behaviour; a Price-to-Utility rule trading the 0.1/0.9 quantiles returned **7016.06% ROI / Sharpe 3.73**
  on BTC (Dec 27 2013–May 31 2022) and **2582.20% / 2.51** on LTC (Oct 7 2011–May 31 2022) at 0.1% fee and
  a 100-unit trade cap (arXiv:2308.00013).

**Off-topic note.** None of the six was discarded. **arXiv:2308.00013** is the weakest fit — primary
category `cs.CE`, a valuation/asset-allocation paper rather than venue mechanics — retained because it is
the only paper here that defines a measurable *on-chain flow* statistic (UTXO age, lifespan, coin-days) a
venue can report per block, i.e. the on-chain analogue of a trade tape; its backtest numbers are treated as
an upper bound, never as a venue-efficiency result. arXiv:1906.03430 is an event study rather than a
microstructure model, but its subject — introducing a derivative venue onto a spot market — is pure venue
mechanics, and it supplies the corpus's only frequency-decomposition method.

## 2. Implementable formulas & algorithms

### 2.1 Execution-risk-aware CEX-DEX entry and fallback

**Purpose.** Decide whether to attempt a cross-venue arbitrage when the on-chain leg may not land, and how to
unwind when it does not — separating *latent* from *attempted* opportunity.

**Formula.** With $Q$ units bought on the DEX at $p^{DEX}(t_n)$ and sold on the CEX at bid $p^{CEX}_{bid}(t_n)$,
win probability $\alpha$, risk aversion $\lambda$ and threshold $\theta$, enter at slot $n$ iff
$$E[\pi(t_n)\mid \mathcal F_{t_n}]-\lambda\,Var[\pi(t_n)\mid \mathcal F_{t_n}]\ \ge\ \theta,$$
$$E[\pi\mid \mathcal F]=\alpha\,Q\big(p^{CEX}_{bid}(t_n)-p^{DEX}(t_n)\big)+(1-\alpha)\,E\big[V^f(t_{n,1},1)\mid \mathcal F\big],$$
$$Var[\pi\mid \mathcal F]=\alpha(1-\alpha)\Big(X^s-E[X^f\mid \mathcal F]\Big)^2+(1-\alpha)\,Var[X^f\mid \mathcal F],$$
$$X^s=Q\big(p^{CEX}_{bid}(t_n)-p^{DEX}(t_n)\big),\qquad X^f=V^f(t_{n,1},1).$$
Fallback after $k$ failed attempts at slot $n+k$, subslot $m$ is the Bellman choice
$$V^f(t_{n+k,m},k)=\max\{u^c,u^r,u^w\},\qquad
u^c=\pi^c,\quad u^r=E[\pi^r]-\lambda\sqrt{Var[\pi^r]},\quad u^w=E[\pi^w]-\lambda\sqrt{Var[\pi^w]}$$
with close-now $\pi^c=Q(p^{CEX}_{bid}(t_n)-p^{CEX}_{ask}(t_{n+k,m}))$, retry
$\pi^r=\alpha Q(p^{CEX}_{bid}(t_n)-p^{DEX}(t_{n+k}))+(1-\alpha)V^f(t_{n+k+1,0},k+1)$, wait
$\pi^w=V^f(t_{n+k,m+1},k)$, and forced close at $k=\bar k$. CEX prices follow a Gaussian random walk
($\varepsilon_j\sim N(0,\sigma^2\delta)$), bid/ask are $(1\mp\beta)p^{CEX}_{mid}$, and the DEX price tracks the
CEX mid with mean-reverting basis $\eta$.

**Required inputs.** Millisecond CEX best bid/ask and mid; DEX price at each slot boundary; pool fee tier;
win probability $\alpha$; $\lambda$; slot duration $\tau$ and subslot step $\delta$.

**Parameters & defaults.** $\alpha=0.35$, $\lambda=0.01$, $\theta=0$, $\delta=1$ s, 16 Monte Carlo paths per
node, reversion window 300 s, wait horizon and maximum wait 3 s. Robustness grid
$\alpha\in\{0.20,0.35,0.50\}$, $\lambda\in\{0,0.01,0.03\}$; the 5 bp pool then shows +416–530% transactions
and +146–186% volume, the 30 bp pool +1152–1468% and +317–385%. Arbitrage-vs-noise labelling: first
transaction in block, pre-trade CEX-DEX gap above the pool fee, move toward the CEX, post-trade gap still at
or above the fee; noise impacts rounded to 1 bp with |impact| > 30 bp dropped.

**Observed effect sizes.** 12 s → 1 s: transaction count +356–1386% by configuration and agent, weighted
average **+535%** (risk-averse) / +371% (simple); ETH volume weighted average **+203%** (risk-averse) /
+168% (simple); PnL +97–365%.

**Failure modes.** $\alpha$ is exogenous, so the equilibrium response (competition compressing $\alpha$) is
absent; gas fees are zero, overstating the 1 bp pool's economics, and the 30 bp full-grid result rests on
small absolute counts; CEX liquidity is infinite with instant guaranteed execution and constant pool
liquidity. Most important: subslot DEX prices are *interpolated* from CEX prices and historical noise, so the
1-second regime is a protocol model, not an observation — the +535% is not a forecast of a deployed upgrade.

### 2.2 Ordered-logit shadow price of time priority, with sandwich attribution

**Purpose.** Price the harm of transaction re-ordering — how much gas a participant must add to be as early in
the block as the MEV agent put itself — and split that harm into the part coming from sandwich legs and the
part that is general re-ordering.

**Formula.** Ordered logit on block quartile $j\in\{1,2,3,4\}$,
$$P(\text{quartile}=j\mid X)=F(\beta^\top X),\qquad
\text{ME}_i=\frac{\partial F}{\partial x_i},\qquad
\text{gas equivalent}_i=\frac{\partial F/\partial x_i}{\partial F/\partial\,\text{max fee per gas}},$$
$$\text{cost}_i=\text{gas equivalent}_i\times \text{gas price}\times p_{ETH},\qquad
\text{shadow price}=\text{gas equivalent}\times N_{\text{daily transactions}},$$
with $X$ = max fee per gas, three mempool-position dummies, four DEX/MEV direction dummies
(`to DEX`, `to MEV`, `from DEX`, `from MEV`), and controls for average gas price per block, gas used and the
builder's payment to the validator; the extended model adds priority fee, sandwich cost, and front-run and
back-run flags. Attribution of the sandwich legs themselves: a sandwich is a triple (front-run, victim,
back-run) at block positions $i<i+1<i+2$ swapping opposite directions on the same pair, returning to flat at
the back-run, so
$$\text{profit}=\underbrace{\text{ETH out of back-run}}_{\text{close}}-\underbrace{\text{ETH into front-run}}_{\text{open}}-\text{gas}-\text{DEX fees},$$
and the leg-level cost split is tested as $\bar g_{\text{back-run}}$ vs $\bar g_{\text{other legs}}$ (Welch).

**Required inputs.** Mempool first-arrival timestamp and quartile per transaction; finalised block position
normalized to [0,1] and quartiled; max fee per gas and priority fee; gas used; builder-to-validator payment;
labelled DEX and MEV-builder addresses; sandwich triplets (from an attribution source) with token amounts
in/out, pool identity and fee tier.

**Parameters & defaults.** Daily estimation on a UTC clock, four quartiles (5- and 10-category variants keep
the same signs and significance); continuous variables z-scored before fitting, effects unscaled when
reported; 0.1/99.9-percentile winsorisation in the extended model; ordered probit as a robustness twin
("qualitatively identical"); endogeneity probed à la Wooldridge with lagged average gas price as instrument
(none found at 5%, average gas price retained as a control). Attribution labels from EigenPhi; gas from
BigQuery mainnet blocks; USD at the sample's average ETH price (\$2,520.05 for October 2024, \$2,597.34 for
Oct 1).

**Observed effect sizes.** Oct 1 2024: `to MEV` +35.79% (+1,316 gas, \$0.0767), `to DEX` +8.42% (\$0.0180),
`from DEX` +35.46% (\$0.0760), `from MEV` −25.25%; front-run **+47.96%** (+1,888 gas, \$0.1100) and back-run
+14.64% (+576 gas, \$0.0336). 3,674 gas ⇒ \$0.21 per transaction; 4,600 gas/tx averaged ⇒ \$0.20;
4.818 bn gas/day ⇒ ≈\$225k/day. Back-run gas 0.0248 ETH (SD 0.0946) vs 0.0025 ETH (SD 0.0036), t = 137.94,
p = 0.0000; 124,946 attacks in October 2024 ⇒ \$7.89 M of gas ≈9.6% of builder payments; EigenPhi net profits
\$81,079,748 over Nov 30 2022–Oct 31 2024 and \$337,279 in October 2024; the part of re-ordering cost
attributable to sandwich legs is only \$17,228 (means) or \$13,107 (medians) — **99.76% of measured
re-ordering cost is not sandwich legs**.

**Failure modes.** Quartile binning measures "early group", not queue position. The dollar figure is an
ex-ante willingness-to-pay, **not** realised loss, and the authors do not net out the cost of *being*
sandwiched (Capponi et al.'s ≈4,500 ETH/month extrapolates to ≈\$11.34 M in Oct 2024). The max-fee marginal
effect is unstable (24–179 gas per +1% across October) and must be held at a single day's gas and ETH price,
so the aggregate inherits their volatility; four MEV surge days were excluded by hand. Attribution depends
entirely on a third-party database, profit definitions differ between sources (EigenPhi nets gas and DEX
fees; the paper's measure is a gas-equivalent shadow price) and are not interchangeable, and an unclosed
back-run still carries gas.

### 2.3 Effective-amount comparison of DEXs and aggregators (DECS)

**Purpose.** Compare what a user *actually receives* on two venues under the identical block state, rather
than what a quote says.

**Formula.**
$$A_{eff}=\underbrace{A^{raw}_{dst}\times p_{dst}}_{\text{dst amount}}-\underbrace{G_{used}\times p_{gas}\times p_{native}}_{\text{tx cost}},
\qquad \text{uplift}=A_{eff}^{out}-A_{eff}^{in},\qquad \text{uplift}\%=\frac{A_{eff}^{out}-A_{eff}^{in}}{V_{in}},$$
$$\text{winner}=\begin{cases}\text{1inch} & A_{eff}^{out}-A_{eff}^{in}>\varepsilon\\ \text{draw} & |A_{eff}^{out}-A_{eff}^{in}|\le\varepsilon\\ \text{competitor} & \text{otherwise}\end{cases},
\qquad \text{win rate}=\frac{W_{out}}{W_{in}}.$$
Parity thresholds are volume-bucketed (see below). For intent-based protocols the gas term is dropped from
$A_{eff}$ because resolvers internalise it into $A^{raw}_{dst}$; that is also why intent systems can only be
compared *indirectly* against the router baseline.

**Required inputs.** Mempool or freshly mined swap transactions with calldata; contract ABIs for decoding
(source token, destination token, minimum output, deadline); an archive-node `debug_traceCall` path to
re-simulate at the same block; gas used and gas price from trace; USD prices for both tokens and the native
asset; the simulation-inclusion constraint
$$mined\_block-simulation\_block\le X.$$

**Parameters & defaults.** $X$ = 4 blocks (Ethereum), 16 (BSC), 24 (Polygon), 192 (Arbitrum); the same gas
limit as the incoming transaction is set when rebuilding calldata; the comparison baseline is 1inch
Classic; wallets rotate hourly from an indexed address pool with sufficient native balance and approvals;
exact-output swaps excluded; transactions with unreliable price data excluded;
$\varepsilon_{USD}=\$1$ for $V_{in}<\$10{,}000$, \$5 for \$10k–100k, \$10 for \$100k–500k, \$50 otherwise.

**Observed effect sizes.** Ethereum: 534,540 comparisons, 71%/27%/3% win/draw/loss, 27:1, \$4,273,546 uplift
(0.17% of \$2.53 bn). Non-Ethereum: 472,264 comparisons, 7%/93%/1%, 11:1, \$187,879 (0.05% of
\$347.5 M). Bucket medians (Ethereum): \$3.08 (<\$10k), \$41.43 (\$10k–100k), \$230.75 (>\$100k); most
transactions land within 0–1 blocks of the mined block (57.4%/24.0% on Ethereum).

**Failure modes.** Private market makers are invisible on-chain until execution: they are <1/10 of
aggregator protocol volume but ≈40% of PMM traffic still appears in simulated routes, so the comparator
under-represents them; off-chain volume-incentive deals are unobservable. Intent orders have indeterminate
execution timing, so only the router baseline makes them comparable — a cross-intent ranking is not
identified. The block-distance constraint $X$ biases the sample toward fast resolvers and penalises
high-latency chains (Arbitrum's 192-block window is ≈6 comparisons deep in the reported distribution).

### 2.4 Funding-aware, execution-constrained auto-tuning (perpetuals)

**Purpose.** Select strategy configurations whose backtest semantics are the same as live semantics, and
make cost-driven performance inflation and parameter fragility visible before deployment.

**Formula.** Net per-bar return and annualisation:
$$r_t^{net}=r_t^{raw}-C_{fee,t}-C_{slip,t}-C_{fund,t},\qquad
r_t^{raw}=\pi_t\,r_t^{mkt},\qquad \Delta\pi_t=\pi_t-\pi_{t-1},$$
$$r_t^{mkt}=\frac{P_t^{close}}{P^{close}_{t-1}}-1,\qquad
r_{ann}=(1+R_{tot})^{AF/N}-1,\qquad AF=2190,$$
with $\pi_t$ derived from $S_{t-1}$ (strict $t+1$), fees and slippage on $|\Delta\pi_t|$, and funding accrued
on notional $\pi_t$ from the 8-hour funding series carried forward, never backfilled. Soft funding bias on
long entry thresholds:
$$\tau_{long}(t)=\tau_{base}+\kappa\cdot\max\!\Big(\frac{|fr_t|-\vartheta_{bias}}{10000},\,0\Big).$$
Momentum score and signal:
$$m_t=\tfrac12\Big(1+\tanh\frac{EMA_{fast,t}-EMA_{slow,t}}{\sigma\,EMA_{slow,t}}\Big),\qquad
C_t=w_{mom}m_t+(1-w_{mom})a_t,\qquad
S_t=\begin{cases}+1, & C_t\ge\tau_t\\ -1, & C_t\le 1-\tau_t\\ 0, & \text{otherwise}\end{cases}$$
Stable-candidate statistics over a cost-scenario grid $s$:
$$R_{m,s}=\prod_{t\in m}(1+r^{net}_{t,s})-1,\qquad
g_s=\exp\Big(\frac{1}{M_m}\sum_m\log\big(1+\max(R_{m,s},-0.999999)\big)\Big)-1,$$
$$mean\_monthly=\mathbb E_s[g_s],\quad min\_monthly=\min_s g_s,\quad
maxDD\_mean=\mathbb E_s[maxDD_s],\quad switch\_density=\frac{\#\{\Delta\pi_t\ne 0\}}{N}.$$

**Required inputs.** One timestamp-aligned 4-hour OHLCV series per contract (bar-open UTC, deduplicated,
continuity-checked, no interpolation); an 8-hour funding-rate series aligned to that grid; a fixed cost
profile plus a cost-scenario grid; the window split (training / validation / long-horizon / blind
hold-out); the Stage-I search budget.

**Parameters & defaults.** Stage I: TPE (Optuna), $N_{opt}=40$ (auxiliary check 120), objective =
cost-adjusted annualised return; Stage II: keep $K=5$ after ex-ante filters, rolling windows of 2,000 bars
stepped 500; cost grid `taker_bps` $\in\{3,4,6\}$ × `fund_mult` $\in\{0.5,1.0,1.5\}$ = 9 scenarios over the
top 40 candidates = 360 strict backtests; guard thresholds `mean_monthly_true` ≥ 0.005, `min_monthly_true`
≥ 0, `maxDD_mean` ≤ 0.30, `switch_density_mean` ≤ 0.12; search-space defaults (ranges in brackets)
`ema_fast` 12 (6–32), `ema_slow` 26 (20–96), `ema_threshold` 0.003 (0.0005–0.0060), `bb_period` 20 (10–30),
`bb_dev` 2.0 (1.0–2.5), `min_hold_bars` 1 (1–6), `cooldown_hours` 0 (0–8), ATR stop/take-profit and
`max_exposure_abs` 0 (0 disables), funding-bias threshold 0 (0–10) with slope 0 (0–0.005). Data: BTC/USDT
core 2019-09-08–2021-12-31 ($N=5{,}069$ 4h returns, mean 0.00043, SD 0.01615), long 2019-09-08–2025-10-14
($N=13{,}368$, mean 0.00026, SD 0.01309); training 2019-09-08–2021-01-01, validation 2021-01-01–2023-01-01,
blind post-ETF 2024-01-01–2025-10-14, 2023 deliberately unused on BTC.

**Observed effect sizes.** Cost ladder on the fixed stress configuration: rigorous CAGR 2.726 (Sharpe 2.049,
MaxDD 0.265, 636 trades), fee-only 4.308 (2.506, 0.262, 636), zero-cost 5.225 (2.711, 0.260, 535).
Two-stage vs one-stage (BTC monthly geometric): training 0.145 vs 0.222; validation 0.038 vs 0.051 with
MaxDD 0.231 vs 0.318; post-2024 0.016 vs 0.023 — while on SOL/USDT the two-stage candidate *also* wins on
return (validation 0.362 vs 0.227, Sharpe 4.208 vs 3.398) and on AVAX/USDT one-stage's 0.479 training return
comes with a 0.795 MaxDD. Offline-to-replay parity: three SOL/USDT 1-hour snapshots (2,000 bars each)
matched exactly on direction and exposure ($\max|\Delta S|=0$, $\max|\Delta\pi|=0$).

**Failure modes.** Linear costs only: no market impact, no capacity constraint, small-account assumptions, so
CAGRs above 1.0 are diagnostics rather than scalability claims. The stable-candidate thresholds are policy,
not constants — a 27-variant scan moves validation CAGR across 0.332–1.058. Compounded metrics inflate in
high-volatility regimes and 4-hour crypto returns are autocorrelated and heavy-tailed, so Sharpe is
descriptive only (constant 3% risk-free rate assumed). Screening does **not** raise returns by construction;
the reported bootstrap interval on the BTC validation difference cannot reject zero.

### 2.5 Venue-event volatility decomposition: bias-corrected RV + DFT bands

**Purpose.** Test whether a venue event (a derivative listing, a rule change, a fee change) changed
volatility in aggregate, and in which frequency bands, without imposing a parametric price process.

**Formula.** With $r_{t,k}$ the $k$-th one-minute log return on day $t$ (1,440 per day for 24/7 trading),
$$\sigma_t=\sqrt{\frac{1440}{1339}\sum_{k=1}^{1440}r_{t,k}^2+2\sum_{k=1}^{1339}r_{t,k}r_{t+1,k}},$$
$$a_t(w)=\frac{2}{1441}\sum_{k=1}^{1441}P_t(k)\cos\frac{2\pi wk}{1441},\qquad
b_t(w)=\frac{2}{1441}\sum_{k=1}^{1441}P_t(k)\sin\frac{2\pi wk}{1441},\qquad
C_t(w)=\sqrt{a_t(w)^2+b_t(w)^2},$$
$$\overline{C}^{(i)}(w)=\sqrt{\frac{\sum_{t\in \text{Period}_i}C_t(w)^2}{|\text{Period}_i|}},\qquad
Change\_Freq_w=\frac{\overline{C}^{(i)}(w)}{\overline{C}^{(0)}(w)}.$$
Because the sample variance equals the sum of squared Fourier amplitudes across all frequencies, band-wise
changes sum into the aggregate. Difference-in-differences:
$$\log(\sigma_t)=\alpha+\beta_1\,Period[k]+\beta_2\,Treatment+\beta_3\,(Period\times Treatment)+\epsilon.$$

**Required inputs.** One-minute prices for $\ge2$ venues and $\ge1$ control asset over symmetric pre/post
windows; an event date; the Garman-Klass estimator as a robustness twin,
$$\sigma_t^{GK}=\sqrt{\frac{1}{1440}\sum_k\Big(\log\frac{H_k}{L_k}\Big)^2-(2\log 2-1)\Big(\log\frac{C_k}{O_k}\Big)^2}.$$

**Parameters & defaults.** 1,441-point daily price vector; $w=1,\dots,720$; Hau's bands — low 1–240,
medium 241–480, high 481–720; four sub-periods of ≈2 months around the event (here Period 1
Dec 18 2017–Feb 28 2018, Periods 2–3 of 2 months each); event date set to the CME launch (Dec 18) rather
than the CBOE launch (Dec 10) because CBOE volume was too small, with the alternative date reported to
leave results unchanged.

**Observed effect sizes.** RV averages 0.0502 → 0.0721 → 0.0480 → 0.0295 across Periods 0–3 (Garman-Klass
identical in the reported table); Period-1/Period-0 band ratios 1.3790/1.3632/1.3517 (Bitflyer) and
1.5352/1.6607/1.6712 (Coinbase); Period-3/Period-0 ratios 0.5664/0.5658/0.5716 and 0.6208/0.6534/0.6690;
DD coefficient $\beta_3=-0.2872$ (t = −2.6845) for $k=3$ only.

**Failure modes.** The event date is a judgement call (two competing launch dates); the four sub-periods
are ≈2 months each, so Period-1 effects cannot be separated from the December 2017 price collapse;
Table 1's five exchange panels are numerically identical as published, so per-venue dispersion must be read
off the DFT band table instead. RV and DFT both consume the whole day before the statistic exists — fine
for an event study, fatal if the same window is used to trade. The two-regime GJR companion is a chosen
specification with Maximum-Likelihood estimation forced by sample size.

### 2.6 On-chain flow-age accounting (UTXO venues)

**Purpose.** The only flow statistic an on-chain venue can produce without a trade tape: how long coins
rested before moving, weighted by size. Used to separate store-of-value behaviour from medium-of-exchange
behaviour and to build a valuation ratio.

**Formula.**
$$WAL[\text{date}=i]=\frac{\sum_{\text{date}=i}\#_{UTXO}\times Lifespan}{\sum_{\text{date}=i}\#_{UTXO}},\qquad
Lifespan=\text{spent block timestamp}-\text{block timestamp},$$
$$CDD[\text{date}=i]=\sum_{\text{date}=i}\#_{UTXO}\times Age_{days},\qquad
Token\ Utility=\frac{\text{token velocity}\times\text{staking ratio}}{\text{price volatility}\times\text{dilute rate}},$$
$$PU=\frac{\text{price}}{Token\ Utility}.$$

**Required inputs.** Full input/output graph with timestamps (every UTXO's birth and death), daily price,
current total supply, staking share (tokens with lifespan > 1 year), 24-hour transacted share of supply,
annual supply growth.

**Parameters & defaults.** PU bands: overvalued > 100, normal 60 < PU < 100, undervalued < 60; signals at
the previous day's 0.1 (buy) and 0.9 (sell) PU quantiles; backtest with \$100,000 initial capital, 0.1%
transaction fee, 100-unit trade cap; data spans BTC 2009-01-03–2022-05-31 and LTC 2011-01-01–2022-05-31,
with trading windows from 2013-12-27 (BTC) and 2011-10-07 (LTC).

**Observed effect sizes.** BTC ROI 7016.06% with annualised Sharpe 3.73 versus LTC 2582.20% and 2.51;
Bitcoin's UTXO age distribution shifts toward the long-age bins while Litecoin's stays dominated by
sub-1-day and sub-1-year coins — the empirical content behind the "bitcoin gold / litecoin silver"
analogy.

**Failure modes.** UTXO-model chains only (account-based chains such as Ethereum have no UTXO lifespan);
"staking ratio" and "token velocity" are not standardised across data vendors; the metric set is
single-asset and spans an extreme bull regime, so the 7016% is a regime artefact rather than an edge;
price-to-utility is a valuation level, not a microstructure signal, and no venue-fee, slippage or
market-impact assumption enters the backtest beyond a flat 0.1% fee.

## 3. Data requirements → available endpoints

Rows below are real entries from `strategies/endpoints.json` (url, category, provider and probe status
copied verbatim); `—` rows are **gaps** — no current provider serves them. The catalog has **no `crypto`
category row at all**, so every crypto-specific venue input lands in the gap block.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| 4h/1h OHLCV bars for the perpetual backtest | `moomoo://get_cur_kline` | `technical_indicators` | `moomoo` | gateway (not live-probed) |
| Intraday/daily bar series (single symbol per call) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | `twelvedata` | ok |
| Daily OHLCV (volatility scaling, Parkinson $\sigma_D$) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | `eodhd` | ok |
| Top-of-book snapshot, one venue at a time | `moomoo://get_market_snapshot` | `core_stock_apis` | `moomoo` | gateway (not live-probed) |
| Technical indicators over the bars (EMA/ATR/BB inputs) | `https://www.alphavantage.co/query` | `technical_indicators` | `alpha_vantage` | ok |
| Risk-free rate for Sharpe annualisation | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | `federal_reserve` | ok |
| Macro series for carry/rate regressors | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | `fred` | ok |
| Venue listing / regulatory / hack headlines | `https://eodhd.com/api/news` | `news_data` | `eodhd` | ok |
| News (secondary) | `https://newsapi.org/v2/everything` | `news_data` | `newsapi` | ok |
| News/sentiment (third; throttled) | `https://api.gdeltproject.org/api/v2/doc/doc` | `news_sentiment` | `gdelt` | rate_limited |
| Symbol universe / tick and contract conventions | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | `eodhd` | ok |
| Event probabilities gating venue flows (upgrades, ETF dates) | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | `polymarket` | ok |
| **CEX book depth (L2/L3) and signed tick trades (`aggTrade`-class)** | — | — | — | **gap** |
| **Perpetual funding-rate history (8h, timestamped), open interest and liquidations** | — | — | — | **gap** |
| **DEX swap events with pool reserves and fee tier (Uniswap v3)** | — | — | — | **gap** |
| **MEV/ordering stack: mempool arrivals, per-block order, builder identity and bids, builder→validator payments, sandwich-leg labels, per-transaction gas** | — | — | — | **gap** |
| **Archive-node `debug_traceCall` simulation + ABI decode path** | — | — | — | **gap** |
| **UTXO set / cohort dataset (BigQuery-class on-chain graph)** | — | — | — | **gap** |
| **Multi-venue synchronised 1-minute panel (≥5 venues, 1,440 obs/day)** | — | — | — | **gap** |

**What the gap costs, quantified.** The ordering paper needs a full month of mainnet — **35,799,578
transactions in October 2024** (1,266,656 on a single day) — joined to mempool first-arrival timestamps and
per-transaction gas; **>98%** of finalized transactions are traceable to the public mempool, so the mempool
is not optional, and sandwich attribution adds **124,946 labelled attacks** in that month alone. The CEX-DEX
paper needs millisecond best bid/ask plus *every* Uniswap v3 swap in three ETH-USDC fee tiers for three
months; its own related work cites 7.2 M arbitrage transactions and \$233.8 M extracted over 19 months.
Without DEX swap events and CEX quotes there is no cross-venue spread series to condition on. DECS needed
**1.2 M swap transactions** decoded, rebuilt and re-simulated at the same block — an archive node plus
per-protocol ABI decoders. The perpetual work is the cheap end: 4-hour bars plus one 8-hour funding series
— **13,368 bars** for the long BTC window, 5,069 for the core — with per-asset streams for ETH
(2021-12-31–2025-11-24) and SOL/AVAX (2021-01-01–2025-12-16). The event study needs **1,440 one-minute
returns per venue per day across five venues for 13 months**, a bar-level panel rather than a tape, so it is
reproducible in principle from bar endpoints once a multi-venue crypto panel exists — which the catalog does
not yet assert. On-chain accounting needs the whole UTXO graph from 2009: the largest requirement here, with
no partial substitute.

## 4. Pitfalls, validation and measurement

- **Look-ahead arrives through the plumbing, not the signal.** AutoQuant's fix is architectural: strict
  $t+1$ (a signal computed at the close of bar $t$ can only affect P&L from $t+1$), funding carried forward
  between 8-hour stamps with **no backfill**, missing OHLCV bars never interpolated, and offline-to-replay
  parity as an exact match ($\max|\Delta S|=0$, $\max|\Delta\pi|=0$ over three 2,000-bar snapshots)
  (arXiv:2512.22476). DECS's inclusion rule $mined\_block-simulation\_block\le X$ is the same idea — $X$ runs
  4 (Ethereum) to 192 (Arbitrum) blocks, most accepted Ethereum comparisons sit 0–1 blocks away
  (57.4% / 24.0%), and widening $X$ trades liquidity-state fidelity for sample size (arXiv:2411.01950).
- **Multiple testing is measurable, so measure it.** Stage I is a best-of-$N$ statistic: at $N_{opt}=40$ TPE
  reaches 0.1172 against a random-search baseline of $-0.7832\pm0.4848$, and that same-budget comparison —
  not the headline return — is the diagnostic. Deflated-Sharpe- and overfitting-probability-style checks
  complement strict semantics, they do **not** replace them (arXiv:2512.22476).
- **Selection policy is a knob; publish its sensitivity.** 27 threshold variants change which trial is
  selected (52/87/108) and swing validation CAGR 0.332–1.058, Sharpe 0.844–1.667, MaxDD 0.209–0.386; freeze
  thresholds ex ante (arXiv:2512.22476).
- **Cost assumptions dominate.** Identical fixed parameters give CAGR 2.726 fully costed, 4.308 fee-only,
  5.225 frictionless — an upper bound on cost-driven inflation, not typical practice (arXiv:2512.22476). The
  CEX-DEX model sets gas to zero and warns its low-fee-pool numbers are therefore optimistic
  (arXiv:2601.00738). DECS excludes exact-output swaps and unreliable prices and scales its parity band with
  size (\$1 → \$50), so "win rate" and "uplift" answer different questions (arXiv:2411.01950).
- **Regime dependence is not a caveat, it is the finding.** Bitcoin's post-futures volatility was higher for
  two months, indistinguishable for two months, and *lower* thereafter, the DD term being significant only
  in Period 3 (arXiv:1906.03430); four hand-identified MEV surge days were removed before estimation
  (arXiv:2508.04003); AutoQuant's frozen baseline loses −24.09% CAGR over the full sample while earning
  +16.59% in training (arXiv:2512.22476).
- **Metric choice decides the conclusion.** Counts and volume disagree (CEX-DEX: +535% transactions versus
  +203% volume, as marginal opportunities carry smaller optimal sizes, arXiv:2601.00738); a 71% win rate
  coexists with 0.17%-of-volume uplift (arXiv:2411.01950); CAGR above 1.0 is a fragility diagnostic, so
  ranking uses monthly geometric mean, drawdown and switch density (arXiv:2512.22476).
- **Null tests, and one missing hold-out.** If ordering were fair, mempool position would predict block
  position — it does not, at 0.1% significance (arXiv:2508.04003). The futures study uses Ethereum as an
  untreated control so a market-wide December 2017 move cannot be read as a futures effect
  (arXiv:1906.03430). DECS validates by publishing methodology and raw data rather than by holding out —
  read its 0.17% uplift as a measurement claim, not a strategy result (arXiv:2411.01950).
- **Sample splits must be stated in bars and timestamps.** AutoQuant: training 2019-09-08–2021-01-01,
  validation 2021-01-01–2023-01-01, blind post-ETF 2024-01-01–2025-10-14, 2023 deliberately unused on BTC,
  half-open intervals so adjacent windows share no bar. Its own bootstrap on the validation difference
  (−0.016, CI [−0.040, +0.008]) shows two-stage screening is **not** established to improve returns
  (arXiv:2512.22476). Sub-slot regimes are models too: the 1-second environment is interpolated from CEX
  prices plus noise and reversion with fixed $\alpha$, which competition would compress
  (arXiv:2601.00738). On-chain statistics ("velocity", "staking ratio", the UTXO age bins) are
  vendor-defined definitions, and the PU backtest's flat 0.1% fee and 100-unit cap are assumptions
  (arXiv:2308.00013).

## 5. Recommended first implementation in FinRobot

Ranked by value per unit of effort against what can be fetched today; items 1, 2, 3, 4 and 8 are buildable
now, the rest are explicitly blocked.

1. **Perpetual cost/funding accounting core.** $r_t^{net}=r_t^{raw}-C_{fee}-C_{slip}-C_{fund}$ with strict
   $t+1$ positions, turnover-proportional costs, an aligned funding series (carry-forward, no backfill) and
   the accounting invariants (exposure, fees, slippage, funding and PnL reconcile across backtest and
   replay). *Data:* `moomoo://get_cur_kline` (4h bars); funding rates are the **gap** — supply an external
   series or a documented constant. *Passes when:* a fixed configuration reproduces the cost-ladder
   ordering (rigorous < fee-only < zero-cost) and the offline and replay paths agree exactly on $\Delta S$
   and $\Delta\pi$ over a 2,000-bar window (arXiv:2512.22476).
2. **Two-stage configuration selector with ex-ante thresholds.** Stage-I black-box search over a bounded
   hyperparameter block, Stage-II screening on held-out rolling windows and a cost grid, retain $K=5$ by
   monthly geometric mean ascending drawdown. *Data:* item 1's engine only. *Passes when:* it can *show* the
   trade-off — a lower-drawdown candidate or an explicit null on returns (bootstrap CI containing zero),
   never a bare higher CAGR (arXiv:2512.22476).
3. **Venue-event volatility decomposition on bars.** Bias-corrected realised volatility plus DFT band
   amplitudes (low 1–240 / medium 241–480 / high 481–720) around a dated venue event, with a control asset,
   a difference-in-differences term and Garman-Klass as a robustness twin. *Data:*
   `moomoo://get_cur_kline` or `https://api.twelvedata.com/time_series` at 1-minute granularity; event dates
   from `https://eodhd.com/api/news` and `https://gamma-api.polymarket.com/markets`. *Passes when:* the
   pre/post band ratios and the $\beta_3$ sign reproduce on the December 2017 futures case and the control
   asset shows no treatment-like change (arXiv:1906.03430).
4. **CEX-DEX arbitrage simulator with execution risk.** The two-agent, $\alpha$-win-probability model with
   fallback Bellman recursion, run at 12 s and 1 s confirmation. *Data:* self-contained (synthetic CEX walk
   + interpolated DEX path); a live version needs CEX quotes and DEX swaps, both **gap**. *Passes when:* the
   mechanical agent reproduces +356–412% transactions and the risk-averse agent the *larger* ≈+535% — i.e.
   selection, not opportunity count, drives the delta (arXiv:2601.00738).
5. **Ordered-logit shadow price of time priority.** Quartile model, marginal effects converted to gas
   equivalents and dollars, aggregated over daily transaction counts. *Data:* mempool arrivals, finalized
   block positions, gas fields, MEV-builder labels — all **gap**; ship only once those exist, since a
   bars-only proxy is not the same object. *Passes when:* mempool position is **insignificant** while the
   MEV/DEX dummies dominate, reproducing ≈4,600 gas/tx (arXiv:2508.04003).
6. **DEX effective-amount comparator with parity bands.** The $A_{eff}$ formula, volume-bucketed
   $\varepsilon$ and the inclusion constraint, with per-protocol ABI decoders. *Data:* archive-node
   `debug_traceCall` and DEX swap events — **gap** (the decode path can be written and unit-tested against
   recorded traces in advance). *Passes when:* re-simulating a recorded swap on the same block reproduces
   the observed destination amount exactly, and the win rate is invariant to which protocol is the baseline
   (arXiv:2411.01950).
7. **On-chain flow-age indicators (UTXO venues).** WAL, CDD, UTXO/STXO age distributions and the
   price-to-utility ratio with 0.1/0.9 quantile signals. *Data:* UTXO cohort dataset — **gap**, with no
   partial substitute. *Passes when:* computed WAL and CDD reproduce published daily BTC series on a fixed
   window; until then it is a schema, not a strategy (arXiv:2308.00013).
8. **Venue cost-profile registry.** One declarative file of per-venue, per-instrument costs (taker/maker
   bps, funding multipliers, slippage, leverage and notional caps) that every backtest must read, with the
   cost grid expressed as perturbations of it. *Data:* none live; use
   `https://eodhd.com/api/exchange-symbol-list/US` for tick/contract conventions. *Passes when:* no backtest
   can run without naming a profile and a cost-sensitivity table is an automatic output
   (arXiv:2512.22476).

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2601.00738v1 | Second Thoughts: How 1-second subslots transform CEX-DEX Arbitrage on Ethereum | 2026 |
| 2512.22476v3 | AutoQuant: An Auditable Expert-System Framework for Execution-Constrained Auto-Tuning in Cryptocurrency Perpetual Futures | 2025 |
| 2508.04003v3 | The Marginal Effects of Ethereum Network MEV Transaction Re-Ordering | 2025 |
| 2411.01950v1 | Advancing DeFi Analytics: Efficiency Analysis with Decentralized Exchanges Comparison Service | 2024 |
| 2308.00013v1 | Bitcoin Gold, Litecoin Silver: An Introduction to Cryptocurrency's Valuation and Trading Strategy | 2023 |
| 1906.03430v1 | The Effects of the Introduction of Bitcoin Futures on the Volatility of Bitcoin Returns | 2019 |
