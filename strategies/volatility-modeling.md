# Volatility Modeling — learnings from the q-fin.ST corpus
442 of 4372 corpus papers matched this category (393 with PDFs); this doc is based on a close reading of 6.

## 1. What the corpus actually offers

- **HAR is the linear workhorse for realized variance (RV).** Corsi's heterogeneous autoregressive model regresses RV on daily/weekly/monthly averages, $RV_t = \omega + \beta^{(d)} RV^{(d)}_{t-1} + \beta^{(w)} RV^{(w)}_{t-1} + \beta^{(m)} RV^{(m)}_{t-1} + \epsilon_t$, where the weekly component is the 5-day mean and the monthly component the 22-day mean of daily RV. Weekly/monthly averages are the practical way to encode the long-memory of volatility (arXiv:2505.11163v1, arXiv:2505.13933v2).
- **Log-transforming RV improves forecast stability.** Across 21 global indices and six loss functions, log-variants (HAR$^{log}$, CHAR$^{log}$, ARFIMA$^{log}$) systematically beat their linear counterparts in MSE, MAD and QLIKE, because $"\log RV"$ stabilizes heteroskedasticity (arXiv:2505.11163v1).
- **EGARCH/TGARCH parameterizations and their crisis behaviour.** Estimating EGARCH(1,1) and TGARCH(1,1) with Student-$t$ errors on Indonesian, Malaysian and Philippine indices (2010–2024) in a by-window design, persistence $\alpha+\beta \approx 1$ throughout; during crises $\alpha+\beta$ rises above 1, the asymmetry term $\gamma$ increases and the degrees of freedom $\nu$ fall; degrees of freedom concentrate in $\nu \in [5,8]$ and a GED robustness check gives shape parameters 1.349/1.350/1.446 (all < 2, i.e. heavy-tailed) (arXiv:2510.16010v1).
- **Subordinated L´evy processes reproduce clustering via a mean-reverting stochastic clock.** VG is Brownian motion evaluated at a Gamma subordinator, $VG(t) = \theta G(t) + \sigma W(G(t))$; VGSA adds an integrated CIR (ICIR) clock so the arrival rate is mean-reverting, and CGMY-SA generalizes the jump activity (arXiv:2507.17431v1).
- **Multivariate forecasts can be reconciled against a univariate portfolio-variance forecast.** A univariate GARCH on synthetic portfolio returns and a bottom-up MGARCH aggregate $\gamma_p^2 = \omega' \hat\Sigma \omega$ are base forecasts for the *same* quantity; GLS/Minte reconciliation combines them, and matters most when the multivariate model is misspecified (Caporin et al., arXiv:2603.17463v2).
- **The strongest RV forecaster is regime-dependent, not stable.** In a 6-ETF, 2219-day walk-forward study, GRU wins low/mid-volatility states while GARCH-$t$/FIGARCH win high-volatility states; a state-gated router cuts high-volatility QLIKE ~24% and underprediction loss ~22% vs. a rolling-best benchmark (arXiv:2604.10402v4).
- **ML/foundation/quantum models are claimed to beat HAR, but only after task-specific adaptation.** TimesFM fine-tuned by *incremental learning* (IL) beats HAR/CHAR/ARFIMA/RGARCH on most loss functions (arXiv:2505.11163v1); a 10-qubit quantum reservoir (QRC) reports the lowest MSE/QLIKE and MCS membership $p=1.0$ against HAR on monthly S&P 500 RV (arXiv:2505.13933v2). Both papers are explicit that zero-shot / un-adapted versions do *not* dominate.

## 2. Implementable formulas & algorithms

### 2.1 GARCH family: GARCH, EGARCH, TGARCH (with Student-$t$)
**Purpose.** Model conditional variance of daily returns; capture clustering and the leverage effect; usable directly for next-day variance forecasts and by-window crisis studies.

GARCH(1,1):
$$\sigma^2_t = \omega + \alpha \epsilon^2_{t-1} + \beta \sigma^2_{t-1}$$

EGARCH(1,1) (Nelson):
$$\log \sigma^2_t = \omega + \beta \log \sigma^2_{t-1} + \gamma \frac{\epsilon_{t-1}}{\sigma_{t-1}} + \alpha\left(\left|\frac{\epsilon_{t-1}}{\sigma_{t-1}}\right| - \mathbb{E}|z|\right)$$

TGARCH(1,1) (Glosten–Jagannathan–Runkle):
$$\sigma^2_t = \omega + \alpha \epsilon^2_{t-1} + \gamma \epsilon^2_{t-1} \mathbb{1}[\epsilon_{t-1}<0] + \beta \sigma^2_{t-1}$$

- **Inputs:** daily log returns; a realized measure RV (for RGARCH).
- **Parameters:** $\omega>0$, $\alpha\ge0$, $\beta\ge0$; $\gamma>0$ ⇒ bad news amplifies volatility; Student-$t$ $\nu\in[5,8]$ typical for emerging markets. Estimate by MLE under Student-$t$ (arXiv:2510.16010v1).
- **Realized-GARCH** (used as a benchmark in arXiv:2505.11163v1) couples returns and a realized measure:
$$\log h_t = \omega + \beta \log h_{t-1} + \alpha \log RV_{t-1}, \qquad \log RV_t = \xi + \phi \log h_t + \tau z_t + u_t$$
  which the paper notes is *not* uniformly better: across 21 indices RGARCH has the worst MSE (0.00804 vs HAR 0.00118) yet is highly resilient under MDA (arXiv:2505.11163v1).
- **Observed effects:** persistence $\alpha+\beta\to1$; during the 2013 Taper Tantrum, COVID (2020–21) and the 2022–23 hiking cycle, $\gamma$ and $\alpha+\beta$ rise and $\nu$ falls; parameters revert after crises; better-institutionalised markets (Malaysia) revert faster than thin ones (Philippines, $\gamma$ reaching 0.32 in COVID) (arXiv:2510.16010v1).
- **Failure modes:** static single-window fits hide regime shifts; near-unit-root $\alpha+\beta\ge1$ makes unconditional variance undefined; residual ARCH remains if lags are too short (Ljung–Box/ARCH–LM diagnostics in arXiv:2510.16010v1).

### 2.2 HAR / CHAR on realized variance
**Purpose.** Directly forecast RV from its own multi-horizon history; the standard linear benchmark.

$$RV_t = \omega + \beta^{(d)} RV_{t-1} + \beta^{(w)} \tfrac{1}{5}\sum_{k=1}^{5} RV_{t-k} + \beta^{(m)} \tfrac{1}{22}\sum_{k=1}^{22} RV_{t-k} + \epsilon_t$$

CHAR replaces RV with bipower variation, $BPV_t = \tfrac{\pi}{2}\sum_{i=2}^{M}|r_i||r_{i-1}|$, which estimates the continuous (jump-free) quadratic variation $\int_{t-1}^t \sigma^2 ds$ (arXiv:2505.11163v1).

- **Inputs:** intraday (5-min) returns to build RV$=\sum_i r_i^2$ and BPV; or, absent intraday data, an OHLC-based proxy (see §2.5).
- **Parameters:** three lags/aggregation windows (1, 5, 22); estimate by OLS with Newey–West HAC errors; fit on $\log RV$ (arXiv:2505.11163v1, arXiv:2505.13933v2).
- **Observed effects:** for most assets HAR$^{log}$ dominates ARFIMA, but no single model wins every loss function; HAR under-performs on directional accuracy (MDA) and percentage errors (MAPE) (arXiv:2505.11163v1).
- **Failure modes:** strong parametric rigidity; misses nonlinearities and regime shifts; linear HAR is not robust when evaluated on QLIKE (asymmetric) vs MSE (symmetric) (arXiv:2505.11163v1, arXiv:2505.13933v2).

### 2.3 Forecast reconciliation for portfolio variance
**Purpose.** Merge a univariate GARCH variance forecast on synthetic portfolio returns with a bottom-up MGARCH covariance forecast; improve portfolio-risk prediction, especially under model misspecification.

Bottom-up aggregation and its linear form:
$$\gamma_p^2 = \omega' \hat\Sigma \omega = \omega'\otimes\omega' D_N \operatorname{vech}(\hat\Sigma) = a'\hat\sigma, \qquad a = D_N'(\omega\otimes\omega).$$
Generalized-least-squares reconciliation subject to $c'y=0$,
$$\tilde y = \left(I_{m+1} - \Omega c (c'\Omega c)^{-1} c'\right)\hat y,$$
with $\Omega$ the forecast-error covariance estimated by the **MinT shrinkage** estimator of Wickramasuriya et al. (arXiv:2603.17463v2).

- **Inputs:** known portfolio weights $\omega$ (N-vector), asset returns, a univariate GARCH and an MGARCH (DCC / OGARCH / Scalar-BEKK) fit.
- **Parameters:** shrinkage intensity of $\Omega$; the constraint vector stacks the base portfolio-variance forecast and the portfolio's bottom-level elements.
- **Coherence fix:** the reconciled correlation matrix may violate $|\rho_{i,j}|\le1$; two remedies are given — (A) non-linear inequality-constrained optimization, or (B) reconcile directly on correlations after decomposing $\hat\Sigma = \hat S \hat R \hat S$ (arXiv:2603.17463v2).
- **Observed effects:** with a known true covariance, reconciliation beats the plain multivariate approach, particularly when the multivariate model is misspecified; with *noisy covariance proxies*, correctly and incorrectly specified models become indistinguishable, and the reconciliation gain shrinks (arXiv:2603.17463v2).
- **Failure modes:** proxy noise dominates; neglecting spillovers becomes harmless under noise; unconstrained reconciliation breaks correlation-matrix validity.

### 2.4 Stochastic-clock subordinated L´evy models (VGSA / CGMY-SA)
**Purpose.** Build clustering, jumps and heavy tails into a generative price model; use the stochastic arrival rate as a scenario generator for tail risk.

Variance Gamma: $VG(t) = \theta G(t) + \sigma W(G(t))$, with the Gamma subordinator $G(t)\sim\Gamma(t/\nu,\nu)$; characteristic function $\mathbb{E}e^{iuVG(t)} = \left(1 - iu\theta\nu + \tfrac{\sigma^2u^2\nu}{2}\right)^{-t/\nu}$.

VGSA replaces $t$ by an integrated CIR clock $T(t)=\int_0^t y(u)\,du$ with $dy = \kappa(\eta-y)du + \lambda\sqrt{y}\,dW_u$ (Feller condition $2\kappa\eta>\lambda^2$); the CKLS generalization $dy = \kappa(\eta-y)du + \lambda y^{\alpha}dW_u$, $\alpha\in(0.5,1]$, stays positive under suitable conditions. CGMY L´evy measure $\nu(dx) = C\frac{e^{-G|x|}}{|x|^{1+Y}}\mathbb{1}_{x<0}dx + C\frac{e^{-Mx}}{x^{1+Y}}\mathbb{1}_{x>0}dx$ with $Y<2$ (arXiv:2507.17431v1).

- **Limit results for calibration/validation:** $\tfrac{1}{t}VG(t)\xrightarrow{a.s.}\theta$; $\tfrac{1}{\sqrt t}(VG(t)-t\theta)\xrightarrow{D}\mathcal{N}(0,\nu\theta^2+\sigma^2)$; ICIR satisfies $\tfrac{1}{t}T(t)\xrightarrow{a.s.}\eta$ and $\tfrac{1}{\sqrt t}(T(t)-\eta t)\xrightarrow{D}\mathcal{N}(0,\eta\lambda^2/\kappa^2)$; $\mathbb{E}[VGSA(t)]=\theta u(t)$, $\mathrm{Var}[VGSA(t)]=(\theta^2\nu+\sigma^2)u(t)+\theta^2\lambda^2 w(t)$ with closed-form $u(t),w(t)$ (arXiv:2507.17431v1).
- **Inputs:** low-frequency return series for calibration; no option data strictly required though the model is option-motivated.
- **Failure modes:** weak identification of $\nu,\theta,\sigma$ from daily data alone; the stochastic clock adds $\kappa,\eta,\lambda$ that are hard to pin down; this paper is theoretical (consistency/asymptotics + Monte Carlo) and reports no out-of-sample financial forecasting gain (arXiv:2507.17431v1).

### 2.5 Garman–Klass proxy and risk-sensitive routing (practical, daily-only inputs)
**Purpose.** When no intraday data exists, use an OHLC-based variance proxy and route among specialists by regime.

The target is the next-day squared Garman–Klass proxy, $y_{t+1} = gk\_proxy^2_{t+1}$; specialists are scored online with a risk-sensitive loss that augments QLIKE with a one-sided underprediction penalty:
$$U^{(m)}_{t+1} = \left(\frac{\max(y_{t+1}-\hat y^{(m)}_t,0)}{y_{t+1}}\right)^2, \qquad L^{(m)}_{t+1} = \mathrm{QLIKE}(y_{t+1},\hat y^{(m)}_t) + \lambda_{under}U^{(m)}_{t+1},$$
$$\mathrm{QLIKE}(y,\hat y) = \frac{y}{\hat y} - \log\frac{y}{\hat y} - 1.$$
Scores aggregate excess loss $R^{(m)}_{t+1}=L^{(m)}_{t+1}-\min_j L^{(j)}_{t+1}$ over a 252-day window with weights $w_t(s)\propto e^{-\gamma_{time}(t-s)}e^{-\|z_t-z_s\|^2/\gamma_{reg}^2}$ on a standardized state vector $z_t$ = {log VIX, log(VIX/VXV), 20-day RV, 20-day volatility-of-volatility, term spread, HY spread}. Pools: $P_{calm}=\{GRU, HAR\text{-}RV, XGBoost\}$, $P_{stress}=\{GARCH\text{-}t, FIGARCH, HAR\text{-}RV\}$; a logistic stress gate $p_t$ blends branches (arXiv:2604.10402v4).

- **Parameters (reported defaults):** $\lambda_{under}=1$, 63-day half-life, $\gamma_{reg}=1.5$, $\rho=0.25$, $\kappa=0.35$, gate midpoint $c=0.55$ and slope $b=0.12$, HAR floor active at $p_t\ge0.65$ or disagreement $\ge0.20$; GRU 20-step/16 hidden units, XGBoost 250 trees/depth 3/lr 0.05; 504-day training window; re-estimate HAR/GRU/XGB every 21 days, GARCH-t/FIGARCH every day (arXiv:2604.10402v4).
- **Observed effect:** overall median QLIKE 0.3232 vs rolling-best 0.3653; high-volatility-regime QLIKE 0.3685 vs 0.4834 (~24% ↓) and underprediction loss 0.0474 vs 0.0609 (~22% ↓) (arXiv:2604.10402v4).
- **Failure modes:** the routing set has a high *miss-best* rate; its value is avoiding bad selections, not picking the exact winner; regime winner is unstable (GRU low/mid, GARCH-t/FIGARCH high) (arXiv:2604.10402v4).

### 2.6 Quantum reservoir computing (reference only)
A fully connected transverse-field Ising reservoir, $H=\sum_{i<j}J_{ij}X_iX_j + v\sum_i Z_i$ with $J_{ij}/v\in[0,1]$ and $v=1$; 10 qubits split into $n_1$ input + $n_2$ hidden, $k=3$ memory lags; $R_Y(x)$ phase encoding scaled to $[-\pi,\pi]$; readout via ridge regression $W_{out}=RVM_1^\top(M_1M_1^\top+\delta I)^{-1}$, $\delta=10^{-8}$ (arXiv:2505.13933v2). Reported one-step monthly S&P 500 RV: QR2 MSE 0.1030 / QLIKE 1.4004 vs HAR MSE 0.1476 / QLIKE 2.0431, MCS $p=1.0$; 7 optimal features chosen by wrapper forward selection. **Not deployable on classical hardware** without a quantum simulator; the authors disclaim quantum supremacy and flag the exponential-concentration limitation (arXiv:2505.13933v2).

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV (close-to-close returns, Garman–Klass) | `https://eodhd.com/api/eod/AAPL` | core_stock_apis | eodhd | ok |
| Daily OHLCV (alt) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | core_stock_apis | tiingo | ok |
| Daily/interval bars | `https://api.twelvedata.com/time_series` | core_stock_apis | twelvedata | ok (supports `interval` param; intraday availability not separately probed — verify) |
| Aggregate bars (intraday candidates) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | core_stock_apis | massive | ok |
| EOD bars (alt) | `https://api.stockdata.org/v1/data/eod` | core_stock_apis | stockdata | ok |
| Daily OHLCV (local gateway) | `moomoo://get_market_snapshot` | core_stock_apis | moomoo | gateway |
| Options surface / model-free implied vol (VIX-like) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | options_surface | cboe | fail — HTTP 307 |
| Expected move (implied, from option chain) | `moomoo://get_option_underlying_overview` | expected_move | moomoo | gateway |
| Macro state: term spread, rates, HY credit spread | `https://api.stlouisfed.org/fred/series/observations` | macro_data | fred | ok |
| Treasury yield curve / risk-free | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | risk_free_curve | federal_reserve | fail — connect/read timeout |
| News/attention features for ML-RV models | `https://eodhd.com/api/news` | news_data | eodhd | ok |
| News sentiment (alt) | `https://www.alphavantage.co/query` | news_sentiment | alpha_vantage | ok |
| Global news tone | `https://api.gdeltproject.org/api/v2/doc/doc` | news_sentiment | gdelt | fail — HTTP 429 rate_limited |
| 5-minute intraday returns for RV / BPV / realized quarticity | **gap** — no provider in the inventory exposes a certified 5-min intraday series; twelvedata `interval` and massive aggregates are the only candidates and need verification | technical_indicators / core_stock_apis | — | gap |
| Oxford-Man-style precomputed RV/BPV library | **gap** — no endpoint; must be computed locally from intraday bars | — | — | gap |
| VIX index quote series | **gap** — no probed endpoint returns `^VIX`; cboe is the closest but failed | — | — | gap |

## 4. Pitfalls, validation and measurement

- **Loss-function choice changes the ranking.** The corpus is unanimous: Realized-GARCH beats EGARCH under QLIKE while EGARCH wins under MSE (cited in arXiv:2505.11163v1); HAR, ARFIMA and RGARCH swap places across MSE/MAD/QLIKE/MAPE/MDA/sMAPE (arXiv:2505.11163v1). QLIKE is asymmetric (penalises underpredictions), robust to noise in the volatility proxy, and unit-invariant (Patton 2011, cited in arXiv:2505.11163v1 and arXiv:2505.13933v2), so it should be the primary metric for risk use. Report at least MSE + QLIKE + one directional metric.
- **Proxy noise, not model error, can dominate.** With noisy covariance proxies, correctly specified MGARCH models and models that neglect spillovers become statistically indistinguishable, and the benefit of forecast reconciliation shrinks (arXiv:2603.17463v2). Never compare models only on a single noisy proxy.
- **Regime dependence invalidates static “best model” claims.** The strongest forecaster flips between calm and stressed states; a leading rolling-best benchmark is unstable by construction (arXiv:2604.10402v4). Always report regime-conditioned losses, and use walk-forward re-estimation.
- **Statistical tests must account for nested models and parameter uncertainty.** Use Diebold–Mariano with Newey–West HAC for pairwise accuracy, Giacomini–White for nested/conditional comparisons, and the Model Confidence Set (α=0.05) to identify a *superior set* rather than a single winner (arXiv:2505.11163v1, arXiv:2505.13933v2, arXiv:2604.10402v4).
- **Zero-shot claims do not hold.** TimesFM is only competitive after *incremental* fine-tuning; short-context pretrained variants fail on MDA/MAPE (arXiv:2505.11163v1). QRC’s advantage is a 10-qubit proof-of-concept with exponential-concentration and hardware caveats (arXiv:2505.13933v2). Treat any “beats HAR” claim as conditional on adaptation.
- **Leakage risks.** Do not use contemporaneous RV as a predictor of RV$_t$; align macro/VIX state variables to trading dates and lag them (the crisis/state dummies in arXiv:2510.16010v1 are window definitions, not features). In incremental fine-tuning, only re-use the *previous test segment* as new training data (arXiv:2505.11163v1).
- **Soundness tests:** residual diagnostics (Ljung–Box for serial correlation, ARCH–LM for remaining heteroskedasticity) and Student-$t$ vs GED robustness (arXiv:2510.16010v1); simulation recovery of $\alpha,\beta,\gamma,\nu$ under by-window splits; and Monte-Carlo validation of subordinator limit theorems (Shapiro–Wilk normality checks) for VGSA (arXiv:2507.17431v1).

## 5. Recommended first implementation in FinRobot

1. **Daily RV proxy module (S).** Build returns from `https://eodhd.com/api/eod/AAPL` (fallback tiingo/twelvedata) and compute a Garman–Klass / squared-return RV proxy when no intraday feed is configured. Data: OHLCV via `core_stock_apis`. Value: unblocks all volatility features without an intraday contract. Risk: GK is noisier than 5-min RV (arXiv:2604.10402v4, arXiv:2505.11163v1).
2. **HAR / HAR-$^{log}$ baseline (S).** Implement the 1/5/22-day HAR on $\log RV$ with Newey–West errors (arXiv:2505.11163v1, arXiv:2505.13933v2). Data: the RV proxy above. Value: the benchmark every other model must beat. Risk: linear rigidity; report MDA separately.
3. **GARCH(1,1) / EGARCH(1,1) / TGARCH(1,1) with Student-$t$ (M).** Per-symbol MLE, by-window refits, $\nu$ free. Data: daily returns only. Value: conditional-variance series and leverage/asymmetry diagnostics; direct fit to the corpus' dominant parameterization (arXiv:2510.16010v1). Risk: near-unit-root persistence in crisis windows.
4. **QLIKE-first evaluation harness (S).** MSE + QLIKE + MDA/sMAPE, DM (Newey–West), Giacomini–White and MCS at 95%; add the underprediction loss $U_{t+1}$ of §2.5. Data: none beyond forecasts. Value: prevents metric-shopping and makes every later model comparable (arXiv:2505.11163v1, arXiv:2604.10402v4, arXiv:2505.13933v2).
5. **Risk-sensitive specialist router (M→L).** Pool {HAR-RV, GARCH-$t$, FIGARCH, GRU, XGBoost}, 252-day excess-loss scoring with time/regime weights, calm/stress gates and a conditional HAR floor. Data: OHLCV + macro state vector from `https://api.stlouisfed.org/fred/series/observations`. Value: ~22–24% high-regime loss reduction vs rolling-best (arXiv:2604.10402v4). Risk: high miss-best rate; needs careful walk-forward validation and the HAR floor to avoid blow-ups.
6. **MGARCH portfolio-variance reconciliation (L).** Univariate GARCH on portfolio returns + DCC/BEKK, MinT reconciliation with the correlation-coherence fix. Data: multi-asset OHLCV (all `core_stock_apis`) + portfolio weights. Value: better portfolio-risk prediction under misspecification (arXiv:2603.17463v2). Risk: proxy noise can erase the gain; heavier compute.
7. **VGSA/CIR scenario generator (M).** Simulate VGSA paths from fitted $\theta,\sigma,\nu,\kappa,\eta,\lambda$ for tail/scenario analysis; no endpoint needed. Value: jump-clustering and fat-tail scenarios to complement GARCH VaR (arXiv:2507.17431v1). Risk: weak identification from daily data; theory-only paper with no OOS evidence — calibrate cautiously.
8. **Defer TimesFM / QRC (—).** TimesFM requires an external pretrained model plus incremental fine-tuning infrastructure (arXiv:2505.11163v1); QRC needs quantum hardware/simulator and is a proof-of-concept (arXiv:2505.13933v2). Mark both **out of scope** until the classical stack above is measured; state explicitly that FinRobot's data layer cannot train these end-to-end today.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2604.10402v4 | Risk-Sensitive Specialist Routing for Volatility Forecasting | 2026 |
| 2603.17463v2 | Multivariate GARCH and portfolio variance prediction: A forecast reconciliation perspective | 2026 |
| 2510.16010v1 | Institutional Differences, Crisis Shocks, and Volatility Structure: A By-Window EGARCH/TGARCH Analysis of ASEAN Stock Markets | 2025 |
| 2507.17431v1 | Analysing Models for Volatility Clustering with Subordinated Processes: VGSA and Beyond | 2025 |
| 2505.13933v2 | Quantum Reservoir Computing for Realized Volatility Forecasting | 2025 |
| 2505.11163v1 | Foundation Time-Series AI Model for Realized Volatility Forecasting | 2025 |
