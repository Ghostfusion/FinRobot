# Asset Pricing & Anomalies — learnings from the q-fin.GN corpus

`350` of 3095 corpus papers matched this category (348 with PDFs); this doc is based on a close reading of `6`.

Headline: **this category is mostly economic context, not a machine-readable estimator pool.** Five of the six
papers are empirical tests of factor models, momentum and bubbles; only two produce constructions that can be
run directly on FinRobot's data (a factor-model GRS comparator, a momentum/liquidity backtester), one produces a
diagnostic (LPPL bubble monitor), and two are lab/simulation models whose statistics are testable but not
tradable. The binding data gap is the same one flagged in
[`../qfin-st/factor-models-alpha.md`](../qfin-st/factor-models-alpha.md): **no provider serves the
Fama–French/Carhart factor-return series, point-in-time market cap, or point-in-time book equity**, so every
factor test below must first *build* its factors from a survivorship-prone panel. Cross-links:
[`../qfin-st/factor-models-alpha.md`](../qfin-st/factor-models-alpha.md) (factor construction, loading-gap
tests) and [`../qfin-st/regime-switching.md`](../qfin-st/regime-switching.md) (regime-conditional
risk models) already derive the construction machinery; this doc concentrates on the *tests* — GRS
model comparison, momentum-universe shrinkage, physical-momentum rankings, and bubble/crash detection.

## 1. What the corpus actually offers

- **FF5 vs FF3 on China's A-share market, 2005-01-01…2020-12-31 (CSMAR, monthly; ST/PT, first six months
  post-IPO and financials excluded).** OLS of the five-factor model on the 5×5 Size-B/M, Size-OP and
  Size-Inv portfolios makes MKT, SMB and RMW significant at 5% (p<0.05), while **HML has t = −1.35
  (p = 0.179)** and **CMA has t = 1.33 (p = 0.184)** — both nominally "redundant" in the time-series
  regression (arXiv:2112.03170v1).
- **Redundancy in the full-sample regression is not redundancy in the cross-section.** After orthogonalising
  HML and CMA ($HMLO$, $CMAO$), the 5×5 regressions show HML coefficients rising monotonically across the
  B/M quintile within each size row (up to t = 4.75 in the Big/high-B/M cell) and CMA coefficients positive
  for conservative and negative for aggressive investment portfolios (down to t = −8.18) (arXiv:2112.03170v1).
- **GRS test (H0: all intercepts zero) favours FF5 in every sort.** GRS statistics fall from
  2.508→2.389 (25 Size-B/M), 3.073→2.377 (25 Size-OP), 2.226→1.670 (25 Size-Inv); both models *accept* the
  null at the 5% level, so GRS is used here as a *comparison* not a rejection (arXiv:2112.03170v1). Mean
  absolute intercept $A|\alpha_i|$ moves 0.019→0.101, 0.090→0.049, 0.048→0.067 respectively.
- **The value factor's information sits in CMA, not RMW.** $\mathrm{corr}(HML,RMW)=0.000637$ but
  $\mathrm{corr}(HML,CMA)=0.475$ (significant) — consistent with HML becoming redundant once CMA enters
  (arXiv:2112.03170v1). A-share turnover fell from >500% in earlier years to 200–300%; US turnover is ~100%
  (arXiv:2112.03170v1).
- **Momentum is not homogeneous in the universe.** In the KOSPI 200 (South Korea, 2000-01…2011-12, KRX daily
  adjusted prices) the best monthly decile momentum return is ≈2%/month; **shrinking the universe to exclude
  the KOSPI 50 (largest 50 caps) adds 0.1–0.6%/month**, and excluding the KOSPI 50 from the KOSPI 100 adds up
  to 1.0%/month; including KOSPI 50 components *weakens* the strategy (arXiv:1211.6517v1).
- **The top 41–100 caps (S6–S8 of the KOSPI 200) outperform every other size decile** on both weekly and
  monthly scales; the largest decile S10 underperforms — the size-return relation on this large-cap-biased
  universe is *skewed toward mid-caps*, not monotone (arXiv:1211.6517v1).
- **Costs eat short-horizon momentum.** KOSPI 200 monthly momentum Sharpe is 0.15–0.2 (annualised 0.5–0.7)
  before cost; with 35 bps per winner/loser basket (70 bps round-trip) only longer-holding strategies survive,
  because the charge is one-time (arXiv:1211.6517v1).
- **A liquidity sort is more stable than a return sort.** Sorting on fractional volume (volume/outstanding
  shares) gives monthly implemented returns of 1.4–1.9% after 70 bps, volatility 7.25–8.75% (vs 8–12% for
  return momentum), and Sharpe >0.2 for almost all lookback/holding pairs (arXiv:1211.6517v1).
- **Investor-group flows have opposite signs.** Individual and institutional net buying negatively predicts
  future returns (contrarian); **foreign-investor net buying positively predicts**, and the foreign edge is
  concentrated in the KOSPI 50/large caps (arXiv:1211.6517v1).
- **Physical momentum: 11 ranking definitions** built from velocity $v=$ log return and mass
  $m\in\{\upsilon\text{ (turnover)},\ \tau\text{ (transaction value / market cap)},\ 1/\sigma\}$; classes
  $p^{(1)}=\sum mv$, $p^{(2)}=\sum mv/\sum m$ (centre-of-mass), $p^{(3)}=\bar v/\sigma$ (Sharpe-like)
  (arXiv:1208.2775v5).
- **KOSPI 200, weekly 6/6 contrarian:** best rule $p^{(1)}(\upsilon,R)$ returns **0.261%/week** (std 2.444%)
  vs the traditional $p^{(0)}$ 0.069%/week (std 2.846%); max drawdown roughly halves (33.4%→20.4%)
  (arXiv:1208.2775v5).
- **S&P 500, weekly 6/6 contrarian:** best rule $p^{(3)}(1/\sigma,R)$ returns **0.107%/week** vs 0.014% for
  $p^{(0)}$ (~7×), with volatility ~50% lower; the Fama–French three-factor model does **not** explain these
  returns (arXiv:1208.2775v5). Data windows: KOSPI 200 2003-01…2012-12, S&P 500 identical window.
- **LPPL bubble model** (Sornette/Woodard): $\ln p(t)=A+B(t_c-t)^m[1+C\cos(\omega\ln(t_c-t)+\phi)]$ with
  $B<0$, $0<m<1$; the preferred scaling ratio is $\lambda=e^{2\pi/\omega}$ (arXiv:0905.0220v1).
- **2008-crisis magnitudes** (framing context for the crash tests): subprime losses ≈$250bn (Oct 2007);
  expected world output loss ≈$4,700bn (≈20×); world stock-market-capitalisation decline ≈$26,400bn
  (≈100×, Jul 2007→Nov 2008). Global CDO issuance $150bn (2004) → ~$500bn (2006) → $2tn (end-2007);
  cumulative notional $0.6tn→$26tn by end-2006 (arXiv:0905.0220v1).
- **Macro fingerprints of the bubble regime:** US household net worth/GDP stable at 300–350% for >40 years,
  then two peaks above 450% since 1995; Fed funds 6.5% (2000) → 1% (2003–04); the Fed rate **lags** the
  S&P 500 by a robustly estimated 1–2 months (reverse causality); ~40% of major US firms' income from
  financial investments; Hang Seng averaged 13.8%/yr with 8 drawdowns >15% in <3 weeks
  (arXiv:0905.0220v1). A bubble lands smoothly about **one-third** of the time, so crash forecasts are only
  probabilistic (arXiv:0905.0220v1).
- **Sociophysics bubble model (Galam):** with local majority groups of size 3,
  $p_{t+1}=p_t^3+3p_t^2(1-p_t)$, fixed points $p_S=0$, $p_{c,3}=0.50$ (unstable), $p_B=1$; the number of
  interactions to an attractor is $n\simeq-\ln|p_{c,3}-p_0|/\ln(3/2)$ (arXiv:1106.1577v1).
- **With groups of size 4 and an optimism parameter $k$**,
  $p_{t+1}=p_t^4+4p_t^3(1-p_t)+6k\,p_t^2(1-p_t)^2$; the separator moves from **0.23** (k=1, fully
  optimistic) through 0.50 (k=0.5) to **0.77** (k=0, pessimistic); a mood shift 1→0 jumps the separator
  0.23→0.77 and reaches the down limit in only 2–3 updates — the model's definition of a crash
  (arXiv:1106.1577v1).
- **Institutionalisation in a high-efficiency lab market:** 62 undergraduates, 10 sessions × 6 traders ×
  10 periods × 120 s, dividend 20¢/share with prob 0.5. Ex-ante declared prices fit intrinsic value better
  than actual trading prices in 9/10 sessions; the **common discrepancy component dominates variance in
  9/10 sessions and rises during trading**; no overconfidence bias — bubbles arise even with atomistic
  agents, complete information and no communication (arXiv:1609.04629v1).
- **Off-topic note.** None of the six is off-topic. The weakest fits are arXiv:1609.04629v1 (a laboratory
  sociology experiment, no market data) and arXiv:1106.1577v1 (a deterministic sociophysics model with no
  estimation on real prices); both are retained because each supplies a *testable bubble-formation statistic*
  (common-discrepancy component; separator drift) that other papers in this doc do not.

## 2. Implementable formulas & algorithms

### 2.1 Fama–French factor construction and the GRS test
**Purpose.** Build the market/SMB/HML/RMW/CMA series from a panel and decide, per sort, whether the
five-factor model dominates the three-factor model by comparing intercept vectors.

**Formula.** Five-factor regression and the 2×3 factor definitions (arXiv:2112.03170v1):
$$R_{it}-R_{Ft}=a_i+b_i(R_{Mt}-R_{Ft})+s_i SMB_t+h_i HML_t+r_i RMW_t+c_i CMA_t+e_{it}$$
$$HML=\tfrac{SH+BH}{2}-\tfrac{SL+BL}{2},\quad RMW=\tfrac{SR+BR}{2}-\tfrac{SW+BW}{2},\quad
CMA=\tfrac{SC+BC}{2}-\tfrac{SA+BA}{2}$$
$$SMB=\tfrac{SMB_{B/M}+SMB_{OP}+SMB_{Inv}}{3},\qquad
SMB_{B/M}=\tfrac{SH+SN+SL}{3}-\tfrac{BH+BN+BL}{3}$$
Size split at the median; B/M, OP, Inv split at the 30%/70% quantiles; each SMB term is the average of its
three 2×3 sub-SMBs. The GRS statistic (H0: $\alpha=0$ for all $N$ portfolios, $K$ factors, $T$ periods) is
$$\mathrm{GRS}=\frac{T}{N}\cdot\frac{T-N-K}{T-K-1}\cdot
\frac{\hat\alpha'\hat\Sigma^{-1}\hat\alpha}{1+\bar f'\hat\Omega^{-1}\bar f}\ \sim\ F(N,\,T-N-K)$$
and the companion summary is $A|\alpha_i|=\tfrac1N\sum_i|\hat a_i|$.

**Required inputs.** Monthly (or daily) total-return panel for a survivorship-free universe; point-in-time
market cap; book equity, operating profitability (OP) and asset growth (Inv) as of formation; risk-free rate.
Excess returns $R_{it}-R_{Ft}$.

**Parameters & defaults.** 2×3 sorts, median/30/70 breaks (the papers' own); 5×5 dependent portfolios;
orthogonalise HML against CMA (and vice versa) by regressing one on the other and taking the residual
($HMLO$, $CMAO$); T = 192 months for the A-share study (2005–2020).

**Observed effect sizes.** FF5 GRS < FF3 GRS in all three sorts (2.389/2.377/1.670 vs 2.508/3.073/2.226);
both accept the null at 5% (arXiv:2112.03170v1). MKT/SMB/RMW p<0.05; HML p=0.179, CMA p=0.184.

**Failure modes.** Treating a non-significant full-sample $h_i$ or $c_i$ as "the factor is useless": the
orthogonalised 5×5 regressions still load significantly (arXiv:2112.03170v1). GRS is a *relative* statistic
here — both models accept the null, so a smaller GRS is evidence of better fit, not of correctness. Corpus
sources disagree because samples differ: an earlier study using 1995–2014 found FF3 *better*, this one
2005–2020 finds FF5 better — the 2005 share-structure reform is the discontinuity (arXiv:2112.03170v1).

### 2.2 Momentum decile backtest with universe shrinkage and transaction cost
**Purpose.** Measure whether a J-month lookback / K-month holding decile momentum portfolio survives costs,
and how its performance changes when the tradable universe is partitioned by index membership (cap sorting).

**Formula.** Sort the universe by cumulative return over $[t-J,t-1]$ into deciles; $R1$ = losers, $R10$ =
winners; dollar-neutral long $R10$ / short $R1$, equal weights. With raw returns $r_W,r_L$,
$$r_\Pi=r_W-r_L,\qquad r_I=r_\Pi-(c_W+c_L),\qquad \mathrm{PF}=\frac{r}{|\,\mathrm{sgn}(r)\,|r|\,|}$$
Switching to the contrarian portfolio is $r_\Pi^\dagger=-r_\Pi$. Subuniverse constructions follow cap/sector
rules (KOSPI 200 universe shown): $T\setminus H^c=(200\setminus100)$, $T\setminus F^c=(200\setminus50)$,
$H\setminus F^c=(100\setminus50)$, $(T\setminus H^c)\cup F=(200\setminus100+50)$ (arXiv:1211.6517v1).

**Required inputs.** Daily split/dividend-adjusted prices; index membership or a cap-sorted universe;
transaction-cost rate; outstanding shares (for the liquidity variant).

**Parameters & defaults.** Ten deciles (equal size); $J,K\in\{1,\dots,12\}$ months (weekly pairs also
reported); transaction cost 35 bps per basket (70 bps round-trip) for the Korean market; overlapping
portfolios used to enlarge the sample (arXiv:1211.6517v1, arXiv:1208.2775v5).

**Observed effect sizes.** Best monthly KOSPI 200 momentum ≈2%/month; excluding the KOSPI 50 adds
0.1–0.6%/month ((100\50) beats (100) by up to 1.0%/month); including KOSPI 50 (e.g. 200\100+50) is 0.3–0.6%
weaker; monthly Sharpe 0.15–0.2 pre-cost (arXiv:1211.6517v1).

**Failure modes.** Universe construction is not random sampling — the KOSPI 200 rule (cap + sector) itself
drives the result, so the "shrinkage" effect is a statement about *which* stocks, not a free parameter
(arXiv:1211.6517v1). Costs are one-time, so short-horizon strategies look fine gross and die net; overlapping
portfolios inflate the effective sample and understate serial dependence; stocks with too few trading days in
a lookback must be dropped (arXiv:1208.2775v5).

### 2.3 Liquidity-sorted portfolio
**Purpose.** Use a turnover-based sort as a more stable alternative (or overlay) to return momentum.

**Formula.** Rank each as-of date by past fractional volume
$$\upsilon_{t,k}=\frac{1}{k}\sum_{i=0}^{k-1}\frac{V_{t-i}}{\text{shares outstanding}_{t-i}}$$
Short the most illiquid decile (L1), long the most liquid decile (L10), equal-weighted dollar-neutral; apply
the same $r_I=r_\Pi-(c_W+c_L)$ convention (arXiv:1211.6517v1).

**Required inputs.** Daily volume and outstanding shares (or a directly supplied turnover series) over the
lookback window; prices for total return.

**Parameters & defaults.** Ten deciles by fractional volume; 35 bps per basket; same lookback/holding grid as
the momentum test. Inverse-volatility mass $1/\sigma$ is the physical-momentum analogue (§2.4).

**Observed effect sizes.** Monthly implemented returns 1.4–1.9% after 70 bps over all parameter pairs;
volatility only 7.25–8.75% (vs 8–12% for return momentum); Sharpe >0.2 almost everywhere; sign flips to
positive when the universe includes the KOSPI 50 (large caps), i.e. the liquidity-return correlation is
universe-dependent (arXiv:1211.6517v1).

**Failure modes.** Fractional volume is only a proxy for liquidity (no spread/Amihud available on daily bars);
the correlation changes sign across universes, so do not port a fitted sign across markets; delisting and
partial-month stocks need explicit handling.

### 2.4 Physical momentum ranking criteria
**Purpose.** Replace the single cumulative-return sort with a family of velocity×mass rankings, and pick the
one whose backtest dominates the traditional momentum/contrarian portfolio.

**Formula.** Map price to position $x(t)=\log S(t)$, so velocity is the log return
$v(t)=dx/dt\approx R(t)$ and cumulated momentum uses a mass $m$ (arXiv:1208.2775v5):
$$p^{(1)}_{t,k}(m,v)=\sum_{i=0}^{k-1} m_{t-i}\,v_{t-i},\qquad
p^{(2)}_{t,k}(m,v)=\frac{\sum_{i=0}^{k-1} m_{t-i}v_{t-i}}{\sum_{i=0}^{k-1} m_{t-i}},\qquad
p^{(3)}_{t,k}(m,v)=\frac{\bar v_{t,k}}{\sigma_{t,k}}$$
Mass candidates: turnover $\upsilon$, fractional transaction value $\tau=\frac{\sum_i \text{value}_{t-i}}
{\text{market cap}}$, inverse volatility $1/\sigma$. Return variant $r$ (raw) or $R$ (log) gives 11 rules
including $p^{(0)}=$ traditional cumulative return ($m\equiv1$). Cost-adjusted return
$r_I=|r_W-r_L|-(c_W+c_L)$.

**Required inputs.** Daily prices, volume, transaction value, outstanding shares / market cap, and a return
volatility estimate over the lookback.

**Parameters & defaults.** Weekly 6-week lookback / 6-week holding (the paper's headline pair); deciles or
equal groups; $c_W+c_L$ per §2.2; drop names traded on only one day in the lookback (needed for $\sigma$)
(arXiv:1208.2775v5).

**Observed effect sizes.** KOSPI 200: $p^{(1)}(\upsilon,R)$ 0.261%/week vs $p^{(0)}$ 0.069%/week; MaxDD
33.4%→20.4%; all $p^{(1)}$/$p^{(2)}$ rules cut 95% VaR/CVaR and raise Sharpe in narrow ranges. S&P 500:
$p^{(3)}(1/\sigma,R)$ 0.107%/week vs 0.014% (~7×), vol ~50% lower (arXiv:1208.2775v5).

**Failure modes.** The log-return≈cumulative-return approximation breaks on heavy tails (|v|→∞ around
crises/M&A/earnings), exactly when the ranking matters most (arXiv:1208.2775v5); the "best" class differs by
market (KOSPI favours $p^{(1)}$, S&P favours $p^{(3)}$), so the criterion must be selected out-of-sample; FF3
loadings do not absorb the returns.

### 2.5 LPPL / finite-time-singularity bubble detector
**Purpose.** Flag a super-exponential (bubble) regime and estimate the most probable critical time $t_c$ at
which the regime ends.

**Formula** (arXiv:0905.0220v1). Finite-time singularity (FTS):
$$\ln p(t)=A+B(t_c-t)^m,\qquad B<0,\ 0<m<1$$
Log-periodic power law (LPPL), adding discrete scale invariance:
$$\ln p(t)=A+B(t_c-t)^m\bigl[1+C\cos(\omega\ln(t_c-t)+\phi)\bigr]$$
with preferred scaling ratio $\lambda=e^{2\pi/\omega}$. Positive-feedback derivation: if the growth rate is
itself price-proportional, $dp/dt=c\,p^2$, giving a $1/(t_c-t)$ divergence. A visual first diagnostic: an
*upward-curving* log-price trajectory against linear time (arXiv:0905.0220v1).

**Required inputs.** Long price history for a single index/asset (or the first principal component of a
cross-asset panel of equity indices, freight indices, commodities, metals, energy and currencies); no
fundamentals.

**Parameters & defaults.** $0<m<1$, $B<0$; fit on the run-up window only; crash defined (for the Hang Seng
example) as a drop >15% in <3 weeks; report $t_c$ as a probability, not a date.

**Observed effect sizes.** Excellent calibration on Nasdaq 1997–1999 and on the 8 pre-crash run-ups of the
Hang Seng (avg 13.8%/yr); the first PCA component of the multi-asset panel shows a clear regime change
mid-2008 (arXiv:0905.0220v1).

**Failure modes.** A bubble can land smoothly ~1/3 of the time; crashes may occur before $t_c$ or not at all —
only probabilistic forecasts are valid (arXiv:0905.0220v1). $t_c$ and $m$ are jointly weakly identified on
short windows and sensitive to the fit end-point; do not treat a fitted $t_c$ as a scheduled event.

### 2.6 Sociophysics local-majority separator / crash alarm (research only)
**Purpose.** A closed-form opinion-dynamics indicator of how far a market's bull/bear split is from the
separator at which a trend inverts, and how fast a mood shift converts into a crash.

**Formula** (arXiv:1106.1577v1). Groups of size 3:
$$p_{t+1}=p_t^3+3p_t^2(1-p_t),\qquad p_S=0,\ p_{c,3}=0.50\ (\text{unstable}),\ p_B=1,\qquad
n\simeq-\frac{\ln|p_{c,3}-p_0|}{\ln(3/2)}$$
Groups of size 4 with optimism $k\in[0,1]$:
$$p_{t+1}=p_t^4+4p_t^3(1-p_t)+6k\,p_t^2(1-p_t)^2,\qquad
p_{c,4}^{k}=\frac{6k-1-\sqrt{13-36k+36k^2}}{6(2k-1)}$$
with $p^{1}_{c,4}\simeq0.23$, $p^{0}_{c,4}\simeq0.77$, $p^{0.5}_{c,4}=0.50$.

**Required inputs.** A daily buy/sell (or order-flow) balance proxy $p_t$ for one asset, e.g. the signed-volume
share or up/down tick share; an estimate of $k$ (market mood) from news sentiment or a breadth measure.

**Parameters & defaults.** $p_0$ = opening buy share; $k$ is *not* observable and must be proxied — the paper
does not estimate it on real data; report results across the full $k\in[0,1]$ range.

**Observed effect sizes.** Purely analytic in the paper: a 5% buy shortfall ($p_0=0.45$) reaches the down limit
in 8 interactions; a $k$:1→0 shift jumps the separator 0.23→0.77 and reaches the down limit in 2–3 updates,
i.e. a crash (arXiv:1106.1577v1).

**Failure modes.** No calibration to real markets anywhere in the paper; the separator depends entirely on the
unobservable $k$, and the mapping from a market split to $p_t$ is not defined empirically. Use as a regime
*label*, not a signal, and only after fitting $k$ from an independent sentiment series.

## 3. Data requirements → available endpoints

Provider rows below are real entries in `strategies/endpoints.json` ("probe status" = the catalog `code`);
**gap** means no current provider can supply it. `moomoo` rows are `gateway` (SDK via local OpenD, not
live-probed).

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| Daily OHLCV panel (prices, volume, turnover base) | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Daily OHLCV (secondary panel) | `https://api.tiingo.com/tiingo/daily/AAPL/prices` | `core_stock_apis` | tiingo | ok |
| Daily/prev aggregate bars (third source) | `https://api.massive.com/v2/aggs/ticker/AAPL/prev` | `core_stock_apis` | massive | ok |
| Intraday bars (weekly/6-week ranking at finer granularity) | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Alternative EOD source | `https://api.stockdata.org/v1/data/eod` | `core_stock_apis` | stockdata | ok |
| Tradable symbol universe / cap construction input | `https://eodhd.com/api/exchange-symbol-list/US` | `exchange_symbols` | eodhd | ok |
| Dividends (total returns for momentum/factor leg returns) | `https://eodhd.com/api/div/AAPL` | `corporate_actions` | eodhd | ok |
| Dividend calendar (cross-check) | `https://api.benzinga.com/api/v2.2/calendar/dividends` | `corporate_actions` | benzinga | ok |
| Fundamentals (book equity, OP, Inv inputs) | `https://api.tiingo.com/tiingo/fundamentals/AAPL/statements` | `fundamental_data` | tiingo | ok |
| Fundamentals (secondary) | `https://www.alphavantage.co/query` | `fundamental_data` | alpha_vantage | ok |
| Technical indicators (momenta/volatility pre-compute) | `https://www.alphavantage.co/query` | `technical_indicators` | alpha_vantage | ok |
| Risk-free rate (excess returns, Sharpe) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Short interest (crowding overlay on momentum legs) | `moomoo://get_short_interest` | `short_interest` | moomoo | gateway |
| Institutional holdings (investor-group proxy) | `moomoo://get_shareholders_institutional` | `institution_data` | moomoo | gateway |
| Insider trades (smart-money overlay) | `moomoo://get_insider_trade_list` | `smart_money` | moomoo | gateway |
| **Fama–French / Carhart / FF5 factor-return series (MKT, SMB, HML, RMW, CMA)** | — | — | — | **gap** |
| **Point-in-time market cap and shares outstanding (as-of formation date)** | — | — | — | **gap** |
| **Point-in-time book equity / OP / Inv (announcement-lagged characteristics)** | — | — | — | **gap** |
| **Net flows by investor group (foreign / institutional / individual)** | — | — | — | **gap** |
| **Non-US universes (China A-share CSMAR, KOSPI 200 membership)** | — | — | — | **gap** |

**What each gap costs, quantified.** (i) *Factor-return series.* Both the FF5-vs-FF3 GRS comparison
(arXiv:2112.03170v1) and the Fama–French-style attribution in arXiv:1208.2775v5 assume an externally
published factor series. Without it FinRobot must build SMB/HML/RMW/CMA from the panel, which requires
point-in-time market cap and announcement-lagged book data — so the factor test is a *build*, not a *fetch*,
and inherits survivorship bias from eodhd/tiingo panels. (ii) *Point-in-time characteristics.* The A-share
study explicitly warns that annual reports are released in March/April of the following year, so formation at
end-December on financial data is look-ahead; the same problem applies to every US factor build on current-only
fundamentals (arXiv:2112.03170v1). (iii) *Investor-group flows.* The strongest single cross-sectional result
in arXiv:1211.6517v1 — foreign net buying predicts positive returns, concentrated in large caps — cannot be
replicated without per-group net flow series; `moomoo` institutional *holdings* are a level, not a daily flow,
and no provider serves the Korean or a US equivalent. (iv) *Non-US universes.* Both momentum papers
(arXiv:1211.6517v1, arXiv:1208.2775v5) and the A-share factor study (arXiv:2112.03170v1) run on CSMAR/KRX/Bloomberg
data that the catalog does not cover; their effects (0.1–1.0%/month) are therefore validation references, not
deployable on the current US stack.

## 4. Pitfalls, validation and measurement

- **Look-ahead in characteristic timing.** Annual accounting statements are disclosed in March/April of the
  following year; forming B/M, OP and Inv portfolios at end-December on those numbers leaks future
  information (arXiv:2112.03170v1). Lag every accounting input to its announcement date.
- **GRS is a comparison, not a rejection.** Both FF3 and FF5 accept the intercept-zero null at 5% in the
  Chinese sample; the *decision* is the ranking of GRS statistics, and $A|\alpha_i|$ should be reported
  alongside (it even *rises* for FF5 on the Size-B/M sort, 0.019→0.101) (arXiv:2112.03170v1).
- **Redundancy ≠ irrelevance.** A non-significant $h_i/c_i$ in one full-sample regression coexists with
  strongly significant loadings in the orthogonalised 5×5 sorts; test both before calling a factor dead
  (arXiv:2112.03170v1).
- **Policy/regime dependence of factor results.** The A-share conclusion flips with the sample period
  (1995–2014 vs 2005–2020) because of the 2005 share-structure reform; fix the sample at a post-reform,
  policy-homogeneous window (arXiv:2112.03170v1).
- **Universe construction is the treatment.** Momentum results are not homogeneous in the universe; index
  membership is cap/sector-based, not random, so a "universe shrinkage" effect is a statement about the
  construction rule (arXiv:1211.6517v1). Never treat a universe restriction as a nuisance parameter.
- **Costs and one-time charging.** At 35 bps per basket (70 bps round-trip) short-horizon momentum turns
  negative while longer holding survives because the charge is one-time; report both raw and implemented
  returns (arXiv:1211.6517v1, arXiv:1208.2775v5).
- **Overlapping portfolios.** Overlapping J/K windows enlarge the sample and create serial dependence; the
  papers use them deliberately (to tame seasonality) but any significance test must account for the overlap
  (arXiv:1208.2775v5).
- **Tail invalidation of the log-return proxy.** $r(t)=\exp(v)-1$ collapses to $v$ only for $|v|\ll1$; around
  crises, bankruptcies and M&A the higher-order terms dominate and the ranking changes (arXiv:1208.2775v5).
- **Probabilistic bubble forecasting.** LPPL gives a critical *time* whose arrival is uncertain: a bubble
  lands smoothly ~1/3 of the time and a crash can precede $t_c$; report a probability, never a date
  (arXiv:0905.0220v1).
- **Lab and model statistics are not market statistics.** The institutionalisation result (common discrepancy
  rising over 10 periods, 9/10 sessions) is in a synthetic double auction with 6 traders and a known dividend
  distribution (arXiv:1609.04629v1); the Galam separator rests on an unobservable mood $k$
  (arXiv:1106.1577v1). Use both as null-hypothesis checklists for real bubble diagnostics, not as signals.

## 5. Recommended first implementation in FinRobot

Ranked by value-per-effort against what the data layer can fetch today. Items 1–4 are buildable now;
items 5–6 are partially blocked; items 7–8 are research.

1. **Panel → factor pipeline + GRS comparator.** *What:* build MKT/SMB/HML/RMW/CMA via the 2×3 sorts of
   §2.1 from the daily panel and fundamentals, run the 5×5 regressions, orthogonalise HML/CMA, and output the
   GRS table plus $A|\alpha_i|$ per sort. *Data:* eodhd/tiingo panel, dividends, federal_reserve risk-free,
   tiingo/alpha_vantage fundamentals. *Passes when:* FF5 GRS < FF3 GRS on the same 25 portfolios and the
   orthogonalised HML/CMA loadings are significant where the corpus reports them. *Risk:* factor returns are a
   **gap** — the series is approximated from a survivorship-prone panel; document it. Effort: **M–L**.
2. **Momentum decile backtester with cost and universe partition.** *What:* J/K lookback/holding grid, decile
   sort, dollar-neutral portfolio, $r_I=r_\Pi-(c_W+c_L)$, and a universe-shrinkage sweep (cap-decile
   partitions standing in for index membership). *Data:* adjusted EOD panel + dividends. *Passes when:* the
   strategy's sign and Sharpe reproduce the corpus pattern (long-horizon survives 70 bps; short-horizon does
   not) on an out-of-sample split. Effort: **S–M**.
3. **Turnover/liquidity portfolio.** *What:* the fractional-volume sort of §2.3 with the same cost
   convention. *Data:* volume + outstanding shares (derived from fundamentals × price). *Passes when:*
   monthly implemented return stays positive after 70 bps with volatility below the return-momentum variant,
   as in the corpus (1.4–1.9%, 7.25–8.75%). Effort: **S**.
4. **Physical-momentum ranking module.** *What:* implement $p^{(1)},p^{(2)},p^{(3)}$ with the three mass
   candidates and select the best rule by out-of-sample Sharpe on a weekly 6/6 grid. *Data:* same panel +
   volatility. *Passes when:* at least one physical rule beats $p^{(0)}$ with lower max drawdown. Effort:
   **S–M**.
5. **LPPL bubble monitor.** *What:* fit the FTS and LPPL models on index-level run-up windows, report
   $\hat m,\hat\omega,\hat t_c$ and the smoothed crash probability. *Data:* long index history (eodhd/
   massive aggs) and/or the first PCA component of a multi-asset panel. *Passes when:* detected pre-crash
   windows align with known drawdowns (>15% in <3 weeks) on a held-out historical run. *Risk:* only
   probabilistic; parameter identifiability on short windows. Effort: **M**.
6. **Investor-flow sub-portfolio.** *What:* sort by net flow by group and check the sign pattern (foreign
   positive / individuals negative). *Data:* **blocked** — net flows by investor group are a **gap**;
   `moomoo` gives holdings levels only. Prototype on holdings *changes* and label clearly as a proxy.
   Effort: **M (after data)**.
7. **Sociophysics separator indicator.** *What:* compute a buy-share proxy $p_t$ and report $p_{c,4}^k$ across
   the full $k$ range as a regime label. *Data:* signed-volume or up/down-tick share from intraday bars.
   *Passes when:* the label's extremes coincide with realised trend reversals more often than a coin flip
   out-of-sample. Effort: **S–M** (research).
8. **Common-discrepancy bubble diagnostic.** *What:* port the dispersion/common decomposition of price
   deviations from intrinsic value to an experimental or index-relative setting, as a validation checklist
   rather than a signal. *Data:* requires an intrinsic-value proxy (dividend-discount or earnings model) —
   **gap** in the current layer. Effort: **M** (research).

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 2112.03170v1 | A revised comparison between FF five-factor model and three-factor model, based on China's A-share market | 2021 |
| 1609.04629v1 | Institutionalization in Efficient Markets: The Case of Price Bubbles | 2016 |
| 1211.6517v1 | Momentum universe shrinkage effect in price momentum | 2012 |
| 1208.2775v5 | Physical approach to price momentum and its application to momentum strategy | 2012 |
| 1106.1577v1 | Market efficiency, anticipation and the formation of bubbles-crashes | 2011 |
| 0905.0220v1 | Financial Bubbles, Real Estate bubbles, Derivative Bubbles, and the Financial and Economic Crisis | 2009 |
