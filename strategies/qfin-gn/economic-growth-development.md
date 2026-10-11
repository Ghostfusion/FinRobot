# Economic Growth & Development — learnings from the q-fin.GN corpus

`287` of 3095 corpus papers matched this category (280 with PDFs); this doc is based on a close reading of `6`.

Headline: **this cluster is macroeconomic context, not tradable signal.** The six assigned papers split into
one *estimator* — a scale-resolved, bimodal ("secular bipolar") decomposition of US real GDP per capita
(arXiv:1607.04136v1) — and five papers by a single author (Nielsen) that make one methodological argument
about historical GDP and GDP/cap series and apply it to five regional datasets (world, Latin America, the
former USSR, Asia, Africa). The argument is negative: the historical GDP/cap series are *hyperbolic*
($1/X = a - kt$ is a straight line), and their apparent "Malthusian stagnation → takeoff → sustained growth"
shape is a purely mathematical property of dividing two hyperbolic distributions, not evidence of three
regimes. There is no cross-sectional return signal, no alpha, no execution content. What *does* transfer is
estimation machinery for long macro series: reciprocal-transform trend/saturation fitting, structural-break
("diversion") detection on the reciprocal line, wavelet scale-resolved local growth rates, and bimodal
regime labelling. The binding constraint is data: the papers' core samples (Maddison AD 1–2008;
US annual real GDP/cap 1800–2010) are far longer than anything FinRobot's endpoint layer serves — `fred`
US real GDP starts 1947 quarterly, and no catalogued provider carries pre-1947 or cross-country history
(§3).

## 1. What the corpus actually offers

- **A bimodal growth-rate distribution for US real GDP per capita** (r-US-GDP-pc). The probability density of
  the *local annualized growth rate* (wavelet scale $s$, averaged over roughly $[t-s,\,t+s]$) is unimodal at
  the largest scale but clearly bimodal at scales of 15, 9 and 6 months, with two stable peaks bracketing
  the long-term average: low mode $\approx 1\%$ and high mode $\approx 3\%$ for $s=6$ months, $\approx 1.1\%$
  / $\approx 2.8\%$ at 9 months, $\approx 1.5\%$ / $\approx 2.8\%$ at 15 months (arXiv:1607.04136v1).
- **The long-term mean is the compensation of the two modes, not a "natural" rate.** OLS slope of
  $\ln(\text{r-US-GDP-pc})$ is $2.0\%$ for quarterly 1947–2015 (chained 2009 USD) and $1.6\%$ for annual
  1800–2010 (1990 Geary-Khamis dollar); the growth rate since 2008 over the last 8 years is $\approx 1.1\%$
  (arXiv:1607.04136v1). The 30-month-scale density peaks at the OLS value $2\%$; the bimodality is a
  small-scale feature (arXiv:1607.04136v1).
- **Annual-data confirmation (1800–2010).** Peak of the density at the 8-year scale is $1.5\%$; the two modes
  at 1, 2 and 4 years are low $= 0.2\%, 1\%, 1.2\%$ and high $= 1.4\%, 1.9\%, 1.8\%$; the 50%-quantile growth
  rate is $1.3\%$ and the conditional expectation above that quantile is $3.3\%$ —
  $\mathbb{E}[g \mid g>1.3\%]=3.3\% \gg 1.6\%$ (arXiv:1607.04136v1). At annual sampling the clean bimodality
  is blurred and the density is positively skewed (arXiv:1607.04136v1).
- **The skeleton retains the signal.** Keeping only the local extrema of the wavelet transform and
  reconstructing a synthetic GDP via
  $\text{GDP}_{\text{pseudo}}(t_k;s)=\text{GDP}_0\prod_{i=1}^{k}(1+g_i)^{\Delta t_i}$ reproduces the realised
  r-US-GDP-pc across scales $s = 1,2,4,8$ years (arXiv:1607.04136v1).
- **The five Nielsen papers reject the three-regime Unified Growth Theory (UGT) with one estimator.** Each
  shows that $1/\text{GDP}$ (or $1/\text{GDP/cap}$) is a decreasing straight line over the whole modern
  record, so the series is a single monotone hyperbolic trajectory; splitting it into "Malthusian",
  "post-Malthusian" and "sustained-growth" regimes is unjustified, and the alleged takeoff at 1750/1870/1900
  does not exist (arXiv:1511.09323v2, arXiv:1512.03164v2, arXiv:1512.05074v2, arXiv:1512.06309v2,
  arXiv:1601.01804v2).
- **Pooled GDP/cap (the theory's own data).** World GDP/cap is the ratio of two hyperbolas, i.e. a
  *linearly-modulated hyperbolic* distribution; the fitted world-GDP singularity is at $t_s = 1979$ and the
  world-population singularity at $t_s = 2045$; the ratio's singularity coincides with the earlier GDP one
  ($1979$). The fitted curve's gradient and growth rate increase monotonically through 1750 and 1870, with no
  discontinuity, and it fits the Maddison (2001) data closely (arXiv:1511.09323v2).
- **Latin America.** The data suggest two hyperbolic segments — slow over AD 1–1500 and fast over AD 1600–1870
  — followed by a *diversion to a slower trajectory* from $\approx 1870$; the fast segment's singularity
  $t_s = 1910$ was bypassed by a safe margin of $\approx 40$ years. A brief decline occurs over AD 1500–1600
  (arXiv:1601.01804v2). The slow→fast change happened $\approx 300$ years *before* the UGT-expected 1900
  takeoff (arXiv:1601.01804v2).
- **Africa.** Hyperbolic growth over AD 1–1820; a transition from a slow to a *faster* hyperbolic trajectory
  around 1820; then a diversion to a slower but still-increasing trajectory around 1950
  (arXiv:1512.03164v2). Nothing unusual happens around 1900, where UGT places the takeoff for less-developed
  countries (arXiv:1512.03164v2).
- **Asia (excluding Japan).** GDP is hyperbolic at least from AD 1000 (the AD 1 point is 88% above the fitted
  curve); no Malthusian stagnation, no takeoff; a minor, hard-to-notice disturbance around 1950 after which
  growth returns to the historical hyperbolic trend (arXiv:1512.05074v2).
- **Former USSR.** Hyperbolic over AD 1–1870, fitted $a = 6.547\times10^{-1}$ and $k = 3.452\times10^{-4}$
  (implied singularity $t_s = a/k \approx 1896$), then a diversion to a slower trajectory from $\approx 1870$;
  the Industrial Revolution produced no visible change in the trajectory (arXiv:1512.06309v2).
- **Off-topic / retention note.** None of the six is off-topic. However, five of the six
  (arXiv:1511.09323v2, arXiv:1512.03164v2, arXiv:1512.05074v2, arXiv:1512.06309v2, arXiv:1601.01804v2) are
  essay-length applications of one identical argument by one author, with heavily repeated text: they are
  retained as the *empirical source* of the reciprocal-transform/structural-break method and as explicit
  warnings about metric choice, not as independent evidence. Only arXiv:1607.04136v1 supplies a fitted,
  multi-scale, forecastable estimator.

**Assessment.** Two of the six deliver implementable constructions (a reciprocal trend/break test; a
scale-resolved bimodal growth decomposition). The remaining four are economic-history context that constrains
*how to read* long macro series (never extrapolate a boom rate) but generate nothing to trade.

## 2. Implementable formulas & algorithms

### 2.1 Reciprocal-transform hyperbolic trend / saturation fit
**Purpose.** Decide whether a long macro series (GDP, GDP/cap, sector output, an index level) is well
described by *one monotone hyperbolic trend* rather than by piecewise regimes, and read off an implied
saturation/singularity time. It is a diagnostic that any long-horizon extrapolation should be run through
before being trusted.

**Formula.** Hyperbolic growth is the reciprocal of a linear function,
$$X(t)=\frac{1}{a-kt},\qquad [X(t)]^{-1}=a-kt,\qquad t_s=\frac{a}{k},\qquad t<t_s,$$
with $a,k>0$ and singularity (escape to infinity) at $t_s=a/k$. Fit $a,k$ by OLS of $1/X$ on $t$; the series
is hyperbolic iff $1/X$ is acceptably linear over the window. Equivalently the same curve is
$1/X_{\text{hyperbolic}} \times 1/X_{\text{linear}}$, so a *ratio of two hyperbolas* (the GDP/cap case) is
$\dfrac{a_p-k_p t}{a_g-k_g t}$ and escapes at the earlier of the two singularities.

**Required inputs.** A long, low-frequency level series: annual GDP (or GDP/cap) by country/region, ideally
with the same vintage for GDP and population so the ratio is coherent. Named fields: `date`, `gdp_level`,
`population`.

**Parameters & defaults.** OLS on $1/X$; report $\hat a,\hat k$, $R^2$ of the reciprocal fit, and $t_s$.
The papers fit whole segments (e.g. former-USSR modern segment $a=6.547\times10^{-1}$,
$k=3.452\times10^{-4}$) and read $t_s$ from the fit (arXiv:1512.06309v2).

**Observed effect sizes.** On the Maddison data the reciprocal fit is visually a straight line over centuries
— world GDP/cap singularity $1979$, world population singularity $2045$ (arXiv:1511.09323v2); Latin America
fast segment $t_s=1910$, bypassed by $\approx 40$ years (arXiv:1601.01804v2). The fit "gives excellent fit"
to GDP/cap with gradient and growth rate increasing monotonically (arXiv:1511.09323v2).

**Failure modes.** A hyperbola is *unimodal by construction*; a good reciprocal fit cannot by itself
adjudicate "one regime vs two regimes". The singularity is not a forecast — every paper here finds it
bypassed by a diversion, so never extrapolate the hyperbolic blow-up. If $1/X$ is not linear the test is
inconclusive (the papers accept any monotone-decreasing trajectory as refuting stagnation,
arXiv:1601.01804v2). Modern series have already left the hyperbolic path, so fit only the pre-diversion
segment.

### 2.2 Diversion / structural-break detection on the reciprocal series
**Purpose.** Locate the point where growth leaves its historical trajectory, using a change of *slope* in
$1/X$; this is the papers' replacement for "takeoff" detection and generalises to any long macro series.

**Formula.** On the reciprocal series $y(t)=1/X(t)=a-kt$, a *downward* bend (steeper negative slope) is a
boost to faster growth; an *upward* bend (shallower slope) is a diversion to slower growth. A single-line
fit means no break. Operationally fit a piecewise / segmented regression with a break date $\tau$:
$$y(t)=a_1-k_1 t+\big[(a_2-a_1)-(k_2-k_1)t\big]\,\mathbf 1\{t\ge\tau\},$$
and test $\Delta k = k_2-k_1$ against zero (or use a CUSUM / Bai–Perron scan) with the sign convention above.

**Required inputs.** Same as 2.1; a window long enough that the pre- and post-break slopes differ measurably.

**Parameters & defaults.** Segmented OLS or CUSUM on $y=1/X$; scan $\tau$ over the sample; a bootstrap /
sup-Wald null for break significance. The papers read break dates off the plots rather than testing them, so
no formal cutoff is published.

**Observed effect sizes.** Detected diversions to slower trajectories: Latin America $\approx 1870$
(arXiv:1601.01804v2); Africa $\approx 1950$ (arXiv:1512.03164v2); former USSR $\approx 1870$
(arXiv:1512.06309v2); pooled GDP/cap "linearly-modulated hyperbolic", no 1750/1870 break
(arXiv:1511.09323v2). Africa's slow→fast bend is $\approx 1820$ (arXiv:1512.03164v2).

**Failure modes.** A monotone smooth curve admits no uniquely determined transition time
(arXiv:1511.09323v2); break-date estimates on centennial data are decade-resolution at best. Beware reading
a "takeoff" where the reciprocal is undisturbed (arXiv:1512.05074v2). Do not import the sign convention
without re-deriving it: on $1/X$ the *visual* slope direction is opposite to the growth-rate direction.

### 2.3 Scale-resolved local growth rate (first-derivative-of-Gaussian wavelet)
**Purpose.** Extract the *local annualized growth rate* of a macro level series at a chosen horizon $s$,
without committing to a global trend or a single differencing period; gives the input distribution for the
bimodality test (2.4).

**Formula.** Continuous wavelet transform with the first derivative of a Gaussian (so the transform of a
constant is zero and the slope is recovered exactly for a linear test signal):
$$W[X](s,t)=\frac1s\int \psi^{(1)}\!\Big(\frac{\tau-t}{s}\Big)X(\tau)\,d\tau,\qquad
g(s,t)=W[\ln(\text{r-US-GDP-pc})](s,t),$$
where $W[X](s,t)$ is, for a negligibly supported mother wavelet, the weighted average of $X$ over
$[t-s,\,t+s]$, and the first-derivative wavelet makes it the local slope. The maps are compressed to a
"skeleton" of local maxima/minima over $t$ at fixed $s$.

**Required inputs.** A level series with enough points per scale: $N \gtrsim$ a few $\times\, s$. Quarterly
real GDP (1947–2015) supports 6-, 9-, 15- and 30-month scales; annual GDP (1800–2010) supports 1-, 2-, 4-
and 8-year scales (arXiv:1607.04136v1).

**Parameters & defaults.** Gaussian mother wavelet (paper reports robustness to other real-valued wavelets);
scales $s=1,2,4,8$ years (annual) or $6,9,15,30$ months (quarterly); part of the map is discarded to edge
effects (the "nonlinear conical envelope") (arXiv:1607.04136v1).

**Observed effect sizes.** Long-term rate recovered as the 30-month/8-year peak: $2.0\%$ quarterly,
$1.5\%$ annual; bimodality emerges at $\le 15$ months / $\le 4$ years (arXiv:1607.04136v1).

**Failure modes.** Edge effects at both ends of the sample. Scale choice changes the answer — at 30 months the
density is unimodal, so a "bimodal growth" claim must state the scale. Redundant transform must be compressed
(skeleton) before interpretation. This is a descriptive decomposition, not a forecast: it does not model the
next regime switch.

### 2.4 Bimodal regime decomposition and skeleton reconstruction
**Purpose.** Turn the scale-resolved growth rates into a two-state (low/high) regime label series, and test
whether that label series is sufficient to rebuild the level path.

**Formula.** Kernel-density estimate of $\{g(s,t)\}$ (or of the skeleton values) at fixed $s$; identify the
two dominant peaks $\mu_{\text{low}}(s),\mu_{\text{high}}(s)$; label $z_t=\text{high}$ if
$g(s,t)>$ separating valley. Reconstruct
$$\hat X(t_k;s)=X_0\prod_{i=1}^{k}(1+g_i(s))^{\Delta t_i};$$
agreement of $\hat X$ with $X$ across scales validates that the skeleton retained the levels information.

**Required inputs.** The $g(s,t)$ field from 2.3, plus $X_0$ (the initial level).

**Parameters & defaults.** Gaussian KDE with width $0.002$ (paper checks robustness over a factor of two)
(arXiv:1607.04136v1); separating threshold between the modes.

**Observed effect sizes.** Mode pairs $(\mu_{\text{low}},\mu_{\text{high}})$: $(1\%,3\%)$ at 6 months,
$(1.1\%,2.8\%)$ at 9 months, $(1.5\%,2.8\%)$ at 15 months; long-run mean $2.0\%$ lies between them
(arXiv:1607.04136v1). Synthetic GDP from the skeleton matches realised GDP at $s=1,2,4,8$ years
(arXiv:1607.04136v1).

**Failure modes.** Annual sampling averages across regime transitions, blurring the modes and producing
positive skew (arXiv:1607.04136v1); the 2008-onward "low regime" is only 8 years of data, so its persistence
is not yet estimable; labels are contemporaneous (a state description, not a predictor). The reconstruction
overshoots around 1945–1955 (WWII-level distortion) (arXiv:1607.04136v1).

### 2.5 Saturation / limit check via ratio-of-hyperbolas (context only)
**Purpose.** Given a ratio series (GDP per capita, output per worker, index-per-capita), decide whether its
apparent "steepening" is a genuine regime change or the mathematical consequence of dividing two monotone
hyperbolas. In the papers this is a *falsification tool*, not a trading construction.

**Formula.** $X(t)=f(t)/g(t)$ with $f,g$ hyperbolic; the ratio is linearly modulated,
$X(t)=(a_p-k_p t)/(a_g-k_g t)$, escapes at $\min(a_f/k_f,\,a_g/k_g)$, and has monotonically increasing gradient
and growth rate regardless of any regime story.

**Required inputs.** Coherent numerator and denominator level series (e.g. GDP and population).

**Parameters & defaults.** Fit each component by 2.1, then form and plot the ratio and its gradient/growth
rate; look for a *discontinuity*, which the data do not show (arXiv:1511.09323v2).

**Observed effect sizes.** Division of two purely mathematical hyperbolas reproduces the full "flat–transition–
steep" shape that motivated UGT, with no economic content (arXiv:1511.09323v2).

**Failure modes.** A tempting but non-actionable result: nothing here is forecastable or tradable. Its only
practical use is to stop a long-horizon extrapolation from being read as a regime forecast.

## 3. Data requirements → available endpoints

The rows below are real entries in `strategies/endpoints.json`; "gap" means **no current provider supplies
it**. The papers' core inputs (long historical national-accounts panels) are the binding constraint: FinRobot
can fetch *current-vintage* US macro via `fred`, but the multi-century, cross-country series the papers use
are absent.

| Input | Endpoint | Category | Provider | Probe status |
|---|---|---|---|---|
| US macro time series (real GDP, GDP/cap, population) | `https://api.stlouisfed.org/fred/series/observations` | `macro_data` | fred | ok |
| Macro indicator list (US and cross-market) | `moomoo://get_macro_indicator_list` | `macro_data` | moomoo | gateway (not live-probed) |
| Economic calendar (release dates for macro prints) | `moomoo://get_economic_calendar` | `economic_calendar` | moomoo | gateway (not live-probed) |
| Fed target-rate path | `moomoo://get_fed_watch_target_rate` | `fed_watch` | moomoo | gateway (not live-probed) |
| Treasury yield curve (discounting long-horizon cash flows) | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all` | `risk_free_curve` | federal_reserve | ok |
| Tradable proxy bars for GDP-linked assets | `https://eodhd.com/api/eod/AAPL` | `core_stock_apis` | eodhd | ok |
| Intraday bars for a macro-conditioned overlay | `https://api.twelvedata.com/time_series` | `core_stock_apis` | twelvedata | ok |
| Long-horizon US annual real GDP/cap (1800–2010, 1990 GKD) | — | — | — | **gap** |
| Cross-country historical GDP/population panel (Maddison AD 1–2008) | — | — | — | **gap** |
| Pre-1947 quarterly national accounts | — | — | — | **gap** |
| Consistent single-vintage GDP **and** population for the per-capita ratio | — | — | — | **gap** |

**What each gap costs, quantified.** The wavelet bimodality result needs $N \gtrsim$ a few times the largest
scale: quarterly 1947–2015 ($\approx 272$ quarters) to resolve 6–30-month scales, and annual 1800–2010
($\approx 210$ points) to resolve 1–8-year scales (arXiv:1607.04136v1). FRED's workhorse US real GDP is
post-1947, so the *1800–2010 annual* panel — and every cross-country comparison in the five Nielsen papers
(Maddison AD 1–2008, region-level) — is a **gap**: without it the only testable object is post-war US, which
cannot distinguish "secular bipolar" (arXiv:1607.04136v1) from "post-diversion slower trajectory"
(arXiv:1512.03164v2, arXiv:1601.01804v2). The per-capita ratio needs GDP *and* population on one vintage;
mixing a current FRED GDP vintage with a historical population series introduces exactly the revision
leakage that makes the reciprocal fit unstable. Empty cells are the honest state, not a missing integration.

## 4. Pitfalls, validation and measurement

- **Metric choice is the whole argument.** The papers repeatedly stress that the *mean* growth rate is not
  the *typical* growth rate: the long-term $2\%$ "almost never describes the actual local growth rate", and
  the conditionally-high mean is $3.3\% \gg 1.6\%$ (arXiv:1607.04136v1). Report modes/quantiles alongside the
  mean; a strategy gated on "the economy grows $2\%$" is conditioned on a value that rarely occurs.
- **The hyperbolic illusion.** A single monotone distribution "looks like" two or three regimes joined by a
  transition; the reciprocal $1/X=a-kt$ is a straight line, and a straight line cannot be split into regimes
  (arXiv:1511.09323v2, arXiv:1512.05074v2, arXiv:1512.06309v2). Any structural-break test on a long macro
  series must therefore be run on the reciprocal (or an explicit segmented model) *and* have its break
  significance tested — visual inspection is exactly the error being refuted.
- **Look-ahead / vintage leakage.** The "slower growth since 2008" reading uses data through 2015; that is
  8 years, shorter than any bimodal scale claimed to be stable (arXiv:1607.04136v1). Chained-2009-dollar and
  1990-GKD vintages differ; comparing a current FRED vintage against the papers' levels mixes revisions.
  Walk-forward any fitted trend/break and re-fit on pre-break data only.
- **Sample split as robustness, not validation.** The bimodality appears in *both* the quarterly 1947–2015
  and the annual 1800–2010 samples (arXiv:1607.04136v1) — a stronger check than any in-sample fit. Conversely
  the annual sample blurs transitions and yields positive skew, so agreement must be argued at matched scales.
- **Scale multiplicity.** The density is unimodal at 30 months and bimodal at 6–15 months
  (arXiv:1607.04136v1); testing many scales without correction or without pre-registering one invites a
  spurious "finding". Fix the scale (and the KDE width) before looking; report the peak locations'
  stability across a factor-of-two kernel-width change, as the paper does.
- **Cost of naive extrapolation.** The Dallas Fed cost of the 2008 crisis ($6–14T) assumes output returns to
  the *pre-crisis* trend, which the paper calls abnormally high; extrapolating a boom rate understates the
  consolidation and mis-measures "loss" (arXiv:1607.04136v1). The same error applies to any GDP-anchored
  valuation or macro overlay.
- **Regime persistence vs prediction.** Nothing in either method forecasts the next switch; the skeleton is a
  description and the diversion dates (≈1870, ≈1950) are ex-post (arXiv:1607.04136v1, arXiv:1512.03164v2,
  arXiv:1512.06309v2). Treat any regime label as a *state feature*, and validate it on an out-of-sample block
  before using it to gate positions.
- **Theory-contradiction caveat.** All five Nielsen papers are adversarial and self-citing; their positive
  claim (hyperbolic growth, later diversions) is well-supported by the reciprocal plots they show, but no
  formal model-selection statistic (AIC/BIC against a piecewise alternative) is reported. Reproduce with an
  explicit segmented-regression comparison before relying on the "single mechanism" conclusion.

## 5. Recommended first implementation in FinRobot

Ranked by value-per-effort against what the data layer can fetch today. Items 1–3 are buildable now on
`fred` + `eodhd`; items 4–5 are diagnostics/context and item 6 is blocked on a long-history panel.

1. **Reciprocal-transform trend/break diagnostic.** *What:* a module that takes any long level series,
   fits $1/X=a-kt$ by OLS, reports $\hat a,\hat k,t_s,R^2$, then runs a segmented-regression/CUSUM break scan
   with the upward/downward sign convention (§2.1–2.2). *Data:* `fred` `series/observations` for US macro;
   `eodhd` `eod` for index/level proxies. *Value:* stops any long-horizon extrapolation from being read as a
   regime forecast. *Passes when:* it recovers a clean reciprocal line on a known-hyperbolic series and
   flags a diversion at a defensible date with a sup-Wald $p<0.05$. *Effort:* S.
2. **Scale-resolved growth-rate feature on US real GDP/cap.** *What:* first-derivative-of-Gaussian CWT
   (§2.3) over scales $6,9,15,30$ months on post-1947 quarterly FRED real GDP and population, with edge
   regions masked. *Data:* `fred`. *Value:* the only genuinely new signal-adjacent object in this category —
   a macro regime feature for overlays. *Passes when:* the 30-month density peaks at the OLS long-run rate and
   the 6–15-month densities are bimodal with the published peak locations within tolerance. *Effort:* M.
3. **Bimodal low/high regime label service.** *What:* KDE ($\text{width}=0.002$) + valley threshold on the
   6–15-month growth rates, emitting a two-state `growth_regime` label per date (§2.4). *Data:* output of
   item 2. *Value:* a coarse macro state for gating strategies; keeps the "2% average hides ~1% and ~3% modes"
   fact visible. *Passes when:* labels are stable across KDE widths in $[0.001,0.004]$ and place 2008–2015 in
   the low mode. *Effort:* S.
4. **Saturation/limit check on ratio series.** *What:* the ratio-of-hyperbolas diagnostic (§2.5) for
   GDP/cap-like series, explicitly labelled non-tradable. *Data:* `fred` GDP + population. *Value:* documents
   that apparent steepening need not be a regime change. *Effort:* S.
5. **Cross-corpus hand-off, not a rebuild.** *What:* route the regime label (item 3) and the reciprocal
   break dates into the existing regime/econometrics machinery rather than re-deriving state inference —
   [`../qfin-st/regime-switching.md`](../qfin-st/regime-switching.md) and
   [`../qfin-st/econometrics-forecasting.md`](../qfin-st/econometrics-forecasting.md). *Effort:* S.
6. **Acquire a long-history macro panel (blocked).** *What:* ingest a Maddison-style historical GDP/population
   panel (AD 1–2008, region level) or at minimum pre-1947 US annual real GDP/cap, registered as a new data
   category. *Value:* the only way to test the bundled "secular bipolar" and "diversion" claims on the data
   that produced them; today both are unverifiable on `fred` alone. *Risk:* licensing/attribution, irregular
   sampling, and single-vintage coherence between GDP and population. *Effort:* M–L (after the panel is
   sourced).

## Appendix — papers read

| arXiv id | Title | Year |
|---|---|---|
| 1607.04136v1 | Secular bipolar growth rate of the real US GDP per capita: implications for understanding past and future economic growth | 2015 |
| 1601.01804v2 | Unified Growth Theory Contradicted by the Economic Growth in Latin America | 2016 |
| 1512.06309v2 | Unified Growth Theory Contradicted by the Economic Growth in the Former USSR | 2015 |
| 1512.05074v2 | Unified Growth Theory Contradicted by the Economic Growth in Asia | 2015 |
| 1512.03164v2 | Unified Growth Theory Contradicted by the Economic Growth in Africa | 2015 |
| 1511.09323v2 | Unified Growth Theory Contradicted by the GDP/cap Data | 2015 |
