# Derivatives & Options — learnings from the q-fin.ST corpus
`236` of 4372 corpus papers matched this category (203 with PDFs); this doc is based on a close reading of `6`.

## 1. What the corpus actually offers

- **Merton jump-diffusion can be *derived*, not assumed, from two information channels.** A max-entropy construction on log-price with a continuity constraint $\langle(\Delta\ln S)^2\rangle=k$ and a directionality constraint $\langle\ln(S'/S)\rangle=k_c$ yields GBM with drift $m_c=(\mu_c-\tfrac12\sigma^2)\Delta t$; adjoining a jump channel with arrival $\langle n\rangle=\lambda\Delta t$ and jump moments $\langle Y\rangle=\kappa,\ \langle Y^2\rangle=\nu$ yields the **Merton jump-diffusion** as the unique posterior, with a Gaussian jump size $P_J(Y)=\frac{1}{\sqrt{2\pi\delta^2}}\exp\!\big(-(Y-\kappa)^2/2\delta^2\big)$, $\delta^2=\nu-\kappa^2$ (arXiv:2607.06355v1).
- **The pricing measure is selected by the same inference:** imposing no-arbitrage through the mean log-return $\langle\ln(S'/S)\rangle_{rn}=(r_f-\tfrac12\sigma^2)\Delta t-\lambda_{rn}\langle e^Y-1-Y\rangle_{rn}\Delta t$ and maximising relative entropy selects the **Esscher transform** $P_{rn}=\frac1Z e^{\theta x}P_{JD}$ among the infinitely many martingale measures; the premium solves Merton's PIDE, with Black–Scholes–Merton as the $\lambda=0$ limit (arXiv:2607.06355v1).
- **Deep hedging works with tiny data.** A 3-input MLP trained under the *real-world* measure on as few as **256 trajectories** (or 256 overlapping windows of one 285-point path) beats discretised Black–Scholes and Leland under proportional costs; earlier deep-hedging work needed $10^5$–$10^6$ paths (arXiv:2505.22836v1).
- **The classical cost-aware hedge beats deep hedging on real data.** On 11,546 real BTC-option episodes, the **Whalley–Wilmott no-trade band** cut transaction cost by \$1.79/episode (95% CI [−2.21, −1.39], p<0.0001) vs Black–Scholes delta by trading ~8× less often; LSTM and feedforward CVaR policies all underperformed every classical benchmark (arXiv:2608.29025v1).
- **Scheduled FOMC meetings create a measurable pre-announcement IV premium** concentrated in short-dated ATM options: IV rises ~2 days before the meeting and up to ~50% on the announcement day before 2 pm ET, while *realised* volatility only rises after the press conference; the effect decays sharply with maturity (arXiv:2608.10693v1).
- **An ML IV-surface forecaster with an FOMC-date feature beats the random walk ~8–9% in 1-step RMSE**, and the FOMC dummy is statistically significant *on announcement days* (Diebold–Mariano p≈0.001–0.004 for nearly all call maturities), though globally the improvement is small (arXiv:2608.10693v1).
- **A time-varying-volatility-scaled SDF is recoverable from S&P 500 option prices alone** and predicts the equity premium out-of-sample: order-4 polynomials give $R^2_{OS}$ up to ~22.6% at 360-day maturity, beating historical-average, M-bound and CYL-bound benchmarks, with predictive power rising in the horizon (arXiv:2607.08500v2).
- **For short/medium maturities, stochastic volatility is nearly redundant and jumps do not activate.** Fourier calibration of Heston/Bates to single-name options finds vol-of-vol $\sigma_v\approx0$ and jump intensity $\lambda\approx0$ at 60-day maturity, i.e. the market-implied density is captured by (near-)deterministic volatility alone (arXiv:2605.27945v1).
- **Numerical transform choice is not a source of model risk.** Lewis (2001) inversion and Carr–Madan (1999) FFT produce near-identical Heston parameters (κ differs 1.22%, θ 0.00%, ρ 0.00%, v₀ 0.01%), confirming a well-posed calibration (arXiv:2605.27945v1).

## 2. Implementable formulas & algorithms

### 2.1 Merton jump-diffusion transition density (entropic derivation)
**Purpose.** Generate a jump-aware scenario process / density for option pricing and scenario stress tests.
**Formula.**
$$P_{JD}(x\mid n)=\frac{1}{\sqrt{2\pi(\sigma^2\Delta t+n\delta^2)}}\exp\!\left[-\frac{\big(x-m_c-n\kappa\big)^2}{2(\sigma^2\Delta t+n\delta^2)}\right],\qquad P_{JD}(x)=\sum_{n=0}^\infty \frac{(\lambda T)^n e^{-\lambda T}}{n!}P_{JD}(x\mid n)$$
with $m_c=(\mu_c-\tfrac12\sigma^2)\Delta t$. Log-price density solves the Kolmogorov–Feller equation (PIDE): $\partial_t p=-\big(\mu_c-\tfrac12\sigma^2\big)\partial_x p+\tfrac12\sigma^2\partial_x^2 p+\lambda\!\int\! p(x-y)-p(x)\,P_J(y)\,dy$ (arXiv:2607.06355v1).
**Required inputs.** Drift $\mu_c$, diffusion $\sigma$, jump intensity $\lambda$, jump mean $\kappa$ and second moment $\nu$ (⇒ $\delta^2=\nu-\kappa^2$).
**Parameters/defaults.** The paper fixes no magnitudes (pure theory); $\lambda=0$ recovers GBM and $\sigma=0$ recovers a compound-Poisson process as the two limits.
**Observed effect sizes.** None reported (theory). Its value is that it pins the *number* of free parameters (five) needed to reproduce the smile.
**Failure modes.** Truncating the Poisson sum too early leaves tail error; the model still cannot produce a *term structure* of skew (one constant $\lambda,\delta$ for all $T$).

### 2.2 Esscher risk-neutral transformation & Merton PIDE
**Purpose.** Convert the physical jump-diffusion into an arbitrage-free pricing measure without picking a utility function.
**Formula.** $P_{rn}(x)=\frac1{Z(\theta)}e^{\theta x}P_{JD}(x)$, with $\theta$ fixed by the martingale condition $\langle S'/S\rangle_{rn}=e^{r_f\Delta t}$; the convexity correction $\lambda_{rn}\langle e^Y-1-Y\rangle_{rn}\Delta t$ enters the risk-neutral log-drift. European price obeys Merton's PIDE, Black–Scholes–Merton as $\lambda\to0$ (arXiv:2607.06355v1).
**Required inputs.** Same as 2.1 plus $r_f$.
**Parameters/defaults.** One scalar $\theta$ per measure; solved from the martingale constraint.
**Observed effect sizes.** Analytical: the risk-neutral Poisson-weighted mixture of lognormals generates the smile/smirk directly.
**Failure modes.** Incomplete market ⇒ $\theta$ is not identified by no-arbitrage alone (the paper makes the observable choice explicit). Using the wrong observable (e.g. arithmetic vs log return) changes the measure.

### 2.3 Deep hedging under proportional transaction costs, light data
**Purpose.** Learn a discrete-time hedge that minimises the standard deviation of discounted terminal wealth $Z_T$ when rebalancing is costly.
**Formula.** Cost of a rebalance: $C_i=\alpha\big|\tfrac{\partial C_\nu}{\partial x}(X_{t_{i+1}},t_{i+1})-\tfrac{\partial C_\nu}{\partial x}(X_{t_i},t_i)\big|X_{t_{i+1}}+O(\Delta t)$; loss $=\operatorname{stdev}(Z_T)$. Volatility update: $\nu^2=\sigma^2+\alpha\sigma\sqrt{\tfrac{2}{\pi\Delta t}}$ (Leland). Discrete no-TC hedge error: $Z_T=\sum_{i=1}^{n}\tfrac12 e^{-rt_{i+1}}\Gamma_\nu X_{t_i}^2\!\left[\nu^2(t_{i+1}-t_i)-\big(\tfrac{X_{t_{i+1}}-X_{t_i}}{X_{t_i}}\big)^2\right]-C_0^\nu+O(\Delta t)$ (arXiv:2505.22836v1).
**Required inputs.** Simulated/real underlying paths under $P$ (drift need not equal $r$), strike, $r$, $\alpha$; NN state = {moneyness $X_t/K$, time-to-maturity $T-t$, previous hedge $H_{t-\Delta t}$}.
**Parameters/defaults.** MLP 3→64→32→1, ReLU; Adam lr $10^{-3}$; batch 64; 500 epochs; 256 trajectories; $S_0=1,\mu=0.05,\sigma=0.2,T=0.25$; $\alpha\in\{0,0.2\%,0.5\%,1\%,2\%\}$.
**Observed effect sizes.** At $\alpha=2\%$, 30 rebalances, overlapping-sequence calibration: NN mean cost **6.55%** (std 0.74%) vs BS **7.76%** (std 1.59%) and Leland **7.13%** (std 0.97%). With only 30 points the NN edge appears at $\alpha\ge1\%$; with 90 points at $\alpha\ge0.5\%$.
**Failure modes.** On real S&P 500 daily data (2024, 286 obs, SOFR 4.5%) the same net produced **unrealistic deltas** because realized volatility regimes shifted — raw price + moneyness alone is insufficient without a volatility-regime input.

### 2.4 Whalley–Wilmott no-trade band vs CVaR deep hedging (fair comparison)
**Purpose.** A cost-aware closed-form hedge that structurally suppresses small trades, benchmarked honestly against learned policies.
**Formula.** No-trade band half-width $H=\Big(\dfrac{3kS^2\Gamma^2}{2\lambda}\Big)^{1/3}$, $\Gamma=\dfrac{\phi(d_1)}{S\sigma\sqrt T}$; rebalance only to the band edge when $|\delta-\Delta|>H$. Leland vol used as the second benchmark: $\sigma_{adj}=\sigma\sqrt{1+\sqrt{\tfrac{2k}{\pi}\tfrac{1}{\sigma\sqrt{\Delta t}}}}$. Deep-hedging loss is CVaR at 95%: $\mathrm{CVaR}_\alpha=\frac{1}{\lceil(1-\alpha)N\rceil}\sum_{i\in \text{worst }(1-\alpha)N}L_i$, optionally plus a turnover penalty (arXiv:2608.29025v1).
**Required inputs.** Underlying + option mid quotes (mark IV), hourly path; round-trip cost $k$; risk-aversion $\lambda$.
**Parameters/defaults.** $k=5$ bp round-trip (2.5 bp/trade); $\Delta t$ = 1 hour; $\lambda=60$ (chosen by inspection; $\lambda=0.01$ gave a band wider than the whole delta range); LSTM 32 units, feedforward 2×32 ReLU, output $1.5\tanh(\cdot)$, Adam lr $10^{-3}$, wd $10^{-5}$, batch 256, early stop patience 10.
**Observed effect sizes.** WW: 2.47 trades/episode, cost 7.91, mean P&L −30.16, CVaR −864.23 vs BS delta 20.40 trades, cost 9.70, P&L −38.82, CVaR −885.24 (11,546 episodes). Cost saving \$1.79 (p<0.0001); P&L advantage directional but **not** significant (CI crosses 0). All three neural configs ≈20.4 trades (indistinguishable from continuous delta hedging) across a 20× turnover-penalty range.
**Failure modes.** WW's P&L edge **vanished in a calm validation window** while its cost edge persisted ⇒ result is regime-conditional; standard continuous-output nets lack the structural sparsity of an explicit band.

### 2.5 IV-surface construction + scheduled-event dynamics + ML forecasting
**Purpose.** Build a fixed-grid IV surface and forecast it, with an exogenous event feature for pre-announcement uncertainty.
**Formulas.** Fixed grid: log-forward-moneyness $k=\ln\frac{S_t}{K}e^{rT}$, total variance $w=\sigma^{IV2}T$; maturities $T^*=\{0,\dots,20\}$ days (0-DTE treated as 0.5 DTE), 41 strikes in $[-0.2,0.2]$.
- Linear: piecewise-linear $w$ in strike then maturity; linear wing extrapolation (Lee's bound), slope from a 2-point finite difference.
- AHBS: $\sigma^{IV}(k,T)=\alpha_0+\alpha_1 k+\alpha_2 k^2+\alpha_3 T+\alpha_4 T^2+\alpha_5 kT+\varepsilon$.
- SVI: $w(k,T)=a+b\big[\rho(k-m)+\sqrt{(k-m)^2+\sigma^2}\big]$.
Forecast target $\sigma^{IV}_t(K^*,T^*)=f(\sigma^{IV}_{t-1},\dots,\sigma^{IV}_{t-l},X_t)+\varepsilon_t$, benchmark random walk $\hat\sigma^{IV}_t=\sigma^{IV}_{t-1}$; $X_t=+1$ on FOMC day, $-1$ the day after (arXiv:2608.10693v1).
**Required inputs.** Full SPX option surface (all expiries/strikes, bid/ask, OI, IV), underlying price, risk-free curve, FOMC calendar.
**Parameters/defaults.** ConvLSTM: lookback $l=5$, lr $5\times10^{-5}$, 3×3 kernel, 32 filters, batch 32, dropout 0.1, MSE, Adam; 112,033 params (168,126 with event branch). Filters: bid≤ask, bid>0, IV>0, convexity & monotonicity in strike, OI>0.
**Observed effect sizes.** Surface fit RMSE: linear 0, SVI 0.02/0.01, AHBS 0.21/0.14 (call/put). 1-step RMSE gain vs RW ≈**8%** (call) / **9%** (put), best with SVI. IV rises ~2 days pre-FOMC, up to **~50%** on announcement day for 0-DTE; effect is strongest at ATM and decays with maturity. DM test on FOMC days with the dummy: p≈0.001–0.004 for almost all call maturities.
**Failure modes.** 0-DTE options are near-unpredictable; error concentrates in **short-maturity wings**; a perfect-fitting interpolation (linear) can *hurt* forecasting through noise overfit; global DM significance is weak because FOMC days are few.

### 2.6 SDF from option prices and equity-premium prediction
**Purpose.** Recover a forward-looking pricing kernel from the cross-section of option prices and use it to forecast the equity premium.
**Formula.** Volatility-scaled piecewise-polynomial SDF
$$n_{TVS}(S_T)=\exp\!\Big\{f_{p,n}\Big(\tfrac{1}{\sigma_{t,t+\tau}\sqrt{\tau}}\ln\tfrac{S_{t+\tau}}{F_{t,t+\tau}}\Big)\Big\},\qquad n_{CVS}(S_T)=\exp\!\Big\{f_{p,n}\Big(\tfrac{1}{\bar\sigma^*_\tau\sqrt{\tau}}\ln\tfrac{S_{t+\tau}}{F_{t,t+\tau}}\Big)\Big\}$$
where $f_{p,n}$ is degree-$n$ polynomial on $[y_{\min},y_{\max}]$ with linear extrapolation (continuous value and slope). Sample strikes $K_{i,t,\tau}=F_{t,\tau}e^{z_i\sigma\sqrt\tau}$, $z_i\in\{-1,-0.6,-0.2,0.2,0.6,1.0\}$. Estimate $\theta$ by minimising the Hansen–Jagannathan distance $\delta^2=\mathbb E[m(\theta)\mathbf f-\mathbf v]'\,\mathbb E[\mathbf f\mathbf f']^{-1}\,\mathbb E[m(\theta)\mathbf f-\mathbf v]$ (GMM, $W=\mathbb E[\mathbf f\mathbf f']$). Variance-swap rate $V_{t,T}=\frac{2}{T-t}\big[\int_0^F\frac{P(K)}{K^2}dK+\int_F^\infty\frac{C(K)}{K^2}dK\big]$. Bond-consistency factor (Carr–Madan spanning), with $m_{t,T}(S_T)=\beta_{t,T}\,n_t(S_T)$:
$$\beta_{t,T}=\frac{D_{t,T}}{n_t(F_{t,T})}+\int_0^{F_{t,T}}\Big(\tfrac{1}{n_t}\Big)^{(2)}(K)\,P_{t,T}(K)\,dK+\int_{F_{t,T}}^{\infty}\Big(\tfrac{1}{n_t}\Big)^{(2)}(K)\,C_{t,T}(K)\,dK$$
(arXiv:2607.08500v2).
**Required inputs.** Full option surface across many strikes and 7 maturities (30–360 days), forward $F$, $r$, dividend yield — all extractable from options alone.
**Parameters/defaults.** Polynomial order $n=2,\dots,6$; **order 4 is the stable best**; integration intervals $[Fe^{-4\sigma_p\sqrt{T-t}},F]$, $[F,Fe^{4\sigma_c\sqrt{T-t}}]$, 1000 trapezoid points, $\Delta$ finite-difference for $g^{(2)}$.
**Observed effect sizes.** TVS passes Hansen's J-test at lower orders than CVS; order-4 out-of-sample $R^2_{OS}$ (Campbell–Thompson vs historical-average): 7.04% (all maturities), **22.57%** at 360 days; power increases monotonically in horizon and is ~0/negative at 30 days. Option returns peak at Call $z=0.2$–$0.6$ then decline in deep OTM ⇒ non-monotonic (hump→W-shaped) SDF.
**Failure modes.** CVS SDF gives **negative** short-maturity equity premia during the 2020 COVID shock (inconsistent); low-order polynomials lack freedom to fit the call wing; deep-OTM numerical integration is unstable.

### 2.7 Heston/Bates/CIR calibration via Lewis inversion and Carr–Madan FFT
**Purpose.** Calibrate a stochastic-vol model plus a short-rate model to a small option panel and price exotics.
**Formulas.** Heston: $dS_t=rS_tdt+\sqrt{v_t}S_tdW_t^S$, $dv_t=\kappa(\theta-v_t)dt+\sigma\sqrt{v_t}dW_t^v$, $\langle dW^S,dW^v\rangle=\rho dt$, call $C=S_0P_1-Ke^{-rT}P_2$. Carr–Madan price: $C(K)=e^{-\alpha k}\frac1\pi\int_0^\infty e^{-iuk}\frac{\phi(u-i(\alpha+1))}{\alpha^2+\alpha-u^2+i(2\alpha+1)u}du$, $k=\ln K$. Bates = Heston $\times\exp[\lambda T(e^{iu\mu_J-\frac12u^2\sigma_J^2}-1)]$. CIR bond: $P(0,T)=A(0,T)e^{-B(0,T)r_0}$, $\gamma=\sqrt{\kappa^2+2\sigma^2}$, Feller $2\kappa\theta>\sigma^2$ (arXiv:2605.27945v1).
**Required inputs.** Option panel (calls+puts, put–call parity for forwards), spot, $r$; rate curve (Euribor/treasury) for CIR.
**Parameters/defaults.** Two-stage optimiser: Differential Evolution then L-BFGS-B; integration limit $u_{max}=200$; MC 120k–200k paths (converges ≈175k); day count 250/yr.
**Observed effect sizes.** Lewis vs Carr–Madan Heston parameters: κ 0.3981 vs 0.4029 (1.22%), θ identical, ρ 0.9906 both, v₀ 0.10157 vs 0.10156. Bates fit at 60 days: **λ≈0, σ_v≈0** (jumps don't activate); CIR to Euribor: κ=2.0, θ≈4.22%, σ=0.411, r₀=0.404%, half-life 0.35 yr, discount-factor RMSE **3.65 bp**; average DF 0.9745 vs flat-curve 0.996 ⇒ flat pricing overvalues by ≈2.2%. Asian call fair \$4.888 (Lewis) vs \$4.888 (FFT), 4% client margin.
**Failure modes.** Vol-of-vol → 0 makes the model collapse to near-Black–Scholes at short tenors and the %-difference in σ is meaningless (tiny denominators); Normal jumps miss heavy tails; CIR forbids negative rates; mid-quote calibration ignores bid–ask/liquidity premia; single-asset parameter stability is untested.

## 3. Data requirements → available endpoints

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Full SPX IV surface (all expiries/strikes, delayed) | `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json` | `options_surface` | cboe | `ok=false`, code `http`, **HTTP 307** (redirect — not currently usable as-is) |
| Per-ticker option chain (expiries, strikes, IV) | `moomoo://get_option_chain` | `options_data` | moomoo | `ok=false`, code `gateway` (local OpenD SDK) |
| Expected move / underlying option overview | `moomoo://get_option_underlying_overview` | `expected_move` | moomoo | `ok=false`, code `gateway` |
| Fed target-rate odds (for FOMC feature) | `moomoo://get_fed_watch_target_rate` | `fed_watch` | moomoo | `ok=false`, code `gateway` |
| Economic / FOMC calendar | `moomoo://get_economic_calendar` | `economic_calendar` | moomoo | `ok=false`, code `gateway` |
| Risk-free curve (treasury) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | `ok=false`, code `connect` (**ReadTimeout**) |
| Underlying spot / EOD | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | `ok=true` |
| Underlying spot (alt) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | `ok=true` |
| Dividend / forward inputs | `https://eodhd.com/api/div/AAPL` | `corporate_actions` | eodhd | `ok=true` |
| Macro series (rates, CPI, used with event studies) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | `ok=true` |
| Realised volatility inputs | `https://www.alphavantage.co/query` | `technical_indicators` | alpha_vantage | `ok=true` |
| FOMC probability proxy | `https://gamma-api.polymarket.com/markets` | `prediction_markets` | polymarket | `ok=true` |
| News / event sentiment | `https://eodhd.com/api/sentiments` | `news_sentiment` | eodhd | `ok=true` |
| News sentiment (alt) | `https://api.gdeltproject.org/api/v2/doc/doc` | `news_sentiment` | gdelt | `ok=false`, code `rate_limited` (HTTP 429) |
| **BTC/Deribit option chain (real-data deep-hedging study)** | — | — | — | **gap** (no crypto-options provider in inventory) |
| **Historical option surface, daily (SDF, FOMC, backtests)** | — | — | — | **gap** (CBOE row is a single delayed snapshot; OptionMetrics is commercial) |
| **Single-name daily option panel (Heston/Bates calibration)** | — | — | — | **gap** (needs a chain history, not just a snapshot) |
| **Variance-swap / VIX term structure direct** | — | — | — | **gap** (must be synthesised from the surface via $V_{t,T}$) |

**Key point on `options_surface` vs `options_data`.** The `options_surface` category is a **single-vendor, full-surface** feed (cboe, SPX only) — it is the right shape (all expiries × strikes) but is one delayed snapshot of one index, and the probe currently fails on an HTTP 307 redirect. Everything in §2.5 and §2.6 needs *many maturities × many strikes on a grid over time*, which this row can supply only for SPX and only at the current instant. Single-name surfaces (SM Energy etc.) must come from `options_data` (`moomoo::get_option_chain` → yfinance failover), which yields a chain but no historical surface. Deep-hedging on BTC (arXiv:2608.29025v1) and any historical-surface study are **not implementable against the current inventory** without adding a vendor.

## 4. Pitfalls, validation and measurement

- **Regime leakage is the dominant trap.** The deep-hedging papers show results are regime-conditional: arXiv:2505.22836v1's net fails on real 2024 S&P data under volatility-regime shifts, and arXiv:2608.29025v1's Whalley–Wilmott P&L edge *disappears in a calm window* while its cost edge persists. Always split train/validation/test chronologically (2608.29025 uses Dec-2019→Dec-2022 train, Jan–Aug-2023 validation, Sep-2023→Dec-2024 test) and report multi-regime windows.
- **Correlated episodes inflate significance.** Episodes sharing a sampled day share the price path; arXiv:2608.29025v1 uses a **block bootstrap blocking by day** (5,000 resamples) rather than per-episode resampling. With only 16 independent days, P&L CIs cross zero even when costs are hugely significant — replication needs more independent blocks.
- **Volatility-scaling is not cosmetic.** The absence of scaling produces inconsistent SDFs (CVS fails J-tests at 60–270 days; TVS passes) and negative COVID-era short-maturity equity premia (arXiv:2607.08500v2). Normalise the dependent variable before fitting.
- **Overfitting the surface hurts forecasting.** Linear interpolation fits the surface perfectly (RMSE 0) yet forecasts *worse* than SVI; the noise it fits generalises poorly (arXiv:2608.10693v1). Score forecasters with RMSE **and** MPE (bias) and use Diebold–Mariano with HAC errors for overlapping horizons.
- **No-arbitrage filters change the dataset materially.** Bid≤ask, bid>0, IV>0, strike monotonicity/convexity and OI>0 (arXiv:2608.10693v1; arXiv:2607.08500v2 drops ask>2·bid and zero-volume contracts). Report how many rows each filter removes (2608.29025 loses 27% to the two-sided-quote filter alone).
- **Jumps and stochastic vol may be redundant at short tenor.** Reporting λ≈0, σ_v≈0 is a *finding*, not a calibration failure (arXiv:2605.27945v1). Do not over-parameterise short-dated fits; monitor the Feller condition $2\kappa\theta>\sigma^2$ and discard the meaningless %-error on σ when σ≈0.
- **Soundness checks.** (i) Heston price agreement across two independent transform methods (Lewis vs Carr–Madan, tolerance ~1.5%); (ii) SDF bond-price consistency $\mathbb E_t[m_{t,T}]=D_{t,T}$; (iii) Hansen J-test for over-identifying restrictions; (iv) for hedging, compare against **both** cost-unaware (BS delta) and cost-aware (Leland, Whalley–Wilmott) baselines under an identical cost assumption.

## 5. Recommended first implementation in FinRobot

1. **Ingest and normalise the SPX surface from `options_surface` (cboe).** Add redirect-following for the `_SPX.json` endpoint (probe shows HTTP 307) and parse into a `(expiry, strike, mid, IV, OI, bid, ask)` frame; apply the §4 filters and build the fixed grid ($k\in[-0.2,0.2]$, $T\in\{0..20\}$ d, 0-DTE→0.5 DTE). *Data:* cboe surface + `risk_free_curve` (repair the ReadTimeout) + `core_stock_apis` spot. *Value:* unlocks every §2.5/§2.6 technique. *Risk:* single-vendor SPX-only, delayed. *Effort:* M.
2. **Ship the pre-FOMC IV event study + event-aware surface forecaster.** Reproduce the ~2-day pre-announcement rise and ATM/short-dated concentration; train the ConvLSTM (l=5, lr 5e-5, 32 filters) with an FOMC dummy feature. *Data:* surface from (1) + FOMC calendar (`economic_calendar` moomoo or a hardcoded Fed calendar; `fed_watch` for odds). *Value:* ~8–9% 1-step RMSE gain and significant event-day skill (arXiv:2608.10693v1). *Risk:* small FOMC sample ⇒ global significance weak; 0-DTE noise. *Effort:* L.
3. **Implement deep hedging with a cost-aware-baseline scorecard.** Train the 3-input MLP (256 paths, overlapping windows) minimising stdev($Z_T$); always benchmark against BS delta **and** Leland and the Whalley–Wilmott band $H=(3kS^2\Gamma^2/2\lambda)^{1/3}$ under an identical $k$. *Data:* simulated GBM paths first, then `options_data` chains (`moomoo`/yfinance) for real deltas. *Value:* reproduces a ~1.2%-of-notional cost reduction at $\alpha=2\%$ (arXiv:2505.22836v1) while guarding against the over-claimed deep-hedging advantage (arXiv:2608.29025v1). *Risk:* needs a volatility-regime input to survive real data. *Effort:* M.
4. **Add a jump-diffusion scenario engine.** Implement the Merton density (Poisson mixture of Gaussians) and the Esscher risk-neutral transform; expose $\lambda,\kappa,\delta$ as scenario dials. *Data:* none beyond a spot and $r$; calibrate $\lambda,\delta$ from the surface via (1). *Value:* jump-aware scenario/stress pricing unavailable in a pure-GBM engine (arXiv:2607.06355v1). *Risk:* parameter identifiability — anchor to observed short-dated skew. *Effort:* S/M.
5. **Add an SDF / equity-premium signal (research tier).** Fit the order-4 TVS SDF by HJ-distance GMM on the surface grid and compute the option-implied equity premium; use it as a slow, long-horizon signal. *Data:* multi-strike, multi-maturity surface over a long history — **blocked** by the historical-surface gap; can only run going forward from (1)'s snapshots. *Value:* $R^2_{OS}$ up to ~22.6% at 360 days (arXiv:2607.08500v2). *Risk:* requires an accumulated history and careful bond-consistency adjustment. *Effort:* L.
6. **Add Heston/Bates/CIR calibration as a pricing sanity-check service.** Calibrate via Lewis inversion and Carr–Madan FFT (cross-check to <1.5%) using the two-stage DE+L-BFGS-B optimiser; report λ, σ_v, Feller condition and the flat-vs-CIR discount-factor gap. *Data:* option panel (`options_data`) + rate curve (`risk_free_curve`/`macro_data` fred). *Value:* detects when the market's skew needs jumps vs stochastic vol (arXiv:2605.27945v1). *Risk:* mid-quote calibration; single-asset stability. *Effort:* M.

## Appendix — papers read

| arXiv id | title | year |
|---|---|---|
| 2607.06355v1 | Entropic Dynamics of Jump-Diffusion Option Pricing | 2026 |
| 2505.22836v1 | Model-Free Deep Hedging with Transaction Costs and Light Data Requirements | 2025 |
| 2608.29025v1 | Deep Hedging Under Realistic Market Frictions: A Regime-Conditional Empirical Study of Dynamic Option Hedging on Bitcoin Options | 2026 |
| 2608.10693v1 | When the Fed Speaks: Dynamics and Forecasts of the Volatility Surface | 2026 |
| 2607.08500v2 | Estimating the Stochastic Discount Factor from Option Prices and Predicting the Equity Premium | 2026 |
| 2605.27945v1 | Stochastic Volatility, Jumps, and Rates: A Unified Framework for Option Pricing and Term-Structure Simulation | 2026 |
