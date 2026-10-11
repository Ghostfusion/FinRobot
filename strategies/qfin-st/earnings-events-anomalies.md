# Earnings & Events — learnings from the q-fin.ST corpus

`45` of 4372 corpus papers matched this category (45 with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **Multi-modal directional prediction of the earnings-announcement day is feasible but only weakly.**
  A 21-dimensional feature space (15 fundamentals + 3 price/technical + 3 FinBERT sentiment scores) fed to
  LSTM/Transformer/logistic-regression models tops out at Macro-F1 0.39 and 43–44% directional accuracy;
  the NEUTRAL class alone is ~67% of labels, so most of the "accuracy" is the no-action state (arXiv:2605.25894).
- **Sentiment features carry incremental, stabilising value.** Ablating FinBERT news-sentiment features
  degrades every model: LSTM Macro-F1 0.325 → 0.292 and expected cost 0.651 → 0.914; the paper attributes
  stability to sentiment beyond fundamentals and price (arXiv:2605.25894).
- **Trading objective, not accuracy, drives model choice.** A weighted cross-entropy with minority-class
  weights makes the LSTM a conservative "safe-bet" (highest UP precision 0.556, lowest cost 0.651) while the
  self-attention Transformer is more sensitive (Macro-F1 0.390) but pays more for UP↔DOWN swaps
  (arXiv:2605.25894).
- **Concavity in the pre-earnings IV smile (and the implied bimodal risk-neutral density) is a real,
  recurring ex-ante signal.** 40% of a 49-quarter sample of seven large caps showed a concave smile
  one day before the announcement; the shape collapsed back to convex the day after (arXiv:2307.15718).
- **Hedging premia are measurably larger under concave smiles.** The ATM straddle's cost-implied move
  (`IMPMOVE`) averages 9.44% before concave announcements vs 4.28% before non-concave ones — a 5.16pp
  premium investors pay for event-risk protection (arXiv:2307.15718).
- **Anomaly profitability is preference-dependent.** Under prospect stochastic dominance (S-shaped utility),
  18 classic anomalies largely *expand* the opportunity set of prospect investors, with in-sample and
  out-of-sample verdicts remarkably consistent (arXiv:2004.02670).
- **Regression event studies are biased under event clustering.** The standard market-model CAR test
  falsely detects abnormal returns when the estimation window contains return spikes and when many events
  share a calendar day; a topological (SOM) correction separates genuine event effects from confounds
  (arXiv:1905.06536).
- **Event-study significance is fragile to dependence and tail assumptions.** A reported 5.7× crypto
  infrastructure-vs-regulatory variance effect collapsed to a directional 3.49× with p≈0.39 once
  cross-asset pseudoreplication and Student-t (ν≈3) tails were respected (arXiv:2602.07046).
- **Persistent event-driven spreads can be explained by a financing channel.** The EUA cost-of-carry
  "anomaly" (C-spread) is cointegrated with the credit spread of EU-ETS compliance entities, which is its
  long-run driver (arXiv:2405.12982).

*Off-topic note:* two of the six papers are not about earnings per se — arXiv:2602.07046 is a
cryptocurrency event study and arXiv:2405.12982 is about the EU carbon-allowance futures spread. Both are
retained because their machinery (dependence-robust event inference; cointegration of an anomaly spread with
a funding spread) transfers directly to earnings-event work.

## 2. Implementable formulas & algorithms

### 2.1 Multi-modal earnings-day direction classifier

**Purpose.** Three-class prediction y ∈ {UP=0, DOWN=1, NEUTRAL=2} of the earnings-day (or next trading day)
return direction from the 30 calendar days before the announcement (arXiv:2605.25894).

**Feature/target construction.** Daily state $x_t \in \mathbb{R}^d$, $d = d_f + d_m + d_n = 15 + 3 + 3 = 21$:
15 quarterly/annual fundamentals (net margin, ROE, debt-to-equity, operating cash flow, …); 3 market
dynamics (adjusted close, 3-day and 6-day simple moving averages); 3 FinBERT class probabilities
(POS/NEG/NEU), averaged across all articles published for a firm on a day. Target from daily return

$$R = \frac{P_{EA} - P_{EA-1}}{P_{EA-1}}, \qquad
y = \begin{cases} \text{UP} & R \ge \tau \\ \text{DOWN} & R \le -\tau \\ \text{NEUTRAL} & \text{otherwise}\end{cases}$$

with the reported threshold **τ = 3%** and $P_{EA-1}$ the close on the prior trading day (use the next
session's close if the release is post-close) (arXiv:2605.25894).

**Model + loss.** Weighted cross-entropy $L = -\sum_k w_k\, y_k \log \hat y_k$ with $w_0, w_1 \ge w_2$
(UP/DOWN mass > NEUTRAL) to counter the ~67% NEUTRAL class. Reported architectures:
2-layer LSTM (hidden 64, dropout 0.5, final hidden → softmax) and a Transformer encoder (2 layers, 4 heads,
FFN 256, sinusoidal positional encodings, global average pooling) vs a flattened (30×21=630) multinomial
logistic baseline (lbfgs, class-balanced). Adam, lr 5e-5, batch 8, 15 epochs (arXiv:2605.25894).

**Reported effect sizes.** With sentiment: LSTM Acc 44.1 / Macro-F1 0.325 / UP-prec 0.556 / cost 0.651;
Attention Acc 43.4 / Macro-F1 0.390 / cost 0.803; logreg cost 1.020. Custom cost metric: 0 for correct,
**3** for UP↔DOWN, **1** otherwise (arXiv:2605.25894).

**Failure modes.** Small data (ten-month window, top-500 universe) and heavy noise; linear baseline has an
unstable UP bias with many costly swaps; LSTM collapses to NEUTRAL (UP precision 0.000 in the no-sentiment
variant); metrics must be Macro-F1 + cost, never raw accuracy.

### 2.2 Concave IV smile → event-risk signal and implied straddle premium

**Purpose.** Detect an ex-ante "event risk" signal before an earnings announcement and quantify the
hedging premium via a delta-neutral ATM straddle (arXiv:2307.15718).

**Smile smoothing (Fast & Stable / Jackwerth).** Fit a smooth IV curve on an equally spaced moneyness grid
$M_j = M_0 + j\Delta$ with **Δ = 0.025**, 17 points (9 observed), by minimising second-derivative roughness
plus fit:

$$\min_{\{\sigma_j\}} \frac{\Delta^4}{2(J+1)} \sum_{j=0}^{J} (\sigma_j'')^2 \;+\; \lambda \sum_{i=0}^{I} (\sigma_i - \hat\sigma_i)^2,
\qquad \textbf{λ = 0.01}$$

(λ lowered until all risk-neutral densities are non-negative, i.e. arbitrage-free; for j off the observed
grid the first-order condition is $\sigma_{j-2}-4\sigma_{j-1}+6\sigma_j-4\sigma_{j+1}+\sigma_{j+2}=0$.)
Note: method assumes European options — the paper feeds Bloomberg's European-equivalent vols
(arXiv:2307.15718).

**Risk-neutral density (Breeden–Litzenberger).** With $G(k) = e^{rT}\,\partial^2 c/\partial k^2$ approximated
on a small strike step $\Delta$ as

$$G(k) \approx e^{rt}\,\frac{c_1 + c_3 - 2 c_2}{\Delta^2}$$

then normalise $\sum G = 1$ to read off bimodality (arXiv:2307.15718).

**Concavity test.** Declare a smile concave iff (i) the second derivative of the fitted curve is negative
near the ATM strike, and (ii) the concavity lies halfway between the second-lowest and second-highest *real*
strikes (excludes local inflection/outlier artefacts). Convexity statistic:

$$\text{CONVEXEST} = IV(ATM - x\%) + IV(ATM + x\%) - 2\,IV(ATM),$$

negative ⇒ concave (arXiv:2307.15718).

**Delta-neutral straddle and implied move.** $w = -(\Delta_p/P)\,/\,(\Delta_c/C - \Delta_p/P)$,
$\text{STRADDLE} = w R_c + (1-w) R_p$, and the break-even move
$\text{IMPMOVE} = (C+P)/S$ (arXiv:2307.15718).

**Reported effect sizes.** Pre-EAD ATM IV mean 75.70% (median 71.60%, max 188.77%); after EAD 69.64%.
`IMPMOVE` straddle: concave 9.44% (median 8.13%) vs non-concave 4.28% (3.74%) → **+5.16pp / +4.39pp**.
Strangle: concave 5.32% (4.00%) vs non-concave 1.27% (0.86%). Realised price return under concave smiles
is on average negative and far below the required move (arXiv:2307.15718).

**Failure modes.** Concavity detection is sensitive to the smoothing spline and to sparse/illiquid deep-OTM
strikes; requires a dense short-dated strike grid (1–4 day expiry was where the effect lived); straddles
opened at concave-implied costs do not pay out on average (premium exceeds realised move).

### 2.3 Event study with dependence-robust, event-level inference

**Purpose.** Estimate and test cumulative abnormal returns (CARs) around an event without over-rejecting
under cross-sectional correlation and event clustering (arXiv:2602.07046, arXiv:1905.06536).

**Abnormal returns.** Constant-mean model $AR_{it} = R_{it} - \bar R_i$ (mean over the event's estimation
window) with a market-model robustness alternative $AR_{it} = R_{it} - (\hat\alpha_i + \hat\beta_i R_{proxy,t})$;
$CAR_i(\tau_1,\tau_2) = \sum_{t=\tau_1}^{\tau_2} AR_{it}$ (arXiv:2602.07046).

**Dependence-aware test.** Average usable asset CARs *within* each event (equal-weighting events), then
resample the event means per group (event-level block bootstrap, 5,000 seeded replications) and cross-check
with an event-level Welch t-test. The resampling unit is the **event**, never the asset-event cell
(arXiv:2602.07046).

**Reported effect sizes.** Infrastructure CAR −0.64% vs regulatory −9.33%, difference +8.69pp (block p=0.202,
Welch p=0.216, 95% CI [−4.50%, +22.22%]); Cohen's d=0.35 with a pooled SD of 24.6pp and a minimum detectable
effect ≈19.5pp at 80% power — an underpowered failure to reject (arXiv:2602.07046).

**Topological correction (event clustering).** Build the per-security feature matrix
$Q = [\,mAW;\ tCAR_{-5..+5};\ tAR_{-5..+5};\ DWR;\ \hat\alpha;\ \hat\beta;\ \text{Corr}(1y);\ \tanh(1/(D_{event}-D_{announce}))\,]$
(modified active weight, t-stats of CARs/ARs over the window, Durbin-Watson ratio of market-model residuals,
intercept, slope, rate/return correlation, and a tanh-transformed day-distance to the firm's earnings
announcement), standardise each dimension, and train a **batch-learning self-organising map** (20×20
hexagonal lattice, initial learning coefficient 0.9, initial neighbourhood 0.001, T=2000 iterations). Regions
whose AR cells coincide with near-earnings cells are attributed to earnings; regions with DW<2, large $\hat\alpha$
and $\hat\beta\approx1$ are flagged as false detections driven by estimation-window spikes
(arXiv:1905.06536).

**Reported effect sizes.** On the GPIF disclosure (1,804 TSE first-section securities, 11-day event window,
250-day estimation window), AR detection rose from ~4–5%/day pre-event to 12.5% on the event day and 16% at
+4d; whole clusters (region A1: seven securities caught by a Pokémon Go return spike; A2: Tokyo-governor
election; A4: 44 banks reacting to the BOJ policy meeting) were shown to be non-earnings effects
(arXiv:1905.06536).

**Failure modes.** Cross-sectional correlation, overlapping windows (24 of 50 event pairs overlapped in
arXiv:2602.07046), spike contamination of OLS parameters (residuals must sum to zero ⇒ a single spike biases
the intercept), and arbitrary outlier exclusion which destroys the statistical rationale.

### 2.4 Prospect stochastic dominance spanning test

**Purpose.** Decide whether an anomaly (or new security) genuinely expands the opportunity set of a
prospect-theory (S-shaped utility) investor relative to a benchmark factor set (arXiv:2004.02670).

**Dominance.** With $G(z,\lambda,F)$ the CDF of portfolio return $\lambda^\top u$ and
$J(z_1,z_2,\lambda;F)=\int_{z_1}^{z_2} G(u,\lambda,F)\,du$, κ prospect-dominates λ (κPλ) iff

$$P_1(z,\lambda,\kappa,F)=J(z,0,\kappa,F)-J(z,0,\lambda,F)\le 0\ \forall z\in\mathbb{R}_-,\quad
P_2(z,\lambda,\kappa,F)=J(0,z,\kappa,F)-J(0,z,\lambda,F)\le 0\ \forall z\in\mathbb{R}_{++}.$$

**Spanning test.** K prospect-spans L ($K\!\triangleright\!L$) iff
$\rho(F)=\max_{i=1,2}\sup_{\lambda\in L}\sup_{z\in A_i}\inf_{\kappa\in K} P_i(z,\lambda,\kappa,F)=0$;
the empirical statistic is $\rho_T = \sqrt{T}\,\rho(F_T)$, with an i.i.d.-free subsampling distribution
(block sizes $b_T \in \{T^{0.6},T^{0.7},T^{0.8},T^{0.9}\}$) and a bias-corrected critical value from
$q_{T,b_T}(1-\alpha)=\gamma_0+\gamma_1 b_T^{-1}+\nu$ → $q^{BC}=\gamma_0+\gamma_1 T^{-1}$. The utility
representation is approximated by piecewise-linear ramp mixtures with **n₁ = 10, n₂ = 5** ⇒ 715 distinct
utilities per half-line and 1,430 small LPs per statistic (arXiv:2004.02670).

**Reported effect sizes.** Over 18 anomalies × 3 factor models (FF-5, Stambaugh-Yuan M-4, Hou-Xue-Zhang q),
most strategies **reject** spanning (expand the prospect opportunity set): e.g. Momentum ρ*=0.0696 vs
q^BC=0.0204 (FF-5); Value 0.1921 vs 0.1878 (FF-5); Idiosyncratic Volatility 0.2386 vs 0.0101 (q-factor).
Size 0 and Growth Option 0 are spanned by every model; Return on Assets is spanned by FF-5 and M-4
(arXiv:2004.02670). In- and out-of-sample verdicts are highly consistent.

**Failure modes.** LP solution cost grows with problem dimension; the asymptotic exactness condition needs a
contact-set regularity (weaker than the extreme-point condition of the MSD predecessor) — check it; mixed
independent/non-independent return structures require the subsampling (not block-bootstrap) variant for
power.

### 2.5 Cointegration of an anomaly spread with a funding spread

**Purpose.** Explain a persistent event/market spread as a function of a financing variable, and test the
error-correction mechanism — transferable to any "spread anomaly" (arXiv:2405.12982).

**Spread definition.** Cost-of-carry spread over the risk-free rate:

$$C_t = \frac{\log(F_{t,T}/S_t)}{T-t} - r(t,T).$$

Build a proxy for the participants' financing cost (e.g. a credit-spread index $Z_t$). Test I(1) with
ADF-GLS; test cointegration with Johansen trace/eigenvalue tests; if a single relation is found, vector
$\{1, -\gamma_1, -\gamma_2\}$ and estimate the ECM

$$\Delta C_t = \alpha_0 + \sum_{i=1}^{3}\beta_i \Delta C_{t-i} + \alpha_1 \Delta Z_t + \alpha_2 \Delta r_t + \alpha_3 \psi_{t-1} + \sum_j \delta_j Y_{j,t} + \epsilon_t,\quad \psi_{t-1}=C_{t-1}-\gamma_1 Z_{t-1}-\gamma_2 r_{t-1}.$$

**Reported effect sizes.** Phase III (2013–2020, 2,008 daily obs): all three series I(1); Johansen finds one
cointegration relation with vector $\{1, -1.21, -0.40\}$; the credit index drives ~94% of the non-stationary
term, the risk-free rate ~6%. ECM lag coefficients $\beta = (-0.33, -0.28, -0.12)$, all p<1%, and
$\alpha_3 = -0.02$ p<1% (mean-reversion). S&P 500, VIX, WTI and EUA-spot GARCH volatility are all
insignificant (arXiv:2405.12982).

**Failure modes.** Running OLS on non-stationary levels yields spurious regression; individual-futures
(not front-contract) series inject roll noise; weekly aggregation removes the short-run autoregressive
structure.

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Earnings calendar (date, BMO/AMC timing) | `https://api.benzinga.com/api/v2.1/calendar/earnings` | earnings_calendar | benzinga | **ok** |
| Earnings calendar (fallback provider) | `moomoo://get_earnings_calendar` | earnings_calendar | moomoo | gateway (SDK, not live) |
| Historical earnings price move / surprise | `moomoo://get_financials_earnings_price_move` | earnings_surprise | moomoo | gateway (SDK, not live) |
| Earnings-day price/vol reaction history | `moomoo://get_financials_earnings_price_history` | earnings_catalyst | moomoo | gateway (SDK, not live) |
| Implied/expected move (option-implied) | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway (SDK, not live) |
| Guidance revisions (catalyst dates) | `https://api.benzinga.com/api/v2.1/calendar/guidance` | guidance_revisions | benzinga | **ok** |
| FDA calendar (catalyst dates) | `https://api.benzinga.com/api/v2.1/calendar/fda` | fda_calendar | benzinga | **ok** |
| Offering/dividend calendars (capital-structure events) | `https://api.benzinga.com/api/v2.1/calendar/offerings`, `https://api.benzinga.com/api/v2.2/calendar/dividends` | offerings_calendar, corporate_actions | benzinga | **ok** |
| Daily OHLCV / prices (AR/CAR, technicals) | `https://eodhd.com/api/eod/AAPL`, `https://api.tiingo.com/tiingo/daily/AAPL/prices`, `https://api.twelvedata.com/time_series` | core_stock_apis | eodhd / tiingo / twelvedata | **ok** |
| Fundamentals (15 metrics) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | fundamental_data | tiingo | **ok** |
| Fundamentals + technical indicators (RSI etc.) | `https://www.alphavantage.co/query` | fundamental_data / technical_indicators | alpha_vantage | **ok** |
| News articles (sentiment corpus) | `https://eodhd.com/api/news`, `https://api.benzinga.com/api/v2/news`, `https://api.stockdata.org/v1/news/all` | news_data | eodhd / benzinga / stockdata | **ok** |
| News sentiment scores | `https://eodhd.com/api/sentiments`, `https://www.alphavantage.co/query` | news_sentiment | eodhd / alpha_vantage | **ok** |
| News sentiment (event-coded tone, GDELT) | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | rate_limited |
| Analyst ratings (pre-event revision) | `https://api.benzinga.com/api/v2.1/calendar/ratings` | analyst_ratings | benzinga | **ok** |
| Short-dated option chain (IV smile grid) | `moomoo://get_option_chain` | options_data | moomoo | gateway (SDK, not live) |
| Listed index option surface | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | http (fails; SPX-only) |
| Risk-free curve (C-spread/DCF) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | connect (fails) |
| Macro/rates (FinBERT-free level control) | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | **ok** |
| SEC filings (event anchor / text) | **gap** — category `SEC_FILINGS` routes to `sec_edgar` (categories.py `PRIORITY`) but **no live row exists in `strategies/endpoints.json`** | sec_filings | sec_edgar | no probe |
| Per-earnings-day strike-level option IVs with European-equivalents (Bloomberg-style) | **gap** — no provider row supplies calibrated IV surfaces for single names | options_surface | — | missing |
| EUA / carbon futures + OIS curve + issuer bond Z-spreads | **gap** — out of data-layer scope | — | — | missing |
| β̂, DW, and market-model residuals for SOM features | Derived locally from `core_stock_apis` OHLCV (**not** fetched) | — | — | derived |

Every row above cites a real row from `strategies/endpoints.json` unless explicitly marked **gap**.
`fmp`, `yfinance`, `finnhub`, and `sec_edgar` appear in `categories.py`'s routing priority but have **no
live-probed row** in the inventory, so they are not cited as available.

## 4. Pitfalls, validation and measurement

- **Dependence / pseudoreplication.** Treating correlated asset-event observations as independent inflates
  significance. In arXiv:2602.07046 six assets overlapped on 45 common events with $\bar\rho\approx0.68$,
  giving an effective sample size of only 1.33–2.35; a naive i.i.d. rule rejected 35.1% of true-null panels
  at the 5% level, vs 4.6% for the Student-t-copula rule. **Test:** always resample at the event level and
  report an effective-degrees-of-freedom sensitivity.
- **Tail mis-specification.** Fitting Student-t errors (ν≈3) but bootstrapping Gaussian innovations is
  strongly anti-conservative. **Test:** match the bootstrap innovation law to the fitted errors.
- **Selection on the dependent variable.** Event inclusion is a researcher degree of freedom; a curated
  screen gave 3.49× while a mechanical filter on the broad pool gave 0.5–1.6×. **Test:** report the effect
  across at least two inclusion rules and never claim significance for the *difference between screens*.
- **Look-ahead / leakage.** Earnings timestamps must be UTC-verified and use the *next* session when the
  release is post-close; forward-fill (FFILL) on fundamentals and weekends is a leakage vector; the FinBERT
  daily average must not include articles published after the label window. **Test:** strict point-in-time
  replay and a shuffled-timestamp ablation.
- **Event clustering.** Overlapping windows and same-day events (arXiv:1905.06536: 309 firms reported on a
  single day) break the zero-cross-correlation assumption behind CAR aggregation. **Test:** the SOM/tanh
  attribution in §2.3, or include event-date dummies.
- **Estimation-window spikes.** A single outlier biases the OLS intercept (residuals sum to zero) and
  manufactures false abnormal returns. **Test:** Durbin-Watson < 2 ⇒ positive serial correlation, refit or
  flag.
- **Underpower & FDR.** Report minimum detectable effect (≈19.5pp in arXiv:2602.07046) before claiming a
  null; multiple testing (18 anomalies, 18 Granger pairs) needs Benjamini-Hochberg control (7 of 10 naive
  sentiment leads survived FDR q<0.05).
- **Class imbalance & threshold sensitivity.** ~67% NEUTRAL means accuracy is meaningless; sweep τ around
  3% and report Macro-F1 plus an asymmetric cost metric (arXiv:2605.25894).
- **Smile artefacts.** Concavity can be an outlier/spline artefact; enforce the two-part definition of
  §2.2 (negative second derivative near ATM **and** concavity between the second-lowest/highest real strikes).
- **Spurious regression.** Never regress non-stationary spread levels on levels; require ADF-GLS I(1) and
  Johansen cointegration before an ECM (arXiv:2405.12982).

## 5. Recommended first implementation in FinRobot

1. **Event-calendar spine + point-in-time data join (S).** Build one canonical events table from
   `benzinga` `earnings_calendar` (+ `guidance_revisions`, `fda_calendar`, `offerings_calendar`), with
   UTC timestamps and BMO/AMC flags, joined to `core_stock_apis` OHLCV. This is the prerequisite for every
   other item; expected value = enabling all event analytics; risk = timestamp accuracy.
2. **Dependence-robust event-study module (M).** Constant-mean AR/CAR with event-level block bootstrap
   (5,000 reps) and an event-level Welch cross-check (§2.3). Data: `core_stock_apis` only. Expected value =
   correct CAR sign/magnitude and honest p-values; risk = overlapping-window handling; effort M.
3. **Earnings-day direction classifier (M).** 21-dim multi-modal model (LSTM + Transformer + logreg
   baseline) with weighted CE, τ=3%, Macro-F1 and the 0/3/1 cost metric (§2.1). Data: `fundamental_data`
   (tiingo/alpha_vantage), `core_stock_apis`, `news_data`+`news_sentiment` (eodhd/alpha_vantage — FinBERT or
   the provider sentiment endpoints), `technical_indicators`. Expected value = a ranked pre-event signal;
   risk = low accuracy / NEUTRAL collapse; effort M.
4. **Implied-move & IV-concavity detector (L).** Fit the Jackwerth smooth smile (Δ=0.025, λ=0.01), compute
   `CONVEXEST`, normalised Breeden-Litzenberger RND, and `IMPMOVE=(C+P)/S`; emit a concavity flag + straddle
   premium. **Data gap:** needs the `moomoo` `options_data` gateway (single-name chains); the live stock
   inventory only has SPX `options_surface`. Expected value = an ex-ante event-risk flag; risk = gateway
   dependency and thin strikes; effort L.
5. **Earnings surprise / drift signal (M).** Use `moomoo` `earnings_catalyst`/`earnings_surprise` (gateway)
   plus `benzinga` `guidance_revisions`; compute standardised unexpected earnings and a post-event drift
   window. Expected value = a classic PEAD overlay; risk = gateway availability; effort M.
6. **Anomaly validation harness — prospect spanning (L).** Implement the LP + subsampling PSD spanning test
   (§2.4) to check whether any strategy FinRobot surfaces genuinely expands a prospect investor's
   opportunity set against a Fama-French-style factor set (factors derivable from `core_stock_apis`).
   Expected value = avoids shipping anomalies that a behavioural investor would not value; risk = LP cost
   and the exactness regularity condition; effort L.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2605.25894v1 | Predicting Stock Price Direction on Earnings Announcement Days using Multi-modal Deep Learning | 2026 |
| 2602.07046v5 | Do Cryptocurrency Markets Differentiate Infrastructure from Regulatory Shocks? A Multi-Moment Event Study with Dependence-Robust Inference | 2026 |
| 2004.02670v1 | Spanning analysis of stock market anomalies under Prospect Stochastic Dominance | 2020 |
| 1905.06536v1 | Improving Regression-based Event Study Analysis Using a Topological Machine-learning Method | 2019 |
| 2405.12982v1 | The puzzle of Carbon Allowance spread | 2024 |
| 2307.15718v2 | Option Smile Volatility and Implied Probabilities: Implications of Concavity in IV Curves | 2023 |
