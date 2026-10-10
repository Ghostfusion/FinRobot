# crypto-assets — learnings from the q-fin.ST corpus

`723` of 4372 corpus papers matched this category (665 with PDFs); this doc is based on a close reading of `6`.

> The `crypto-assets` tag in the manifest is broad — its year histogram runs from 1998 to 2026, so pre-2017 members are mostly cryptography/ledger-adjacent rather than crypto-asset market studies. All six papers read here are 2025–2026 and all are crypto-market studies. Co-tag counts confirm the sub-field split: `correlation-networks-econophysics` 142, `ml-price-prediction` 120, `microstructure-execution` 112, `econometrics-forecasting` 80, `mean-reversion-pairs` 79.

## 1. What the corpus actually offers

**Short-horizon reversal is a measurement problem before it is a crypto fact.**

- At 15-minute horizons, directional reversal is pervasive in crypto and near-absent in US equities under one matched, strictly out-of-sample protocol: **90% of 183 Binance USDT spot pairs** are FDR-significant (`BH q = 0.05`) versus **2.7% of 187 US stocks/ETFs** (164/183 vs 5/187); class-mean out-of-sample AUC gap $+0.031$ (95% CI $[+0.027,+0.035]$), stable across bootstrap block lengths (arXiv:2608.21888).
- The signal lives in **signs, not magnitudes**: lag-one *return* autocorrelation is $\approx 0$ on the majors (BTC $\rho_1 = -0.003$, ETH $+0.005$, XRP $-0.023$), yet a parameter-free sign statistic reproduces the whole class gap. Class-mean kernel-weighted sign correlation $R$ (Eq. 2 below) is $-0.035$ (95% CI $[-0.041,-0.029]$), negative in **98% of crypto pairs vs 50% of stocks**; sign-flip rate rises monotonically with the size of the previous move, from **50.2% to 53.0%** across deciles of $|r_{t-1}|$ (arXiv:2608.21888).
- Finite memory, standing effect: mean AUC decays monotonically with the sampling interval and is **gone by 4 hours** (Figure 2); the hourly rerun keeps 58% of crypto pairs significant vs 0% of stocks; every focal coin-year since 2021 is two-model significant (**24/24 coin-years**) (arXiv:2608.21888).
- Mechanism evidence on the originating tape: reversal concentrates after moves that **aggressive taker flow** pushed and grows with flow intensity — OOS AUC $0.540$ after flow-driven bars vs $0.519$ after flow-opposed; pooled flow-driven minus flow-opposed flip-rate difference $+0.021$ (CI $[0.015,0.026]$). Net order-book depth consumed by the move conditions **nothing** (flip-rate difference $-0.002$, CI $[-0.007,+0.004]$), i.e. the book re-forms within the 15-minute bar (arXiv:2608.21888).
- Economic bound: gross edge peaks near **1.3 bp per trade against a 5 bp cheapest round-trip spot cost** — detectable, not capturable at benchmark costs (arXiv:2608.21888).
- Wrapper transmission (generalises to any NAV-linked ETF): a fund whose NAV *is* a continuously traded price inherits its underlying's reversal, nulls included, from its first months of trading (BTC/Ether families match to a **family gap $\le 0.001$**, $+3.0$ cross-sectional SD above the 187-stock reference); five correlated-but-not-NAV-linked controls (GDX, NEM, COIN, MSTR, UUP) carry **nothing** (0/5 significant). IBIT and Binance BTC move together at $r=0.982$ per minute and the largest displaced correlation at $\pm1..\pm10$ minutes is $0.013$ — no exploitable lead (arXiv:2608.21888).

**Sampling clock: tick vs time vs information bars.**

- Controlled six-bar-type comparison (dollar, volume, volatility, range, Renko, hybrid) on BTCUSDT USDT-margined perpetuals, Jan 2020–Dec 2025 (2,192 days), two pipelines driven by raw Binance `aggTrade` ticks vs one-minute OHLCV: **tick Renko** achieves $|\mathrm{VR}(4)-1| = 0.020$, $|\mathrm{AC}(1)| = 0.002$ (best random-walk conformance); **tick volatility** cuts VR(4) deviation by **69%** vs the minute baseline ($0.028$ vs $0.089$); **tick hybrid** has the lowest tail risk of any tick pipeline (excess kurtosis $6.77$, Jarque–Bera $174{,}557$, 40× below the 1h time-bar baseline $7{,}156{,}670$) (arXiv:2608.26158).
- The tick advantage is **bar-type-specific and proportional to the information minute aggregation discards**. At matched frequency (tick series coarsened $1{:}k$ to the minute bar count, phase-averaged): matched tick dollar bars lead on **6/6** criteria, hybrid **5/6**, volatility **4/6** with LB $p=0.510$ (serial independence recovered); volume bars stay minute-favoured (arithmetic equivalence of the two volume signals) and range/Renko stay structurally mismatched (arXiv:2608.26158).
- Statistical bar quality does **not** buy directional forecastability: out-of-sample AUC-ROC spans **0.498–0.596** across every bar type and data source (minute Renko RF 0.596, tick volatility RF 0.563), with no systematic ordering by any quality criterion; inverting a directionally anti-predictive model merely captures the sample's uptrend (arXiv:2608.26158).

**Realized-volatility roughness and multifractality.**

- Bitcoin realized volatility admits a **low pathwise roughness index**: the model-free normalized $p$-variation estimator of Cont–Das returns a unique root in **341/380 rolling 90-day window-frequency configurations (89.7%)** and **113/128 non-overlapping (88.3%)**; conditional rolling medians of $\hat H$ are **0.054, 0.065, 0.086, 0.080** at 1/5/10/15 minutes; **every finite estimate in every analysis is $< 1/2$** (largest $\approx 0.193$) (arXiv:2507.00575).
- Finite-sample bias in the Hurst exponent of RV: $H(\Delta) = H_0\, n/(n+a)$ with $n = 1440/\Delta$; fitted $H_0 = 0.1379/0.1308/0.1262$ and $a = 2.93/3.02/3.15$ (close to the integer 3) across three periods. The relative error at the widely used **5-minute RV is only ~1%**, so 5-minute RV is safe for HE estimation (arXiv:2511.03314).
- RV is **multifractal but less so than returns**: mean $\Delta h(3) = 0.034$ for RV versus $\Delta h(3) \approx 0.12$ for price returns; mean $-B_1 = 0.0057$, consistent with stock RV (arXiv:2511.03314).
- The roughness estimate is **not invariant to time or measurement design**: root availability is lowest at 1 minute (79/95, 83.2%); locally truncated RV drops the 1-minute fixed-window root rate 62.5% → 37.5%; bipower variation returns a unique root in only 20/24 eligible configs and moves the median 5-minute estimate from 0.068 to 0.019; annual median $\hat H$ rises at 10 and 15 minutes (Spearman $\rho = 0.714$, $p=0.047$; $\rho = 0.833$, $p=0.010$); penalized segmentation finds **292 breakpoints across 32 configs** (median 10, range 3–15) (arXiv:2507.00575).

**Event studies: protocol upgrades and on-chain launches (the generalisable template).**

- Ethereum's Pectra upgrade (EIP-7251, May 2025) raised max effective balance 32 → 2,048 ETH and enabled CL reward compounding. Simulation: relative consensus-layer APR uplift **+4.7% for 32–2,048 ETH, decaying to +0.3% for 8,192–10,240 ETH** (200 Monte Carlo runs per balance point, 1-year horizon) (arXiv:2606.23337).
- Empirical 913,225-validator panel: 30-day median CL APR 0x02 2.525% vs 0x01 2.249% (**+12.3% relative**), but the advantage **collapses to +1.5% at 335 days** (2.651% vs 2.611%, $\Delta_{med}=+0.039$ pp, Mann–Whitney $p=1.8\times10^{-12}$). The 30-day gap is a **proposer-reward variance artefact**, not compounding — a textbook demonstration that short-window event effects can be pure sampling variance (arXiv:2606.23337).
- Bonding-curve launchpad (Pump.fun, Solana, Sept 2025): 655,770 tokens, **0.63% graduated** (4,338); median 457 bonding-curve steps and **4.4 minutes** to graduation. Conditioning graduation probability on time-consistent behavioural variables (bot share, trade count, presence of historically successful traders, creator prolificness) shifts the curve materially; fast accumulation through few trades dominates; bot-dominated tokens have lower graduation probability beyond intermediate stages (arXiv:2602.14860).

**Which findings are crypto-specific, and which generalise:**

| Finding | Scope |
|---|---|
| Magnitude/breadth of 15-min reversal (90% vs 2.7%) and its 1.3 bp vs 5 bp economics | **Crypto-specific** (venue structure, retail-heavy, no consolidated tape) |
| Reversal lives in *signs*; conditioning on aggressive taker flow | Generalisable **measurement** lesson; the flow data itself is crypto-only here |
| Wrapper/NAV inheritance (fund tape = wrapped process) | **Generalises to any ETF/ETN on a continuously traded underlying** (metals, FX, crypto) |
| Information-bar construction, VR(4)/AC(1)/timeout diagnostics | Generalises to any high-frequency series |
| Near-chance directional predictability from statistical bar quality | Generalises (weak-form efficiency caution) |
| Realized-vol roughness estimator + finite-sample $H(\Delta)$ correction | Generalises across assets; crypto adds a 24/7, multi-regime test bed |
| Event-study design around a dated protocol change | Generalises as a template (earnings, index reconstitution, upgrades) |
| Bonding-curve graduation, pump-and-dump mechanics, staking APR | **Crypto/on-chain-specific** |

## 2. Implementable formulas & algorithms

### 2.1 Matched cross-market short-horizon reversal measurement

**Purpose.** Measure *conditional* sign predictability at a fixed intraday horizon on one market and compare it, under an identical protocol, against a matched control market. This is the reusable core of arXiv:2608.21888 — it is a measurement device, not a model of markets.

**Constrained kernel logit** (primary estimator; three free parameters regardless of $N$):

$$P(\text{up}_t) = \mathrm{sigmoid}\!\left(C + A\sum_{k=1}^{N} k^{-\alpha} s_{t-k}\right), \qquad s_{t-k} = \tanh(\lambda\, r_{t-k}), \qquad r_t = \frac{\text{close}_t - \text{open}_t}{\text{open}_t}$$

$A<0$ is mean reversion, $A>0$ momentum; $\alpha$ is memory decay; $\lambda$ a fixed soft-clip. Tying the lag weights to $A k^{-\alpha}$ keeps effective degrees of freedom at two regardless of $N$.

**Parameter-free corroborator** (nothing fitted; used wherever a fitted result needs confirmation):

$$R = \mathrm{corr}\!\left(\sigma_t,\ \sum_{k=1}^{12} k^{-\alpha}\sigma_{t-k}\right), \qquad \sigma_t = \mathrm{sgn}(r_t),\ \alpha \equiv 1$$

**Required inputs.** Intra-bar open-to-close returns on a fixed grid; label $\mathbf{1}[r_t>0]$.

**Parameters / defaults reported.** $N = 12$, $\lambda = 150$, $\alpha$ tied and fitted. Walk-forward: train 5,760 / test 960 candles, step = test-block size, non-overlapping test blocks concatenated and scored once. Statistic: base-rate-invariant **AUC**. Inference: one-sided moving-block bootstrap ($\text{block}=384$ candles, $B=300$ resamples → attainable $p$-floor $1/(B+1)=0.0033$); per-asset conjunction $p_\cap=\max(p_{\text{constr}}, p_{\text{free}})$; **Benjamini–Hochberg FDR at $q=0.05$ jointly across all assets**. Population gap: *joint* moving-block bootstrap on the shared time grid ($B=1{,}000$; 5,000 in sensitivity). A one-lag special case ($N=1$, "bet against the previous candle") already reaches crypto class-mean AUC 0.527 vs 0.531 for the 12-lag kernel.

**Observed effect sizes.** AUC gap $+0.031$ (constrained) / $+0.026$ (free AR(12)); $+0.022$ after dropping flat bars; $+0.011$ (CI $[+0.008,+0.014]$) with both flat-bar and one-bar-gap adjustments; $+0.020$ (CI $[+0.010,+0.028]$) on a frozen six-month holdout; $R$-gap $-0.035$; DFA-Hurst class gap $-0.049$ (CI $[-0.084,-0.012]$). Accuracy is small: 52.3% unthresholded on BTC.

**Failure modes (all documented).** (i) *Flat bars* ($r_t=0$) get label 0 by convention and hand a reversal model free "correct" calls — rescore on non-flat bars only (worth 0.009 of AUC). (ii) *Bid–ask bounce / staleness* at the feature–label boundary — insert a one-bar gap (71% of the excess survives). (iii) *Intraday heteroskedasticity* buries real dependence in pooled AUC (17.6× for listed instruments vs 5.0× for crypto); rescoring within hour-of-day strata *widened* the gap to $+0.0335$. (iv) *Cross-sectional dependence*: with mean pairwise correlation 0.40 the effective number of independent crypto observations is $\approx 2.5$, so 183 pairs are not 183 replications — always use the joint bootstrap. (v) A single crypto market factor explains only ~19% of the sign reversal (projecting it out retains 81%).

### 2.2 Information bars with adaptive (EMA) thresholds

**Purpose.** Replace the calendar clock with an activity clock so that each bar carries comparable information content, improving return normality and reducing serial dependence — *only* for the bar types whose activity signal minute-aggregation actually destroys.

**Activity signals per bar type** (accumulator $S$; bar closes when $S \ge \hat\theta$):

| Bar | Minute pipeline | Tick pipeline |
|---|---|---|
| Dollar | $\Delta^{dv}_m = c_m v_m$ | $\Delta^{dv}_i = p_i q_i$ |
| Volume | $\Delta^{qty}_m = v_m$ | $\Delta^{qty}_i = q_i$ |
| Volatility | $\Delta^{ctc}_m = \lvert c_m-c_{m-1}\rvert/c_{m-1}$ | $\Delta^{rv}_i = \lvert\log(p_i/p_{i-1})\rvert$ |
| Range | $(h_m-l_m)/c_m$ (summed) | $(H_b-L_b)/p_{open}$ (running extremes) |
| Renko | $\delta_m = \lvert c_m-p_{ref}\rvert/p_{ref}$ (instantaneous, not accumulated) | $\delta_i = \lvert p_i-p_{ref}\rvert/p_{ref}$ |
| Hybrid | $\Delta^{dv}_m$ **OR** $\Delta^{ctc}_m$ | $\Delta^{dv}_i$ **OR** $\Delta^{rv}_i$ |

**Adaptive threshold (EMA, the paper's original design choice):**

$$\hat\theta_{n+1} = (1-\alpha)\,\hat\theta_n + \alpha\cdot\min(s_n,\,2\hat\theta_n)$$

where $s_n$ is the realised bar size; the cap at $2\hat\theta_n$ stops one flash-crash bar from permanently inflating the target. $\alpha$ is itself adapted from the recent coefficient of variation of bar sizes (high CV → faster adaptation). Initial threshold = median daily activity measure / target bars-per-day, calibrated on $L=14$ days (≥2 weekly cycles, within one volatility regime).

**Parameters / defaults.** Duration bounds $[d_{\min}, d_{\max}]$ in minutes, derived from estimated bar duration and frequency target; **timeout% (bars closed by $d_{\max}$) > 10% means the threshold is unachievable and the bars carry no genuine information**. Hybrid OR logic (AND produces >60% timeouts at the BTC dollar-volume/volatility correlation $\rho \approx 0.5$–$0.7$); each hybrid threshold is set to 2× the desired bar frequency. For the tick pipeline, replace minute-derived thresholds with tick-native ones (exact $\sum p_i q_i$, $\sum\lvert\log(p_i/p_{i-1})\rvert$, exact running high–low) so resolution is the only variable.

**Quality criteria and reported values.** $|\mathrm{VR}(4)-1|$ (variance ratio, target 0), $|\mathrm{AC}(1)|$ (target 0), excess kurtosis, Jarque–Bera, Ljung–Box $p$, bar-size CV (uniformity, lower better), Shannon entropy (diversity, higher better), timeout%. Tick Renko: $|\mathrm{VR}(4)-1|=0.020$, $|\mathrm{AC}(1)|=0.002$. Tick volatility: $|\mathrm{VR}(4)-1|=0.028$ vs minute 0.089. Matched-frequency tick volatility: LB $p=0.510$, kurtosis 1.79, JB 1,203; matched tick dollar: 6/6 criteria.

**Failure modes.** (i) *Frequency confound*: tick pipelines sampled 2.8–26.6× more often; finer sampling mechanically inflates kurtosis — must coarsen $1{:}k$ (phase-averaged) before comparing. (ii) *Regime mismatch*: a calibration window at \$7–8k BTC was applied over six years including the March 2020 crash, 2021 peak, 2022 trough and the Jan-2024 spot ETF — all series reject independence/normality at $N=30k$–$200k$; the EMA tracks but drifts. (iii) *Renko at tick resolution* has no minimum-duration constraint (236,098 bars vs 8,985, 26×) — needs a tick-native duration floor. (iv) At large $N$, JB and LB $p$-values are useless ($p\approx 0$ for everything); rank on **effect sizes** only.

### 2.3 Realized volatility, roughness, and multifractality

**Purpose.** (a) Build a realized-volatility path, (b) estimate its pathwise roughness with a model-free estimator, and (c) correct the sampling-induced bias in the Hurst exponent.

**Realized volatility and log-vol increments:**

$$RV_{t,\Delta} = \sum_{i=1}^{n} r_{t,i,\Delta}^2,\quad n = 1440/\Delta; \qquad V_t = \log RV_t - \log RV_{t-1}$$

**Normalized $p$-variation roughness (Cont–Das), model-free:**

$$W(L,K,p) = \frac{1}{K}\sum_{j=0}^{K-1} \frac{\bigl|X_{(j+1)n}-X_{jn}\bigr|^{p}}{\sum_{i=jn}^{(j+1)n-1}\bigl|X_{i+1}-X_{i}\bigr|^{p}},\quad p>1$$

with $K=\max(2,\lfloor\sqrt{N}\rfloor)$, $n=\lfloor N/K\rfloor$, $L=Kn$. Solve $W(L,K,\hat p)=1$ over $H=1/p \in [0.01,0.95]$ in log form; report a finite $\hat H$ **only when exactly one root** exists. Report *root availability* separately from the distribution of finite estimates.

**Finite-sample Hurst correction:**

$$H(\Delta) = H_0\,\frac{n}{n+a},\quad n = 1440/\Delta$$

Fit $H_0$ (the $\Delta\to0$ value) and $a$; report relative error $a/(n+a)$. At 5-minute $\Delta$ this is ~1%.

**Multifractal diagnostics.** MF-DFA $F_q(s)\propto s^{h(q)}$ (first-order detrending); width $\Delta h = \max_q h(q)-\min_q h(q)$; strength $\Delta h(k) = h(-k)-h(k)$ and Taylor slope $h(q)=B_0+B_1 q$, with $B_1\approx -\Delta h(3)/6$.

**Jump-robust alternatives.** Locally truncated RV with threshold $c\,\hat\sigma$, $\hat\sigma_t = \mathrm{median}(|r_{t-1..t-1440}|)/\Phi^{-1}(0.75)$, $c\in\{4,6,8\}$; realized bipower variation $\mathrm{BPV}_b^{(m)} = \frac{\pi}{2}\sum_{i=2}^{m}|r_{b,i}||r_{b,i-1}|$ (undefined at 1-minute bins).

**Parameters / defaults.** Sampling $\Delta \in \{1,5,10,15\}$ minutes from a common 1-minute base; primary temporal design = 90-day windows every 30 days (non-overlapping subset = every third window); $H$ search $[0.01,0.95]$; MF-DFA moment orders $q\in\{0.5,1,1.5,2,2.5,3\}$, scales 60–2,880 minutes, negative $q$ excluded when the RV path has exact zeros; surrogate $p$-value floor with $R=19$ replications is 0.05.

**Observed effect sizes.** Unique roots 89.7% (rolling) / 88.3% (non-overlapping) / 26-of-32 (fixed panel); medians 0.054/0.065/0.086/0.080; $H_0 \approx 0.12$–$0.14$; 5-minute relative error ~1%; $\Delta h(3)$: RV 0.034 vs returns 0.12; IAAFT surrogates leave residual MF-DFA width in only 3/8 five-minute samples and log-moment curvature in 1/8 — most apparent multifractality is reproduced by the marginal distribution + linear dependence.

**Failure modes.** (i) Root may not exist or may be non-unique — do not impute. (ii) Truncation removes 0.27–1.88% of observations but 10.1–32.8% of squared variation, and *lowers* 1-minute root availability (62.5%→37.5%); jump-robust measures change magnitude (5-min median 0.068→0.019). (iii) Microstructure noise dominates at 1 minute (the 1-minute point deviates from the ansatz). (iv) The estimate is a property of the **observed** RV path, not of latent spot volatility (Cont–Das: realized volatility can read $H<1/2$ even under diffusive spot volatility).

### 2.4 Event study around a dated protocol change (staking-upgrade template)

**Purpose.** The Pectra study (arXiv:2606.23337) is a reusable template for measuring the effect of a dated, exogenous protocol change on a population of homogeneous agents — directly analogous to an earnings or index-reconstitution event study.

**Effective-balance hysteresis update** (the treatment mechanism):

$$B_{eff} \leftarrow \begin{cases}\min(\lfloor B_{act}\rfloor,\ B_{cap}) & \text{if } B_{act}\notin [B_{eff}-\Delta_\downarrow,\ B_{eff}+\Delta_\uparrow]\\ B_{eff} & \text{otherwise}\end{cases}$$

with $\Delta_\downarrow = 0.25$ ETH, $\Delta_\uparrow = 1.25$ ETH, $B_{cap}\in\{32,2048\}$ ETH by credential type.

**Reward/APR:** $R_{CL,v,epoch}\propto B_{eff,v,epoch}$ (all other protocol parameters validator-independent);

$$\mathrm{APR}_v = \frac{R_{v,window}}{B_{act,start,v}}\cdot\frac{E_{year}}{E_{window}}\cdot 100,\qquad E_{year}\approx 51{,}480\ \text{epochs (6.4 min each)}$$

**Design.** Monte Carlo simulation (200 runs/balance point, 1-year horizon, 96–99% participation, $S_{total}=38.8$M ETH) to predict; then an empirical cohort comparison of all active validators with a **Mann–Whitney $U$** test (chosen because the APR distribution has excess kurtosis $+10.9$, skew $+0.50$ after 5/95 winsorisation, and unequal variance — Shapiro–Wilk rejects normality at $p\approx3.8\times10^{-36}$). Report **both** $p$ and the effect size $\Delta_{med} = \mathrm{med}_{0x02}-\mathrm{med}_{0x01}$; with $n$ in $10^5$–$10^6$ the $p$-value saturates.

**Parameters.** Winsorise 5/95 within each group before any statistic; use the longest window the data spans (335 days) with time-adjusted annualisation $\mathrm{APR}=(\mathrm{cl}_{365d}/B_{eff})\times 365/\min(d,365)$, requiring $d\ge7$ active days to avoid amplifying tiny accumulators.

**Observed effect sizes.** Simulated CL APR uplift +4.7% (32–2,048 ETH) → +0.3% (8,192–10,240 ETH); 30-day empirical +12.3% (2.525% vs 2.249%) collapsing to +1.5% at 335 days (2.651% vs 2.611%, $\Delta_{med}=+0.039$ pp, $p=1.8\times10^{-12}$).

**Failure modes.** (i) **Short-window variance artefact** — the 30-day lead is proposer-reward luck on high-$B_{eff}$ validators, not the treatment; a genuine compounding gap would persist/grow with time. (ii) A naive "last 365 days" filter covers only the ~20% of 0x02 stake activated pre-upgrade (survivorship). (iii) Selection: adoption (25% of staked ETH, 80% new deposits / 20% migration) is endogenous; the empirical median difference is an association, not the simulated causal uplift.

### 2.5 Bonding-curve launch event study (on-chain template)

**Purpose.** Model the probability that a new asset reaches a protocol-defined success threshold, conditional on real-time-observable state — a template for any state-contingent success/graduation event (arXiv:2602.14860).

**Constant-product bonding curve:** $xy = k = x_0^{tot,virt}\,y_0^{tot,virt}$; marginal price $P = x/y$; graduation when $x^{tot,virt}$ reaches 115 SOL (30 synthetic + 85 real). Baseline estimator and profitability boundary:

$$p_{std}(vSol) = P\bigl(\text{grad}\,\big|\,\exists x: x > vSol\bigr), \qquad \text{profitable iff } p(vSol;\theta) > \frac{vSol^2}{115^2}$$

(the breakeven follows from $E[r] = p\cdot\frac{115^2}{vSol^2} - 1$ for buy-and-hold to graduation).

**Conditioning variables** (all constructed strictly from information available up to the current $vSol$): bot share $1-\tau$ (from on-chain log inspection: direct contract calls vs dApp frontend), cumulative trade count, presence of a historically profitable trader, creator prolificness. Compare $p_\theta(vSol)=P(\text{grad}\mid\tau>\theta)$ for $\theta\in\{0.3,0.7\}$ against $p_{std}$.

**Observed effect sizes.** Graduation base rate 0.63%; median 457 steps / 4.4 min; conditioning on non-bot share lifts the curve above baseline; $p_{std}$ alone lies *below* the breakeven curve.

**Failure modes.** (i) Extreme class imbalance (0.63%) — AUC on a near-deterministic threshold is easy; discrimination must be measured away from the graduation region. (ii) Manipulation is embedded in the mechanism (pre-graduation liquidation incentives, honeypots); a high predicted probability near threshold is mechanical. (iii) Wallet-level identity is not user-level (multiple wallets per trader inflate "successful trader" counts).

## 3. Data requirements → available endpoints

The data layer routes on 33 categories (`finrobot_desktop/finrobot/engine/data/categories.py`). **There is no `crypto` category and no on-chain provider anywhere in the 14-provider inventory** — the only crypto-adjacent routes are the generic equity EOD endpoints (EODHD also serves crypto via `.CC` tickers, Twelve Data and yfinance accept crypto tickers, but the adapters carry no crypto symbol mapping) and the news/sentiment feeds. Every row below cites a real probed endpoint from `strategies/endpoints.json`; rows the layer cannot serve are marked **gap**.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Crypto spot OHLCV, 15-min (183 Binance pairs) | `https://eodhd.com/api/eod/AAPL` (EODHD crypto would be `BTC-USD.CC` on the same route) | core_stock_apis | eodhd | ok (endpoint); **gap** — EOD-only, no 15-min granularity, no crypto symbol mapping in the adapter |
| Crypto OHLCV via generic series API | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok; **gap** — adapter hard-codes `interval=1day`; intraday crypto not wired |
| US equity/ETF control series, 15-min & daily | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| US equity prev-close / aggregates | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | core_stock_apis | massive | ok |
| Crypto news (event windows) | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| Crypto/asset news sentiment score | `https://eodhd.com/api/sentiments` | news_sentiment | eodhd | ok |
| Sentiment (alternative) | `https://www.alphavantage.co/query` | news_sentiment | alpha_vantage | ok |
| Headline news / retractions | `https://api.benzinga.com/api/v2/news` | news_data | benzinga | ok |
| Global news stream (crypto coverage) | `https://newsapi.org/v2/everything` | news_data | newsapi | ok |
| Global news tone (event study) | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | rate_limited (HTTP 429) |
| Risk-free / rate curve for carry & APR comparison | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Prediction-market probabilities on crypto events | `https://gamma-api.polymarket.com/markets` | prediction_markets | polymarket | ok |
| Crypto options surface (e.g. Deribit DVOL/skew) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | **gap** — cboe row is SPX-only (also HTTP 307); no crypto options provider |
| Intraday bars / indicators (possible intraday route) | `moomoo://get_cur_kline` | technical_indicators | moomoo | gateway (local OpenD SDK); equity-focused, not wired for crypto |
| **Tick / aggTrade trades** | — | — | — | **gap** — no tick provider in the inventory |
| **Taker imbalance / order-book depth** | — | — | — | **gap** — no L2/order-flow provider |
| **Perpetual funding rate / basis** | — | — | — | **gap** — no derivatives provider |
| **On-chain: staking, validators, bonding curve, wallet flows** | — | — | — | **gap** — no on-chain provider (needed for §2.4 and §2.5) |

**Implication:** §2.1 (via NAV-linked US crypto ETFs as a proxy tape), §2.2 (from minute OHLCV), §2.3 (from minute closes) and the equity control leg are implementable today against `core_stock_apis` / `news_data` / `news_sentiment`. §2.4 and §2.5, and any order-flow conditioning or tick-vs-minute comparison, require new providers and cannot be built on the current layer.

## 4. Pitfalls, validation and measurement

- **Leakage.** Fit strictly out of sample with a chronological validation tail; concatenate non-overlapping test blocks and score once. Insert a **one-bar gap** between features and label (removes bid–ask bounce; 71% of the crypto excess survived it). In bar pipelines use a **1% embargo** between train and test folds. In the Pump.fun design, every conditioning variable must be constructed only from trades up to the current $vSol$ — the paper's central methodological claim.
- **Overfitting / selection.** Freeze the design *before* running the wide universe; then report a **frozen post-sample holdout** (arXiv:2608.21888 refetched 2026-02→2026-08 with no model/geometry/statistic changes; gap attenuated to $+0.020$ but stayed clear of zero). Report an **ex-ante universe** (re-ranked by first-sample-month volume) to bound survivor tilt; note that delisted pairs are unrecoverable from public APIs, so the selection objection is only partly addressable. Add an **exact permutation null** preserving the dependence structure (0/340 admissible label shifts reached the gap).
- **Interval honesty.** A fit-conditional bootstrap prices sampling variation but not estimation uncertainty; refitting both models inside each replicate cut the gap by a third to a half and roughly doubled the interval width. Prefer permutation inference, which needs no interval.
- **Power.** An equity null is only meaningful with a power calculation: the 15-min design detected a crypto-sized effect in the equity class with median power 0.98 and bounded the stock class-mean AUC at $\le 0.5007$.
- **Effect size vs $p$-value at large $N$.** At $10^5$–$10^6$ observations every test rejects. Rank on AUC gaps, $\Delta h$, $\Delta_{med}$, $|\mathrm{VR}(4)-1|$, $|\mathrm{AC}(1)|$, and always report the effect size next to the $p$-value (arXiv:2606.23337, arXiv:2608.26158).
- **Regime and non-stationarity.** Multi-regime samples (2020 crash, 2021 peak, 2022 trough, 2024 ETF) inflate kurtosis and reject normality/independence for *all* bar types; roughness root availability and magnitude vary across periods and measures (292 structural breaks in 32 configs); short event windows can manufacture effects (30-day +12.3% → 335-day +1.5%). Always rerun across sub-periods and alternative window lengths.
- **Microstructure noise.** 1-minute RV is contaminated (deviation from the finite-sample ansatz; truncation lowers root availability there); use 5-minute RV as the default. Detectability must be separated from signal: pool-free intraday heteroskedasticity can hide real dependence (SPX reads AUC 0.492 but 0.515 after variance homogenisation).
- **Cost reality.** A statistically clear edge can be economically nil: 1.3 bp gross vs 5 bp round-trip. Any backtest must subtract the *cheapest realistic* round-trip cost for the venue.
- **Dependence.** Never treat $N$ correlated assets as $N$ replications ($N_{eff}\approx2.5$ for crypto here); use a joint moving-block bootstrap on the shared time grid.
- **Validation checklist for any implementation.** (1) Walk-forward, non-overlapping, concatenated. (2) One-bar gap + non-flat rescoring. (3) Joint block bootstrap for any population claim. (4) Frozen post-sample holdout. (5) Permutation null. (6) Power calculation for any "no effect" claim. (7) Effect sizes reported alongside $p$-values. (8) Cost-adjusted P&L.

## 5. Recommended first implementation in FinRobot

1. **Crypto-proxy reversal monitor (effort S).** Compute the §2.1 sign statistic $R$ and 15-min AUC on US-listed NAV-linked crypto ETFs (IBIT/FBTC/ETHA, or EODHD `.CC` crypto if a symbol mapping is added) against an equity control, using the existing `core_stock_apis` route (`eodhd`, `tiingo`, `massive`). *Data needed:* 15-min bars (gap: EOD only today — start on daily/intraday-equivalent and document). *Expected value:* a live, low-maintenance gauge of short-horizon reversal breadth; reusable measurement harness. *Risk:* the paper shows the edge is below spot capture costs, so this is a monitor, not a strategy. *Build:* walk-forward kernel logit + parameter-free sign statistic + joint block bootstrap.
2. **Information-bar sampler in the data layer (effort M).** Implement dollar/volume/volatility bars with the §2.2 EMA threshold and duration bounds from minute OHLCV (no tick needed); emit `|VR(4)-1|`, `|AC(1)|`, bar-size CV, and **timeout%** as first-class diagnostics (timeout > 10% ⇒ reject calibration). *Data needed:* minute OHLCV (`twelvedata` intraday — currently hard-coded daily; `moomoo` kline gateway). *Expected value:* a sampling substrate for downstream ML with the paper's quality gates, plus a reusable diagnostic. *Risk:* the paper shows statistical bar quality does **not** imply forecastability — do not sell it as alpha.
3. **Realized-vol roughness estimator with finite-sample correction (effort M).** From minute closes compute RV at 1/5/10/15 min, the normalized $p$-variation roughness (report root-availability separately from finite $\hat H$), MF-DFA $\Delta h$, and the $H(\Delta)=H_0 n/(n+a)$ fit; default to 5-minute RV (~1% bias). *Data needed:* 1-minute closes (same routes as #2). *Expected value:* a regime/stress descriptor and a defensible default sampling frequency for any volatility work. *Risk:* root non-existence and measure-sensitivity must be surfaced, not smoothed.
4. **Dated-event study harness (effort M).** Generalise §2.4 into a reusable module: given a dated event and a treated/control population, winsorise 5/95, run Mann–Whitney $U$ with a median-difference effect size, time-adjusted annualisation, and forced sub-period reruns. *Data needed:* `earnings_calendar` (benzinga), `corporate_actions`, price history (`core_stock_apis`), `macro_data` (`fred`) for the control. *Expected value:* turns the staking-upgrade template into an earnings/reconstitution/regulatory event analyzer. *Risk:* short-window variance artefacts — enforce a minimum post-event window.
5. **On-chain ingestion provider (effort L, requires a decision).** §2.4 and §2.5 and all order-flow conditioning are **blocked** on the current layer. To close the gap, add one on-chain/aggregator provider (e.g. Dune, Beaconcha.in, CoinGecko, Glassnode) behind a new category, plus a tick/aggTrade source for §2.2. *Data needed:* new provider + key (env-var name only, e.g. a `*_API_KEY`). *Expected value:* unlocks staking APR, bonding-curve graduation, validator flows, and tick-vs-minute bar work. *Risk:* new vendor, cost, rate limits.
6. **Bonding-curve graduation model (effort L, blocked on #5).** Implement the time-consistent conditional graduation probability $p_{std}(vSol)$ and the $vSol^2/115^2$ breakeven for a launchpad feed. *Data needed:* on-chain swap/curve state (#5). *Expected value:* an early-stage success-probability engine and a template for any state-contingent success event. *Risk:* extreme base rate, embedded manipulation; treat as a research surface, not a tradable signal.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2608.21888v1 | Short-horizon mean reversion in cryptocurrency markets: a matched cross-market measurement | 2026 |
| 2608.26158v1 | A Frequency-Controlled Comparison of Tick- and Minute-Based Information Bars for Cryptocurrency Markets | 2026 |
| 2606.23337v1 | When Staking Rewards Compound: Measuring the Impact of Ethereum's Pectra Upgrade | 2026 |
| 2602.14860v1 | Predicting the success of new crypto-tokens: the Pump.fun case | 2026 |
| 2511.03314v1 | Multifractality and sample size influence on Bitcoin volatility patterns | 2025 |
| 2507.00575v4 | Pathwise Roughness of Bitcoin Realized Volatility: Stability Across Time, Sampling, and Volatility Measures | 2025 |
