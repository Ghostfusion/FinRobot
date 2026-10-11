---
id: high-frequency-latency
name: High-Frequency Latency Measurement
version: 1.0.0
author: finrobot
domain: quant-research
description: Measure and decompose tick-to-book latency into a floor-plus-slope-per-message budget, reporting medians, p99/p99.9 and p99/p50 amplification, not averages. Use when benchmarking actor delivery, socket-to-book tails, ring-buffer or C++ hot-path optimisations, or sizing a feed handler.
triggers:
- latency
- tick-to-book
- latency budget
- tail latency
- p99
- feed handler
- ring buffer
- disruptor
- socket-to-book
- microbenchmark
- fast_send
- message pool
requires_data:
- input: Daily OHLCV (daily returns, $\sigma_D$ proxy)
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Daily OHLCV (secondary)
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Daily/previous aggregate bars
  provider: massive
  category: core_stock_apis
  status: ok
- input: Daily OHLCV (tertiary)
  provider: stockdata
  category: core_stock_apis
  status: ok
- input: Intraday 5-min bars ($RV,RQ,CJ$, HARQ, push-response)
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: Intraday technical indicators / bars
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
- input: Tradable symbol universe / tick sizes
  provider: eodhd
  category: exchange_symbols
  status: ok
- input: '**Tick / NBBO event stream (event-time pushes)**'
  provider: ''
  category: ''
  status: gap
- input: '**Market-by-order (MBO) message stream (LOBSTER-style)**'
  provider: ''
  category: ''
  status: gap
- input: '**L2/L3 book depth (≥3 ranks)**'
  provider: ''
  category: ''
  status: gap
- input: '**Hardware receive timestamps / colocation feed (wire-to-book)**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# High-Frequency Latency Measurement

You are an expert low-latency systems and market-microstructure researcher who measures tick-to-book latency budgets and locates where microseconds go. You consume benchmark harness output (delivery-mode, ring-buffer and C++ hot-path timings) and, when supplied, a decoded per-packet venue feed with socket timestamps; intraday bars serve only as a coarse fallback. You refuse to fabricate nanosecond figures, wire-to-book timestamps, or percentiles that were not measured, and you state the intraday-data limitation plainly: NBBO/MBO streams and hardware receive timestamps are a gap in the current data layer, so live-path claims stay socket-to-book and feed-driven figures are not inferred from daily bars.

> Source: FinRobot strategies corpus review — `strategies/qfin-tr/high-frequency-latency.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **A synchronous-delivery concurrency pattern removes the actor-model overhead that made it "unsuitable for HFT".** `fast_send` runs the receiver's handler inline on the sender's thread under the receiver's exclusive-access lock and returns the reply by value, while the handler cannot tell which delivery mode was used (*receiver transparency*). Measured on an AMD EPYC 9374F, pinned, `-O3 -march=native`: a cross-thread asynchronous round trip is $\approx 3{,}370$ ns; co-scheduling both actors on one thread (*grouping*) is 90 ns ($37\times$); inline `fast_send` is $\sim 30$ ns amortised ($\sim 110\times$). A single `fast_send` hop is $\sim 10$ ns against $\sim 1$ ns for a bare devirtualised call (arXiv:2609.21173).

- **The same paper measures a live CME MDP 3.0 socket-to-book path: the framework is under 1% of the floor and none of the tail.** 8.29 M messages over 53 minutes on ES, NQ, ZN (2026-09-16) fit $\text{median} \approx \text{floor} + \text{slope}\times\text{idx}$; the floor (first message in a packet) agrees to $\pm 0.42\,\mu$s across six streams at $6.8$–$7.2\,\mu$s and moves $\le +0.4\,\mu$s during an FOMC release that lifted packet rate $4.6$–$9.8\times$; the per-message slope is $312$–$966$ ns/msg. Unconditional $p_{99}$ runs from $18.5\,\mu$s (ES book) to $219\,\mu$s (ZN trade), $p_{99.9}$ up to $410\,\mu$s, max up to $5{,}567\,\mu$s (arXiv:2609.21173).

- **The latency tail is the feed, not the code.** 87–99.7% of messages arrive at an empty decoder ring; in-packet position is the dominant within-packet contributor (the last message of a 45-message packet pays $44\times 0.57 \approx 25\,\mu$s deterministically); a memory pool cut the grouped tail maximum from 5.5 ms to $33\,\mu$s. The design lever is the per-message *service* cost (the slope), not queue depth or the messaging layer (arXiv:2609.21173).

- **C++ micro-optimisations are individually large and individually benchmarked.** Cache warming (sequential pre-pass) cut an array-traversal benchmark from 267.7 ms to 25.6 ms ($\approx 90\%$); `constexpr` factorial ran 0.245 ns/iter vs 2.69 ns runtime ($\approx 90.9\%$); compile-time dispatch 1.92 ns vs 2.60/2.15 ns runtime. Applied to a market-neutral pairs-trading backtest, a fixed-array buffer cut latency 48.6%, SIMD + loop-unrolling 31.3%, inlining 21.4%, combined 87.3% ($517{,}559$ ns $\to$ $65{,}588$ ns mean, SD $4{,}233 \to 400$ ns, paired $t$-test significant) (arXiv:2309.04259). Counter-intuitive but consistent: the *combined* optimisation lowered executed instructions (6.01 B $\to$ 3.27 B), while the individual techniques *raised* them (buffer 8.27 B, inlining 9.07 B, SIMD 8.35 B) yet still ran faster — memory access pattern, not instruction count, drove the gain.

- **The LMAX Disruptor ring buffer beats a mutex/condition-variable queue at scale.** At 1,000 events the Disruptor averaged 74,908 ns vs 931,255 ns for the simple queue ($t = 22.596$, $p = 1.243\times10^{-23}$); the gap widens with event count ($+2{,}464$ ns at 10 events to $+341.7$ ms at $10^6$). The paper separately quotes LMAX's own reference figures — three orders of magnitude lower mean latency, $\sim 8\times$ throughput — which were *not* re-measured and should be read as vendor claims (arXiv:2309.04259).

- **A 1% latency increase is associated with a 0.9% higher exposure to adverse order-book changes.** This is Ende et al. (2011), relayed by arXiv:2309.04259, which maps its own 87.3% speed-up onto a claimed 78.6% exposure reduction — an extrapolation across studies and hardware, useful as an order-of-magnitude only.

- **Speed bumps are weaker than intended, and only the asymmetric kind works.** In a lab market (56 University of Toronto students, 16 groups, 32 rounds, $N=1{,}344$ trader-rounds), no-bump investment was 75% of endowment; any bump cut it to 66%; *asymmetric* bumps (liquidity takers delayed, market maker not) cut it 20% (60.32% deterministic, 58.72% random), *symmetric* bumps left it at essentially no-bump (75.10% deterministic, 71.07% random). One SD of bump size (2 s $=$ 40% of the unconditional exchange latency) cut asymmetric-regime investment a further 8.33%; small→large (20%→100% of latency) 16.7%; under the low-cost technology tier 16.67%. Random vs deterministic: no significant difference; symmetric: no effect on investment (arXiv:1910.03068).

- **Real venue bumps span 350 µs to 200 ms.** IEX / NYSE American 350 µs (all orders), TSX Alpha 1–3 ms randomised (liquidity takers), Aequitas NEO 3–9 ms (takers), Thomson Reuters 0–3 ms (all but cancels), Eurex 1 or 3 ms (takers), proposed ICE 3 ms, NASDAQ PHLX 5 ms, Interactive Brokers 10–200 ms (Table 1, arXiv:1910.03068). The design space is asymmetric-and-long, not symmetric.

- **A GPU-accelerated MARL environment for HFT is the first open, large-scale one.** JaxMARL-HFT runs heterogeneous agents on market-by-order data with up to $240\times$ end-to-end training speed-up on identical hardware, processing one year of AMZN 2024 order data ($\approx 400$ M orders) in 4 GB GPU RAM across 4,096 parallel environments. Environment-step throughput is 21,969 steps/s (100 messages/step, 1 agent/type) vs 463 (PyMarketSim), 734 (ABIDES-gym), 1,805 (CPU-MARL); at 1 message/step 351,119 vs 10,830 / 2,979 / 4,896. Speed-up grows with agent count: $\sim 5$–$35\times$ (1 agent/type), $95$–$125\times$ (5), $200$–$240\times$ (10) (arXiv:2511.02136).

- **The MARL agents are honest about their P&L.** Under IPPO with a two-player (market-making + execution) setup, no learned market-making strategy made net profit — they lost $\approx 0.2$ ticks on average, partly because resting orders are cancelled every RL step, destroying time priority; the execution agent cut cost by up to 20% of a tick versus TWAP (arXiv:2511.02136).

- **Regime-aware volatility forecasting works; return prediction barely does.** On 5-minute CSI 300 data 2005–2023, a HARQ + filtered high-volatility-probability model beats baseline HARQ on every loss (MSE-log 0.267345 vs 0.279911; QLIKE 0.162259 vs 0.171013; LMAE 0.402701 vs 0.410499), with the gain concentrated in high-volatility states; return prediction over 2,004 out-of-sample days is weak and state-dependent (full-sample correlation 0.0449 and hit ratio 53.49% with HAC $p=0.0009$; low-volatility correlation 0.0638, $p=0.0013$; high-volatility correlation $-0.0617$, insignificant $p=0.1928$) (arXiv:2606.09478).

- **Push-response structure in SPY is real but only after lag-specific standardisation.** From $\approx 2.6\times10^9$ NBBO events over $\approx 1{,}512$ regular-trading-hours days (2018–2023, seven exchanges), conditional responses cluster near zero for short lags ($L\in\{1\}\cup\{50,\dots,5000\}$ ticks) and develop a ridge beyond $|z_p|\approx 1$ for longer lags ($L$ up to $5\times10^5$); the antisymmetric (sign-conditioned) component dominates at short and mid lags while the symmetric (magnitude) component dominates at extremes; large negative pushes elicit stronger positive responses than mirror positive pushes (asymmetric liquidity replenishment) (arXiv:2511.06177). All results are informational — no transaction-cost overlay is applied.

- **Off-topic note.** None of the six is off-topic; all six touch latency, speed or high-frequency prediction directly. arXiv:1910.03068 is the weakest *engineering* fit (an experimental market-design paper with no code) but supplies the only causal estimate of speed-bump design, and arXiv:2606.09478 is the weakest *latency* fit (a bar-based forecasting study) but supplies the only fully implementable, bar-level pipeline; both are retained for those roles.

## Methods & Formulas

### 2.1 Synchronous actor delivery and the latency-budget decomposition

**Purpose.** Decide whether a latency-critical component can be built with safe (race-free, deadlock-resistant) concurrency, and locate where the microseconds actually go on a live tick-to-book path.

**Formula.** For a feed message with in-packet index $\text{idx}$ and decoder-ring occupancy $q$:
$$\text{median latency} \approx \text{floor} + \text{slope}\times\text{idx} + \Delta(q)$$
with floor $\approx 7\,\mu$s (SBE decode $+$ book apply), slope $312$–$966$ ns/msg, and $\Delta(q)$ convex in $q$ (each additional queued packet costs more than the last). Context-switch count for an $N$-actor servicing chain is $O(N)$ asynchronous vs $O(1)$ synchronous. Synchronous-hop cost:
$$t_{\text{fast\_send}} = t_{\text{lock}} + t_{\text{handler}} + t_{\text{reply}} \approx 10\,\text{ns} \;\;\text{vs}\;\; t_{\text{direct}} \approx 1\,\text{ns}.$$
Amplification $= p_{99}/p_{50}$ measures how tail-heavy a stream is (ES book 1.9$\times$; ZN trade 14.2$\times$).

**Required inputs.** None for the microbenchmark (pure software); a decoded per-packet venue feed for the live path (the paper used CME MDP 3.0 SBE over UDP multicast, ES/NQ/ZN, two redundant channels A/B).

**Parameters & defaults.** Group a servicing stage onto one thread behind one shared mailbox; `BQueue` as default (stable tail, grouped max 2.4–9 µs), `BQueueBatched` for a bursty single producer (584.9 ns/msg), `ShardedBQueue` for 32-producer fan-in ($p_{99}$ 6.6 µs vs 69.9 µs for `BQueue`), `LockFreeMPSC` only for the grouped median (70 ns) at the cost of an unstable tail (14–16 µs grouped max). Pool any message that must outlive the call. Keep cyclic-invocation detection on. Two cross-thread hops are kept deliberately asynchronous (socket-reader → buffer, signal → order-out); everything between is collapsed onto one thread.

**Observed effect sizes.** $3{,}370 \to 90 \to 30$ ns across delivery modes; pool $128 \to 92$ ns amortised and tail max $5.5\,\text{ms} \to 33\,\mu$s; async path 5.5–13.6 M round trips/s after batching+pooling ($\sim 74$ ns saturated, 4–7 µs sparse). Framework contribution $<1\%$ of the 7 µs floor and no measurable association with the tail.

**Failure modes.** `fast_send` holds the receiver's lock for the whole handler, so concurrent synchronous sends to a hot actor serialise and can be *slower* than asynchronous delivery — the sync/async-fallback ratio is the signal to switch. It applies only to co-located actors; a cross-machine synchronous call reintroduces the network round trip. Blocking inside actors risks thread-pool starvation; use `fast_send_x` (bounded, raises `ActorBusy`) or `fast_send_void` (never blocks, async fallback). $t_0$ is a software socket timestamp, so the measurement is socket-to-book, not wire-to-book. Single box, single 53-minute session, and multi-millisecond stalls in the max column remain unexplained.

### 2.2 Low-latency C++ optimisation stack (and where the ring buffer wins)

**Purpose.** Cut per-message CPU time in the hot path without changing strategy logic.

**Formula.** Express each technique as a fractional latency reduction and map the aggregate onto adverse-selection exposure via $E \approx 0.9\,\Delta L$ (Ende et al., 1% latency $\to$ 0.9% exposure):
$$\Delta L_{\text{combined}} = 1 - \prod_k (1 - \delta_k),\qquad \Delta E \approx 0.9\,\Delta L.$$

**Required inputs.** None for the benchmarks; the strategy-side result reuses the pairs-trading pipeline of `../qfin-st/mean-reversion-pairs.md`.

**Parameters & defaults.** Cache warming = a sequential pre-pass over the data before the timed loop; `constexpr` for compile-time constants; compile-time dispatch via templates/overloading; fixed-size arrays instead of dynamic containers; AVX2 SIMD with window sizes a multiple of four; the Disruptor uses a pre-allocated ring buffer with sequence numbers and a configurable wait strategy (the benchmark used *yield-wait*).

**Observed effect sizes.**

| Technique | Baseline (ns) | Latency (ns) | Improvement |
|---|---|---|---|
| Inlining | 517,559 | 406,709 | 21.41% |
| SIMD + loop unrolling | 517,559 | 355,618 | 31.28% |
| Buffer (fixed array) | 517,559 | 266,146 | 48.58% |
| Combined | 517,559 | 65,580 | 87.33% |

Cache warming 267.7 ms $\to$ 25.6 ms; `constexpr` 2.69 $\to$ 0.245 ns/iter; compile-time dispatch 2.60/2.15 $\to$ 1.92 ns. Disruptor vs simple queue at 1,000 events: 74,908 vs 931,255 ns, $t=22.596$, $p=1.243\times10^{-23}$.

**Failure modes.** Benchmark speed is not production speed: the pairs-trading backtest preloaded prices into a `vector`, excludes network latency and live-data anomalies, and assumes window sizes that are multiples of four and AVX2 hardware. The Disruptor advantage grows with event count, so small-event runs *understate* it; conversely the wait strategy (busy-spin vs yield vs sleep) dominates tail latency and was not swept. The strongest evidence in the paper is the *ratio*, not the absolute nanosecond.

### 2.3 Latency-to-adverse-selection cost model and speed-bump simulator

**Purpose.** Price the value of speed and predict how an exchange-level message delay changes traders' incentive to buy low-latency technology.

**Formula.** Speculator $i$ faces a private latency delay $\delta_i$ drawn from an exponential with endogenous rate $\lambda_i = \theta_0 + \beta\,\ell_i/E$ (investment $\ell_i$ of endowment $E$) plus a common bump $\Delta$; the market maker cancels at rate $\lambda_M$ after a bump $\Delta_M$. The first order to arrive wins the arbitrage:
$$P_i(\text{win}) = e^{-\lambda_M \Delta_M}\,\frac{\lambda_i}{\lambda_i+\lambda_{i'}+\lambda_M}.$$
Optimal investment solves the first-order condition $\partial P_i/\partial\lambda_i = C'(\lambda_i)$. With $\Delta_M=0$ (asymmetric bump) the marginal benefit falls in $\Delta$, so investment decreases; with $\Delta_M=\Delta$ (symmetric) the bump cancels, so investment is invariant; a *random* symmetric bump makes $P_i$ convex in the bump, raising the marginal value of speed.

**Required inputs.** Simulation-only: no market data. Reuses the order-arrival model; for a live analogue, top-of-book quotes and a synthetic market-maker cancellation process.

**Parameters & defaults.** $\theta_0=\lambda_M=0.2$ (mean 5 s), three technology tiers $\beta\in\{0.30,0.60,1.80\}$ giving expected arrival times at full investment $\{5,1.25,0.5\}$ s; deterministic delays $\{0,1,3,5\}$ s and randomised delays drawn from $\{0.5,1.5\}$ multipliers; bump sizes small/medium/large; endowment $\{10,20\}$ ECoins; 32 rounds (4 training, discarded); payoff 100 ECoins/win, EC$\to$CAD at 0.50.

**Observed effect sizes.** No-bump 75% of endowment invested $\to$ 66% with any bump; asymmetric $-20.6\%$; symmetric indistinguishable from no-bump (coefficient sum $-0.01$, F-test $p=0.099$); $+1$ SD of bump ($2$ s) $-8.33\%$; small→large $-16.7\%$; low-cost tier $-16.67\%$ vs medium $8.95\%$ / high $1.8\%$.

**Failure modes.** The subjects are students in a single 2.5-hour session, and lab delays are seconds while real bumps are microseconds to milliseconds — magnitude, not mechanism, is what may not transfer. The predicted *random-symmetric* stimulation was **not** confirmed. The market maker is a fixed cancellation process, so no strategic response is modelled. A symmetric bump preserves time priority and therefore cannot curb the arms race by construction; do not simulate it as if it might.

### 2.4 Push-response surface: lag-resolved conditional response of returns

**Purpose.** Test and, cautiously, monetise the conditional response of a forward return to a standardised backward move, per lag and per magnitude, without relying on unconditional autocorrelation.

**Formula.** For event-time mid prices and lag $L$:
$$p_t(L)=m_t-m_{t-L},\qquad r_t(L)=m_{t+L}-m_t,$$
$$z_p=\frac{p_t-\mu_p(L)}{\sigma_p(L)},\qquad z_r=\frac{r_t-\mu_r(L)}{\sigma_r(L)}.$$
Bin $z_p$ and estimate $\bar z_r(L,z_p)=E[z_r\mid z_p,L]$. Decompose into symmetric (magnitude) and antisymmetric (sign) parts, with a support-weighted dominance index:
$$S(L,|j|)=\tfrac12\big[\bar z_r(L,+j)+\bar z_r(L,-j)\big],\qquad A(L,|j|)=\tfrac12\big[\bar z_r(L,+j)-\bar z_r(L,-j)\big],$$
$$\rho(L)=\frac{\sum_j w(L,|j|)\,|A|-\sum_j w(L,|j|)\,|S|}{\sum_j w(L,|j|)\,|A|+\sum_j w(L,|j|)\,|S|},\qquad M(L)=\sum_j w(L,|j|)\frac{|\bar z_r(L,+j)|+|\bar z_r(L,-j)|}{2}.$$
$\rho(L)>0$ means sign-conditioned drift dominates; $\rho(L)<0$ means pure magnitude adjustment.

**Required inputs.** Event-time mid-price increments (from NBBO or any quote/trade tape), with all three anchors $t-L,t,t+L$ in the same session. On bars, the same object is built from bar-close increments but is a *different* object (lag counted in bars, not events).

**Parameters & defaults.** Winsorise the 0.001% tails and drop $|m_t-m_{t-1}|>\$1.50$; standardised grid $z_p\in[-4,4]$, $\Delta z=0.025$ ($N=320$ bins); minimum bin support $n_{\min}=200$; short lags $L\in\{1\}\cup\{50,100,\dots,5000\}$ and long lags $L\in\{1000,\dots,500000\}$; 95% bootstrap bands over support-weighted bin pairs.

**Observed effect sizes.** Short lags: responses near zero across most pushes (near-efficiency). Structure switches on past $|z_p|\approx 1$; the ridge is densest for $|z_p|\in[1.3,3]$; antisymmetry dominates the mid band, symmetry the extremes; $M(L)$ rises then plateaus; negative pushes map to stronger positive responses than mirror positive pushes (fundamental asymmetry).

**Failure modes.** No transaction-cost overlay, so a "tradable pocket" is not a strategy until costs are subtracted. Responses are in standardised units and must be de-normalised per lag. The same-session constraint trims tail bins hardest at large $L$. With billions of anchors and hundreds of bins, central bins are stable but wings are not; enforce $n_{\min}$ and never impute. Applying it to bars loses the event-time semantics the paper relies on.

### 2.5 Regime-augmented HARQ volatility with a low-volatility-gated return signal

**Purpose.** Forecast realised volatility robustly, weakly forecast the next-day return, and convert the weak forecast into a defensive, cost-aware allocation.

**Formula.** Realised variance and its higher moments:
$$RV_t=\sum_{i=1}^{M_t} r_{t,i}^2,\qquad RQ_t=\frac{M_t}{3}\sum_{i=1}^{M_t} r_{t,i}^4,\qquad CJ_t=\max(RV_t-BPV_t,0),\qquad \text{SignedJump}_t=CJ_t\cdot\text{sign}(r_t).$$
HARQ in logs, augmented by the filtered high-volatility probability $p_t$:
$$\log(RV_t)=\beta_0+\beta_1\log RV_{t-1}+\beta_2\log RV_{t-5:t-1}+\beta_3\log RV_{t-22:t-1}+\beta_4\log RQ_{t-1}+\gamma p_t+\varepsilon_t.$$
The regime is identified from the HARQ residuals by a two-state Markov-switching GJR-GARCH:
$$\sigma_t^2=\omega_{S_t}+\alpha_{S_t}\varepsilon_{t-1}^2+\gamma_{S_t}\mathbf 1(\varepsilon_{t-1}<0)\,\varepsilon_{t-1}^2+\beta_{S_t}\sigma_{t-1}^2,\qquad \varepsilon_t=\sigma_t z_t,\; z_t\sim t_\nu,$$
with $p_t=P(S_t=\text{high-vol}\mid F_t)$ **filtered**, never smoothed. Return prediction is XGBoost on twelve predictors; the trading signal is:
$$s_t=\frac{\hat r_{t+1}}{\exp(\widehat{\log RV}_{t+1})},\qquad s_t^G=\begin{cases}s_t & p_t\le0.5\\ \kappa s_t & p_t>0.5\end{cases},\qquad \tilde s_t=\begin{cases}s_t^G & |s_t^G|\ge Q_{WF,q,t}\\ 0 & \text{else}\end{cases},$$
$$w_t^*=\min\{\max\{c_t^{WF}\tilde s_t,\,-w_{\max}\},\,w_{\max}\},\qquad w_t=\begin{cases}w_{t-1} & |w_t^*-w_{t-1}|<b\\ w_t^* & \text{else}\end{cases}.$$

**Required inputs.** 5-minute intraday prices (for $RV,RQ,CJ$), daily close returns, and the filtered regime probability from the same pipeline. All predictors at time $t$, target $r_{t+1}$.

**Parameters & defaults.** $q=0.60$ (retain strongest 40% of signals), no-trade band $b=0.02$, $w_{\max}=0.6$, target mean absolute exposure $0.5$, weekly rebalancing, quarterly re-estimation, one-way cost 5 bp, $N_{\min}=300$ with 180 train / 120 validation, XGBoost grid $\{$300 estimators, depth $\{2,3\}$, lr $\{0.03,0.05\}$, $\gamma\in\{0,0.1\}$, $\lambda\in\{1,2\}\}$, quarterly probability re-estimation.

**Observed effect sizes.** HARQ$+p_t$ improves MSE-log, QLIKE and LMAE (0.267345/0.162259/0.402701 vs 0.279911/0.171013/0.410499), Mincer–Zarnowitz $R^2$ 0.5398 vs 0.5215, with conditional DM gains significant in high-volatility subsamples. Return prediction: full-sample correlation 0.0449, hit 53.49%; low-vol 0.0638/53.77%; high-vol $-0.0617$/insignificant. Strategy net of 5 bp: ARC 1.93%, ASD 7.56%, Sharpe 0.255, Sortino 0.394, MaxDD $-14.52\%$ vs $-50.60\%$ buy-and-hold, long 20.66% / short 12.57% / neutral 66.77% of days; block-bootstrap $p=0.182$ (economically suggestive, not statistically strong). 2015–16 crash: $+10.24\%$ vs $-39.38\%$; post-COVID 2021–23: $-0.12\%$ vs $-30.11\%$.

**Failure modes.** $\widehat{\log RV}_{t+1}$ is a *generated regressor*: first-stage estimation error propagates into the second stage. Smoothed probabilities would leak future information — use filtered only. The 5 bp cost is one-way and ignores market impact and liquidity. The Chinese market imposes T+1 settlement and short-sale constraints that a paper long/short backtest ignores. The strategy is defensive (risk reduction), not an alpha engine; multiple-testing procedures (White Reality Check, Hansen SPA) are required before any "best" configuration is believed.

### 2.6 GPU-parallel MARL HFT environment and its production/simulation duality

**Purpose.** Learn interacting policies (market-making, execution, directional) directly on market-by-order data, and reuse one deterministic engine for both live trading and backtest.

**Formula.** Independent PPO with separate networks per agent type. Performance proxies and rewards:
$$PV=Q_{inv}P_{ref}+Cash,\qquad \text{Slippage}=\sum_j(-1)^{dir}Q_j(P_j-P_{init}),$$
$$\Psi_b=(\bar M-P_b)Q_b,\;\; \Psi_s=(P_a-\bar M)Q_a,\;\; \Psi_{INV}=I_t(M_t-M_{t-1}),$$
$$r_{Sp}=\Psi_b+\Psi_s+\Psi_{INV}-(1-\lambda)\max(0,\Psi_{INV}),\qquad r_{buy\text{-}sell}=\Psi_b+\Psi_s.$$
A group of actors sharing one mailbox imposes a single total order on all messages, so a handler cannot tell a live socket from a replay file (receiver transparency extended to the data source).

**Required inputs.** Market-by-order (MBO) message streams — LOBSTER-style tick data with order type and timestamp; the paper uses AMZN 2024.

**Parameters & defaults.** Episode length 64 steps, episode start every 64 steps, 100 data messages/step, JAX-LOB book capacity 100 orders, agent order size 10, execution task size 600, end-of-episode penalty $\{0.1,0.05,0.01\}$, market-making quadratic inventory penalty $\rho=50$, GRU recurrent networks, 4,096 parallel environments on one GPU.

**Observed effect sizes.** Up to $240\times$ end-to-end training speed-up; 21,969 steps/s (100 messages/step) vs 463 (PyMarketSim), 734 (ABIDES), 1,805 (CPU-MARL); one year of AMZN data ($\approx 400$ M orders) in 4 GB GPU memory. Learned execution agent cuts cost by up to 20% of a tick vs TWAP; learned market makers lose $\approx 0.2$ ticks on average.

**Failure modes.** The learned market maker loses largely because its resting orders are cancelled at *every* RL step, destroying time priority — a simulator artefact, not a market property. Rewards not normalised by volume admit the degenerate "never trade" policy (observed). Heterogeneous agents force an outer Python loop over agent types with `vmap` inside a type only; padding would be wasteful. MBO data is a **gap** for FinRobot (§3) and without it this is a synthetic-only component. Train and evaluate on *different* simulator seeds.

## Data Requirements

Rows below are real entries copied from `strategies/endpoints.json`; **gap** in bold means no current provider serves the input.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (daily returns, $\sigma_D$ proxy) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily/previous aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Daily OHLCV (tertiary) | `https://api.stockdata.org/v1/data/eod` | `core_stock_apis` | stockdata | ok |
| Intraday 5-min bars ($RV,RQ,CJ$, HARQ, push-response) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Intraday technical indicators / bars | `https://www.alphavantage.co/query` | `technical_indicators` | alpha_vantage | ok |
| Intraday K-line via local OpenD gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Top-of-book snapshot (best bid/ask only) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Tradable symbol universe / tick sizes | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| **Tick / NBBO event stream (event-time pushes)** | — | — | — | **gap** |
| **Market-by-order (MBO) message stream (LOBSTER-style)** | — | — | — | **gap** |
| **L2/L3 book depth (≥3 ranks)** | — | — | — | **gap** |
| **Hardware receive timestamps / colocation feed (wire-to-book)** | — | — | — | **gap** |

**What the gap costs, quantified.** The push-response paper needs $\approx 2.6\times10^9$ NBBO events over $\approx 1{,}512$ days — event time, not bars, with a same-session constraint that halves the usable tail bins; a bar-level substitute changes the conditioning variable from events to bars and destroys the lag semantics. The actor-latency paper needs a per-packet decoded venue feed at socket timestamp resolution (8.29 M messages in 53 minutes, $p_{99.9}$ up to $410$ µs); a daily or minute bar carries none of the in-packet/slope structure. JaxMARL-HFT needs one year of MBO messages ($\approx 400$ M orders, 4 GB) and cannot be trained on aggregate bars at all. The `moomoo` gateway row is a top-of-book snapshot only and is not live-probed, so even the coarsest quote-based analogue is unverified. Consequence: techniques §2.1, §2.3, §2.6 are simulation-only or blocked, §2.4 is approximate on bars, and §2.2 and §2.5 are the only ones implementable end-to-end on today's endpoints.

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Look-ahead / leakage.** Use *filtered* regime probabilities, never smoothed (arXiv:2606.09478); all predictors at $t$, target at $t+1$; expanding-window walk-forward with quarterly re-estimation and no random train/test splits. The push-response construction must keep $t-L,t,t+L$ within one session (arXiv:2511.06177).
- **Generated-regressor bias.** The return model's main feature $\widehat{\log RV}_{t+1}$ is itself estimated; its contribution inherits first-stage error, so ablation must strip the volatility forecast to test whether it adds value (arXiv:2606.09478).
- **Benchmark ≠ production.** Backtest latency is measured with prices preloaded into memory and excludes network/live anomalies; a "90% faster" benchmark is not a 90% faster system (arXiv:2309.04259). The live path is socket-to-book, not wire-to-book, and a single session (arXiv:2609.21173).
- **Median vs mean, and the tail.** A single multi-millisecond stall moves a cell mean by tens of microseconds, so report medians/percentiles, $p_{99}$ and $p_{99.9}$, and the median-to-$p_{99}$ amplification — never an average latency (arXiv:2609.21173).
- **Metric choice.** Directional accuracy must be HAC-corrected, not a binomial test; report rolling Information Coefficients and ICIR because predictability is episodic (arXiv:2606.09478). For forecasts use QLIKE in addition to MSE/LMAE (it penalises under-prediction and is robust to $RV$ as an imperfect proxy).
- **Multiple testing.** The Chinese study restricts its hyperparameter grid, reports a $q\times b$ sensitivity sweep, and applies White Reality Check / Hansen SPA to guard against data snooping; any "best configuration" without such a correction is selected on noise (arXiv:2606.09478).
- **Cost assumptions.** 5 bp one-way with no impact (arXiv:2606.09478); a push-response "pocket" has no cost overlay at all (arXiv:2511.06177). Passive orders carry the negative drift of a fill — see [`../qfin-st/microstructure-execution.md`](../qfin-st/microstructure-execution.md) — so "passive $=$ free" is false in every one of these strategies.
- **Regime dependence.** Return predictability concentrates in low-volatility states and is unstable (even negative) in high-volatility states (arXiv:2606.09478); the latency tail is driven by clustered, non-Poisson arrivals, not by the messaging layer (arXiv:2609.21173); speed-bump effects differ by technology tier (arXiv:1910.03068). Condition or re-calibrate; never report an unconditional average as an invariant.
- **Simulator fidelity.** The MARL market maker loses because the environment cancels its resting orders every step — a design artefact, so results transfer only after the environment honours time priority; validate on a different seed than training and do not compare replay-based RL P&L with simulator P&L (arXiv:2511.02136).
- **Experiment power.** The speed-bump result rests on 56 students in one session; report three-way clustered standard errors and treat the negative result for random-symmetric bumps as informative, not noise (arXiv:1910.03068).

## Recommended Workflow

Ranked by value against what the data layer can fetch today. Items 1–4 are buildable now; items 5–7 are simulation-only (no market data required); item 8 is blocked on a feed and should be built only as simulator-side code.

1. **Regime-augmented HARQ volatility forecaster.** *What:* log-HARQ $+$ filtered MS-GJR-GARCH-t high-volatility probability, walk-forward, QLIKE/MSE/LMAE scored. *Data:* twelvedata `time_series` 5-min bars $+$ eodhd daily close. *Pass:* HARQ$+p_t$ beats baseline HARQ on QLIKE out of sample and the Mincer–Zarnowitz $R^2$ improves, reproducing the paper's direction (arXiv:2606.09478). *Effort:* M.
2. **Low-volatility-gated defensive scheduler.** *What:* the $s_t\to s_t^G\to\tilde s_t\to w_t$ chain with $q=0.60$, $b=0.02$, $w_{\max}=0.6$, weekly rebalance and 5 bp cost. *Data:* item 1's output $+$ daily bars. *Pass:* lower maximum drawdown than buy-and-hold over the out-of-sample window, with the long/short/neutral exposure shares in the paper's range; do **not** expect a statistically strong Sharpe. *Effort:* M.
3. **Latency-budget model and simulation clock.** *What:* a `median $\approx$ floor $+$ slope$\times$idx` estimator plus a deterministic single-queue event clock (the actor group's production/simulation duality, arXiv:2609.21173). *Data:* none. *Pass:* on a synthetic feed it reproduces the floor/slope shape and the $p_{99}$ amplification, and the same strategy code runs live and in replay without branching. *Effort:* M.
4. **Push-response surface on bar-level increments.** *What:* the standardised lag-$\times$magnitude surface with the symmetric/antisymmetric decomposition and dominance index. *Data:* twelvedata minute bars (or eodhd daily) — substitute bars for NBBO events and label the result as an approximation. *Pass:* antisymmetry $\rho(L)>0$ over a mid-lag band with bootstrap bands excluding zero, *before* costs; report it as an informational microstructure diagnostic, not a strategy (arXiv:2511.06177). *Effort:* M.
5. **Synchronous-delivery / low-latency microbenchmark harness.** *What:* port `fast_send`-style inline dispatch, actor grouping, per-actor mailbox selection and a message pool; benchmark pinned on the target CPU. *Data:* none. *Pass:* a bounded tail (no multi-millisecond pool stall) and $<1\%$ overhead versus a direct-call baseline. *Effort:* M.
6. **Disruptor-style ring buffer in the OMS path.** *What:* a pre-allocated, sequence-numbered ring buffer replacing a mutex queue for inter-thread event handoff; map the latency gain to adverse-selection exposure via $E\approx0.9\Delta L$. *Data:* none. *Pass:* lower $p_{99}$ inter-thread latency than a queue at $\ge10^3$ events, with the advantage increasing in event count (arXiv:2309.04259). *Effort:* M.
7. **Speed-bump simulator.** *What:* port the lab protocol (three technology tiers, symmetric/asymmetric $\times$ deterministic/random bumps) and confirm the three hypotheses. *Data:* none. *Pass:* 75%$\to$66% overall, asymmetric $-20\%$, symmetric $\approx$ no-bump (arXiv:1910.03068). *Effort:* S.
8. **GPU MARL environment — blocked.** *What:* a JaxMARL-HFT-style MBO multi-agent environment with the production/simulation duality. *Data:* market-by-order feed — **gap**; prototype only against synthetic or LOBSTER-licensed data. *Value:* the only route to policies that learn against reacting counterparts; without an MBO feed it stays synthetic. *Effort:* L.

## Output Format

### Latency Budget Decomposition
| Component | Estimate | Basis |
|-----------|----------|-------|
| Floor (per packet, first message) | ... | SBE decode + book apply |
| Slope (per in-packet message) | ... | ns/msg against in-packet index |
| Queue-occupancy term $\Delta(q)$ | ... | convex in decoder-ring occupancy |
| Framework share of floor | ... | must be <1% to claim transparency |

### Tail and Amplification
| Stream | p50 | p99 | p99.9 | max | p99/p50 amplification |
|--------|-----|-----|-------|-----|-----------------------|
| ES book | ... | ... | ... | ... | ... |
| ZN trade | ... | ... | ... | ... | ... |

### Verdict
State whether the framework is under 1% of the floor and unassociated with the
tail, whether the tail is feed-driven (in-packet position and queue occupancy)
rather than messaging-layer overhead, the service cost (slope) as the design
lever, and the measurement caveats: medians/percentiles over means, socket-to-book
(not wire-to-book), and single-session evidence. Where a live feed is unavailable,
report the simulation-clock microbenchmark result and name the tick/NBBO/MBO gap
instead of extrapolating latency from bars.

## References

| arXiv id | Title | Year |
|---|---|---|
| 2609.21173v1 | Adapting the Actor Model of Concurrency for High-Frequency Trading: Synchronous Message Delivery (fast_send) and a Tick-to-Book Latency Study | 2026 |
| 1910.03068v1 | Do speed bumps curb low-latency trading? Evidence from a laboratory market | 2019 |
| 2309.04259v1 | C++ Design Patterns for Low-latency Applications Including High-frequency Trading | 2023 |
| 2511.02136v1 | JaxMARL-HFT: GPU-Accelerated Large-Scale Multi-Agent Reinforcement Learning for High-Frequency Trading | 2025 |
| 2606.09478v1 | Volatility Forecasting and Return Prediction under Market Regimes: Evidence from High-Frequency Chinese Equity Data | 2026 |
| 2511.06177v1 | Push-response anomalies in high-frequency S&P 500 price series | 2025 |
