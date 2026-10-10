# Microstructure & Execution — learnings from the q-fin.ST corpus

`600` of 4372 corpus papers matched this category (514 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category has no support in the current data layer.** Not one of the 33 routing
categories in `finrobot/engine/data/categories.py` exposes a limit-order-book, an order-level event
stream, or a signed trade tape, and no endpoint in `strategies/endpoints.json` serves depth or
order-flow (`moomoo://get_market_snapshot` is a top-of-book snapshot behind a local gateway). Every
technique below needs at minimum L2 depth and signed trades; the strongest ones need full L3
market-by-order. The doc therefore separates (a) what can be *estimated* from the coarsest data
FinRobot can actually fetch, and (b) what is **simulation-only** until a book feed is added.

## 1. What the corpus actually offers

- **The square-root law (SRL) of market impact, reproduced from anonymous Nasdaq TotalView-ITCH
  data alone.** \\(I/\sigma_D = c\,(Q/V_D)^{1/2}\\) with the exponent *fixed* at the universal
  \\(1/2\\), fitted \\(c_{\rm raw}=0.69\\) (95% CI \\([0.64,0.75]\\)), bias-corrected
  \\(c_{\rm eff}=c_{\rm raw}/2=0.34\\); free-exponent estimate \\(\hat\delta=0.50\\) with bootstrap
  CI \\([0.32,0.66]\\) that excludes the linear case \\(\delta=1\\). Metaorder size tail
  \\(P(Q)\propto Q^{-\beta-1}\\) with \\(\beta=1.54\pm0.15\\) (arXiv:2606.24019).
- **Functional form is decisive, not marginal:** sqrt impact (\\(R^2=0.95\\)) beats linear
  (\\(R^2=0.20\\)) by \\(\Delta{\rm AIC}=22\\) and logarithmic by \\(\Delta{\rm AIC}=5\\) on the same
  log-binned data; log-bin means rise \\(0.026\to0.056\\) across four bins in near-exact
  \\(Q^{1/2}\\) proportion (arXiv:2606.24019).
- **Two structural null tests isolate the mechanism:** shuffling aggressor signs (timestamps held
  fixed, \\(N=10^4\\)) collapses directional alignment from 85.9% to a 49.6% null (\\(z=23\\),
  \\(p<10^{-4}\\)); scrambling event chronology destroys the law entirely (0 of 80 scrambled
  calibrations viable) (arXiv:2606.24019).
- **Preconditions are observable:** aggressor-sign autocorrelation decays as \\(C(\ell)\propto
  \ell^{-\gamma}\\) with \\(\gamma=0.66<1\\) (long-memory flow) while the mid-price variance ratio
  stays in \\([0.91,1.04]\\) from 10 s to 5 min (Hurst 0.49) — predictable flow coexisting with a
  diffusive price is exactly what the universality theories require (arXiv:2606.24019).
- **A Hawkes-type duration law with heavy-tailed residuals.** A self-exciting, exponentially
  decaying *flexible-residual* point process, \\(\Lambda_n=\mu+(\Lambda_{n-1}-\mu+\alpha)e^{-\beta
  \tau_n}\\), is ergodic and positive Harris recurrent under \\(\alpha<\beta\mu_\varepsilon\\), with
  stationary mean duration \\(E[\tau_n]=(\beta\mu_\varepsilon-\alpha)/(\beta\mu)\\). Fitting
  non-exponential residuals (Gamma \\(\kappa\approx0.35\\), Burr XII) shrinks KS/W goodness-of-fit
  statistics by roughly a factor of 2–25 versus an exponential/Hawkes residual, though point-forecast
  rRMSE barely moves (arXiv:2604.00346).
- **AAPL one-tick mid-price durations are violently over-dispersed:** 1,023,480 durations in Dec
  2022, mean 0.4801 s vs median 0.1281 s, SD 0.9937 s, skew 5.75, kurtosis 61.5, over-dispersion
  SD/mean 2.0698 (arXiv:2604.00346).
- **Limit-order fills carry a *negative drift*: they coincide with adverse mid-price moves.** In a
  minimal discrete model, \\(E_t[d_t\mid f]=(R_fP(U)-P(D))/P(f)<0\\) for a buy limit order whenever
  \\(R_f<1\\); the same result holds in a general compound Hawkes (GCHP) formulation. Live-simulated
  10Y T-bond futures gave an average post-fill drift of \\(-0.0065\\), i.e. \\(\approx\tfrac12\\) tick
  (\\(\tfrac12\\) tick \\(=0.0078125\\)), the *same* penalty as crossing the spread with a market
  order (arXiv:2407.16527).
- **Microprice as a recursive conditional-expectation estimator.** Stoikov's microprice
  \\(P_{\rm micro}=M+g(I,S)\\) with \\(g_1(I,S)=E[M_{\tau_1}-M_t\mid I_t=I,S_t=S]\\) and
  \\(g_{i+1}(I,S)=E[g_i(I_{\tau_1},S_{\tau_1})\mid I_t=I,S_t=S]\\), convergent when \\(B^*G_1=0\\).
  Adding higher-rank book features (volume proportions at ranks \\(1..L\\)) cut the \\(L_2\\) price
  error by ~10–20% on a blue chip (TSLA), less on a small cap (TEM) (arXiv:2411.13594).
- **Execution is an allocation over the simplex, and RL beats heuristics.** Logistic-normal
  actor-critic allocating inventory across market orders and limit orders at 1..K ticks returned
  \\(1.13\\) ticks/lot vs TWAP's \\(-0.36\\) and submit-and-leave's \\(-1.64\\) in a market with a
  strategic trader, and beat a Dirichlet-policy RL baseline almost everywhere (arXiv:2507.06345).
- **LOB event streams are a joint (time, type) distribution and a diffusion model beats neural
  Hawkes.** LOBDIF decomposes that joint distribution into \\(K\\) Gaussian steps and reaches
  event-type accuracy 0.44–0.52 vs 0.33–0.37 for a stochastic Hawkes and 0.44–0.47 for PCT-LSTM,
  at 1.4–1.9 ms/step after skip-step sampling (arXiv:2412.09631).
- **Off-topic note:** none of the six is off-topic; arXiv:2412.09631 is the weakest fit (it is
  event-stream *forecasting*, not execution) but it supplies the only generative model of the
  order-flow process in the set and is retained for that role.

## 2. Implementable formulas & algorithms

### 2.1 Square-root impact calibration and cost model
**Purpose.** Predict the temporary price move of a metaorder before sending it, and turn that into a
pre-trade cost in ticks.

**Formula.**
$$I = \varepsilon\,(m_{\text{end}}-m_{\text{start}}),\qquad
\frac{I}{\sigma_D}=c\left(\frac{Q}{V_D}\right)^{\delta},\qquad \delta=\tfrac12 $$
where \\(\sigma_D\\) is a daily volatility scale (the paper uses the Parkinson high–low estimator of
the mid) and \\(V_D\\) the daily volume. Equivalently a *child-order* law: mean impact vs log
child-fill count \\(L\\) has slope 0.62. Size tail \\(P(Q)\propto Q^{-\beta-1}\\), \\(\beta\approx1.5\\).

**Required inputs.** Signed executions grouped into parent orders; per-execution mid price; daily
\\(\sigma_D,V_D\\).

**Parameters & defaults.** Exponent fixed at \\(\tfrac12\\) (do **not** fit it on one name);
\\(c\\) by *relative* least squares (\\(\min\sum(\hat I-I)^2/\hat I^2\\)) on log-spaced bins of
\\(\ge100\\) metaorders; tail \\(\beta\\) by Hill with a KS-optimal cutoff. Reported \\(c\\) range
across 9 reconstruction settings \\([0.63,0.77]\\), cross-sectional band \\([0.5,1.0]\\).
Metaorder reconstruction defaults: 30 s bins, imbalance-dominance threshold 0.3, keep runs of
duration \\(\ge60\\) s and size \\(\ge10\,V_D\\).

**Observed effect sizes.** \\(R^2=0.95\\) (sqrt) vs 0.20 (linear); \\(\Delta{\rm AIC}=22\\) vs
linear, \\(+5\\) vs log. 32 weekly walk-forward recalibrations: \\(c\in[0.63,1.01]\\) (mean 0.75).
Non-dimensional impact \\(0.026\to0.056\\) across bins.

**Failure modes.** Fitting \\(\delta\\) on a single name over ~20 days is unidentifiable (CI
\\([0.32,0.66]\\)); anonymous reconstruction inflates \\(c\\) by ~2× (use \\(c_{\rm raw}\\) as an
upper bound); power law is statistically indistinguishable from lognormal; hidden/cross prints
(~19% incl. auctions) need a tick rule to sign; auction crosses \\(\ge50{,}000\\) shares must be
dropped.

### 2.2 Self-exciting flexible-residual duration / intensity model
**Purpose.** Forecast the elapsed time to the next mid-price (one-tick) move and, via the intensity,
when to expect order-flow bursts.

**Formula.** With i.i.d. heavy-tailed innovations \\(\varepsilon_n\\) and transform \\(\Phi\\),
$$\tau_n=\Phi^{-1}(\varepsilon_n,\Lambda_{n-1}),\qquad
\Lambda_n=\mu+(\Lambda_{n-1}-\mu+\alpha)e^{-\beta\tau_n}=\Lambda_{n-1}+\alpha-\beta\varepsilon_n+\beta\mu\tau_n$$
$$\Phi(t,x)=\mu t+(x-\mu+\alpha)\frac{1-e^{-\beta t}}{\beta},\qquad
\lambda_{n-1}(t)=h_\varepsilon\!\big(\Phi(t,\Lambda_{n-1})\big)\,\Psi(t,\Lambda_{n-1})$$
Reduces to the exponential Hawkes process when \\(\varepsilon\\) is unit-exponential (\\(h_\varepsilon\equiv1\\)).
Log-likelihood \\(\ell_n=\log f_\varepsilon(\Phi(\tau_n,X_{n-1}))+\log\Psi(\tau_n,X_{n-1})\\).
Stationary mean duration \\(E[\tau_n]=(\beta\mu_\varepsilon-\alpha)/(\beta\mu)\\).

**Required inputs.** A point process of event times — here, timestamps of successive one-tick
mid-price moves (each needs two consecutive same-direction half-tick mid changes).

**Parameters & defaults.** Stability \\(\alpha<\beta\mu_\varepsilon\\); persistence controlled by
\\(\alpha/\beta\\) (simulation uses \\(\alpha/\beta=0.95\\) vs \\(0.70\\) at \\(\beta=0.1\\)). Residuals:
Gamma (\\(\kappa\approx0.35\\)), generalized Gamma (\\(d\approx0.33\\),\\(p\approx1.25\\)), or Burr XII
(\\(s_1\approx270\\),\\(s_2\approx0.48\\)), all rescaled to \\(E[\varepsilon]=1\\). Rolling window:
re-estimate on the last 5,000 events (~45 min) and forecast the next 100.

**Observed effect sizes.** SE-Gamma raises \\(R^2\\) from 0.078 (SE-Exp/Hawkes) to 0.137 and drops
KS from 0.138 to 0.051; ACD-Gamma gets KS 0.024 and Wasserstein 0.0002. SE-Burr best rRMSE in the
self-exciting class (1.803 vs 1.839 for SE-Exp). Exponential residuals inflate \\(\mu,\alpha,\beta\\)
by ~an order of magnitude (SE-Exp \\(\alpha=90.96\\) vs SE-Gamma \\(\alpha=0.094\\)) — a diagnostic
that the residual family is wrong.

**Failure modes.** Non-exponential kernels lose the finite-state Markov property (only the
exponential kernel admits the elapsed-time representation); ACD-type models are highly persistent
(\\(a+b_1\approx1\\), near unit root); forecasting *point* accuracy is weak everywhere (best
\\(R^2\approx0.14\\)) even when distributional fit is good — use it for intensity/timing features, not
for price direction.

### 2.3 Negative drift of a limit-order fill (fill-aware backtester)
**Purpose.** Stop backtests from assuming limit orders escape the spread cost; make passive fills
carry the adverse move they are correlated with.

**Formula.** Discrete model with events \\(U,M,D\\) (\\(+1,0,-1\\) tick) and fill probabilities
\\(P(f\mid M)=P(f\mid U)=R_f<1\\), \\(P(f\mid D)=1\\):
$$P(f)=P(D)+R_f\big(P(M)+P(U)\big),\qquad
E_t[d_t\mid f]=\frac{R_fP(U)-P(D)}{P(f)}<0$$
For sell limit orders the sign flips. GCHP form:
$$E_t[d^h_t\mid f]=\frac{R_f\big(Q(U)P(U|U)+Q(D)P(U|D)\big)-\big(Q(U)P(D|U)+Q(D)P(D|D)\big)}{P(f)}<0.$$

**Required inputs.** Best bid/ask and mid at event granularity, plus knowledge of which price
levels are queue-active (for the fill logic).

**Parameters & defaults.** Calibrated on 1 s resampled TY futures: \\(P(U)=P(D)=0.0173\\),
\\(P(M)=0.965\\), \\(R_f=0.018\\), \\(P(f\mid D)=0.99\\). Predicted drift \\(-0.48\\) ticks vs empirical
\\(-0.45\\); fills over 100-event windows.

**Observed effect sizes.** Average post-fill drift \\(-0.0065\\) vs \\(\tfrac12\\) tick
\\(=0.0078125\\) — the passive order earns ~1/2 tick of edge and then pays ~1/2 tick of adverse
move. In a matched backtest (same TY Mar24 day, 576,670 events) the adverse-fill+Bernoulli rule
reproduced the live P&L path far better than 100%-fill (13,935 orders/85% fill) or exponential-fill
(3,785 orders/30% fill); the proposed rule gave 3,459 orders/65% fill vs live 3,305/60%.

**Failure modes.** Fill inter-arrival times are heavy-tailed (Pareto-like), *not* exponential — an
exponential-fill backtester under-fills by ~2× and flatters the strategy; a machine-learning
short-alpha signal correlates only 15–25% with the next move, so it cannot dodge the drift;
alternative backtesters that stop at the spread move ("the agent always moves its quote in time")
are provably wrong when the price jumps a full tick.

### 2.4 Microprice and higher-rank imbalance correction
**Purpose.** Produce a sub-spread fair-value estimate to price (or cancel) passive orders.

**Formula.** Mid \\(M=(P_b+P_a)/2\\), imbalance \\(I=Q_b/(Q_b+Q_a)\\),
$$P_{\rm micro}=M+g(I,S),\qquad g_1(I,S)=E[M_{\tau_1}-M_t\mid I_t=I,S_t=S]$$
$$g_{i+1}(I,S)=E\big[g_i(I_{\tau_1},S_{\tau_1})\mid I_t=I,S_t=S\big]$$
Estimated from transition matrices \\(Q\\) (no mid change), \\(T\\) (mid change) and \\(R\\) (mid-change
distribution): \\(G_1=({\bf 1}-Q)^{-1}RK\\), \\(B=({\bf 1}-Q)^{-1}T\\),
\\(G^*=\sum_{i\ge0}B^iG_1\\). Symmetrize each observation
\\((I_t,S_t,I_{t+1},S_{t+1},\Delta M)\mapsto(1-I_t,S_t,1-I_{t+1},S_{t+1},-\Delta M)\\) so that
\\(B^*G_1=0\\).

**Required inputs.** Top-of-book bid/ask prices and sizes (for \\(M,I,S\\)), plus at least a few
higher price ranks of depth for the correction features
\\(F=(P_{A,1..L},P_{B,1..L},S,\Delta M,G^*)^\top\\) with \\(P_{A,i}=A_i/V_{\rm total}\\),
\\(P_{B,i}=B_i/V_{\rm total}\\).

**Parameters & defaults.** Rank depth \\(L\\) (≥3 used); the correction is learned as a classifier
over tick adjustments \\(\{-2,-1,0,+1,+2\}\\); labels are the future mid price after \\(s\\) events
(tick/volume/dollar bars), measured in ticks from the current microprice. Tsetlin encoder: sparse
binary hypervectors of dimension \\(N\\), bind = segment-wise circular rotation, bundle = majority.

**Observed effect sizes.** \\(L_2\\) error \\(\sqrt{T^{-1}\sum(\hat P_{{\rm micro},t}-P_{t+N})^2}\\)
improves ~10–20%: TSLA 0.0619 (SD 0.0149) vs 0.0925; 0.0326 (0.0091) vs 0.0375. TEM (small cap)
much weaker: 0.1630 vs 0.1723, and worse with wide spreads. Gains concentrate when spreads are
tight and imbalance is near zero.

**Failure modes.** The recursion needs enough historical top-of-book states and converges fast but
requires volume; on wide-spread, illiquid names the higher-rank signal is contaminated by
spoofing/flickering orders, so the correction can hurt; everything is at microsecond–millisecond
latency, useless if evaluated on 1-minute bars.

### 2.5 RL execution with market *and* limit orders (logistic-normal actor-critic)
**Purpose.** Learn an order-placement policy (how much to cross, how deep to post, how much to hold)
rather than a coarse "trade X% now" schedule.

**Formula.** State = (best bid/ask; first \\(K-1\\) volume levels each side; market/limit/cancel
order-flow imbalances \\(\Delta^M,\Delta^L,\Delta^C\\); mid-price drift \\(\Delta p\\); private:
time, remaining inventory \\(M(t)\\), number of resting orders \\(m(t)\\), level+queue position
\\((l^i,q^i)\\)). Action \\(a\in S^K\\): \\(a^0\\) = fraction sent as a market order, \\(a^k\\) =
fraction posted \\(k\\) ticks above the best bid, \\(a^K\\) = fraction withheld. Policy is
logistic-normal on the simplex,
$$a^k=\frac{e^{x^k}}{1+\sum_{l=0}^{K-1}e^{x^l}},\qquad
a^K=\frac{1}{1+\sum_{l=0}^{K-1}e^{x^l}},\qquad
\nabla_\theta J=E\!\left[\sum_n A^{\pi_\theta}(s_n,a_n)\nabla_\theta\log\varphi_\theta\big(h^{-1}(a_n)\mid s_n\big)\right]$$
Reward = normalized **implementation shortfall**, average revenue per lot relative to the initial
best bid: \\(r(s_n,a_n)=(\bar r(s_n,a_n)-\gamma_n p^b(0))/M\\), with forced terminal liquidation.
Advantage estimated with GAE \\(\lambda^{\rm GAE}=1\\).

**Required inputs.** A *reactive* market simulation (historical replay is explicitly insufficient:
replay cannot generate direct or indirect impact). Environment: noise traders (independent Poisson
intensities), tactical traders (intensities \\(\propto\\) weighted volume imbalance
\\(I=(V^b-V^a)/(V^b+V^a)\\), \\(V^b=\sum_k v^{b,k}e^{-c(k-1)}\\)), and a strategic directional trader.

**Parameters & defaults.** \\(\Delta t=15\\) s, \\(N=10\\), \\(T=150\\) s, depth \\(D=30\\), \\(K=6\\);
noise market-order intensity \\(\lambda^M=0.1237\\); sizes \\(1+\delta|Z|\\) with \\(\delta=2\\) and a
5-SD cap; tactical damping \\(c=0.65\\), reaction \\(d=2\\); strategic trader \\(\nu^M=1\\),
\\(\nu^L=2\\) every 3 s. Policy net: 2 hidden layers, tanh, \\(K\\)-node output; \\(\Sigma=\sigma I_K\\)
annealed linearly from \\(\sigma_{\rm init}\\) to \\(\sigma_{\rm final}\\) over \\(H\\) steps; output
bias \\(b=(-1,\dots,-1)\\); positions 20 and 60 lots (~20%/60% of interval volume).

**Observed effect sizes** (Table 1, expected ticks/lot relative to initial bid):

| Market | Lots | SL | TWAP | Dirichlet-RL | Logistic-normal-RL |
|---|---|---|---|---|---|
| Noise | 20 | 0.52 | −0.06 | 0.21 | **0.61** |
| Noise | 60 | −1.09 | −1.40 | **−0.71** | −0.72 |
| Noise+Tactical | 20 | 0.10 | 0.48 | 0.73 | **0.81** |
| Noise+Tactical | 60 | −3.36 | −0.96 | **−0.23** | −0.25 |
| +Strategic | 20 | −1.64 | −0.36 | 1.06 | **1.13** |
| +Strategic | 60 | −2.51 | −1.45 | 0.03 | **0.23** |

The policy learns to post *deep* (actions \\(a_5,a_6\\)) when tactical traders punish visible size and
to cross the spread when the strategic trader is selling — i.e. front-/back-loading emerges from
the features, it is not hard-coded.

**Failure modes.** Training is expensive and stochastic (high reward SD everywhere); validation
must use a *different* random seed than training to avoid overfitting the market simulator; results
are not comparable to replay-based RL papers because state/action spaces differ; the simulator, not
the algorithm, determines whether indirect impact exists at all.

### 2.6 Diffusion model for the LOB event stream (generative simulator)
**Purpose.** Generate realistic (time, event-type) order-flow sequences for RL training and
scenario stress tests, without a historical L3 feed.

**Formula.** Event types \\(e\in\{0,1,2,3\}\\) = bid submit / bid cancel / ask submit / ask cancel.
Forward: \\(x^k=\sqrt{\bar\alpha_k}x^0+\sqrt{1-\bar\alpha_k}\epsilon\\). Loss
$$\mathcal L=E_{k\sim[1,K],x^0,\epsilon}\big\|\epsilon^k-\epsilon_\theta(x^k,h_{i-1},k)\big\|^2$$
(an ordinary denoising diffusion objective, except the noise predictor is conditioned on the
history embedding \\(h_{i-1}\\)). Time encoding is sinusoidal,
\\(\phi(t)[j]=\cos/\sin(t/10000^{(j-1)/M})\\); event type is one-hot then linear. History is
\\(h=[h^{(t,e)}\Vert h^{(t)}\Vert h^{(e)}]\\) from three self-attention blocks.

**Required inputs.** A recorded event stream — any source will do; the published models used
LOBSTER (MSFT, Nasdaq) and CSMAR (Pingan Bank, China Telecom), with only event *type* + timestamp.

**Parameters & defaults.** \\(L=50\\) history, encoding dim 64 (\\({\approx}256\\) no better), Adam
lr \\(2\times10^{-3}\\), 200 epochs, \\(K\in[50,1000]\\) (\\(K{=}100\\) typical; accuracy rises with
\\(K\\) with diminishing returns). **Skip-step sampling** with stride \\(\tau\in\{5,10,20,50\}\\)
gives up to ~10× speed-up with *no measurable accuracy loss*, no retraining.

**Observed effect sizes.** Event-type accuracy 0.44–0.52 vs 0.33–0.37 (Hawkes), 0.42–0.47
(PCT-LSTM); log-time MAE 0.84–1.98 vs 1.07–2.73; runtime 1.4–1.9 ms/step; all improvements
significant by paired Wilcoxon (\\(p<0.05\\), 5 runs averaged). Time encoding matters more than event
encoding (removing time costs up to 6.4% MAE).

**Failure modes.** The pure stochastic Hawkes baseline is weak because it has few parameters — do
not read the margin as "diffusion ≫ Hawkes" in absolute terms; datasets are single-name and short
(two days each); the model is generative, not a profitability claim; disagreement between LOBSTER
(4 types) and CSMAR (3 types) changes label semantics.

## 3. Data requirements → available endpoints

Provider rows below are real entries in `strategies/endpoints.json`; "gap" means **no current
provider can supply it.**

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (for \\(\sigma_D\\) Parkinson, \\(V_D\\), ADV) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily/prev aggregate bars | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday minute bars (coarsest execution proxy) | `https://api.twelvedata.com/time_series` (`interval=1min`) | `core_stock_apis` | twelvedata | ok |
| Intraday K-line via local OpenD gateway | `moomoo://get_cur_kline` | `technical_indicators` | moomoo | gateway (not live-probed) |
| Top-of-book snapshot (best bid/ask only) | `moomoo://get_market_snapshot` | `core_stock_apis` | moomoo | gateway (not live-probed) |
| Tradable symbol universe / tick sizes | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| **L2/L3 book depth (≥3 ranks)** | — | — | — | **gap** |
| **Market-by-order event stream (ITCH / DBN)** | — | — | — | **gap** |
| **Signed trade tape with aggressor flag** | — | — | — | **gap** |
| **Order-level queue positions / cancellations** | — | — | — | **gap** |
| **Venue-tagged parent (meta) orders** | — | — | — | **gap** |

**What the gap costs, quantified.** The SRL paper needed the *full* Nasdaq TotalView-ITCH
market-by-order feed for one name: 178 trading days, ~0.5 billion events, averaging ~3.2 million
events/day at nanosecond resolution, with a full book reconstruction. The duration paper needed
1,023,480 one-tick mid-price moves for a single symbol in a single month. The microprice paper
needed L3 snapshots for higher-rank imbalances. The negative-drift result needs best bid/ask at
event granularity plus queue-position fill logic. The RL work needs a *simulator*, not historic
data — but a simulator that reproduces real fill/queue mechanics (2.6) still needs one historic
event stream to calibrate. So: **the minimum viable addition is a single-name L3 market-by-order
archive** (Databento DBN or exchange ITCH, e.g. via a Databento subscription), sized at
\\(O(10^8)\\) events/symbol/quarter; an L2 fix from a broker is strictly second-best (loses the
aggressor-sign and queue-position fields the papers rely on). Absent that, everything in §2 is
either an offline research artifact or a *synthetic-only* component.

## 4. Pitfalls, validation and measurement

- **Anonymous-reconstruction bias.** Metaorders inferred from an anonymous tape absorb same-signed
  child flow from *other* participants, over-counting size and inflating the prefactor by ~2×
  (arXiv:2606.24019). Report the raw and bias-corrected estimate, and treat the raw \\(c\\) as an
  upper bound. Robustness: sweep dominance thresholds \\(\{0.2,0.3,0.4\}\\) and bin widths
  \\(\{20,30,45\}\\) s — the law must persist in all 9 settings.
- **Fitted-vs-imposed exponent.** Never fit \\(\delta\\) on one name/short window; fix it at
  \\(\tfrac12\\) and report the free fit only as a consistency check with a bootstrap CI. CI
  \\([0.32,0.66]\\) did not exclude \\(\tfrac12\\) but also would not have excluded a linear law at
  the margins, so the *cross-sectional* prior is doing the work.
- **Sign and chronology null tests are the acceptance gate.** Any impact estimator must (i) lose
  all directional power when aggressor signs are permuted (target: collapse from ~86% to
  ~50%, \\(z>20\\)) and (ii) produce non-viable fits when the event timeline is scrambled (target:
  ~0/80). If shuffling signs still "works", the estimator is leaking.
- **Embrace in-sample failure to expose bad fills.** The negative-drift paper deliberately
  calibrates *and* evaluates in-sample to show that 100%-fill and exponential-fill models do not
  fit even in-sample — do the same for a fill simulator. Then validate out-of-sample against a
  live paper-trading baseline, not against another model.
- **Out-of-sample discipline.** For impact, re-estimate \\(c,\beta\\) every 5 trading days on a
  trailing 20-day window (walk-forward). For durations, rolling 5,000-event windows (~45 min) beat a
  deterministic seasonality term for intraday variation. For RL, train and evaluate on *different*
  simulator seeds.
- **Distributional assumption tests.** Over-dispersion SD/mean \\(=2.07\\) (durations) falsifies
  Poisson/exponential. Run KS and Wasserstein on residuals, plus a likelihood-ratio + Clauset
  goodness-of-fit (\\(p=0.63\\)) for power-law vs exponential tails — and accept that power law is
  *not* separable from lognormal (\\(Z=3.5\\) but not decisive).
- **Regime/impact asymmetry.** Recovery after a market order is stronger with mean-reverting
  tactical traders and weaker when a persistent strategic seller is present (arXiv:2507.06345); big
  *limit* orders acquire much more impact when counterparties react to imbalance. Any fixed
  \\(c\\) or fill rate is a regime-average, not an invariant — condition or re-calibrate.
- **No indirect impact in replay.** Historical-data RL cannot model participants reacting to your
  algorithm; only an agent-based simulator produces both direct and indirect impact
  (arXiv:2507.06345). Do not report replay-based execution P&L as realistic.
- **Latency / evaluation horizon.** Microprice and duration models are sub-second by construction;
  evaluating them on ≥1-minute bars destroys the signal. Match the evaluation horizon to the
  data granularity, and measure with the papers' metrics: \\(L_2\\) error to the future price
  (microprice), rRMSE / R² / LRMSE / KS / Wasserstein (durations), log-time MAE + type accuracy
  (event streams).

## 5. Recommended first implementation in FinRobot

Ordered by value-per-effort against what the layer can fetch today. Items 1–2 are buildable now;
items 3–6 are blocked on a book feed and should be built only as simulator-side code.

1. **Pre-trade impact/cost estimator on daily + intraday bars.** *What:* a cost model
   \\(\text{tick cost}=c\,\sigma_D\,(Q/V_D)^{1/2}\\) (or its tick-per-lot form) with
   \\(c\\) carried as a conservative constant (0.69 raw, 0.34 corrected) and \\(\sigma_D\\) from
   Parkinson high–low on daily bars. *Data:* eodhd `eod` / tiingo `prices` (daily OHLCV),
   twelvedata `time_series` for intraday ADV. *Value:* gives every execution/rebalance suggestion a
   defensible slippage number instead of paying 0. *Risk:* \\(c\\) is only valid when
   \\(Q/V_D\lesssim10^{-2}\\) and is regime-averaged; do not extrapolate to huge orders. *Effort:* S.
2. **TWAP / VWAP / submit-and-leave baseline scheduler with honest fill accounting.**
   *What:* the two heuristics from arXiv:2507.06345 plus a passing note that limit fills carry the
   \\(\approx\tfrac12\\)-tick negative drift, so "passive = free" is false. *Data:* none beyond
   quotes/ADV; compute weights from intraday volume profiles. *Value:* makes FinRobot's execution
   advice internally consistent and non-flattering. *Risk:* without a real fill model this is
   still optimistic — label it as such. *Effort:* S.
3. **LOB market simulator (agent-based).** *What:* port the noise/tactical/strategic agent model
   (Poisson arrivals, imbalance-reactive intensities \\(d\!\cdot\!I^\pm\\), damping \\(c=0.65\\),
   sizes \\(1+\delta|Z|\\)) and the fill logic from §2.3, then the logistic-normal actor-critic from
   §2.5. *Data:* none live — self-contained. *Value:* the only route in this repo to a policy that
   trades market *and* limit orders, and the only honest way to study indirect impact. *Risk:*
   simulator misspecification; results transfer only if calibrated to a real tape. *Effort:* L.
4. **Duration/intensity feature service (Hawkes-style).** *What:* the flexible-residual self-exciting
   model on event times, used as a *timing* feature (burst detection), not a direction signal.
   *Data:* requires an event/tick stream — **blocked today**; can only be prototyped on bars as
   "duration to a one-tick bar move", which is not the same object. *Value:* high once a tape
   exists; low as a bars hack. *Risk:* best point-forecast \\(R^2\approx0.14\\) — sells nothing on its
   own. *Effort:* M (after feed).
5. **Microprice estimator.** *What:* Stoikov microprice + higher-rank imbalance correction, exposed
   as a sub-spread fair value for passive order pricing. *Data:* L2 depth with ≥3 ranks —
   **blocked**. *Value:* ~10–20% \\(L_2\\) error reduction on liquid names; near-zero on illiquid
   ones. *Risk:* spoofing contamination at depth. *Effort:* M (after feed).
6. **Acquire a book feed.** *What:* add a Databento DBN / exchange ITCH (or at minimum a broker L2)
   ingestion path and register it as a new data category
   (e.g. `order_book_depth` / `tick_trades`) in `finrobot/engine/data/categories.py`. *Data:* the
   feed itself. *Value:* unblocks items 4–5 and the calibration of item 3; without it this whole
   category stays synthetic. *Risk:* cost, storage (\\(10^8\\) events/name/quarter), and the
   licensing terms on redistributing ITCH. *Effort:* L.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2606.24019v1 | Empirical Confirmation of the Square-Root Law of Market Impact in a U.S. Large-Cap Equity | 2026 |
| 2604.00346v2 | Forecasting duration in high-frequency financial data using a self-exciting flexible residual point process | 2026 |
| 2507.06345v2 | Reinforcement Learning for Trade Execution with Market and Limit Orders | 2025 |
| 2412.09631v1 | Limit Order Book Event Stream Prediction with Diffusion Model | 2024 |
| 2411.13594v1 | High resolution microprice estimates from limit orderbook data using hyperdimensional vector Tsetlin Machines | 2024 |
| 2407.16527v1 | The Negative Drift of a Limit Order Fill | 2024 |
