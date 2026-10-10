# market-simulation-agent-models — learnings from the q-fin.ST corpus
`109` of 4372 corpus papers matched this category; this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **The corpus is dominated by agent-based-market (ABM) simulation and LLM multi-agent equity research, not by validated agent alpha.** 109 tags span three distinct literatures: (a) *generative market simulators* (multi-agent order-book/ABM: `Scalable Agent-Based Modeling for Complex Financial Market Simulations` 2312.14903, `Multi-Asset Spot and Option Market Simulation` 2112.06823, `Agent Trading Arena` 2502.17967), (b) *LLM multi-agent investment systems* (TradingAgents, Trading-R1, FinRobot 2411.08804, MarketSenseAI), and (c) *long-horizon Monte-Carlo wealth simulators*. Only a handful of the LLM papers produce portfolio-level, cost-aware, statistically tested evidence; most are demo-grade.
- **The single strongest evaluation methodology in the three LLM papers read is a Monte-Carlo selection null that holds universe, dates, count and weighting fixed.** On the S&P 500 cohort (467 names, 19 monthly dates, Sep 2024–Mar 2026) the equal-weight strong-buy book returns +2.18%/month vs a +1.15% equal-weight universe benchmark, +25.2 pp compound, at the 99.7th percentile of 10,000 same-sized random draws, *p* = 0.003; the S&P 100 cohort (35 dates) is directionally consistent (+30.5 pp compound) but **fails significance at *p* = 0.17** because it averages only ~10 picks/month (arXiv:2604.17327).
- **No single agent carries the edge; attribution is adaptive.** Non-negative least squares (NNLS) of thesis embeddings onto the 4 agent embeddings (agent–agent cosines 0.46–0.79) reconstructs the thesis at mean cosine 0.944, and the winning agent rotates (Fundamentals 5/19 dates, Macro 6/19, Dynamics 5/19, News 3/19) with the macro regime (arXiv:2604.17327).
- **The ordinal recommendation carries genuine cross-sectional rank information but only at the date level.** Ordinal-score ICIR = +0.489, *t* = +2.13, *p* = 0.024 (*T* = 19); the individual agent date-level ICs are all insignificant (*p* > 0.08) (arXiv:2604.17327).
- **Long-horizon crypto buy-and-hold is, on a market-wide basis, a fantasy of survivorship bias.** 480,000,000 Monte-Carlo episodes over 378 non-stablecoin tokens give a 731–1095-day median excess return of **−28.4%**, CVaR₁% ≈ 1.08 (tail scenarios wipe out principal *and* the 1-month T-bill opportunity cost), >50% of outcomes losing >10% beyond day 181, yet a top-quartile mean of **+1326.7%** (arXiv:2512.02029).
- **For long-horizon simulations the drift, not the volatility, is the binding input.** Diffusive noise grows as √ΔT but the deterministic drift grows as ΔT; the crossover is ΔT× = (σ₁ᵧ/µ₁ᵧ)² — 0.42 yr for US short-duration govt, 2.51 yr for US large cap, 59.3 yr for global core infrastructure (24-yr sample 2000-01-31…2024-02-29) (arXiv:2511.18125).
- **Sentiment, not realized risk–return, is the stable long-horizon predictor in crypto.** A 1σ shock to the 24-week EMA of the Fear & Greed Index lowers forward top-quartile mean excess returns by 15–22 pp and median returns by 6–10 pp at 1–3 yr horizons; endogenous realized risk–return metrics have economically negligible population-level effects (arXiv:2512.02029).
- **Two of the three LLM multi-agent papers are demo-grade and are flagged as such.** AlphaAgents evaluates 15 tech stocks over a **4-month** window (Feb–May 2024), equal-weighted, no transaction-cost model, no null distribution, no significance test, benchmark = the same 15 stocks (arXiv:2508.11152). The Chinese-REIT paper is stronger (28 funds, 12-month out-of-sample backtest, 0.03% cost) but reports "significantly outperform" without a significance test and its win-rates are uncorrected for multiplicity across 28 assets (arXiv:2602.00082).
- **One assigned paper is off-topic.** `Multi-Agent Stock Prediction Systems` (arXiv:2502.15853) contains **no multi-agent system and no simulation**: it is a TSLA LSTM/GRU/attention accuracy comparison. Its headline ("attention 95.15% accuracy") is a leakage artifact — the split is the last 30 calendar days and bidirectional/seq2seq models are granted *future* context — so it is reported here only as a cautionary example, not as evidence.

## 2. Implementable formulas & algorithms

### 2.1 Monte-Carlo selection null (the corpus's best agent-evaluation primitive)
**Purpose.** Test whether a signal's buy basket beats *random selection from the same universe on the same dates*, isolating selection skill from market/sector beta and position count.
**Formula.** Signal basket $S_d \subseteq U_d$ with $n_d = |S_d|$:
$$R_d^{SB} = \frac{1}{n_d}\sum_{i\in S_d} r_{i,d}^{(1m)}, \qquad R_d^{EW} = \frac{1}{|U_d|}\sum_{i\in U_d} r_{i,d}^{(1m)}$$
For each of $K$ simulations draw $n_d$ names uniformly *without replacement* from $U_d$; aggregate mean-monthly $\bar R^{(k)}=\frac1T\sum_d R_d^{(k)}$ and compound $C^{(k)}=\prod_d(1+R_d^{(k)})-1$. One-tailed empirical $p = K^{-1}\sum_k \mathbf 1[\bar R^{(k)} \ge \bar R^{SB}]$.
**Inputs.** Universe membership per date; 1-month forward total returns.
**Parameters/defaults.** $K = 10{,}000$, fixed seed, same $n_d$ per date, equal weights. Paper uses monthly (first-Friday) cadence and 1-month buy-and-hold returns.
**Observed effect.** S&P 500 *p* = 0.003 (99.7th pct, +1.02%/mo excess ≈ +12.4% annualised alpha); S&P 100 *p* = 0.17. Win rate 11/19 and 20/35 months.
**Failure modes.** (i) Underpowered when $n_d$ is small (S&P 100: ~10 names → wide null); (ii) a linearity fact — $E[R^{EW}]$ = MC null mean, so "beating EW" and "beating the null" are the same statement; (iii) gross of costs, so it is an upper bound on tradable alpha.

### 2.2 Date-level Information Coefficient & ICIR
**Purpose.** Measure cross-sectional rank skill and attach a *t*-test with the correct effective sample size.
$$IC_d = \mathrm{Spearman}(x_{i,d}, r_{i,d}^{(1m)}), \quad \overline{IC}=\frac1T\sum_d IC_d, \quad ICIR=\frac{\overline{IC}}{\mathrm{std}(IC_d)}, \quad t = ICIR\sqrt{T}$$
**Inputs.** A per-stock signal $x$ (ordinal score, or NNLS agent weight) and forward returns, restricted to the *actionable long universe* (buy + strong-buy only).
**Parameters/defaults.** Non-overlapping monthly windows; significance threshold $|ICIR| > t_{0.05}/\sqrt T$ (0.47 at *T* = 19; 0.34 at *T* = 35). Pooled IC (all stock-dates) is reported **directionally only** because within-date cross-sectional dependence invalidates its *p*-value.
**Observed effect.** Score ICIR +0.489 (*p* = 0.024); Fundamentals pooled IC +0.052 vs score pooled IC +0.006 (continuous weights encode ~9× finer cross-sectional information than the discrete label).
**Failure modes.** Pooled IC conflates stock fixed effects with timing; short *T* makes ICIR thresholds fragile; excluding hold/sell stocks changes the sample by ~74 stocks/date (S&P 500) vs ~19 (S&P 100).

### 2.3 NNLS agent attribution
**Purpose.** Attribute a synthesised thesis to its specialist agents, correcting for semantic collinearity that breaks univariate cosine similarity.
$$\hat{\mathbf w}_{i,d} = \arg\min_{w \ge 0}\ \lVert t_{i,d} - A_{i,d} w\rVert_2^2, \qquad A_{i,d}=[a^{news}|a^{fund}|a^{dyn}|a^{macro}] \in \mathbb R^{D\times 4}$$
**Inputs.** Thesis and per-agent summary embeddings ($D = 1536$, OpenAI `text-embedding-3-small`).
**Parameters/defaults.** Weights normalised to sum to 1; uniform fallback when no feasible positive solution exists; validated by thesis–reconstruction cosine $C^{TR}$ (accept if ≈0.94) and by Spearman agreement with univariate cosines ($\rho_s$ 0.53–0.83).
**Observed effect.** $C^{TR}$ = 0.944 (detects well-posedness); News has the highest thesis cosine (0.903) but near-zero pooled IC (+0.004), proving cosine alone is misleading.
**Failure modes.** Ill-conditioned when agents are highly collinear; tiny negative weights must be clipped; attribution is *descriptive* — it does not establish causality.

### 2.4 Long-horizon SAA Monte-Carlo process (drift-dominant regime)
**Purpose.** Generate plausible multi-decade wealth distributions for index-level model portfolios.
$$\mathbf r(t+\delta t) = \boldsymbol\mu(t) + \Sigma(t)^{1/2}\,\boldsymbol\epsilon(t+\delta t), \qquad \mathbf p(t+\delta t)=\mathbf p(t)\odot(1+\mathbf r(t+\delta t))$$
with the random-walk scaling $\mu_{\delta t}=\mu_{1y}\,\delta t/1y$, $\sigma_{\delta t}=\sigma_{1y}\sqrt{\delta t/1y}$; crossover $\Delta T_\times=(\sigma_{1y}/\mu_{1y})^2$, Sharpe $=\sqrt{1y/\Delta T_\times}$.
**Components to add (all reported as necessary):** (i) **drift uncertainty** — sample $\mu$ from a normal centred on the CMA value, because a drift error $\delta\mu$ costs $\Delta T\cdot\delta\mu$ (deterministic, beats the √ΔT diffusion); (ii) **negative return correlation (NRC)** at multi-year scale (lagged drift term), which "stabilises" the long-horizon dispersion; (iii) **LMARCH** heteroskedasticity with *shared* parameters across the cross-section (parameter count stays $O(n^2)$, not $O(n^4)$); (iv) **multivariate non-central Student** innovations for fat tails and down-side asymmetry; (v) absorbing state at $p_{min}=p(0)/100$.
**Parameters/defaults.** Time step δt = 1 month (allowed 1 day–1 year); correlation matrix must be positive definite; 24-yr calibration sample.
**Observed effect.** For horizons ≳15 yr the process is always drift-dominated; ignoring drift uncertainty materially mis-states the terminal distribution.
**Failure modes.** (i) CMA drift errors dominate the answer; (ii) non-PSD correlation matrices cannot be square-rooted; (iii) at ~20 independent returns per 20-yr sample the empirical validation is inherently weak (author states validation is "not comfortable").

### 2.5 Survivorship-aware Monte-Carlo wealth simulator
**Purpose.** Estimate the *full* distribution of buy-hold-sell outcomes net of fees and the T-bill opportunity cost, including delisted assets.
$$\tau_i \sim \mathrm{DiscreteUniform}\{\ell,\dots,h\},\quad s_i \sim \mathrm{Unif}\{0,\dots,T-\tau_i-1\},\quad c_i \sim \mathrm{Unif}\{0,\dots,C-1\}$$
$$P_i^{buy}=L_{s_i,c_i}+U_i^{(1)}(H_{s_i,c_i}-L_{s_i,c_i}),\quad P_i^{sell}=L_{e_i,c_i}+U_i^{(2)}(H_{e_i,c_i}-L_{e_i,c_i})$$
$$G_i=(1-\phi)^2\,\frac{P_i^{sell}}{P_i^{buy}}-1,\qquad R_i^{rf}=\exp(\gamma_{e_i}-\gamma_{s_i-1}),\qquad X_i=G_i-R_i^{rf}$$
**Inputs.** Longest available daily HLCV per asset (including since-delisted ones), daily T-bill rate.
**Parameters/defaults.** $\phi = 0.001$ per side; six horizon bands 1–30, 31–90, 91–180, 181–365, 366–730, 731–1095 days; 10M episodes/band/basket = 480M; validity filter $H\ge L>0$; 50-consecutive-failure cap.
**Observed effect.** ALL-basket 731–1095 d: median excess −28.4%, top-25% mean +1326.7%, CVaR₁% ≈ 1.08; P(loss > 10%) > 50% beyond 181 d.
**Failure modes.** (i) Survivorship enters through the *asset panel*, not the simulation — delisted tokens must be retained; (ii) intraday U(0,1) price draw is a modelling assumption; (iii) token-level results (BTC) are *not* generalisable to the market basket — this is the whole point of the study.

### 2.6 Bayesian multi-horizon local projection for regime/sentiment effects
**Purpose.** Quantify how macro-sentiment shocks move forward realized risk–return distributions without specifying a full VAR.
**Pipeline (as reported).** Unit-root tagging (DF-GLS, KPSS, Zivot–Andrews) → strictly-causal transforms (level / rolling-linear detrend with $L$ = 52 weeks / fractional differencing $d=0.5$, $K=200$) → EMA+VOL features at $w \in \{4,8,12,24\}$ weeks → purged, gap-separated CV (`TimeSeriesSplit`, gap $g(h)=\lceil h/7\rceil+1$) → multitask ElasticNet ($\rho=1/2$) → non-overlapping block bootstrap ($b=\min(20,\max(4,\text{round}(n^{1/3})))$, $R=1000$) stability selection ($\tau_g,\tau_c$) → Bayesian LP (NUTS, 4 chains, `target_accept=0.95`, `max_treedepth=12`).
**Observed effect.** 24-week EMA of Fear & Greed: −15 to −22 pp on forward top-quartile mean excess, −6 to −10 pp on median, per 1σ, over 1–3 yr; DOGE ≈ 3× more sensitive than majors.
**Failure modes.** Unvalidated on out-of-sample crisis periods; causal standardisation clipped at $\varepsilon=10^{-2}$; requires long history the corpus only partially has.

### 2.7 Volatility-adaptive label thresholds + teacher-distilled decision agent (REITs MAS)
**Purpose.** Turn a low-volatility multi-agent analysis into discrete, supervise-able labels and a closed analysis→prediction→decision→execution loop.
$$\theta_t=\max\!\big(q_L,\ \min(\sigma_t\cdot m_t,\ q_U)\big),\qquad m_t=m_0 a_{high}\ \text{if}\ \tfrac{\sigma_t^{(short)}}{\sigma_t^{(long)}}>\tau_{high},\ \text{else } m_0 a_{low}\ \text{if}<\tau_{low},\ \text{else } m_0$$
$$R_k=\frac{P_{t+k}-P_t}{P_t},\qquad \text{label}_k=\text{up if } R_k\ge\varepsilon_k,\ \text{down if } R_k\le-\varepsilon_k,\ \text{else side},\quad \varepsilon_k=\sqrt k\,\theta_t$$
Two-stage training: SFT cross-entropy on teacher (DeepSeek-R1) reasoning traces, then GSPO RL with $R=\alpha\cdot\text{correctness}+\beta\cdot\text{FormatScore}$, $\alpha+\beta=1$.
**Parameters/defaults.** $N_v \approx 30$ d; quantiles $(q_L,q_U)=(0.30,0.70)$; $(\tau_{high},\tau_{low})=(1.4,0.7)$; horizons $k\in\{1,5,20\}$; ~33% of days classified sideways; cost 0.03%/trade.
**Observed effect.** DeepSeek-R1 agent CR 15.50% / Sharpe 1.71 / MDD −4.09%; fine-tuned Qwen3-8B CR 13.75% / Sharpe 1.77 / MDD −3.46%; Buy&Hold CR 10.69% / Sharpe 0.75 / MDD −11.12%; smaller-drawdown win rate 100% / 96.4% across 28 funds.
**Failure modes.** (i) No significance test on the outperformance; (ii) one asset class, 28 funds, 12 months, one regime; (iii) agent strategies still drew down synchronously in Apr/May/Aug 2025 corrections and missed the Mar–Apr 2025 acceleration (author-acknowledged); (iv) reward "correctness" optimises direction, not P&L.

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Universe daily OHLCV history (MC null, IC, SAA calibration) | https://eodhd.com/api/eod/AAPL | core_stock_apis | eodhd | ok |
| Same, secondary/tertiary sources | https://api.tiingo.com/tiingo/daily/AAPL/prices ; https://api.twelvedata.com/time_series ; https://api.massive.com/v2/aggs/ticker/AAPL/prev | core_stock_apis | tiingo / twelvedata / massive | ok |
| Universe & cross-listing symbol lists (fixed cohorts) | https://eodhd.com/api/exchange-symbol-list/US | exchange_symbols | eodhd | ok |
| News agent input (ticker news) | https://eodhd.com/api/news ; https://api.benzinga.com/api/v2/news ; https://newsapi.org/v2/everything | news_data | eodhd / benzinga / newsapi | ok |
| News sentiment (News agent) | https://eodhd.com/api/sentiments ; https://www.alphavantage.co/query | news_sentiment | eodhd / alpha_vantage | ok / ok |
| News sentiment (fallback) | https://api.gdeltproject.org/api/v2/doc/doc | news_sentiment | gdelt | rate_limited |
| Fundamentals / financial statements (Fundamentals agent) | https://api.tiingo.com/tiingo/fundamentals/AAPL/statements ; https://www.alphavantage.co/query | fundamental_data | tiingo / alpha_vantage | ok |
| 10-K/10-Q primary document text (RAG tool) | — | sec_filings (`sec_edgar`) | sec_edgar | **gap** — category routed in `categories.py` but no live-probed row in `endpoints.json` |
| Macro agent inputs (rates, CPI, etc.) | https://api.stlouisfed.org/fred/series/observations | macro_data | fred | ok |
| 1-month T-bill opportunity cost (HODL) & risk-free | https://api.stlouisfed.org/fred/series/observations (T-bill series) | macro_data | fred | ok — note the dedicated `risk_free_curve` row (federal_reserve) failed probe (`connect`) |
| Analyst ratings (Sentiment agent) | https://api.benzinga.com/api/v2.1/calendar/ratings | analyst_ratings | benzinga | ok |
| Earnings calendar (event windows) | https://api.benzinga.com/api/v2.1/calendar/earnings | earnings_calendar | benzinga | ok |
| Macro-sentiment / event probabilities | https://gamma-api.polymarket.com/markets | prediction_markets | polymarket | ok |
| Crypto asset panel (378 tokens incl. delisted) | — | — | — | **gap** — no probed crypto endpoint; moomoo gateway unprobed/offline, yfinance/CoinGecko not in inventory |
| Crypto Fear & Greed Index (24-wk EMA) | — | — | — | **gap** — alternative.me not in inventory; closest live substitutes are Polymarket (above) and FRED macro series |
| Agent theses & specialist summaries (NNLS attribution) | — | — | — | **gap** — produced internally; requires an embedding model (`OPENAI_API_KEY`) |
| Forward 1-month returns, IC, ICIR, MC null | derived from OHLCV above | core_stock_apis | fmp / eodhd / … | ok (derived) |

## 4. Pitfalls, validation and measurement

- **Look-ahead / knowledge leakage is the dominant threat for LLM agents.** MarketSenseAI's defence is *live generation* — every signal produced at its observation date, with the S&P 500 cohort entirely after the LLM pre-training cut-off (arXiv:2604.17327). Any FinRobot backtest that replays a prompt over historical text without pinning the model's cutoff is contaminated. Non-negotiable test: regenerate signals at each date with only information available then.
- **Random train/test splits and bidirectional context leak the future.** `LSTM-Bidirectional` / `Seq2Seq` "95% accuracy" on a random-looking 30-day holdout (arXiv:2502.15853) is the canonical leakage demo; it teaches nothing about live skill. Validation must be strictly chronological and, for horizon-h forecasts, gap-separated by $g(h)=\lceil h/7\rceil+1$ (arXiv:2512.02029).
- **Survivorship bias silently inverts conclusions.** The crypto panel spans 378 tokens *including* ones that died; the resulting market-wide median excess return is **−28.4%** while the top quartile is **+1326.7%** (arXiv:2512.02029). Any equity agent backtest must retain delisted tickers (EODHD/tiingo history) or state the bias explicitly.
- **Short effective sample sizes overstate significance.** *T* = 19 monthly dates gives a 0.47 ICIR significance floor; *p* = 0.003 on 19 dates is evidence "from a specific live period rather than asymptotic proof," and the market-beta robustness check (α = +1.18%/mo, *t* = 1.45, *p* = 0.17) is itself underpowered (arXiv:2604.17327). Report date-level *t*-tests, never pooled-IC *p*-values.
- **Agent systems are regime-dependent, and bullish windows flatter high-risk agents.** AlphaAgents' risk-neutral book beats its benchmark only because Feb–May 2024 was a tech bull run, while the risk-averse book *underperforms* by excluding volatile names (arXiv:2508.11152). A single-regime backtest is not evidence. Sub-period / regime-split reporting is required.
- **Vendor self-evaluation and demo-grade scopes must be labelled.** The MarketSenseAI study is authored by the system's developer (Alpha Tensor Technologies) and cannot be independently reproduced because the live signals are proprietary; AlphaAgents is explicitly "not yet a full portfolio optimization engine" on 15 names/4 months. Treat both as *methodological templates*, not as transferable alpha claims.
- **At long horizons, validate the drift, not the volatility model.** Because drift error compounds as ΔT while diffusion grows as √ΔT, a simulator that tunes GARCH parameters but freezes the CMA drift is mis-prioritised; the paper's own graphs show the terminal distribution is dominated by the drift (arXiv:2511.18125).
- **A sound implementation test-set for FinRobot:** (1) MC selection null with matched universe/date/count; (2) date-level ICIR *t*-test on the actionable universe; (3) NNLS reconstruction cosine ≥ ~0.9 and cosine/weight Spearman agreement; (4) sub-period stability of the winning-agent rotation; (5) net-of-cost (≥ 20 bps/mo drag at 35-name monthly rebalancing is the reported headroom) and a beta/Jensen-α robustness regression; (6) for simulators, folded-CDF comparison of simulated vs empirical tails at increasing ΔT and the ΔT× crossover diagnostic.

## 5. Recommended first implementation in FinRobot

1. **Agent-signal validation harness (highest value).** Wrap every FinRobot recommendation in the Monte-Carlo selection null (§2.1) + date-level IC/ICIR (§2.2), with matched universe/date/count and a fixed seed. Data: OHLCV from `core_stock_apis` (eodhd/tiingo/twelvedata) + `exchange_symbols` for cohorts. Expected value: turns FinRobot's agent prose into a falsifiable portfolio-level claim and immediately exposes over-confident signals. Risk: small *T* needs ≥ 30 monthly dates before trusting ICIR. Effort: **M**.
2. **Live-generation protocol guardrail.** Pin every agent call to an as-of date and refuse to evaluate any signal whose inputs post-date it; log the LLM cutoff. Data: none (procedure). Expected value: eliminates the corpus's #1 false-positive source. Risk: none, pure hygiene. Effort: **S**.
3. **NNLS attribution for FinRobot's own agent crew.** Embed thesis + each specialist's output (`OPENAI_API_KEY`, 1536-d), solve the NNLS problem, publish weights and $C^{TR}$; surface the rotating "winning agent". Data: internal embeddings (**gap** in the provider layer — build in-repo). Expected value: interpretable attribution and a regime-rotation monitor. Risk: collinear agents degrade attribution. Effort: **M**.
4. **SAA long-horizon simulator module.** Multivariate process with random-walk scaling, drift uncertainty, NRC, LMARCH and non-central-Student innovations, absorbing state at p(0)/100. Data: index OHLCV + FRED macro + `federal_reserve`/FRED risk-free (note the `risk_free_curve` probe failure). Expected value: retirement/goal-probability answers with honest uncertainty; appropriate for the app's planning surface. Risk: drift uncertainty is the answer, so *must* be propagated. Effort: **L**.
5. **Survivorship-aware exposure stress test.** Reuse §2.5's Monte-Carlo wealth sampler for the equity universe FinRobot covers, retaining delisted names, net of fees + T-bill cost, reporting median, CVaR₁% and P(loss>10%). Data: long OHLCV incl. delisted (eodhd/tiingo) + FRED T-bill. Expected value: converts single-name "look how it performed" narratives into distributional risk statements. Risk: delisted-history coverage is the weak link. Effort: **M**.
6. **Macro-sentiment overlay (lightweight).** Reproduce the Fear & Greed EMA effect direction with available substitutes — Polymarket event markets + FRED macro — as a forward-excess-return conditioner rather than a signal generator. Data: `prediction_markets` (polymarket, ok) + `macro_data` (fred, ok). Expected value: cheap, robust long-horizon context flag. Risk: **crypto Fear & Greed is a gap**, so only the analogue is testable; do not claim the 15–22 pp numbers. Effort: **S**.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2604.17327v1 | Signal or Noise in Multi-Agent LLM-based Stock Recommendations? | 2026 |
| 2602.00082v1 | Design and Empirical Study of a Large Language Model-Based Multi-Agent Investment System for Chinese Public REITs | 2026 |
| 2511.18125v1 | Random processes for long-term market simulations | 2025 |
| 2512.02029v1 | HODL Strategy or Fantasy? 480 Million Crypto Market Simulations and the Macro-Sentiment Effect | 2025 |
| 2508.11152v1 | AlphaAgents: Large Language Model based Multi-Agents for Equity Portfolio Constructions | 2025 |
| 2502.15853v1 | Multi-Agent Stock Prediction Systems: Machine Learning Models, Simulations, and Real-Time Trading Strategies *(off-topic: no MAS, no simulation; leakage-grade results)* | 2025 |
