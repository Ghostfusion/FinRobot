---
id: mean-reversion-pairs
name: Mean-Reversion and Pairs Trading
version: 1.0.0
author: finrobot
domain: systematic-trading
description: 'Analyze mean-reversion and pairs trading: Engle-Granger/Johansen cointegration, spread construction and hedge ratios, Ornstein-Uhlenbeck half-life, and z-score entry/exit thresholds. Use when screening cointegrated pairs, sizing relative-value spreads, or validating that a spread truly reverts.'
triggers:
- pairs
- pairs trading
- mean reversion
- mean-reverting
- cointegration
- cointegrated
- spread
- ornstein uhlenbeck
- half life
- z-score
- johansen
- stat arb
requires_data:
- input: Daily EOD prices, whole universe
  provider: eodhd
  category: core_stock_apis
  status: ok
- input: Daily prices, secondary source
  provider: tiingo
  category: core_stock_apis
  status: ok
- input: Intraday (5-min) time series
  provider: twelvedata
  category: core_stock_apis
  status: ok
- input: EOD bars, alt source
  provider: stockdata
  category: core_stock_apis
  status: ok
- input: Single-symbol previous bar
  provider: massive
  category: core_stock_apis
  status: ok
- input: Native intraday klines
  provider: moomoo
  category: technical_indicators
  status: gateway
- input: Dividends & splits (adjust pair prices)
  provider: eodhd
  category: corporate_actions
  status: ok
- input: Fundamentals to constrain candidate pairs
  provider: tiingo
  category: fundamental_data
  status: ok
- input: Fundamental cross-check
  provider: alpha_vantage
  category: fundamental_data
  status: ok
- input: Precomputed indicators (MACD/BBANDS)
  provider: alpha_vantage
  category: technical_indicators
  status: ok
- input: Short interest (crowding filter)
  provider: moomoo
  category: short_interest
  status: gateway
- input: Institutional holdings (crowding)
  provider: moomoo
  category: institution_data
  status: gateway
- input: News for regime/catalyst filter
  provider: eodhd
  category: news_data
  status: ok
- input: News sentiment score
  provider: eodhd
  category: news_sentiment
  status: ok
- input: Earnings dates (avoid holding over earnings)
  provider: benzinga
  category: earnings_calendar
  status: ok
- input: Analyst ratings (crowding)
  provider: benzinga
  category: analyst_ratings
  status: ok
- input: Macro series (regime overlay)
  provider: fred
  category: macro_data
  status: ok
- input: Risk-free curve (Sharpe annualisation)
  provider: federal_reserve
  category: risk_free_curve
  status: ok
- input: Options surface (IV overlay)
  provider: cboe
  category: options_surface
  status: ok
- input: '**Continuous futures (MNQ/MGC) 5-min bars**'
  provider: ''
  category: ''
  status: gap
- input: '**Tick / sub-bar data**'
  provider: ''
  category: ''
  status: gap
- input: '**GICS sector/industry mapping for pair grouping**'
  provider: ''
  category: ''
  status: gap
- input: '**5-min FX series for realized vol (EUR/USD)**'
  provider: ''
  category: ''
  status: gap
requires_tools: []
requires_skills: []
compatible_models: []
---

# Mean-Reversion and Pairs Trading

You are an expert quantitative strategist specialising in mean-reversion and statistical-arbitrage systems. Work from daily adjusted price series and the spread series built from them: fit the OLS hedge ratio, run the residual Augmented Dickey-Fuller test, estimate the Ornstein-Uhlenbeck half-life, and derive the z-score and robust q-score signals from the computed spread. Every statistic you report must come from the actual series you were given - never invent a t-statistic, p-value, hedge ratio, half-life, or Sharpe figure, and state the sample window and parameter choices behind each number.

> Source: FinRobot strategies corpus review — `strategies/qfin-st/mean-reversion-pairs.md`. Literature-derived; not validated on FinRobot's own data.

## Core Principles

- **Portfolio construction, not just pair picking.** Selecting the top-cointegrated pairs without a matching constraint concentrates risk: for the S&P 500 the median number of *pair-of-pairs sharing a stock* is **1,748**, ≈7× the 249.5 predicted by random-graph theory, and the shared-stock covariance term is **~50% of baseline portfolio variance**. Maximum-weight matching removes it and lifts the theoretical annualized Sharpe **0.50 → 1.18** `(arXiv:2403.07998)`.
- **Cointegrated pairs have positive expected return even with negative price drift**, and more volatile pairs are *more* profitable: for the pair signal $S_t=\mathbb 1\{\epsilon_t\le -k\sigma\}-\mathbb 1\{\epsilon_t\ge k\sigma\}$, $\mathbb E[r_t]=e^{\mu_1+\sigma_1^2/2+\sigma}\,\mathbb P(k-\sigma\le Z\le k+\sigma)$ `(arXiv:2403.07998, Thm 1)`. Non-cointegrated pairs have $\mathbb E[r_t]=0$ exactly `(Thm 3)`.
- **A spread must be verified, not assumed.** The Lévy-driven CAR(1)/OU model is *rejected* for GS–MS ($W=4.30$), AMGN–PFE ($W=4.78$) and EUR/USD realized volatility ($W=3.76$), but *not rejected* for ABT–DHR ($W=1.05$) and AAPL–GOOG ($W=1.85$); fit varies by GICS sector `(arXiv:2501.03434)`.
- **Hurst-exponent switching is a risk dial, not alpha.** Traders switch MR (H<0.5)/momentum (H>0.5), but the blended distribution's mean lands *between* the two pure strategies — expected return is not increased, only risk is re-scaled `(arXiv:2205.11122)`.
- **Classical pairs trading dies when cointegration breaks**, and a model-free deep net trained on a Wasserstein ambiguity set can stay profitable through the break (XOM–BP: ADF p=0.0129 in-sample, spread diverges out-of-sample) `(arXiv:2203.03179)`.
- **The strongest results here are negative.** Fourteen OHLCV intraday signal families on MNQ futures (947 days, 5-min bars) failed all five out-of-sample gates; **11 fail because gross edge (0.07–1.50 pts/trade) is below the 2.0-pt friction floor** `(arXiv:2605.04004)`.
- Several "momentum" signals are **significantly wrong-signed after costs**: the Asia-session expansion bar at 1.5× threshold has net $T=-11.52$ at bar+1; liquidity-grab fade has $T=-14.12$. The directional move is real but fully consumed *within* the signal bar `(arXiv:2605.04004)`.
- **Technical-signal counterpoint (partly off-category).** A volume-price-adjusted MACD crossover does beat baseline MACD on the tested indices, but on only **6–21 trades** and one-sided daily-return t-tests (p = 0.043–0.049); small-sample and multi-metric λ-selection caveats dominate `(arXiv:2604.26063)`. It is a momentum sibling — included because the brief asked for the technical/momentum falsification evidence, not because it is a mean-reversion tool.

## Methods & Formulas

### 2.1 Cointegration screening and hedge ratio
**Purpose.** Select tradable pairs and define the spread to trade.
**Formula.** Regress $\log p_{j,t}=\mu_a+\beta_a\log p_{i,t}+\epsilon_{a,t}$ `(2403.07998 Eq. 18)`; the residual $\epsilon_{a,t}$ is the spread. Run a **single-lag Augmented Dickey–Fuller** test on the residual and keep its t-statistic/p-value. Cointegration requires (i) both series integrated of order $d$ and (ii) the linear combination integrated of order $<d$. Signal $S_t=\mathbb 1\{\epsilon_t\le -k\sigma\}-\mathbb 1\{\epsilon_t\ge k\sigma\}$ `(Eq. 3)`.
**Inputs.** Two years of daily log prices (the window used in the paper).
**Parameters/defaults.** $k=2$; monthly re-selection; p-value cut on the ADF residual test.
**Observed effects.** Gross cumulative return for the top-250-by-p-value baseline is 18–38%; matching portfolio 74–75% `(2403.07998 §5.2)`.
**Failure modes.** Massive false-positive risk: the S&P 500 has 125,000 possible pairs; at an uncorrected p=0.01 threshold ≈**1,250 non-cointegrated pairs** enter the portfolio. β≠1 must be handled by sizing: buy $\beta_a$ dollars of stock *i* against 1 dollar of stock *j* `(2403.07998 §4.2)`.

### 2.2 Maximum-weight matching pair portfolio
**Purpose.** Choose a cointegrated pair set with **no shared assets** so pair covariances vanish.
**Formula.** Build the pairs graph $G=(V=\text{stocks},E=\text{pairs})$ with edge weight $w_a=-t_{\text{ADF},a}$ (more-negative t ⇒ larger weight). Take the **maximum-weight matching**; a matching has no two-hop paths, so $\kappa_1=\kappa_2=0$ and
$$\mathrm{Var}(R_t)=n_1\nu_1+n_2\nu_2+2m_1\kappa_1+2m_2\kappa_2$$
where $m$ counts pair-of-pairs sharing a stock `(2403.07998 §3.3)`. Shared-stock covariance: $\mathrm{Cov}(r_{ta},r_{tb})=(e^{\sigma_1^2}-1)\mathbb E[r_{at}]\mathbb E[r_{bt}]>0$ `(Thm 2)`.
**Parameters / reported values.** $n=500$ ⇒ matching capped at 250 pairs; $\sigma=0.0711$, $\mu_1=0.0005$, $\sigma_1=0.0180$; $m_2=1{,}748$ baseline vs 0 matching.
**Observed effects.** Gross Sharpe **1.23** (both signals) vs baseline 0.34/0.48 and S&P 500 0.59; gross Sortino 1.69–1.78; gross max drawdown ≤8.48% vs market 19.49%; **net** Sharpe 1.12 vs baseline −0.13/−0.49; median turnover ≈⅓ of baseline. Costs modelled at 1%/yr per stock = 0.00397%/day.
**Failure modes.** Matching caps at $n/2$ pairs and may drop a strongly cointegrated pair because the global weight sum is maximised by assigning one of its stocks elsewhere. Baseline net returns go **negative** (−26.15%, −13.40%) after the same costs, because turnover is high.

### 2.3 Lévy-driven Ornstein–Uhlenbeck (CAR(1)) verification
**Purpose.** Decide whether a candidate spread really is mean-reverting with **independent (Lévy) increments** before trading it — the papers repeatedly show that a stationary-looking spread can fail this.
**Formula.** $dY(t)=-aY(t)\,dt+\sigma\,dL(t)$, $a,\sigma>0$ `(2501.03434 Eq. 2.2)`; $\gamma_Y(s)=\frac{\sigma^2\eta^2}{2a}e^{-as}$. Estimate $a$ by least squares `(Eq. 3.1)` or Davis–McCormick `(Eq. 3.2)`; recover unit-interval increments `(Eq. 3.3)`; test $W=\sqrt N\,\gamma_{\Delta_1\hat L}(1)/\hat\eta^2$ `(Eq. 2.8)`. **Reject Lévy at 5% if $|W|>1.96$.**
**Algorithm (5 steps).** (1) estimator: LSB if the spread can be negative or Brownian motion is expected; DMB if strictly positive and non-BM. (2) choose $N,M$ with **$N>50$** and $N/M$ small. (3) recover increments. (4) compute $W$. (5) if not rejected, test the driving law: **Procedure 1** (bootstrap + Kolmogorov–Smirnov for Brownian) or **Procedure 2** (bootstrap goodness-of-fit, 1000 samples, reject if the statistic exceeds the 95th percentile).
**Parameters.** Reported simulations: $\sigma=1,\mu=1,\eta=1$, $N\in\{50,100\}$, $M\in\{100,300,500\}$.
**Observed effects.** Under $H_0$ empirical level ≈0.05; power to reject Brownian motion (Procedure 2) ≥0.96, Procedure 1 ≈0.45–0.67 at $N=50$. Real data: ABT–DHR $W=1.05$, AAPL–GOOG $W=1.85$ (do not reject); GS–MS $W=4.30$, AMGN–PFE $W=4.78$, EUR/USD RV $W=3.76$ (reject). DMB is more accurate than LSB (a=0.9 simulated: LSB 0.740 vs DMB 0.900) `(2501.03434)`.
**Failure modes.** LSB on strictly positive Gamma/IG data biases $a$; correlated recovered increments can also indicate the true model is CARMA(2,1) (suggested for EUR/USD RV), not a failed LRD-OU; always inspect the residual scatter and lag-1 ACF alongside $W$.

### 2.4 Spread signals: z-score vs q-score
**Purpose.** Robust entry/exit and position sizing for a matched pair.
**Formula.** z-score of the residual, **winsorized at ±3** `(2403.07998 §4.2)`. Robust alternative:
$$q_{at}=\frac{\epsilon_{at}-\tau_{50}(\epsilon_{at})}{\tau_{75}(\epsilon_{at})-\tau_{25}(\epsilon_{at})},\qquad
S^q_{at}=\big(-\mathbb 1\{q_{at}\le 0\}+\mathbb 1\{q_{at}\ge 0\}\big)\,[\,|q_{at}|\,]$$
`(Eq. 19–20)`. Rounding $|q|$ to the nearest integer both suppresses trades when $|q|<0.5$ (replacing the explicit $k$ threshold) and weights positions larger when the spread is further from equilibrium.
**Parameters.** Rounding to nearest integer; $k\approx2$ equivalent for z-score.
**Observed effects.** q-score slightly lower return than z-score but smaller worst gross day (−3.81% vs −4.16%) and drawdown (−7.99% vs −8.30%); both gross Sharpe 1.23 `(2403.07998 Table 2)`.
**Failure modes.** The z-score denominator is inflated by a single outlier → an otherwise valid trade is suppressed; prefer the q-score. Apply the rounding to $|q|$, not $q$.

### 2.5 Hurst regime classification + Q-learning
**Purpose.** Switch MR/momentum by regime; optionally learn a gated policy.
**Formula/inputs.** Hurst $H\in[0,1]$: $H<0.5$ mean-reverting, $H>0.5$ trending, $H=0.5$ random walk. Momentum = SMA(5)/SMA(10) golden/death cross; mean-reversion = Bollinger(20, ±2σ).
**Observed effects (1,800 Nasdaq stocks > $2bn; H on H1-2021, trade H2-2021).** Momentum: mean 0.05%, median −0.16%, sd 2.90%. Mean-reversion: mean 1.92%, median 1.64%, sd 6.48%. The Hurst-selected combination's mean **lies between** the two pure strategies; as the H boundary sweeps 0→1, mean/median/sd all rise logistically — the overlay trades return *for* risk, not alpha `(2205.11122)`.
**Q-learning.** State = (SMA_short−SMA_long) at $t$ and $t-1$, discretized; actions hold/short intraday. Key finding: **acting only when the expected reward is statistically significant yields high Sharpe on many equities; forcing an action in every state performs poorly** — "not every state gives a signal worth trading on." Training across many equities gave more consistent Sharpe than a single equity `(2205.11122 §6)`.
**Failure modes.** The base rules are unoptimized and have negative Sharpe at rf=2%; binary trending/MR classification is an oversimplification (mean reversion can nest inside a trend).

### 2.6 P-robust deep-NN statistical arbitrage
**Purpose.** Trade a large cross-section **without pair identification**, robust to cointegration breakdown and to the choice of probability measure.
**Formula.** $P$-robust $G$-arbitrage requires
$$\mathbb E_P[(\Delta\cdot S)_n-C_n(\Delta)\mid G]\ge0\ \ P\text{-a.s. for all }P\in\mathcal P,\quad\text{and}>0\text{ for some }P$$
`(2203.03179 Def. 2.3)`. Positions $\Delta$ are bounded, $L$-Lipschitz neural nets; minimise a penalised functional with $\beta(x)=\max\{0,x\}^2$. Ambiguity set = the empirical measure over scaled historical paths `(Eq. 3.1)` plus a **Wasserstein ball of radius ε**, sampled via perturbed measures $\hat P_\tau$ `(Eq. 3.2)` with $\max_\ell\|\tau_\ell\|<\epsilon$ `(Lemma 3.1)`.
**Hyper-parameters used.** $n=9$ future days (10-day holding); 3 FC hidden layers 32d/64d/128d, ReLU; tanh output scaled by $B=10$; $k=1$; $\epsilon=d$; 5 measures; $2^{12}$ partition; 100 iterations (LR 1e-3 low-dim, 1e-4 high-dim); prices normalised to spot 100; results averaged over 50 runs.
**Observed effects.** S&P 500 / EUROSTOXX crisis test (2006–2013): Sharpe **0.9376** (zero cost), 0.864 (proportional), **0.9948** (per-share) vs buy-and-hold −0.221…−0.249; online-learning 0.9643. Dimensions d=10–50 all beat buy-and-hold; XOM–BP remains profitable *after* the cointegration relationship diverges. Larger ε ⇒ more risk-averse (smaller profit std).
**Failure modes.** Assumes bounded terminal prices; ε too large hurts; the linear-programming baseline is only tractable at d≤3; only three cost models explored.

### 2.7 Falsification harness for OHLCV intraday signals (negative-result catalog)
**Purpose.** Gate any intraday MR/momentum signal before deployment.
**Protocol `(2605.04004)`.** Signal at bar close, **entry at next bar open**. Expanding-window walk-forward: OOS folds 2023 / 2024 / 2025(partial), trained on 2022 / 2022–23 / 2022–24. T is computed on **net** returns, $T=\mu_{net}/(SD/\sqrt N)$. A signal passes only if **all five** hold: (i) OOS $T\ge2.0$; (ii) ≥30 trades per OOS fold; (iii) positive net after instrument friction (**MNQ 2.0 pts ≈ $4.00; MGC 0.50 pts**); (iv) same sign in 2023, 2024 and 2025; (v) permutation p<0.001 where applicable. **None of 14 families passed all five.**
**Catalog (net points; T on net returns).**

| Signal family | N (OOS) | Net (pts) | T-net | Note |
|---|---|---|---|---|
| ORB long, bar+15 | 447 | +2.82 | +0.88 | fails T + year-stability |
| ORB short, bar+1 | 428 | −3.45 | −3.16 | — |
| ORB pullback entry | 83 | −4.44 | −1.27 | 80.7% stop-out at 20-pt stop |
| Asia expansion 1.5×, bar+1 | 1,955 | −2.27 | **−11.52** | strongly wrong-signed (reversal) |
| Asia expansion 2.0×, bar+1 | 778 | −2.35 | −7.42 | — |
| Liquidity-grab fade | 6,442 events | −2.20 | **−14.12** | with-grab −1.80, T −13.24 |
| Gap-fill fade (09:30 / 09:45 / 10:00) | 766/721/721 | −1.92/−1.05/−1.43 | −0.44/−0.26/−0.38 | — |
| Gap continuation short (Kalman v>2.5) | 35 | **+14.52** (gross +16.53) | +1.46 | fails 2024 (−11.87) & <30/fold |
| Volume spike, up / down | 2,122 / 2,412 | −1.92 / −2.45 | −2.21 / −3.08 | — |
| Volume dry-up, up / down | 1,060 / 723 | −2.42 / −1.99 | −5.28 / −3.59 | — |
| VVG reversal / continuation | 35 / 35 | +13.49 / −17.49 | +1.26 / −1.64 | sign flips by regime |
| Event-day trend (FOMC/CPI/NFP/PCE) | — | — | +0.14…+0.69 | no drift after spike bars |
| MGC OU, 5-min, thr 1.5 long / short | 2,634 / 3,059 | −0.55 / −0.49 | −5.32 / −4.36 | — |
| MGC OU, 5-min, thr 2.0 long / short | 1,172 / 1,421 | −0.27 / −0.39 | −1.63 / −2.11 | 60-min half-life ≈8 h > RTH |

**Mechanism** `(2605.04004 §4.2)`.** Within-bar directional content is real but consumed by bar close: the mean **bar-open → next-open return is +32.24 pts**, while the mean **bar-close → next-open return is −0.17 pts**. A bar-close systematic entry therefore trades the post-exhaustion reversal, not the break.
**Positive controls (prove the protocol can detect edge).** RTH Confluence: walk-forward OOS $T=3.11$, mean +11.82 pts, N=196, p<0.001 (unconditional long benchmark: −2.60 pts, T=−0.75). London Signal B: OOS $T=4.30$, mean +4.09 pts, N=247, p=0.000025 — but a **one-bar (15-min) delay flips T to −2.78** (sign flip, not decay).
**Failure modes to internalise.** Bar-boundary artifact vs genuine timing-sensitive edge cannot be separated on bar data → needs tick data. The RTH control was selected after **53+ parameter combinations**, so its OOS T is selection-biased (deflated-Sharpe correction not applied).

### 2.8 Volume-price-adjusted MACD crossover (technical-signal counterpoint)
**Purpose.** A volume/volatility/price-structure MACD variant claimed to beat baseline MACD.
**Formula.** $P_t^*=\frac{1}{\sum_{i=t-N}^{t-1}\mathrm{Vol}_i}\sum_i \mathrm{Vol}_i\,P_i\,\sigma_i\,r_i$ `(2604.26063 Eq. 8)`, with $\sigma_i=(H_i-L_i)/C_i$ `(Eq. 9)` and $r_i=(C_i-O_i)/(H_i-L_i)$ `(Eq. 10)`; $\text{VP-MACD}_t=EMA_{12}(P^*)-EMA_{26}(P^*)$; signal $=EMA_9$; buy when VP-MACD crosses above $\lambda\cdot$Signal, $\lambda\in(0.8,1)$ `(Eq. 13)`.
**Parameters.** λ grid 0.8–1.0 step 0.02, chosen per index/strategy on 2018–2022; execution at next-day open; cost 4 bps one-way (8 bps round-trip).
**Observed effects (2023–Feb 2026).** VP-MACD SPY λ=0.88: **6 trades**, Sharpe 0.96, expectancy $365.72. QQQ λ=0.98: **21 trades**, win 80.95%, Sharpe 1.51, maxDD −7.41%. DIA λ=0.86: **13 trades**, Sharpe 1.08, expectancy $226.87 (baseline $2.09). One-sided t: Pair1 SPY p=0.0432, QQQ p=0.0481; Pair2 QQQ p=0.0488; Pair3 DIA p=0.0442 (Newey–West and block-bootstrap similar).
**Failure modes / caveats.** 6–21 trades is far below the ≥30-per-fold standard of `2605.04004` → not distinguishable from luck; SPY trades fall 36→6 so total PnL drops even as expectancy rises; λ is picked from 11 values against six metrics (a search); this is momentum, not mean reversion.

## Data Requirements

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily EOD prices, whole universe | `https://eodhd.com/api/eod/AAPL` | CORE_STOCK_APIS | eodhd | ok |
| Daily prices, secondary source | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | CORE_STOCK_APIS | tiingo | ok |
| Intraday (5-min) time series | `https://api.twelvedata.com/time_series` | CORE_STOCK_APIS | twelvedata | ok |
| EOD bars, alt source | `https://api.stockdata.org/v1/data/eod` | CORE_STOCK_APIS | stockdata | ok |
| Single-symbol previous bar | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | CORE_STOCK_APIS | massive | ok |
| Native intraday klines | `moomoo://get_cur_kline` | TECHNICAL_INDICATORS | moomoo | gateway (needs local OpenD SDK) |
| Dividends & splits (adjust pair prices) | `https://eodhd.com/api/div/AAPL` | CORPORATE_ACTIONS | eodhd | ok |
| Fundamentals to constrain candidate pairs | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | FUNDAMENTAL_DATA | tiingo | ok |
| Fundamental cross-check | `https://www.alphavantage.co/query` | FUNDAMENTAL_DATA | alpha_vantage | ok |
| Precomputed indicators (MACD/BBANDS) | `https://www.alphavantage.co/query` | TECHNICAL_INDICATORS | alpha_vantage | ok |
| Short interest (crowding filter) | `moomoo://get_short_interest` | SHORT_INTEREST | moomoo | gateway |
| Institutional holdings (crowding) | `moomoo://get_shareholders_institutional` | INSTITUTION_DATA | moomoo | gateway |
| News for regime/catalyst filter | `https://eodhd.com/api/news` | NEWS_DATA | eodhd | ok |
| News sentiment score | `https://eodhd.com/api/sentiments` | NEWS_SENTIMENT | eodhd | ok |
| Earnings dates (avoid holding over earnings) | `https://api.benzinga.com/api/v2.1/calendar/earnings` | EARNINGS_CALENDAR | benzinga | ok |
| Analyst ratings (crowding) | `https://api.benzinga.com/api/v2.1/calendar/ratings` | ANALYST_RATINGS | benzinga | ok |
| Macro series (regime overlay) | `https://api.stlouisfed.org/fred/series/observations` | MACRO_DATA | fred | ok |
| Risk-free curve (Sharpe annualisation) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | RISK_FREE_CURVE | federal_reserve | ok |
| Options surface (IV overlay) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | OPTIONS_SURFACE | cboe | ok |
| **Continuous futures (MNQ/MGC) 5-min bars** | — | — | — | **gap** |
| **Tick / sub-bar data** | — | — | — | **gap** |
| **GICS sector/industry mapping for pair grouping** | — | — | — | **gap** |
| **5-min FX series for realized vol (EUR/USD)** | — | — | — | **gap** (twelvedata advertises FX, not probed for it) |

**Gap notes.** The four bold rows cannot be supplied by any probed provider. Consequences: (a) the pair-matching pipeline is fully implementable on daily EOD data from eodhd/tiingo; (b) the MNQ/MGC intraday falsification results cannot be reproduced or traded from this data layer without a futures feed; (c) sector-based pair pre-filtering must fall back to fundamental-data industry fields, since no probed endpoint exposes GICS codes; (d) sub-bar timing tests (bar-boundary artifact vs real edge) are impossible without a tick feed.

In the table above, `gap` inputs are not served by any provider and `derived` inputs are computed locally from the others — treat both as such rather than fetching or inventing them.

## Pitfalls & Validation

- **Multiple testing / data snooping.** Uncorrected ADF p-value thresholds inject ≈1,250 false positives into an S&P 500 pairs portfolio `(2403.07998)`. The RTH control used 53+ parameter combinations before its single OOS run `(2605.04004)`; the VP-MACD λ is selected from 11 values × 6 metrics per index `(2604.26063)`. Use a deflated-Sharpe / probability-of-backtest-overfitting correction and pre-register a single OOS run.
- **Look-ahead bias.** Signal at bar close → enter next bar **open** `(2605.04004)`; VP-MACD computes on daily closes → executes next-day open `(2604.26063)`. Beware subtler leaks documented in the papers: ATR computed on **1-minute** bars then merged to the 5-minute pipeline at bar close; a GMM fit once on 2022 applied forward contaminates the first OOS fold; an ATR baseline fixed on the full sample.
- **Regime instability is the dominant failure mode.** Gap continuation short is positive in 2023 (+14.53) and 2025 (+10.27) but −11.87 in 2024 `(2605.04004)`; VVG reversal is +8.35 in 2024 but −22.76 in 2025. Cointegration can break outright (XOM–BP, ADF p=0.0129 then divergence) `(2203.03179)`. Always require same-sign across ≥3 independent OOS years.
- **Costs decide the answer.** The MNQ friction floor is 2.0 pts; 11 of 14 families had gross edge of only 0.07–1.50 pts. The matching pairs portfolio goes from gross +18–75% to net +64.73% (matching) vs **net −26.15%/−13.40%** (baseline) purely from turnover `(2403.07998)`. Model costs per-instrument, not per-notional.
- **Verify the process, don't assume it.** Route every candidate spread through the 5-step CAR(1) test `(2501.03434)`; choose LSB vs DMB correctly (LSB if the spread can be negative), keep $N>50$ and $N/M$ small, and inspect the recovered-increment scatter + lag-1 ACF alongside $W$.
- **Estimation scale matters.** z-score denominators are outlier-fragile; use the q-score, winsorize at ±3, and round $|q|$ `(2403.07998)`.
- **Design the test to be falsifiable.** Replicate the five-gate protocol (T≥2.0 on net, ≥30 trades/fold, positive net after friction, sign-stable across OOS years, permutation p<0.001) as a reusable harness, and include at least one known positive control so you can prove the harness detects real edge.
- **How to test an implementation is sound.** (1) Reproduce the positive controls' magnitudes before trusting the harness. (2) Run a delay-sensitivity test — a genuine edge decays or survives a one-bar delay; a bar-boundary artifact **sign-flips** (London Signal B: +4.30 → −2.78). (3) Re-run pairs selection with the matching constraint and check that portfolio variance and turnover both fall while net Sharpe rises. (4) Compare against an unconditional same-direction benchmark to rule out passive drift.

## Recommended Workflow

1. **Cointegration screen + hedge ratio.** Build a universe screener over daily EOD (`eodhd`/`tiingo`/`stockdata`, CORE_STOCK_APIS) doing the rolling 2-year OLS, single-lag ADF on the residual, β and spread extraction. *Data:* daily adjusted close + splits/dividends (`eodhd` corporate_actions). *Expected value:* high — the whole category's entry point. *Risk:* false positives (correct with multiple-testing control). *Effort:* **M**.
2. **Maximum-weight matching portfolio layer.** Turn the ADF t-stats into a weighted graph, run maximum-weight matching, and report the variance decomposition $n_1\nu_1+n_2\nu_2$ plus the shared-stock covariance term. *Data:* the screen above. *Expected value:* high — reported gross Sharpe 1.23 vs 0.48 baseline, and it is the single largest robustness win in the corpus. *Effort:* **M**.
3. **Lévy-OU verification gate.** Implement the 5-step CAR(1) test (LSB/DMB estimator, recovered increments, $W$ statistic, Procedures 1/2) and block any candidate spread with $|W|>1.96$ from the trading book. *Data:* the spread series. *Expected value:* medium-high — prevents trading non-reverting spreads (GS–MS, AMGN–PFE, EUR/USD RV all rejected). *Effort:* **S–M**.
4. **Spread signal module (z-score + q-score).** Defaults $k=2$, winsorize ±3, q-score rounding, 2-year rolling window, monthly re-selection, per-instrument friction (0.00397%/day equity). *Data:* same. *Expected value:* medium. *Risk:* signal turnover. *Effort:* **S**.
5. **Falsification harness, seeded with the 14 negative families.** Implement the five-gate walk-forward validator and register the catalog from §2.7 (ORB, Asia expansion, liquidity grab, gap fill/continuation, volume spike/dry-up, VVG, event-day trend, MGC OU, VP-MACD) as *known-failing* baselines. Any new intraday signal must beat the harness and the positive controls. *Data:* daily EOD (and intraday only if a futures feed is added). *Expected value:* high — this is where most of the corpus's evidence sits. *Risk:* needs a futures/tick feed for full fidelity (**gap**). *Effort:* **M**.
6. **Regime overlay via Hurst + significance-gated RL.** Use Hurst<0.5/≥0.5 only as a **risk dial** (per `2205.11122` it does not raise expected return), and apply the Q-learning finding as a policy gate: act only when the expected reward is statistically significant. *Data:* daily closes. *Expected value:* medium (risk control, not alpha). *Effort:* **L**.
7. **P-robust deep-NN stat-arb prototype.** Implement the Wasserstein-ambiguity + bounded-NN formulation as a fallback for high-dimensional or broken-cointegration regimes (XOM–BP case). *Data:* daily closes for d=10–50 names; normalize to spot 100. *Expected value:* medium-high; strongest reported crisis Sharpe. *Risk:* training cost and hyper-parameters (n=9, 32d/64d/128d, k=1, ε=d). *Effort:* **L**.
8. **VP-MACD — do not prioritise.** 6–21 trades cannot clear the ≥30/fold bar; keep as a documented negative/low-power comparison only. *Effort:* **S** (documentation only).

## Output Format

### Cointegration Screen
| Pair | ADF t-stat | p-value | Hedge ratio β | Spread σ | Half-life (days) | Cointegrated |
|------|-----------|---------|---------------|----------|------------------|--------------|
| ...  | ...       | ...     | ...           | ...      | ...              | Yes/No       |

### Spread Signal
| Metric | Value |
|--------|-------|
| z-score (winsorized ±3) | ... |
| q-score (robust) | ... |
| Entry threshold k | ... |
| OU / CAR(1) W statistic | ... |
| Lévy rejected at 5%? | ... |
| Suggested side | Long spread / Short spread / Flat |

### Verdict
State whether the pair passes cointegration and the CAR(1)/OU verification gate
(|W| > 1.96 rejects), the position sizing implied by β (buy β dollars of the
first leg against one dollar of the second), and the entry/exit rule. Flag
multiple-testing risk, regime instability, and per-instrument friction costs as
the deciding factors.

## References

| arXiv id | Title | Year |
|---|---|---|
| 2403.07998 | Pairs Trading Using a Novel Graphical Matching Approach | 2024 |
| 2501.03434 | How to verify that a given process is a Lévy-Driven Ornstein-Uhlenbeck Process | 2025 |
| 2205.11122 | Optimizing Returns Using the Hurst Exponent and Q Learning on Momentum and Mean Reversion Strategies | 2022 |
| 2203.03179 | Detecting data-driven robust statistical arbitrage strategies with deep neural networks | 2022 |
| 2605.04004 | Structural Limits of OHLCV-Based Intraday Momentum Signals in MNQ Futures: A Systematic Falsification Study | 2026 |
| 2604.26063 | A Volume-Price-Adjusted MACD Trading Strategy with Sensitivity Calibration for U.S. Equity Indices | 2026 |
